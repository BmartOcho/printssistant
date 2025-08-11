
from __future__ import annotations
from lxml import etree
import yaml
from typing import Any, Dict
from .jobspec import JobSpec, TrimSize

def _eval_xpath(tree: etree._ElementTree, expr: str):
    if expr.startswith("number("):
        # Let XPath number() cast
        return tree.xpath(expr)
    return tree.xpath(expr)

def load_jobspec_from_xml(xml_path: str, map_yaml_path: str) -> JobSpec:
    tree = etree.parse(xml_path)
    with open(map_yaml_path, "r") as f:
        mapping: Dict[str, str] = yaml.safe_load(f)

    data: Dict[str, Any] = {}
    for target, xpath in mapping.items():
        value = _eval_xpath(tree, xpath)
        # Flatten simple results
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
            if hasattr(value, "text"):
                value = value.text
        elif isinstance(value, list) and len(value) == 0:
            value = None

        # Assign into nested dict by dotted path
        cursor = data
        parts = target.split(".")
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = value

    # Special handling for trim_size
    ts = data.get("trim_size", {})
    if ts and ("w_in" in ts and "h_in" in ts):
        data["trim_size"] = TrimSize(**ts)
    return JobSpec(**data)
