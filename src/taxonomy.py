"""Location & sector taxonomy with double-counting guards.

Locations appear at three levels in ONE column - never sum across levels:
  - national : "US" (U.S. Total)
  - region   : EIA census-division codes ENC, ESC, MAT, MTN, NEW, PCC, PCN,
               SAT, WNC, WSC, plus the legacy "90" (Pacific)
  - state    : 2-letter codes (incl. DC and PR)

Sectors include aggregates (also double-count if summed with their parts):
  - 94 Independent Power Producers = 2 (IPP Non-CHP) + 3 (IPP CHP)
  - 98 Electric Power              = 1 (Electric Utility) + 2 + 3
Clean, non-overlapping TOTAL coal use = 98 + 8 + 9 + 10.
"""
from __future__ import annotations

import pandas as pd

from src.data import (
    AGGREGATE_COMPONENTS,
    CLEAN_SECTOR_BREAKDOWN,
    SECTOR_AGGREGATES,
    SECTOR_LEAVES,
)

NATIONAL = "US"

# EIA region / census-division codes present in the data (legacy "90" = Pacific).
REGION_CODES = {
    "ENC", "ESC", "MAT", "MTN", "NEW", "PCC", "PCN", "SAT", "WNC", "WSC", "90",
}

# Standard EIA census-division membership (only states actually in the data
# are used when cross-checking; missing states such as MA/VT have ~no coal).
REGION_MEMBERS = {
    "NEW": ["CT", "ME", "MA", "NH", "RI", "VT"],
    "MAT": ["NJ", "NY", "PA"],
    "ENC": ["IL", "IN", "MI", "OH", "WI"],
    "WNC": ["IA", "KS", "MN", "MO", "ND", "NE", "SD"],
    "SAT": ["DE", "DC", "FL", "GA", "MD", "NC", "SC", "VA", "WV", "PR"],
    "ESC": ["AL", "KY", "MS", "TN"],
    "WSC": ["AR", "LA", "OK", "TX"],
    "MTN": ["AZ", "CO", "ID", "MT", "NM", "NV", "UT", "WY"],
    "PCC": ["CA", "OR", "WA"],
    "PCN": ["AK", "HI"],
    "90": ["AK", "CA", "HI", "OR", "WA"],
}

LOCATION_LEVELS = ("national", "region", "state")

SECTOR_DESCRIPTIONS = {
    1: "Electric Utility",
    2: "IPP Non-CHP",
    3: "IPP CHP",
    8: "Commercial and Institutional",
    9: "Coke Plants",
    10: "Other Industrial",
    94: "Independent Power Producers",
    98: "Electric Power",
}


def _location_level(loc: str) -> str:
    if loc == NATIONAL:
        return "national"
    if loc in REGION_CODES:
        return "region"
    return "state"


def add_location_level(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with a `location_level` column (national/region/state)."""
    out = df.copy()
    out["location_level"] = out["location"].map(_location_level)
    return out


def filter_location(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Return rows at exactly one location level (computes level if needed)."""
    if "location_level" not in df.columns:
        df = add_location_level(df)
    return df[df["location_level"] == level].copy()


def filter_sector_leaves(df: pd.DataFrame) -> pd.DataFrame:
    """Return only mutually-exclusive leaf sectors (1,2,3,8,9,10)."""
    return df[df["sector"].isin(SECTOR_LEAVES)].copy()


def total_coal_use(df: pd.DataFrame, level: str = "national") -> pd.Series:
    """Total U.S. coal use from the clean non-overlapping breakdown
    (98 + 8 + 9 + 10) at a location level, grouped by period.

    Use level='national' on US rows for the headline trend, or 'state' for a
    state-level total (summed across the clean breakdown per state-year).
    """
    sub = filter_location(df, level)
    sub = sub[sub["sector"].isin(CLEAN_SECTOR_BREAKDOWN)]
    return sub.groupby("period")["consumption"].sum(min_count=1)


# --- Consistency checks (double-counting guards) -----------------------------

def _get(g: pd.DataFrame, sector: int):
    """Consumption value for a sector in a (location,period) group, or None."""
    v = g.loc[g["sector"] == sector, "consumption"]
    if len(v) == 0:
        return None
    val = v.iloc[0]
    return None if pd.isna(val) else float(val)


def check_sector_aggregates(df: pd.DataFrame, tol: float = 1.0) -> pd.DataFrame:
    """Verify 98 == 1+2+3 and 94 == 2+3 per (location, period) where all
    components are present and non-null. Returns rows that FAIL (empty = ok)."""
    fails = []
    for (loc, yr), g in df.groupby(["location", "period"]):
        present = set(g["sector"].tolist())
        for agg, comps in AGGREGATE_COMPONENTS.items():
            need = set(comps) | {agg}
            if not need <= present:
                continue
            parts = [_get(g, s) for s in comps]
            a = _get(g, agg)
            if a is None or any(p is None for p in parts):
                continue
            if abs(a - sum(parts)) > tol:
                fails.append({
                    "location": loc, "period": yr,
                    "check": f"{agg}=={'+'.join(map(str, comps))}",
                    "aggregate": a, "sum_components": sum(parts),
                    "diff": a - sum(parts),
                })
    return pd.DataFrame(fails)


def check_us_vs_states(df: pd.DataFrame) -> pd.DataFrame:
    """Compare U.S. Total consumption to the sum of state rows for each leaf
    sector x year. Returns a report with pct_diff (negative => states undercount
    US, e.g. due to states with no coal that are absent from the data)."""
    out = add_location_level(df)
    leaves = out[out["sector"].isin(SECTOR_LEAVES)]
    us = (leaves[leaves["location_level"] == "national"]
          .groupby(["period", "sector"])["consumption"].sum(min_count=1)
          .rename("us_total"))
    st = (leaves[leaves["location_level"] == "state"]
          .groupby(["period", "sector"])["consumption"].sum(min_count=1)
          .rename("states_sum"))
    rep = pd.concat([us, st], axis=1).dropna()
    rep["pct_diff"] = (rep["states_sum"] - rep["us_total"]) / rep["us_total"] * 100
    return rep.reset_index().sort_values(["sector", "period"])


def check_regions_vs_states(df: pd.DataFrame, tol_pct: float = 0.5) -> pd.DataFrame:
    """For each region, compare the region row to the sum of its member states
    present in the data, per (period, sector). Returns rows that exceed tol_pct."""
    out = add_location_level(df)
    fails = []
    region_rows = out[out["location_level"] == "region"]
    state_rows = out[out["location_level"] == "state"]
    for region, members in REGION_MEMBERS.items():
        rsub = region_rows[region_rows["location"] == region]
        ssub = state_rows[state_rows["location"].isin(members)]
        for (yr, sec), rg in rsub.groupby(["period", "sector"]):
            rv = rg["consumption"].sum(min_count=1)
            if pd.isna(rv) or rv == 0:
                continue
            sv = ssub[(ssub["period"] == yr) & (ssub["sector"] == sec)]["consumption"].sum(min_count=1)
            if pd.isna(sv):
                continue
            pct = (sv - rv) / rv * 100
            if abs(pct) > tol_pct:
                fails.append({
                    "region": region, "period": yr, "sector": sec,
                    "region_value": rv, "states_sum": sv, "pct_diff": round(pct, 2),
                })
    return pd.DataFrame(fails)
