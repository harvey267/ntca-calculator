from datetime import datetime
from typing import Dict, List, Tuple

# ----------------------------------------------------------------------
# 1. Official SSA tables (update annually – sources in comments)
# ----------------------------------------------------------------------
# Average Wage Index (AWI) – https://www.ssa.gov/oact/cola/AWI.html
AWI: Dict[int, float] = {
    1951: 2799.16, 1952: 2973.32, 1953: 3139.44, 1954: 3155.64, 1955: 3301.44,
    # … (all years up to 2024) …
    2022: 63795.13, 2023: 66621.80, 2024: 69846.57
}

# Taxable maximum earnings – https://www.ssa.gov/oact/cola/cbb.html
MAX_EARN: Dict[int, int] = {
    # … (1937-2024) …
    2023: 160200, 2024: 168600, 2025: 176100
}

# PIA bend points by **eligibility year** (year you turn 62)
# https://www.ssa.gov/oact/cola/bendpoints.html
BEND_POINTS: Dict[int, Tuple[int, int]] = {
    2025: (1226, 7391),   # first $1,226 → 90%, next up to $7,391 → 32%, rest → 15%
    # 2026: (1286, 7749),   # add when SSA releases
}

# ----------------------------------------------------------------------
# 2. Core SSA formulas
# ----------------------------------------------------------------------
def _index_one_year(earn: float, year: int, indexing_year: int) -> float:
    """Index a single year's earnings to the indexing_year base."""
    if year >= indexing_year:                     # recent years → no indexing
        return earn
    awi_year = AWI.get(year)
    awi_index = AWI.get(indexing_year, AWI[2024])  # fallback to latest
    if awi_year is None:
        return earn
    factor = awi_index / awi_year
    return earn * factor


def index_earnings(earnings: Dict[int, float], eligibility_year: int) -> Dict[int, float]:
    """Return a dict {year: indexed_earnings} capped at the taxable max."""
    indexing_year = eligibility_year - 2
    indexed = {}
    for yr, inc in earnings.items():
        capped = min(inc, MAX_EARN.get(yr, MAX_EARN[2025]))
        indexed[yr] = round(_index_one_year(capped, yr, indexing_year), 2)
    return indexed


def calculate_aime(indexed_earnings: Dict[int, float]) -> int:
    """AIME = floor( sum(top-35 indexed) / 420 )"""
    values = sorted(indexed_earnings.values(), reverse=True)[:35]
    # pad with zeros if <35 years
    values += [0.0] * (35 - len(values))
    total = sum(values)
    aime = total / 420
    return int(aime)                     # SSA floors to nearest dollar


def calculate_pia(aime: int, eligibility_year: int) -> float:
    """PIA using the bend points for the eligibility year, rounded to nearest dime."""
    bp1, bp2 = BEND_POINTS.get(eligibility_year, BEND_POINTS[2025])
    pia = (
        0.90 * min(aime, bp1) +
        0.32 * max(0, min(aime, bp2) - bp1) +
        0.15 * max(0, aime - bp2)
    )
    return round(pia * 10) / 10          # nearest $0.10


# ----------------------------------------------------------------------
# 3. Early / delayed claiming (exact SSA reduction tables)
# ----------------------------------------------------------------------
def _fra(birth_year: int) -> Tuple[int, int]:
    """Return (FRA years, FRA months)."""
    if birth_year <= 1937:
        return 65, 0
    elif birth_year == 1938:
        return 65, 2
    elif birth_year == 1939:
        return 65, 4
    elif birth_year == 1940:
        return 65, 6
    elif birth_year == 1941:
        return 65, 8
    elif birth_year == 1942:
        return 65, 10
    elif 1943 <= birth_year <= 1954:
        return 66, 0
    elif birth_year == 1955:
        return 66, 2
    elif birth_year == 1956:
        return 66, 4
    elif birth_year == 1957:
        return 66, 6
    elif birth_year == 1958:
        return 66, 8
    elif birth_year == 1959:
        return 66, 10
    else:  # 1960 and later
        return 67, 0


def reduction_factor(claim_age: int, fra_years: int, fra_months: int) -> float:
    """Exact SSA reduction (5/9 % per month for first 36, 5/12 % thereafter)."""
    months_early = (fra_years - claim_age) * 12 - fra_months
    if months_early <= 0:
        return 1.0
    if months_early <= 36:
        return 1 - months_early * (5/9) / 100
    else:
        extra = months_early - 36
        return 1 - (36 * 5/9 + extra * 5/12) / 100


def delay_factor(claim_age: int, fra_years: int, fra_months: int) -> float:
    """8 % per year (2/3 % per month) after FRA, up to age 70."""
    months_late = (claim_age - fra_years) * 12 + fra_months
    if months_late <= 0:
        return 1.0
    capped = min(months_late, (70 - fra_years) * 12 + fra_months)
    return 1 + capped * (2/3) / 100


# ----------------------------------------------------------------------
# 4. Public API – one function you call
# ----------------------------------------------------------------------
def ss_benefits(
    birth_year: int,
    earnings: Dict[int, float],
    claim_ages: List[int] = None
) -> Dict[int, float]:
    """
    Returns {claim_age: monthly_benefit} for the requested ages.
    Default ages: 62, FRA, 70.
    """
    if claim_ages is None:
        fra_y, _ = _fra(birth_year)
        claim_ages = [62, fra_y, 70]

    fra_y, fra_m = _fra(birth_year)
    results = {}

    for age in claim_ages:
        claim_year = birth_year + age
        indexed = index_earnings(earnings, claim_year)
        aime = calculate_aime(indexed)
        pia = calculate_pia(aime, claim_year)

        if age < fra_y or (age == fra_y and fra_m > 0):
            benefit = pia * reduction_factor(age, fra_y, fra_m)
        elif age > fra_y:
            benefit = pia * delay_factor(age, fra_y, fra_m)
        else:
            benefit = pia

        results[age] = round(benefit, 2)

    return results


# ----------------------------------------------------------------------
# 5. Quick demo (replace with your own data)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    demo_earnings = {
        2000: 76000, 2001: 80400, 2002: 84900,
        # … add up to 2024 or later …
        2022: 147000, 2023: 160200, 2024: 168600,
    }

    print(ss_benefits(birth_year=1960, earnings=demo_earnings))
    # Example output (will vary with full history):
    # {62: 2156.30, 67: 3080.40, 70: 3823.70}
