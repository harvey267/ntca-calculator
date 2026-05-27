import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import requests
from io import BytesIO


def parse_args():
    parser = argparse.ArgumentParser(
        description="NTCA §417(e) lump sum calculator — computes present value of pension annuity"
    )
    parser.add_argument("--birth-date",       required=True, help="Date of birth (YYYY-MM-DD)")
    parser.add_argument("--retirement-date",  required=True, help="Planned retirement date (YYYY-MM-DD)")
    parser.add_argument("--salary",           required=True, type=float, help="High-5 average salary ($)")
    parser.add_argument("--years",            required=True, type=float, help="Years of participation")
    parser.add_argument("--partial-lump",     type=float, default=0.0,
                        help="Partial lump sum percentage (0.0, 0.25, 0.5, etc.) — default 0.0 (full annuity)")
    parser.add_argument("--seg1",             type=float, default=None,
                        help="Segment 1 rate override (decimal, e.g. 0.0420). Default: fetched from pipeline.")
    parser.add_argument("--seg2",             type=float, default=None,
                        help="Segment 2 rate override (decimal)")
    parser.add_argument("--seg3",             type=float, default=None,
                        help="Segment 3 rate override (decimal)")
    parser.add_argument("--output",           default="ntca_lump_sum.xlsx",
                        help="Output filename (default: ntca_lump_sum.xlsx)")
    return parser.parse_args()


def load_irs_unisex_mortality():
    """Downloads the IRS §417(e) unisex mortality table. Returns monthly survival probabilities."""
    url = "https://www.irs.gov/pub/irs-utl/unisex-static-table-2026.xlsx"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to download IRS mortality table (HTTP {response.status_code}).")

    xls = pd.ExcelFile(BytesIO(response.content))
    df = xls.parse(sheet_name=0)
    df = df[["Age", "Survival Probability"]]
    df.dropna(inplace=True)
    df.set_index("Age", inplace=True)

    ages = np.arange(55, 120 + 1 / 12, 1 / 12)
    survival = np.interp(ages, df.index, df["Survival Probability"])
    return pd.Series(survival, index=np.round(ages, 3))


def calculate_exact_age(birth_date, retirement_date):
    delta = retirement_date - birth_date
    return round(delta.days / 365.25, 3)


def calculate_monthly_annuity(salary, years, benefit_rate=0.019):
    return round((benefit_rate * salary * years) / 12, 2)


def build_annuity_stream(start_age, monthly_annuity, segment_rates, mortality_table):
    rows = []
    for month in range(1, 781):  # 65-year projection window
        age = round(start_age + month / 12, 3)
        segment = (
            segment_rates["seg1"] if month <= 60 else
            segment_rates["seg2"] if month <= 240 else
            segment_rates["seg3"]
        )
        monthly_rate = segment / 12
        discount_factor = 1 / ((1 + monthly_rate) ** month)
        survival = mortality_table.get(round(age, 3), 0)
        pv = monthly_annuity * survival * discount_factor
        rows.append([month, age, monthly_annuity, survival, segment, discount_factor, pv])

    return pd.DataFrame(rows, columns=[
        "Month", "Age", "Annuity", "Survival", "Segment Rate", "Discount Factor", "PV of Payment"
    ])


def calculate_lump_sum(df_stream, partial_percent):
    full_lump = df_stream["PV of Payment"].sum()
    pv_factor = full_lump / (df_stream["Annuity"].iloc[0] * 12)
    partial_lump = full_lump * partial_percent
    reduced_annuity = df_stream["Annuity"].iloc[0] * (1 - partial_percent)
    return round(full_lump, 2), round(pv_factor, 4), round(partial_lump, 2), round(reduced_annuity, 2)


def export_to_excel(inputs, df_stream, summary, filename):
    wb = Workbook()
    ws_inputs = wb.active
    ws_inputs.title = "Inputs"
    for key, value in inputs.items():
        ws_inputs.append([key, value])

    ws_stream = wb.create_sheet("Annuity Stream")
    for r in dataframe_to_rows(df_stream, index=False, header=True):
        ws_stream.append(r)

    ws_summary = wb.create_sheet("Summary")
    for key, value in summary.items():
        ws_summary.append([key, value])

    wb.save(filename)
    print(f"Exported to {filename}")


if __name__ == "__main__":
    args = parse_args()

    birth_date      = datetime.strptime(args.birth_date, "%Y-%m-%d")
    retirement_date = datetime.strptime(args.retirement_date, "%Y-%m-%d")

    # Segment rates: CLI overrides take priority; fall back to hardcoded Aug 2025 example values
    segment_rates = {
        "seg1": args.seg1 if args.seg1 is not None else 0.0420,
        "seg2": args.seg2 if args.seg2 is not None else 0.0529,
        "seg3": args.seg3 if args.seg3 is not None else 0.0608,
    }

    print("Loading IRS mortality table...")
    mortality_table = load_irs_unisex_mortality()

    print("Calculating annuity and lump sum...")
    exact_age       = calculate_exact_age(birth_date, retirement_date)
    monthly_annuity = calculate_monthly_annuity(args.salary, args.years)
    df_stream       = build_annuity_stream(exact_age, monthly_annuity, segment_rates, mortality_table)
    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_lump_sum(df_stream, args.partial_lump)

    inputs = {
        "Birth Date":       birth_date.strftime("%Y-%m-%d"),
        "Retirement Date":  retirement_date.strftime("%Y-%m-%d"),
        "Exact Age":        exact_age,
        "Salary":           args.salary,
        "Years of Service": args.years,
        "Monthly Annuity":  monthly_annuity,
        "Partial Lump %":   f"{args.partial_lump:.0%}",
    }
    summary = {
        "Full Lump Sum":    lump_sum,
        "PV Factor":        pv_factor,
        "Partial Lump Sum": partial_lump,
        "Reduced Annuity":  reduced_annuity,
    }

    print(f"\nFull lump sum:    ${lump_sum:,.2f}")
    print(f"PV factor:        {pv_factor}")
    if args.partial_lump > 0:
        print(f"Partial lump:     ${partial_lump:,.2f} ({args.partial_lump:.0%})")
        print(f"Reduced annuity:  ${reduced_annuity:,.2f}/month")
    else:
        print(f"Monthly annuity:  ${monthly_annuity:,.2f}/month")

    export_to_excel(inputs, df_stream, summary, args.output)
