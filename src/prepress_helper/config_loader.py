from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
import re
import yaml

from .jobspec import JobSpec

CFG_FILENAMES = {
    "policies": "policies.yml",
    "stocks": "stock_rules.yml",
    "products": "product_presets.yml",
    "presses": "press_capabilities.yml",
}

def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data

def load_shop_config(config_dir: str | Path = "config") -> Dict[str, Any]:
    """Load all YAMLs under config/ into a single dict."""
    cfg_dir = Path(config_dir)
    out: Dict[str, Any] = {"policies": {}, "stocks": {}, "products": {}, "presses": {}}
    for key, fname in CFG_FILENAMES.items():
        data = _load_yaml(cfg_dir / fname)
        # accept either flat or namespaced structure
        if key == "stocks":
            out["stocks"] = data.get("stocks", data) or {}
        elif key == "presses":
            out["presses"] = data.get("presses", data) or {}
        else:
            out[key] = data or {}
    return out

# --- helpers to use cfg ---

_PRODUCT_CANON = [
    (r"\b(tri[\s-]?fold|brochure)\b", "trifold"),
    (r"\b(business\s*card|bc)\b", "business_card"),
    (r"\b(postcard|pc)\b", "postcard"),
    (r"\b(booklet|catalog|book)\b", "booklet"),
    (r"\b(banner)\b", "banner"),
    (r"\b(flyer|one[-\s]?sheet)\b", "flyer"),
    (r"\b(label)\b", "label"),
]

def _canonical_product(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    t = name.lower()
    for pat, label in _PRODUCT_CANON:
        if re.search(pat, t):
            return label
    return None

def _match_stock_rule(stock_name: Optional[str], stocks_cfg: Any) -> Optional[Dict[str, Any]]:
    """very light fuzzy: substring match by 'name' field"""
    if not stock_name:
        return None
    rules = stocks_cfg if isinstance(stocks_cfg, list) else stocks_cfg.get("stocks", [])
    s = (stock_name or "").lower()
    best = None
    for r in rules:
        nm = str(r.get("name", "")).lower()
        if nm and (nm in s or s in nm):
            best = r
            break
    return best

def apply_shop_config(js: JobSpec, shop_cfg: Dict[str, Any]) -> JobSpec:
    """
    - Applies product presets (default bleed/safety/fold style) if missing.
    - Attaches stock-based params (e.g., fold_in_offset_in) into js.special.
    - Exposes the entire shop cfg under js.special['shop'] so custom keys are available.
    """
    # ensure special exists
    if js.special is None:
        js.special = {}

    # expose raw config for skills/scripts
    js.special["shop"] = shop_cfg

    # product presets
    prod_key = _canonical_product(getattr(js, "product", None))
    presets = shop_cfg.get("products", {})
    preset = presets.get(prod_key) if isinstance(presets, dict) else None
    if isinstance(preset, dict):
        # fill defaults only if missing
        if getattr(js, "bleed_in", None) in (None, 0) and "bleed_in" in preset:
            js.bleed_in = float(preset["bleed_in"])
        if getattr(js, "safety_in", None) in (None, 0) and "safety_in" in preset:
            js.safety_in = float(preset["safety_in"])
        # carry through any extra product knobs to special
        js.special.setdefault("product_preset", preset)

    # stock rules (e.g., fold offset, min text)
    rule = _match_stock_rule(getattr(js, "stock", None), shop_cfg.get("stocks", {}))
    if rule:
        # make selected stock rule available
        js.special.setdefault("stock_rule", rule)
        # preferred fold-in offset for fold math
        if "fold_in_offset_in" in rule and "fold_in_offset_in" not in js.special:
            js.special["fold_in_offset_in"] = float(rule["fold_in_offset_in"])

    return js
