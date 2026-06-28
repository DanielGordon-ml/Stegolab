"""Core: frame format, payload codec, errors, keys, capacity, and I/O."""

from . import capacity, errors, frame, io, keys, payload_codec, types
from .capacity import build_capacity_report, frame_overhead_bytes, nominal_overhead
from .frame import encode_frame, frame_total_len, header_len_from_prefix, parse_frame, payload_len_from_header
from .keys import derive_seed, permutation
from .payload_codec import decode_payload, encode_payload, select_compression
from .types import (
    CapacityReport,
    Compression,
    Encryption,
    FrameFields,
    ParsedFrame,
    PayloadType,
    RecoveryClass,
)

__all__ = [
    "capacity", "errors", "frame", "io", "keys", "payload_codec", "types",
    "build_capacity_report", "frame_overhead_bytes", "nominal_overhead",
    "encode_frame", "frame_total_len", "header_len_from_prefix", "parse_frame", "payload_len_from_header",
    "derive_seed", "permutation",
    "decode_payload", "encode_payload", "select_compression",
    "CapacityReport", "Compression", "Encryption", "FrameFields", "ParsedFrame",
    "PayloadType", "RecoveryClass",
]
