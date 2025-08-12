from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

def tips(job: JobSpec) -> List[str]:
    shop = (job.special or {}).get("shop", {})
    policies = shop.get("policies", {})
    tac = policies.get("max_ink_coverage") or job.special.get("max_ink_coverage")
    t: List[str] = [
        "Work in CMYK; avoid placing RGB assets directly.",
        "Body text ≤ 18 pt: 100K only and set to overprint.",
        "Aim for effective 300 PPI on placed images (150+ for wide-format).",
    ]
    if tac:
        t.append(f"Keep total area coverage (TAC) ≤ {tac}%. Large solids should respect TAC limits.")
    rb = (
        job.special.get("rich_black")
        or policies.get("sleek_black")
        or policies.get("rich_black")
        or "60/40/40/100"
    )
    t.insert(1, f"Rich black for large solids/headlines: {rb}.")
    icc = job.special.get("icc_profile") or policies.get("icc_profile")
    if icc:
        t.append(f"Use shop ICC: {icc}.")
    return t

def scripts(job: JobSpec) -> Dict[str, str]:
    shop = (job.special or {}).get("shop", {})
    policies = shop.get("policies", {})
    rb = (
        job.special.get("rich_black")
        or policies.get("sleek_black")
        or policies.get("rich_black")
        or "60/40/40/100"
    )
    icc = job.special.get("icc_profile") or policies.get("icc_profile", "US Web Coated (SWOP) v2")
    small_pt = job.special.get("small_text_pt") or policies.get("small_text_pt", 18)
    try:
        c, m, y, k = [int(x) for x in rb.replace("%","").split("/")]
    except Exception:
        c, m, y, k = 60, 40, 40, 100

    jsx_ai = f"""
// color_policies.jsx (Illustrator)
(function(){{
  if (app.documents.length===0) return;
  app.executeMenuCommand("doc-color-cmyk");
  var doc = app.activeDocument;
  function has(n){{ try{{ doc.swatches.getByName(n); return true; }}catch(e){{ return false; }} }}
  var name = "Rich Black {c}/{m}/{y}/{k}";
  if (!has(name)) {{
    var col = new CMYKColor(); col.cyan={c}; col.magenta={m}; col.yellow={y}; col.black={k};
    var s = doc.swatches.add(); s.name = name; s.color = col;
  }}
  for (var i=0;i<doc.textFrames.length;i++) {{
    var r = doc.textFrames[i].textRange, ca=r.characterAttributes;
    if (ca.size <= {small_pt}) {{
      var fc = ca.fillColor;
      var is100K = (fc.typename==="CMYKColor" && fc.cyan===0 && fc.magenta===0 && fc.yellow===0 && fc.black===100);
      if (is100K) ca.overprintFill = true;
    }}
  }}
}})();
"""
    jsx_ps = f"""
// convert_open_doc_to_cmyk.jsx (Photoshop)
(function(){{
  if (app.documents.length === 0) return;
  var icc = "{icc}";
  app.activeDocument.convertProfile(icc, Intent.RELATIVECOLORIMETRIC, true, true);
}})();
"""
    return {"illustrator_jsx_color": jsx_ai, "photoshop_jsx_cmyk": jsx_ps}
