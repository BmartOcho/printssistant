from prepress_helper.jobspec import JobSpec
from prepress_helper.skills import spot_policy


def _js():
    return JobSpec(
        product="Test",
        trim_size={"w_in": 11.0, "h_in": 8.5},
        bleed_in=0.125,
        safety_in=0.125,
        pages=1,
        colors={"front": "CMYK", "back": "No Printing"},
        stock="Vinyl",
        finish=None,
        imposition_hint="Banner",
        due_at=None,
        special={},
    )


def test_spot_on_wide_format_allows_white():
    js = _js()
    tips = spot_policy.tips(js, ["wide_format"], "white ink spot")
    joined = " ".join(tips).lower()
    assert "white" in joined and "spot" in joined


def test_spot_on_sheetfed_recommends_convert():
    js = _js()
    tips = spot_policy.tips(js, [], "pantone 185")
    assert any("convert" in t.lower() and "cmyk" in t.lower() for t in tips)
