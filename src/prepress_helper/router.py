from __future__ import annotations
from typing import List, Tuple, Set, Any
import re

from prepress_helper.jobspec import JobSpec
from prepress_helper.config_loader import load_shop_config

# Load once; CLI/API already calls apply_shop_config downstream.
SHOP_CFG = load_shop_config("config")


def _norm(s: Any) -> str:
    return (str(s) if s is not None else "").strip().lower()


def _machine_name(js: JobSpec) -> str:
    sp = getattr(js, "special", {}) or {}
    return _norm(sp.get("machine"))


def _wide_format_machine_names() -> Set[str]:
    """
    Collect normalized names from press_capabilities.yml:
      presses:
        roll_printers: [ "HP Latex 365", ... ]
        flatbed_printers: [ "Arizona 2280", ... ]
    """
    presses = (SHOP_CFG or {}).get("presses", {}) or {}

    def _to_names(value) -> List[str]:
        # accept list[str] or list[dict{name: str}]
        out: List[str] = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict) and "name" in item:
                    out.append(item["name"])
        return out

    roll = _to_names(presses.get("roll_printers", []))
    flat = _to_names(presses.get("flatbed_printers", []))
    return { _norm(n) for n in (roll + flat) }


_WIDE_NAMES = _wide_format_machine_names()


def fold_preferences_from_message(msg: str) -> Tuple[str | None, str | None]:
    """
    Parse hints like 'trifold roll fold right-in' → ('roll','right')
    Returns (style, fold_in) where style ∈ {'roll','z'} and fold_in ∈ {'left','right'}
    """
    m = _norm(msg)
    style = None
    fold_in = None

    if re.search(r"\b(z[\s-]*fold)\b", m):
        style = "z"
    elif re.search(r"\b(roll[\s-]*fold|tri[\s-]*fold|trifold)\b", m):
        style = "roll"

    if re.search(r"\bleft[\s-]*(in|panel)\b", m) or "left-in" in m:
        fold_in = "left"
    elif re.search(r"\bright[\s-]*(in|panel)\b", m) or "right-in" in m:
        fold_in = "right"

    return style, fold_in


def detect_intents(js: JobSpec, msg: str) -> List[str]:
    """
    Returns an ordered list of intents.
    NEW: wide_format is ONLY set when js.special.machine matches a configured
         roll_printer or flatbed_printer (no size- or message-based fallback).
    """
    intents: List[str] = []

    # Always suggest basic document setup
    intents.append("doc_setup")

    # Wide-format strictly by machine list
    machine = _machine_name(js)
    if machine and machine in _WIDE_NAMES:
        intents.append("wide_format")

    m = _norm(msg)

    # Fold math only when asked (msg hints)
    if re.search(r"\b(tri[\s-]*fold|trifold|roll[\s-]*fold|z[\s-]*fold)\b", m):
        intents.append("fold_math")

    # Color guidance when clearly requested
    if re.search(r"\b(cmyk|rich\s*black|tac|ink\s*coverage|color\s*policy|icc)\b", m):
        intents.append("color_policy")

    # Preserve order & uniqueness
    seen: set[str] = set()
    out: List[str] = []
    for i in intents:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out
