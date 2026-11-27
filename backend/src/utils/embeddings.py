"""Dependency-free local text embeddings.

A hashed bag-of-words (unigrams + bigrams, sublinear TF, L2-normalised) vector.
It captures lexical overlap rather than deep semantics, but it is deterministic,
fast, and needs no API — used for the in-memory index and for LLM providers
(such as Groq) that do not offer an embeddings endpoint.
"""

from __future__ import annotations

import re
import zlib
from collections import Counter
from typing import List

import numpy as np

LOCAL_EMBEDDING_DIM = 1536

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has in is it its of on or that the to was were which who with "
    "what when where how many did does according provided corpus".split()
)


def _tokens(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def local_embed(text: str, dim: int = LOCAL_EMBEDDING_DIM) -> List[float]:
    """Embed ``text`` into a ``dim``-dimensional unit vector via feature hashing."""
    return local_embed_array(text, dim).tolist()


def local_embed_array(text: str, dim: int = LOCAL_EMBEDDING_DIM) -> np.ndarray:
    """Same as :func:`local_embed` but returns a float32 numpy array."""
    toks = _tokens(text)
    features = Counter(toks)
    features.update(f"{a} {b}" for a, b in zip(toks, toks[1:]))

    vec = np.zeros(dim, dtype=np.float32)
    for feat, count in features.items():
        h = zlib.crc32(feat.encode("utf-8"))
        sign = 1.0 if (h >> 31) & 1 else -1.0
        vec[h % dim] += sign * (1.0 + np.log(count))

    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec
