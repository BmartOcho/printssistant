# src/prepress_helper/jobspec.py
from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TrimSize(BaseModel):
    model_config = ConfigDict(extra="ignore")
    w_in: float = Field(..., ge=0)
    h_in: float = Field(..., ge=0)


class JobSpec(BaseModel):
    # Ignore unexpected XML fields; allow population by field name or alias
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    product: Optional[str] = None
    trim_size: Optional[TrimSize] = None
    bleed_in: Optional[float] = Field(default=None, ge=0)
    safety_in: Optional[float] = Field(default=None, ge=0)
    pages: int = Field(1, ge=1)
    colors: Dict[str, str] = Field(default_factory=lambda: {"front": "", "back": ""})
    stock: Optional[str] = None
    finish: Optional[str] = None
    imposition_hint: Optional[str] = None
    due_at: Optional[str] = None
    special: Dict[str, Any] = Field(default_factory=dict)

    # --- Normalizers ---------------------------------------------------------
    @field_validator("product", "stock", "finish", "imposition_hint", "due_at", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("colors", mode="before")
    @classmethod
    def _normalize_colors(cls, v):
        if isinstance(v, dict):
            # lower-case keys; ensure front/back exist
            out = {str(k).lower(): ("" if v[k] is None else str(v[k])) for k in v}
            out.setdefault("front", out.get("f", ""))  # tolerate 'f'/'b' shorthand if ever used
            out.setdefault("back", out.get("b", ""))
            return {"front": out.get("front", ""), "back": out.get("back", "")}
        return {"front": "", "back": ""}
