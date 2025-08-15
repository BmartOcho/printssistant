from prepress_helper.cli import _dedupe_tips

def test_prefers_wide_format_setup_over_generic():
    tips = [
        "Create a document at 11.0×8.5 in with 0.125 in bleed on all sides.",
        "Set document to 11.0×8.5 in; bleed 0.125\"; safety 0.125\".",
    ]
    out = _dedupe_tips(tips)
    assert out == ["Set document to 11.0×8.5 in; bleed 0.125\"; safety 0.125\"."]

def test_rgb_allowed_drops_cmyk_admonition():
    tips = [
        "Use CMYK document color mode; avoid placing RGB assets directly.",
        "RGB assets allowed; embed sRGB/Adobe RGB and let the RIP handle conversion.",
    ]
    out = _dedupe_tips(tips)
    assert out == ["RGB assets allowed; embed sRGB/Adobe RGB and let the RIP handle conversion."]
