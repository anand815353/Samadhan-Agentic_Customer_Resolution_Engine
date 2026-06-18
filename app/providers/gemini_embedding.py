"""Gemini API embedding provider adapter (T-042)."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.providers.base_embedding import EmbeddingProviderError
from app.providers.embedding_schemas import EmbeddingBatchResult, EmbeddingVectorResult

GEMINI_EMBEDDING_DIMENSION = 768


class GeminiEmbeddingProvider:
    """Gemini API embeddings via google-genai SDK."""

    provider_name = "gemini_api"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.gemini_embedding_model
        self.dimension = GEMINI_EMBEDDING_DIMENSION

    def _validate_config(self) -> str:
        api_key = self._settings.gemini_api_key.get_secret_value()
        if not api_key:
            raise EmbeddingProviderError("GEMINI_API_KEY not configured")
        return api_key

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        if not texts:
            return EmbeddingBatchResult(
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
                error="no texts provided",
            )
        try:
            api_key = self._validate_config()
            vectors = await asyncio.to_thread(self._embed_sync, api_key, texts)
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
                error=f"gemini embedding failed: {exc}",
            )
        return EmbeddingBatchResult(
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
            vectors=vectors,
        )

    def _embed_sync(self, api_key: str, texts: list[str]) -> list[EmbeddingVectorResult]:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(model=self.model_name, contents=texts)
        embeddings = getattr(response, "embeddings", None) or []
        if len(embeddings) != len(texts):
            raise EmbeddingProviderError("gemini embedding response size mismatch")

        vectors: list[EmbeddingVectorResult] = []
        for index, (text, item) in enumerate(zip(texts, embeddings, strict=True)):
            values = list(getattr(item, "values", None) or [])
            if not values:
                raise EmbeddingProviderError("gemini embedding returned empty vector")
            vectors.append(EmbeddingVectorResult(text=text, vector=values, index=index))
        self.dimension = len(vectors[0].vector)
        return vectors
