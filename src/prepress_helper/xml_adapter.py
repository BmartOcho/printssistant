# src/prepress_helper/xml_adapter.py
from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
import math
import re
from lxml import etree as ET
import yaml

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
    if v is None:
        return None
    if isinstance(v, bool):
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
        # "3" or "3.0" -> "3"
        if re.fullmatch(r"\d+(\.0+)?", s):
            try:
                return str(int(float(s)))
            except Exception:
                return None
        return s
    return None


def _normalize_imposition_pair(text: str) -> str | None:
    """
    Normalize '8x4', '8×4', '8 X 4', '8 by 4' -> '8x4' (ASCII x).
    """
    s = text.strip().lower()
    if not s:
        return None
    s = (
        s.replace("×", "x")
         .replace(" by ", "x")
         .replace(" x ", "x")
         .replace(" x", "x")
         .replace("x ", "x")
    )
    m = re.fullmatch(r"(\d+)\s*x\s*(\d+)", s)
    if m:
        return f"{int(m.group(1))}x{int(m.group(2))}"
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return f"{int(a)}x{int(b)}"
    return None


def _fallback_imposition_from_xml(tree: ET._ElementTree) -> str | None:
    """Free-text scan of XML for 'AxB' as a last resort."""
    try:
        text = ET.tostring(tree.getroot(), encoding="unicode", method="text")
    except Exception:
        return None
    for m in re.finditer(r"(\d+)\s*[x×X]\s*(\d+)", text):
        a, b = int(m.group(1)), int(m.group(2))
        if 2 <= a <= 30 and 2 <= b <= 30:
            return f"{a}x{b}"
    nums = re.findall(r"\d+", text)
    if len(nums) >= 2:
        a, b = int(nums[0]), int(nums[1])
        if 2 <= a <= 30 and 2 <= b <= 30:
            return f"{a}x{b}"
    return None


def _first_int_from_nodes_text(tree: ET._ElementTree, needle: str) -> str | None:
    """
    Find first integer from any node where local-name() contains `needle` (case-insensitive).
    Looks at element *text*.
    """
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
    """
    Find first integer from any attribute whose local-name contains `needle` (case-insensitive).
    """
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
    Robust pull of Across/Down from XML, namespace-agnostic.
    We check:
      1) element text where local-name contains 'across' / 'down'
      2) attributes whose names contain 'across' / 'down'
    """
    # element text
    across = _first_int_from_nodes_text(tree, "across")
    down = _first_int_from_nodes_text(tree, "down")

    # if missing, try attributes
    if not across:
        across = _first_int_from_attrs(tree, "across")
    if not down:
        down = _first_int_from_attrs(tree, "down")

    return across, down


def load_jobspec_from_xml(xml_path: str, map_yaml_path: str) -> JobSpec:
    tree = ET.parse(xml_path)
    with open(map_yaml_path, "r", encoding="utf-8") as f:
        mapping = yaml.safe_load(f) or {}

    # NEW: friendly validation for mapping file
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ValueError(f"Mapping YAML must be a dict of 'target: xpath'. Got: {type(mapping).__name__}")

    data: Dict[str, Any] = {}

    for target, xpath in mapping.items():
        if not xpath:
            continue
        try:
            raw = tree.xpath(xpath)
        except ET.XPathEvalError:
            # Skip bad XPaths but keep parsing the rest
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

    # Normalize numerics (NaN -> None)
    for key in ("bleed_in", "safety_in", "pages", "trim_w_in", "trim_h_in"):
        if key in data:
            data[key] = _to_num(data[key])

    # NEW: ensure pages is an int if integral
    if "pages" in data:
        coerced = _coerce_int_like(data["pages"])
        if coerced is not None:
            data["pages"] = coerced

    # Build nested trim_size if separate W/H present
    tw = data.get("trim_w_in")
    th = data.get("trim_h_in")
    if isinstance(tw, (int, float)) and isinstance(th, (int, float)):
        data["trim_size"] = {"w_in": float(tw), "h_in": float(th)}

    # Colors normalization
    colors = data.get("colors", {}) or {}
    if isinstance(colors, dict):
        if colors.get("front") is None:
            colors["front"] = ""
        back = colors.get("back")
        if back is None or (isinstance(back, str) and back.strip() == ""):
            colors["back"] = "No Printing"
        data["colors"] = colors

    # Special normalization
    special = data.get("special", {}) or {}
    if isinstance(special, dict):
        # artwork_file -> first token (strip GUIDs/timestamps)
        af = special.get("artwork_file")
        if isinstance(af, str):
            af = af.strip()
            special["artwork_file"] = af.split()[0] if af else None

        # Compose imposition_across (AxB) with a strict preference order:
        # 1) Across/Down from XML (elements/attributes)
        # 2) Mapped separate across/down fields (if both present)
        # 3) Combined string from mapping (normalize)
        # 4) Free-text fallback from XML
        composed: str | None = None

        a_xml, d_xml = _extract_across_down_from_xml(tree)
        if a_xml and a_xml.isdigit() and d_xml and d_xml.isdigit():
            composed = f"{a_xml}x{d_xml}"
        else:
            ia_raw = special.get("imposition_across")
            id_raw = special.get("imposition_down")
            ia = _as_clean_int_str(ia_raw)
            idn = _as_clean_int_str(id_raw)
            if ia and ia.isdigit() and idn and idn.isdigit():
                composed = f"{ia}x{idn}"
            else:
                if isinstance(ia_raw, str):
                    combined = _normalize_imposition_pair(ia_raw)
                    if combined:
                        composed = combined
                if composed is None:
                    composed = _fallback_imposition_from_xml(tree)

        if composed:
            special["imposition_across"] = composed
        else:
            special.pop("imposition_across", None)

        # Golden expects only the combined key; drop the separate down key entirely
        special.pop("imposition_down", None)

        # Remove empty values
        special = {k: v for k, v in special.items() if v not in (None, "", [])}

        data["special"] = special

    # Defaults expected by goldens
    if data.get("safety_in") is None:
        data["safety_in"] = 0.125

    ih = data.get("imposition_hint")
    if ih is None or (isinstance(ih, str) and ih.strip() == ""):
        data["imposition_hint"] = "Flat Product"

    # finish: empty/None -> None
    if "finish" in data and (data["finish"] is None or (isinstance(data["finish"], str) and data["finish"].strip() == "")):
        data["finish"] = None

    return JobSpec(**data)
