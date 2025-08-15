# src/prepress_helper/skills/policy_enforcer.py
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _shop(js) -> Dict[str, Any]:
    return (getattr(js, "special", {}) or {}).get("shop", {})  # type: ignore[attr-defined]


def _policies(js) -> Dict[str, Any]:
    return _shop(js).get("policies", {})


def _presses(js) -> Dict[str, Any]:
    return _shop(js).get("presses", {})


def _norm_float(v: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if v is None:
            return default
        f = float(v)
        if math.isnan(f):  # covers NaN coming from XML
            return default
        return f
    except Exception:
        return default


def _maybe_press_cfg(presses: Dict[str, Any], machine_name: Optional[str]) -> Dict[str, Any]:
    """Best-effort fuzzy match of a machine name to a key in `presses`."""
    if not isinstance(presses, dict) or not machine_name:
        return {}
    m = machine_name.lower().strip()
    m_norm = m.replace(" ", "_").replace("-", "_")
    for key, cfg in presses.items():
        k = key.lower()
        if k in m or m in k or k in m_norm or m_norm in k:
            return cfg or {}
    return {}


def soft_nags(js) -> List[str]:
    """
    Return 'soft nag' strings based on shop policy & (rough) press detection.
    Non-fatal prompts that guide the operator.
    """
    nags: List[str] = []

    pol = _policies(js)
    presses = _presses(js)

    # --- Safety & Bleed minimums ---
    safety_min = _norm_float(pol.get("safety_min_in"))
    bleed_min = _norm_float(pol.get("bleed_min_in"))

    eff_safety = _norm_float(getattr(js, "safety_in", None), safety_min)
    if safety_min is not None and (eff_safety is None or eff_safety < safety_min):
        nags.append(f'Soft-nag: Safety increased to {safety_min:.3f}" (min {safety_min:.3f}").')

    eff_bleed = _norm_float(getattr(js, "bleed_in", None), bleed_min)
    if bleed_min is not None and (eff_bleed is None or eff_bleed < bleed_min):
        nags.append(f'Soft-nag: Bleed increased to {bleed_min:.3f}" (min {bleed_min:.3f}").')

    # --- ICC profile hint ---
    machine = (getattr(js, "special", {}) or {}).get("machine")  # type: ignore[attr-defined]
    press_cfg = _maybe_press_cfg(presses, machine)
    icc = press_cfg.get("icc") or press_cfg.get("icc_profile") or pol.get("default_icc")
    if icc:
        nags.append(f"Soft-nag: Using ICC profile: {icc}.")

    # --- Wide-format grommet reminder (heuristic) ---
    # Flag as wide if the matched press indicates roll/flatbed-ish traits:
    # either a big max width (>= 54) or it explicitly allows RGB (common for LFP RIPs).
    maxw = _norm_float(press_cfg.get("max_width_in"))
    allow_rgb = bool(press_cfg.get("allow_rgb"))
    is_wide = (maxw is not None and maxw >= 54) or allow_rgb
    if is_wide:
        g_spacing = _norm_float(pol.get("grommet_spacing_in"), 12.0) or 12.0
        nags.append(f'Soft-nag: Confirm grommet spacing; assuming {g_spacing:.0f}" by default.')

    return nags
