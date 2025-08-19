from prepress_helper.jobspec import JobSpec
from prepress_helper.skills import color_policy, policy_enforcer


def _bc_jobspec():
    return JobSpec(
        product="Business Card",
        trim_size={"w_in": 3.5, "h_in": 2.0},
        bleed_in=0.125,
        safety_in=0.125,
        pages=1,
        colors={"front": "CMYK", "back": "No Printing"},
        special={
            "shop": {
                "policies": {
                    "max_ink_coverage": 300,
                    "sleek_black": "60/60/80/100",
                    "allow_rgb": False,
                    "icc_profile": "US Web Coated (SWOP) v2",
                    "small_text_pt": 10,
                }
            },
            "small_text_pt": 10,
        },
    )


def test_tac_warning_triggers_over_limit():
    js = _bc_jobspec()
    tips = policy_enforcer.tips(js, "heavy solid 340 TAC")
    assert any("exceeds TAC 300%" in t for t in tips)


def test_tac_warning_not_triggered_under_limit():
    js = _bc_jobspec()
    tips = policy_enforcer.tips(js, "solid 260 TAC")
    assert not any("exceeds TAC" in t for t in tips)


def test_color_policy_uses_shop_settings():
    js = _bc_jobspec()
    tips = color_policy.tips(js)
    assert any("Body text ≤ 10 pt" in t for t in tips)
    assert any("60/60/80/100" in t for t in tips), "Should reflect shop rich black"
    assert any("US Web Coated (SWOP) v2" in t for t in tips)
