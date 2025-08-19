from __future__ import annotations

import re
from typing import Any, Dict, List

from prepress_helper.jobspec import JobSpec


def _shop(js: JobSpec) -> Dict[str, Any]:
    sp = js.special or {}
    return sp.get("shop", {}) if isinstance(sp, dict) else {}


def _pol(js: JobSpec) -> Dict[str, Any]:
    return _shop(js).get("policies", {}) or {}


def _is_wide_machine(js: JobSpec) -> bool:
    sp = js.special or {}
    machine = (sp.get("machine") or "").lower()
    caps = _shop(js).get("press_capabilities", {}) or {}
    rolls = [s.lower() for s in caps.get("roll_printers", [])]
    flats = [s.lower() for s in caps.get("flatbed_printers", [])]
    return bool(machine) and (machine in rolls or machine in flats)


def tips(js: JobSpec, message: str) -> List[str]:
    """
    Policy-driven *tips*:
      - TAC guardrail (+ over-limit warning)
      - Shop rich black (wide-format vs sheet-fed)
    """
    out: List[str] = []
    pol = _pol(js)
    text = (message or "").lower()

    # Effective TAC max: use shop policy if present, else default 300 for tests/fixtures
    tac_max = int(pol.get("tac_max_percent") or 300)
    out.append(f"Keep total area coverage (TAC) ≤ {tac_max}% per shop policy.")
    m = re.search(r"(\d{2,3})\s*%?\s*tac", text)
    if m:
        proposed = int(m.group(1))
        if proposed > tac_max:
            out.append(f"⚠ Proposed coverage {proposed}% exceeds TAC {tac_max}%. Reduce ink builds or adjust profile.")

    # Shop rich black (prefer wide-format if applicable)
    rb = pol.get("rich_black", {}) or {}
    formula = (
        rb.get("wide_format" if _is_wide_machine(js) else "sheet_fed") or rb.get("sheet_fed") or rb.get("wide_format")
    )
    if isinstance(formula, (list, tuple)) and len(formula) == 4:
        c, m, y, k = formula
        out.append(f"Use shop rich black: {c}/{m}/{y}/{k}.")

    return out


def soft_nags(js: JobSpec) -> List[str]:
    out: List[str] = []
    pol = _pol(js)

    # Safety min bump notice
    try:
        safety_min = pol.get("safety_min_in")
        sval = js.safety_in if isinstance(js.safety_in, (int, float)) else None
        if safety_min is not None:
            smin = float(safety_min)
            if sval is None or float(sval) < smin:
                out.append(f'Soft-nag: Safety increased to {smin:.3f}" (min {smin:.3f}").')
    except Exception:
        pass

    # ICC reminder
    icc = pol.get("default_icc")
    if icc:
        out.append(f"Soft-nag: Using ICC profile: {icc}.")

    # Grommet confirmation for wide-format devices
    if _is_wide_machine(js):
        out.append('Soft-nag: Confirm grommet spacing; assuming 12" by default.')

    return out


def scripts(js: JobSpec, message: str) -> Dict[str, str]:
    """
    API expects this symbol; keep minimal for now.
    (Add Illustrator/Photoshop policy scripts here later if desired.)
    """
    return {}
