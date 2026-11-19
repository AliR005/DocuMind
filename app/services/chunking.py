def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into fixed-width character chunks with a shared overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between zero and chunk_size - 1")
    if not text:
        return []

    step = chunk_size - chunk_overlap
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += step

    return chunks
