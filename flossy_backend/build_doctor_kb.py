# build_doctor_kb.py — FULL UPDATED VERSION WITH SEMANTIC CLUSTERING + LABELS
import os
import time
import json
import math
import re
import unicodedata
import faiss
import numpy as np
from typing import List
from PyPDF2 import PdfReader

# ML for clustering + labeling
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import defaultdict

# Google Embeddings
from google.genai import Client

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(BASE_DIR, "books")

RAW_TEXT_OUTPUT = os.path.join(BASE_DIR, "dental_book_raw.txt")
CLEAN_TEXT_OUTPUT = os.path.join(BASE_DIR, "dental_book_cleaned.txt")

EMB_PATH = os.path.join(BASE_DIR, "dental_embeddings.faiss")
META_PATH = os.path.join(BASE_DIR, "dental_meta.json")

MAX_BATCH = 100
RETRY_MAX = 5
INITIAL_BACKOFF = 1.0

client = Client(api_key=os.getenv("GOOGLE_API_KEY"))
if client is None:
    raise RuntimeError("Missing GOOGLE_API_KEY")


# ---------------------------------------------------------
# 1. EXTRACT PDF TEXT
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    print(f"📘 Reading: {os.path.basename(pdf_path)}")

    extracted = []
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
        except:
            text = None
        if text:
            extracted.append(text.strip())
        print(f"   Extracted page {idx+1}/{len(reader.pages)}", end="\r")

    print("")
    return "\n".join(extracted)


# ---------------------------------------------------------
# 2. CLEANING OCR / ACADEMIC PDF
# ---------------------------------------------------------
def clean_academic_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\ufeff", "").replace("∩╗┐", "")
    text = re.sub(r"ΓÇ\w+", " ", text)

    # Fix hyphens (but preserve newlines)
    text = re.sub(r"(\w+)-\s+(\w+)", r"\1\2", text)

    # Preserve paragraph breaks:
    text = text.replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse long gaps to double newline

    # Remove DOI and metadata
    text = re.sub(r"DOI[:\s].*?(?=Abstract|Keywords|1\.)", " ", text, flags=re.S | re.I)
    text = re.sub(r"Received:.*?Published:.*?(Review)?", " ", text, flags=re.S)

    # Remove emails, correspondence
    text = re.sub(r"Email:\s*\S+", " ", text)
    text = re.sub(r"Correspondence.*?:", " ", text)

    # Remove citations like [1], (2020)
    text = re.sub(r"\[\d+(–\d+)?(?:,\d+(–\d+)?)*\]", " ", text)
    text = re.sub(r"\(\d{4}\)", " ", text)

    # Remove figure/table refs
    text = re.sub(r"(Figure|Table)\s?\d+(\.\d+)?", " ", text, flags=re.I)

    # Remove junk numbers but keep line breaks
    text = re.sub(r"\b\d{3,}\b", " ", text)

    # Clean punctuation but DO NOT remove newlines
    text = re.sub(r"[ \t]+", " ", text)  # collapse spaces
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)

    # Final trimming
    text = text.strip()

    return text


# ---------------------------------------------------------
# 3. MERGE PDFs → CLEAN TEXT
# ---------------------------------------------------------
def convert_pdfs_to_text() -> str:
    print("\n📚 Converting PDFs → cleaned text...\n")

    if not os.path.exists(BOOKS_DIR):
        raise RuntimeError(f"No /books folder found at {BOOKS_DIR}")

    pdf_files = [f for f in os.listdir(BOOKS_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise RuntimeError("No PDF files found in /books")

    all_raw = []

    for pdf in pdf_files:
        raw = extract_text_from_pdf(os.path.join(BOOKS_DIR, pdf))
        all_raw.append(raw)

    raw_text = "\n".join(all_raw)

    with open(RAW_TEXT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(raw_text)

    cleaned = clean_academic_text(raw_text)

    with open(CLEAN_TEXT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✔ Raw text saved → {RAW_TEXT_OUTPUT}")
    print(f"✔ Cleaned text saved → {CLEAN_TEXT_OUTPUT}")

    return cleaned


# ---------------------------------------------------------
# 4. PARAGRAPH SPLITTING
# ---------------------------------------------------------
def split_into_paragraphs(text: str) -> List[str]:
    chunks = re.split(r"\n{1,}|\.  ", text)
    paragraphs = [c.strip() for c in chunks if c and isinstance(c, str) and len(c.strip()) > 120]
    return paragraphs


# ---------------------------------------------------------
# 5. EMBEDDINGS (Gemini batching)
# ---------------------------------------------------------
def embed_chunks_batched(chunks: List[str]) -> np.ndarray:
    print("\n✨ Embedding paragraphs...\n")

    all_vecs = []
    total = len(chunks)
    batches = math.ceil(total / MAX_BATCH)

    for b in range(batches):
        start = b * MAX_BATCH
        end = min(start + MAX_BATCH, total)
        batch = chunks[start:end]

        attempt = 0
        backoff = INITIAL_BACKOFF

        while True:
            try:
                resp = client.models.embed_content(
                    model="models/text-embedding-004",
                    contents=batch
                )
                for emb in resp.embeddings:
                    all_vecs.append(emb.values)
                print(f"  → embedded batch {b+1}/{batches} ✓")
                break

            except Exception as e:
                attempt += 1
                print(f"⚠ Error embedding batch {b+1}: {e}")
                if attempt >= RETRY_MAX:
                    raise RuntimeError("Too many embedding failures")
                time.sleep(backoff)
                backoff *= 2

    arr = np.array(all_vecs, dtype=np.float32)
    print(f"✔ Embeddings shape: {arr.shape}")
    return arr


# ---------------------------------------------------------
# 6. TF-IDF CLUSTER LABELING
# ---------------------------------------------------------
def label_clusters_with_tfidf(paragraphs: List[str], labels: List[int], top_k=3):
    clusters = defaultdict(list)
    for p, lb in zip(paragraphs, labels):
        clusters[lb].append(p)

    docs = []
    cluster_ids = []
    for cid, paras in clusters.items():
        docs.append(" ".join(paras))
        cluster_ids.append(cid)

    vec = TfidfVectorizer(stop_words="english", max_df=0.8)
    tfidf = vec.fit_transform(docs)
    vocab = vec.get_feature_names_out()

    out = {}
    for i, cid in enumerate(cluster_ids):
        vec_row = tfidf[i].toarray().ravel()
        idxs = vec_row.argsort()[::-1][:top_k]
        terms = [vocab[j] for j in idxs if vec_row[j] > 0]

        label = ", ".join(terms) if terms else f"topic_{cid}"
        example = clusters[cid][0]

        out[cid] = {
            "label": label,
            "example": example,
            "paras": clusters[cid]
        }
    return out


# ---------------------------------------------------------
# 7. SEMANTIC CLUSTERING
# ---------------------------------------------------------
def semantic_cluster_and_label(paragraphs, embeddings, k_requested=20):
    n = len(paragraphs)

    if n == 0:
        return [], [], {}

    if n == 1:
        return [paragraphs[0]], [0], {
            0: {"label": "single-paragraph", "example": paragraphs[0], "paras": [paragraphs[0]]}
        }

    k = min(k_requested, max(2, n // 2))
    print(f"🧩 Clustering {n} paragraphs → k={k}")

    km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(embeddings)

    # Group paragraphs
    groups = defaultdict(list)
    for p, lb in zip(paragraphs, labels):
        groups[lb].append(p)

    # Merge clusters into block text
    blocks = [" ".join(groups[cid]) for cid in sorted(groups.keys())]

    # Label
    labeled = label_clusters_with_tfidf(paragraphs, labels)

    # Remap metadata to match block order 0..k-1
    meta = {}
    for new_idx, cid in enumerate(sorted(groups.keys())):
        meta[new_idx] = labeled[cid]

    return blocks, labels, meta


# ---------------------------------------------------------
# 8. BUILD FAISS INDEX + META
# ---------------------------------------------------------
def build_faiss_index(chunks, embeddings, blocks_meta):
    n, dim = embeddings.shape
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, EMB_PATH)

    meta = {
        "chunks": chunks,
        "blocks": []
    }

    for idx, info in blocks_meta.items():
        meta["blocks"].append({
            "block_idx": idx,
            "label": info["label"],
            "example": info["example"][:300],
            "paras": info["paras"][:20]
        })

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✔ FAISS saved → {EMB_PATH}")
    print(f"✔ Metadata saved → {META_PATH}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n🚀 Building Doctor Semantic Knowledge Base\n")

    cleaned = convert_pdfs_to_text()

    paragraphs = split_into_paragraphs(cleaned)
    print(f"✔ Extracted {len(paragraphs)} semantic paragraphs")

    para_embeddings = embed_chunks_batched(paragraphs)

    blocks, labels, blocks_meta = semantic_cluster_and_label(paragraphs, para_embeddings)

    print("\n✔ Topic Labels:")
    for idx, info in blocks_meta.items():
        print(f"  [{idx}] {info['label']}")

    # Final blocks are now your RAG chunks
    chunks = blocks

    final_embeddings = embed_chunks_batched(chunks)

    build_faiss_index(chunks, final_embeddings, blocks_meta)

    print("\n🎉 DONE — RAG KB built with semantic topics, clustering, and FAISS index.\n")
