# scripts/inspect_mapping.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml
from lxml import etree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prepress_helper.xml_adapter import load_jobspec_from_xml  # noqa: E402


def _get_dotted(d: Dict[str, Any], dotted: str) -> Any:
    cur: Any = d
    for p in dotted.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _textify_list(val):
    out = []
    for v in val:
        if isinstance(v, ET._Element):
            out.append("".join(v.itertext()).strip())
        elif isinstance(v, bytes):
            out.append(v.decode("utf-8", "ignore").strip())
        else:
            out.append(str(v).strip())
    return [x for x in out if x != ""]


def inspect(xml_path: str, map_path: str, only: List[str] | None = None) -> Dict[str, Any]:
    tree = ET.parse(xml_path)
    with open(map_path, "r", encoding="utf-8") as f:
        mapping: Dict[str, str] = yaml.safe_load(f) or {}

    js = load_jobspec_from_xml(xml_path, map_path)
    jsd = js.model_dump()

    report: Dict[str, Any] = {"xml": xml_path, "map": map_path, "rows": []}

    for target, xp in mapping.items():
        if only and target not in only:
            continue
        row: Dict[str, Any] = {"target": target, "xpath": xp}
        try:
            val = tree.xpath(xp)
            if isinstance(val, list):
                raw_texts = _textify_list(val)
                row["raw_values"] = raw_texts
                row["picked"] = raw_texts[0] if raw_texts else None
            else:
                row["raw_value"] = str(val).strip()
                row["picked"] = row["raw_value"] if row["raw_value"] != "" else None
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"

        row["final_jobspec_value"] = _get_dotted(jsd, target)
        report["rows"].append(row)

    # Bonus: show a few canonical fields even if not directly mapped
    for extra in [
        "trim_size.w_in",
        "trim_size.h_in",
        "bleed_in",
        "safety_in",
        "colors.front",
        "colors.back",
        "special.imposition_across",
        "special.artwork_file",
    ]:
        if only and extra not in only:
            continue
        report["rows"].append({"target": extra, "xpath": "(composed)", "final_jobspec_value": _get_dotted(jsd, extra)})

    return report


def main():
    ap = argparse.ArgumentParser(description="Inspect XML → map → JobSpec mapping.")
    ap.add_argument("-x", "--xml", required=True, help="XML file")
    ap.add_argument("-m", "--map", required=True, help="config/xml_map.yml")
    ap.add_argument("-f", "--fields", help="comma-separated target keys to inspect (optional)")
    ap.add_argument("--json", action="store_true", help="emit machine-friendly JSON")
    args = ap.parse_args()

    only = [s.strip() for s in args.fields.split(",")] if args.fields else None
    rep = inspect(args.xml, args.map, only)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"\nXML: {rep['xml']}")
        print(f"MAP: {rep['map']}\n")
        for r in rep["rows"]:
            tgt = r["target"]
            xp = r.get("xpath")
            picked = r.get("picked")
            finalv = r.get("final_jobspec_value")
            err = r.get("error")
            raws = r.get("raw_values")
            raw = r.get("raw_value")
            print(f"[{tgt}]")
            print(f"  xpath: {xp}")
            if err:
                print(f"  ERROR: {err}")
            if raws is not None:
                print(f"  raw_values: {raws}")
            if raw is not None:
                print(f"  raw_value: {raw}")
            print(f"  picked: {picked}")
            print(f"  final_jobspec_value: {finalv}\n")


if __name__ == "__main__":
    main()
