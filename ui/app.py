# ui/app.py
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

# -----------------------
# Session state & utils
# -----------------------


def _tid(text: str) -> str:
    """Stable 8-char ID per tip for checkbox keys."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("job", None)  # Pydantic JobSpec object
    ss.setdefault("intents", [])
    ss.setdefault("tips", [])  # list[str]
    ss.setdefault("scripts", {})  # dict[str, str]
    ss.setdefault("completed", {})  # tip_id -> bool
    ss.setdefault("last_parse_key", None)  # changes when new job is parsed


_init_state()


def _parse_key(js: Any, tips: List[str]) -> str:
    """A fingerprint for the current job so we reset checklist only when data changes."""
    try:
        payload = js.model_dump()  # pydantic
    except Exception:
        payload = js
    raw = json.dumps({"job": payload, "tips": tips}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


# -----------------------
# Import app libraries
# (imports after state/utils; we silence E402 since we need runtime path logic)
# -----------------------

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prepress_helper.config_loader import (  # noqa: E402
    apply_shop_config,
    load_shop_config,
)
from prepress_helper.router import (  # noqa: E402
    detect_intents,
    fold_preferences_from_message,
    set_shop_cfg,
)
from prepress_helper.skills import doc_setup  # noqa: E402
from prepress_helper.xml_adapter import load_jobspec_from_xml  # noqa: E402

# Optional skills
try:  # noqa: E402
    from prepress_helper.skills import color_policy  # type: ignore  # noqa: E402
except Exception:  # noqa: E402
    color_policy = None  # type: ignore  # noqa: E402
try:  # noqa: E402
    from prepress_helper.skills import fold_math  # type: ignore  # noqa: E402
except Exception:  # noqa: E402
    fold_math = None  # type: ignore  # noqa: E402
try:  # noqa: E402
    from prepress_helper.skills import policy_enforcer  # type: ignore  # noqa: E402
except Exception:  # noqa: E402
    policy_enforcer = None  # type: ignore  # noqa: E402
try:  # noqa: E402
    from prepress_helper.skills import wide_format  # type: ignore  # noqa: E402
except Exception:  # noqa: E402
    wide_format = None  # type: ignore  # noqa: E402


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
        "\u00a0": " ",
    }
    for k, v in table.items():
        s = s.replace(k, v)
    return s


@st.cache_resource
def _load_shop_cfg() -> Dict[str, Any]:
    cfg = load_shop_config("config")
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
        ext = ".jsx" if (name.endswith("_jsx") or "jsx" in name.lower()) else ".txt"
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


def _tips_checklist(tips: List[str]) -> None:
    st.subheader("Checklist")

    if not tips:
        st.info("No tips available for this job.")
        return

    # Bulk controls
    cols = st.columns([1, 1, 6])
    if cols[0].button("✅ Mark all done"):
        for tip in tips:
            tid = _tid(tip)
            st.session_state.completed[tid] = True
            st.session_state[f"cb_{tid}"] = True
    if cols[1].button("↩️ Clear all"):
        for tip in tips:
            tid = _tid(tip)
            st.session_state.completed[tid] = False
            st.session_state[f"cb_{tid}"] = False

    done = sum(st.session_state.completed.get(_tid(t), False) for t in tips)
    st.caption(f"Progress: {done}/{len(tips)}")

    # Render checkboxes with stable keys and on_change handler
    def _on_toggle(tip_text: str) -> None:
        tid = _tid(tip_text)
        st.session_state.completed[tid] = st.session_state.get(f"cb_{tid}", False)

    for tip in tips:
        tid = _tid(tip)
        # Initialize widget state from stored completion (only first time)
        if f"cb_{tid}" not in st.session_state:
            st.session_state[f"cb_{tid}"] = st.session_state.completed.get(tid, False)
        st.checkbox(
            tip,
            key=f"cb_{tid}",
            on_change=_on_toggle,
            args=(tip,),
            help="Click to mark this step complete.",
        )


def _job_summary(js) -> None:
    st.subheader("JobSpec")
    try:
        st.json(js.model_dump())
    except Exception:
        st.json(js)


def _session_download(js, message: str, intents: List[str], tips: List[str]) -> None:
    st.subheader("Save / Load Session")

    try:
        jobspec = js.model_dump()
    except Exception:
        jobspec = js

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "message": message,
        "intents": intents,
        "jobspec": jobspec,
        "tips_checked": st.session_state.completed,
        "version": "mvp-1",
    }
    b = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    st.download_button(
        "💾 Download session JSON",
        data=b,
        file_name="printssistant_session.json",
        mime="application/json",
    )

    up = st.file_uploader("Or load a previously saved session.json", type=["json"], key="session_upl")
    if up:
        try:
            data = json.loads(up.read().decode("utf-8"))
            st.success("Session loaded. (Viewer below)")
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
    st.caption("Tip: change machine or message and re-run.")

tab1, tab2 = st.tabs(["Parse XML & Advise", "Manual JobSpec"])

# -----------------------
# Tab 1: Parse XML & Advise
# -----------------------
with tab1:
    st.subheader("1) Upload job XML")

    with st.form("xml_parse_form", clear_on_submit=False):
        xml_file = st.file_uploader("XML file", type=["xml"])
        sample_hint = st.text_input(
            "…or type a local XML path (optional)", value="", placeholder=r"samples\J208823.xml"
        )
        submitted = st.form_submit_button("Parse XML → Build JobSpec")

    if submitted:
        try:
            xml_path = ""
            if xml_file is not None:
                xml_path = _write_temp_uploaded(xml_file)
            elif sample_hint.strip():
                xml_path = sample_hint.strip()

            if not xml_path or not os.path.exists(xml_path):
                st.error("Please upload an XML or provide a valid local path.")
            else:
                # Build JobSpec
                js = load_jobspec_from_xml(xml_path, mapping_path)

                # Optional machine override
                if selected_machine and selected_machine != "(none)":
                    special = dict(js.special or {})
                    special["machine"] = selected_machine
                    js.special = special

                # Apply shop policies (bleed/safety mins, etc.)
                js = apply_shop_config(js, SHOP_CFG)

                # Detect intents & collect tips/scripts
                intents = detect_intents(js, message or "")
                tips: List[str] = []
                scripts: Dict[str, str] = {}
                tips += doc_setup.tips(js)
                scripts.update(doc_setup.scripts(js))

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

                # Normalize and de-dupe tips
                seen = set()
                tips_norm = [normalize_ascii(t) for t in tips]
                tips_dedup = []
                for t in tips_norm:
                    if t not in seen:
                        seen.add(t)
                        tips_dedup.append(t)

                # Persist to session
                fingerprint = _parse_key(js, tips_dedup)
                if st.session_state.last_parse_key != fingerprint:
                    # Reset checklist for a new job
                    st.session_state.completed = {}
                    # Clean old checkbox widget keys
                    for k in list(st.session_state.keys()):
                        if str(k).startswith("cb_"):
                            del st.session_state[k]
                    st.session_state.last_parse_key = fingerprint

                st.session_state.job = js
                st.session_state.intents = intents
                st.session_state.tips = tips_dedup
                st.session_state.scripts = scripts

                st.success("Parsed and advised. See summary and checklist below.")

        except Exception as e:
            st.exception(e)

    # Render current session (if any)
    if st.session_state.job:
        _job_summary(st.session_state.job)
        st.subheader("Intents")
        st.write(", ".join(st.session_state.intents) if st.session_state.intents else "—")
        _tips_checklist(st.session_state.tips)
        _scripts_downloads(st.session_state.scripts)
        _session_download(st.session_state.job, message, st.session_state.intents, st.session_state.tips)

# -----------------------
# Tab 2: Manual JobSpec
# -----------------------
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
            from prepress_helper.jobspec import JobSpec, TrimSize  # noqa: E402

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

            intents2 = detect_intents(js2, message or "")
            tips2: List[str] = []
            scripts2: Dict[str, str] = {}
            tips2 += doc_setup.tips(js2)
            scripts2.update(doc_setup.scripts(js2))

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

            # Persist manual run as current session (same UX as XML parse)
            fingerprint = _parse_key(js2, tips2_dedup)
            if st.session_state.last_parse_key != fingerprint:
                st.session_state.completed = {}
                for k in list(st.session_state.keys()):
                    if str(k).startswith("cb_"):
                        del st.session_state[k]
                st.session_state.last_parse_key = fingerprint

            st.session_state.job = js2
            st.session_state.intents = intents2
            st.session_state.tips = tips2_dedup
            st.session_state.scripts = scripts2

            # Render
            _job_summary(js2)
            st.subheader("Intents")
            st.write(", ".join(intents2) if intents2 else "—")
            _tips_checklist(tips2_dedup)
            _scripts_downloads(scripts2)
            _session_download(js2, message, intents2, tips2_dedup)

        except Exception as e:
            st.exception(e)
