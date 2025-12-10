# main_ml.py
import os
import json
import uuid
import jwt
import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# -------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")

# -------------------------------------------------------------
# App + CORS setup
# -------------------------------------------------------------
app = FastAPI(title="FlossyAI ML Service", description="Handles FAISS, RL, GenAI inference")

FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")
allow_origins = ["*"] if FRONTEND_ORIGINS == "*" else [o.strip() for o in FRONTEND_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Lazy globals (same as backend)
# -------------------------------------------------------------
_genai_client = None
_bandit = None
ACTIONS = None
PROMPT_VARIANTS = None
MODELS = None

_faiss_index = None
_faiss_chunks = None

# -------------------------------------------------------------
# Lazy loaders from original backend (unchanged)
# -------------------------------------------------------------
def get_genai_client():
    global _genai_client
    if _genai_client is None:
        try:
            from google.genai import Client
            _genai_client = Client(api_key=GEMINI_API_KEY)
            print("GenAI client initialized (lazy).")
        except Exception as e:
            print("GenAI client failed to initialize:", e)
            _genai_client = None
    return _genai_client


def get_bandit_and_meta():
    global _bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    if _bandit is None:
        try:
            from rl_core import bandit as bandit_obj, ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M, LinUCB as LinUCBClass
            ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            _bandit = bandit_obj if bandit_obj is not None else LinUCBClass(
                bandit_name="doctor_global_v1",
                actions=list(range(len(_A))),
                d=768,
                alpha=1.0
            )
            print("RL bandit loaded lazily.")
        except Exception as e:
            print("Failed to lazy-load RL bandit:", e)
            try:
                from rl_core import ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M
                ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            except Exception:
                ACTIONS, PROMPT_VARIANTS, MODELS = [], [], []
            _bandit = None
    return _bandit, ACTIONS, PROMPT_VARIANTS, MODELS


def load_faiss_index():
    global _faiss_index, _faiss_chunks
    if _faiss_index is None:
        try:
            import faiss
        except Exception as e:
            raise RuntimeError("faiss import failed: " + str(e))

        if not os.path.exists("dental_embeddings.faiss"):
            raise FileNotFoundError("FAISS file missing: dental_embeddings.faiss")

        if not os.path.exists("dental_meta.json"):
            raise FileNotFoundError("Meta file missing: dental_meta.json")

        _faiss_index = faiss.read_index("dental_embeddings.faiss")
        with open("dental_meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        _faiss_chunks = meta.get("chunks", [])
        print("FAISS index loaded (lazy).")
    return _faiss_index, _faiss_chunks

# -------------------------------------------------------------
# Lightweight health check
# -------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ml-service-ok", "time": datetime.now(timezone.utc).isoformat()}

# -------------------------------------------------------------
# The EXACT doctor_ai logic copied from backend (NO CHANGES)
# -------------------------------------------------------------
from utils import ai_generate, cos_sim, embed_with_client
from models import LLMInteraction   # Only if you still want logging
from database import SessionLocal   # If DB writes needed


@app.post("/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse({"answer": "No query provided."}, status_code=400)

    doctor_name = payload.get("doctor_name", "Doctor")

    # --- Load FAISS index ---
    try:
        index, chunks = load_faiss_index()
    except FileNotFoundError:
        return JSONResponse({"answer": "Knowledge base not available on the server."}, status_code=500)
    except Exception as e:
        return JSONResponse({"answer": f"Error loading KB: {e}"}, status_code=500)

    # --- GenAI lazy ---
    genai_client = get_genai_client()

    # --- RL bandit lazy ---
    bandit, ACTIONS, PROMPT_VARIANTS, MODELS = get_bandit_and_meta()

    # --- Embedding ---
    try:
        query_emb = np.array(embed_with_client(genai_client, query), dtype=float)
    except Exception:
        query_emb = np.zeros(768, dtype=float)

    x_context = query_emb
    if bandit:
        if x_context.shape[0] != bandit.d:
            if x_context.shape[0] > bandit.d:
                x_context = x_context[:bandit.d]
            else:
                pad = np.zeros(bandit.d - x_context.shape[0], dtype=float)
                x_context = np.concatenate([x_context, pad])

        chosen_action_id, scores = bandit.choose(x_context, eps=0.1)
        try:
            prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
            chosen_prompt_template = PROMPT_VARIANTS[prompt_idx]
            chosen_model = MODELS[model_idx]
        except Exception:
            chosen_prompt_template = "{query}"
            temp = 0.0
            ctx_size = 2
            chosen_model = None
    else:
        chosen_prompt_template = "{query}"
        temp = 0.0
        ctx_size = 2
        chosen_model = None
        chosen_action_id = -1

    qvec = np.array([query_emb], dtype="float32")
    ctx_size = max(1, min(ctx_size, len(chunks)))
    try:
        Dvals, I = index.search(qvec, ctx_size)
        context = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))
    except Exception:
        context = ""

    prompt = chosen_prompt_template.format(
        doctor=doctor_name,
        context=context,
        query=query
    )

    try:
        answer = ai_generate(prompt, temperature=temp, model=chosen_model, client_override=genai_client)
    except Exception as e:
        print("ai_generate failed:", e)
        answer = "FlossyAI couldn't generate an answer right now."

    try:
        answer_vec = np.array(embed_with_client(genai_client, answer), dtype=float)
    except Exception:
        answer_vec = np.zeros_like(query_emb)

    try:
        context_vec = np.array(embed_with_client(genai_client, context), dtype=float) if context else np.zeros_like(query_emb)
    except Exception:
        context_vec = np.zeros_like(query_emb)

    semantic_similarity = float(cos_sim(query_emb, answer_vec))
    groundedness = float(cos_sim(answer_vec, context_vec))

    request_id = str(uuid.uuid4())

    # Optional: persist logs (only if DB configured)
    try:
        db = SessionLocal()
        interaction = LLMInteraction(
            request_id=request_id,
            doctor_id=doctor_name,
            query=query,
            response=answer,
            context_used=context,
            semantic_similarity=semantic_similarity,
            groundedness=groundedness,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(interaction)
        db.commit()
        db.close()
    except Exception as e:
        print("DB logging failed:", e)

    return {
        "answer": answer,
        "request_id": request_id,
        "semantic_similarity": semantic_similarity,
        "groundedness": groundedness
    }


@app.get("/")
def root():
    return {"service": "FlossyAI ML Service", "status": "running"}
