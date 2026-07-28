"""Query the Chroma index `backend/rag/ingest.py` builds (`agents.md` §4).

`Retriever` opens the persisted collection once and reuses one embeddings client for every
`search()` call — the same lifecycle as `backend.agents.tools.build_toolbelt`'s `store`. Each
`search()` now costs one live call to Gemini's embedding API (ADR-0013), not a local model
inference — a real, per-query network dependency this didn't have before.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.rag.ingest import COLLECTION_NAME, EMBEDDING_MODEL, NO_PAGE
from data_pipeline.config import get_settings


@dataclass(frozen=True)
class Passage:
    text: str
    source_id: str
    title: str
    org: str
    url: str
    page: int | None  # None if the source has no page structure


class Retriever:
    def __init__(self, chroma_dir: Path | None = None, model_name: str = EMBEDDING_MODEL):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set — retrieval embeds the query via Gemini's API now, "
                "not a local model (ADR-0013); see .env.example and runbook.md §1.2"
            )
        persist_dir = chroma_dir or settings.chroma_dir
        client = chromadb.PersistentClient(path=str(persist_dir))
        if COLLECTION_NAME not in {c.name for c in client.list_collections()}:
            raise FileNotFoundError(
                f"no '{COLLECTION_NAME}' collection at {persist_dir} — run "
                "`uv run python -m backend.rag.ingest` first"
            )
        self._collection = client.get_collection(COLLECTION_NAME)
        self._embedder = GoogleGenerativeAIEmbeddings(
            model=model_name, google_api_key=settings.gemini_api_key
        )

    def search(self, query: str, k: int = 4) -> list[Passage]:
        query_embedding = [self._embedder.embed_query(query)]
        result = self._collection.query(query_embeddings=query_embedding, n_results=k)
        documents = result["documents"][0] if result["documents"] else []
        metadatas = result["metadatas"][0] if result["metadatas"] else []
        return [
            Passage(
                text=text,
                source_id=meta["source_id"],
                title=meta["title"],
                org=meta["org"],
                url=meta["url"],
                page=None if meta["page"] == NO_PAGE else meta["page"],
            )
            for text, meta in zip(documents, metadatas, strict=True)
        ]
