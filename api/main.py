from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import tempfile, os

from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents, fold_preferences_from_message
from prepress_helper.skills import doc_setup
from prepress_helper.config_loader import load_shop_config, apply_shop_config

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
SHOP_CFG = load_shop_config("config")

class AdviseRequest(BaseModel):
    jobspec: JobSpec
    message: str | None = None
    debug_ml: bool = False

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
        js = apply_shop_config(js, SHOP_CFG)
        return JSONResponse(js.model_dump())

@app.post("/advise")
async def advise(req: AdviseRequest):
    js = apply_shop_config(req.jobspec, SHOP_CFG)
    intents = detect_intents(js, req.message or "")
    tips = doc_setup.tips(js)
    scripts = doc_setup.scripts(js)

    if "fold_math" in intents and fold_math:
        style, fin = fold_preferences_from_message(req.message or "")
        tips += fold_math.tips(js, style=style, fold_in=fin)  # type: ignore
        scripts.update(fold_math.scripts(js, style=style, fold_in=fin))  # type: ignore

    if "color_policy" in intents and color_policy:
        tips += color_policy.tips(js)  # type: ignore
        scripts.update(color_policy.scripts(js))  # type: ignore

    seen=set(); tips2=[]
    for t in tips:
        if t not in seen:
            tips2.append(t); seen.add(t)

    out = {"intents": intents, "tips": tips2, "scripts": scripts}

    # optional ML debug
    try:
        from prepress_helper.ml.product_classifier import predict_label  # type: ignore
        if req.debug_ml:
            pred = predict_label(js, req.message or "")
            if pred:
                out["meta"] = {"ml_prediction": pred[0], "prob": round(pred[1], 4)}
    except Exception:
        pass

    return out
