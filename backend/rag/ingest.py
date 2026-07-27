"""Chunk + embed the RAG knowledge base into a persisted Chroma index (`agents.md` §4).

    uv run python -m backend.rag.ingest    # rebuilds the index from data/knowledge_base/

Source documents and their citations live in `data/knowledge_base/sources.json` — the 3-doc
Phase 4 MVP settled at kickoff (ADR-0009): Mumbai Climate Action Plan, NDMA's heat-wave hazard
page, IMD's FAQ on Heat Wave (`references.md` §4). `data/knowledge_base/` itself is gitignored,
same as every other pipeline artifact (ADR-0004) — this script, not the files, is what's
committed and regenerable.

Chunking is by **word count**, not exact BPE tokens: ~800 "tokens" is approximated as ~800
whitespace-split words with 100 overlap. Close enough for English prose, and one fewer moving
part than loading a second tokenizer just to size chunks — the accuracy that matters here is
retrieval quality, not chunk-boundary precision (`docs/conventions.md`'s "boring, explainable
tech").
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from data_pipeline.config import get_settings

log = logging.getLogger("urbanheat.rag.ingest")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "policy_docs"
CHUNK_WORDS = 800
CHUNK_OVERLAP_WORDS = 100
# Chroma metadata values must be a primitive type — None isn't accepted, so an unpaginated
# source (e.g. a web page, not a PDF) is stored with this sentinel and translated back to
# `page=None` on the way out (backend/rag/retrieve.py).
NO_PAGE = -1


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source_id: str
    title: str
    org: str
    url: str
    page: int  # NO_PAGE if the source has no page structure (e.g. a web page)


def _split_pages(text: str) -> list[tuple[int, str]]:
    """Split on `--- page N ---` markers (added when the source PDF was extracted). A source
    with no markers — a web page, not a paginated document — is one block, `NO_PAGE`.
    """
    if "--- page " not in text:
        return [(NO_PAGE, text.strip())]
    pages: list[tuple[int, str]] = []
    for block in text.split("--- page ")[1:]:
        num_str, _, rest = block.partition(" ---")
        pages.append((int(num_str), rest.strip()))
    return pages


def _chunk_words(
    text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP_WORDS
) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = size - overlap
    windows = (words[i : i + size] for i in range(0, len(words), step))
    return [" ".join(window) for window in windows if window]


def load_chunks(knowledge_base_dir: Path) -> list[Chunk]:
    manifest_path = knowledge_base_dir / "sources.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"{manifest_path} not found — collect the Phase 4 MVP documents first "
            "(references.md §4, runbook.md)"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    chunks: list[Chunk] = []
    for source in manifest:
        raw = (knowledge_base_dir / source["file"]).read_text(encoding="utf-8")
        for page, page_text in _split_pages(raw):
            for i, piece in enumerate(_chunk_words(page_text)):
                chunks.append(
                    Chunk(
                        id=f"{source['id']}_p{page}_c{i}",
                        text=piece,
                        source_id=source["id"],
                        title=source["title"],
                        org=source["org"],
                        url=source["url"],
                        page=page,
                    )
                )
    return chunks


def build_index(
    knowledge_base_dir: Path | None = None,
    chroma_dir: Path | None = None,
    model_name: str = EMBEDDING_MODEL,
) -> int:
    """Rebuild the Chroma collection from scratch. Returns the number of chunks indexed."""
    settings = get_settings()
    kb_dir = knowledge_base_dir or (settings.data_dir / "knowledge_base")
    persist_dir = chroma_dir or settings.chroma_dir
    persist_dir.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks(kb_dir)
    if not chunks:
        raise ValueError(f"{kb_dir} listed no documents with any extractable text")

    model = SentenceTransformer(model_name, device="cpu")
    embeddings = model.encode([c.text for c in chunks], show_progress_bar=False).tolist()

    client = chromadb.PersistentClient(path=str(persist_dir))
    if COLLECTION_NAME in {c.name for c in client.list_collections()}:
        client.delete_collection(COLLECTION_NAME)  # rebuild from scratch, not an incremental add
    collection = client.create_collection(COLLECTION_NAME)
    collection.add(
        ids=[c.id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[
            {"source_id": c.source_id, "title": c.title, "org": c.org, "url": c.url, "page": c.page}
            for c in chunks
        ],
    )
    log.info("indexed %d chunks from %s into %s", len(chunks), kb_dir, persist_dir)
    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
    n_chunks = build_index()
    print(f"indexed {n_chunks} chunks")
