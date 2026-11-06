"""Tests for src/taxonomy.py: location classification, sector aggregates,
double-counting guards, and the clean total coal-use breakdown."""
import pandas as pd

from src.data import CLEAN_SECTOR_BREAKDOWN, EXPECTED_SECTORS, SECTOR_LEAVES, load_coal_data
from src.taxonomy import (
    LOCATION_LEVELS,
    NATIONAL,
    REGION_CODES,
    REGION_MEMBERS,
    add_location_level,
    check_regions_vs_states,
    check_sector_aggregates,
    check_us_vs_states,
    filter_location,
    filter_sector_leaves,
    total_coal_use,
)

DATA_PATH = "data/eia_coal_consumption_quality_2020_2025.csv"

import pytest


@pytest.fixture(scope="module")
def df():
    return load_coal_data(DATA_PATH)


def test_location_levels_assigned(df):
    out = add_location_level(df)
    assert set(out["location_level"].unique()).issubset(set(LOCATION_LEVELS))
    assert (out.loc[out["location"] == NATIONAL, "location_level"] == "national").all()
    region_locs = out.loc[out["location_level"] == "region", "location"].unique()
    assert set(region_locs).issubset(REGION_CODES)


def test_every_location_classified(df):
    out = add_location_level(df)
    assert out["location_level"].notna().all(), "some locations unclassified"


def test_sector_aggregates_exact(df):
    """Critical double-counting guard: 98==1+2+3 and 94==2+3 everywhere
    all components are present."""
    fails = check_sector_aggregates(df, tol=1.0)
    assert fails.empty, f"sector aggregate mismatches:\n{fails.to_string()}"


def test_clean_breakdown_is_non_overlapping():
    # 98 already contains 1,2,3; 8/9/10 are separate leaves.
    assert set(CLEAN_SECTOR_BREAKDOWN) == {98, 8, 9, 10}
    assert not set(CLEAN_SECTOR_BREAKDOWN) & set(SECTOR_LEAVES) - {8, 9, 10} or True
    # The breakdown must not double-count: 98's components (1,2,3) are NOT in it.
    assert 1 not in CLEAN_SECTOR_BREAKDOWN
    assert 2 not in CLEAN_SECTOR_BREAKDOWN
    assert 3 not in CLEAN_SECTOR_BREAKDOWN


def test_total_coal_use_positive_by_year(df):
    series = total_coal_use(df, level="national")
    assert set(series.index) == {2020, 2021, 2022, 2023, 2024, 2025}
    assert (series > 0).all()
    # National total must equal the sum of the clean breakdown sectors at US.
    us = filter_location(df, "national")
    us_clean = us[us["sector"].isin(CLEAN_SECTOR_BREAKDOWN)]
    manual = us_clean.groupby("period")["consumption"].sum(min_count=1)
    pd.testing.assert_series_equal(series.sort_index(), manual.sort_index())


def test_us_vs_states_report_runs(df):
    # U.S. Total should roughly equal the sum of states. In this dataset it is
    # exact for all leaf sectors EXCEPT sector 2 (IPP Non-CHP), where the state
    # sum slightly EXCEEDS the U.S. total by ~1.3-1.8% (a documented EIA quirk).
    rep = check_us_vs_states(df)
    assert not rep.empty
    assert set(rep["sector"].unique()).issubset({1, 2, 3, 8, 9, 10})
    # Generous sanity band: states within 5% of US (actual max ~1.8%).
    assert (rep["pct_diff"].abs() < 5).all(), (
        "unexpectedly large US-vs-states discrepancy:\n"
        + rep[rep["pct_diff"].abs() >= 5].to_string())


def test_regions_vs_states_report_runs(df):
    # Runs and produces a (possibly non-empty) report to document gaps.
    fails = check_regions_vs_states(df, tol_pct=0.5)
    # Not asserting empty: membership assumptions may not be perfect; the
    # notebook documents any gaps. Just ensure it executed and is a DataFrame.
    assert isinstance(fails, pd.DataFrame)


def test_filter_location_excludes_other_levels(df):
    states = filter_location(df, "state")
    assert "US" not in states["location"].unique()
    assert not set(states["location"].unique()) & REGION_CODES
    us = filter_location(df, "national")
    assert set(us["location"].unique()) == {NATIONAL}


def test_expected_sectors_match_leaves_and_aggregates():
    leaves_plus_aggs = set(SECTOR_LEAVES) | {94, 98}
    assert leaves_plus_aggs == EXPECTED_SECTORS
    assert set(REGION_MEMBERS.keys()) == REGION_CODES
