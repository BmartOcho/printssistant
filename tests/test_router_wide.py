# tests/test_router_wide.py
from prepress_helper.router import _is_wide_format_machine, set_shop_cfg


def test_wide_format_signals():
    cfg = {
        "presses": {
            "hp_latex_570": {"max_width_in": 64, "substrates": ["Banner_13oz"]},
            "indigo_7900": {"max_width_in": 13},
        }
    }
    set_shop_cfg(cfg)
    assert _is_wide_format_machine("hp_latex_570") is True
    assert _is_wide_format_machine("indigo_7900") is False
