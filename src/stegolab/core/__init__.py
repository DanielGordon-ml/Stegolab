"""Core: frame format, payload codec, errors, keys, capacity, and I/O."""

from . import bitstream, capacity, errors, frame, io, keys, payload_codec, types
from .bitstream import bits_to_bytes, bytes_to_bits
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
    "bitstream", "capacity", "errors", "frame", "io", "keys", "payload_codec", "types",
    "bits_to_bytes", "bytes_to_bits",
    "build_capacity_report", "frame_overhead_bytes", "nominal_overhead",
    "encode_frame", "frame_total_len", "header_len_from_prefix", "parse_frame", "payload_len_from_header",
    "derive_seed", "permutation",
    "decode_payload", "encode_payload", "select_compression",
    "CapacityReport", "Compression", "Encryption", "FrameFields", "ParsedFrame",
    "PayloadType", "RecoveryClass",
]
