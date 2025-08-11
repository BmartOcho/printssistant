
from __future__ import annotations
from typing import List
from .jobspec import JobSpec

def _long_edge(job: JobSpec) -> float:
    return max(getattr(job.trim_size, "w_in", 0.0) or 0.0,
               getattr(job.trim_size, "h_in", 0.0) or 0.0)

def detect_intents(job: JobSpec, user_msg: str) -> List[str]:
    msg = (user_msg or "").lower()
    intents: List[str] = []
    if any(k in msg for k in ["setup", "artboard", "document", "preset"]):
        intents.append("doc_setup")
    if "fold" in msg or (job.product and "fold" in job.product):
        intents.append("fold_math")
    if any(k in msg for k in ["color", "cmyk", "rgb", "icc", "rich black"]):
        intents.append("color_policy")
    if any(k in msg for k in ["script", "jsx", "action", "automation"]):
        intents.append("automation_scripts")
    return intents or ["doc_setup"]
