"""Retrieval package for semantic search."""

from .embeddings import (
    EmbeddingModel,
    EmbeddingCache,
    get_embedding_model,
    compute_query_embedding,
    compute_catalog_embeddings,
)

from .vector_store import (
    VectorStore,
    get_vector_store,
    initialize_vector_store,
)

from .reranker import (
    Reranker,
    RerankConfig,
    apply_filters,
    get_reranker,
)

__all__ = [
    "EmbeddingModel",
    "EmbeddingCache",
    "get_embedding_model",
    "compute_query_embedding",
    "compute_catalog_embeddings",
    "VectorStore",
    "get_vector_store",
    "initialize_vector_store",
    "Reranker",
    "RerankConfig",
    "apply_filters",
    "get_reranker",
]