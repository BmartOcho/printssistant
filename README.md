Prepress Helper (MVP)

A real-time, app-agnostic assistant for prepress & design teams. It ingests job XML and short user prompts, normalizes details into a JobSpec, and returns contextual tips + ready-to-run scripts (e.g., Illustrator JSX). Think “Clippy for prepress,” grounded in your shop’s policies.

License: No license (all rights reserved) for now.
Scope: PDF preflight is out-of-scope for the MVP (PitStop covers this). Focus here is guidance, playbooks, and scripts from XML + user input.

What’s new / important

CWD-proof config loader (works from any working dir; also supports packaged config via importlib.resources).

ASCII-only tips (no more mojibake in PowerShell).

Imposition mapping fixed: map ImposeAcross/ImposeDown separately; loader recombines to "AxB" and drops imposition_down.

Wide-format detection improved (treats max_width_in and substrates as wide please advise on setupsignals).

24/24 tests passing on Windows (Py 3.11/3.12).

Quickstart

SPIN UP EVERYTHING:
cd "C:\Users\Benjamin\Desktop\Python Apps\printssistant"
powershell -ExecutionPolicy Bypass -File .\dev-up.ps1


PUSH TO GITHUB FROM POWERSHELL
    git add .
This command stages all modified and new files in your current directory for the next commit. You can also specify individual files or folders instead of . to stage only specific changes. Commit your staged changes.
Code

    git commit -m "Your descriptive commit message"
Replace "Your descriptive commit message" with a concise and meaningful message describing the changes you made.
Push your committed changes to the remote GitHub repository:
Code

    git push origin main


1) Environment

Python 3.11–3.12 recommended.

Windows (PowerShell):

cd "C:\Users\<you>\Desktop\Python Apps\printssistant"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"


macOS/Linux (bash):

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"


-e ".[dev]" installs the project editable plus dev deps (pytest, httpx, etc.).
Seeing -e git+https://github.com/...#egg=printssistant in pip freeze is normal for editable installs.

2) Run the API (use the venv’s Python)
python -m uvicorn api.main:app --reload


Swagger UI: http://127.0.0.1:8000/docs

Tip: avoid bare uvicorn (which might use a global interpreter). Prefer python -m uvicorn ….

3) Hit the endpoints

Open two terminals:

A (server): runs Uvicorn (leave it running).

B (client): send requests.

Parse XML → JobSpec

# from project root; replace the XML path if needed
curl.exe -X POST "http://127.0.0.1:8000/parse_xml" `
  -F "xml=@samples/J208823.xml" `
  -F "mapping_path=config/xml_map.yml"


Advise (POST /advise) — PowerShell-native:

$body = @'
{
  "jobspec": {
    "product": "Cairn Business Card (Single Community)",
    "trim_size": {"w_in": 3.5, "h_in": 2.0},
    "bleed_in": 0.125,
    "safety_in": 0.25,
    "pages": 2,
    "colors": {"front":"CMYK","back":"No Printing"},
    "stock": "130# Pro Digital Silk Cover",
    "imposition_hint": "Flat Product",
    "special": {
      "imposition_across": "4x5",
      "machine": "hp_latex_570"
    }
  },
  "message": "please advise on setup",
  "debug_ml": false
}
'@

Invoke-RestMethod -Uri "http://127.0.0.1:8000/advise" -Method Post `
  -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 6


Console encoding: if you ever see funny symbols (e.g., â¤), normalize PowerShell:

chcp 65001 | Out-Null
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)


(We also normalized tips to ASCII, so you likely won’t need this.)

Config & mapping

Mapping file: config/xml_map.yml
Use separate fields; the loader recombines to "AxB" and removes the separate down key.

special.imposition_across: "string((//ImposeAcross)[1])"
special.imposition_down:   "string((//ImposeDown)[1])"


If the XML doesn’t contain Across/Down, the loader falls back to a robust text/attribute scan and may produce a best-effort "AxB". In that case, “orientation” is inferred—update goldens accordingly.

Shop config is loaded once and injected into the router:

# api/main.py
from prepress_helper.router import set_shop_cfg
SHOP_CFG = load_shop_config("config")
set_shop_cfg(SHOP_CFG)

Repo layout
src/prepress_helper/         # core library
  jobspec.py                 # pydantic model (extra=ignore, ASCII normalizers)
  xml_adapter.py             # XML → JobSpec via YAML; robust imposition handling
  router.py                  # intent detection; set_shop_cfg(); wide-format signals
  skills/
    doc_setup.py             # ASCII tips; Illustrator JSX scaffold
api/main.py                  # FastAPI app (/parse_xml, /advise)
config/xml_map.yml           # XPath mapping (per shop XML)
tests/                       # unit tests + goldens

Tests

Run all tests:

python -m pytest -q


Focused test:

python -m pytest -q -k test_parse_card_matches_golden


When XML lacks Across/Down and a golden assumes an orientation, regenerate that golden from the current loader:

@"
from prepress_helper.xml_adapter import load_jobspec_from_xml
import json
js = load_jobspec_from_xml(r'samples\J208819.xml', r'config\xml_map.yml')
with open(r'tests\goldens\J208819.jobspec.json','w',encoding='utf-8') as f:
    json.dump(js.model_dump(), f, indent=2, ensure_ascii=False)
print('Golden updated.')
"@ | python -

Wide-format detection

The router flags wide_format if:

the press entry has max_width_in and it’s large (e.g., ≥ 24), or has substrates; or

any of category/type/format/family/tags include roll, roll-to-roll, flatbed, or wide.

Ensure your /advise payload sets:

"special": { "machine": "hp_latex_570" }


…where "hp_latex_570" matches a key in your presses config.

Useful smoke checks

Verify imports come from your working tree:

python -c "import api,prepress_helper,inspect,sys; print(inspect.getsourcefile(api)); print(inspect.getsourcefile(prepress_helper)); print(sys.executable)"


Start the server (always via venv Python):

python -m uvicorn api.main:app --reload

CI (optional)

.github/workflows/ci.yml:

name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix: { python-version: ['3.11', '3.12'] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ matrix.python-version }} }
      - run: python -m pip install -U pip
      - run: python -m pip install -e ".[dev]"
      - run: python -m pytest -q

Packaging (optional)

Build a single-file CLI with PyInstaller (includes config data):

pyinstaller -F -n printssistant-cli --collect-data prepress_helper src\prepress_helper\cli.py

Contributing (internal)

Keep main protected. Use feature branches + PRs.

Conventional Commits (feat:, fix:, chore:…).

Run python -m pytest -q before PRs.

Note on No License: This repo is currently closed-source. Others cannot use/modify/distribute without your permission. You can add a license later (MIT/Apache/GPL) if you decide to open it.
