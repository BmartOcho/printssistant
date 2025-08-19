# tests/test_config_loader_aliases.py
from prepress_helper.config_loader import apply_shop_config
from prepress_helper.jobspec import JobSpec


def _mk(js=None):
    return JobSpec(**(js or {}))


def test_policy_alias_bleed_safety():
    js = _mk({"bleed_in": 0.0, "safety_in": 0.0})

    cfg_a = {"policies": {"bleed_min_in": 0.125, "safety_min_in": 0.25}}
    out_a = apply_shop_config(js, cfg_a)
    assert out_a.bleed_in == 0.125 and out_a.safety_in == 0.25

    cfg_b = {"policies": {"min_bleed_in": 0.2, "min_safety_in": 0.3}}
    out_b = apply_shop_config(js, cfg_b)
    assert out_b.bleed_in == 0.2 and out_b.safety_in == 0.3
