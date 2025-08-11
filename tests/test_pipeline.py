from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.router import detect_intents
from prepress_helper.jobspec import JobSpec, TrimSize

def test_parse_card():
    js = load_jobspec_from_xml("samples/J208819.xml", "config/xml_map.yml")
    assert js.trim_size and js.trim_size.w_in == 3.5 and js.trim_size.h_in == 2.0
    intents = detect_intents(js, "document setup")
    assert intents[0] == "doc_setup"

def test_fold_gates_on_size():
    tri = JobSpec(trim_size=TrimSize(w_in=11.0, h_in=8.5))
    intents = detect_intents(tri, "trifold roll fold")
    assert "fold_math" in intents
