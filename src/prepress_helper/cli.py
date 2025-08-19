from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import typer

from prepress_helper.config_loader import apply_shop_config, load_shop_config
from prepress_helper.jobspec import JobSpec
from prepress_helper.router import detect_intents, fold_preferences_from_message
from prepress_helper.skills import doc_setup
from prepress_helper.xml_adapter import load_jobspec_from_xml

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


def _uniq(seq: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in seq:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def _read_json_auto(path: str) -> Any:
    """Read JSON allowing UTF-8/UTF-8 BOM/UTF-16 LE/BE."""
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
        text = data.decode("utf-8-sig")
    elif data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):  # UTF-16
        text = data.decode("utf-16")
    else:
        text = data.decode("utf-8")
    return json.loads(text)


def _dedupe_nags(lines: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in lines:
        norm = s.strip().lower()
        if norm not in seen:
            out.append(s)
            seen.add(norm)
    return out


def _dedupe_tips(tips: List[str]) -> List[str]:
    """
    De-duplicate tips and apply preferred phrasing:
      - Prefer 'Set document to ...' over 'Create a document at ...'
      - Prefer 'RGB assets allowed...' over CMYK admonitions
      - Prefer 'Use shop rich black...' over generic 'Rich black ...'
      - Collapse duplicate CMYK admonitions (e.g. 'Use CMYK...' vs 'Work in CMYK...')
    """
    lower = [t.strip().lower() for t in tips]
    has_set_document = any("set document to" in t for t in lower)
    has_rgb_allowed = any("rgb assets allowed" in t for t in lower)
    has_shop_rich = any("use shop rich black" in t for t in lower)

    out: List[str] = []
    seen: set[str] = set()
    seen_rgb_admon = False  # collapse variations that contain 'avoid placing rgb assets directly'

    for s in tips:
        key = s.strip().lower()
        if key in seen:
            continue

        if has_set_document and "create a document at" in key:
            continue

        if "avoid placing rgb assets directly" in key:
            if has_rgb_allowed:
                # If RGB is allowed, drop admonitions entirely
                continue
            # Otherwise, keep only the first admonition we encounter
            if seen_rgb_admon:
                continue
            seen_rgb_admon = True

        if has_shop_rich and ("rich black" in key) and ("use shop rich black" not in key):
            continue

        out.append(s)
        seen.add(key)

    return out


@app.command()
def parse_xml(
    xml: str,
    map: str,
    out: Optional[str] = typer.Option(
        None,
        "--out",
        help="Write UTF-8 JSON to this path (avoids shell redirection encoding issues).",
    ),
):
    """Parse XML into a normalized JobSpec and print JSON (or write to --out)."""
    js = load_jobspec_from_xml(xml, map)
    js = apply_shop_config(js, SHOP_CFG)
    payload = json.dumps(js.model_dump(), indent=2)

    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        typer.echo(payload)


@app.command()
def advise(
    jobspec: str,
    msg: Optional[str] = typer.Option(None, "--msg", help="Free text hint like 'trifold roll fold'"),
    fold: Optional[str] = typer.Option(None, "--fold", help="Override fold style: roll|z"),
    fold_in: Optional[str] = typer.Option(None, "--fold-in", help="Override which panel folds in: left|right"),
    debug_ml: bool = typer.Option(False, "--debug-ml", help="Include ML prediction/confidence when available"),
):
    """Given a JobSpec JSON file and options, print tips & scripts."""
    raw = _read_json_auto(jobspec)
    js = JobSpec(**raw)
    js = apply_shop_config(js, SHOP_CFG)

    intents = detect_intents(js, msg or "")
    tips: List[str] = []
    scripts: Dict[str, str] = {}
    nags: List[str] = []

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

    # Soft nags
    if policy_enforcer and hasattr(policy_enforcer, "soft_nags"):
        try:
            extra = policy_enforcer.soft_nags(js) or []  # type: ignore[attr-defined]
            nags.extend(extra)
        except Exception:
            pass

    # Apply de-dupers
    tips = _dedupe_tips(tips)
    nags = _dedupe_nags(nags)

    out: Dict[str, Any] = {"intents": intents, "tips": tips, "scripts": scripts}
    if nags:
        out["nags"] = nags

    if debug_ml and predict_label:
        pred = predict_label(js, msg or "")
        if pred:
            label, prob = pred
            out["meta"] = {"ml_prediction": label, "prob": round(prob, 4)}

    typer.echo(json.dumps(out, indent=2))


if __name__ == "__main__":
    app()
