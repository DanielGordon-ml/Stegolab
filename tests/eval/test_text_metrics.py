from stegolab.eval import text_metrics as tm
from stegolab.text.zero_width import DEFAULT_ALPHABET

ZW = DEFAULT_ALPHABET[0]


def test_zero_width_count():
    assert tm.zero_width_count(f"a{ZW}b{ZW}{ZW}c") == 3
    assert tm.zero_width_count("plain text") == 0


def test_visible_text_and_equal():
    cover = "hello world"
    stego = f"hello{ZW} world{ZW}{ZW}"
    assert tm.visible_text(stego) == cover
    assert tm.visible_equal(cover, stego) is True
    assert tm.visible_equal(cover, "hello there") is False


def test_unicode_category_summary():
    summary = tm.unicode_category_summary(f"A1 {ZW}")
    assert summary.get("Lu", 0) == 1   # 'A'
    assert summary.get("Nd", 0) == 1   # '1'
    assert summary.get("Cf", 0) >= 1   # ZWNJ is a format char


def test_normalization_survival_reports_survival():
    stego = f"word{ZW}word{ZW}"
    result = tm.normalization_survival(stego)
    assert result["NFKC"]["before"] == 2
    # honest: NFKC does NOT strip default zero-width chars
    assert result["NFKC"]["after"] == 2
    assert result["NFKC"]["survives"] is True


def test_analyze_text_dispatch():
    cover = "alpha beta gamma"
    stego = f"alpha{ZW} beta{ZW} gamma"
    report = tm.analyze_text(cover, stego, ["zero-width-count", "visible-diff", "normalization"])
    assert report["zero-width-count"] == 2
    assert report["visible-diff"]["visible_equal"] is True
    assert report["normalization"]["NFC"]["survives"] is True
