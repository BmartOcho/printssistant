from __future__ import annotations
from typing import Any, Dict
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

def _normalize_imposition_across(val: Any) -> str | None:
    """Normalize strings like '8x4', '8×4', '8 X 4' -> '8×4'. Return None if not confident."""
    if not isinstance(val, str):
        return None
    s = val.strip()
    if not s:
        return None
    # Try explicit "AxB" first with any of x/×/X
    m = re.fullmatch(r"\s*(\d+)\s*[x×X]\s*(\d+)\s*", s)
    if m:
        return f"{int(m.group(1))}×{int(m.group(2))}"
    # Fallback: pull first two integers we see (e.g., "8 by 4")
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return f"{int(a)}×{int(b)}"
    return None

def _fallback_imposition_from_xml(tree: ET._ElementTree) -> str | None:
    """
    If mapping didn't yield a usable imposition_across, scan the XML text for
    the first 'AxB' pair (2..30) where the separator can be x/×/X.
    """
    try:
        text = ET.tostring(tree.getroot(), encoding="unicode", method="text")
    except Exception:
        return None
    # Prefer explicit AxB with x/×/X
    for m in re.finditer(r"(\d+)\s*[x×X]\s*(\d+)", text):
        a, b = int(m.group(1)), int(m.group(2))
        if 2 <= a <= 30 and 2 <= b <= 30:
            return f"{a}×{b}"
    # As an extra guard, accept the first two integers found anywhere
    nums = re.findall(r"\d+", text)
    if len(nums) >= 2:
        a, b = int(nums[0]), int(nums[1])
        if 2 <= a <= 30 and 2 <= b <= 30:
            return f"{a}×{b}"
    return None

def load_jobspec_from_xml(xml_path: str, map_yaml_path: str) -> JobSpec:
    tree = ET.parse(xml_path)
    with open(map_yaml_path, "r", encoding="utf-8") as f:
        mapping = yaml.safe_load(f) or {}

    data: Dict[str, Any] = {}

    for target, xpath in mapping.items():
        if not xpath:
            continue
        raw = tree.xpath(xpath)
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

    # Build nested trim_size if separate W/H present
    tw = data.get("trim_w_in")
    th = data.get("trim_h_in")
    if isinstance(tw, (int, float)) and isinstance(th, (int, float)):
        data["trim_size"] = {"w_in": float(tw), "h_in": float(th)}

    # Colors: keep provided strings; default back side to "No Printing" if missing/empty
    colors = data.get("colors", {}) or {}
    if isinstance(colors, dict):
        if colors.get("front") is None:
            colors["front"] = ""
        back = colors.get("back")
        if back is None or (isinstance(back, str) and back.strip() == ""):
            colors["back"] = "No Printing"
        data["colors"] = colors

    # Special: normalize machine, artwork_file, imposition_across
    special = data.get("special", {}) or {}
    if isinstance(special, dict):
        # machine: collapse list -> first
        m = special.get("machine")
        if isinstance(m, list):
            special["machine"] = m[0] if m else None

        # artwork_file -> first token (strip GUIDs/timestamps)
        af = special.get("artwork_file")
        if isinstance(af, str):
            af = af.strip()
            special["artwork_file"] = af.split()[0] if af else None

        # imposition_across -> normalize mapping value; if not usable, fallback from XML text
        ia = special.get("imposition_across")
        norm = _normalize_imposition_across(ia)
        if norm is None:
            norm = _fallback_imposition_from_xml(tree)
        if norm is not None:
            special["imposition_across"] = norm
        else:
            special.pop("imposition_across", None)

        data["special"] = special

    # Defaults expected by goldens (parse-time)
    if data.get("safety_in") is None:
        data["safety_in"] = 0.125

    ih = data.get("imposition_hint")
    if ih is None or (isinstance(ih, str) and ih.strip() == ""):
        data["imposition_hint"] = "Flat Product"

    # finish: empty/None -> None (goldens store null here)
    if "finish" in data and (data["finish"] is None or (isinstance(data["finish"], str) and data["finish"].strip() == "")):
        data["finish"] = None

    return JobSpec(**data)
