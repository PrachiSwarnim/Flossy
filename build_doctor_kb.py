# build_doctor_kb.py
import os
import time
import json
import math
import faiss
import numpy as np
from PyPDF2 import PdfReader
from google.genai import Client
from typing import List

# ----------------------------
# CONFIG
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(BASE_DIR, "books")

TEXT_OUTPUT = os.path.join(BASE_DIR, "dental_book_cleaned.txt")
EMB_PATH = os.path.join(BASE_DIR, "dental_embeddings.faiss")
META_PATH = os.path.join(BASE_DIR, "dental_meta.json")

# Embedding API limits
MAX_BATCH = 100       # Gemini embedding API limit per request
RETRY_MAX = 5
INITIAL_BACKOFF = 1.0  # seconds

# Initialize client
client = Client(api_key=os.getenv("GOOGLE_API_KEY"))
if client is None:
    raise RuntimeError("Missing GOOGLE_API_KEY environment variable")

# ----------------------------
# 1. EXTRACT TEXT FROM PDF
# ----------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    print(f"📘 Reading: {os.path.basename(pdf_path)}")
    for idx, page in enumerate(reader.pages):
        content = page.extract_text()
        if content:
            text += content + "\n"
        print(f"   Extracted page {idx+1}/{len(reader.pages)}", end="\r")
    print("")  # newline after progress
    return text

# ----------------------------
# 2. MERGE ALL PDFs → CLEAN TEXT
# ----------------------------
def convert_pdfs_to_text() -> str:
    print("\n📚 Converting PDFs to text...\n")
    if not os.path.exists(BOOKS_DIR):
        raise RuntimeError(f"'books' folder not found at {BOOKS_DIR}")

    all_text = ""
    pdf_files = [f for f in os.listdir(BOOKS_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise RuntimeError("No PDF files found inside /books folder.")

    for pdf in pdf_files:
        path = os.path.join(BOOKS_DIR, pdf)
        all_text += extract_text_from_pdf(path)
        all_text += "\n\n"

    cleaned_text = " ".join(all_text.split())

    with open(TEXT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    print(f"\n✔ Text extracted & saved to: {TEXT_OUTPUT}\n")
    return cleaned_text

# ----------------------------
# 3. CHUNK TEXT
# ----------------------------
def chunk_text(text: str, chunk_size: int = 700) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# ----------------------------
# 4. GENERATE EMBEDDINGS (batched + retry)
# ----------------------------
def embed_chunks_batched(chunks: List[str]) -> np.ndarray:
    print("\n✨ Generating embeddings (batched)...\n")
    embeddings_all = []

    total_chunks = len(chunks)
    batches = math.ceil(total_chunks / MAX_BATCH)

    for b in range(batches):
        start = b * MAX_BATCH
        end = min(start + MAX_BATCH, total_chunks)
        batch = chunks[start:end]
        attempt = 0
        backoff = INITIAL_BACKOFF

        while True:
            try:
                print(f"  Embedding batch {b+1}/{batches} (chunks {start}-{end-1})...", end=" ")
                resp = client.models.embed_content(
                    model="models/text-embedding-004",
                    contents=batch
                )

                # FIX: extract .values from ContentEmbedding
                for emb in resp.embeddings:
                    embeddings_all.append(emb.values)

                print("done")
                break

            except Exception as e:
                attempt += 1
                print(f"\n   ⚠ batch failed (attempt {attempt}): {e}")
                if attempt >= RETRY_MAX:
                    raise RuntimeError(f"Embedding failed after {RETRY_MAX} retries: {e}")
                print(f"   Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= 2.0

    # FIX: convert to numpy array of float32
    emb_array = np.array(embeddings_all, dtype=np.float32)

    print(f"\n✔ Generated embeddings shape: {emb_array.shape}")
    return emb_array

# ----------------------------
# 5. BUILD FAISS INDEX
# ----------------------------
def build_faiss_index(chunks: List[str], embeddings: np.ndarray):
    print("\n🧠 Building FAISS index...\n")

    if embeddings.ndim != 2:
        raise ValueError("Embeddings must be 2-D (n_samples, dim)")

    n, dim = embeddings.shape
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, EMB_PATH)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks}, f)

    print(f"✔ Saved FAISS index to: {EMB_PATH}")
    print(f"✔ Saved meta to:        {META_PATH}")

# ----------------------------
# MAIN PIPELINE
# ----------------------------
if __name__ == "__main__":
    print("\n🚀 Starting Full Doctor KB Build Pipeline\n")

    # 1) PDFs -> text
    full_text = convert_pdfs_to_text()

    # 2) Text -> chunks
    chunks = chunk_text(full_text)
    print(f"✔ Total chunks: {len(chunks)}")

    # 3) Chunks -> embeddings (batched)
    embeddings = embed_chunks_batched(chunks)

    # 4) Build FAISS index
    build_faiss_index(chunks, embeddings)

    print("\n=============================================")
    print("🎉 DONE! Doctor Knowledge Base Fully Updated!")
    print("=============================================\n")
