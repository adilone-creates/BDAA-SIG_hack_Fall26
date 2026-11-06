"""Unit reconciliation & quality-measure standardization.

The dataset's `heat-content` uses TWO different units depending on sector:
  - Electric-power sectors (1, 2, 3, 94, 98): million Btu per short ton (~15-26).
  - Non-electric sectors (8, 9, 10): Btu per pound (~7,200-15,000).

The matching `*-units` columns are MISLABELED (the heat-content-units value
reads "average sulfur percent by weight"), so units are inferred from the
sector/magnitude and reconciled to a single `heat_content_btu_lb` column.
Conversion: MMBtu/short ton -> Btu/lb is x500 (1 short ton = 2000 lb).

`sulfur-content` and `ash-content` are consistently "% by weight" across all
rows, so no conversion is applied.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Sectors that report heat-content in million Btu per short ton.
ELECTRIC_POWER_SECTORS = {1, 2, 3, 94, 98}

# 1 short ton = 2000 lb  =>  MMBtu/ton * 1e6 / 2000 = *500 Btu/lb.
MMBTU_PER_TON_TO_BTU_PER_LB = 500

# Sectors that already report heat-content in Btu per pound.
NON_ELECTRIC_SECTORS = {8, 9, 10}


def reconcile_units(df: pd.DataFrame, heat_col: str = "heat-content") -> pd.DataFrame:
    """Add `heat_content_btu_lb` on a single comparable scale (Btu/lb).

    Electric-power rows are converted from MMBtu/short ton (x500); non-electric
    rows are already Btu/lb and pass through. NaN and reported 0.0 are preserved
    (0.0 means 'no coal burned', which legitimately maps to 0 Btu/lb).
    """
    out = df.copy()
    is_ep = out["sector"].isin(ELECTRIC_POWER_SECTORS)
    raw = out[heat_col]
    out["heat_content_btu_lb"] = np.where(is_ep, raw * MMBTU_PER_TON_TO_BTU_PER_LB, raw)
    return out


def add_preliminary_flag(df: pd.DataFrame, preliminary_years=(2025,)) -> pd.DataFrame:
    """Flag preliminary/sparse years (2025 is preliminary in this dataset)."""
    out = df.copy()
    out["is_preliminary"] = out["period"].isin(preliminary_years)
    return out


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Full cleaning pipeline: reconcile heat-content units + flag preliminary."""
    df = reconcile_units(df)
    df = add_preliminary_flag(df)
    return df
