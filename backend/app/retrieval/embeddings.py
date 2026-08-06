from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding


MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    """
    Load the embedding model once per Python process.
    """
    return TextEmbedding(model_name=MODEL_NAME)


def embed_passage(text: str) -> list[float]:
    """
    Convert one stored document chunk into a vector.
    """
    return _embed_text(text=text, prefix="passage")


def embed_query(text: str) -> list[float]:
    """
    Convert a user's search query into a vector.
    """
    return _embed_text(text=text, prefix="query")


def embed_passages(texts: list[str]) -> list[list[float]]:
    """
    Convert multiple stored document chunks into vectors.
    """

    if not texts:
        return []

    prepared_texts: list[str] = []

    for text in texts:
        cleaned_text = text.strip()

        if not cleaned_text:
            raise ValueError("Passage text cannot be empty.")

        prepared_texts.append(f"passage: {cleaned_text}")

    vectors = get_embedding_model().embed(prepared_texts)

    return [vector.tolist() for vector in vectors]


def _embed_text(text: str, prefix: str) -> list[float]:
    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError("Text cannot be empty.")

    prepared_text = f"{prefix}: {cleaned_text}"

    vectors = get_embedding_model().embed([prepared_text])
    vector = next(vectors)

    return vector.tolist()