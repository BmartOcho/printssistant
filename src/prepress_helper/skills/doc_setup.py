# src/prepress_helper/skills/doc_setup.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _shop_policies(js) -> Dict[str, Any]:
    special = getattr(js, "special", {}) or {}
    shop = special.get("shop", {}) if isinstance(special, dict) else {}
    return shop.get("policies", {}) if isinstance(shop, dict) else {}


def _trim(js) -> Tuple[float | None, float | None]:
    ts = getattr(js, "trim_size", None)
    if ts:
        w = getattr(ts, "w_in", None)
        h = getattr(ts, "h_in", None)
        if isinstance(w, (int, float)) and isinstance(h, (int, float)):
            return float(w), float(h)
    # fallback if raw fields exist on root
    w = getattr(js, "trim_w_in", None)
    h = getattr(js, "trim_h_in", None)
    return (
        float(w) if isinstance(w, (int, float)) else None,
        float(h) if isinstance(h, (int, float)) else None,
    )


def _is_nan(x: Any) -> bool:
    return isinstance(x, float) and x != x  # NaN check


def _fmt_in(x: float) -> str:
    s = f"{x:.3f}"
    return s.rstrip("0").rstrip(".")


def _get_min(pol: Dict[str, Any], a: str, b: str, default: float) -> float:
    """Accept either naming style, e.g. bleed_min_in or min_bleed_in."""
    val = pol.get(a, pol.get(b, default))
    try:
        return float(val if val is not None else default)
    except Exception:
        return default


def tips(js) -> List[str]:
    pol = _shop_policies(js)
    bleed_min = _get_min(pol, "bleed_min_in", "min_bleed_in", 0.125)
    safety_min = _get_min(pol, "safety_min_in", "min_safety_in", 0.25)

    # bleed
    bleed = getattr(js, "bleed_in", None)
    bleed = None if _is_nan(bleed) else bleed
    eff_bleed = max(float(bleed or 0.0), bleed_min)

    # safety (defaults to policy min if missing/NaN)
    safety = getattr(js, "safety_in", None)
    safety = None if _is_nan(safety) else safety
    eff_safety = max(float(safety if safety is not None else safety_min), safety_min)

    w, h = _trim(js)

    out: List[str] = []
    if w and h:
        # ASCII 'x' instead of Unicode '×'
        out.append(
            f"Create a document at {_fmt_in(w)}x{_fmt_in(h)} in with {_fmt_in(eff_bleed)} in bleed on all sides."
        )
    else:
        out.append(f"Create a document with {_fmt_in(eff_bleed)} in bleed on all sides.")
    out.append(f"Set safety margins to {_fmt_in(eff_safety)} in; keep text and logos inside.")
    out.append("Use CMYK document color mode; avoid placing RGB assets directly.")
    return out


def scripts(js) -> Dict[str, str]:
    pol = _shop_policies(js)
    bleed_min = _get_min(pol, "bleed_min_in", "min_bleed_in", 0.125)

    bleed = getattr(js, "bleed_in", None)
    bleed = None if _is_nan(bleed) else bleed
    eff_bleed = max(float(bleed or 0.0), bleed_min)

    w, h = _trim(js)
    w = w or 8.5
    h = h or 11.0

    jsx = f"""
// create_artboard.jsx
(function(){{
  var bleed = {_fmt_in(eff_bleed)}; // inches
  var w = {_fmt_in(w)}, h = {_fmt_in(h)}; // inches
  var doc = app.documents.add(DocumentColorSpace.CMYK, w*72, h*72);
  doc.documentPreferences.documentBleedUniformSize = true;
  doc.documentPreferences.documentBleedTopOffset = bleed*72;
}})();
""".strip(
        "\n"
    )
    return {"illustrator_jsx": jsx}
