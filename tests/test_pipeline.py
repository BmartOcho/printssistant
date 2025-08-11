from __future__ import annotations
from pathlib import Path
import json
import pytest

from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.jobspec import JobSpec, TrimSize
from prepress_helper.router import detect_intents

SAMPLES = Path("samples")
CONFIG = Path("config/xml_map.yml")
GOLDENS = Path("tests/goldens")

@pytest.mark.skipif(not (SAMPLES / "J208819.xml").exists(), reason="sample XML not present")
def test_parse_card_matches_golden():
    js = load_jobspec_from_xml(str(SAMPLES / "J208819.xml"), str(CONFIG))
    got = js.model_dump()
    with open(GOLDENS / "J208819.jobspec.json", "r", encoding="utf-8") as f:
        want = json.load(f)
    assert got == want

def test_router_doc_setup_for_card():
    js = JobSpec(trim_size=TrimSize(w_in=3.5, h_in=2.0), pages=1)
    intents = detect_intents(js, "document setup")
    assert intents and intents[0] == "doc_setup"

def test_router_fold_math_for_brochure_size():
    js = JobSpec(trim_size=TrimSize(w_in=11.0, h_in=8.5), pages=2)
    intents = detect_intents(js, "trifold roll fold")
    assert "fold_math" in intents
