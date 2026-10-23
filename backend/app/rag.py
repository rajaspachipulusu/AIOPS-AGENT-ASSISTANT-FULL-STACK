"""
RAG (Retrieval-Augmented Generation) module.

 1. Ingest markdown documents from docs_corpus/, chunk them.
 2. Embed chunks using Ollama's nomic-embed-text model.
 3. Store embeddings in a local ChromaDB collection (persisted to disk).
 4. At query time: embed the question, retrieve top-k chunks, and ask the
    LLM to answer using only that retrieved context.
"""
import glob
import os

import chromadb
import requests

from app.config import get_settings

_settings = get_settings()
OLLAMA_URL = f"{_settings.ollama_base_url}/api/embeddings"
GENERATE_URL = f"{_settings.ollama_base_url}/api/generate"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen3:8b"

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_store")
COLLECTION_NAME = "enterprise_docs"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs_corpus")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 4


def _chunk_text(text_: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text_):
        end = start + size
        chunks.append(text_[start:end])
        start += size - overlap
    return chunks


def _embed(text_: str) -> list[float]:
    response = requests.post(
        OLLAMA_URL,
        json={"model": EMBED_MODEL, "prompt": text_},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(COLLECTION_NAME)


def ingest_docs() -> int:
    """Reads all markdown files in docs_corpus/, chunks + embeds them, and
    (re)populates the Chroma collection. Returns the number of chunks stored."""
    collection = _get_collection()

    # Clear existing data for a clean re-ingest.
    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids, embeddings, documents, metadatas = [], [], [], []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.md"))):
        filename = os.path.basename(path)
        with open(path, "r") as f:
            content = f.read()
        for i, chunk in enumerate(_chunk_text(content)):
            ids.append(f"{filename}::{i}")
            embeddings.append(_embed(chunk))
            documents.append(chunk)
            metadatas.append({"source": filename, "chunk_index": i})

    if ids:
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return len(ids)


def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    collection = _get_collection()
    query_embedding = _embed(question)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": doc, "source": meta["source"], "distance": dist})
    return hits


def _call_ollama_generate(prompt: str) -> str:
    response = requests.post(
        GENERATE_URL,
        json={"model": CHAT_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]


def answer_from_docs(question: str) -> dict:
    hits = retrieve(question)
    context = "\n\n---\n\n".join(
        f"[Source: {h['source']}]\n{h['text']}" for h in hits
    )
    prompt = f"""Answer the user's question using ONLY the context below. If the
context does not contain the answer, say you don't have enough information.
Cite the source file name(s) you used at the end of your answer.

Context:
{context}

Question: {question}

Answer:"""
    answer = _call_ollama_generate(prompt).strip()
    return {
        "question": question,
        "answer": answer,
        "sources": [{"source": h["source"], "distance": h["distance"]} for h in hits],
    }
