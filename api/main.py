from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json, tempfile, os

from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents
from prepress_helper.skills import doc_setup

# Optional skills
try:
    from prepress_helper.skills import fold_math  # type: ignore
except Exception:
    fold_math = None  # type: ignore

try:
    from prepress_helper.skills import color_policy  # type: ignore
except Exception:
    color_policy = None  # type: ignore

app = FastAPI(title="Printssistant API", version="0.0.1")

class AdviseRequest(BaseModel):
    jobspec: JobSpec
    message: str | None = None

@app.get("/")
def root():
    return {"status": "ok", "service": "printssistant", "docs": "/docs"}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/parse_xml")
async def parse_xml(xml: UploadFile = File(...), mapping_path: str = Form(...)):
    with tempfile.TemporaryDirectory() as td:
        xml_path = os.path.join(td, xml.filename)
        with open(xml_path, "wb") as f:
            f.write(await xml.read())
        js = load_jobspec_from_xml(xml_path, mapping_path)
        return JSONResponse(js.model_dump())

@app.post("/ingest")
async def ingest(xml: UploadFile = File(...), mapping_path: str = Form(...)):
    with tempfile.TemporaryDirectory() as td:
        xml_path = os.path.join(td, xml.filename)
        with open(xml_path, "wb") as f:
            f.write(await xml.read())
        js = load_jobspec_from_xml(xml_path, mapping_path)
        return js.model_dump()

@app.post("/advise")
async def advise(req: AdviseRequest):
    intents = detect_intents(req.jobspec, req.message or "")
    tips = doc_setup.tips(req.jobspec)
    scripts = doc_setup.scripts(req.jobspec)

    # Fold math
    if "fold_math" in intents and fold_math:
        from prepress_helper.router import fold_preferences_from_message
        style, fin = fold_preferences_from_message(req.message or "")
        tips += fold_math.tips(req.jobspec, style=style, fold_in=fin)  # type: ignore
        scripts.update(fold_math.scripts(req.jobspec, style=style, fold_in=fin))  # type: ignore

    # Color policy
    if "color_policy" in intents and color_policy:
        tips += color_policy.tips(req.jobspec)  # type: ignore
        scripts.update(color_policy.scripts(req.jobspec))  # type: ignore

    # de-dupe
    seen=set(); tips2=[]
    for t in tips:
        if t not in seen:
            tips2.append(t); seen.add(t)

    return {"intents": intents, "tips": tips2, "scripts": scripts}
