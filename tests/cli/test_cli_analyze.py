import json

from typer.testing import CliRunner

from stegolab.cli import app

runner = CliRunner()
COVER_TEXT = " ".join(f"word{i}" for i in range(600))


def _prep(tmp_path):
    cover = tmp_path / "cover.txt"
    cover.write_text(COVER_TEXT, encoding="utf-8")
    payload = tmp_path / "s.txt"
    payload.write_bytes(b"analyze me")
    stego = tmp_path / "stego.txt"
    r = runner.invoke(app, ["hide", "--payload", str(payload), "--cover", str(cover),
                            "--out", str(stego), "--method", "text-zero-width"])
    assert r.exit_code == 0, r.output
    return cover, stego


def test_analyze_text_json(tmp_path):
    cover, stego = _prep(tmp_path)
    r = runner.invoke(app, ["analyze", "--cover", str(cover), "--stego", str(stego),
                            "--method", "text-zero-width",
                            "--metrics", "zero-width-count,visible-diff,normalization", "--json"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["ok"] is True
    assert out["command"] == "analyze"
    assert out["result"]["zero-width-count"] > 0
    assert out["result"]["visible-diff"]["visible_equal"] is True
    assert out["result"]["normalization"]["NFKC"]["survives"] is True


def test_analyze_image_method_is_deferred(tmp_path):
    cover, stego = _prep(tmp_path)
    r = runner.invoke(app, ["analyze", "--cover", str(cover), "--stego", str(stego),
                            "--method", "image-lsb"])
    assert r.exit_code == 5  # UnsupportedMethod: image metrics are a later phase


def test_analyze_non_utf8_cover_exit_2(tmp_path):
    cover = tmp_path / "cover.bin"
    cover.write_bytes(b"\xff\xfe not valid utf-8")
    stego = tmp_path / "stego.txt"
    stego.write_text("hello world", encoding="utf-8")
    r = runner.invoke(app, ["analyze", "--cover", str(cover), "--stego", str(stego),
                            "--method", "text-zero-width"])
    assert r.exit_code == 2  # InvalidArguments from non-UTF-8 input, surfaced via the envelope
