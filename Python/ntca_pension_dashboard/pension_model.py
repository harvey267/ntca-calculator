# ================================
# 📦 SECTION 1: Imports & Constants
# ================================

import pandas as pd
import numpy as np
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import streamlit as st
import os  # Used to verify mortality table file existence

# === Buy-Out Trigger Date ===
# NTCA grants an extra year of service if retirement occurs on or after Feb 1, 2030.
BUY_OUT_EFFECTIVE_DATE = date(2030, 2, 1)

# ============================================
# 📊 SECTION 2: Load IRS §417(e) Mortality Table
# ============================================

@st.cache_data
def load_irs_unisex_mortality(csv_path):
    """
    Loads and processes the IRS-provided unisex mortality table.
    Returns a Series of cumulative survival probabilities indexed by age (55–120).
    """

    # Verify file exists
    if not os.path.exists(csv_path):
        st.error(f"FATAL ERROR: Mortality table '{csv_path}' not found.")
        st.stop()
        return None

    # Attempt to read CSV
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        st.error(f"Error reading mortality table '{csv_path}': {e}")
        st.stop()
        return None

    # Normalize column names
    df.columns = df.columns.str.strip()
    if "417 (e)" in df.columns:
        df.rename(columns={"417 (e)": "qx"}, inplace=True)
    elif "417(e)" in df.columns:
        df.rename(columns={"417(e)": "qx"}, inplace=True)
    else:
        st.error("FATAL ERROR: Expected column '417(e)' not found.")
        st.stop()
        return None

    # Clean and sort data
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["qx"] = pd.to_numeric(df["qx"], errors="coerce")
    df.dropna(subset=["Age", "qx"], inplace=True)
    df.sort_values("Age", inplace=True)

    # Calculate survival probability px = 1 - qx
    df["px"] = 1 - df["qx"]

    # Filter for ages 55+
    df = df[df["Age"] >= 55].copy()
    if df.empty:
        st.error("FATAL ERROR: No mortality data found for Age 55+.")
        st.stop()
        return None

    # Calculate cumulative survival from age 55
    df["cum_survival"] = df["px"].cumprod()
    df["cum_survival"] /= df["cum_survival"].iloc[0]  # Normalize to 1.0 at age 55

    # Interpolate survival curve for ages 55–120
    all_ages = np.arange(55, 121)
    cum_survival_interp = np.interp(all_ages, df["Age"], df["cum_survival"])
    return pd.Series(cum_survival_interp, index=all_ages)

# ====================================
# 📆 SECTION 3: Age & Annuity Calculators
# ====================================

def calculate_exact_age(birth_date, calc_date):
    """
    Calculates fractional age using year and month only.
    NTCA uses month-level precision, not day-level.
    """
    return calc_date.year - birth_date.year + (calc_date.month - birth_date.month) / 12.0

def calculate_monthly_annuity(high_5_salary, service_years, benefit_rate=0.019):
    """
    Calculates monthly annuity using NTCA's formula:
    High-5 × Service Years × Benefit Rate ÷ 12
    """
    return (high_5_salary * service_years * benefit_rate) / 12.0

# ====================================================
# 📉 SECTION 4: Annuity Stream & Lump Sum Calculations
# ====================================================

def build_annual_stream(exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset):
    """
    Builds a stream of annual payments and their present value.
    Applies IRS segment rates and mortality probabilities.
    """

    total_years = 64  # Projection horizon
    annual_annuity = monthly_annuity * 12

    df = pd.DataFrame(index=range(1, total_years + 1))
    df.index.name = "Year"
    df["Age"] = exact_age + df.index

    # Interpolate survival probability for each age
    df["Survival"] = np.interp(df["Age"], mortality_table.index, mortality_table.values)

    # Assign segment rates by year band
    df["Segment Rate (Annual)"] = segment_rates["seg1"]
    df.loc[df.index > 5, "Segment Rate (Annual)"] = segment_rates["seg2"]
    df.loc[df.index > 20, "Segment Rate (Annual)"] = segment_rates["seg3"]

    # Apply discounting with offset
    df["Discount Factor"] = 1 / ((1 + df["Segment Rate (Annual)"]) ** (df.index - discount_offset))

    # Calculate present value of each payment
    df["PV of Payment"] = annual_annuity * df["Survival"] * df["Discount Factor"]

    return df

def calculate_annual_lump_sum(df_stream, monthly_annuity, partial_percent):
    """
    Calculates lump sum and partial options from the annuity stream.
    Returns full lump sum, PV factor, partial lump, and reduced annuity.
    """
    full_lump = df_stream["PV of Payment"].sum()
    annual_annuity = monthly_annuity * 12
    pv_factor = full_lump / annual_annuity
    partial_lump = full_lump * partial_percent
    reduced_annuity = monthly_annuity * (1 - partial_percent)
    return round(full_lump, 2), round(pv_factor, 4), round(partial_lump, 2), round(reduced_annuity, 2)

# ====================================
# 🧮 SECTION 5: Adjusted Inputs Calculator
# ====================================

def get_adjusted_inputs(base_salary, base_years, calc_date, last_emp_date, assumed_growth):
    """
    Adjusts service years and salary based on retirement date.
    Applies monthly accrual and buy-out logic.
    """

    # Monthly accrual: service years increase by 1/12 per month after the user's retirement date.
    # base_anchor_date is the retirement date passed in via calc_date when months_since_anchor = 0.
    base_anchor_date = calc_date
    months_since_anchor = (calc_date.year - base_anchor_date.year) * 12 + (calc_date.month - base_anchor_date.month)
    fractional_accrual = round(months_since_anchor / 12.0, 4) if months_since_anchor >= 0 else 0.0
    adjusted_years = round(base_years + fractional_accrual, 4)

    # Buy-out logic: +1 year if retirement is on or after Feb 1, 2030
    if calc_date >= BUY_OUT_EFFECTIVE_DATE:
        adjusted_years = round(adjusted_years + 1.0, 4)

    # Salary is frozen (no growth applied)
    adjusted_salary = base_salary

    return adjusted_salary, adjusted_years

# ==========================================
# 📆 SECTION 6: Retirement Window Simulation
# ==========================================

def simulate_retirement_window(
    birth_date, start_date, months, salary, base_years,
    rate_tables, mortality_table, partial_percent, assumed_growth,
    offset_mode, discount_offset  # ✅ corrected
):
    """
    Simulates NTCA-style pension calculations over a rolling retirement window.
    Each row represents a retirement date offset by i months from the start_date.

    Applies:
    - Monthly accrual logic from the user's selected retirement date
    - Buy-out trigger on/after Feb 1, 2030 (+1 service year)
    - IRS segment rate discounting
    - §417(e) mortality-based survival probabilities
    - Partial lump sum and reduced annuity options
    - Customizable discount offset logic (dynamic, fixed, or user-defined)
    """

    rows = []  # Store each month's simulation result

    for i in range(months):
        # Calculate retirement date for this iteration
        retire_date = start_date + relativedelta(months=i)
        last_emp_date = retire_date - relativedelta(days=1)

        # Determine applicable IRS segment rates based on plan year
        plan_year = retire_date.year
        if retire_date.month == 1:
            plan_year -= 1  # NTCA uses prior year rates for January retirements
        year = plan_year if plan_year in rate_tables else max(rate_tables.keys())
        segment_rates = rate_tables[year]

        # Adjust salary and service years based on retirement date
        adjusted_salary, adjusted_years = get_adjusted_inputs(
            salary, base_years, retire_date, last_emp_date, assumed_growth
        )

        # Calculate exact age at retirement
        exact_age = calculate_exact_age(birth_date, retire_date)

        # Calculate monthly annuity using NTCA formula
        monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)

        # Determine discount offset based on selected mode
        if offset_mode == "Dynamic (Day-Level)":
            discount_offset = ((retire_date.month - 1) + (retire_date.day - 1) / 30.0) / 12.0
        # For Fixed and Custom, use passed-in discount_offset directly

        # Build annuity stream and calculate present value
        df_stream = build_annual_stream(
            exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset
        )

        # Calculate lump sum and partial options
        lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_annual_lump_sum(
            df_stream, monthly_annuity, partial_percent
        )

        # Append results for this retirement date
        rows.append({
            "Retirement Date": retire_date,
            "Exact Age": exact_age,
            "Service Years": adjusted_years,
            "Adjusted Salary": adjusted_salary,
            "Monthly Annuity": monthly_annuity,
            "Full Lump Sum": lump_sum,
            "Partial Lump": partial_lump,
            "Reduced Annuity": reduced_annuity
            # Optional: add audit flags or SPD citations here
        })

    # Convert all rows into a DataFrame
    df = pd.DataFrame(rows)

    return df

# ==================================================
# 📉 SECTION 7: Segment Rate Sensitivity Simulation
# ==================================================

def simulate_segment_rate_sensitivity(exact_age, monthly_annuity, mortality_table, base_rates, offset_mode):
    """
    Simulates how lump sum values change when IRS segment rates are adjusted up/down.
    Useful for stress testing and understanding rate sensitivity.
    """

    scenarios = []

    # Use NTCA-style fixed offset for sensitivity analysis
    discount_offset = 0.0674083  # Equivalent to ~0.8 months

    # Base case
    stream = build_annual_stream(exact_age, monthly_annuity, base_rates, mortality_table, discount_offset)
    base_lump, _, _, _ = calculate_annual_lump_sum(stream, monthly_annuity, 0.0)
    scenarios.append(["Base Case", "N/A", base_lump])

    # Apply +/- 0.5% and 1.0% shifts to each segment rate
    for i in [-0.01, -0.005, 0.005, 0.01]:
        for seg in ["seg1", "seg2", "seg3"]:
            rates = base_rates.copy()
            rates[seg] += i

            stream = build_annual_stream(exact_age, monthly_annuity, rates, mortality_table, discount_offset)
            lump, _, _, _ = calculate_annual_lump_sum(stream, monthly_annuity, 0.0)

            scenarios.append([f"{seg} {i:+.1%}", f"{rates[seg]:.2%}", lump])

    df = pd.DataFrame(scenarios, columns=["Scenario", "New Rate", "Lumpsum"])
    df["Change from Base"] = df["Lumpsum"] - base_lump

    return df

# ====================================
# 📆 SECTION 8: Feb 1st Projection
# ====================================

def run_feb_1_projection(
    birth_date, salary, base_years, partial_percent,
    rate_tables, assumed_growth, feb_1_date, mortality_table,
    offset_mode, discount_offset  # ✅ Unified offset
):
    """
    Runs a special projection for the next Feb 1st retirement date.
    Applies buy-out logic (+1 year of service) and customizable discount offset.
    """

    last_emp_date = feb_1_date - relativedelta(days=1)

    # Determine applicable IRS segment rates
    plan_year = feb_1_date.year
    if feb_1_date.month == 1:
        plan_year -= 1
    year = plan_year if plan_year in rate_tables else max(rate_tables.keys())
    segment_rates = rate_tables[year]

    # Adjust inputs
    adjusted_salary, adjusted_years = get_adjusted_inputs(
        salary, base_years, feb_1_date, last_emp_date, assumed_growth
    )
    exact_age = calculate_exact_age(birth_date, feb_1_date)
    monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)

    # Apply discount offset logic
    if offset_mode == "Dynamic (Day-Level)":
        discount_offset = ((feb_1_date.month - 1) + (feb_1_date.day - 1) / 30.0) / 12.0
    # For Fixed and Custom, use passed-in discount_offset directly

    # Build annuity stream and calculate lump sum
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

# ============================================
# 🧠 SECTION 9: Main Simulation Wrapper
# ============================================

def run_simulation(
    birth_date, retire_date, salary, base_years, partial_percent,
    rate_tables, assumed_growth, mortality_table_csv,
    offset_mode, discount_offset  # ✅ Only 10 arguments
):
    """
    Main entry point for all pension calculations.
    Returns:
    - Summary values for selected retirement date
    - Feb 1 projection (buy-out trigger)
    - 24-month simulation window
    - Segment rate sensitivity analysis
    """

    # Load mortality table
    mortality_table = load_irs_unisex_mortality(mortality_table_csv)
    if mortality_table is None:
        return None

    # Determine last employment date
    initial_last_emp_date = retire_date - relativedelta(days=1)

    # Determine applicable IRS segment rates
    plan_year = retire_date.year
    if retire_date.month == 1:
        plan_year -= 1
    initial_year = plan_year if plan_year in rate_tables else max(rate_tables.keys())
    segment_rates = rate_tables[initial_year]

    # Adjust inputs for retirement date
    adjusted_salary, adjusted_years = get_adjusted_inputs(
        salary, base_years, retire_date, initial_last_emp_date, assumed_growth
    )
    exact_age = calculate_exact_age(birth_date, retire_date)
    monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)

    # Apply discount offset logic
    if offset_mode == "Dynamic (Day-Level)":
        discount_offset = ((retire_date.month - 1) + (retire_date.day - 1) / 30.0) / 12.0
    # For Fixed and Custom, use passed-in discount_offset directly

    # Build annuity stream and calculate lump sum
    df_stream = build_annual_stream(
        exact_age, monthly_annuity, segment_rates, mortality_table, discount_offset
    )
    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_annual_lump_sum(
        df_stream, monthly_annuity, partial_percent
    )

    # Determine next Feb 1 date for buy-out logic
    feb_1_date = date(initial_last_emp_date.year, 2, 1)
    if initial_last_emp_date >= (feb_1_date - relativedelta(days=1)):
        feb_1_date = date(initial_last_emp_date.year + 1, 2, 1)

    # Run Feb 1 projection
    feb_1_summary = run_feb_1_projection(
        birth_date, salary, base_years, partial_percent,
        rate_tables, assumed_growth, feb_1_date, mortality_table,
        offset_mode, discount_offset  # ✅ Unified offset passed through
    )

    # Run 24-month simulation window
    df_retire_sim = simulate_retirement_window(
        birth_date, retire_date, months=24,
        salary=salary, base_years=base_years,
        rate_tables=rate_tables, mortality_table=mortality_table,
        partial_percent=partial_percent, assumed_growth=assumed_growth,
        offset_mode=offset_mode, discount_offset=discount_offset  # ✅ Unified offset passed through
    )

    # Run segment rate sensitivity analysis
    df_rate_sim = simulate_segment_rate_sensitivity(
        exact_age, monthly_annuity, mortality_table, segment_rates, offset_mode
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