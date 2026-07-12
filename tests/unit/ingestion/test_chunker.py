from contexts.knowledge_ingestion.infrastructure.chunker import chunk_text


def test_chunk_respects_size_and_overlap():
    words = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_text(words, size=800, overlap=128)
    assert len(chunks) >= 2
    # first chunk has 800 words
    assert len(chunks[0].split()) == 800
    # overlap: last 128 words of chunk 0 begin chunk 1
    assert chunks[0].split()[-128:] == chunks[1].split()[:128]


def test_short_text_single_chunk():
    chunks = chunk_text("hola mundo", size=800, overlap=128)
    assert chunks == ["hola mundo"]


def test_empty_text_yields_no_chunks():
    assert chunk_text("   ", size=800, overlap=128) == []


def test_overlap_equal_to_size_raises_valueerror():
    import pytest
    with pytest.raises(ValueError, match="overlap must be smaller than size"):
        chunk_text("some words here", size=100, overlap=100)


def test_overlap_greater_than_size_raises_valueerror():
    import pytest
    with pytest.raises(ValueError, match="overlap must be smaller than size"):
        chunk_text("some words here", size=100, overlap=150)


def test_size_zero_raises_valueerror():
    import pytest
    with pytest.raises(ValueError, match="size must be greater than 0"):
        chunk_text("some words here", size=0, overlap=0)


def test_negative_overlap_raises_valueerror():
    import pytest
    with pytest.raises(ValueError, match="overlap must be non-negative"):
        chunk_text("some words here", size=100, overlap=-1)
