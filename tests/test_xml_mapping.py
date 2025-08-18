from prepress_helper.xml_adapter import load_jobspec_from_xml

def test_imposition_and_pages_int():
    js = load_jobspec_from_xml("samples/J208823.xml", "config/xml_map.yml")
    assert js.special.get("imposition_across")  # e.g. "4x5"
    assert "imposition_down" not in (js.special or {})
    assert isinstance(js.pages, int)
