from prepress_helper.cli import _dedupe_tips


def test_cmyk_lines_deduped():
    tips = [
        "Use CMYK document color mode; avoid placing RGB assets directly.",
        "Work in CMYK; avoid placing RGB assets directly.",
    ]
    out = _dedupe_tips(tips)
    assert len(out) == 1


def test_rich_black_shop_specific_wins():
    tips = [
        "Rich black for large solids/headlines: 60/60/80/100.",
        "Use shop rich black: 60/60/80/100.",
    ]
    out = _dedupe_tips(tips)
    assert out == ["Use shop rich black: 60/60/80/100."]
