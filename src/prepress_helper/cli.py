from __future__ import annotations
import json
import typer
from typing import Optional, List, Dict

from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents, fold_preferences_from_message
from prepress_helper.skills import doc_setup

# Optional skills (import if present)
try:
    from prepress_helper.skills import fold_math  # type: ignore
except Exception:
    fold_math = None  # type: ignore

try:
    from prepress_helper.skills import color_policy  # type: ignore
except Exception:
    color_policy = None  # type: ignore

app = typer.Typer(add_completion=False, help="Printssistant CLI")

def _uniq(seq: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in seq:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out

@app.command()
def parse_xml(xml: str, map: str):
    """Parse XML into a normalized JobSpec and print JSON."""
    js = load_jobspec_from_xml(xml, map)
    typer.echo(json.dumps(js.model_dump(), indent=2))

@app.command()
def advise(
    jobspec: str,
    msg: Optional[str] = typer.Option(None, "--msg", help="Free text hint like 'trifold roll fold'"),
    fold: Optional[str] = typer.Option(None, "--fold", help="Override fold style: roll|z"),
    fold_in: Optional[str] = typer.Option(None, "--fold-in", help="Override which panel folds in: left|right"),
    policy: Optional[str] = typer.Option(None, "--policy", help="Path to policies.yml"),
):
    """Given a JobSpec JSON file and options, print tips & scripts."""
    import yaml

    with open(jobspec, "r", encoding="utf-8") as f:
        raw = json.load(f)
    js = JobSpec(**raw)

    # Optional policies.yml → js.special
    if policy:
        with open(policy, "r", encoding="utf-8") as pf:
            pol = yaml.safe_load(pf) or {}
        if isinstance(pol, dict):
            js.special.update(pol)  # type: ignore

    intents = detect_intents(js, msg or "")

    tips: List[str] = []
    scripts: Dict[str, str] = {}

    # Always include basic doc setup
    tips += doc_setup.tips(js)
    scripts.update(doc_setup.scripts(js))

    # Fold math (if routed)
    if "fold_math" in intents and fold_math:
        # infer from message, allow CLI options to override
        inf_style, inf_in = fold_preferences_from_message(msg or "")
        use_style = (fold or inf_style or "roll").lower()
        use_in = (fold_in or inf_in or "right").lower()
        tips += fold_math.tips(js, style=use_style, fold_in=use_in)  # type: ignore
        scripts.update(fold_math.scripts(js, style=use_style, fold_in=use_in))  # type: ignore

    # Color policy (if routed)
    if "color_policy" in intents and color_policy:
        tips += color_policy.tips(js)  # type: ignore
        scripts.update(color_policy.scripts(js))  # type: ignore

    # De-dupe overlapping messages
    tips = _uniq(tips)
    typer.echo(json.dumps({"intents": intents, "tips": tips, "scripts": scripts}, indent=2))

if __name__ == "__main__":
    app()
