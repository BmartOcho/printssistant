from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

def _dims(job: JobSpec) -> tuple[float, float]:
    if not job.trim_size:
        return (24.0, 18.0)
    return (float(job.trim_size.w_in), float(job.trim_size.h_in))

def _is_rgb_allowed(job: JobSpec) -> bool:
    # precedence: product preset -> press -> policies
    shop = (job.special or {}).get("shop", {})
    products = shop.get("products", {})
    presses = shop.get("presses", {})
    policies = shop.get("policies", {})

    # product preset (e.g., banner.allow_rgb)
    preset = (job.special or {}).get("product_preset") or products.get("banner")
    if isinstance(preset, dict) and "allow_rgb" in preset:
        return bool(preset["allow_rgb"])

    # press capability (if you later attach a press to job.special["press"])
    press_key = (job.special or {}).get("press")
    if press_key and press_key in presses:
        p = presses[press_key] or {}
        if "allow_rgb" in p:
            return bool(p["allow_rgb"])

    # policy fallback (default False)
    allow = policies.get("allow_rgb")
    return bool(allow) if allow is not None else False

def _min_ppi(job: JobSpec) -> int:
    shop = (job.special or {}).get("shop", {})
    products = shop.get("products", {})
    preset = (job.special or {}).get("product_preset") or products.get("banner")
    if isinstance(preset, dict) and "min_ppi" in preset:
        try:
            return int(preset["min_ppi"])
        except Exception:
            pass
    return 150

def _grommet(job: JobSpec) -> tuple[float|None, float|None]:
    shop = (job.special or {}).get("shop", {})
    products = shop.get("products", {})
    preset = (job.special or {}).get("product_preset") or products.get("banner", {})
    gm = None
    gs = None
    if isinstance(preset, dict):
        if "grommet_margin_in" in preset:
            try: gm = float(preset["grommet_margin_in"])
            except Exception: pass
        if "grommet_spacing_in" in preset:
            try: gs = float(preset["grommet_spacing_in"])
            except Exception: pass
    return gm, gs

def tips(job: JobSpec) -> List[str]:
    w, h = _dims(job)
    bleed = job.bleed_in or 0.0
    safety = job.safety_in or 0.25
    allow_rgb = _is_rgb_allowed(job)
    minppi = _min_ppi(job)
    gm, gs = _grommet(job)

    t: List[str] = [
        f"Set document to {w}×{h} in; bleed {bleed}\"; safety {safety}\".",
        ( "RGB assets allowed; embed sRGB/Adobe RGB and let the RIP handle conversion."
          if allow_rgb else
          "Work in CMYK; avoid placing RGB assets directly." ),
        f"For large-format output, aim for ≥ {minppi} PPI at final size (200+ if viewed close).",
    ]

    # ICC hint
    policies = ((job.special or {}).get("shop", {})).get("policies", {})
    icc = job.special.get("icc_profile") or policies.get("icc_profile")
    if icc:
        t.append(f"Use device/profile: {icc}.")

    # Grommet guidance
    if gm:
        t.append(f"Keep critical content ≥ {gm}\" from all edges (grommet/safe margin).")
    if gs:
        t.append(f"Plan grommets ~every {gs}\" along edges unless specified otherwise.")

    return t

def scripts(job: JobSpec) -> Dict[str, str]:
    w, h = _dims(job)
    bleed = job.bleed_in or 0.0
    safety = job.safety_in or 0.25
    gm, gs = _grommet(job)

    # Guides: safety rectangle via four guides; optional grommet-grid as vertical guides
    left  = round(safety*72, 3)
    right = round((w - safety)*72, 3)
    top   = round(safety*72, 3)
    bot   = round((h - safety)*72, 3)

    grom_js = ""
    if gs and gm is not None:
        # vertical guides across width at spacing from gm..(w-gm)
        start = gm
        end = max(gm, w - gm)
        xs = []
        x = start
        while x <= end:
            xs.append(round(x*72, 3))
            x += gs
        xs_str = ", ".join(str(v) for v in xs)
        grom_js = f"""
  // Grommet vertical guides
  var xs = [{xs_str}];
  for (var i=0;i<xs.length;i++){{ addV(xs[i]); }}
"""

    jsx = f"""
// wide_format_guides.jsx
(function(){{
  var w = {w}, h = {h}, bleed = {bleed}, safety = {safety};
  if (app.documents.length === 0) {{
    var doc = app.documents.add(DocumentColorSpace.CMYK, w*72, h*72);
    doc.documentPreferences.documentBleedUniformSize = true;
    doc.documentPreferences.documentBleedTopOffset = bleed*72;
  }}
  var doc = app.activeDocument;
  function addV(x){{ var g = doc.guides.add(); g.orientation = Direction.VERTICAL; g.coordinate = x; }}
  function addH(y){{ var g = doc.guides.add(); g.orientation = Direction.HORIZONTAL; g.coordinate = y; }}
  // Safety guides
  addV({left}); addV({right});
  addH({top});  addH({bot});{grom_js}
}})();
"""
    return {"illustrator_jsx_wide_format_guides": jsx}
