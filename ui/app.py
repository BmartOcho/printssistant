# ui/app.py
from __future__ import annotations

import io
import json
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional

import streamlit as st

from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# Your library imports
from prepress_helper.xml_adapter import load_jobspec_from_xml
from prepress_helper.config_loader import load_shop_config, apply_shop_config
from prepress_helper.router import (
    detect_intents,
    fold_preferences_from_message,
    set_shop_cfg,
)
from prepress_helper.skills import doc_setup

# Optional skills: safely import if present
try:
    from prepress_helper.skills import color_policy  # type: ignore
except Exception:
    color_policy = None  # type: ignore

try:
    from prepress_helper.skills import fold_math  # type: ignore
except Exception:
    fold_math = None  # type: ignore

try:
    from prepress_helper.skills import policy_enforcer  # type: ignore
except Exception:
    policy_enforcer = None  # type: ignore

try:
    from prepress_helper.skills import wide_format  # type: ignore
except Exception:
    wide_format = None  # type: ignore


# -----------------------
# Helpers
# -----------------------

def normalize_ascii(s: str) -> str:
    """Keep console/Windows-friendly text."""
    if not isinstance(s, str):
        return s
    table = {
        "≤": "<=",
        "≥": ">=",
        "×": "x",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "\u00a0": " ",  # NBSP
    }
    for k, v in table.items():
        s = s.replace(k, v)
    return s


@st.cache_resource
def _load_shop_cfg() -> Dict[str, Any]:
    """Load once per session; works from any CWD thanks to your robust loader."""
    cfg = load_shop_config("config")
    # Inject into router for wide-format detection etc.
    set_shop_cfg(cfg)
    return cfg


def _write_temp_uploaded(file) -> str:
    """Persist Streamlit upload to a temp path so xml_adapter can read it."""
    if file is None:
        return ""
    suffix = os.path.splitext(file.name or "upload.xml")[1] or ".xml"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(file.getbuffer())
    tmp.flush()
    tmp.close()
    return tmp.name


def _scripts_downloads(scripts: Dict[str, str]) -> None:
    st.subheader("Scripts")
    if not scripts:
        st.info("No scripts produced for this job.")
        return

    for name, content in scripts.items():
        ext = ".jsx" if name.endswith("_jsx") or "jsx" in name.lower() else ".txt"
        file_name = f"{name}{ext}"
        st.code(content, language="javascript" if ext == ".jsx" else "text")
        st.download_button(
            "Download " + file_name,
            data=content.encode("utf-8"),
            file_name=file_name,
            mime="text/plain",
            key=f"dl_{name}",
        )
        st.divider()


def _tips_checklist(tips: List[str]) -> Dict[str, bool]:
    st.subheader("Checklist")
    if not tips:
        st.info("No tips available for this job.")
        return {}

    # Make stable keys so check states survive reruns
    states: Dict[str, bool] = {}
    cols = st.columns([1, 1, 1])
    colidx = 0

    all_key = "check_all"
    none_key = "uncheck_all"

    # bulk controls
    with st.container():
        b1, b2 = st.columns([1, 1])
        mark_all = b1.button("✅ Mark all done", key=all_key)
        unmark_all = b2.button("↩️ Uncheck all", key=none_key)

    default_all = False
    if mark_all:
        default_all = True
    if unmark_all:
        default_all = False

    for i, tip in enumerate(tips):
        key = f"tip_{abs(hash(tip)) % 10**9}"
        # initialize to default_all when bulk was clicked
        if mark_all or unmark_all:
            st.session_state[key] = default_all
        # Draw the checkbox
        with cols[colidx]:
            states[tip] = st.checkbox(tip, key=key, value=st.session_state.get(key, False))
        colidx = (colidx + 1) % len(cols)

    st.caption("These mirror the paper checklist—complete them as you go.")
    return states


def _job_summary(js) -> None:
    st.subheader("JobSpec")
    st.json(js.model_dump())


def _session_download(js, message: str, intents: List[str], tips: List[str], checks: Dict[str, bool]) -> None:
    st.subheader("Save / Load Session")

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "message": message,
        "intents": intents,
        "jobspec": js.model_dump(),
        "tips_checked": checks,
        "version": "mvp-1",
    }
    b = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    st.download_button("💾 Download session JSON", data=b, file_name="printssistant_session.json", mime="application/json")

    up = st.file_uploader("Or load a previously saved session.json", type=["json"], key="session_upl")
    if up:
        try:
            data = json.loads(up.read().decode("utf-8"))
            st.success("Session loaded. Scroll up to re-run with its values if desired.")
            st.json(data)
        except Exception as e:
            st.error(f"Could not load session: {e}")


# -----------------------
# UI
# -----------------------

st.set_page_config(page_title="Printssistant — Operator Console", layout="wide")
st.title("🖨️ Printssistant — Operator Console (MVP)")

SHOP_CFG = _load_shop_cfg()

with st.sidebar:
    st.header("Settings")
    mapping_path = st.text_input("Mapping YAML path", value="config/xml_map.yml", help="XPath mapping file")
    presses = list((SHOP_CFG.get("presses") or {}).keys())
    selected_machine = st.selectbox("Machine (optional)", options=["(none)"] + presses, index=0)
    message = st.text_input("Operator message (prompts, fold notes, color cues…)", value="please advise on setup")
    debug_ml = st.checkbox("Debug ML (if available)", value=False)
    st.caption("Tip: you can change the machine or message and rerun.")

tab1, tab2 = st.tabs(["Parse XML & Advise", "Manual JobSpec"])

with tab1:
    st.subheader("1) Upload job XML")
    xml_file = st.file_uploader("XML file", type=["xml"])
    sample_hint = st.text_input("…or type a local XML path (optional)", value="", placeholder=r"samples\J208823.xml")

    parse_clicked = st.button("Parse XML → Build JobSpec")

    js = None
    if parse_clicked:
        try:
            xml_path = ""
            if xml_file is not None:
                xml_path = _write_temp_uploaded(xml_file)
            elif sample_hint.strip():
                xml_path = sample_hint.strip()

            if not xml_path or not os.path.exists(xml_path):
                st.error("Please upload an XML or provide a valid local path.")
            else:
                js = load_jobspec_from_xml(xml_path, mapping_path)

                # Optionally add machine from sidebar
                if selected_machine and selected_machine != "(none)":
                    special = dict(js.special or {})
                    special["machine"] = selected_machine
                    js.special = special

                # Apply shop policies (bleed/safety mins, etc.)
                js = apply_shop_config(js, SHOP_CFG)

        except Exception as e:
            st.exception(e)

    if js:
        _job_summary(js)

        # 2) Detect intents and collect tips/scripts
        intents = detect_intents(js, message or "")
        tips: List[str] = []
        scripts: Dict[str, str] = {}

        # Always include baseline doc setup
        tips += doc_setup.tips(js)
        scripts.update(doc_setup.scripts(js))

        # Optional skills triggered by intents
        if "color_policy" in intents and color_policy:
            try:
                tips += color_policy.tips(js)  # type: ignore
                scripts.update(color_policy.scripts(js))  # type: ignore
            except Exception:
                pass

        if "fold_math" in intents and fold_math:
            try:
                style, fin = fold_preferences_from_message(message or "")
                tips += fold_math.tips(js, style=style, fold_in=fin)  # type: ignore
                scripts.update(fold_math.scripts(js, style=style, fold_in=fin))  # type: ignore
            except Exception:
                pass

        if policy_enforcer:
            try:
                tips += policy_enforcer.tips(js, message or "")
                scripts.update(policy_enforcer.scripts(js, message or ""))
            except Exception:
                pass

        if "wide_format" in intents and wide_format:
            try:
                tips += wide_format.tips(js)  # type: ignore
                scripts.update(wide_format.scripts(js))  # type: ignore
            except Exception:
                pass

        # De-dupe + normalize tips to ASCII
        seen = set()
        tips = [normalize_ascii(t) for t in tips]
        tips_dedup = []
        for t in tips:
            if t not in seen:
                seen.add(t)
                tips_dedup.append(t)

        st.subheader("Intents")
        st.write(", ".join(intents) if intents else "—")

        checks = _tips_checklist(tips_dedup)
        _scripts_downloads(scripts)
        _session_download(js, message, intents, tips_dedup, checks)

with tab2:
    st.subheader("Build a JobSpec manually")
    colA, colB = st.columns(2)

    with colA:
        product = st.text_input("Product", value="Brochure")
        w_in = st.number_input("Trim width (in)", value=8.5, step=0.1)
        h_in = st.number_input("Trim height (in)", value=11.0, step=0.1)
        bleed_in = st.number_input("Bleed (in)", value=0.125, step=0.01)
        safety_in = st.number_input("Safety (in)", value=0.25, step=0.01)
        pages = st.number_input("Pages", min_value=1, value=2, step=1)

    with colB:
        front = st.text_input("Colors (front)", value="CMYK")
        back = st.text_input("Colors (back)", value="No Printing")
        stock = st.text_input("Stock", value="80# Gloss Cover")
        imposition_hint = st.text_input("Imposition hint", value="Flat Product")

    if st.button("Generate advice from manual spec"):
        try:
            from prepress_helper.jobspec import JobSpec, TrimSize

            js2 = JobSpec(
                product=product,
                trim_size=TrimSize(w_in=float(w_in), h_in=float(h_in)),
                bleed_in=float(bleed_in),
                safety_in=float(safety_in),
                pages=int(pages),
                colors={"front": front, "back": back},
                stock=stock,
                imposition_hint=imposition_hint,
                special={"machine": selected_machine} if selected_machine != "(none)" else {},
            )
            js2 = apply_shop_config(js2, SHOP_CFG)

            _job_summary(js2)

            intents2 = detect_intents(js2, message or "")
            tips2: List[str] = doc_setup.tips(js2)
            scripts2: Dict[str, str] = doc_setup.scripts(js2)

            if "color_policy" in intents2 and color_policy:
                tips2 += color_policy.tips(js2)  # type: ignore
                scripts2.update(color_policy.scripts(js2))  # type: ignore

            if "fold_math" in intents2 and fold_math:
                style, fin = fold_preferences_from_message(message or "")
                tips2 += fold_math.tips(js2, style=style, fold_in=fin)  # type: ignore
                scripts2.update(fold_math.scripts(js2, style=style, fold_in=fin))  # type: ignore

            if policy_enforcer:
                tips2 += policy_enforcer.tips(js2, message or "")
                scripts2.update(policy_enforcer.scripts(js2, message or ""))

            if "wide_format" in intents2 and wide_format:
                tips2 += wide_format.tips(js2)  # type: ignore
                scripts2.update(wide_format.scripts(js2))  # type: ignore

            # normalize + de-dupe
            seen = set()
            tips2 = [normalize_ascii(t) for t in tips2]
            tips2_dedup = []
            for t in tips2:
                if t not in seen:
                    seen.add(t)
                    tips2_dedup.append(t)

            st.subheader("Intents")
            st.write(", ".join(intents2) if intents2 else "—")

            checks2 = _tips_checklist(tips2_dedup)
            _scripts_downloads(scripts2)
            _session_download(js2, message, intents2, tips2_dedup, checks2)

        except Exception as e:
            st.exception(e)
