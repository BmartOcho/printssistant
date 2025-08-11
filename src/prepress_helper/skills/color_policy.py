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
    jsx_ai = """
// color_policies.jsx (Illustrator)
(function(){
  if (app.documents.length===0) return;
  app.executeMenuCommand("doc-color-cmyk"); // ensure CMYK
  // Add Rich Black swatch if missing
  var doc = app.activeDocument;
  function has(name){ try{ doc.swatches.getByName(name); return true;}catch(e){return false;} }
  if (!has("Rich Black 60/40/40/100")){
    var c = new CMYKColor(); c.cyan=60; c.magenta=40; c.yellow=40; c.black=100;
    var s = doc.swatches.add(); s.name="Rich Black 60/40/40/100"; s.color=c;
  }
  // Overprint small 100K text
  for (var i=0;i<doc.textFrames.length;i++){
    var r = doc.textFrames[i].textRange;
    var ca = r.characterAttributes;
    if (ca.size <= 18){
      var k = (ca.fillColor.typename==="CMYKColor") && ca.fillColor.cyan===0 && ca.fillColor.magenta===0 && ca.fillColor.yellow===0 && ca.fillColor.black===100;
      if (k){ ca.overprintFill = true; }
    }
  }
})();
"""
    jsx_ps = """
// convert_open_doc_to_cmyk.jsx (Photoshop)
(function(){
  if (app.documents.length === 0) return;
  var icc = "US Web Coated (SWOP) v2";
  app.activeDocument.convertProfile(icc, Intent.RELATIVECOLORIMETRIC, true, true);
})();
"""
    return {"illustrator_jsx_color": jsx_ai, "photoshop_jsx_cmyk": jsx_ps}
