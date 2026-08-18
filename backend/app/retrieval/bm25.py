from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.$:/-]+")


@dataclass(frozen=True, slots=True)
class BM25Document:
    document_id: str
    text: str


@dataclass(frozen=True, slots=True)
class BM25Result:
    document_id: str
    score: float


def tokenize(text: str) -> list[str]:
    """Tokenize prose while preserving useful code and error-name characters."""

    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def rank_bm25(
    query: str,
    documents: Iterable[BM25Document],
    *,
    limit: int = 10,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[BM25Result]:
    """Rank documents with Okapi BM25 and omit documents with no lexical match."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")
    if k1 <= 0:
        raise ValueError("k1 must be greater than 0.")
    if not 0 <= b <= 1:
        raise ValueError("b must be between 0 and 1.")

    query_terms = tokenize(query)
    if not query_terms:
        raise ValueError("Query must contain at least one searchable token.")

    corpus = list(documents)
    if not corpus:
        return []

    tokenized_documents = [tokenize(document.text) for document in corpus]
    document_frequencies = _document_frequencies(tokenized_documents)
    average_length = sum(map(len, tokenized_documents)) / len(tokenized_documents)
    query_term_counts = Counter(query_terms)
    ranked: list[BM25Result] = []

    for document, terms in zip(corpus, tokenized_documents, strict=True):
        term_frequencies = Counter(terms)
        score = sum(
            query_frequency
            * _term_score(
                term_frequency=term_frequencies[term],
                document_frequency=document_frequencies.get(term, 0),
                document_length=len(terms),
                average_length=average_length,
                document_count=len(corpus),
                k1=k1,
                b=b,
            )
            for term, query_frequency in query_term_counts.items()
        )
        if score > 0:
            ranked.append(BM25Result(document_id=document.document_id, score=score))

    ranked.sort(key=lambda result: (-result.score, result.document_id))
    return ranked[:limit]


def _document_frequencies(documents: list[list[str]]) -> Counter[str]:
    frequencies: Counter[str] = Counter()
    for terms in documents:
        frequencies.update(set(terms))
    return frequencies


def _term_score(
    *,
    term_frequency: int,
    document_frequency: int,
    document_length: int,
    average_length: float,
    document_count: int,
    k1: float,
    b: float,
) -> float:
    if term_frequency == 0 or average_length == 0:
        return 0.0

    inverse_document_frequency = math.log(
        1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
    )
    length_normalization = 1 - b + b * document_length / average_length
    return inverse_document_frequency * (
        term_frequency * (k1 + 1) / (term_frequency + k1 * length_normalization)
    )
