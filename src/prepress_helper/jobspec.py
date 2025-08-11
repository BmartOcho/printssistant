
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TrimSize(BaseModel):
    w_in: float
    h_in: float

class JobSpec(BaseModel):
    product: Optional[str] = None
    trim_size: Optional[TrimSize] = None
    bleed_in: float = 0.125
    safety_in: float = 0.125
    pages: int = 1
    colors: Dict[str, str] = Field(default_factory=dict)
    stock: Optional[str] = None
    finish: Optional[str] = None
    imposition_hint: Optional[str] = None
    due_at: Optional[str] = None
    special: Dict[str, Any] = Field(default_factory=dict)
