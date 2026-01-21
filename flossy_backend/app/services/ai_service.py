import os
import json
import tempfile

from typing import Optional, Tuple, List
from app.core.config import GOOGLE_API_KEY

# Globals for Lazy Loading
_faiss_index = None
_faiss_chunks = None
_bandit = None
ACTIONS = None
PROMPT_VARIANTS = None
MODELS = None
_genai_client = None

# GCS Configuration - Your bucket: gs://doctor_kb
GCS_BUCKET_NAME = os.getenv("GCS_KB_BUCKET", "doctor_kb")
GCS_FAISS_PATH = "dental_embeddings.faiss"
GCS_META_PATH = "dental_meta.json"

# Local cache paths
LOCAL_FAISS_PATH = "/tmp/dental_embeddings.faiss"
LOCAL_META_PATH = "/tmp/dental_meta.json"


def download_from_gcs(bucket_name: str, source_blob: str, dest_path: str) -> bool:
    """Download a file from Google Cloud Storage."""
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_blob)
        
        if not blob.exists():
            print(f"⚠️ GCS blob not found: gs://{bucket_name}/{source_blob}")
            return False
        
        blob.download_to_filename(dest_path)
        print(f"✅ Downloaded gs://{bucket_name}/{source_blob} → {dest_path}")
        return True
    except ImportError:
        print("⚠️ google-cloud-storage not installed. Using local files only.")
        return False
    except Exception as e:
        print(f"❌ GCS download failed: {e}")
        return False


def load_faiss_index():
    global _faiss_index, _faiss_chunks
    if _faiss_index is None:
        try:
            import faiss
        except ImportError:
            raise RuntimeError("FAISS library not installed. Please install faiss-cpu.")

        # Check for local files first (for local development)
        local_faiss = "dental_embeddings.faiss"
        local_meta = "dental_meta.json"
        
        faiss_path = local_faiss
        meta_path = local_meta
        
        # If local files don't exist, try to download from GCS
        if not os.path.exists(local_faiss):
            print(f"📥 Local FAISS not found, trying GCS bucket: {GCS_BUCKET_NAME}")
            if download_from_gcs(GCS_BUCKET_NAME, GCS_FAISS_PATH, LOCAL_FAISS_PATH):
                faiss_path = LOCAL_FAISS_PATH
            else:
                print(f"⚠️ FAISS file missing: {local_faiss} and GCS download failed. Continuing without KB.")
                _faiss_index = None # Mark as failed but don't crash
        
        if not os.path.exists(local_meta) and not os.path.exists(LOCAL_META_PATH):
            print(f"📥 Local meta not found, trying GCS bucket: {GCS_BUCKET_NAME}")
            if download_from_gcs(GCS_BUCKET_NAME, GCS_META_PATH, LOCAL_META_PATH):
                meta_path = LOCAL_META_PATH
            else:
                print(f"⚠️ Meta file missing: {local_meta} and GCS download failed. Continuing without KB.")
        elif os.path.exists(LOCAL_META_PATH):
            meta_path = LOCAL_META_PATH

        if faiss_path and os.path.exists(faiss_path) and os.path.exists(meta_path):
            try:
                _faiss_index = faiss.read_index(faiss_path)
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                _faiss_chunks = meta.get("chunks", [])
                print(f"✅ FAISS index loaded ({len(_faiss_chunks)} chunks).")
            except Exception as e:
                print(f"❌ Error loading FAISS: {e}")
                _faiss_index = None
                _faiss_chunks = []
        else:
            _faiss_index = None
            _faiss_chunks = []
            print("⚠️ KB Files missing or unreachable. AI will use general knowledge.")

    return _faiss_index, _faiss_chunks

def get_genai_client():
    # Use the one initialized in llm_client if available
    from app.services.llm_client import genai_client as _static_genai_client
    return _static_genai_client

def get_bandit_and_meta():
    global _bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    if _bandit is None:
        try:
            # Assumes rl_core.py is in the python path (root of backend)
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
