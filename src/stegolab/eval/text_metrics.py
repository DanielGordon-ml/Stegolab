"""Text cover/stego comparison metrics (spec §13.2)."""

from __future__ import annotations

import unicodedata
from collections import Counter

from ..text.zero_width import DEFAULT_ALPHABET


def zero_width_count(text: str, alphabet: list[str] = DEFAULT_ALPHABET) -> int:
    alset = set(alphabet)
    return sum(1 for ch in text if ch in alset)


def visible_text(text: str, alphabet: list[str] = DEFAULT_ALPHABET) -> str:
    alset = set(alphabet)
    return "".join(ch for ch in text if ch not in alset)


def visible_equal(cover: str, stego: str, alphabet: list[str] = DEFAULT_ALPHABET) -> bool:
    return visible_text(cover, alphabet) == visible_text(stego, alphabet)


def unicode_category_summary(text: str) -> dict:
    return dict(Counter(unicodedata.category(ch) for ch in text))


def normalization_survival(stego: str, alphabet: list[str] = DEFAULT_ALPHABET) -> dict:
    before = zero_width_count(stego, alphabet)
    out = {}
    for form in ("NFC", "NFKC"):
        after = zero_width_count(unicodedata.normalize(form, stego), alphabet)
        out[form] = {"before": before, "after": after, "survives": after == before}
    return out


def analyze_text(cover: str, stego: str, metrics: list[str], alphabet: list[str] = DEFAULT_ALPHABET) -> dict:
    report: dict = {}
    for metric in metrics:
        if metric == "zero-width-count":
            report[metric] = zero_width_count(stego, alphabet)
        elif metric == "visible-diff":
            report[metric] = {"visible_equal": visible_equal(cover, stego, alphabet)}
        elif metric == "codepoints":
            report[metric] = unicode_category_summary(stego)
        elif metric == "normalization":
            report[metric] = normalization_survival(stego, alphabet)
        else:
            report[metric] = {"error": f"unknown or unsupported metric in this phase: {metric}"}
    return report
