"""OpenAI embedding provider adapter (T-042)."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.providers.base_embedding import EmbeddingProviderError
from app.providers.embedding_schemas import EmbeddingBatchResult, EmbeddingVectorResult


class OpenAIEmbeddingProvider:
    """OpenAI embeddings API adapter."""

    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.openai_embedding_model
        self.dimension = 1536

    def _validate_config(self) -> str:
        api_key = self._settings.openai_api_key.get_secret_value()
        if not api_key:
            raise EmbeddingProviderError("OPENAI_API_KEY not configured")
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
                error=f"openai embedding failed: {exc}",
            )
        return EmbeddingBatchResult(
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
            vectors=vectors,
        )

    def _embed_sync(self, api_key: str, texts: list[str]) -> list[EmbeddingVectorResult]:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(input=texts, model=self.model_name)
        data = sorted(response.data, key=lambda item: item.index)
        if len(data) != len(texts):
            raise EmbeddingProviderError("openai embedding response size mismatch")

        vectors: list[EmbeddingVectorResult] = []
        for index, (text, item) in enumerate(zip(texts, data, strict=True)):
            values = list(item.embedding)
            if not values:
                raise EmbeddingProviderError("openai embedding returned empty vector")
            vectors.append(EmbeddingVectorResult(text=text, vector=values, index=index))
        self.dimension = len(vectors[0].vector)
        return vectors
