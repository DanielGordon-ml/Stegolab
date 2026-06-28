"""Key derivation and deterministic permutation (spec §8.6).

seed = SHA-256(utf8(key))[:8] (big-endian) -> NumPy PCG64 -> Fisher-Yates shuffle.
Pinned to PCG64 so the permutation is reproducible across platforms.
"""

from __future__ import annotations

import hashlib

import numpy as np


def derive_seed(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def permutation(n: int, key: str) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(derive_seed(key)))
    perm = np.arange(n)
    rng.shuffle(perm)  # in-place Fisher-Yates
    return perm
