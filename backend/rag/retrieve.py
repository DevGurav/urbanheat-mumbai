"""Query the Chroma index `backend/rag/ingest.py` builds (`agents.md` §4).

`Retriever` loads the embedding model and opens the persisted collection once — construction
is the expensive part (~seconds), `search()` after that is cheap. Built once per app/agent-graph
lifetime, the same lifecycle as `backend.agents.tools.build_toolbelt`'s `store`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

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
        persist_dir = chroma_dir or settings.chroma_dir
        client = chromadb.PersistentClient(path=str(persist_dir))
        if COLLECTION_NAME not in {c.name for c in client.list_collections()}:
            raise FileNotFoundError(
                f"no '{COLLECTION_NAME}' collection at {persist_dir} — run "
                "`uv run python -m backend.rag.ingest` first"
            )
        self._collection = client.get_collection(COLLECTION_NAME)
        self._model = SentenceTransformer(model_name, device="cpu")

    def search(self, query: str, k: int = 4) -> list[Passage]:
        query_embedding = self._model.encode([query]).tolist()
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
