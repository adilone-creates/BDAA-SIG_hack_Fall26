"""Tests for src/data.py: schema, dtypes, blank-vs-zero handling, key ranges."""
import pandas as pd
import pytest

from src.data import (
    EXPECTED_COLUMNS,
    EXPECTED_SECTORS,
    EXPECTED_YEARS,
    MEASURE_COLUMNS,
    load_coal_data,
    missingness_summary,
)

DATA_PATH = "data/eia_coal_consumption_quality_2020_2025.csv"


@pytest.fixture(scope="module")
def df():
    return load_coal_data(DATA_PATH)


def test_columns_present(df):
    assert all(c in df.columns for c in EXPECTED_COLUMNS)


def test_row_count_positive(df):
    assert len(df) > 0


def test_measure_columns_numeric(df):
    for c in MEASURE_COLUMNS:
        assert pd.api.types.is_numeric_dtype(df[c]), f"{c} not numeric"


def test_blanks_are_nan(df):
    # The dataset has plenty of blanks (esp. 2025, prices, stocks).
    assert df[MEASURE_COLUMNS].isna().any().any(), "expected some NaN blanks"


def test_reported_zeros_preserved(df):
    # California IPP rows report 0.0; these must stay 0.0, not become NaN.
    assert (df[MEASURE_COLUMNS] == 0.0).any().any(), "expected reported 0.0 values"


def test_year_range(df):
    assert set(df["period"].unique()) == EXPECTED_YEARS


def test_sector_set(df):
    assert set(df["sector"].unique()) == EXPECTED_SECTORS


def test_period_and_sector_int(df):
    assert pd.api.types.is_integer_dtype(df["period"])
    assert pd.api.types.is_integer_dtype(df["sector"])


def test_strings_stripped(df):
    for c in ["location", "stateDescription", "sectorDescription"]:
        assert (df[c].str.strip() == df[c]).all()


def test_missingness_runs(df):
    report = missingness_summary(df)
    assert "missing_pct" in report.columns
    assert report["missing"].sum() > 0  # there are blanks
