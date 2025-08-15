from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TrimSize(BaseModel):
    w_in: float
    h_in: float

class JobSpec(BaseModel):
    product: Optional[str] = None
    trim_size: Optional[TrimSize] = None
    bleed_in: Optional[float] = None
    safety_in: Optional[float] = None  # <- Optional to tolerate missing Safety in XML
    pages: Optional[int] = 1
    colors: Dict[str, str] = Field(default_factory=lambda: {"front": "", "back": ""})
    stock: Optional[str] = None
    finish: Optional[str] = ""
    imposition_hint: Optional[str] = ""
    due_at: Optional[str] = None
    special: Dict[str, Any] = Field(default_factory=dict)
