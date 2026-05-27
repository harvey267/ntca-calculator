# NTCA Pension Calculator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Tools for calculating NTCA §417(e) lump sum pension options and running retirement income projections.**

Implements the IRS three-segment interest rate model and unisex mortality table to compute present value of pension annuities, with support for partial lump sum elections, retirement window simulation, and Social Security income integration.

---

## What's included

| Tool | Description |
|------|-------------|
| `Python/ntca_lump_sum_calculator.py` | CLI: lump sum present value for a single retirement date |
| `Python/ntca_pension_dashboard/` | Streamlit dashboard: full interactive simulator with retirement window, segment rate sensitivity, and SSA income |
| `Python/segment_rate_pipeline.py` | Downloads Treasury HQM files, extracts segment rates, predicts next month |
| `_resources/` | IRS and NTCA public reference documents |
| `Guide to Understanding Your NTCA Pension Lump Sum.md` | Plain-language explanation of the lump sum calculation method |

---

## Quick start — CLI calculator

```bash
pip install pandas numpy openpyxl requests python-dateutil

python3 Python/ntca_lump_sum_calculator.py \
  --birth-date 1970-01-01 \
  --retirement-date 2030-01-01 \
  --salary 80000 \
  --years 25 \
  --partial-lump 0.25
```

Outputs a summary to stdout and exports `ntca_lump_sum.xlsx` with the full annuity stream.

**Segment rate overrides** (otherwise falls back to built-in August 2025 example rates):
```bash
  --seg1 0.0420 --seg2 0.0529 --seg3 0.0608
```

---

## Quick start — Streamlit dashboard

```bash
pip install streamlit pandas numpy scikit-learn openpyxl requests python-dateutil

cd Python/ntca_pension_dashboard
streamlit run app.py
```

Enter your inputs in the sidebar. To include Social Security projections, upload a CSV with your earnings history:

```bash
cp ../../ssa_earnings.example.csv ssa_earnings.csv
# edit ssa_earnings.csv with your actual year/income values
```

The CSV format is:
```
year,income
2000,35000
2001,38000
...
```

---

## Segment rate pipeline

Downloads the latest HQM yield curve data from Treasury, extracts the three §417(e) segment rate averages, and predicts next month's rates using linear regression:

```bash
pip install pandas scikit-learn openpyxl requests
mkdir hqm_data
python3 Python/segment_rate_pipeline.py
```

Outputs `segment_rates.xlsx` with historical and predicted rates.

---

## Inputs explained

| Field | What it is |
|-------|-----------|
| Birth date | Your date of birth |
| Retirement date | Planned benefit commencement date |
| High-5 salary | Average of your 5 highest compensation years in the last 10 plan years |
| Years of service | Total years of NTCA plan participation (fractions are valid, e.g. 25.833) |
| Partial lump % | Percentage of lump sum to take (remainder stays as monthly annuity) |
| Segment rates | IRS §417(e) rates for the applicable look-back month — see `_resources/` or pull from Treasury |

---

## Disclaimer

This is an educational tool. All calculations are estimates based on publicly available IRS rules and reverse-engineered NTCA methodology. Always verify with NTCA directly for official benefit amounts.

**Maintainer:** Thomas Harvey — [THT Systems](https://www.tomharveytraining.com)
