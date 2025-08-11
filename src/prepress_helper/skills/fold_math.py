from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

INCH = 1.0

def _axis(job: JobSpec) -> tuple[str, float]:
    """Return ('width'|'height', length_in) for the folding axis."""
    if not job.trim_size:
        return ("width", 0.0)
    w, h = job.trim_size.w_in, job.trim_size.h_in
    # Heuristic: most tri-folds fold along the longer edge
    return ("width", max(w, h))

def _trifold_panels(total: float, style: str = "roll", fold_in: str = "right") -> List[float]:
    """
    Compute tri-fold panel widths along the folding axis.
    - style: 'roll' (two equal outer panels, fold-in panel 1/16" shorter) or 'z' (equal thirds)
    - fold_in: which panel folds in for roll-fold ('left'|'right'). Controls which panel is smaller.
    """
    if style == "z":
        third = round(total / 3.0, 4)
        return [third, third, third]

    # roll-fold default: two equal outers (O), one fold-in (I = O - 1/16")
    # 2*O + I = total ; I = O - 1/16  =>  3*O - 1/16 = total  => O = (total + 1/16)/3
    outer = round((total + (1.0/16.0)) / 3.0, 4)
    inner = round(outer - (1.0/16.0), 4)
    if fold_in == "left":
        return [inner, outer, outer]
    else:
        return [outer, outer, inner]

def tips(job: JobSpec, style: str = "roll", fold_in: str = "right") -> List[str]:
    axis, length = _axis(job)
    if length < 8.0:  # unlikely a tri-fold; avoid nonsense on business cards, etc.
        return [
            "This job’s finished size looks too small for a tri-fold. Confirm product type and dimensions before placing fold guides."
        ]
    panels = _trifold_panels(length, style=style, fold_in=fold_in)
    bleed = job.bleed_in or 0.125
    safety = job.safety_in or 0.125
    return [
        f"Tri-fold ({style}) along {axis}: panel widths ≈ {', '.join(f'{p:.4g}\"' for p in panels)} (total {length}\").",
        f"Add fold guides at cumulative positions: {', '.join(f'{p:.4g}\"' for p in [panels[0], panels[0]+panels[1]])}.",
        f"Use {bleed}\" bleed and keep type {safety}\" from folds and trim.",
        "If the panel that folds inside is opposite, swap which side is the smaller panel.",
    ]

def scripts(job: JobSpec, style: str = "roll", fold_in: str = "right") -> Dict[str, str]:
    # Build Illustrator JSX that adds guides at fold positions for the current artboard.
    axis, length = _axis(job)
    if not job.trim_size:
        w, h = 11.0, 8.5
    else:
        w, h = job.trim_size.w_in, job.trim_size.h_in
    panels = _trifold_panels(max(w, h), style=style, fold_in=fold_in)
    pos1 = round(panels[0] * 72, 3)
    pos2 = round((panels[0] + panels[1]) * 72, 3)
    bleed = job.bleed_in or 0.125

    jsx = f"""
// add_trifold_guides.jsx
(function(){{
  var bleed = {bleed}; // inches
  var w = {w}, h = {h}; // inches
  if (app.documents.length === 0) {{
    var doc = app.documents.add(DocumentColorSpace.CMYK, w*72, h*72);
    doc.documentPreferences.documentBleedUniformSize = true;
    doc.documentPreferences.documentBleedTopOffset = bleed*72;
  }}
  var doc = app.activeDocument;
  function addV(x){{
    var g = doc.guides.add();
    g.orientation = Direction.VERTICAL;
    g.coordinate = x;
  }}
  // Fold guides at {panels[0]:.4f}", {panels[0]+panels[1]:.4f}"
  addV({pos1});
  addV({pos2});
}})();
"""
    return {"illustrator_jsx": jsx}
