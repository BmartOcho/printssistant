from prepress_helper.jobspec import JobSpec
from prepress_helper.router import detect_intents


def _js():
    return JobSpec(
        product="Test",
        trim_size={"w_in": 3.5, "h_in": 2.0},
        bleed_in=0.125,
        safety_in=0.125,
        pages=1,
        colors={"front": "CMYK", "back": "No Printing"},
        stock="Coated",
        finish=None,
        imposition_hint="Flat Product",
        due_at=None,
        special={},
    )


def test_spot_intent_detected():
    intents = detect_intents(_js(), "Pantone 185 with white ink spot")
    assert "spot" in intents


def test_min_specs_intent_detected():
    intents = detect_intents(_js(), "small text and hairline")
    assert "min_specs" in intents
