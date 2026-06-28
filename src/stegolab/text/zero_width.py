"""text-zero-width: hide a framed payload in invisible Unicode characters (spec §9.5).

Bits → symbols (one alphabet char per `bits_per_symbol` bits, MSB-first) → distributed
across word-boundary slots as contiguous blocks (so document order == symbol order).
Extraction is position-independent: collect the alphabet's characters in document order,
decode, and validate the frame checksum. Visible text is preserved exactly.
"""

from __future__ import annotations

import numpy as np

from ..core import bitstream, capacity as cap, frame as frame_mod, io as core_io, payload_codec
from ..core.errors import CapacityExceeded, InvalidArguments
from ..core.types import CapacityReport, PayloadType

DEFAULT_ALPHABET = ["‌", "‍", "​", "﻿"]  # 00,01,10,11
MINIMAL_ALPHABET = ["‌", "‍"]                       # 0,1


def alphabet_for(params: dict) -> list[str]:
    name = params.get("alphabet") or "default"
    if name == "default":
        return DEFAULT_ALPHABET
    if name == "minimal":
        return MINIMAL_ALPHABET
    raise InvalidArguments(f"unknown alphabet: {name}")


def bits_per_symbol(alphabet: list[str]) -> int:
    n = len(alphabet)
    bps = n.bit_length() - 1
    if (1 << bps) != n or bps < 1:
        raise InvalidArguments("alphabet size must be a power of two >= 2")
    return bps


def eligible_slots(cover_text: str) -> list[int]:
    """Insertion positions: the index just after each space (word boundary)."""
    return [i + 1 for i, ch in enumerate(cover_text) if ch == " "]


def _read_text(path) -> str:
    try:
        return core_io.read_bytes(path).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidArguments("cover/stego text is not valid UTF-8") from exc


def _payload_type_for_mime(mime: str) -> PayloadType:
    if mime.startswith("text/"):
        return PayloadType.TEXT
    if mime.startswith("image/"):
        return PayloadType.IMAGE
    return PayloadType.BYTES


def _frame_file(payload_path: str, compress: str) -> bytes:
    raw = core_io.read_bytes(payload_path)
    mime = core_io.detect_mime(payload_path)
    return payload_codec.encode_payload(
        raw=raw, payload_type=_payload_type_for_mime(mime),
        original_filename=core_io.sanitize_filename(str(payload_path)),
        mime_type=mime, compression=compress,
    )


def _max_density(params: dict) -> int:
    d = int(params.get("max_density", 4))
    if d < 1:
        raise InvalidArguments("max_density must be >= 1")
    return d


def capacity(*, cover: str, params: dict) -> CapacityReport:
    alphabet = alphabet_for(params)
    bps = bits_per_symbol(alphabet)
    density = _max_density(params)
    slots = eligible_slots(_read_text(cover))
    total_bits = len(slots) * bps * density
    return cap.build_capacity_report(
        total_bits, cap.nominal_overhead(), is_estimate=True,
        assumptions=f"text-zero-width bits_per_symbol={bps}, max_density={density}; eligible slots = word boundaries",
    )


def hide(*, cover: str, payload: str, out: str, overwrite: bool, params: dict) -> dict:
    alphabet = alphabet_for(params)
    bps = bits_per_symbol(alphabet)
    density = _max_density(params)
    cover_text = _read_text(cover)
    if any(ch in cover_text for ch in alphabet):
        raise InvalidArguments("cover already contains alphabet characters; choose another cover or alphabet")

    framed = _frame_file(payload, params.get("compress", "auto"))
    bits = bitstream.bytes_to_bits(framed)
    pad = (-len(bits)) % bps
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    groups = bits.reshape(-1, bps)
    weights = (1 << np.arange(bps - 1, -1, -1)).astype(np.int64)
    idxs = (groups * weights).sum(axis=1)
    chars = [alphabet[i] for i in idxs]

    slots = eligible_slots(cover_text)
    if len(chars) > len(slots) * density:
        raise CapacityExceeded(
            f"payload needs {len(chars)} symbols but cover holds {len(slots) * density}"
        )
    stego = _insert_blocks(cover_text, slots, chars)
    core_io.write_bytes(out, stego.encode("utf-8"), overwrite=overwrite)
    return {"method": "text-zero-width", "out": out, "symbols": len(chars), "bytes": len(framed),
            "params": {"alphabet": params.get("alphabet") or "default", "max_density": density}}


def _insert_blocks(cover_text: str, slots: list[int], chars: list[str]) -> str:
    """Distribute chars as contiguous blocks across slots (even split), preserving order."""
    s = len(slots)
    n = len(chars)
    base, rem = divmod(n, s)
    counts = [base + (1 if j < rem else 0) for j in range(s)]
    pieces = []
    prev = 0
    k = 0
    for pos, c in zip(slots, counts):
        pieces.append(cover_text[prev:pos])
        if c:
            pieces.append("".join(chars[k:k + c]))
            k += c
        prev = pos
    pieces.append(cover_text[prev:])
    return "".join(pieces)


def extract(*, stego: str, out: str, overwrite: bool, params: dict) -> dict:
    alphabet = alphabet_for(params)
    bps = bits_per_symbol(alphabet)
    stego_text = _read_text(stego)
    index_of = {ch: i for i, ch in enumerate(alphabet)}
    syms = np.array([index_of[ch] for ch in stego_text if ch in index_of], dtype=np.int64)
    if syms.size:
        shifts = np.arange(bps - 1, -1, -1)
        bits = ((syms[:, None] >> shifts) & 1).astype(np.uint8).reshape(-1)
    else:
        bits = np.zeros(0, dtype=np.uint8)
    usable = (bits.size // 8) * 8
    parsed = frame_mod.parse_frame(bitstream.bits_to_bytes(bits[:usable]))
    original = payload_codec.decode_payload(parsed)
    core_io.write_bytes(out, original, overwrite=overwrite)
    return {"method": "text-zero-width", "out": out, "bytes": len(original),
            "original_filename": parsed.original_filename, "mime_type": parsed.mime_type, "integrity": "ok"}
