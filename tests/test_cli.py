from __future__ import annotations
from pathlib import Path
import json
import pytest
from typer.testing import CliRunner

from prepress_helper.cli import app

runner = CliRunner()

@pytest.mark.skipif(not Path("samples/J208819.xml").exists(), reason="sample XML not present")
def test_cli_parse_xml_produces_jobspec_json():
    result = runner.invoke(app, ["parse-xml", "samples/J208819.xml", "config/xml_map.yml"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["trim_size"]["w_in"] == 3.5
    assert data["trim_size"]["h_in"] == 2.0
    assert data["colors"]["front"]

def test_cli_advise_with_constructed_jobspec():
    # minimal jobspec to exercise advise path without files
    js = {
        "trim_size": {"w_in": 11.0, "h_in": 8.5},
        "bleed_in": 0.125,
        "safety_in": 0.125,
        "pages": 2,
        "colors": {"front": "CMYK", "back": "CMYK"},
    }
    tmp = Path("tests/.tmp.jobspec.json")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(js), encoding="utf-8")

    result = runner.invoke(app, ["advise", str(tmp), "--msg", "trifold roll fold"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert "fold_math" in data["intents"]
    assert any("Tri-fold" in t for t in data["tips"])
