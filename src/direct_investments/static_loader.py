"""
static_loader.py — Reads hand-edited YAML files from data/static/.
Each loader returns (DataFrame, meta_dict). Meta carries last_updated + sources.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parents[2] / "data" / "static"


def _read_yaml(filename: str) -> dict[str, Any] | None:
    """Read a YAML file from data/static/. Returns None if missing or unreadable."""
    try:
        import yaml
    except ImportError:
        logger.error("PyYAML not installed — install with `pip install PyYAML`.")
        return None

    path = STATIC_DIR / filename
    if not path.exists():
        logger.warning(f"Static file missing: {path}")
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def _meta_from(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "last_updated": payload.get("last_updated", ""),
        "unit": payload.get("unit", ""),
        "sources": payload.get("sources", {}),
        "notes": payload.get("notes", ""),
    }


def load_quarterly_long(filename: str, value_field: str = "value") -> tuple[pd.DataFrame, dict]:
    """
    Generic loader for the quarterly schema:
        quarters:
          - period: "2024Q1"
            <company>: <value>
            <company>: <value>
    Returns a long-form DataFrame with columns: period, company, value.
    """
    payload = _read_yaml(filename)
    if not payload:
        return pd.DataFrame(columns=["period", "company", value_field]), {}

    meta = _meta_from(payload)
    rows = []
    for q in payload.get("quarters", []):
        period = q.get("period")
        if not period:
            continue
        for company, value in q.items():
            if company == "period":
                continue
            try:
                rows.append({"period": period, "company": company, value_field: float(value)})
            except (TypeError, ValueError):
                continue
    df = pd.DataFrame(rows)
    return df, meta


def load_simple_series(filename: str, value_field: str = "value") -> tuple[pd.DataFrame, dict]:
    """
    Loader for single-series schemas:
        periods:
          - period: "2024"
            value: 50
    Returns DataFrame with columns: period, value.
    """
    payload = _read_yaml(filename)
    if not payload:
        return pd.DataFrame(columns=["period", value_field]), {}

    meta = _meta_from(payload)
    rows = []
    for entry in payload.get("periods", []):
        period = entry.get("period")
        value = entry.get("value")
        if period is None or value is None:
            continue
        try:
            rows.append({"period": period, value_field: float(value)})
        except (TypeError, ValueError):
            continue
    return pd.DataFrame(rows), meta
