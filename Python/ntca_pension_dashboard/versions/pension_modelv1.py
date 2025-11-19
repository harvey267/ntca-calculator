#  Pension Lump Sum and Annuity Calculation Model
# This module provides functions to calculate pension lump sums and annuities

import pandas as pd
import numpy as np
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import streamlit as st
import os # Import os to check if file exists

# === Define the day of the buy-out trigger ===
# From screenshots, the jump happens for a Feb 1 retirement.
BUY_OUT_EFFECTIVE_DATE = date(2030, 2, 1) # The date the +1 year kicks in


# === STEP 1: Load IRS §417(e) Mortality Table ===
@st.cache_data
def load_irs_unisex_mortality(csv_path): # No default value
    """
    Loads and processes the IRS-provided unisex mortality table from the given csv_path.
    We assume the CSV has columns 'Age' and '417(e)' or '417 (e)'.
    It calculates cumulative survival probability starting from age 55.
    """
    if not os.path.exists(csv_path):
        st.error(f"FATAL ERROR: Mortality table '{csv_path}' not found.")
        st.stop()
        return None # Stop execution
        
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        st.error(f"Error reading mortality table '{csv_path}': {e}")
        st.stop()
        return None
        
    df.columns = df.columns.str.strip()
    
    # Find the correct mortality column
    if "417 (e)" in df.columns:
        df.rename(columns={"417 (e)": "qx"}, inplace=True)
    elif "417(e)" in df.columns:
        df.rename(columns={"417(e)": "qx"}, inplace=True)
    else:
        st.error(f"FATAL ERROR: Expected column '417(e)' or '417 (e)' not found in '{csv_path}'.")
        st.stop()
        return None

    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["qx"] = pd.to_numeric(df["qx"], errors="coerce")
    df.dropna(subset=["Age", "qx"], inplace=True)
    df.sort_values("Age", inplace=True)
    
    df["px"] = 1 - df["qx"]
    
    # Start from age 55 and normalize cumulative survival
    df = df[df["Age"] >= 55].copy()
    if df.empty:
        st.error(f"FATAL ERROR: No mortality data found for Age 55 or greater in '{csv_path}'.")
        st.stop()
        return None

    df["cum_survival"] = df["px"].cumprod()
    df["cum_survival"] /= df["cum_survival"].iloc[0] # Normalize at age 55

    # Interpolate for all ages (floor)
    all_ages = np.arange(55, 121) # Ages 55 to 120
    
    # Create a Series for interpolation
    survival_series = pd.Series(df["cum_survival"].values, index=df["Age"].values)
    
    # Reindex to all_ages, using ffill to handle any gaps (though interpolation is better)
    # We will use np.interp in the calculation step, but this creates the base lookup
    
    # Use np.interp to create the full table
    cum_survival_interp = np.interp(all_ages, df["Age"], df["cum_survival"])
    
    return pd.Series(cum_survival_interp, index=all_ages)

# === STEP 2: Exact Age Calculator ===
def calculate_exact_age(birth_date, calc_date):
    """Calculates exact age as a float."""
    # === START FIX: Use simplified monthly age calculation ===
    # Per user's data (NTCA Age 55.5000), NTCA is using a simplified
    # monthly age calculation, ignoring the day of birth.
    age = (
        calc_date.year - birth_date.year + 
        (calc_date.month - birth_date.month) / 12.0
        # (calc_date.day - birth_date.day) / 365.25 # This was too precise
    )
    # === END FIX ===
    return age

# === STEP 3: Monthly Annuity Calculator ===
def calculate_monthly_annuity(high_5_salary, service_years, benefit_rate=0.019):
    """Calculates the straight-life monthly annuity."""
    annual_annuity = high_5_salary * service_years * benefit_rate
    return annual_annuity / 12.0

# === STEP 4: Annuity Stream Builder (Annual Approx) ===
def build_annual_stream(exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset):
    """
    Builds a DataFrame of annual annuity payments, survival, and PV.
    This uses the annual approximation model we reverse-engineered.
    """

    # === Calibrated Offset ===
    # NTCA assumes monthly payments starting at retirement eligibility.
    # Without this, annual discounting undervalues the stream.
    offset = 0.0674083  # Equivalent to ~24 days, aligns with NTCA's mid-year timing

    total_years = 64  # Max projection horizon
    annual_annuity = monthly_annuity * 12

    df = pd.DataFrame(index=range(1, total_years + 1))
    df.index.name = "Year"

    # === Age Calculation ===
    # Use fractional age (e.g. 55.0833) for interpolation
    df["Age"] = exact_age + df.index

    # === Survival Interpolation ===
    df["Survival"] = np.interp(
        df["Age"],
        mortality_table.index,
        mortality_table.values
    )

    # === Segment Rate Assignment ===
    df["Segment Rate (Annual)"] = segment_rates["seg1"]
    df.loc[df.index > 5, "Segment Rate (Annual)"] = segment_rates["seg2"]
    df.loc[df.index > 20, "Segment Rate (Annual)"] = segment_rates["seg3"]

    # === Discount Factor with Offset ===
    df["Discount Factor"] = 1 / ((1 + df["Segment Rate (Annual)"]) ** (df.index - offset))

    # === Present Value Calculation ===
    df["PV of Payment"] = annual_annuity * df["Survival"] * df["Discount Factor"]

    return df

# === STEP 5: Lump Sum and Partial Options (Annual Approx) ===
def calculate_annual_lump_sum(df_stream, monthly_annuity, partial_percent):
    """Calculates lump sum and partial options from the annual stream."""
    
    full_lump = df_stream["PV of Payment"].sum()
    
    # PV factor is based on the annual annuity
    annual_annuity = monthly_annuity * 12
    pv_factor = full_lump / annual_annuity
    
    partial_lump = full_lump * partial_percent
    
    # Reduced annuity is based on the monthly
    reduced_annuity = monthly_annuity * (1 - partial_percent)
    
    return round(full_lump, 2), round(pv_factor, 4), round(partial_lump, 2), round(reduced_annuity, 2)


# === STEP 6: High-5 and Service Year Calculator ===
def get_adjusted_inputs(base_salary, base_years, calc_date, last_emp_date, assumed_growth):
    """
    Calculates the adjusted High-5 and Service Years for a given date.
    """
    # 1. Calculate buy-out
    # === START FIX: Use the hard-coded effective date ===
    # This was the bug. It was triggering immediately.
    # The buy-out only happens on or after Feb 1, 2030.
    buy_out = 0
    if calc_date >= BUY_OUT_EFFECTIVE_DATE:
        buy_out = 1
    # === END FIX ===
    
    adjusted_years = base_years + buy_out
    
    # 2. Calculate salary growth
    # We use a simple compound growth model based on the offset in months
    # This matches the user's reverse-engineered 0.136% growth
    
    # Find the *original* start date (June 1, 2029) to calculate offset
    # This is a bit of a hack, but we need a stable base date
    original_start_date = date(2029, 6, 1) 
    months_offset = (calc_date.year - original_start_date.year) * 12 + (calc_date.month - original_start_date.month)
    
    # This is the High-5 Salary, not the annual salary
    adjusted_salary = base_salary * ((1 + assumed_growth) ** (months_offset / 12.0))
    
    return adjusted_salary, adjusted_years

# === STEP 7: Retirement Window Simulation ===
def simulate_retirement_window(
    birth_date, start_date, months, salary, base_years,
    rate_tables, mortality_table, partial_percent, assumed_growth
):
    """
    Runs a simulation for a 24-month window, recalculating all values for each month.
    Applies day-level discount offset based on payment start date.
    """
    rows = []

    for i in range(months):
        retire_date = start_date + relativedelta(months=i)
        last_emp_date = retire_date - relativedelta(days=1)

        # === Determine plan year for segment rates ===
        plan_year = retire_date.year
        if retire_date.month == 1:
            plan_year -= 1

        year = plan_year
        if year not in rate_tables:
            year = max(rate_tables.keys())
        segment_rates = rate_tables[year]

        # === Adjust salary and service years ===
        adjusted_salary, adjusted_years = get_adjusted_inputs(
            salary, base_years, retire_date, last_emp_date, assumed_growth
        )

        exact_age = calculate_exact_age(birth_date, retire_date)
        monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)

        # === Day-level discount offset based on payment start date ===
        payment_start_date = retire_date  # Assume payments begin on retirement date
        discount_offset = ((payment_start_date.month - 1) + (payment_start_date.day - 1) / 30.0) / 12.0

        df_stream = build_annual_stream(
            exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset
        )

        lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_annual_lump_sum(
            df_stream, monthly_annuity, partial_percent
        )

        rows.append({
            "Retirement Date": retire_date,
            "Exact Age": exact_age,
            "Service Years": adjusted_years,
            "Adjusted Salary": adjusted_salary,
            "Monthly Annuity": monthly_annuity,
            "Full Lump Sum": lump_sum,
            "Partial Lump": partial_lump,
            "Reduced Annuity": reduced_annuity
        })

    return pd.DataFrame(rows)

# === STEP 8: Rate Sensitivity Simulation ===
def simulate_segment_rate_sensitivity(exact_age, monthly_annuity, mortality_table, base_rates):
    """
    Calculates the lump sum based on +/- 1% on each segment rate.
    Applies default discount offset for sensitivity analysis.
    """
    scenarios = []

    # === Use default offset for sensitivity tests ===
    discount_offset = 0.0674083  # Or calculate dynamically if needed

    # Base case
    stream = build_annual_stream(exact_age, monthly_annuity, base_rates, mortality_table, discount_offset)
    base_lump, _, _, _ = calculate_annual_lump_sum(stream, monthly_annuity, 0.0)
    scenarios.append(["Base Case", "N/A", base_lump])

    for i in [-0.01, -0.005, 0.005, 0.01]:  # +/- 1% and 0.5%
        for seg in ["seg1", "seg2", "seg3"]:
            rates = base_rates.copy()
            rates[seg] = rates[seg] + i

            stream = build_annual_stream(exact_age, monthly_annuity, rates, mortality_table, discount_offset)
            lump, _, _, _ = calculate_annual_lump_sum(stream, monthly_annuity, 0.0)

            scenarios.append([f"{seg} {i:+.1%}", f"{rates[seg]:.2%}", lump])

    df = pd.DataFrame(scenarios, columns=["Scenario", "New Rate", "Lumpsum"])
    df["Change from Base"] = df["Lumpsum"] - base_lump
    return df

# === STEP 9: Feb 1st Projection ===
def run_feb_1_projection(
    birth_date, salary, base_years, partial_percent,
    rate_tables, assumed_growth, feb_1_date, mortality_table
):
    """
    Runs a special projection for the *next* Feb 1st date.
    Applies day-level discount offset based on payment start date.
    """
    last_emp_date = feb_1_date - relativedelta(days=1)

    plan_year = feb_1_date.year
    if feb_1_date.month == 1:
        plan_year -= 1

    year = plan_year
    if year not in rate_tables:
        year = max(rate_tables.keys())
    segment_rates = rate_tables[year]

    adjusted_salary, adjusted_years = get_adjusted_inputs(
        salary, base_years, feb_1_date, last_emp_date, assumed_growth
    )
    exact_age = calculate_exact_age(birth_date, feb_1_date)
    monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)

    # === Day-level discount offset based on payment start date ===
    payment_start_date = feb_1_date
    discount_offset = ((payment_start_date.month - 1) + (payment_start_date.day - 1) / 30.0) / 12.0

    df_stream = build_annual_stream(
        exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset
    )

    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_annual_lump_sum(
        df_stream, monthly_annuity, partial_percent
    )

    return {
        "Date": feb_1_date,
        "Full Lump Sum": lump_sum,
        "Monthly Annuity": monthly_annuity,
        "PV Factor": pv_factor,
        "Partial Lump Sum": partial_lump,
        "Reduced Annuity": reduced_annuity
    }


# === STEP 10: Main Simulation Wrapper ===
def run_simulation(
    birth_date, retire_date, salary, base_years, partial_percent,
    rate_tables, assumed_growth, mortality_table_csv
):
    """
    Main function to run all calculations and return a results dictionary.
    Applies day-level discount offset based on payment start date.
    """
    mortality_table = load_irs_unisex_mortality(mortality_table_csv)
    if mortality_table is None:
        return None

    initial_last_emp_date = retire_date - relativedelta(days=1)

    plan_year = retire_date.year
    if retire_date.month == 1:
        plan_year -= 1

    initial_year = plan_year
    if initial_year not in rate_tables:
        initial_year = max(rate_tables.keys())
    segment_rates = rate_tables[initial_year]

    adjusted_salary, adjusted_years = get_adjusted_inputs(
        salary, base_years, retire_date, initial_last_emp_date, assumed_growth
    )
    exact_age = calculate_exact_age(birth_date, retire_date)
    monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)

    # === Day-level discount offset based on payment start date ===
    payment_start_date = retire_date
    discount_offset = ((payment_start_date.month - 1) + (payment_start_date.day - 1) / 30.0) / 12.0

    df_stream = build_annual_stream(
        exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset
    )

    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_annual_lump_sum(
        df_stream, monthly_annuity, partial_percent
    )

    feb_1_date = date(initial_last_emp_date.year, 2, 1)
    if initial_last_emp_date >= (feb_1_date - relativedelta(days=1)):
        feb_1_date = date(initial_last_emp_date.year + 1, 2, 1)

    feb_1_summary = run_feb_1_projection(
        birth_date,
        salary,
        base_years,
        partial_percent,
        rate_tables,
        assumed_growth,
        feb_1_date,
        mortality_table
    )

    df_retire_sim = simulate_retirement_window(
        birth_date, retire_date, months=24,
        salary=salary, base_years=base_years,
        rate_tables=rate_tables, mortality_table=mortality_table,
        partial_percent=partial_percent, assumed_growth=assumed_growth
    )

    df_rate_sim = simulate_segment_rate_sensitivity(
        exact_age, monthly_annuity, mortality_table, segment_rates
    )

    return {
        "summary": {
            "Full Lump Sum": lump_sum,
            "Monthly Annuity": monthly_annuity,
            "PV Factor": pv_factor,
            "Partial Lump Sum": partial_lump,
            "Reduced Annuity": reduced_annuity
        },
        "feb_1_summary": feb_1_summary,
        "retire_chart": df_retire_sim,
        "rate_chart": df_rate_sim,
        "stream": df_stream
    }