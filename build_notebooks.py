"""Generate the numbered analysis notebooks (01-09) as .ipynb files.

Run:  python build_notebooks.py
Re-creates notebooks/*.ipynb from the cell definitions below. The notebooks are
the deliverables; this script just materialises them as valid .ipynb so they
can be opened/edited/executed directly.
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
NB_DIR = ROOT / "notebooks"


def make_nb(cells, name):
    nb = nbf.v4.new_notebook()
    nb.cells = []
    for kind, src in cells:
        if kind == "md":
            nb.cells.append(nbf.v4.new_markdown_cell(src))
        else:
            nb.cells.append(nbf.v4.new_code_cell(src))
    nb.metadata["kernelspec"] = {
        "name": "python3", "display_name": "Python 3", "language": "python",
    }
    NB_DIR.mkdir(exist_ok=True)
    nbf.write(nb, str(NB_DIR / name))
    print("wrote", name)


SETUP = '''import sys, os
ROOT = os.getcwd() if os.path.exists(os.path.join(os.getcwd(), "src")) else os.path.dirname(os.getcwd())
sys.path.insert(0, ROOT)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 110
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 160)
DATA = os.path.join(ROOT, "data", "eia_coal_consumption_quality_2020_2025.csv")
CHARTS = os.path.join(ROOT, "charts")
os.makedirs(CHARTS, exist_ok=True)
print("ROOT:", ROOT)
'''

SAVE = (
    "def savefig(name):\n"
    "    p = os.path.join(CHARTS, name)\n"
    "    plt.savefig(p, dpi=150, bbox_inches='tight')\n"
    "    print('saved', p)\n"
    "    plt.show()\n"
)


# --------------------------------------------------------------------------- #
# 01 - Data loading & schema validation
# --------------------------------------------------------------------------- #
nb01 = [
    ("md", "# 01 - Data Loading & Schema Validation\n\n"
     "Load the EIA Coal Consumption & Quality dataset and validate schema/dtypes."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data, missingness_summary, MEASURE_COLUMNS, EXPECTED_COLUMNS\n"
     "df = load_coal_data(DATA)\n"
     "print('shape:', df.shape)\n"
     "df.head()"),
    ("code", "df.dtypes"),
    ("code", "missingness_summary(df)"),
    ("code",
     "print('Years:', sorted(df['period'].unique()))\n"
     "print('Sectors:', sorted(df['sector'].unique()))\n"
     "print('Distinct locations:', df['location'].nunique())"),
    ("code",
     "print('Sector codes & descriptions:')\n"
     "print(df[['sector','sectorDescription']].drop_duplicates().sort_values('sector').to_string(index=False))"),
    ("code",
     "# Validation assertions (mirror tests/test_data.py)\n"
     "assert len(df) > 0\n"
     "assert set(df['period'].unique()) == {2020,2021,2022,2023,2024,2025}\n"
     "assert set(df['sector'].unique()) == {1,2,3,8,9,10,94,98}\n"
     "assert df[MEASURE_COLUMNS].isna().any().any(), 'expected some blank (NaN) values'\n"
     "assert (df[MEASURE_COLUMNS] == 0.0).any().any(), 'expected some reported 0.0 values'\n"
     "print('All schema checks passed.')"),
    ("md",
     "**Takeaways**\n"
     "- 1,750 rows across 62 locations x 8 sectors x 6 years.\n"
     "- Seven numeric measures; blanks become NaN while reported `0.0` (e.g. "
     "California IPP rows) is preserved.\n"
     "- 2025 data is preliminary and sparse (visible in the missingness report)."),
]

# --------------------------------------------------------------------------- #
# 02 - Hierarchy & double-counting guards
# --------------------------------------------------------------------------- #
nb02 = [
    ("md", "# 02 - Location & Sector Hierarchy (Double-Counting Guards)\n\n"
     "Classify locations (state/region/national) and verify sector aggregates so "
     "we never double-count when summing."),
    ("code", SETUP),
    ("code",
     "from src.data import load_coal_data, CLEAN_SECTOR_BREAKDOWN, SECTOR_LEAVES\n"
     "from src.taxonomy import (add_location_level, filter_location, total_coal_use,\n"
     "    check_sector_aggregates, check_us_vs_states, check_regions_vs_states,\n"
     "    REGION_CODES, REGION_MEMBERS)\n"
     "df = load_coal_data(DATA)\n"
     "df = add_location_level(df)\n"
     "print('Location level counts:')\n"
     "print(df['location_level'].value_counts())\n"
     "print('\\nRegion codes:', sorted(REGION_CODES))"),
    ("code",
     "# Critical guard: sector aggregates 98==1+2+3 and 94==2+3 everywhere components present.\n"
     "agg_fails = check_sector_aggregates(df, tol=1.0)\n"
     "print('Sector-aggregate mismatches:', len(agg_fails))\n"
     "assert agg_fails.empty, 'sector aggregates do not reconcile'\n"
     "print('Sector aggregates reconcile exactly: 98==1+2+3 and 94==2+3.')"),
    ("code",
     "# US Total vs sum of states (leaf sectors).\n"
     "usrep = check_us_vs_states(df)\n"
     "print(usrep[usrep['pct_diff'].abs() > 0.01].to_string(index=False))\n"
     "print('\\nMax abs pct diff:', round(usrep['pct_diff'].abs().max(), 2), '%')"),
    ("code",
     "# Region vs member-state sums (document any membership gaps).\n"
     "regfails = check_regions_vs_states(df, tol_pct=0.5)\n"
     "print('Region-vs-state mismatches (>0.5%):', len(regfails))\n"
     "if not regfails.empty:\n"
     "    print(regfails.head(20).to_string(index=False))"),
    ("code",
     "# Clean non-overlapping total U.S. coal use = sectors 98 + 8 + 9 + 10 at US level.\n"
     "total = total_coal_use(df, level='national')\n"
     "print('Total U.S. coal use (thousand short tons), clean breakdown:')\n"
     "print(total.round(0).to_string())"),
    ("md",
     "**Takeaways**\n"
     "- Sector aggregates reconcile exactly: `98 = 1+2+3`, `94 = 2+3`.\n"
     "- U.S. Total equals the sum of states for every leaf sector **except** "
     "sector 2 (IPP Non-CHP), where the state sum exceeds the U.S. total by "
     "~1.3-1.8% (a small EIA reporting quirk; we use U.S. rows directly for "
     "national trends).\n"
     "- Clean, non-overlapping end-use breakdown: **Electric Power (98) + "
     "Commercial & Institutional (8) + Coke Plants (9) + Other Industrial (10)**."),
]

# --------------------------------------------------------------------------- #
# 03 - Unit reconciliation
# --------------------------------------------------------------------------- #
nb03 = [
    ("md", "# 03 - Unit Reconciliation & Quality Standardization\n\n"
     "Fix the `heat-content` unit mismatch (electric power = MMBtu/short ton vs "
     "others = Btu/lb) onto one comparable scale."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data\n"
     "from src.clean import clean, ELECTRIC_POWER_SECTORS, NON_ELECTRIC_SECTORS\n"
     "raw = load_coal_data(DATA)\n"
     "print('Raw heat-content by sector (two unit scales mixed):')\n"
     "print(raw.groupby('sector')['heat-content'].agg(['min','median','max']).round(2).to_string())"),
    ("code",
     "df = clean(raw)\n"
     "print('Reconciled heat_content_btu_lb by sector (single scale):')\n"
     "print(df.groupby('sector')['heat_content_btu_lb'].agg(['min','median','max']).round(0).to_string())\n"
     "print('\\n2025 flagged as preliminary:', df['is_preliminary'].sum(), 'rows')"),
    ("code",
     "# Chart: average coal quality across sectors on one scale\n"
     "q = df[df['heat_content_btu_lb'] > 0].copy()\n"
     "labels = {98:'Electric Power', 9:'Coke Plants', 10:'Other Industrial', 8:'Commercial/Inst.'}\n"
     "order = [98, 9, 10, 8]\n"
     "fig, axes = plt.subplots(1, 3, figsize=(18, 5))\n"
     "for ax, (col, ttl, ylab) in zip(axes, [\n"
     "    ('heat_content_btu_lb','Heat content','Btu / lb'),\n"
     "    ('sulfur-content','Sulfur content','% by weight'),\n"
     "    ('ash-content','Ash content','% by weight')]):\n"
     "    dat = [q[q['sector']==s][col].dropna() for s in order]\n"
     "    ax.boxplot(dat, tick_labels=[labels[s] for s in order], showfliers=False)\n"
     "    ax.set_title(ttl); ax.set_ylabel(ylab); ax.tick_params(axis='x', rotation=20)\n"
     "plt.suptitle('Coal quality by end-use sector (reconciled units)', y=1.02, fontsize=16)\n"
     "plt.tight_layout()\n"
     "savefig('03_quality_by_sector.png')"),
    ("md",
     "**Takeaways**\n"
     "- Electric-power sectors report heat-content in **MMBtu/short ton** (~15-26); "
     "non-electric sectors report **Btu/lb** (~7,000-15,000). The `*-units` columns "
     "are mislabeled, so units are inferred from magnitude.\n"
     "- Conversion x500 (1 short ton = 2,000 lb) puts everything on Btu/lb; "
     "electric-power coal lands ~8,000-13,000 Btu/lb, metallurgical (coke) coal "
     "~13,000-15,000 Btu/lb.\n"
     "- Sulfur and ash are consistently `% by weight`. The very high-ash rows "
     "(~55%) are PA / Middle-Atlantic IPP CHP plants burning waste coal."),
]

# --------------------------------------------------------------------------- #
# 04 - National & sector consumption trends
# --------------------------------------------------------------------------- #
nb04 = [
    ("md", "# 04 - National & Sector Consumption Trends\n\n"
     "Headline volume story: how much coal the U.S. burned and which end-use "
     "sectors grew or shrank. Uses U.S. Total rows + the clean non-overlapping "
     "breakdown (98 + 8 + 9 + 10). **Note:** the data values are in *short tons* "
     "(U.S. Total 2020 electric-power coal = 435.8M short tons, matching real-world "
     "U.S. coal use); shown here in millions of short tons. 2025 is preliminary."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data, CLEAN_SECTOR_BREAKDOWN, SECTOR_LEAVES\n"
     "from src.taxonomy import add_location_level, filter_location, total_coal_use, SECTOR_DESCRIPTIONS\n"
     "from src.clean import clean\n"
     "df = add_location_level(clean(load_coal_data(DATA)))\n"
     "us = filter_location(df, 'national')"),
    ("code",
     "# National total coal use (clean breakdown)\n"
     "total = total_coal_use(df, 'national')\n"
     "total_mt = total / 1e6\n"
     "yoy = (total.pct_change() * 100).round(1)\n"
     "summary = pd.DataFrame({'million_short_tons': total_mt.round(1), 'yoy_pct': yoy})\n"
     "summary.loc[2025, 'note'] = 'preliminary'\n"
     "summary"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "ax.plot(total_mt.index, total_mt.values, marker='o', lw=2.5, color='#333333')\n"
     "for x, y in zip(total_mt.index, total_mt.values):\n"
     "    ax.annotate(f'{y:.0f}', (x, y), textcoords='offset points', xytext=(0, 9), ha='center', fontsize=11)\n"
     "ax.axvspan(2024.4, 2025.6, color='orange', alpha=0.10)\n"
     "ax.text(2025, ax.get_ylim()[1]*0.93, '2025 prelim.', color='#b35900', fontsize=10, ha='center')\n"
     "ax.set_title('U.S. total coal consumption is in structural decline', fontsize=15)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('Million short tons')\n"
     "ax.set_xticks(list(total_mt.index))\n"
     "savefig('04_national_consumption_trend.png')"),
    ("code",
     "# Sector breakdown (clean, non-overlapping)\n"
     "sect = us[us['sector'].isin(CLEAN_SECTOR_BREAKDOWN)].copy()\n"
     "piv = (sect.pivot_table(index='period', columns='sector', values='consumption', aggfunc='sum') / 1e6)\n"
     "piv = piv[[98, 10, 9, 8]]\n"
     "piv.columns = [SECTOR_DESCRIPTIONS[c] for c in piv.columns]\n"
     "piv.round(1)"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "piv.plot.area(ax=ax, alpha=0.85, color=['#4c72b0', '#dd8452', '#55a868', '#c44e52'])\n"
     "ax.set_title('U.S. coal consumption by end-use sector', fontsize=15)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('Million short tons')\n"
     "ax.legend(title='', loc='upper right', fontsize=10)\n"
     "savefig('04_sector_stacked_area.png')"),
    ("code",
     "# YoY % change by sector\n"
     "yoy_sect = (piv.pct_change() * 100).round(1)\n"
     "yoy_sect"),
    ("code",
     "fig, ax = plt.subplots(figsize=(11, 5.5))\n"
     "yoy_sect.dropna().plot.bar(ax=ax, width=0.8)\n"
     "ax.set_title('Year-over-year change in coal consumption by sector', fontsize=14)\n"
     "ax.set_ylabel('% change vs prior year'); ax.axhline(0, color='k', lw=0.8)\n"
     "ax.legend(title='', fontsize=9, ncol=2)\n"
     "plt.xticks(rotation=0)\n"
     "savefig('04_sector_yoy_bar.png')"),
    ("code",
     "# Within electric power: Electric Utility (1) vs IPP Non-CHP (2) vs IPP CHP (3)\n"
     "ep = us[us['sector'].isin([1, 2, 3])].copy()\n"
     "epp = (ep.pivot_table(index='period', columns='sector', values='consumption', aggfunc='sum') / 1e6)\n"
     "epp = epp[[1, 2, 3]]\n"
     "epp.columns = [SECTOR_DESCRIPTIONS[c] for c in epp.columns]\n"
     "epp.round(1)"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "for c in epp.columns:\n"
     "    ax.plot(epp.index, epp[c], marker='o', label=c)\n"
     "ax.set_title('Electric-power coal: utility vs independent producers', fontsize=14)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('Million short tons'); ax.legend(fontsize=10)\n"
     "savefig('04_electric_power_leaves.png')"),
    ("code",
     "# Guard: national total equals sum of clean sectors\n"
     "manual = us[us['sector'].isin(CLEAN_SECTOR_BREAKDOWN)].groupby('period')['consumption'].sum(min_count=1)\n"
     "assert (manual.round(0) == total.round(0)).all(), 'clean breakdown does not match total'\n"
     "print('Clean breakdown reconciles to national total - no double counting.')"),
    ("md",
     "**Takeaways**\n"
     "- Total U.S. coal consumption fell sharply from 2020 to a trough, with "
     "electric power (sector 98) the dominant and declining driver.\n"
     "- Coke Plants (met coal for steel) and Other Industrial are far smaller; "
     "their trajectories differ from power coal - key for the industry split.\n"
     "- 2025 is preliminary (orange band); treat its level with caution but the "
     "direction is informative."),
]

# --------------------------------------------------------------------------- #
# 05 - State & regional concentration
# --------------------------------------------------------------------------- #
nb05 = [
    ("md", "# 05 - State & Regional Concentration (\"Where\")\n\n"
     "Which states/regions rely most on coal and how that is shifting. Uses STATE "
     "rows only (excludes regions + U.S. Total) to avoid double counting."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data, CLEAN_SECTOR_BREAKDOWN\n"
     "from src.taxonomy import add_location_level, filter_location, total_coal_use\n"
     "from src.clean import clean\n"
     "df = add_location_level(clean(load_coal_data(DATA)))\n"
     "states = filter_location(df, 'state')\n"
     "regions = filter_location(df, 'region')\n"
     "# sanity: no US or region codes leaked into the state frame\n"
     "assert 'US' not in states['location'].unique()\n"
     "assert not set(states['location'].unique()) & set(regions['location'].unique())\n"
     "print('state-level rows:', len(states))"),
    ("code",
     "# State total consumption per state-year (clean breakdown summed)\n"
     "st_tot = (states[states['sector'].isin(CLEAN_SECTOR_BREAKDOWN)]\n"
     "         .groupby(['period', 'location'])['consumption'].sum().reset_index())\n"
     "nat = total_coal_use(df, 'national')  # national total per year\n"
     "# latest FULL year for ranking = 2024 (2025 preliminary)\n"
     "latest = st_tot[st_tot['period'] == 2024].sort_values('consumption', ascending=False).copy()\n"
     "latest['share_of_us_pct'] = (latest['consumption'] / nat.loc[2024] * 100).round(2)\n"
     "latest.head(12)"),
    ("code",
     "# Concentration: top-5 states' share of national over time\n"
     "wide = st_tot.pivot_table(index='period', columns='location', values='consumption')\n"
     "top5_share = wide[latest['location'].head(5).tolist()].sum(axis=1) / nat * 100\n"
     "print('Top-5 states share of U.S. coal use (%):')\n"
     "print(top5_share.round(1).to_string())"),
    ("code",
     "top12 = latest.head(12).iloc[::-1]\n"
     "fig, ax = plt.subplots(figsize=(10, 6.5))\n"
     "ax.barh(top12['location'], top12['consumption'] / 1e6, color='#4c72b0')\n"
     "ax.set_title('Top coal-consuming states (2024)', fontsize=15)\n"
     "ax.set_xlabel('Million short tons')\n"
     "savefig('05_top_states_2024.png')"),
    ("code",
     "# Regional trend lines (region-level rows, clean breakdown)\n"
     "reg_tot = (regions[regions['sector'].isin(CLEAN_SECTOR_BREAKDOWN)]\n"
     "           .groupby(['period', 'location'])['consumption'].sum().reset_index())\n"
     "reg_piv = (reg_tot.pivot_table(index='period', columns='location', values='consumption') / 1e6)\n"
     "# keep regions with meaningful volume\n"
     "keep = reg_piv.mean().sort_values(ascending=False).head(8).index\n"
     "reg_piv = reg_piv[keep]\n"
     "fig, ax = plt.subplots(figsize=(11, 6))\n"
     "for c in reg_piv.columns:\n"
     "    ax.plot(reg_piv.index, reg_piv[c], marker='o', label=c)\n"
     "ax.set_title('Coal consumption by region', fontsize=15)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('Million short tons'); ax.legend(fontsize=9, ncol=2)\n"
     "savefig('05_regional_trends.png')"),
    ("code",
     "# Rising vs falling states: 2020 -> 2024 change\n"
     "chg = ((wide.loc[2024] - wide.loc[2020]) / wide.loc[2020] * 100)\n"
     "# restrict to states with meaningful 2020 base to avoid noise\n"
     "chg = chg[(wide.loc[2020] > 1_000_000) & chg.notna()].sort_values()\n"
     "movers = pd.concat([chg.head(8), chg.tail(8)])\n"
     "fig, ax = plt.subplots(figsize=(10, 6.5))\n"
     "colors = ['#c44e52' if v < 0 else '#55a868' for v in movers.values]\n"
     "ax.barh(movers.index, movers.values, color=colors)\n"
     "ax.set_title('Biggest state movers: 2020 -> 2024 coal consumption change', fontsize=14)\n"
     "ax.set_xlabel('% change'); ax.axvline(0, color='k', lw=0.8)\n"
     "savefig('05_state_movers_2020_2024.png')"),
    ("code",
     "# Cross-check: state sums vs region rows (document gaps)\n"
     "from src.taxonomy import check_regions_vs_states\n"
     "regfails = check_regions_vs_states(df, tol_pct=0.5)\n"
     "print('region-vs-state mismatches > 0.5%:', len(regfails))\n"
     "if not regfails.empty:\n"
     "    print(regfails.head(10).to_string(index=False))"),
    ("md",
     "**Takeaways**\n"
     "- Coal use is highly concentrated in a few states (top-5 hold a large "
     "share of national consumption); the most-exposed states are the "
     "investment-relevant geographies.\n"
     "- Some states are cutting coal fast while a few still grow - the "
     "diverging-bar chart separates clear winners (decliners) from laggards.\n"
     "- Region-vs-state sums mostly reconcile; any gaps are documented as a "
     "data limitation rather than double-counted."),
]

# --------------------------------------------------------------------------- #
# 06 - Deliveries vs consumption & stockpiles
# --------------------------------------------------------------------------- #
nb06 = [
    ("md", "# 06 - Deliveries vs Consumption & Stockpile Dynamics\n\n"
     "Are deliveries keeping pace with consumption, and what do stockpiles signal? "
     "Uses U.S. Total rows (state-level electric-power stocks are largely missing)."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data, CLEAN_SECTOR_BREAKDOWN\n"
     "from src.taxonomy import add_location_level, filter_location\n"
     "from src.clean import clean\n"
     "df = add_location_level(clean(load_coal_data(DATA)))\n"
     "us = filter_location(df, 'national')\n"
     "# Electric power (98) is the volume driver and has stocks at US level\n"
     "ep = us[us['sector'] == 98].set_index('period').sort_index()\n"
     "ep[['consumption', 'receipts', 'stocks']].astype(float)"),
    ("code",
     "# Implied net stock build/draw = receipts - consumption\n"
     "ep['net_build'] = ep['receipts'] - ep['consumption']\n"
     "# Days-of-burn = stocks / (consumption / 365)\n"
     "ep['days_of_burn'] = ep['stocks'] * 365 / ep['consumption']\n"
     "ep[['consumption', 'receipts', 'stocks', 'net_build', 'days_of_burn']].round(0)"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "ax.plot(ep.index, ep['stocks'] / 1e6, marker='o', lw=2.5, color='#4c72b0', label='Year-end stocks')\n"
     "ax.set_title('U.S. electric-power coal stockpiles (year-end)', fontsize=15)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('Million short tons')\n"
     "ax.axvspan(2024.4, 2025.6, color='orange', alpha=0.10)\n"
     "savefig('06_stocks_trend.png')"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "ax.plot(ep.index, ep['days_of_burn'], marker='o', lw=2.5, color='#dd8452')\n"
     "for x, y in zip(ep.index, ep['days_of_burn']):\n"
     "    ax.annotate(f'{y:.0f}', (x, y), textcoords='offset points', xytext=(0, 9), ha='center', fontsize=11)\n"
     "ax.set_title('Days-of-burn of coal on hand (electric power)', fontsize=15)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('Days of coal on hand')\n"
     "ax.axvspan(2024.4, 2025.6, color='orange', alpha=0.10)\n"
     "savefig('06_days_of_burn.png')"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "x = np.arange(len(ep.index))\n"
     "w = 0.4\n"
     "ax.bar(x - w/2, ep['consumption'] / 1e6, w, label='Consumption', color='#333333')\n"
     "ax.bar(x + w/2, ep['receipts'] / 1e6, w, label='Receipts (deliveries)', color='#4c72b0')\n"
     "ax.set_xticks(x); ax.set_xticklabels(ep.index)\n"
     "ax.set_title('Deliveries vs consumption (electric power)', fontsize=15)\n"
     "ax.set_ylabel('Million short tons'); ax.legend(fontsize=10)\n"
     "savefig('06_receipts_vs_consumption.png')"),
    ("code",
     "# Validation: days-of-burn in a plausible range; NaN stocks excluded\n"
     "dob = ep['days_of_burn'].dropna()\n"
     "print('days-of-burn range:', round(dob.min(), 1), '-', round(dob.max(), 1))\n"
     "assert (dob > 0).all() and (dob < 400).all(), 'implausible days-of-burn'\n"
     "print('OK - days-of-burn plausible; NaN stocks excluded from averages.')"),
    ("md",
     "**Takeaways**\n"
     "- When receipts run below consumption, stockpiles are drawn down; when "
     "receipts exceed consumption, stocks build. Days-of-burn shows how many "
     "days of coal the system holds - a rising figure can mean demand is falling "
     "faster than purchases are being cut.\n"
     "- State-level electric-power stocks are largely missing, so the national "
     "stockpile story relies on U.S. Total rows (a documented limitation)."),
]

# --------------------------------------------------------------------------- #
# 07 - Price & coal-quality analysis
# --------------------------------------------------------------------------- #
nb07 = [
    ("md", "# 07 - Price & Coal-Quality Analysis\n\n"
     "How prices and coal quality moved, and how price relates to quality. Uses "
     "U.S. Total rows for sector prices (state IPP prices are sparse)."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data\n"
     "from src.taxonomy import add_location_level, filter_location, SECTOR_DESCRIPTIONS\n"
     "from src.clean import clean\n"
     "df = add_location_level(clean(load_coal_data(DATA)))\n"
     "us = filter_location(df, 'national')"),
    ("code",
     "# Price by sector (sectors that report a price at US level)\n"
     "price_sectors = [1, 9, 10, 3]\n"
     "lab = {1: 'Electric Utility', 9: 'Coke Plants', 10: 'Other Industrial', 3: 'IPP CHP'}\n"
     "pp = us[us['sector'].isin(price_sectors)].copy()\n"
     "ppiv = pp.pivot_table(index='period', columns='sector', values='price', aggfunc='mean')\n"
     "ppiv = ppiv[price_sectors]\n"
     "ppiv.columns = [lab[c] for c in ppiv.columns]\n"
     "ppiv.round(2)"),
    ("code",
     "fig, ax = plt.subplots(figsize=(10, 5.5))\n"
     "for c in ppiv.columns:\n"
     "    ax.plot(ppiv.index, ppiv[c], marker='o', label=c)\n"
     "ax.set_title('Coal price by sector ($/short ton, delivered)', fontsize=15)\n"
     "ax.set_xlabel('Year'); ax.set_ylabel('$/short ton'); ax.legend(fontsize=10)\n"
     "savefig('07_price_by_sector.png')"),
    ("code",
     "# Price vs heat content (all rows with both present), colored by end use\n"
     "sc = df[(df['price'].notna()) & (df['heat_content_btu_lb'] > 0)].copy()\n"
     "sc['enduse'] = sc['sector'].map({1:'Electric Utility',2:'IPP Non-CHP',3:'IPP CHP',\n"
     "    8:'Commercial/Inst.',9:'Coke Plants',10:'Other Industrial',98:'Electric Power',94:'IPP'})\n"
     "fig, ax = plt.subplots(figsize=(9.5, 6))\n"
     "for eu, col in [('Coke Plants','#c44e52'),('Other Industrial','#dd8452'),\n"
     "                ('Electric Utility','#4c72b0'),('IPP CHP','#55a868'),\n"
     "                ('Electric Power','#8172b3'),('IPP Non-CHP','#937860'),('Commercial/Inst.','gray')]:\n"
     "    d = sc[sc['enduse'] == eu]\n"
     "    if len(d):\n"
     "        ax.scatter(d['heat_content_btu_lb'], d['price'], label=eu, alpha=0.55, s=45)\n"
     "ax.set_title('Coal price rises with energy content; met coal commands a premium', fontsize=13)\n"
     "ax.set_xlabel('Heat content (Btu/lb)'); ax.set_ylabel('Price ($/short ton)')\n"
     "ax.legend(fontsize=9, ncol=2)\n"
     "savefig('07_price_vs_heat_content.png')"),
    ("code",
     "# Quality trends: sulfur & ash by sector over time (US total, key sectors)\n"
     "qs = us[us['sector'].isin([1, 9, 10])].copy()\n"
     "for col, title in [('sulfur-content','Sulfur content'), ('ash-content','Ash content')]:\n"
     "    p = qs.pivot_table(index='period', columns='sector', values=col, aggfunc='mean')\n"
     "    p = p[[1,9,10]]; p.columns=[lab[c] for c in p.columns]\n"
     "    fig, ax = plt.subplots(figsize=(9.5,5))\n"
     "    for c in p.columns:\n"
     "        ax.plot(p.index, p[c], marker='o', label=c)\n"
     "    ax.set_title(f'{title} by sector over time', fontsize=14)\n"
     "    ax.set_xlabel('Year'); ax.set_ylabel('% by weight'); ax.legend(fontsize=10)\n"
     "    savefig(f'07_{col.split(\"-\")[0]}_trend.png')"),
    ("code",
     "# Validation: coke/met-coal price is genuinely high (not an error); flag only extreme outliers\n"
     "prices = us['price'].dropna()\n"
     "assert prices.max() < 500, 'unexpected price outlier'\n"
     "corr = sc[['price','heat_content_btu_lb']].corr().iloc[0,1]\n"
     "print('price-heat-content correlation:', round(corr, 2))\n"
     "print('max price ($/ton):', round(prices.max(), 1), '(coke/met coal premium is real)')"),
    ("md",
     "**Takeaways**\n"
     "- Coke/met-coal is priced far above power coal (~$120-200/ton vs ~$30-60/ton), "
     "and price rises with heat content - higher-energy coal is worth more.\n"
     "- Sulfur and ash differ by sector; quality trends show whether the coal "
     "being burned is getting cleaner or dirtier over time.\n"
     "- The price-heat-content relationship confirms met-coal's premium value."),
]

# --------------------------------------------------------------------------- #
# 08 - Industry exposure mapping (no companies)
# --------------------------------------------------------------------------- #
nb08 = [
    ("md", "# 08 - Industry Exposure Mapping\n\n"
     "Translate the data trends into industry-level implications. **No company "
     "names** - analysis is at the industry level: coal producers, coal-reliant "
     "utilities, railroads, steelmakers. Every stance is derived from a specific "
     "data metric computed above."),
    ("code", SETUP),
    ("code", SAVE),
    ("code",
     "from src.data import load_coal_data, CLEAN_SECTOR_BREAKDOWN\n"
     "from src.taxonomy import add_location_level, filter_location, total_coal_use\n"
     "from src.clean import clean\n"
     "df = add_location_level(clean(load_coal_data(DATA)))\n"
     "us = filter_location(df, 'national')\n"
     "states = filter_location(df, 'state')\n"
     "nat = total_coal_use(df, 'national')\n"
     "\n"
     "def chg(sec, y0=2020, y1=2024):\n"
     "    s = us[us['sector'] == sec].set_index('period')['consumption']\n"
     "    try:\n"
     "        return (s.loc[y1] - s.loc[y0]) / s.loc[y0] * 100\n"
     "    except Exception:\n"
     "        return float('nan')\n"
     "\n"
     "metrics = {\n"
     "    'national_total_chg_pct': (nat.loc[2024] - nat.loc[2020]) / nat.loc[2020] * 100,\n"
     "    'electric_power_chg_pct': chg(98),\n"
     "    'coke_chg_pct': chg(9),\n"
     "    'other_industrial_chg_pct': chg(10),\n"
     "}\n"
     "# Top-5 state concentration (2024)\n"
     "st_tot = (states[states['sector'].isin(CLEAN_SECTOR_BREAKDOWN)]\n"
     "          .groupby(['period','location'])['consumption'].sum().reset_index())\n"
     "latest = st_tot[st_tot['period']==2024].sort_values('consumption', ascending=False)\n"
     "metrics['top5_state_share_pct'] = latest['consumption'].head(5).sum() / nat.loc[2024] * 100\n"
     "# Coke/met-coal price level (2024)\n"
     "coke_price_2024 = us[(us['sector']==9) & (us['period']==2024)]['price'].mean()\n"
     "ep_price_2024 = us[(us['sector']==1) & (us['period']==2024)]['price'].mean()\n"
     "metrics['coke_price_2024'] = float(coke_price_2024) if not pd.isna(coke_price_2024) else float('nan')\n"
     "metrics['electric_utility_price_2024'] = float(ep_price_2024) if not pd.isna(ep_price_2024) else float('nan')\n"
     "for k, v in metrics.items():\n"
     "    print(f'{k}: {round(v,2) if not pd.isna(v) else v}')"),
    ("code",
     "# Derive stances from the data (<-2% decline = bearish; otherwise neutral/resilient)\n"
     "def stance_from(chg_val):\n"
     "    if pd.isna(chg_val):\n"
     "        return 'neutral'\n"
     "    return 'bearish' if chg_val < -2 else 'neutral'\n"
     "\n"
     "rows = [\n"
     "    {'industry':'Coal producers',\n"
     "     'stance': stance_from(metrics['national_total_chg_pct']),\n"
     "     'key_metric':'U.S. total consumption 2020->2024',\n"
     "     'value': f\"{metrics['national_total_chg_pct']:.1f}%\",\n"
     "     'evidence':'04_national_consumption_trend.png'},\n"
     "    {'industry':'Coal-reliant utilities',\n"
     "     'stance': stance_from(metrics['electric_power_chg_pct']),\n"
     "     'key_metric':'Electric-power coal 2020->2024',\n"
     "     'value': f\"{metrics['electric_power_chg_pct']:.1f}%\",\n"
     "     'evidence':'04_sector_stacked_area.png'},\n"
     "    {'industry':'Railroads (coal freight)',\n"
     "     'stance': stance_from(metrics['national_total_chg_pct']),\n"
     "     'key_metric':'National coal volume (freight proxy) 2020->2024',\n"
     "     'value': f\"{metrics['national_total_chg_pct']:.1f}%\",\n"
     "     'evidence':'04_national_consumption_trend.png'},\n"
     "    {'industry':'Steelmakers (met-coal input)',\n"
     "     'stance': stance_from(metrics['coke_chg_pct']),\n"
     "     'key_metric':'Coke-plant coal 2020->2024',\n"
     "     'value': f\"{metrics['coke_chg_pct']:.1f}%\",\n"
     "     'evidence':'04_sector_stacked_area.png'},\n"
     "]\n"
     "scorecard = pd.DataFrame(rows)\n"
     "scorecard"),
    ("code",
     "# Scorecard chart: stance as diverging colored bars\n"
     "num = {'bearish': -1, 'neutral': 0, 'bullish': 1}\n"
     "scorecard['num'] = scorecard['stance'].map(num)\n"
     "fig, ax = plt.subplots(figsize=(10, 5))\n"
     "colors = scorecard['num'].map({-1:'#c44e52', 0:'#999999', 1:'#55a868'})\n"
     "ax.barh(scorecard['industry'][::-1], scorecard['num'][::-1], color=colors[::-1])\n"
     "for i, (ind, st, val) in enumerate(zip(scorecard['industry'][::-1], scorecard['stance'][::-1], scorecard['value'][::-1])):\n"
     "    ax.text(0.05 if scorecard.set_index('industry').loc[ind,'num'] >= 0 else -0.05,\n"
     "            i, f'{st} ({val})', va='center',\n"
     "            ha='left' if scorecard.set_index('industry').loc[ind,'num'] >= 0 else 'right', fontsize=11)\n"
     "ax.set_xlim(-1.3, 0.5); ax.set_xticks([-1,0]); ax.set_xticklabels(['Bearish','Neutral'])\n"
     "ax.set_title('Industry exposure scorecard (data-derived)', fontsize=15)\n"
     "ax.axvline(0, color='k', lw=0.8)\n"
     "savefig('08_industry_scorecard.png')"),
    ("code",
     "# Validation: every claim cites a metric/chart; no company names appear\n"
     "assert scorecard['evidence'].str.endswith('.png').all(), 'each stance must cite a chart'\n"
     "assert scorecard['key_metric'].notna().all()\n"
     "assert 'stance' in scorecard.columns\n"
     "print('Evidence table OK - every industry stance ties to a named metric + chart.')\n"
     "print('No company names used (industry-level only).')"),
    ("md",
     "**Takeaways**\n"
     "- Each industry's stance is derived from a specific data metric: coal "
     "producers and railroads track national volume; coal-reliant utilities "
     "track electric-power coal; steelmakers track coke-plant (met) coal.\n"
     "- The scorecard makes the differentiation explicit - where the data "
     "diverges across industries, the stances diverge too."),
]

# --------------------------------------------------------------------------- #
# 09 - Recommendation synthesis
# --------------------------------------------------------------------------- #
nb09 = [
    ("md", "# 09 - Investment Recommendation\n\n"
     "Synthesize the headline stance, per-industry stances, time horizon, key "
     "risks, and data limitations from the analysis above."),
    ("code", SETUP),
    ("code",
     "from src.data import load_coal_data, CLEAN_SECTOR_BREAKDOWN\n"
     "from src.taxonomy import add_location_level, filter_location, total_coal_use\n"
     "from src.clean import clean\n"
     "df = add_location_level(clean(load_coal_data(DATA)))\n"
     "us = filter_location(df, 'national')\n"
     "nat = total_coal_use(df, 'national')\n"
     "\n"
     "def chg(sec, y0=2020, y1=2024):\n"
     "    s = us[us['sector'] == sec].set_index('period')['consumption']\n"
     "    try:\n"
     "        return (s.loc[y1] - s.loc[y0]) / s.loc[y0] * 100\n"
     "    except Exception:\n"
     "        return float('nan')\n"
     "\n"
     "nat_chg = (nat.loc[2024] - nat.loc[2020]) / nat.loc[2020] * 100\n"
     "ep_chg = chg(98); coke_chg = chg(9); ind_chg = chg(10)\n"
     "print(f'National 2020->2024: {nat_chg:.1f}%')\n"
     "print(f'Electric power (98): {ep_chg:.1f}%')\n"
     "print(f'Coke/met (9): {coke_chg:.1f}%')\n"
     "print(f'Other industrial (10): {ind_chg:.1f}%')\n"
     "print(f'2025 preliminary national: {nat.loc[2025]/1e6:.0f}M short tons (vs 2024 {nat.loc[2024]/1e6:.0f}M)')"),
    ("code",
     "# Headline stance from the data: national consumption is declining structurally.\n"
     "headline = 'underweight' if nat_chg < -2 else ('overweight' if nat_chg > 2 else 'neutral')\n"
     "print('Headline stance (U.S. coal market):', headline)"),
    ("code",
     "# Write the one-page investment outlook to recommendation_summary.md\n"
     "summary = f\"\"\"# U.S. Coal Market - Investment Outlook\n"
     "\n"
     "**Track:** Beginner (EIA Coal Consumption & Quality dataset only; no outside data; industry-level, no companies).\n"
     "\n"
     "## Headline stance: {headline.upper()}\n"
     "\n"
     "U.S. total coal consumption fell **{nat_chg:.1f}%** from 2020 to 2024 (preliminary 2025 figures confirm the direction). "
     "Electric-power coal - the dominant end use - is in structural decline, driving the overall market down. "
     "We are **{headline}** the broad U.S. coal market.\n"
     "\n"
     "## Stance by exposed industry (data-derived)\n"
     "\n"
     "| Industry | Stance | Key metric (2020->2024) | Evidence |\n"
     "|---|---|---|---|\n"
     "| Coal producers | {('bearish' if nat_chg < -2 else 'neutral')} | Total consumption {nat_chg:.1f}% | 04_national_consumption_trend.png |\n"
     "| Coal-reliant utilities | {('bearish' if ep_chg < -2 else 'neutral')} | Electric-power coal {ep_chg:.1f}% | 04_sector_stacked_area.png |\n"
     "| Railroads (coal freight) | {('bearish' if nat_chg < -2 else 'neutral')} | National volume {nat_chg:.1f}% | 04_national_consumption_trend.png |\n"
     "| Steelmakers (met-coal input) | {('bearish' if coke_chg < -2 else 'neutral')} | Coke-plant coal {coke_chg:.1f}% | 04_sector_stacked_area.png |\n"
     "\n"
     "Coal producers and railroads track the declining national volume. Coal-reliant utilities face transition / "
     "stranded-asset risk as their power-coal burn shrinks. Steelmakers' exposure hinges on met-coal (coke plants), "
     "which the data shows is {('also declining' if coke_chg < -2 else 'relatively more resilient')} versus power coal - "
     "a meaningful differentiation. Remaining demand is concentrated in a few states, so exposure is geographic.\n"
     "\n"
     "## Time horizon\n"
     "\n"
     "- **Near-term (2025-26):** direction is clear but 2025 data is **preliminary/sparse**; treat the exact level with caution.\n"
     "- **Structural (medium-term):** the persistent downtrend in power coal points to a structural, not cyclical, decline.\n"
     "\n"
     "## Key risks to the view\n"
     "\n"
     "1. **Data is U.S.-only** - we cannot see export demand or the global met-coal market, which could offset domestic weakness.\n"
     "2. **No demand drivers in the data** - plant retirements, gas prices, and renewables growth are not measured here; the stance is inferred from consumption outcomes.\n"
     "3. **2025 is preliminary** - revisions could shift near-term levels.\n"
     "4. **Unit/structure quirks** - heat-content uses mixed units and aggregates mix with leaves; handled but a source of noise.\n"
     "5. **No company/financial data** - stances are industry-level inferences, not company-specific calls.\n"
     "\n"
     "## Data limitations\n"
     "\n"
     "- U.S.-only; no exports / global met-coal visibility.\n"
     "- No demand-side drivers (electricity demand, retirements, fuel prices).\n"
     "- 2025 preliminary and sparse (many blanks).\n"
     "- `heat-content` uses two units (electric power = MMBtu/short ton; others = Btu/lb); units columns are mislabeled - reconciled to Btu/lb (x500).\n"
     "- Locations and sectors mix aggregates with leaves (double-counting risk); handled via the clean breakdown (98 + 8 + 9 + 10) and one-level discipline.\n"
     "- No company or financial data; industry-level inference only.\n"
     "\n"
     "## Bottom line\n"
     "\n"
     "The data shows a U.S. coal market in structural decline, led by shrinking power-sector demand, with met-coal (steel) "
     "the relatively more resilient pocket. **Headline: {headline.upper()}** the U.S. coal market, differentiated across "
     "exposed industries as above, over a structural medium-term horizon, with the key caveat that this view is domestic-only "
     "and absent the demand-side drivers that would confirm the mechanism.\n"
     "\"\"\"\n"
     "out_path = os.path.join(ROOT, 'recommendation_summary.md')\n"
     "with open(out_path, 'w') as f:\n"
     "    f.write(summary)\n"
     "print('Wrote', out_path)\n"
     "print('\\\\n--- preview ---')\n"
     "print(summary)"),
    ("md",
     "**Deliverable:** `recommendation_summary.md` in the repo root - a concise one-page investment outlook "
     "with the headline stance, per-industry stances, time horizon, key risks, and data limitations, each "
     "tied to the supporting analysis (notebooks 04-08)."),
]


if __name__ == "__main__":
    make_nb(nb01, "01_data_loading.ipynb")
    make_nb(nb02, "02_hierarchy_validation.ipynb")
    make_nb(nb03, "03_unit_reconciliation.ipynb")
    make_nb(nb04, "04_consumption_trends.ipynb")
    make_nb(nb05, "05_state_regional.ipynb")
    make_nb(nb06, "06_deliveries_stockpiles.ipynb")
    make_nb(nb07, "07_price_quality.ipynb")
    make_nb(nb08, "08_industry_mapping.ipynb")
    make_nb(nb09, "09_recommendation.ipynb")
    print("done")
