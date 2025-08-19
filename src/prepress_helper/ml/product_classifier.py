from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

# Lazy imports so the app works even if ML deps aren't installed
try:
    import joblib  # type: ignore
except Exception:
    joblib = None  # type: ignore

_MODEL_CACHE = {"path": None, "model": None}


def _candidate_paths() -> list[Path]:
    env = os.getenv("PRINTSSISTANT_MODEL")
    if env:
        return [Path(env)]
    here = Path(__file__).resolve()
    # typical project layout: <repo>/models/product_type.joblib
    # and also allow running from site-packages (cwd/models)
    return [
        here.parents[3] / "models" / "product_type.joblib",  # repo root (…/src/prepress_helper/ml/../../..)
        Path.cwd() / "models" / "product_type.joblib",
    ]


def load_model() -> Optional[object]:
    """Load and memoize the classifier pipeline. Returns None if unavailable."""
    if _MODEL_CACHE["model"] is not None:
        return _MODEL_CACHE["model"]
    if joblib is None:
        return None
    for p in _candidate_paths():
        try:
            if p.exists():
                model = joblib.load(p)
                _MODEL_CACHE["path"] = p
                _MODEL_CACHE["model"] = model
                return model
        except Exception:
            continue
    return None


def _features_from_jobspec(js, title_hint: str = "") -> dict:
    title = (getattr(js, "product", None) or "").strip()
    if title_hint:
        title = f"{title} {title_hint}".strip()
    w = float(getattr(getattr(js, "trim_size", None), "w_in", 0.0) or 0.0)
    h = float(getattr(getattr(js, "trim_size", None), "h_in", 0.0) or 0.0)
    pages = int(getattr(js, "pages", 0) or 0)
    long_edge = max(w, h)
    short_edge = min(w, h)
    aspect = round(long_edge / (short_edge or 1.0), 4) if short_edge else 0.0
    return {
        "title": title,
        "w_in": w,
        "h_in": h,
        "pages": pages,
        "long_edge": long_edge,
        "short_edge": short_edge,
        "aspect": aspect,
    }


def predict_label(js, title_hint: str = "") -> Optional[Tuple[str, float]]:
    """
    Returns (label, probability) or None if model not available.
    Labels (suggested): business_card, trifold, postcard, booklet, banner, label, flyer, brochure
    """
    model = load_model()
    if model is None:
        return None
    feats = _features_from_jobspec(js, title_hint)
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None
    X = pd.DataFrame([feats])
    try:
        probs = model.predict_proba(X)[0]
        idx = probs.argmax()
        label = model.classes_[idx]
        return str(label), float(probs[idx])
    except Exception:
        # model without predict_proba (e.g., LinearSVC)
        try:
            label = model.predict(X)[0]
            return str(label), 1.0
        except Exception:
            return None
