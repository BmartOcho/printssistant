from __future__ import annotations
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient

from api.main import app  # <-- now that api/ is a package, this works

client = TestClient(app)

def test_advise_endpoint_basic():
    jobspec = {
        "trim_size": {"w_in": 3.5, "h_in": 2.0},
        "bleed_in": 0.125,
        "safety_in": 0.125,
        "pages": 1,
        "colors": {"front": "CMYK", "back": "No Printing"},
    }
    payload = {"jobspec": jobspec, "message": "color policy"}
    resp = client.post("/advise", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "scripts" in data and isinstance(data["scripts"], dict)
    # either the intent was detected or the tips mention rich black
    assert ("color_policy" in data.get("intents", [])) or any(
        "rich black" in t.lower() for t in data.get("tips", [])
    )

@pytest.mark.skipif(
    not (Path("samples/J208819.xml").exists() and Path("config/xml_map.yml").exists()),
    reason="sample XML/mapping not present",
)
def test_parse_xml_endpoint_roundtrip():
    files = {"xml": ("J208819.xml", Path("samples/J208819.xml").read_bytes(), "application/xml")}
    data = {"mapping_path": "config/xml_map.yml"}
    resp = client.post("/parse_xml", data=data, files=files)
    assert resp.status_code == 200, resp.text
    js = resp.json()
    assert js["trim_size"]["w_in"] == 3.5 and js["trim_size"]["h_in"] == 2.0
