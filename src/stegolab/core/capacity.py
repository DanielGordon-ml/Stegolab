"""Frame overhead and capacity reports (spec §8.3, §13)."""

from __future__ import annotations

from .types import (
    DEFAULT_MIME,
    FIXED_HEADER_FIELDS,
    FIXED_PREFIX_LEN,
    CapacityReport,
    Encryption,
)


def frame_overhead_bytes(
    original_filename: str,
    mime_type: str,
    encryption: Encryption = Encryption.NONE,
    salt_len: int = 0,
    nonce_len: int = 0,
) -> int:
    header_len = (
        FIXED_HEADER_FIELDS
        + 2 + len(original_filename.encode("utf-8"))
        + 2 + len(mime_type.encode("utf-8"))
    )
    if int(encryption) != 0:
        header_len += (1 + salt_len) + (1 + nonce_len)
    return FIXED_PREFIX_LEN + header_len


def nominal_overhead() -> int:
    return frame_overhead_bytes("", DEFAULT_MIME)


def build_capacity_report(
    total_capacity_bits: int,
    overhead_bytes: int,
    *,
    is_estimate: bool,
    assumptions: str,
) -> CapacityReport:
    total_bytes = total_capacity_bits // 8
    usable_bytes = max(0, total_bytes - overhead_bytes)
    return CapacityReport(
        total_bits=total_capacity_bits,
        total_bytes=total_bytes,
        overhead_bytes=overhead_bytes,
        usable_bytes=usable_bytes,
        is_estimate=is_estimate,
        assumptions=assumptions,
    )
