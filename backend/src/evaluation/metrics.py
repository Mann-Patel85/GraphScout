"""Answer-quality metrics for the 3-way benchmark.

All scores are computed against ground truth; when no ground truth is
available the scorers return ``None`` rather than a made-up number.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Iterable, List, Optional, Union

GroundTruth = Union[str, Iterable[str], None]

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation/articles, collapse whitespace (SQuAD-style)."""
    text = text.lower().translate(_PUNCT_TABLE)
    text = _ARTICLES.sub(" ", text)
    return " ".join(text.split())


def _as_list(ground_truth: GroundTruth) -> List[str]:
    if ground_truth is None:
        return []
    if isinstance(ground_truth, str):
        items = [ground_truth]
    else:
        items = list(ground_truth)
    return [g for g in (str(x).strip() for x in items) if g]


def _token_f1(prediction: str, reference: str) -> float:
    pred_tokens = normalize_text(prediction).split()
    ref_tokens = normalize_text(reference).split()
    if not pred_tokens or not ref_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(ref_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def _contains(haystack: str, needle: str) -> bool:
    n = normalize_text(needle)
    if not n:
        return False
    return re.search(rf"(?<!\w){re.escape(n)}(?!\w)", normalize_text(haystack)) is not None


def answer_accuracy(answer: str, ground_truth: GroundTruth) -> Optional[float]:
    """1.0 if any reference answer appears in the prediction, else best token F1."""
    refs = _as_list(ground_truth)
    if not refs:
        return None
    if any(_contains(answer, r) for r in refs):
        return 1.0
    return max(_token_f1(answer, r) for r in refs)


def context_recall(context: str, ground_truth: GroundTruth) -> Optional[float]:
    """Fraction of reference-answer tokens present in the retrieved evidence."""
    refs = _as_list(ground_truth)
    if not refs:
        return None
    ctx_tokens = set(normalize_text(context).split())
    best = 0.0
    for r in refs:
        if _contains(context, r):
            return 1.0
        ref_tokens = normalize_text(r).split()
        if ref_tokens:
            best = max(best, sum(t in ctx_tokens for t in ref_tokens) / len(ref_tokens))
    return best


def extract_ground_truth(item: dict) -> List[str]:
    """Read ground truth from either dataset format (``ground_truth`` str or ``answer`` list)."""
    if item.get("ground_truth"):
        return _as_list(item["ground_truth"])
    return _as_list(item.get("answer"))
