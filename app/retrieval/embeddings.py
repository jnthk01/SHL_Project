"""
Embedding generation for semantic retrieval.
Uses sentence-transformers with all-MiniLM-L6-v2 model.
"""

import logging
from typing import List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Model configuration
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Output dimension for all-MiniLM-L6-v2


class EmbeddingModel:
    """
    Wrapper for sentence-transformers embedding model.
    Lazy-loads model on first use for faster startup.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model = None
        self._device = "cpu"  # Can be "cuda" if GPU available

    @property
    def model(self):
        """Lazy load model on first access."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Embedding model loaded successfully")
            except Exception as e:
                # Optional feature - silently skip if not available
                self._model = None
        return self._model

    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single string or list of strings
            normalize: Whether to normalize embeddings (L2)
            show_progress: Show encoding progress

        Returns:
            Numpy array of embeddings, shape (n, embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings

    def encode_assessment(self, assessment: dict) -> np.ndarray:
        """
        Generate embedding for an assessment.
        Combines name, description, skills into single text.
        """
        # Build combined text for rich embedding
        parts = [
            assessment.get("name", ""),
            assessment.get("description", ""),
            " ".join(assessment.get("skills", [])),
        ]
        text = " | ".join([p for p in parts if p])

        return self.encode(text)

    def encode_batch(self, assessments: List[dict]) -> np.ndarray:
        """
        Generate embeddings for multiple assessments.

        Args:
            assessments: List of assessment dictionaries

        Returns:
            Numpy array of embeddings, shape (n, embedding_dim)
        """
        texts = []
        for a in assessments:
            parts = [
                a.get("name", ""),
                a.get("description", ""),
                " ".join(a.get("skills", [])),
            ]
            texts.append(" | ".join([p for p in parts if p]))

        return self.encode(texts, normalize=True)


class EmbeddingCache:
    """Simple cache for pre-computed embeddings."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[np.ndarray]:
        """Get cached embedding."""
        return self._cache.get(key)

    def set(self, key: str, embedding: np.ndarray):
        """Store embedding in cache."""
        self._cache[key] = embedding

    def clear(self):
        """Clear all cached embeddings."""
        self._cache.clear()


# Global embedding model instance (lazy loaded)
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """Get global embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


def compute_query_embedding(query: str) -> np.ndarray:
    """Compute embedding for a search query."""
    model = get_embedding_model()
    return model.encode(query)


def compute_catalog_embeddings(catalog: List[dict]) -> np.ndarray:
    """Compute embeddings for entire catalog."""
    model = get_embedding_model()
    return model.encode_batch(catalog)