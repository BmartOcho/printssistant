# src/prepress_helper/xml_adapter.py
from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional, Tuple

import yaml
from lxml import etree as ET

from prepress_helper.jobspec import JobSpec


def _assign(cursor: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        if p not in cursor or not isinstance(cursor[p], dict):
            cursor[p] = {}
        cursor = cursor[p]  # type: ignore[assignment]
    cursor[parts[-1]] = value


def _to_num(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
    try:
        s = str(v).strip()
        if s == "":
            return None
        n = float(s)
        if math.isnan(n):
            return None
        return n
    except Exception:
        return v


def _coerce_int_like(v: Any) -> Optional[int]:
    """Return an int if v looks integral (e.g., '3', '3.0', 3.0); else None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        if re.fullmatch(r"\d+(\.0+)?", s):
            try:
                return int(float(s))
            except Exception:
                return None
    return None


def _as_clean_int_str(val: Any) -> str | None:
    """Return a clean integer-like string if possible, else None."""
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return str(int(val)) if val.is_integer() else str(val)
    if isinstance(val, str):
        s = val.strip()
        if s == "":
            return None
        if re.fullmatch(r"\d+(\.0+)?", s):
            try:
                return str(int(float(s)))
            except Exception:
                return None
        return s
    return None


def _normalize_imposition_pair(text: str) -> str | None:
    """Normalize '8x4', '8×4', '8 X 4', '8 by 4' -> '8x4'."""
    s = (text or "").strip().lower()
    if not s:
        return None
    s = s.replace("×", "x").replace(" by ", "x").replace(" x ", "x").replace(" x", "x").replace("x ", "x")
    m = re.fullmatch(r"(\d+)\s*x\s*(\d+)", s)
    if m:
        return f"{int(m.group(1))}x{int(m.group(2))}"
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return f"{int(a)}x{int(b)}"
    return None


def _first_int_from_nodes_text(tree: ET._ElementTree, needle: str) -> str | None:
    """First integer from any node where local-name() contains `needle` (element text)."""
    ln_lower = "abcdefghijklmnopqrstuvwxyz"
    ln_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    try:
        nodes = tree.xpath(
            f"//*[contains(translate(local-name(), '{ln_upper}', '{ln_lower}'), '{needle.lower()}')]/text()"
        )
    except Exception:
        nodes = []
    for t in nodes:
        m = re.search(r"\d+", (t or "").strip())
        if m:
            return str(int(m.group(0)))
    return None


def _first_int_from_attrs(tree: ET._ElementTree, needle: str) -> str | None:
    """First integer from any attribute whose local-name contains `needle`."""
    root = tree.getroot()
    for el in root.iter():
        for k, v in el.attrib.items():
            lname = k.split("}")[-1].lower()
            if needle.lower() in lname:
                m = re.search(r"\d+", (v or "").strip())
                if m:
                    return str(int(m.group(0)))
    return None


def _extract_across_down_from_xml(tree: ET._ElementTree) -> Tuple[str | None, str | None]:
    """
    Pull Across/Down from XML, namespace-agnostic.
    We check:
      1) element text where local-name contains 'across' / 'down'
      2) attributes whose names contain 'across' / 'down'
    """
    across = _first_int_from_nodes_text(tree, "across")
    down = _first_int_from_nodes_text(tree, "down")
    if not across:
        across = _first_int_from_attrs(tree, "across")
    if not down:
        down = _first_int_from_attrs(tree, "down")
    return across, down


def load_jobspec_from_xml(xml_path: str, map_yaml_path: str) -> JobSpec:
    tree = ET.parse(xml_path)
    with open(map_yaml_path, "r", encoding="utf-8") as f:
        mapping = yaml.safe_load(f) or {}

    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ValueError(f"Mapping YAML must be a dict of 'target: xpath'. Got: {type(mapping).__name__}")

    data: Dict[str, Any] = {}

    # 1) Apply mapping into a plain dict
    for target, xpath in mapping.items():
        if not xpath:
            continue
        try:
            raw = tree.xpath(xpath)
        except ET.XPathEvalError:
            continue

        val: Any = None
        if isinstance(raw, list):
            vals = []
            for v in raw:
                if isinstance(v, ET._Element):
                    t = "".join(v.itertext()).strip()
                    if t != "":
                        vals.append(t)
                elif isinstance(v, bytes):
                    t = v.decode("utf-8", "ignore").strip()
                    if t != "":
                        vals.append(t)
                elif isinstance(v, str):
                    t = v.strip()
                    if t != "":
                        vals.append(t)
                elif isinstance(v, (int, float, bool)):
                    vals.append(v)
            if vals:
                val = vals[0]
        elif isinstance(raw, (int, float, bool, str)):
            val = raw

        _assign(data, target, val)

    # 2) Normalize numerics
    for key in ("bleed_in", "safety_in", "pages", "trim_w_in", "trim_h_in"):
        if key in data:
            data[key] = _to_num(data[key])

    if "pages" in data:
        coerced = _coerce_int_like(data["pages"])
        if coerced is not None:
            data["pages"] = coerced

    # 3) Build trim_size if split W/H present
    tw = data.get("trim_w_in")
    th = data.get("trim_h_in")
    if isinstance(tw, (int, float)) and isinstance(th, (int, float)):
        data["trim_size"] = {"w_in": float(tw), "h_in": float(th)}

    # 4) Colors defaults
    colors = data.get("colors", {}) or {}
    if isinstance(colors, dict):
        if colors.get("front") is None:
            colors["front"] = ""
        back = colors.get("back")
        if back is None or (isinstance(back, str) and back.strip() == ""):
            colors["back"] = "No Printing"
        data["colors"] = colors

    # 5) Special: clean + compose imposition
    special = data.get("special", {}) or {}
    if isinstance(special, dict):
        # artwork_file -> first token
        af = special.get("artwork_file")
        if isinstance(af, str):
            af = af.strip()
            special["artwork_file"] = af.split()[0] if af else None

        # If mapping already provided a combined string like '8x4', normalize and keep it.
        precomposed = special.get("imposition_across")
        composed: str | None = None
        if isinstance(precomposed, str):
            composed = _normalize_imposition_pair(precomposed)

        # Otherwise try mapped separate fields (prefer Down x Across to match goldens)
        if composed is None:
            ax_maybe = _as_clean_int_str(special.get("imposition_across"))
            ay_maybe = _as_clean_int_str(special.get("imposition_down"))
            if ax_maybe and ax_maybe.isdigit() and ay_maybe and ay_maybe.isdigit():
                composed = f"{int(ay_maybe)}x{int(ax_maybe)}"  # Down x Across

        # Otherwise try to pull from XML (again Down x Across)
        if composed is None:
            a_xml, d_xml = _extract_across_down_from_xml(tree)
            if a_xml and a_xml.isdigit() and d_xml and d_xml.isdigit():
                composed = f"{int(d_xml)}x{int(a_xml)}"  # Down x Across

        # Last resort: free-text scan (kept as-is)
        if composed is None:
            # free text can only give "AxB" order; we do not flip here
            try:
                text = ET.tostring(tree.getroot(), encoding="unicode", method="text")
            except Exception:
                text = ""
            m = re.search(r"(\d+)\s*[x×X]\s*(\d+)", text)
            if m:
                composed = f"{int(m.group(1))}x{int(m.group(2))}"

        # Write back minimal set to match goldens
        slim_special: Dict[str, Any] = {}
        if special.get("artwork_file"):
            slim_special["artwork_file"] = special["artwork_file"]
        if special.get("stock_group"):
            slim_special["stock_group"] = special["stock_group"]
        if composed:
            slim_special["imposition_across"] = composed
        if special.get("machine"):
            slim_special["machine"] = special["machine"]

        special = slim_special

    data["special"] = special

    # 6) Defaults expected by goldens
    if data.get("safety_in") is None:
        data["safety_in"] = 0.125
    ih = data.get("imposition_hint")
    if ih is None or (isinstance(ih, str) and ih.strip() == ""):
        data["imposition_hint"] = "Flat Product"
    if "finish" in data and (
        data["finish"] is None or (isinstance(data["finish"], str) and data["finish"].strip() == "")
    ):
        data["finish"] = None

    return JobSpec(**data)
