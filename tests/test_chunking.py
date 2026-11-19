import pytest

from app.services.chunking import split_text


def test_chunks_preserve_requested_overlap_without_contained_trailing_chunk():
    text = "abcdefghij"

    chunks = split_text(text, chunk_size=6, chunk_overlap=2)

    assert chunks == ["abcdef", "efghij"]
    reconstructed = chunks[0] + "".join(chunk[2:] for chunk in chunks[1:])
    assert reconstructed == text
    assert chunks[0][-2:] == chunks[1][:2]


@pytest.mark.parametrize(
    ("text", "chunk_size", "chunk_overlap", "expected"),
    [
        ("", 6, 2, []),
        ("abc", 6, 2, ["abc"]),
        ("abcdef", 6, 2, ["abcdef"]),
        ("abcdefg", 6, 2, ["abcdef", "efg"]),
        ("abcdefghij", 6, 5, ["abcdef", "bcdefg", "cdefgh", "defghi", "efghij"]),
        ("abc", 3, 0, ["abc"]),
    ],
)
def test_chunking_boundaries(text, chunk_size, chunk_overlap, expected):
    chunks = split_text(text, chunk_size, chunk_overlap)

    assert chunks == expected
    assert all(chunks)
    if chunks:
        reconstructed = chunks[0] + "".join(chunk[chunk_overlap:] for chunk in chunks[1:])
        assert reconstructed == text


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (3, -1), (3, 3)],
)
def test_chunking_rejects_invalid_parameters(chunk_size, chunk_overlap):
    with pytest.raises(ValueError):
        split_text("content", chunk_size, chunk_overlap)
