"""
Vector store for semantic retrieval using FAISS.
Provides fast approximate nearest neighbor search.
"""

import logging
import numpy as np
from typing import List, Optional, Tuple
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class VectorStore:
    """
    Vector store for semantic similarity search.
    Uses FAISS IndexFlatIP (inner product) with normalized vectors.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._index = None
        self._catalog = []  # Store original catalog items
        self._id_to_idx = {}  # Mapping from assessment ID to index

    def build_index(self, catalog: List[dict], embeddings: np.ndarray):
        """
        Build FAISS index from catalog embeddings.

        Args:
            catalog: List of assessment dictionaries
            embeddings: Numpy array of embeddings, shape (n, dimension)
        """
        if not FAISS_AVAILABLE:
            self._build_fallback_index(catalog, embeddings)
            return

        n = len(catalog)
        logger.info(f"Building FAISS index for {n} items, dimension {self.dimension}")

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized = embeddings / norms

        # Use Inner Product index with normalized vectors = cosine similarity
        self._index = faiss.IndexFlatIP(self.dimension)
        self._index.add(normalized.astype('float32'))

        # Store catalog for retrieval
        self._catalog = catalog

        logger.info(f"FAISS index built with {self._index.ntotal} vectors")

    def _build_fallback_index(self, catalog: List[dict], embeddings: np.ndarray):
        """Fallback numpy-based search when FAISS unavailable."""
        self._catalog = catalog
        self._embeddings = embeddings
        logger.info("Using numpy fallback for similarity search")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10
    ) -> List[Tuple[dict, float]]:
        """
        Search for top-k most similar assessments.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return

        Returns:
            List of (assessment, score) tuples, sorted by score descending
        """
        if self._index is None:
            return self._fallback_search(query_embedding, k)

        # Normalize query
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_normalized = query_embedding / norm
        else:
            query_normalized = query_embedding

        # Search
        query_vec = query_normalized.reshape(1, -1).astype('float32')
        distances, indices = self._index.search(query_vec, min(k, self._index.ntotal))

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self._catalog):
                # Convert distance to similarity score (0-1)
                score = float((dist + 1) / 2)  # Map [-1, 1] to [0, 1]
                results.append((self._catalog[idx], score))

        return results

    def _fallback_search(
        self,
        query_embedding: np.ndarray,
        k: int
    ) -> List[Tuple[dict, float]]:
        """Fallback numpy-based search."""
        if not hasattr(self, "_embeddings"):
            return []

        # Normalize
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Compute similarities
        similarities = np.dot(self._embeddings, query_norm)

        # Get top-k indices
        top_k_idx = np.argsort(similarities)[::-1][:k]

        results = []
        for idx in top_k_idx:
            if idx < len(self._catalog):
                score = float((similarities[idx] + 1) / 2)
                results.append((self._catalog[idx], score))

        return results

    def save(self, path: str):
        """Save index and catalog to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if FAISS_AVAILABLE and self._index is not None:
            faiss.write_index(self._index, str(path.with_suffix(".index")))

        with open(path.with_suffix(".catalog"), "wb") as f:
            pickle.dump(self._catalog, f)

        logger.info(f"Saved index and catalog to {path}")

    def load(self, path: str) -> bool:
        """Load index and catalog from disk."""
        path = Path(path)

        if not path.with_suffix(".catalog").exists():
            return False

        try:
            with open(path.with_suffix(".catalog"), "rb") as f:
                self._catalog = pickle.load(f)

            if FAISS_AVAILABLE:
                index_path = path.with_suffix(".index")
                if index_path.exists():
                    self._index = faiss.read_index(str(index_path))
                    logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors")
                    return True

            # Fallback mode
            logger.info("Loaded catalog in fallback mode")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    @property
    def is_built(self) -> bool:
        """Check if index is built."""
        return self._index is not None or hasattr(self, "_embeddings")

    def __len__(self) -> int:
        return len(self._catalog)


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def initialize_vector_store(catalog: List[dict], force_rebuild: bool = False):
    """
    Initialize the global vector store with catalog embeddings.

    Args:
        catalog: List of assessment dictionaries
        force_rebuild: Force rebuild even if index file exists
    """
    from .embeddings import compute_catalog_embeddings

    store = get_vector_store()

    # Check if already built
    if store.is_built and not force_rebuild:
        logger.info("Vector store already initialized")
        return

    # Compute embeddings
    logger.info("Computing catalog embeddings...")
    embeddings = compute_catalog_embeddings(catalog)

    # Build index
    store.build_index(catalog, embeddings)
    logger.info(f"Vector store initialized with {len(catalog)} assessments")