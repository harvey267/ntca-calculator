from datetime import datetime
from typing import Dict, List

# SSA bend points for 2025 (example — update annually)
BEND_POINTS = {
    2025: {"bend1": 1115, "bend2": 6721}
}

# SSA indexing factors (example — update annually or load from file)
INDEXING_FACTORS = {
    1985: 0.31, 1986: 0.33, 1987: 0.35, 1988: 0.37, 1989: 0.39,
    # ...
    2023: 1.00, 2024: 1.03, 2025: 1.06
}


def calculate_pia(aime: float, bend1: float, bend2: float) -> float:
    """Calculate Primary Insurance Amount based on AIME and bend points."""
    if aime <= bend1:
        return 0.9 * aime
    elif aime <= bend2:
        return 0.9 * bend1 + 0.32 * (aime - bend1)
    else:
        return 0.9 * bend1 + 0.32 * (bend2 - bend1) + 0.15 * (aime - bend2)


def index_earnings(income_by_year: Dict[int, float], claim_year: int) -> List[float]:
    """Index earnings using SSA wage indexing rules."""
    index_base_year = claim_year - 2
    base_factor = INDEXING_FACTORS.get(index_base_year, 1.0)
    indexed = []

    for year, income in income_by_year.items():
        factor = INDEXING_FACTORS.get(year, 1.0)
        if year <= index_base_year:
            indexed_income = income * (base_factor / factor)
        else:
            indexed_income = income  # No indexing for recent years
        indexed.append(indexed_income)

    return indexed


def calculate_aime(indexed_earnings: List[float]) -> float:
    """Calculate Average Indexed Monthly Earnings from top 35 years."""
    top_35 = sorted(indexed_earnings, reverse=True)[:35]
    return sum(top_35) / (35 * 12)


def calculate_ss_benefits(birth_year: int, income_by_year: Dict[int, float]) -> Dict[int, float]:
    """Calculate estimated monthly Social Security benefits at ages 62, 67, and 70."""
    results = {}
    for age in [62, 67, 70]:
        claim_year = birth_year + age
        bend = BEND_POINTS.get(claim_year, BEND_POINTS[2025])  # fallback
        indexed = index_earnings(income_by_year, claim_year)
        aime = calculate_aime(indexed)
        pia = calculate_pia(aime, bend["bend1"], bend["bend2"])

        if age == 62:
            benefit = pia * 0.70
        elif age == 67:
            benefit = pia
        elif age == 70:
            benefit = pia * 1.24

        results[age] = round(benefit, 2)

    return results
