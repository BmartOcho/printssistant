from __future__ import annotations
import json, re
import typer
from typing import Optional, List, Dict, Any

from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents, fold_preferences_from_message
from prepress_helper.skills import doc_setup
from prepress_helper.config_loader import load_shop_config, apply_shop_config

# Optional skills
try:
    from prepress_helper.skills import policy_enforcer  # type: ignore
except Exception:
    policy_enforcer = None  # type: ignore

try:
    from prepress_helper.skills import fold_math  # type: ignore
except Exception:
    fold_math = None  # type: ignore

try:
    from prepress_helper.skills import color_policy  # type: ignore
except Exception:
    color_policy = None  # type: ignore

# Optional ML (for debug meta only)
try:
    from prepress_helper.ml.product_classifier import predict_label  # type: ignore
except Exception:
    predict_label = None  # type: ignore

app = typer.Typer(add_completion=False, help="Printssistant CLI")
SHOP_CFG = load_shop_config("config")

def _canon_tip(t: str) -> str:
    s = t.strip().lower()
    s = re.sub(r"[.\s]+$", "", s)
    s = s.replace("use cmyk document color mode;", "work in cmyk;")
    s = s.replace("rgb assets not allowed—convert to cmyk before placing", "work in cmyk; avoid placing rgb assets directly")
    s = s.replace("≤", "<=")
    s = s.replace("-", "-")
    return s

def _dedupe_tips(tips: List[str]) -> List[str]:
    # Prefer shop-specific rich black if present
    has_shop_rb = any(t.lower().startswith("use shop rich black") for t in tips)
    out: List[str] = []
    seen: set[str] = set()
    for t in tips:
        if has_shop_rb and t.lower().startswith("rich black for large solids"):
            continue
        key = _canon_tip(t)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out

@app.command()
def parse_xml(xml: str, map: str):
    """Parse XML into a normalized JobSpec and print JSON."""
    js = load_jobspec_from_xml(xml, map)
    js = apply_shop_config(js, SHOP_CFG)
    typer.echo(json.dumps(js.model_dump(), indent=2))

@app.command()
def advise(
    jobspec: str,
    msg: Optional[str] = typer.Option(None, "--msg", help="Free text hint like 'trifold roll fold'"),
    fold: Optional[str] = typer.Option(None, "--fold", help="Override fold style: roll|z"),
    fold_in: Optional[str] = typer.Option(None, "--fold-in", help="Override which panel folds in: left|right"),
    debug_ml: bool = typer.Option(False, "--debug-ml", help="Include ML prediction/confidence when available"),
):
    """Given a JobSpec JSON file and options, print tips & scripts."""
    with open(jobspec, "r", encoding="utf-8") as f:
        raw = json.load(f)
    js = JobSpec(**raw)
    js = apply_shop_config(js, SHOP_CFG)

    intents = detect_intents(js, msg or "")

    tips: List[str] = []
    scripts: Dict[str, str] = {}

    # Always include basic doc setup
    tips += doc_setup.tips(js)
    scripts.update(doc_setup.scripts(js))

    # Fold math
    if "fold_math" in intents and fold_math:
        inf_style, inf_in = fold_preferences_from_message(msg or "")
        use_style = (fold or inf_style or "roll").lower()
        use_in = (fold_in or inf_in or "right").lower()
        tips += fold_math.tips(js, style=use_style, fold_in=use_in)  # type: ignore
        scripts.update(fold_math.scripts(js, style=use_style, fold_in=use_in))  # type: ignore

    # Color policy
    if "color_policy" in intents and color_policy:
        tips += color_policy.tips(js)  # type: ignore
        scripts.update(color_policy.scripts(js))  # type: ignore

    # Policy enforcer (TAC, shop rich black echo, RGB allowance, etc.)
    if policy_enforcer:
        tips += policy_enforcer.tips(js, msg or "")  # type: ignore
        scripts.update(policy_enforcer.scripts(js, msg or ""))  # type: ignore

    tips = _dedupe_tips(tips)
    out: Dict[str, Any] = {"intents": intents, "tips": tips, "scripts": scripts}

    if debug_ml and predict_label:
        pred = predict_label(js, msg or "")
        if pred:
            label, prob = pred
            out["meta"] = {"ml_prediction": label, "prob": round(prob, 4)}

    typer.echo(json.dumps(out, indent=2))

if __name__ == "__main__":
    app()
