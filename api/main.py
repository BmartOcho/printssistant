
from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import json, tempfile, os
from pydantic import BaseModel
from src.prepress_helper.jobspec import JobSpec
from src.prepress_helper.xml_adapter import load_jobspec_from_xml
from src.prepress_helper.router import detect_intents
from src.prepress_helper.skills import doc_setup

app = FastAPI(title="Prepress Helper API", version="0.0.1")

class AdviseRequest(BaseModel):
    jobspec: JobSpec
    message: str | None = None

@app.post("/parse_xml")
async def parse_xml(xml: UploadFile = File(...), mapping_path: str = Form(...)):
    # mapping_path should point to a server-side file like "config/xml_map.yml"
    with tempfile.TemporaryDirectory() as td:
        xml_path = os.path.join(td, xml.filename)
        with open(xml_path, "wb") as f:
            f.write(await xml.read())
        js = load_jobspec_from_xml(xml_path, mapping_path)
        return JSONResponse(js.model_dump())

@app.post("/advise")
async def advise(req: AdviseRequest):
    intents = detect_intents(req.jobspec, req.message or "")
    # MVP: only doc_setup
    tips = doc_setup.tips(req.jobspec)
    scripts = doc_setup.scripts(req.jobspec)
    return {"intents": intents, "tips": tips, "scripts": scripts}
