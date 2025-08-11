
from __future__ import annotations
from typing import Dict, List, Any
from ..jobspec import JobSpec

def tips(job: JobSpec) -> List[str]:
    w = job.trim_size.w_in if job.trim_size else None
    h = job.trim_size.h_in if job.trim_size else None
    bleed = job.bleed_in or 0.125
    safety = job.safety_in or 0.125
    advice = [
        f"Create a document at {w}×{h} in with {bleed} in bleed on all sides." if w and h else
        f"Create a document with {bleed} in bleed on all sides.",
        f"Set safety margins to {safety} in; keep text and logos inside.",
        "Use CMYK document color mode; avoid placing RGB assets directly.",
    ]
    return advice

def scripts(job: JobSpec) -> Dict[str, str]:
    bleed = job.bleed_in or 0.125
    w = job.trim_size.w_in if job.trim_size else 8.5
    h = job.trim_size.h_in if job.trim_size else 11.0
    jsx = f"""
// create_artboard.jsx
(function(){{
  var bleed = {bleed}; // inches
  var w = {w}, h = {h}; // inches
  var doc = app.documents.add(DocumentColorSpace.CMYK, w*72, h*72);
  doc.documentPreferences.documentBleedUniformSize = true;
  doc.documentPreferences.documentBleedTopOffset = bleed*72;
}})();
"""
    return { "illustrator_jsx": jsx }
