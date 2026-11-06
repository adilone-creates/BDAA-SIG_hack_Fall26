"""Tests for src/clean.py: heat-content unit reconciliation + preliminary flag."""
import numpy as np
import pandas as pd

from src.clean import (
    ELECTRIC_POWER_SECTORS,
    NON_ELECTRIC_SECTORS,
    MMBTU_PER_TON_TO_BTU_PER_LB,
    add_preliminary_flag,
    clean,
    reconcile_units,
)
from src.data import load_coal_data

DATA_PATH = "data/eia_coal_consumption_quality_2020_2025.csv"

import pytest


@pytest.fixture(scope="module")
def raw():
    return load_coal_data(DATA_PATH)


@pytest.fixture(scope="module")
def df(raw):
    return clean(raw)


def test_electric_power_raw_heat_is_mmbtu_per_ton(raw):
    # Electric-power sectors report heat-content in MMBtu/short ton (< 100).
    ep = raw[raw["sector"].isin(ELECTRIC_POWER_SECTORS)]
    assert ep["heat-content"].max() < 100


def test_nonelectric_raw_heat_is_btu_per_lb(raw):
    # Non-electric sectors report heat-content in Btu/lb (> 1000).
    ne = raw[raw["sector"].isin(NON_ELECTRIC_SECTORS)]
    assert ne["heat-content"].min() > 1000


def test_reconciled_column_present(df):
    assert "heat_content_btu_lb" in df.columns


def test_reconciled_in_plausible_band(df):
    # Genuine (non-null, non-zero) heat contents land in a plausible coal range
    # (lignite ~4,000 Btu/lb up to met-coal ~15,000 Btu/lb).
    hc = df["heat_content_btu_lb"]
    genuine = hc[(hc.notna()) & (hc > 0)]
    assert genuine.min() >= 4000
    assert genuine.max() <= 16000


def test_conversion_factor_applied(raw):
    out = reconcile_units(raw)
    ep = out[out["sector"].isin(ELECTRIC_POWER_SECTORS)].dropna(subset=["heat-content"])
    # Electric power: converted = raw * 500 (for the non-zero rows)
    nz = ep[ep["heat-content"] > 0]
    if not nz.empty:
        ratio = nz["heat_content_btu_lb"] / nz["heat-content"]
        assert np.allclose(ratio.unique(), MMBTU_PER_TON_TO_BTU_PER_LB)
    # Non-electric: converted == raw
    ne = out[out["sector"].isin(NON_ELECTRIC_SECTORS)].dropna(subset=["heat-content"])
    if not ne.empty:
        assert np.allclose(ne["heat_content_btu_lb"], ne["heat-content"])


def test_blank_and_zero_preserved(df):
    # NaN stays NaN
    assert df["heat_content_btu_lb"].isna().any()
    # reported 0.0 stays 0.0
    assert (df["heat_content_btu_lb"] == 0.0).any()


def test_preliminary_flag(raw):
    out = add_preliminary_flag(raw)
    assert out.loc[out["period"] == 2025, "is_preliminary"].all()
    assert not out.loc[out["period"] != 2025, "is_preliminary"].any()


def test_sulfur_ash_are_percent_by_weight(df):
    # Both are reported consistently as "% by weight" (no unit mismatch like
    # heat-content). Physically a percent-by-weight cannot exceed 100%. The
    # high end is legitimate: PA / Middle-Atlantic IPP CHP plants burn waste
    # coal with ~55% ash and ~4,500 Btu/lb heat content.
    for c in ["sulfur-content", "ash-content"]:
        vals = df[c].dropna()
        assert vals.min() >= 0
        assert vals.max() < 100, f"{c} exceeds 100% - likely a unit error"
        # And not in the thousands (which would signal a raw-weight unit mix).
        assert vals.max() < 1000
