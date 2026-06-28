import numpy as np
import pytest

from stegolab.core import bitstream


def test_round_trip_identity():
    data = bytes(range(256))
    bits = bitstream.bytes_to_bits(data)
    assert bits.dtype == np.uint8
    assert bits.shape == (256 * 8,)
    assert set(np.unique(bits).tolist()) <= {0, 1}
    assert bitstream.bits_to_bytes(bits) == data


def test_msb_first_layout():
    # 0x80 = 1000_0000 -> first bit is 1, rest 0
    bits = bitstream.bytes_to_bits(b"\x80")
    assert bits.tolist() == [1, 0, 0, 0, 0, 0, 0, 0]
    # 0x01 = 0000_0001 -> last bit is 1
    assert bitstream.bytes_to_bits(b"\x01").tolist() == [0, 0, 0, 0, 0, 0, 0, 1]


def test_empty():
    assert bitstream.bytes_to_bits(b"").shape == (0,)
    assert bitstream.bits_to_bytes(np.zeros(0, dtype=np.uint8)) == b""


def test_non_multiple_of_8_raises():
    with pytest.raises(ValueError):
        bitstream.bits_to_bytes(np.array([1, 0, 1], dtype=np.uint8))
