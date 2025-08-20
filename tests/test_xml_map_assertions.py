# tests/test_xml_map_assertions.py
import json
from pathlib import Path

import pytest

from prepress_helper.xml_adapter import load_jobspec_from_xml

SAMPLES = Path("samples")
CONFIG = Path("config/xml_map.yml")


@pytest.mark.skipif(not (SAMPLES / "J208823.xml").exists(), reason="sample XML not present")
def test_card_must_have_colors_and_imposition():
    js = load_jobspec_from_xml(str(SAMPLES / "J208823.xml"), str(CONFIG)).model_dump()
    assert js["colors"]["front"] in {"CMYK", "CMYK+Spot", "CMYK+W"}  # adapt to your shop
    assert js["colors"]["back"] != ""  # should be "No Printing" or an ink callout
    assert "x" in (js["special"].get("imposition_across") or ""), "composed imposition like '4x5' expected"


@pytest.mark.skipif(not (SAMPLES / "J208819.xml").exists(), reason="sample XML not present")
def test_golden_fields_stable():
    js = load_jobspec_from_xml(str(SAMPLES / "J208819.xml"), str(CONFIG)).model_dump()
    want = json.load(open("tests/goldens/J208819.jobspec.json", "r", encoding="utf-8"))
    assert js["special"]["imposition_across"] == want["special"]["imposition_across"]
