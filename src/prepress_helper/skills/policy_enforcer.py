from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

def _get_policies(job: JobSpec) -> Dict:
    shop = (job.special or {}).get("shop", {})
    return shop.get("policies", {})

def _extract_tac_from_text(msg: str) -> int | None:
    # crude TAC detector: “300”, “300%”, “TAC 320”
    import re
    m = re.search(r'(\d{2,3})\s*%?\s*(?:tac|total|coverage)?', msg.lower())
    if not m:
        return None
    try:
        v = int(m.group(1))
        return v if 50 <= v <= 400 else None
    except:
        return None

def tips(job: JobSpec, message: str = "") -> List[str]:
    p = _get_policies(job)
    out: List[str] = []
    tac_limit = p.get("max_ink_coverage") or (job.special or {}).get("max_ink_coverage")
    if tac_limit:
        out.append(f"Keep total area coverage (TAC) ≤ {tac_limit}% per shop policy.")
        seen = _extract_tac_from_text(message or "")
        if seen and tac_limit and seen > int(tac_limit):
            out.append(f"⚠️ Proposed coverage {seen}% exceeds TAC {tac_limit}%. Reduce ink builds or adjust profile.")
    # honor custom rich black names
    rb = (job.special or {}).get("rich_black") or p.get("sleek_black") or p.get("rich_black")
    if rb:
        out.append(f"Use shop rich black: {rb}.")
    # optional RGB allowance
    if p.get("allow_rgb") is False:
        out.append("RGB assets not allowed—convert to CMYK before placing.")
    return out

def scripts(job: JobSpec, message: str = "") -> Dict[str, str]:
    # no scripts yet—pure policy checks (add preflight actions here later)
    return {}
