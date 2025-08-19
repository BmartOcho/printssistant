# tests/test_xml_imposition_mapping_first.py
from prepress_helper.xml_adapter import load_jobspec_from_xml
import tempfile, textwrap, os, yaml

def test_mapping_first_imposition():
    xml = textwrap.dedent("""\
        <Job>
          <ImposeAcross>6</ImposeAcross>
          <ImposeDown>7</ImposeDown>
        </Job>
    """)
    mapping = {"special.imposition_across": "string((//ImposeAcross)[1])",
               "special.imposition_down": "string((//ImposeDown)[1])"}

    with tempfile.TemporaryDirectory() as td:
        xmlp = os.path.join(td, "job.xml")
        mapp = os.path.join(td, "map.yml")
        open(xmlp, "w", encoding="utf-8").write(xml)
        open(mapp, "w", encoding="utf-8").write(yaml.dump(mapping))
        js = load_jobspec_from_xml(xmlp, mapp)
        assert js.special.get("imposition_across") == "6x7"
