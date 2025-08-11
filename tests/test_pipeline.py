from pathlib import Path
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.skills import doc_setup

def test_parse_and_tip():
    js = load_jobspec_from_xml("samples/J208819.xml", "config/xml_map.yml")
    tips = doc_setup.tips(js)
    assert any("bleed" in t.lower() for t in tips)
