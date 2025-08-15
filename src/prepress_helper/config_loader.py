# src/prepress_helper/config_loader.py
from __future__ import annotations
from typing import Dict, Any
import os
import yaml
from .jobspec import JobSpec

def _load_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}

def load_shop_config(cfg_dir: str) -> Dict[str, Any]:
    policies = _load_yaml(os.path.join(cfg_dir, "policies.yml"))
    products = _load_yaml(os.path.join(cfg_dir, "product_presets.yml"))

    presses_raw = _load_yaml(os.path.join(cfg_dir, "press_capabilities.yml"))
    presses: Dict[str, Any] = {}
    if isinstance(presses_raw.get("presses"), dict):
        presses.update(presses_raw["presses"])
    for group in ("roll_printers", "sheetfed_presses", "digital_presses", "offset_presses"):
        if isinstance(presses_raw.get(group), dict):
            presses.update(presses_raw[group])

    return {"policies": policies, "products": products, "presses": presses}

def apply_shop_config(js: JobSpec, shop_cfg: Dict[str, Any]) -> JobSpec:
    pol = shop_cfg.get("policies", {}) or {}
    min_bleed = float(pol.get("min_bleed_in", 0.125))
    min_safety = float(pol.get("min_safety_in", 0.25))

    # Track adjustments so we can soft-nag later
    special = dict(js.special or {})
    adjustments = dict(special.get("adjustments") or {})

    orig_bleed = float(js.bleed_in or 0.0)
    orig_safety = float(js.safety_in or 0.0)

    new_bleed = max(orig_bleed, min_bleed)
    new_safety = max(orig_safety, min_safety)

    if new_bleed != orig_bleed:
        adjustments["bleed_in"] = {"from": orig_bleed, "to": new_bleed, "min": min_bleed}
    if new_safety != orig_safety:
        adjustments["safety_in"] = {"from": orig_safety, "to": new_safety, "min": min_safety}

    js.bleed_in = new_bleed
    js.safety_in = new_safety

    special["adjustments"] = adjustments
    special["shop"] = shop_cfg
    js.special = special
    return js
