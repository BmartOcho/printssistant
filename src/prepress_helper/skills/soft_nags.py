# src/prepress_helper/skills/soft_nags.py
from __future__ import annotations

from typing import Dict, List, Optional

from ..jobspec import JobSpec


def _shop(job: JobSpec) -> Dict:
    return (job.special or {}).get("shop", {})  # type: ignore


def _policies(job: JobSpec) -> Dict:
    return _shop(job).get("policies", {})  # type: ignore


def _enabled(job: JobSpec, name: str) -> bool:
    pol = _policies(job)
    sn = pol.get("soft_nags") or {}
    if sn is True:  # legacy truthy
        return True
    if not isinstance(sn, dict):
        return False
    if sn.get("enable") is False:
        return False
    return bool(sn.get(name, True))


def _is_wide(intents: Optional[List[str]]) -> bool:
    return bool(intents and "wide_format" in intents)


def _fmt_in(x: float) -> str:
    return f'{x:.3f}"'


def _find_icc(job: JobSpec) -> Optional[str]:
    # Try special → product preset → press → policies.default_icc
    special = job.special or {}
    if isinstance(special.get("icc_profile"), str):
        return special["icc_profile"]  # type: ignore

    shop = _shop(job)
    shop.get("products") or {}
    preset = special.get("product_preset")
    if isinstance(preset, dict) and isinstance(preset.get("icc_profile"), str):
        return preset["icc_profile"]

    press_key = special.get("press")
    presses = shop.get("presses") or {}
    if press_key and isinstance(presses.get(press_key), dict):
        p = presses[press_key]
        if isinstance(p.get("icc_profile"), str):
            return p["icc_profile"]

    default_icc = _policies(job).get("default_icc")
    if isinstance(default_icc, str):
        return default_icc

    return None


def tips(job: JobSpec, message: str = "", intents: Optional[List[str]] = None) -> List[str]:
    out: List[str] = []
    pol = _policies(job)

    # 1) Adjustments we made (bleed/safety)
    if _enabled(job, "adjustments"):
        adj = (job.special or {}).get("adjustments", {})
        if isinstance(adj, dict):
            b = adj.get("bleed_in")
            if isinstance(b, dict) and b.get("from") is not None and b.get("to") is not None:
                out.append(f'Soft-nag: Bleed increased to {_fmt_in(float(b["to"]))} (min {_fmt_in(float(b["min"]))}).')
            s = adj.get("safety_in")
            if isinstance(s, dict) and s.get("from") is not None and s.get("to") is not None:
                out.append(f'Soft-nag: Safety increased to {_fmt_in(float(s["to"]))} (min {_fmt_in(float(s["min"]))}).')

    # 2) Wide-format grommet confirmation
    if _is_wide(intents) and _enabled(job, "grommets"):
        default_grom = float(pol.get("grommet_spacing_default_in", 12))
        grom = (job.special or {}).get("grommet_spacing_in")
        if not isinstance(grom, (int, float)):
            out.append(f'Soft-nag: Confirm grommet spacing; assuming {default_grom:.0f}" by default.')

    # 3) ICC profile presence
    if _enabled(job, "icc_missing"):
        icc = _find_icc(job)
        if not icc:
            out.append("Soft-nag: No ICC profile specified—using system default.")
        else:
            # Gentle confirmation (info-style)
            out.append(f"Soft-nag: Using ICC profile: {icc}.")

    return out


def scripts(job: JobSpec, message: str = "", intents: Optional[List[str]] = None) -> Dict[str, str]:
    # No scripts for nags—just guidance.
    return {}
