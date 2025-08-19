# tests/test_xml_normalization.py
from prepress_helper.xml_adapter import load_jobspec_from_xml
import tempfile, textwrap, os, yaml

def test_pages_and_colors_and_finish():
    xml = textwrap.dedent("""\
        <Job>
          <Pages>3.0</Pages>
          <ProcessFront>CMYK</ProcessFront>
          <ProcessBack></ProcessBack>
          <Finish></Finish>
        </Job>
    """)
    mapping = {
        "pages": "number((//Pages)[1])",
        "colors.front": "string(//ProcessFront)",
        "colors.back": "string(//ProcessBack)",
        "finish": "string(//Finish)"
    }
    with tempfile.TemporaryDirectory() as td:
        xmlp = os.path.join(td, "job.xml")
        mapp = os.path.join(td, "map.yml")
        open(xmlp, "w", encoding="utf-8").write(xml)
        open(mapp, "w", encoding="utf-8").write(yaml.dump(mapping))
        js = load_jobspec_from_xml(xmlp, mapp)
        assert js.pages == 3
        assert js.colors["back"] == "No Printing"
        assert js.finish is None
