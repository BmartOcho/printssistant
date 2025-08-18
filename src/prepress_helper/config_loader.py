# src/prepress_helper/config_loader.py
from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
import yaml

try:
    # Python 3.9+ importlib.resources modern API
    from importlib import resources
except Exception:  # pragma: no cover
    resources = None  # type: ignore

from .jobspec import JobSpec


# ----------------------------
# Helpers
# ----------------------------

_EXPECTED_FILES = ("policies.yml", "product_presets.yml", "press_capabilities.yml")


def _num(val: Any, default: float) -> float:
    """Coerce to float safely; fall back to default if not possible."""
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _read_yaml_path(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _read_yaml_pkg(package: str, resource_name: str) -> Dict[str, Any]:
    """Read a YAML file packaged inside a Python package via importlib.resources."""
    if resources is None:
        return {}
    try:
        base = resources.files(package)  # type: ignore[attr-defined]
        file = base.joinpath(resource_name)
        if not file.is_file():
            return {}
        with file.open("rb") as f:  # .open() yields a binary handle
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _looks_like_cfg_dir(d: Path) -> bool:
    if not d or not d.exists() or not d.is_dir():
        return False
    return any((d / name).is_file() for name in _EXPECTED_FILES)


def _resolve_cfg_dir(cfg_dir: Optional[str]) -> Optional[Path]:
    """
    Find a usable config directory by checking, in order:
    1) the given path (as-is and relative to CWD),
    2) project root (../../ from this file) / <cfg_dir or 'config'>,
    3) packaged resources at 'prepress_helper/config' (handled elsewhere).
    """
    candidates: list[Path] = []

    if cfg_dir:
        p = Path(cfg_dir)
        candidates.append(p)
        candidates.append(Path.cwd() / cfg_dir)

    # project root (…/src/prepress_helper/config_loader.py -> project root is parents[2])
    this_file = Path(__file__).resolve()
    project_root = this_file.parents[2] if len(this_file.parents) >= 3 else this_file.parents[-1]
    candidates.append(project_root / (cfg_dir or "config"))

    for c in candidates:
        if _looks_like_cfg_dir(c):
            return c

    return None


# ----------------------------
# Public API
# ----------------------------

def load_shop_config(cfg_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load shop config from YAML. Works when launched from any working directory and when frozen.

    Search order:
    - cfg_dir (as given)
    - cwd/cfg_dir
    - project_root/cfg_dir
    - packaged 'prepress_helper/config' (if present)
    """
    # Resolve a filesystem directory first
    base = _resolve_cfg_dir(cfg_dir)

    if base:
        policies = _read_yaml_path(base / "policies.yml")
        products = _read_yaml_path(base / "product_presets.yml")
        presses_raw = _read_yaml_path(base / "press_capabilities.yml")
    else:
        # Fallback to packaged resources (requires files under prepress_helper/config in the wheel)
        policies = _read_yaml_pkg("prepress_helper.config", "policies.yml")
        products = _read_yaml_pkg("prepress_helper.config", "product_presets.yml")
        presses_raw = _read_yaml_pkg("prepress_helper.config", "press_capabilities.yml")

    # Normalize press capabilities into a single dict
    presses: Dict[str, Any] = {}
    if isinstance(presses_raw.get("presses"), dict):
        presses.update(presses_raw["presses"])
    for group in ("roll_printers", "sheetfed_presses", "digital_presses", "offset_presses"):
        if isinstance(presses_raw.get(group), dict):
            presses.update(presses_raw[group])

    return {"policies": policies or {}, "products": products or {}, "presses": presses or {}}


def apply_shop_config(js: JobSpec, shop_cfg: Dict[str, Any]) -> JobSpec:
    policies = shop_cfg.get("policies", {}) or {}

    # accept both naming styles: min_bleed_in / bleed_min_in ; min_safety_in / safety_min_in
    min_bleed = _num(policies.get("min_bleed_in", policies.get("bleed_min_in", 0.125)), 0.125)
    min_safety = _num(policies.get("min_safety_in", policies.get("safety_min_in", 0.25)), 0.25)


    # Track adjustments so we can soft-nag later
    special = dict(js.special or {})
    adjustments = dict((special.get("adjustments") or {}))

    orig_bleed = _num(getattr(js, "bleed_in", 0.0), 0.0)
    orig_safety = _num(getattr(js, "safety_in", 0.0), 0.0)

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
