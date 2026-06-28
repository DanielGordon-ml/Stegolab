import hashlib

import numpy as np

from stegolab.core import keys


def test_derive_seed_is_deterministic_and_matches_sha256():
    expected = int.from_bytes(hashlib.sha256(b"course-demo").digest()[:8], "big")
    assert keys.derive_seed("course-demo") == expected
    assert keys.derive_seed("course-demo") == keys.derive_seed("course-demo")


def test_permutation_is_a_valid_permutation():
    perm = keys.permutation(1000, "k")
    assert sorted(perm.tolist()) == list(range(1000))


def test_permutation_is_deterministic_for_same_key():
    a = keys.permutation(500, "same-key")
    b = keys.permutation(500, "same-key")
    assert np.array_equal(a, b)


def test_different_keys_give_different_orders():
    a = keys.permutation(500, "key-a")
    b = keys.permutation(500, "key-b")
    assert not np.array_equal(a, b)


def test_permutation_zero_length():
    assert keys.permutation(0, "k").tolist() == []
