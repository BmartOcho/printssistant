from __future__ import annotations
from typing import List, Dict
from ..jobspec import JobSpec

def tips(job: JobSpec) -> List[str]:
    rb = "60C/40M/40Y/100K"
    return [
        "Work in CMYK; avoid placing RGB assets directly.",
        f"Use rich black ({rb}) for large solids/headlines; body text ≤18 pt should be 100K only and overprint.",
        "Check placed images’ effective PPI ≥300 for print (≥150 for wide-format).",
    ]

def scripts(job: JobSpec) -> Dict[str, str]:
    jsx_ai = f"""
// color_policies.jsx (Illustrator)
// 1) Ensure CMYK doc; 2) Add Rich Black swatch; 3) Set small 100K text to overprint
(function(){{
  function ensureCMYK(){{
    if (app.documents.length===0) return;
    app.executeMenuCommand("doc-color-cmyk");
  }}
  function addRichBlack(){{
    var doc = app.activeDocument;
    var sw = doc.swatches.getByName("Rich Black {job.special.get('rb','60/40/40/100')}");
    if (!sw){{
      var c = new CMYKColor(); c.cyan=60; c.magenta=40; c.yellow=40; c.black=100;
      var s = doc.swatches.add(); s.name = "Rich Black 60/40/40/100"; s.color = c;
    }}
  }}
  function overprintSmallBlackText(pt){{
    var doc = app.activeDocument;
    for (var i=0; i<doc.textFrames.length; i++) {{
      var tf = doc.textFrames[i];
      var r = tf.textRange;
      var ca = r.characterAttributes;
      if (ca.size <= pt) {{
        var c = ca.fillColor;
        if (c.typename === "CMYKColor" && c.cyan===0 && c.magenta===0 && c.yellow===0 && c.black===100) {{
          ca.overprintFill = true;
        }}
      }}
    }}
  }}
  if (app.documents.length>0) {{
    ensureCMYK(); addRichBlack(); overprintSmallBlackText(18);
  }}
}})();
"""
    jsx_ps = """
// convert_open_doc_to_cmyk.jsx (Photoshop)
(function(){
  if (app.documents.length === 0) { return; }
  var icc = "US Web Coated (SWOP) v2";
  app.activeDocument.convertProfile(icc, Intent.RELATIVECOLORIMETRIC, true, true);
})();
"""
    return {"illustrator_jsx_color": jsx_ai, "photoshop_jsx_cmyk": jsx_ps}
