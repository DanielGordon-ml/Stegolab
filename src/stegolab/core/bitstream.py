"""Convert framed bytes to/from an MSB-first bit array (NumPy uint8 of 0/1)."""

from __future__ import annotations

import numpy as np


def bytes_to_bits(data: bytes) -> np.ndarray:
    if not data:
        return np.zeros(0, dtype=np.uint8)
    arr = np.frombuffer(data, dtype=np.uint8)
    return np.unpackbits(arr)  # MSB-first, shape (8*len,)


def bits_to_bytes(bits: np.ndarray) -> bytes:
    bits = np.asarray(bits, dtype=np.uint8)
    if bits.size % 8 != 0:
        raise ValueError("bit array length must be a multiple of 8")
    if bits.size == 0:
        return b""
    return np.packbits(bits).tobytes()
