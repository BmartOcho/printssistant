# src/prepress_helper/skills/policy_enforcer.py
from __future__ import annotations
from typing import List, Dict, Optional
from ..jobspec import JobSpec

def _shop(job: JobSpec) -> Dict:
    return (job.special or {}).get("shop", {})  # type: ignore

def _policies(job: JobSpec) -> Dict:
    return _shop(job).get("policies", {})  # type: ignore

def _presses(job: JobSpec) -> Dict:
    return _shop(job).get("presses", {})  # type: ignore

def _resolve_allow_rgb(job: JobSpec) -> Optional[bool]:
    # precedence: product preset -> press -> global policies -> None
    shop = _shop(job)
    products = shop.get("products", {}) or {}
    preset = (job.special or {}).get("product_preset")  # type: ignore

    if isinstance(preset, dict) and "allow_rgb" in preset:
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

def _is_wide_from_intents(intents: Optional[List[str]]) -> bool:
    return bool(intents and ("wide_format" in intents))

def tips(
    job: JobSpec,
    message: str = "",
    intents: Optional[List[str]] = None,
) -> List[str]:
    pol = _policies(job)
    out: List[str] = []

    # TAC enforcement + lightweight message parse
    tac_limit = pol.get("max_ink_coverage") or (job.special or {}).get("max_ink_coverage")  # type: ignore
    if tac_limit:
        out.append(f"Keep total area coverage (TAC) ≤ {tac_limit}% per shop policy.")
        import re
        m = re.search(r'(\d{2,3})\s*%?\s*(?:tac|total|coverage)?', (message or "").lower())
        if m:
            try:
                seen = int(m.group(1))
                if 50 <= seen <= 400 and int(tac_limit) < seen:
                    out.append(f"⚠️ Proposed coverage {seen}% exceeds TAC {tac_limit}%. Reduce ink builds or adjust profile.")
            except Exception:
                pass

    # RGB allowance (negative only; positive messaging handled by wide_format or other skills)
    allow = _resolve_allow_rgb(job)
    if allow is False:
        out.append("RGB assets not allowed—convert to CMYK before placing.")

    # Rich black selection by workflow
    rb_sheet = pol.get("rich_black_sheetfed") or pol.get("rich_black")
    rb_wide = pol.get("rich_black_wide") or pol.get("rich_black")

    use_wide = _is_wide_from_intents(intents)
    rb_val = (rb_wide if use_wide else rb_sheet)
    if rb_val:
        out.append(f"Use shop rich black: {rb_val}.")

    return out

def scripts(job: JobSpec, message: str = "", intents: Optional[List[str]] = None) -> Dict[str, str]:
    return {}
