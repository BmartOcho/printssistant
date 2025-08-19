from __future__ import annotations

from typing import Any, Dict, List

from prepress_helper.config_loader import load_shop_config
from prepress_helper.jobspec import JobSpec

SHOP = load_shop_config("config")


def _get(cfg: Dict[str, Any], path: str, default=None):
    cur = cfg
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


KEYWORDS_MIN_TEXT = {
    "small text",
    "tiny text",
    "fine text",
    "reverse text",
    "knockout text",
    "white text",
}
KEYWORDS_HAIRLINE = {"hairline", "thin line", "fine line", "barcodes", "micro lines"}


def tips(js: JobSpec, msg: str, intents: List[str]) -> List[str]:
    """
    Provide minimum text and stroke guidance based on shop policy.
    Triggered when message hints at small text/lines OR when explicitly asked.
    """
    msg_l = (msg or "").lower()
    t_small = any(k in msg_l for k in KEYWORDS_MIN_TEXT)
    t_lines = any(k in msg_l for k in KEYWORDS_HAIRLINE)
    is_wide = "wide_format" in intents

    out: List[str] = []

    # Always restate document fundamentals (these are deduped by the CLI)
    out.append(f"Create a document at {js.trim_size.w_in}×{js.trim_size.h_in} in with 0.125 in bleed on all sides.")
    out.append("Set safety margins to 0.25 in; keep text and logos inside.")

    # Text guidance
    m_body = _get(SHOP, "policies.min_text_pt.body_k_only", 7)
    m_knock = _get(SHOP, "policies.min_text_pt.small_knockout", 8)
    if t_small or "doc_setup" in intents:
        out.append(f"Minimum text size: body 100K text ≥ {m_body} pt.")
        out.append(f"Small reversed/knockout text ≥ {m_knock} pt (heavier weight if possible).")

    # Stroke guidance
    s_k = _get(SHOP, "policies.min_stroke_pt.k_only", 0.25)
    s_knock = _get(SHOP, "policies.min_stroke_pt.knockout", 0.35)
    s_wide = _get(SHOP, "policies.min_stroke_pt.wide_format", 0.5)
    if t_lines or "doc_setup" in intents:
        if is_wide:
            out.append(f"Minimum hairline width (wide-format): ≥ {s_wide} pt.")
        else:
            out.append(f"Minimum hairline width: 100K lines ≥ {s_k} pt; reversed/knockout lines ≥ {s_knock} pt.")

    return out


def scripts(js: JobSpec, msg: str, intents: List[str]) -> Dict[str, str]:
    # Focus on guidance; scripts here would duplicate color_policy behavior.
    return {}
