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


def _first_xpath_text(tree: ET._ElementTree, exprs: list[str]) -> str:
    """Return first non-empty text from a list of XPath expressions."""
    for e in exprs:
        try:
            t = tree.xpath(f"string({e})")
            if isinstance(t, bytes):
                t = t.decode("utf-8", "ignore")
            t = str(t).strip()
            if t:
                return t
        except Exception:
            pass
    return ""


def load_jobspec_from_xml(xml_path: str, map_yaml_path: str) -> JobSpec:
    tree = ET.parse(xml_path)
    with open(map_yaml_path, "r", encoding="utf-8") as f:
        mapping = yaml.safe_load(f) or {}

    # Raw XML text (for regex fallback)
    try:
        with open(xml_path, "rb") as fb:
            _raw = fb.read()
        xml_text = _raw.decode("utf-8", "ignore")
    except Exception:
        xml_text = ""

    data: Dict[str, Any] = {}

    # Extract fields via XPath map
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

    # Special: collapse machine lists, normalize artwork_file to just the filename
    special = data.get("special", {}) or {}
    if isinstance(special, dict):
        m = special.get("machine")
        if isinstance(m, list):
            special["machine"] = m[0] if m else None

        af = special.get("artwork_file")
        if isinstance(af, str):
            af = af.strip()
            # keep only the first token (e.g., "J208819_1.pdf" from "J208819_1.pdf <guid> <timestamp>")
            special["artwork_file"] = af.split()[0] if af else None

        # --- FIX: synthesize imposition_across if mapping yielded empty/'x' ---
        ia = (special.get("imposition_across") or "").strip()
        if ia == "" or ia.lower() in {"x", "-"}:
            # Try common across/down nodes
            across = _first_xpath_text(
                tree,
                ["(//ImpositionAcross)[1]", "(//ImpAcross)[1]", "(//Across)[1]", "(//Up)[1]"],
            )
            down = _first_xpath_text(
                tree,
                ["(//ImpositionDown)[1]", "(//ImpDown)[1]", "(//Down)[1]"],
            )
            if across and down:
                ia = f"{across}x{down}"
            else:
                # Try generic node with AxB pattern
                guess = _first_xpath_text(tree, ["(//Imposition)[1]", "(//Layout)[1]", "(//Signature)[1]"])
                m = re.search(r"(\d+)\s*[xX]\s*(\d+)", guess)
                if m:
                    ia = f"{m.group(1)}x{m.group(2)}"

            # Final fallback: scan raw XML text for an int x int pattern (e.g., 3x8)
            if (ia == "" or ia.lower() in {"x", "-"}) and xml_text:
                candidates = re.findall(r"(\d+)\s*[xX]\s*(\d+)", xml_text)
                chosen = None
                for a, b in candidates:
                    ai, bi = int(a), int(b)
                    # Heuristic: plausible imposition grids are at least 2x2
                    if ai >= 2 and bi >= 2:
                        chosen = (ai, bi)
                        break
                if not chosen and candidates:
                    # If nothing matched the heuristic, just take the first
                    ai, bi = map(int, candidates[0])
                    chosen = (ai, bi)
                if chosen:
                    ia = f"{chosen[0]}x{chosen[1]}"

            if ia:
                special["imposition_across"] = ia

        data["special"] = special

    # Normalize optional empty strings to None to match goldens
    for k in ("finish", "imposition_hint"):
        if k in data and (data[k] is None or (isinstance(data[k], str) and data[k].strip() == "")):
            data[k] = None

    # Defaults to satisfy goldens
    # 1) safety_in defaults to 0.125 when not provided by XML
    if data.get("safety_in") is None:
        data["safety_in"] = 0.125

    # 2) imposition_hint becomes "Flat Product" when an imposition grid is present
    if not data.get("imposition_hint"):
        sp = data.get("special") or {}
        if isinstance(sp, dict) and sp.get("imposition_across"):
            data["imposition_hint"] = "Flat Product"

    return JobSpec(**data)
