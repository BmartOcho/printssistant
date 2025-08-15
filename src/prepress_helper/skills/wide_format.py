from __future__ import annotations
from typing import List, Dict, Tuple
from ..jobspec import JobSpec

def _dims(job: JobSpec) -> Tuple[float, float]:
    if not job.trim_size:
        return (24.0, 18.0)
    return (float(job.trim_size.w_in), float(job.trim_size.h_in))

def _get_shop(job: JobSpec) -> Dict:
    return (job.special or {}).get("shop", {})

def _get_preset(job: JobSpec) -> Dict:
    shop = _get_shop(job)
    products = shop.get("products", {})
    preset = (job.special or {}).get("product_preset")
    if isinstance(preset, dict):
        return preset
    return products.get("banner", {}) if isinstance(products.get("banner", {}), dict) else {}

def _is_rgb_allowed(job: JobSpec) -> bool:
    # precedence: product preset -> press -> policies
    shop = _get_shop(job)
    presses = shop.get("presses", {})
    policies = shop.get("policies", {})
    preset = _get_preset(job)

    if "allow_rgb" in preset:
        return bool(preset["allow_rgb"])

    press_key = (job.special or {}).get("press")
    if press_key and press_key in presses and "allow_rgb" in presses[press_key]:
        return bool(presses[press_key]["allow_rgb"])

    allow = policies.get("allow_rgb")
    return bool(allow) if allow is not None else False

def _min_ppi(job: JobSpec) -> int:
    preset = _get_preset(job)
    try:
        return int(preset.get("min_ppi", 150))
    except Exception:
        return 150

def _grommet(job: JobSpec) -> Tuple[float|None, float|None]:
    preset = _get_preset(job)
    gm = None; gs = None
    if "grommet_margin_in" in preset:
        try: gm = float(preset["grommet_margin_in"])
        except Exception: pass
    if "grommet_spacing_in" in preset:
        try: gs = float(preset["grommet_spacing_in"])
        except Exception: pass
    return gm, gs

def _icc(job: JobSpec) -> str|None:
    # precedence: product preset -> job.special -> policies
    preset = _get_preset(job)
    if "icc_profile" in preset and preset["icc_profile"]:
        return str(preset["icc_profile"])
    shop = _get_shop(job)
    policies = shop.get("policies", {})
    return (job.special or {}).get("icc_profile") or policies.get("icc_profile")

def tips(job: JobSpec) -> List[str]:
    w, h = _dims(job)
    bleed = job.bleed_in or 0.0
    safety = job.safety_in or 0.25
    allow_rgb = _is_rgb_allowed(job)
    minppi = _min_ppi(job)
    gm, gs = _grommet(job)

    t: List[str] = [
        f"Set document to {w}×{h} in; bleed {bleed}\"; safety {safety}\".",
        ("RGB assets allowed; embed sRGB/Adobe RGB and let the RIP handle conversion."
         if allow_rgb else
         "Work in CMYK; avoid placing RGB assets directly."),
        f"For large-format output, aim for ≥ {minppi} PPI at final size (200+ if viewed close).",
    ]

    icc = _icc(job)
    if icc:
        t.append(f"Use device/profile: {icc}.")

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

    # Safety guides
    left  = round(safety*72, 3)
    right = round((w - safety)*72, 3)
    top   = round(safety*72, 3)
    bot   = round((h - safety)*72, 3)

    grom_vert = ""
    grom_horz = ""
    if gs and gm is not None:
        # vertical positions
        xs = []
        x = gm
        endx = max(gm, w - gm)
        while x <= endx + 1e-6:
            xs.append(round(x*72, 3))
            x += gs
        # horizontal positions
        ys = []
        y = gm
        endy = max(gm, h - gm)
        while y <= endy + 1e-6:
            ys.append(round(y*72, 3))
            y += gs

        xs_str = ", ".join(str(v) for v in xs)
        ys_str = ", ".join(str(v) for v in ys)
        grom_vert = f"""
  // Grommet vertical guides
  var xs = [{xs_str}];
  for (var i=0;i<xs.length;i++){{ addV(xs[i]); }}"""
        grom_horz = f"""
  // Grommet horizontal guides
  var ys = [{ys_str}];
  for (var j=0;j<ys.length;j++){{ addH(ys[j]); }}"""

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
  addH({top});  addH({bot});{grom_vert}{grom_horz}
}})();
"""
    return { "illustrator_jsx_wide_format_guides": jsx }
