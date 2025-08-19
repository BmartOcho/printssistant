# tests/test_tips_ascii.py
from prepress_helper.skills import doc_setup
from prepress_helper.jobspec import JobSpec, TrimSize

def test_doc_setup_ascii_and_dedup():
    js = JobSpec(trim_size=TrimSize(w_in=3.5, h_in=2.0), bleed_in=0.125, safety_in=0.25, pages=2)
    tips = doc_setup.tips(js)
    assert all(("×" not in t and "≤" not in t and "≥" not in t) for t in tips)
