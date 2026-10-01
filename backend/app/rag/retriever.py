"""
RAG Retriever — semantic search over the knowledge base.
Every agent uses this to ground decisions in policy documents.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.config.settings import settings
from app.rag.embeddings import embed_query

logger = logging.getLogger(__name__)


class RetrievalResult:
    def __init__(self, chunk: str, source: str, domain: str, score: float):
        self.chunk = chunk
        self.source = source
        self.domain = domain
        self.score = score

    def to_dict(self) -> dict:
        return {
            "chunk": self.chunk,
            "source": self.source,
            "domain": self.domain,
            "score": round(float(self.score), 4),
        }

    def __repr__(self) -> str:
        return f"RetrievalResult(source={self.source}, score={self.score:.3f})"


class RAGRetriever:
    """
    Semantic retrieval over the FAISS knowledge base index.
    Agents call retrieve() to ground their decisions in policy text.
    """

    def __init__(self) -> None:
        self._index = None
        self._chunks: List[str] = []
        self._metadata: List[Dict] = []
        self._loaded = False

    def _try_load(self) -> bool:
        """Lazy-load the FAISS index from disk."""
        if self._loaded:
            return True

        index_path = Path(settings.faiss_index_path)
        index_file = index_path / "index.faiss"
        chunks_file = index_path / "chunks.json"

        if not index_file.exists() or not chunks_file.exists():
            logger.warning(
                "RAG index not found at %s. Run scripts/ingest_knowledge.py first.",
                index_path,
            )
            return False

        try:
            import faiss
            self._index = faiss.read_index(str(index_file))
            with open(chunks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._chunks = data["chunks"]
            self._metadata = data["metadata"]
            self._loaded = True
            logger.info("RAG index loaded: %d vectors", self._index.ntotal)
            return True
        except Exception as e:
            logger.error("Failed to load RAG index: %s", e)
            return False

    def retrieve(self, query: str, top_k: int = None) -> List[RetrievalResult]:
        """
        Retrieve top-k relevant chunks for a query.

        Args:
            query: Natural language query
            top_k: Number of results (defaults to settings.rag_top_k)

        Returns:
            List of RetrievalResult ordered by relevance score descending
        """
        if top_k is None:
            top_k = settings.rag_top_k

        if not self._try_load():
            logger.warning("RAG retrieval skipped — index not available.")
            return []

        query_vec = embed_query(query)
        # Normalize for cosine similarity
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm
        query_vec = query_vec.astype(np.float32).reshape(1, -1)

        k = min(top_k, len(self._chunks))
        scores, indices = self._index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self._metadata[idx]
            results.append(
                RetrievalResult(
                    chunk=self._chunks[idx],
                    source=meta.get("source", "unknown"),
                    domain=meta.get("domain", "unknown"),
                    score=float(score),
                )
            )
        return results

    def retrieve_with_metadata(self, query: str, domain_filter: Optional[str] = None) -> List[dict]:
        """
        Retrieve results and optionally filter by domain.
        Returns list of dicts for easy JSON serialization.
        """
        results = self.retrieve(query)
        if domain_filter:
            results = [r for r in results if r.domain == domain_filter]
        return [r.to_dict() for r in results]

    def format_context(self, results: List[RetrievalResult]) -> str:
        """Format results as a context string for LLM prompts."""
        if not results:
            return "No relevant policy documents found."
        parts = []
        for r in results:
            parts.append(
                f"[Source: {r.source} | Score: {r.score:.3f}]\n{r.chunk}"
            )
        return "\n\n---\n\n".join(parts)

    def index_documents(self) -> bool:
        """Rebuild the FAISS index from the knowledge base."""
        from app.rag.ingestion import ingest_knowledge_base, save_index
        try:
            chunks, metadata, embeddings = ingest_knowledge_base()
            if not chunks:
                logger.warning("No documents found to index.")
                return False
            save_index(chunks, metadata, embeddings)
            self._loaded = False  # Force reload on next query
            return True
        except Exception as e:
            logger.error("Failed to index documents: %s", e)
            return False


# Global singleton
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever
