"""Lexical passage ranking for grounding prompts.

Retrieval here is scoped before it is ranked: the explanation only ever
offers passages from the documents the matched rules already depend on, so
ranking is a small in-memory BM25 over a few hundred passages. That keeps the
retrieval inspectable and free of any provider dependency; it can be swapped
without changing the citation contract, which is enforced after generation
by :mod:`permit_pathways.ai.corpus`.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .corpus import Passage

_TOKEN = re.compile(r"[a-z0-9§]+(?:\.[0-9]+)*")
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "will",
        "with",
        "shall",
        "may",
        "any",
        "such",
        "not",
        "no",
        "other",
        "than",
        "under",
        "upon",
        "which",
        "who",
        "whom",
        "within",
        "without",
    ]
)
_K1 = 1.5
_B = 0.75


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.casefold()) if t not in _STOPWORDS]


@dataclass(frozen=True)
class RankedPassage:
    passage: Passage
    score: float


def rank_passages(
    query: str, passages: list[Passage], limit: int
) -> list[RankedPassage]:
    """Score passages against the query with BM25 and return the top ``limit``."""
    if limit <= 0 or not passages:
        return []
    query_terms = tokenize(query)
    if not query_terms:
        return []
    docs = [Counter(tokenize(p.text)) for p in passages]
    lengths = [sum(c.values()) for c in docs]
    average = max(sum(lengths) / len(lengths), 1.0)
    document_frequency: Counter[str] = Counter()
    for counts in docs:
        document_frequency.update(counts.keys())
    total = len(docs)
    ranked: list[RankedPassage] = []
    for passage, counts, length in zip(passages, docs, lengths, strict=True):
        score = 0.0
        for term in set(query_terms):
            frequency = counts.get(term)
            if not frequency:
                continue
            idf = math.log(
                1
                + (total - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + _K1 * (1 - _B + _B * length / average)
            score += idf * frequency * (_K1 + 1) / denominator
        if score > 0:
            ranked.append(RankedPassage(passage, score))
    ranked.sort(key=lambda r: (-r.score, r.passage.passage_id))
    return ranked[:limit]
