from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

def _axis_length(job: JobSpec) -> float:
    if not job.trim_size:
        return 0.0
    return max(job.trim_size.w_in, job.trim_size.h_in)

def _trifold_panels(total: float, style: str = "roll", fold_in: str = "right") -> List[float]:
    if style == "z":
        t = round(total / 3.0, 4)
        return [t, t, t]
    outer = round((total + (1.0/16.0)) / 3.0, 4)  # two outers equal
    inner = round(outer - (1.0/16.0), 4)          # fold-in panel smaller by 1/16"
    return [inner, outer, outer] if fold_in == "left" else [outer, outer, inner]

def tips(job: JobSpec, style: str = "roll", fold_in: str = "right") -> List[str]:
    length = _axis_length(job)
    if length < 8.0:
        return ["Size looks too small for a tri-fold—confirm product and dimensions before placing fold guides."]
    panels = _trifold_panels(length, style=style, fold_in=fold_in)
    bleed = job.bleed_in or 0.125
    safety = job.safety_in or 0.125
    return [
        f"Tri-fold ({style}) along long edge: panel widths ≈ {', '.join(f'{p:.4g}\"' for p in panels)} (total {length}\").",
        f"Add fold guides at {panels[0]:.4g}\" and {(panels[0]+panels[1]):.4g}\" from the left edge.",
        f"Use {bleed}\" bleed; keep type {safety}\" from folds/trim.",
        "If your fold-in panel is opposite, flip which side is smaller."
    ]

def scripts(job: JobSpec, style: str = "roll", fold_in: str = "right") -> Dict[str, str]:
    if not job.trim_size:
        w, h = 11.0, 8.5
    else:
        w, h = job.trim_size.w_in, job.trim_size.h_in
    length = max(w, h)
    panels = _trifold_panels(length, style=style, fold_in=fold_in)
    pos1 = round(panels[0]*72, 3)
    pos2 = round((panels[0]+panels[1])*72, 3)
    bleed = job.bleed_in or 0.125
    jsx = f"""
// add_trifold_guides.jsx
(function(){{
  var bleed = {bleed};
  var w = {w}, h = {h};
  if (app.documents.length === 0) {{
    var doc = app.documents.add(DocumentColorSpace.CMYK, w*72, h*72);
    doc.documentPreferences.documentBleedUniformSize = true;
    doc.documentPreferences.documentBleedTopOffset = bleed*72;
  }}
  var doc = app.activeDocument;
  function addV(x){{ var g = doc.guides.add(); g.orientation = Direction.VERTICAL; g.coordinate = x; }}
  addV({pos1}); addV({pos2});
}})();
"""
    return {"illustrator_jsx_trifold_guides": jsx}
