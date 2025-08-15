from __future__ import annotations
import re
from typing import List, Tuple
from .jobspec import JobSpec

_WIDE_WORDS = re.compile(r"\b(banner|poster|sign|display|backdrop|step\s*and\s*repeat)\b", re.I)
_FOLD_WORDS = re.compile(r"\b(tri[\s-]?fold|z[\s-]?fold|roll\s*fold|brochure|fold)\b", re.I)
_COLOR_WORDS = re.compile(r"\b(cmyk|rgb|rich\s*black|icc|profile|color|ink|tac)\b", re.I)

def _long_edge(job: JobSpec) -> float:
    if not job.trim_size:
        return 0.0
    return max(float(job.trim_size.w_in), float(job.trim_size.h_in))

def _canonical_product(job: JobSpec) -> str:
    p = (getattr(job, "product", "") or "").lower()
    for patt, label in (
        (r"\b(tri[\s-]?fold|brochure)\b", "trifold"),
        (r"\b(business\s*card|bc)\b", "business_card"),
        (r"\b(postcard|pc)\b", "postcard"),
        (r"\b(booklet|catalog|book)\b", "booklet"),
        (r"\b(banner|poster|sign)\b", "banner"),
    ):
        if re.search(patt, p):
            return label
    return p.strip() or "unknown"

def fold_preferences_from_message(msg: str) -> Tuple[str|None, str|None]:
    """Infer fold style and which panel folds in from free text."""
    m = (msg or "").lower()
    style = "z" if "z fold" in m or "z-fold" in m else ("roll" if "roll" in m else None)
    fin = "left" if "left" in m else ("right" if "right" in m else None)
    return style, fin

def detect_intents(job: JobSpec, message: str) -> List[str]:
    intents: List[str] = []

    # Always consider doc setup as base knowledge
    intents.append("doc_setup")

    m = message or ""
    prod = _canonical_product(job)
    long_edge = _long_edge(job)

    # Fold math triggers
    if prod == "trifold" or _FOLD_WORDS.search(m):
        # add a light size sanity check (still allow ML to flip later)
        if long_edge >= 8.0:
            intents.append("fold_math")

    # Color policy triggers
    if _COLOR_WORDS.search(m):
        intents.append("color_policy")

    # Wide-format triggers:
    # - explicit words OR product canonical banner/poster/sign
    # - OR large size heuristic (≥ 24" long edge) common for wide-format
    if prod == "banner" or _WIDE_WORDS.search(m) or long_edge >= 24.0:
        intents.append("wide_format")

    # De-duplicate while preserving order
    seen=set(); out=[]
    for i in intents:
        if i not in seen:
            out.append(i); seen.add(i)
    return out
