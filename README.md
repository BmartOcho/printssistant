
# Prepress Helper (MVP)

A real-time, app-agnostic assistant for prepress & design teams. It ingests **job XML** and short **user prompts**, normalizes details into a `JobSpec`, and returns **contextual tips** plus **ready-to-run scripts** (e.g., Illustrator/Photoshop JSX). Think *“Clippy for prepress”*—but grounded in your shop’s policies.

> **License:** No license (all rights reserved) for now. You control distribution.
>
> **Scope:** PDF preflight is out-of-scope for the MVP (tools like PitStop already do this well). This project focuses on guidance, playbooks, and scripts based on XML + user input.

## Quickstart

### 1) Environment
- Python 3.11+
- Create & activate a venv
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2) Install (editable)
```bash
pip install -e .
```

### 3) Run the API
```bash
uvicorn api.main:app --reload
```
- Swagger UI: http://localhost:8000/docs

### 4) Try the CLI
```bash
prepress-helper parse-xml --xml sample_job.xml --map config/xml_map.yml
prepress-helper advise --jobspec sample_jobspec.json --msg "Set up a trifold brochure"
```

## Repository layout
```
src/prepress_helper/         # Core library
  jobspec.py                 # Pydantic model for normalized job data
  xml_adapter.py             # Configurable XML → JobSpec via YAML + XPath
  router.py                  # Intent detection & skill routing
  skills/                    # Small, focused helpers that emit tips/scripts
    doc_setup.py             # Example skill: artboard/bleed/fold guides
  kb/                        # Knowledge base (SOPs/playbooks)
    sample_policies/         # Example markdown policies
api/main.py                  # FastAPI app exposing /parse_xml and /advise
cli/main.py                  # Typer CLI for local workflows
config/xml_map.yml           # Example mapping from shop XML to JobSpec fields
```

## Roadmap (MVP → v0.1)
- [ ] Expand skills: `fold_math`, `color_policy`, `automation_scripts`
- [ ] KB-backed answers (RAG) using your SOP markdown
- [ ] Script parameterization (ICC, sizes) from `JobSpec`
- [ ] Telemetry on accepted/ignored tips (privacy-respecting)
- [ ] Adapter packs for alternate shop XMLs

## Contributing (internal)
- Keep `main` protected. Use feature branches + PRs.
- Follow Conventional Commits (e.g., `feat: add fold math skill`).
- Run `pytest` before submitting PRs.

---

**Note on No License:** This repo is currently *closed-source by default.* Others cannot legally use/modify/distribute the code without your permission. You can add a license later (MIT/Apache/GPL) if you decide to open it.
