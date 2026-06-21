"""Embedding provider factory."""

from app.core.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.embeddings.mock import MockEmbeddingProvider
from app.providers.embeddings.openai import OpenAIEmbeddingProvider

_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        if settings.use_openai_embeddings:
            _provider = OpenAIEmbeddingProvider()
        else:
            _provider = MockEmbeddingProvider()
    return _provider


def embedding_model_for_doc_type(doc_type: str) -> str:
    if doc_type == "filing" and settings.rag_embedding_model_filing:
        return settings.rag_embedding_model_filing
    return settings.embedding_model


async def _embed_with_model(
    provider: EmbeddingProvider, texts: list[str], model: str
) -> list[list[float]]:
    if isinstance(provider, OpenAIEmbeddingProvider):
        return await provider.embed_texts(texts, model=model)
    return await provider.embed_texts(texts)


async def embed_documents_by_type(documents: list[dict]) -> list[dict]:
    """Embed documents using per-type model selection; annotate meta with model name."""
    if not documents:
        return []

    provider = get_embedding_provider()
    by_model: dict[str, list[tuple[int, dict]]] = {}
    for index, doc in enumerate(documents):
        doc_type = (doc.get("meta") or {}).get("type", "document")
        model = embedding_model_for_doc_type(doc_type)
        by_model.setdefault(model, []).append((index, doc))

    embedded: list[dict | None] = [None] * len(documents)
    for model, items in by_model.items():
        texts = [doc["content"] for _, doc in items]
        vectors = await _embed_with_model(provider, texts, model)
        for (index, doc), vector in zip(items, vectors, strict=True):
            meta = dict(doc.get("meta") or {})
            meta["embedding_model"] = model
            embedded[index] = {**doc, "embedding": vector, "meta": meta}

    return [doc for doc in embedded if doc is not None]
