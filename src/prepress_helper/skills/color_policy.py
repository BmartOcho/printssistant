from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

def tips(job: JobSpec) -> List[str]:
    return [
        "Work in CMYK; avoid placing RGB assets directly.",
        "Rich black for large solids/headlines: 60C/40M/40Y/100K.",
        "Body text ≤ 18 pt: 100K only and set to overprint.",
        "Aim for effective 300 PPI on placed images (150+ for wide-format).",
    ]

def scripts(job: JobSpec) -> Dict[str, str]:
    rb = job.special.get("rich_black", "60/40/40/100")
    try:
        c, m, y, k = [int(x) for x in rb.replace("%", "").split("/")]
    except Exception:
        c, m, y, k = 60, 40, 40, 100
    icc = job.special.get("icc_profile", "US Web Coated (SWOP) v2")
    small_pt = job.special.get("small_text_pt", 18)

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
