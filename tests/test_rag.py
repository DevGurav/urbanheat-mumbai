"""The RAG knowledge base: chunking (pure logic, always runs), then ingest + retrieval against
the real `data/knowledge_base/` documents and the persisted Chroma index (gitignored, ADR-0004
— skip cleanly if either hasn't been built, same pattern as every other data-backed test).
"""

import pytest

from backend.rag.ingest import NO_PAGE, _chunk_words, _split_pages, load_chunks

# --- pure logic: chunking, no fixtures, always runs -----------------------------------------


def test_split_pages_with_markers():
    text = "--- page 1 ---\n\nfirst page\n\n--- page 2 ---\n\nsecond page"
    pages = _split_pages(text)
    assert pages == [(1, "first page"), (2, "second page")]


def test_split_pages_without_markers_is_one_unpaged_block():
    pages = _split_pages("just some web page text")
    assert pages == [(NO_PAGE, "just some web page text")]


def test_chunk_words_respects_size_and_overlap():
    words = [f"w{i}" for i in range(1000)]
    text = " ".join(words)
    chunks = _chunk_words(text, size=800, overlap=100)
    assert len(chunks) == 2  # 1000 words, step=700: starts at 0 and 700
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert len(first_words) == 800
    # the overlap: the last 100 words of chunk 1 are the first 100 of chunk 2
    assert first_words[-100:] == second_words[:100]


def test_chunk_words_empty_text_is_no_chunks():
    assert _chunk_words("") == []
    assert _chunk_words("   ") == []


# --- against the real knowledge base ---------------------------------------------------------


@pytest.fixture
def knowledge_base_dir(settings):
    kb_dir = settings.data_dir / "knowledge_base"
    if not (kb_dir / "sources.json").exists():
        pytest.skip(f"{kb_dir}/sources.json not built — see references.md §4")
    return kb_dir


def test_load_chunks_covers_all_three_mvp_sources(knowledge_base_dir):
    chunks = load_chunks(knowledge_base_dir)
    source_ids = {c.source_id for c in chunks}
    assert source_ids == {"mcap_summary_2022", "ndma_heatwave_hazard", "imd_faq_heatwave"}
    assert all(c.text.strip() for c in chunks)  # no empty chunks


def test_load_chunks_every_chunk_has_real_provenance(knowledge_base_dir):
    chunks = load_chunks(knowledge_base_dir)
    for c in chunks:
        assert c.title and c.org and c.url.startswith("https://")


# --- against the persisted Chroma index -------------------------------------------------------


@pytest.fixture
def retriever(settings):
    from backend.rag.retrieve import Retriever

    try:
        return Retriever(chroma_dir=settings.chroma_dir)
    except FileNotFoundError as exc:
        pytest.skip(f"Chroma index not built: {exc}")


def test_retriever_finds_the_imd_criteria_passage(retriever):
    passages = retriever.search("what temperature declares a heat wave", k=4)
    assert len(passages) == 4
    assert any(p.source_id == "imd_faq_heatwave" for p in passages)
    assert all(p.url.startswith("https://") for p in passages)


def test_retriever_respects_k(retriever):
    assert len(retriever.search("Mumbai heat", k=1)) == 1
    assert len(retriever.search("Mumbai heat", k=3)) == 3


# --- the search_knowledge tool, wired into the toolbelt ---------------------------------------


def test_search_knowledge_tool_returns_cited_passages(retriever):
    from backend.agents.tools import _make_search_knowledge

    tool = _make_search_knowledge(retriever)
    result = tool.invoke({"query": "heat wave criteria", "k": 2})
    assert len(result["passages"]) == 2
    for passage in result["passages"]:
        assert passage["source"] and passage["org"] and passage["url"]


def test_build_toolbelt_without_retriever_omits_search_knowledge():
    from unittest.mock import MagicMock

    from backend.agents.tools import build_toolbelt

    tools = build_toolbelt(MagicMock())
    assert "search_knowledge" not in {t.name for t in tools}
    assert len(tools) == 7


def test_build_toolbelt_with_retriever_includes_search_knowledge(retriever):
    from unittest.mock import MagicMock

    from backend.agents.tools import build_toolbelt

    tools = build_toolbelt(MagicMock(), retriever=retriever)
    assert "search_knowledge" in {t.name for t in tools}
    assert len(tools) == 8
