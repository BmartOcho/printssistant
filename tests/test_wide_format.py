from prepress_helper.jobspec import JobSpec
from prepress_helper.router import detect_intents
from prepress_helper.skills import wide_format

def _banner_job(rgb=True):
    return JobSpec(
        product="Vinyl Banner",
        trim_size={"w_in": 72.0, "h_in": 24.0},
        bleed_in=0.0,
        safety_in=0.25,
        pages=1,
        colors={"front": "CMYK", "back": "No Printing"},
        special={
            "shop": {
                "policies": {"icc_profile": "GRACoL 2013"},
                "products": {
                    "banner": {
                        "min_ppi": 150,
                        "allow_rgb": rgb,
                        "grommet_margin_in": 0.5,
                        "grommet_spacing_in": 12
                    }
                }
            },
            "product_preset": {
                "min_ppi": 150,
                "allow_rgb": rgb,
                "grommet_margin_in": 0.5,
                "grommet_spacing_in": 12
            }
        }
    )

def test_router_marks_wide_format_by_size():
    js = _banner_job()
    intents = detect_intents(js, "")
    assert "wide_format" in intents

def test_wide_format_tips_rgb_allowed():
    js = _banner_job(rgb=True)
    tips = wide_format.tips(js)
    assert any("RGB assets allowed" in t for t in tips)
    assert any("≥ 150 PPI" in t or "150 PPI" in t for t in tips)

def test_wide_format_tips_rgb_blocked():
    js = _banner_job(rgb=False)
    tips = wide_format.tips(js)
    assert any("Work in CMYK" in t for t in tips)

def test_wide_format_scripts_add_guides():
    js = _banner_job()
    scr = wide_format.scripts(js)
    code = scr.get("illustrator_jsx_wide_format_guides","")
    assert "addV" in code and "addH" in code
