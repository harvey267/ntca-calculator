import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import requests
from io import BytesIO

# === CONFIGURABLE INPUTS ===
birth_date = datetime(1974, 5, 31)
retirement_date = datetime(2029, 5, 31)
estimated_salary = 126_339.20
years_of_service = 26.167
partial_lump_percent = 0.25  # 0.0, 0.25, 0.5, etc.

# === SEGMENT RATES (example: August 2025) ===
segment_rates = {
    "seg1": 0.0420,  # 4.20%
    "seg2": 0.0529,  # 5.29%
    "seg3": 0.0608   # 6.08%
}

# === STEP 1: Load IRS Mortality Table ===
def load_irs_unisex_mortality():
    """
    Downloads and parses the IRS unisex mortality table for §417(e).
    Returns a Series of monthly survival probabilities from age 55 to 120.
    """
    url = "https://www.irs.gov/pub/irs-utl/unisex-static-table-2026.xlsx"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to download IRS mortality table.")

    xls = pd.ExcelFile(BytesIO(response.content))
    df = xls.parse(sheet_name=0)  # Adjust if needed
    df = df[['Age', 'Survival Probability']]  # Adjust column names
    df.dropna(inplace=True)
    df.set_index('Age', inplace=True)

    # Interpolate monthly survival probabilities
    ages = np.arange(55, 120 + 1/12, 1/12)
    survival = np.interp(ages, df.index, df['Survival Probability'])
    return pd.Series(survival, index=np.round(ages, 3))

# === STEP 2: Calculate Exact Age ===
def calculate_exact_age(birth_date, retirement_date):
    delta = retirement_date - birth_date
    return round(delta.days / 365.25, 3)

# === STEP 3: Monthly Annuity Calculation ===
def calculate_monthly_annuity(salary, years, rate=0.019):
    return round((rate * salary * years) / 12, 2)

# === STEP 4: Build Annuity Stream ===
def build_annuity_stream(start_age, monthly_annuity, segment_rates, mortality_table):
    rows = []
    for month in range(1, 781):  # 65 years
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
    df = pd.DataFrame(rows, columns=[
        "Month", "Age", "Annuity", "Survival", "Segment Rate", "Discount Factor", "PV of Payment"
    ])
    return df

# === STEP 5: Lump Sum and Partial Options ===
def calculate_lump_sum(df_stream, partial_percent):
    full_lump = df_stream["PV of Payment"].sum()
    pv_factor = full_lump / (df_stream["Annuity"].iloc[0] * 12)
    partial_lump = full_lump * partial_percent
    reduced_annuity = df_stream["Annuity"].iloc[0] * (1 - partial_percent)
    return round(full_lump, 2), round(pv_factor, 4), round(partial_lump, 2), round(reduced_annuity, 2)

# === STEP 6: Export to Excel ===
def export_to_excel(inputs, df_stream, summary, filename="ntca_lump_sum.xlsx"):
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
    print(f"✅ Exported to {filename}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("📥 Loading IRS mortality table...")
    mortality_table = load_irs_unisex_mortality()

    print("📊 Calculating annuity and lump sum...")
    exact_age = calculate_exact_age(birth_date, retirement_date)
    monthly_annuity = calculate_monthly_annuity(estimated_salary, years_of_service)
    df_stream = build_annuity_stream(exact_age, monthly_annuity, segment_rates, mortality_table)
    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_lump_sum(df_stream, partial_lump_percent)

    inputs = {
        "Birth Date": birth_date.strftime("%Y-%m-%d"),
        "Retirement Date": retirement_date.strftime("%Y-%m-%d"),
        "Exact Age": exact_age,
        "Salary": estimated_salary,
        "Years of Service": years_of_service,
        "Monthly Annuity": monthly_annuity,
        "Partial Lump %": f"{partial_lump_percent:.0%}"
    }

    summary = {
        "Full Lump Sum": lump_sum,
        "PV Factor": pv_factor,
        "Partial Lump Sum": partial_lump,
        "Reduced Annuity": reduced_annuity
    }

    export_to_excel(inputs, df_stream, summary)
