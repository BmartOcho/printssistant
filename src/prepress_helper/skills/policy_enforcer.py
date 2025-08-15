from __future__ import annotations
from typing import List, Dict, Optional
from ..jobspec import JobSpec

def _shop(job: JobSpec) -> Dict:
    return (job.special or {}).get("shop", {})  # type: ignore

def _products(job: JobSpec) -> Dict:
    return _shop(job).get("products", {})  # type: ignore

def _presses(job: JobSpec) -> Dict:
    return _shop(job).get("presses", {})  # type: ignore

def _policies(job: JobSpec) -> Dict:
    return _shop(job).get("policies", {})  # type: ignore

def _preset(job: JobSpec) -> Dict:
    # If job.special.product_preset is a dict, prefer it; else fall back to products.banner
    pp = (job.special or {}).get("product_preset")  # type: ignore
    if isinstance(pp, dict):
        return pp
    prod = _products(job).get("banner", {})
    return prod if isinstance(prod, dict) else {}

def _resolve_allow_rgb(job: JobSpec) -> Optional[bool]:
    """Precedence: product preset -> press -> global policies -> None."""
    preset = _preset(job)
    if "allow_rgb" in preset:
        try:
            return bool(preset["allow_rgb"])
        except Exception:
            pass

    press_key = (job.special or {}).get("press")  # type: ignore
    if press_key and press_key in _presses(job):
        press = _presses(job).get(press_key, {})
        if isinstance(press, dict) and "allow_rgb" in press:
            try:
                return bool(press["allow_rgb"])
            except Exception:
                pass

    pol = _policies(job)
    if "allow_rgb" in pol:
        try:
            return bool(pol["allow_rgb"])
        except Exception:
            pass

    return None

def tips(job: JobSpec, message: str = "") -> List[str]:
    pol = _policies(job)
    out: List[str] = []

    # TAC enforcement
    tac_limit = pol.get("max_ink_coverage") or (job.special or {}).get("max_ink_coverage")  # type: ignore
    if tac_limit:
        out.append(f"Keep total area coverage (TAC) ≤ {tac_limit}% per shop policy.")
        # naive TAC detection in free text
        import re
        m = re.search(r'(\d{2,3})\s*%?\s*(?:tac|total|coverage)?', (message or "").lower())
        if m:
            try:
                seen = int(m.group(1))
                if 50 <= seen <= 400 and int(tac_limit) < seen:
                    out.append(f"⚠️ Proposed coverage {seen}% exceeds TAC {tac_limit}%. Reduce ink builds or adjust profile.")
            except Exception:
                pass

    # Rich black echo (prefer any shop/preset values)
    rb = (
        (job.special or {}).get("rich_black") or  # type: ignore
        pol.get("sleek_black") or
        pol.get("rich_black")
    )
    if rb:
        out.append(f"Use shop rich black: {rb}.")

    # RGB allowance (with proper precedence)
    allow = _resolve_allow_rgb(job)
    if allow is False:
        out.append("RGB assets not allowed—convert to CMYK before placing.")
    # If allow is True, we don't add a line here; wide_format (or other skills) will add a positive RGB tip.
    # If allow is None, we stay silent and let other skills decide.

    return out

def scripts(job: JobSpec, message: str = "") -> Dict[str, str]:
    # Policy enforcer is advisory-only for now.
    return {}
