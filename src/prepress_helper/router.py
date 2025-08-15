from __future__ import annotations
from typing import List, Dict, Any, Tuple

try:
    # Optional: tests sometimes override SHOP_CFG directly
    SHOP_CFG: Dict[str, Any] = SHOP_CFG  # type: ignore[name-defined]
except Exception:
    SHOP_CFG = {}  # Default empty; tests may set this

def _is_wide_format_machine(machine: str) -> bool:
    caps = SHOP_CFG.get("press_capabilities", {}) or {}
    rolls = [s.lower() for s in caps.get("roll_printers", [])]
    flats = [s.lower() for s in caps.get("flatbed_printers", [])]
    m = (machine or "").lower()
    return bool(m) and (m in rolls or m in flats)

def fold_preferences_from_message(msg: str) -> Tuple[str | None, str | None]:
    text = (msg or "").lower()
    style = None
    fin = None
    if "roll" in text:
        style = "roll"
    if "z-fold" in text or "z fold" in text or "zfold" in text:
        style = "z"
    if "left panel in" in text or "folds in left" in text:
        fin = "left"
    if "right panel in" in text or "folds in right" in text:
        fin = "right"
    return style, fin

def detect_intents(js, message: str) -> List[str]:
    intents: List[str] = ["doc_setup"]
    text = (message or "").lower()

    # Color policy cues
    if any(k in text for k in ("color policy", "rich black", "tac", "ink coverage", "cmyk", "rgb")):
        intents.append("color_policy")

    # Fold cues
    if any(k in text for k in ("trifold", "tri-fold", "z-fold", "z fold", "roll fold")):
        intents.append("fold_math")

    # Spot color cues
    if any(k in text for k in ("pantone", "spot", "white ink")):
        intents.append("spot")

    # Minimum spec cues
    if any(k in text for k in ("hairline", "small text", "tiny type", "min spec", "minimum spec")):
        intents.append("min_specs")

    # Wide-format by machine name (from XML→special.machine)
    machine = ""
    try:
        if js.special and isinstance(js.special, dict):
            machine = str(js.special.get("machine") or "")
    except Exception:
        machine = ""
    if _is_wide_format_machine(machine):
        intents.append("wide_format")

    # De-dupe
    seen = set()
    out: List[str] = []
    for i in intents:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out
