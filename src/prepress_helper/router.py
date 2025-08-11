from __future__ import annotations
from typing import List, Tuple
from .jobspec import JobSpec

# Adjust if you want fold logic on smaller pieces
FOLD_MIN_LONG_EDGE = 10.5

def _long_edge(job: JobSpec) -> float:
    ts = getattr(job, "trim_size", None)
    if not ts:
        return 0.0
    w = float(getattr(ts, "w_in", 0.0) or 0.0)
    h = float(getattr(ts, "h_in", 0.0) or 0.0)
    return max(w, h)

def _contains(text: str | None, *keywords: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in keywords)

def detect_intents(job: JobSpec, user_msg: str) -> List[str]:
    """
    Return a list of skill intents to run, in priority order.
    Possible intents: 'doc_setup', 'fold_math', 'color_policy'.
    """
    msg = (user_msg or "").lower()
    intents: List[str] = []

    # Document setup signal
    if any(k in msg for k in ("setup", "artboard", "document", "preset", "new doc", "new document")):
        intents.append("doc_setup")

    # Color policy signals
    if any(k in msg for k in ("color", "cmyk", "rgb", "icc", "rich black", "ink", "swop", "gracol")):
        intents.append("color_policy")

    # Fold math signals with size gate (override with 'force fold')
    fold_hint = (
        "fold" in msg
        or _contains(job.product, "fold", "brochure", "tri-fold", "trifold", "gatefold", "z-fold")
    )
    if fold_hint and ("force fold" in msg or _long_edge(job) >= FOLD_MIN_LONG_EDGE):
        intents.append("fold_math")

    # Default if nothing matched
    if not intents:
        intents.append("doc_setup")

    # De-dup while preserving order
    seen = set()
    out: List[str] = []
    for it in intents:
        if it not in seen:
            out.append(it)
            seen.add(it)
    return out

def fold_preferences_from_message(user_msg: str) -> Tuple[str, str]:
    """
    Parse message to infer fold style and which panel folds in.
    Returns (style, fold_in):
      style ∈ {'roll','z'}
      fold_in ∈ {'left','right'}
    """
    msg = (user_msg or "").lower()
    style = "z" if ("z fold" in msg or "z-fold" in msg or "accordion" in msg) else "roll"
    fold_in = "left" if ("left folds in" in msg or "fold in left" in msg) else "right"
    return style, fold_in
