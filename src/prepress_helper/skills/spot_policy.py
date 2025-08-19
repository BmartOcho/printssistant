from __future__ import annotations

from typing import Any, Dict, List

from prepress_helper.config_loader import load_shop_config
from prepress_helper.jobspec import JobSpec

SHOP = load_shop_config("config")


def _get(cfg: Dict[str, Any], path: str, default=None):
    cur = cfg
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def tips(js: JobSpec, intents: List[str], msg: str) -> List[str]:
    out: List[str] = []
    spot_cfg = _get(SHOP, "policies.spot_policy", {}) or {}

    allow_sheet = bool(spot_cfg.get("allow_spot_on_sheet_fed", False))
    allow_wide = bool(spot_cfg.get("allow_spot_on_wide_format", True))
    whitelist = set(spot_cfg.get("whitelist_spots", []))
    is_wide = "wide_format" in intents

    # General guidance driven by workflow
    if is_wide and allow_wide:
        if whitelist:
            wl = ", ".join(sorted(whitelist))
            out.append(f"Spot colors allowed for wide-format: {wl}. Use spots only when needed (e.g., White/Gloss).")
        else:
            out.append("Spot colors allowed for wide-format. Use spots only when needed (e.g., White/Gloss).")
        if "White" in whitelist:
            out.append(
                "If using White Ink, place white objects on a topmost spot swatch named 'White' with overprint OFF unless RIP requires otherwise."
            )
    else:
        if allow_sheet:
            out.append(
                "Spot colors permitted on sheet-fed only when specified by the job ticket; otherwise convert to CMYK."
            )
        else:
            out.append("Convert Pantone/spot colors to CMYK for sheet-fed production unless explicitly required.")

    # Message nudge if Pantone mentioned
    m = (msg or "").lower()
    if any(k in m for k in ("pantone", "pms", "spot", "varnish", "foil", "white ink", "white spot")):
        if is_wide and allow_wide:
            out.append("Verify spot channels map correctly in RIP (e.g., 'White'/'Gloss').")
        else:
            out.append("Before export, expand/redefine spot swatches as CMYK to avoid unintended separations.")

    return out


def scripts(js: JobSpec, intents: List[str], msg: str) -> Dict[str, str]:
    spot_cfg = _get(SHOP, "policies.spot_policy", {}) or {}
    whitelist = set(spot_cfg.get("whitelist_spots", []))
    add_white = "White" in whitelist

    scripts: Dict[str, str] = {}
    if add_white:
        scripts["illustrator_jsx_spot_white"] = (
            r"""
// add_white_spot.jsx (Illustrator)
(function(){
  if (app.documents.length===0) return;
  var doc = app.activeDocument;
  function ensureSpot(name){
    try { var s = doc.spots.getByName(name); return s; } catch(e) {}
    var sp = doc.spots.add();
    sp.name = name;
    sp.colorType = ColorModel.SPOT;
    var c = new CMYKColor(); c.cyan=0; c.magenta=0; c.yellow=0; c.black=0;
    sp.color = c;
    return sp;
  }
  ensureSpot("White");
})();
""".strip()
        )
    return scripts
