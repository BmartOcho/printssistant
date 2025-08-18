from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional

# Module-level cache, populated by set_shop_cfg() from the API on startup.
SHOP_CFG: Dict[str, Any] = {}


def set_shop_cfg(cfg: Dict[str, Any]) -> None:
    """Inject shop config after load_shop_config() runs in the API."""
    global SHOP_CFG
    SHOP_CFG = cfg or {}


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _is_wide_format_machine(machine: str) -> bool:
    """
    True if `machine` is a known wide-format device.

    Supports two shapes:
      A) Legacy grouped lists under SHOP_CFG['press_capabilities']:
         - roll_printers: [str, ...]
         - flatbed_printers: [str, ...]
      B) Normalized dict under SHOP_CFG['presses']:
         - presses: { "<name>": { category/type/format/family/tags: ... }, ... }
    """
    m = _norm(machine)
    if not m:
        return False

    # --- A) legacy grouped lists
    caps = SHOP_CFG.get("press_capabilities") or {}
    rolls = [ _norm(x) for x in (caps.get("roll_printers") or []) ]
    flats = [ _norm(x) for x in (caps.get("flatbed_printers") or []) ]
    if m in rolls or m in flats:
        return True

    # --- B) normalized presses dict
    presses: Dict[str, Any] = SHOP_CFG.get("presses") or {}
    candidate: Optional[Dict[str, Any]] = None

    # try exact key match, then case-insensitive
    if m in presses:
        candidate = presses[m] if isinstance(presses[m], dict) else None
    else:
        for k, v in presses.items():
            if _norm(k) == m and isinstance(v, dict):
                candidate = v
                break

    if isinstance(candidate, dict):
        for field in ("category", "type", "format", "family", "tags"):
            val = candidate.get(field)
            if isinstance(val, str):
                low = val.lower()
                if any(tok in low for tok in ("roll", "flatbed", "wide")):
                    return True
            elif isinstance(val, list):
                lowlist = [str(x).lower() for x in val]
                if any(any(tok in item for tok in ("roll", "flatbed", "wide")) for item in lowlist):
                    return True

    return False


def fold_preferences_from_message(msg: str) -> Tuple[str | None, str | None]:
    text = (msg or "").lower()
    style: Optional[str] = None
    fin: Optional[str] = None

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

    # Wide-format by machine name (from XML → special.machine)
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
