"""Optional Vertex AI embedding provider adapter (T-042)."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.providers.base_embedding import EmbeddingProviderError
from app.providers.embedding_schemas import EmbeddingBatchResult, EmbeddingVectorResult

VERTEX_EMBEDDING_DIMENSION = 768


class VertexEmbeddingProvider:
    """Vertex AI embeddings via optional google-cloud-aiplatform SDK."""

    provider_name = "vertex_ai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.vertex_embedding_model
        self.dimension = VERTEX_EMBEDDING_DIMENSION

    def _validate_config(self) -> tuple[str, str]:
        project_id = self._settings.vertex_ai_project_id.strip()
        if not project_id:
            raise EmbeddingProviderError("VERTEX_AI_PROJECT_ID not configured")
        location = self._settings.vertex_ai_location.strip() or "us-central1"
        return project_id, location

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        if not texts:
            return EmbeddingBatchResult(
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
                error="no texts provided",
            )
        try:
            project_id, location = self._validate_config()
            vectors = await asyncio.to_thread(
                self._embed_sync,
                project_id,
                location,
                texts,
            )
        except EmbeddingProviderError as exc:
            return EmbeddingBatchResult(
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
                error=exc.message,
            )
        except Exception as exc:  # noqa: BLE001 — controlled provider boundary
            return EmbeddingBatchResult(
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
                error=f"vertex embedding failed: {exc}",
            )
        return EmbeddingBatchResult(
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
            vectors=vectors,
        )

    def _embed_sync(
        self,
        project_id: str,
        location: str,
        texts: list[str],
    ) -> list[EmbeddingVectorResult]:
        try:
            from vertexai import init
            from vertexai.language_models import TextEmbeddingModel
        except ImportError as exc:
            raise EmbeddingProviderError("Vertex AI SDK not installed") from exc

        init(project=project_id, location=location)
        model = TextEmbeddingModel.from_pretrained(self.model_name)
        response = model.get_embeddings(texts)
        if len(response) != len(texts):
            raise EmbeddingProviderError("vertex embedding response size mismatch")

        vectors: list[EmbeddingVectorResult] = []
        for index, (text, item) in enumerate(zip(texts, response, strict=True)):
            values = list(item.values)
            if not values:
                raise EmbeddingProviderError("vertex embedding returned empty vector")
            vectors.append(EmbeddingVectorResult(text=text, vector=values, index=index))
        self.dimension = len(vectors[0].vector)
        return vectors
