# src/prepress_helper/router.py
from __future__ import annotations

import re
from typing import Any, Dict, Tuple

# Global shop config injected by the app/tests
SHOP_CFG: Dict[str, Any] = {}


def set_shop_cfg(cfg: Dict[str, Any] | None) -> None:
    """Set global shop configuration used by detection helpers."""
    global SHOP_CFG
    SHOP_CFG = cfg or {}


def _normalize(s: str | None) -> str:
    return (s or "").strip().lower()


def _is_wide_format_machine(name: str | None) -> bool:
    """
    Heuristics + config-driven detection for wide-format printers.
    Returns True for roll/flatbed wide-format devices.
    """
    machine = _normalize(name)
    if not machine:
        return False

    # Obvious keyword hints
    keyword_hits = ("latex", "flatbed", "arizona", "oce", "mimaki", "roland", "vutek")
    if any(k in machine for k in keyword_hits):
        return True

    cfg = SHOP_CFG or {}

    # press_capabilities from tests (roll/flatbed lists)
    caps = cfg.get("press_capabilities") or {}
    roll = [(_normalize(p)) for p in (caps.get("roll_printers") or [])]
    flat = [(_normalize(p)) for p in (caps.get("flatbed_printers") or [])]
    if machine in roll or machine in flat:
        return True

    # presses section with width hints
    presses = cfg.get("presses") or {}
    for pname, meta in presses.items():
        if _normalize(pname) == machine:
            max_w = (meta or {}).get("max_width_in", 0) or 0
            try:
                return float(max_w) >= 24.0
            except Exception:
                return False

    return False


def _maybe_color_policy(js) -> bool:
    # Very light heuristic; always safe to include color policy unless truly unknown.
    cols = js.colors or {}
    front = _normalize(cols.get("front"))
    back = _normalize(cols.get("back"))
    return bool(front or back)


def _maybe_fold_math(message: str) -> bool:
    msg = _normalize(message)
    return any(k in msg for k in ("fold", "panel", "score", "crease"))


def _maybe_wide_format(js) -> bool:
    # Prefer explicit machine hint
    machine = (js.special or {}).get("machine")
    if _is_wide_format_machine(machine):
        return True

    # Fallback on product/stock hints
    product = _normalize(getattr(js, "product", None))
    stock = _normalize(getattr(js, "stock", None))
    if any(k in product for k in ("banner", "poster", "sign", "wide")):
        return True
    if any(k in stock for k in ("banner", "poly", "sav", "vinyl")):
        return True

    return False


def fold_preferences_from_message(message: str) -> Tuple[str | None, float | None]:
    """
    Extract a fold 'style' and an inside panel allowance ('fold_in' in inches) from free text.
    Examples:
      "roll fold with 0.125 fold-in" -> ("roll", 0.125)
      "z fold 1/8 in" -> ("z", 0.125)
    """
    msg = _normalize(message)
    style = None
    for s in ("roll", "z", "gate", "half", "tri", "accordion"):
        if re.search(rf"\b{s}\b", msg):
            style = s
            break

    # find something like "0.125", "1/8", "1/4", followed by in/inch
    fold_in = None
    frac = re.search(r"(\d+)\s*/\s*(\d+)\s*(in|inch|inches)?", msg)
    dec = re.search(r"(\d*\.\d+|\d+)\s*(in|inch|inches)", msg)
    if frac:
        try:
            num = float(frac.group(1))
            den = float(frac.group(2))
            fold_in = round(num / den, 4)
        except Exception:
            fold_in = None
    elif dec:
        try:
            fold_in = round(float(dec.group(1)), 4)
        except Exception:
            fold_in = None

    return style, fold_in


def detect_intents(js, message: str) -> list[str]:
    """
    Decide which skills/modules to run for a given JobSpec + free-text message.
    Always includes 'doc_setup'.
    """
    intents: list[str] = ["doc_setup"]

    if _maybe_color_policy(js):
        intents.append("color_policy")

    if _maybe_fold_math(message):
        intents.append("fold_math")

    if _maybe_wide_format(js):
        intents.append("wide_format")

    # policy enforcer is useful on most sheet-fed/wide jobs
    intents.append("policy_enforcer")

    # de-dup while preserving order
    seen = set()
    result = []
    for it in intents:
        if it not in seen:
            seen.add(it)
            result.append(it)
    return result
