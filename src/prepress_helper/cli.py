from __future__ import annotations
import json
import typer
from typing import Optional, Annotated, List, Dict
from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents
from prepress_helper.skills import doc_setup
from prepress_helper.skills import fold_math
from prepress_helper.skills import color_policy #NEW

app = typer.Typer(add_completion=False, help="Printssistant CLI")

@app.command()
def parse_xml(xml: str, map: str):
    js = load_jobspec_from_xml(xml, map)
    typer.echo(json.dumps(js.model_dump(), indent=2))

@app.command()
def advise(jobspec: str, msg: Optional[str] = typer.Option(None, "--msg")):
    with open(jobspec, "r", encoding="utf-8") as f:
        raw = json.load(f)
    js = JobSpec(**raw)
    intents = detect_intents(js, msg or "")
    tips: List[str] = []
    scripts: Dict[str, str] = {}
    # Always include basic doc setup
    tips += doc_setup.tips(js)
    scripts.update(doc_setup.scripts(js))
    # Fold math when requested
    if "fold_math" in intents:
        tips += fold_math.tips(js)
        scripts.update(fold_math.scripts(js))
    typer.echo(json.dumps({"intents": intents, "tips": tips, "scripts": scripts}, indent=2))

if "color_policy" in intents:
    tips += color_policy.tips(js)
    scripts.update(color_policy.scripts(js))

if __name__ == "__main__":
    app()
