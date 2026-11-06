"""Data loading and schema validation for the EIA U.S. Coal Consumption and
Quality dataset.

Each row is one location x sector x year (2020-2025). Measures
(consumption, receipts, stocks, price, heat-content, sulfur-content,
ash-content) are numeric; a blank means "not available" -> NaN, while 0.0 is a
reported zero (this distinction is preserved, not blanket-filled).

NOTE: the per-measure `*-units` columns are present but their *values* are
mislabeled/unreliable (e.g. heat-content-units reads "average sulfur percent by
weight"). Treat units columns as documentation only; infer units from magnitude
(see src/clean.py).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Exact column order in the source CSV.
EXPECTED_COLUMNS = [
    "period", "location", "stateDescription", "sector", "sectorDescription",
    "ash-content", "consumption", "heat-content", "price", "receipts",
    "stocks", "sulfur-content",
    "ash-content-units", "consumption-units", "heat-content-units",
    "price-units", "receipts-units", "stocks-units", "sulfur-content-units",
]

# Numeric measures (thousands of short tons for volumes; dollars/short ton for
# price; percent by weight for ash/sulfur; heat-content has mixed units - see
# clean.py).
MEASURE_COLUMNS = [
    "ash-content", "consumption", "heat-content", "price",
    "receipts", "stocks", "sulfur-content",
]

# Unit columns follow the naming pattern `<measure>-units` but their values are
# unreliable; kept for reference only.
UNIT_COLUMNS = [f"{c}-units" for c in MEASURE_COLUMNS]

STRING_COLUMNS = ["location", "stateDescription", "sectorDescription"]
INT_COLUMNS = ["period", "sector"]

# Sector codes present in the data (leaf + aggregate).
EXPECTED_SECTORS = {1, 2, 3, 8, 9, 10, 94, 98}
EXPECTED_YEARS = {2020, 2021, 2022, 2023, 2024, 2025}

# Sector hierarchy (verified against U.S. Total 2020):
#   94 Independent Power Producers = 2 (IPP Non-CHP) + 3 (IPP CHP)
#   98 Electric Power               = 1 (Electric Utility) + 2 + 3
# Clean, non-overlapping end-use breakdown of TOTAL coal use:
#   98 (Electric Power) + 8 (Commercial & Institutional) + 9 (Coke Plants)
#   + 10 (Other Industrial)
CLEAN_SECTOR_BREAKDOWN = [98, 8, 9, 10]
SECTOR_AGGREGATES = {94, 98}          # these are sums of leaf sectors
SECTOR_LEAVES = [1, 2, 3, 8, 9, 10]   # mutually exclusive end-use sectors
# Which leaf sectors roll up into an aggregate:
AGGREGATE_COMPONENTS = {
    94: [2, 3],
    98: [1, 2, 3],
}


def load_coal_data(path: str | Path) -> pd.DataFrame:
    """Load the EIA coal CSV with correct dtypes.

    - period, sector -> int
    - location, stateDescription, sectorDescription -> stripped str
    - measure columns -> float (blanks -> NaN, 0.0 preserved)
    - `*-units` columns -> str (documentation only, values unreliable)

    Raises FileNotFoundError / ValueError on schema problems.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    df = pd.read_csv(path)

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    for c in STRING_COLUMNS:
        df[c] = df[c].astype(str).str.strip()

    for c in INT_COLUMNS:
        # Keys should never be blank; coerce defensively then cast.
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64").astype(int)

    for c in MEASURE_COLUMNS:
        # blanks -> NaN, "0.0" -> 0.0; pd.to_numeric keeps reported zeros intact.
        df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in df.columns:
        if c.endswith("-units"):
            df[c] = df[c].astype(str)

    return df


def missingness_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return a per-column missingness report (count + pct of rows)."""
    n = len(df)
    miss = df.isna().sum()
    return pd.DataFrame({
        "missing": miss,
        "missing_pct": (miss / n * 100).round(2),
    }).sort_values("missing", ascending=False)
