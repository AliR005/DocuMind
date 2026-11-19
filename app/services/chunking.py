def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into fixed-width character chunks with a shared overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between zero and chunk_size - 1")
    if not text:
        return []

    step = chunk_size - chunk_overlap
    return [text[start : start + chunk_size] for start in range(0, len(text), step)]
