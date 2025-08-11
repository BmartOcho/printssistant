from __future__ import annotations
import json
import typer
from typing import Optional, List, Dict

from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents
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

@app.command()
def parse_xml(xml: str, map: str):
    """Parse XML into a normalized JobSpec and print JSON."""
    js = load_jobspec_from_xml(xml, map)
    typer.echo(json.dumps(js.model_dump(), indent=2))

@app.command()
def advise(jobspec: str, msg: Optional[str] = typer.Option(None, "--msg")):
    """Given a JobSpec JSON file and optional message, print tips & scripts."""
    with open(jobspec, "r", encoding="utf-8") as f:
        raw = json.load(f)
    js = JobSpec(**raw)

    intents = detect_intents(js, msg or "")

    tips: List[str] = []
    scripts: Dict[str, str] = {}

    # Always include basic setup
    tips += doc_setup.tips(js)
    scripts.update(doc_setup.scripts(js))

    # Add fold math if routed
    if "fold_math" in intents and fold_math:
        tips += fold_math.tips(js)  # type: ignore
        scripts.update(fold_math.scripts(js))  # type: ignore

    # Add color policy if routed
    if "color_policy" in intents and color_policy:
        tips += color_policy.tips(js)  # type: ignore
        scripts.update(color_policy.scripts(js))  # type: ignore

    typer.echo(json.dumps({"intents": intents, "tips": tips, "scripts": scripts}, indent=2))

if __name__ == "__main__":
    app()
