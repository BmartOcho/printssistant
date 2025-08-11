from __future__ import annotations
import json
import typer
from typing import Optional
from prepress_helper.jobspec import JobSpec
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents
from prepress_helper.skills import doc_setup

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
    tips = doc_setup.tips(js)
    scripts = doc_setup.scripts(js)
    typer.echo(json.dumps({"intents": intents, "tips": tips, "scripts": scripts}, indent=2))

if __name__ == "__main__":
    app()
