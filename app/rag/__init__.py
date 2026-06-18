"""RAG and policy knowledge module."""

from app.rag.constants import (
    ALL_POLICY_DOMAINS,
    DEFAULT_TOP_K,
    HIGH_RISK_RETRIEVAL_FAILURE_INTENTS,
    INTENT_TO_POLICY_DOMAIN,
    POLICIES_QDRANT_COLLECTION,
)
from app.rag.in_memory_retrieval import (
    InMemoryPolicyRetrievalService,
    default_demo_policy_chunks,
)
from app.rag.qdrant_retrieval import QdrantPolicyRetrievalService
from app.rag.qdrant_store import (
    InMemoryPolicyVectorSearchStore,
    InMemoryPolicyVectorStore,
    PolicyVectorSearchStore,
    QdrantPolicyVectorSearchStore,
    QdrantStoreError,
    deterministic_point_id,
    get_policy_vector_search_store,
    get_policy_vector_store,
    validate_qdrant_url,
)
from app.rag.retrieval import (
    PolicyRetrievalService,
    RaisingPolicyRetrievalService,
    RetrievalServiceError,
    UnavailablePolicyRetrievalService,
    get_policy_retrieval_service,
)
from app.rag.chunk_schemas import DocumentChunkingResult, PolicyDocumentChunk
from app.rag.chunking import DocumentChunker, derive_chunk_visibility
from app.rag.embedding_schemas import EmbeddedPolicyChunk
from app.rag.embeddings import DocumentEmbeddingService
from app.rag.extraction import DocumentTextExtractor, MAX_EXTRACTION_BYTES, SUPPORTED_EXTENSIONS
from app.rag.extraction_schemas import DocumentExtractionResult, SupportedFileType
from app.rag.schemas import RetrievedPolicyChunk, RetrievalRequest, RetrievalResult

__all__ = [
    "ALL_POLICY_DOMAINS",
    "DEFAULT_TOP_K",
    "DocumentChunker",
    "DocumentChunkingResult",
    "DocumentEmbeddingService",
    "DocumentExtractionResult",
    "DocumentTextExtractor",
    "EmbeddedPolicyChunk",
    "InMemoryPolicyVectorSearchStore",
    "InMemoryPolicyVectorStore",
    "PolicyVectorSearchStore",
    "QdrantPolicyRetrievalService",
    "QdrantPolicyVectorSearchStore",
    "derive_chunk_visibility",
    "MAX_EXTRACTION_BYTES",
    "HIGH_RISK_RETRIEVAL_FAILURE_INTENTS",
    "INTENT_TO_POLICY_DOMAIN",
    "InMemoryPolicyRetrievalService",
    "POLICIES_QDRANT_COLLECTION",
    "PolicyDocumentChunk",
    "PolicyRetrievalService",
    "QdrantStoreError",
    "RaisingPolicyRetrievalService",
    "RetrievalRequest",
    "RetrievalResult",
    "RetrievalServiceError",
    "RetrievedPolicyChunk",
    "SUPPORTED_EXTENSIONS",
    "SupportedFileType",
    "UnavailablePolicyRetrievalService",
    "default_demo_policy_chunks",
    "deterministic_point_id",
    "get_policy_retrieval_service",
    "get_policy_vector_search_store",
    "get_policy_vector_store",
    "validate_qdrant_url",
]
