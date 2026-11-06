# U.S. Coal Market Investment Outlook

Data-backed investment outlook on the U.S. coal market using the EIA Coal
Consumption and Quality dataset (2020-2025). Beginner track: this dataset only,
no outside data, no company names (industry-level analysis).

## Quickstart
```bash
pip install -r requirements.txt
pytest                       # validate src/ modules
# then run notebooks 01 -> 09 in notebooks/ in order
```

## Structure
- `data/` - source dataset (EIA coal CSV)
- `src/` - importable data loading, taxonomy, and cleaning modules (pytest-tested)
- `notebooks/` - numbered analysis notebooks (01 -> 09)
- `charts/` - exported slide-ready figures (hi-res PNG)
- `tests/` - pytest validation for src/ modules

## Key data-handling notes
- Locations mix states, regions, and a U.S. total (`US`) - pick one level per analysis.
- Sectors include aggregates: `98` Electric Power = `1+2+3`; `94` IPP = `2+3`.
  Clean non-overlapping end-use split: `98 + 8 + 9 + 10`.
- `heat-content` uses two units (electric power = MMBtu/short ton; others =
  Btu/lb); the units columns are mislabeled, so units are inferred from magnitude
  and reconciled to a single `heat_content_btu_lb` column.
- 2025 data is preliminary/sparse. Blanks = unavailable (NaN); `0.0` = reported zero.

> Full methodology write-up is a separate deliverable phase.
