import numpy as np
import pytest
from PIL import Image

from stegolab.core import errors
from stegolab.image import randomized_lsb as rlsb


def _cover(tmp_path, w=64, h=64, seed=1):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8)).save(tmp_path / "c.png")
    return tmp_path / "c.png"


def _payload(tmp_path, data=b"keyed secret payload here"):
    (tmp_path / "p.txt").write_bytes(data)
    return tmp_path / "p.txt"


def test_same_key_round_trip(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    out, rec = tmp_path / "s.png", tmp_path / "r.txt"
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"key": "course-demo"})
    rlsb.extract(stego=str(out), out=str(rec), overwrite=False, params={"key": "course-demo"})
    assert rec.read_bytes() == b"keyed secret payload here"


def test_wrong_key_fails(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    out, rec = tmp_path / "s.png", tmp_path / "r.txt"
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"key": "right"})
    with pytest.raises((errors.IntegrityCheckFailed, errors.CorruptedPayload, errors.NoPayloadFound)):
        rlsb.extract(stego=str(out), out=str(rec), overwrite=False, params={"key": "wrong"})


def test_deterministic_output(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    o1, o2 = tmp_path / "s1.png", tmp_path / "s2.png"
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(o1), overwrite=False, params={"key": "k"})
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(o2), overwrite=False, params={"key": "k"})
    assert o1.read_bytes() == o2.read_bytes()


def test_requires_key_unless_allow_unkeyed(tmp_path):
    cover, payload = _cover(tmp_path), _payload(tmp_path)
    out = tmp_path / "s.png"
    with pytest.raises(errors.InvalidArguments):
        rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={})
    # allow_unkeyed succeeds
    rlsb.hide(cover=str(cover), payload=str(payload), out=str(out), overwrite=False, params={"allow_unkeyed": True})
    assert out.exists()
