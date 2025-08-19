import prepress_helper.router as router
from prepress_helper.jobspec import JobSpec, TrimSize


def _js(machine: str | None, w=11.0, h=8.5):
    return JobSpec(
        product="Test",
        trim_size=TrimSize(w_in=w, h_in=h),
        bleed_in=0.125,
        safety_in=0.125,
        pages=1,
        colors={"front": "CMYK", "back": "No Printing"},
        stock="Test",
        finish=None,
        imposition_hint="Flat",
        due_at=None,
        special={"machine": machine} if machine else {},
    )


def test_marks_wide_format_when_machine_is_roll_printer():
    # Temporarily override config for this test
    router.SHOP_CFG = {"press_capabilities": {"roll_printers": ["hp latex 560"], "flatbed_printers": []}}
    js = _js("HP Latex 560")
    intents = router.detect_intents(js, "")
    assert "wide_format" in intents


def test_marks_wide_format_when_machine_is_flatbed():
    router.SHOP_CFG = {"press_capabilities": {"roll_printers": [], "flatbed_printers": ["oce arizona 1260"]}}
    js = _js("Oce Arizona 1260")
    intents = router.detect_intents(js, "")
    assert "wide_format" in intents


def test_does_not_mark_wide_format_for_sheet_fed_even_if_large():
    router.SHOP_CFG = {"press_capabilities": {"roll_printers": [], "flatbed_printers": []}}
    # Big sheet, but sheet-fed machine name → should NOT set wide_format
    js = _js("Fuji J Press 750S", w=26.0, h=12.0)
    intents = router.detect_intents(js, "")
    assert "wide_format" not in intents


def test_message_keyword_alone_does_not_force_wide_format():
    router.SHOP_CFG = {"press_capabilities": {"roll_printers": [], "flatbed_printers": []}}
    js = _js(None)
    intents = router.detect_intents(js, "banner")
    assert "wide_format" not in intents
