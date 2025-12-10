# symptom_kb.py (RL-integrated)
import os
import json
import faiss
import numpy as np
import tempfile
import struct
import re
import asyncio
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
from models import SymptomCluster, SymptomExample, LLMInteraction
from dotenv import load_dotenv

# Use shared LLM client & utils so embeddings and generation are consistent
from llm_client import genai_client
from utils import ai_generate, embed_with_client, cos_sim

# RL bandit (contextual) - chooses prompt variant, temp, ctx_size, model
try:
    from rl_core import bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    RL_ENABLED = True
except Exception:
    # If rl_core isn't available, gracefully degrade
    bandit = None
    ACTIONS = []
    PROMPT_VARIANTS = []
    MODELS = []
    RL_ENABLED = False

load_dotenv()

# config
EMBED_MODEL = "models/text-embedding-004"
INDEX_FILE = "symptom_index.faiss"
META_FILE = "symptom_meta.json"
EMBED_DIM = 768
SIMILARITY_THRESHOLD_DEFAULT = 0.78

# ----------------------
# UTIL: vector <-> bytes
# ----------------------
def vec_to_bytes(v: np.ndarray) -> bytes:
    return v.astype("float32").tobytes()

def bytes_to_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype="float32")

# ----------------------
# FAISS Manager
# ----------------------
class FaissManager:
    def __init__(self, dim=EMBED_DIM, index_file=INDEX_FILE, meta_file=META_FILE):
        self.dim = dim
        self.index_file = index_file
        self.meta_file = meta_file
        self.index = None
        self.meta = {"ids": []}  # row -> cluster_id mapping
        self._load()

    def _load(self):
        if os.path.exists(self.index_file):
            try:
                self.index = faiss.read_index(self.index_file)
            except Exception as e:
                print("FAISS load failed:", e)
                self.index = None
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dim)
        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    self.meta = json.load(f)
            except Exception:
                self.meta = {"ids": []}

    def save(self):
        try:
            faiss.write_index(self.index, self.index_file)
        except Exception as e:
            print("faiss write failed:", e)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.meta, f)

    def add(self, vector: np.ndarray, cluster_id: int):
        v = vector.astype("float32").reshape(1, -1)
        faiss.normalize_L2(v)
        self.index.add(v)
        self.meta["ids"].append(cluster_id)
        self.save()

    def search(self, vector: np.ndarray, k=1) -> Tuple[List[float], List[int]]:
        v = vector.astype("float32").reshape(1, -1)
        faiss.normalize_L2(v)
        if self.index.ntotal == 0:
            return [], []
        D, I = self.index.search(v, k)
        dlist = D[0].tolist()
        ilist = I[0].tolist()
        mapped = []
        for rid in ilist:
            if rid < len(self.meta["ids"]):
                mapped.append(self.meta["ids"][rid])
            else:
                mapped.append(None)
        return dlist, mapped

    def rebuild_from_db(self, db: Session):
        # rebuild index from DB centroids — safe and consistent
        clusters = db.query(SymptomCluster).all()
        centroids = []
        ids = []
        for c in clusters:
            if c.centroid:
                vec = bytes_to_vec(c.centroid)
                centroids.append(vec)
                ids.append(c.id)
        if not centroids:
            self.index = faiss.IndexFlatIP(self.dim)
            self.meta = {"ids": []}
            self.save()
            return
        arr = np.vstack([v.astype("float32") for v in centroids])
        faiss.normalize_L2(arr)
        new_index = faiss.IndexFlatIP(arr.shape[1])
        new_index.add(arr)
        self.index = new_index
        self.meta["ids"] = ids
        self.save()

# ----------------------
# EMBEDDING + EXTRACTION
# ----------------------
def embed_texts_sync(texts: List[str]) -> List[np.ndarray]:
    """Synchronous wrapper using embed_with_client (which uses shared genai_client)."""
    if not texts:
        return []
    vectors = []
    for t in texts:
        vec = embed_with_client(genai_client, t)
        vectors.append(np.array(vec, dtype="float32"))
    return vectors

async def extract_symptoms_with_generative_llm(text: str, db: Session,
                                               context_vector: Optional[np.ndarray]=None) -> Dict:
    """
    RL-enabled symptom extraction.
    - If RL is enabled, bandit chooses an action (prompt variant, temp, model).
    - We call the chosen prompt to extract JSON array of phrases.
    - We log an LLMInteraction row containing action_id and metrics for nightly updates.
    """
    # choose RL action (if available)
    action_id = None
    chosen_prompt_template = None
    chosen_model = None
    chosen_temp = 0.0
    chosen_ctx_size = None
    similarity_threshold = SIMILARITY_THRESHOLD_DEFAULT

    if RL_ENABLED and bandit is not None and context_vector is not None:
        # ensure vector dims match bandit.d
        x = np.array(context_vector, dtype=float)
        if x.shape[0] != bandit.d:
            if x.shape[0] > bandit.d:
                x = x[:bandit.d]
            else:
                pad = np.zeros(bandit.d - x.shape[0], dtype=float)
                x = np.concatenate([x, pad])
        # choose action
        action_id, _ = bandit.choose(x, eps=0.05)
        prompt_idx, chosen_temp, ctx_size, model_idx, *maybe = ACTIONS[action_id]
        chosen_prompt_template = PROMPT_VARIANTS[prompt_idx]
        chosen_model = MODELS[model_idx]
        chosen_ctx_size = ctx_size
        # optional: let bandit action include threshold override (if you encode it)
        if len(maybe) >= 1 and maybe[0] is not None:
            similarity_threshold = maybe[0]

    # build extraction prompt
    if chosen_prompt_template:
        extraction_prompt = chosen_prompt_template + "\n\n" + f"Extract short symptom phrases from the patient message below and return a JSON array of strings.\nPatient message: \"\"\"{text}\"\"\""
    else:
        extraction_prompt = f"""
Extract short symptom phrases from the patient message below. Return a JSON array of short strings ONLY.
Patient message: \"\"\"{text}\"\"\" 
Example output: ["bleeding gums", "sensitivity to cold"]
"""

    # Run LLM call in executor to avoid blocking event loop
    loop = asyncio.get_running_loop()
    try:
        res = await loop.run_in_executor(None, lambda: ai_generate(
            prompt=extraction_prompt,
            temperature=chosen_temp if chosen_prompt_template else 0.0,
            model=chosen_model if chosen_model else "gemini-2.5-flash",
            client_override=genai_client
        ))
        # ai_generate returns text string (strip inside ai_generate)
        clean = res.strip()
    except Exception as e:
        print("LLM extraction call failed:", e)
        clean = ""

    # robust JSON parse
    phrases = []
    try:
        # try to strip code fences
        if clean.startswith("```"):
            clean = clean.strip("` \n")
        parsed = json.loads(clean)
        if isinstance(parsed, list):
            phrases = [p.strip() for p in parsed if isinstance(p, str) and p.strip()]
    except Exception:
        # very permissive fallback: split by commas/newlines and dedupe
        raw_parts = re.split(r"[,\n;]+", clean or "")
        if raw_parts:
            phrases = [p.strip().strip('"') for p in raw_parts if p.strip()]
        if not phrases:
            phrases = [text.strip()]

    # compute embeddings synchronously (cheap)
    vectors = embed_texts_sync(phrases)

    # prepare return structure and log an LLMInteraction for nightly training
    request_id = str(uuid.uuid4())
    llm_log = {
        "request_id": request_id,
        "query": text,
        "extracted_phrases": phrases,
        "action_id": action_id,
        "prompt_used": chosen_prompt_template or extraction_prompt,
        "model_used": chosen_model,
        "temp_used": chosen_temp,
        "ctx_size": chosen_ctx_size,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    }

    # Save an initial LLMInteraction row (so nightly audit can update rewards)
    try:
        # compute quick metrics if context_vector provided
        sem_sims = []
        grounded_sims = []
        if context_vector is not None and vectors:
            ctx_vec = np.array(context_vector, dtype=float)
            for v in vectors:
                a = np.array(v, dtype=float)
                sem_sims.append(float(cos_sim(ctx_vec, a)))
                grounded_sims.append(float(cos_sim(a, ctx_vec)))
        # store minimal interaction
        interaction = LLMInteraction(
            request_id=request_id,
            doctor_id="symptom_kb",
            query=text,
            response=json.dumps(phrases),
            context_used=llm_log["prompt_used"],
            semantic_similarity=np.mean(sem_sims) if sem_sims else None,
            groundedness=np.mean(grounded_sims) if grounded_sims else None,
            prompt_variant=(action_id if action_id is not None else None),
            action_id=(action_id if action_id is not None else None),
            temp_used=chosen_temp,
            model_used=chosen_model,
            ctx_size_used=chosen_ctx_size,
            timestamp=datetime.utcnow()
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        print("Failed to log LLMInteraction for symptom extraction:", e)
        db.rollback()

    return {"text": text, "extracted": phrases, "request_id": request_id, "action_id": action_id, "threshold": similarity_threshold}

# ----------------------
# SymptomKB main class (uses RL-driven extraction above)
# ----------------------
class SymptomKB:
    def __init__(self, db: Session):
        self.db = db
        self.faiss = FaissManager()
        # ensure faiss aligns with DB on startup
        try:
            self.faiss.rebuild_from_db(self.db)
        except Exception as e:
            print("faiss rebuild warning:", e)

    def _get_all_clusters(self) -> Dict[int, SymptomCluster]:
        clusters = self.db.query(SymptomCluster).all()
        return {c.id: c for c in clusters}

    def create_cluster_with_metadata(self, vector: np.ndarray, examples: List[str]) -> SymptomCluster:
        # Ask LLM for metadata synchronously using shared ai_generate
        prompt = f"""
Given these patient symptom phrases: {examples}
Produce a JSON object with fields:
- canonical_name (short, lowercase, dash free)
- display_name (human friendly)
- metadata: {{ causes: [..], severity: "1-5", urgency: "low/medium/high", explanation: "patient-friendly text", recommended_action: "..." }}
Return JSON only.
"""
        try:
            meta_text = ai_generate(prompt=prompt, temperature=0.0, model="gemini-2.5-flash", client_override=genai_client)
            if meta_text.startswith("```"):
                meta_text = meta_text.strip("` \n")
            meta_obj = json.loads(meta_text)
        except Exception as e:
            print("metadata LLM parse failed:", e)
            meta_obj = {
                "canonical_name": examples[0][:40].lower().replace(" ", "_"),
                "display_name": examples[0][:60],
                "metadata": {"causes": [], "severity": "3", "urgency": "medium", "explanation": "Auto-generated", "recommended_action": "Contact clinic"}
            }

        cluster = SymptomCluster(
            canonical_name=meta_obj.get("canonical_name") or meta_obj.get("display_name","cluster"),
            display_name=meta_obj.get("display_name") or meta_obj.get("canonical_name"),
            metadata=meta_obj.get("metadata", {}),
            centroid=vec_to_bytes(vector.astype("float32")),
            count=1,
            created_at=datetime.utcnow()
        )
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)
        # add to FAISS
        try:
            self.faiss.add(vector, cluster.id)
        except Exception as e:
            print("faiss add failed:", e)
            # attempt rebuild fallback
            self.faiss.rebuild_from_db(self.db)
        return cluster

    def update_cluster_centroid(self, cluster: SymptomCluster, new_vector: np.ndarray):
        if cluster.centroid:
            old = bytes_to_vec(cluster.centroid)
            n = cluster.count or 1
            updated = (old * n + new_vector) / (n + 1)
        else:
            updated = new_vector
        cluster.centroid = vec_to_bytes(updated.astype("float32"))
        cluster.count = (cluster.count or 0) + 1
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)

        # sync to FAISS (safe: rebuild from DB to avoid duplicates)
        try:
            self.faiss.rebuild_from_db(self.db)
        except Exception as e:
            print("faiss rebuild after update failed:", e)

    def store_example(self, cluster: SymptomCluster, text: str, vector: np.ndarray):
        ex = SymptomExample(cluster_id=cluster.id, text=text, vector=vec_to_bytes(vector.astype("float32")))
        self.db.add(ex)
        self.db.commit()
        self.db.refresh(ex)
        return ex

    # -------------------------
    # public: process a raw text
    # -------------------------
    async def process_text(self, text: str) -> Dict:
        """
        1) call RL-driven LLM extractor
        2) embed phrases
        3) match to clusters (FAISS)
        4) update or create clusters
        5) return structured result
        """
        # --- extraction (RL chooses template/model/temp) ---
        extract_res = await extract_symptoms_with_generative_llm(text, self.db, context_vector=None)
        phrases = extract_res.get("extracted", [])
        # fallback
        if not phrases:
            phrases = [text.strip()]

        vectors = embed_texts_sync(phrases)
        results = []

        for phrase, vec in zip(phrases, vectors):
            cluster, score = self.find_best_cluster(vec)
            if cluster and score >= SIMILARITY_THRESHOLD_DEFAULT:
                self.update_cluster_centroid(cluster, vec)
                example = self.store_example(cluster, phrase, vec)
                results.append({
                    "phrase": phrase,
                    "cluster_id": cluster.id,
                    "canonical": cluster.canonical_name,
                    "display": cluster.display_name,
                    "score": float(score),
                    "created": False,
                    "metadata": cluster.metadata
                })
            else:
                new_cluster = self.create_cluster_with_metadata(vec, [phrase])
                example = self.store_example(new_cluster, phrase, vec)
                results.append({
                    "phrase": phrase,
                    "cluster_id": new_cluster.id,
                    "canonical": new_cluster.canonical_name,
                    "display": new_cluster.display_name,
                    "score": None,
                    "created": True,
                    "metadata": new_cluster.metadata
                })
        return {"text": text, "extracted": results}

    def find_best_cluster(self, vector: np.ndarray) -> Tuple[Optional[SymptomCluster], float]:
        dlist, mapped = self.faiss.search(vector, k=1)
        if not dlist:
            return None, 0.0
        score = dlist[0]
        cluster_id = mapped[0]
        if cluster_id is None:
            return None, float(score)
        cluster = self.db.query(SymptomCluster).filter(SymptomCluster.id == cluster_id).first()
        return cluster, float(score)

# helper to instantiate
def get_symptom_kb(db: Session) -> SymptomKB:
    return SymptomKB(db)
