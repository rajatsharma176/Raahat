"""
RAG Document Ingestion — loads knowledge base documents, chunks them,
embeds them, and builds the FAISS index.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from app.config.settings import settings
from app.rag.embeddings import embed_texts

logger = logging.getLogger(__name__)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def ingest_knowledge_base(knowledge_path: str = None) -> Tuple[List[str], List[Dict], np.ndarray]:
    """
    Load all .txt files from the knowledge base directory,
    chunk them, and return (chunks, metadata, embeddings).

    Returns:
        chunks: list of text chunks
        metadata: list of dicts with {source, domain}
        embeddings: numpy array of shape (N, dim)
    """
    if knowledge_path is None:
        knowledge_path = settings.knowledge_base_path

    kb_path = Path(knowledge_path)
    if not kb_path.exists():
        logger.warning("Knowledge base path does not exist: %s", kb_path)
        return [], [], np.array([])

    all_chunks: List[str] = []
    all_meta: List[Dict] = []

    for txt_file in sorted(kb_path.rglob("*.txt")):
        domain = txt_file.parent.name
        source = str(txt_file.relative_to(kb_path))
        try:
            text = txt_file.read_text(encoding="utf-8")
            chunks = _chunk_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_meta.append({"source": source, "domain": domain, "file": txt_file.name})
            logger.info("Ingested %s: %d chunks", source, len(chunks))
        except Exception as e:
            logger.error("Failed to ingest %s: %s", txt_file, e)

    if not all_chunks:
        return [], [], np.array([])

    logger.info("Embedding %d chunks...", len(all_chunks))
    embeddings = embed_texts(all_chunks)
    return all_chunks, all_meta, embeddings


def save_index(chunks: List[str], metadata: List[Dict], embeddings: np.ndarray, index_path: str = None) -> None:
    """Save FAISS index and chunk data to disk."""
    import faiss

    if index_path is None:
        index_path = settings.faiss_index_path

    Path(index_path).mkdir(parents=True, exist_ok=True)

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized vecs)
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = embeddings / norms
    index.add(normalized.astype(np.float32))

    faiss.write_index(index, str(Path(index_path) / "index.faiss"))

    with open(Path(index_path) / "chunks.json", "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks, "metadata": metadata}, f, indent=2)

    logger.info("FAISS index saved: %d vectors at %s", index.ntotal, index_path)
