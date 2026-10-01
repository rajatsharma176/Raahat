"""
RAG Embeddings module — wraps sentence-transformers for document encoding.
"""
from __future__ import annotations

import logging
import numpy as np
from typing import List

logger = logging.getLogger(__name__)

_model = None


def get_embedding_model():
    """Lazy-load the sentence-transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from app.config.settings import settings
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """Encode a list of texts to dense vectors."""
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def embed_query(query: str) -> np.ndarray:
    """Encode a single query string."""
    return embed_texts([query])[0]
