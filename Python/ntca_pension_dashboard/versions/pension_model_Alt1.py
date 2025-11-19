# pension_model.py (full updated code with fixes and correct function order)

#  Pension Lump Sum and Annuity Calculation Model
# This module provides functions to calculate pension lump sums and annuities

import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta
import streamlit as st
import os  # Import os to check if file exists

# === Define the day of the buy-out trigger ===
# From screenshots, the jump happens for a Feb 1 retirement,
# meaning the last employment day is Jan 31.
BUY_OUT_TRIGGER_DAY = 31 
BUY_OUT_TRIGGER_MONTH = 1

# === STEP 1: Load IRS §417(e) Mortality Table ===
@st.cache_data
def load_irs_unisex_mortality(csv_path):  # No default value
    """
    Loads and processes the IRS-provided unisex mortality table from the given csv_path.
    We assume the CSV has columns 'Age' and '417(e)' or '417 (e)'.
    It calculates cumulative survival probability starting from age 55.
    """
    if not os.path.exists(csv_path):
        st.error(f"FATAL ERROR: Mortality table '{csv_path}' not found.")
        st.stop()
        return None  # Stop execution
        
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
        st.error(f"FATAL ERROR: Expected column '417(e)' not found in '{csv_path}'.")
        st.stop()
        return None

    try:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
        df["qx"] = pd.to_numeric(df["qx"], errors="coerce")
    except Exception as e:
        st.error(f"Error processing columns in '{csv_path}': {e}")
        st.stop()
        return None

    df.dropna(subset=["Age", "qx"], inplace=True)
    df.sort_values("Age", inplace=True)
    
    # Calculate survival probability 'px' (1 - probability of dying)
    df["px"] = 1 - df["qx"]

    # Filter for ages 55 and up
    df = df[df["Age"] >= 55].copy()
    
    if df.empty:
        st.error(f"No data found for age 55+ in '{csv_path}'.")
        st.stop()
        return None

    # Calculate cumulative survival from age 55
    df["cum_survival"] = df["px"].cumprod()

    # --- START FIX (Same as v10) ---
    # Shift the series down by one so that the value at Age X
    # represents the probability of surviving *to* Age X.
    df["cum_survival"] = df["cum_survival"].shift(1)
    
    # Set the survival probability AT age 55 (the start) to 1.0
    df.loc[df["Age"] == 55, "cum_survival"] = 1.0
    # --- END FIX ---

    # Interpolate to get a smooth curve for fractional ages
    min_age = 55
    max_age = 120  # Max age in table
    
    # Create a lookup series (Age -> cum_survival)
    # This series is indexed by *integer* age
    survival_series = pd.Series(df["cum_survival"].values, index=df["Age"].values)
    survival_series = survival_series[~survival_series.index.duplicated(keep='first')]

    # Create a full index from 55 to max_age
    full_age_index = np.arange(min_age, max_age + 1)
    
    # Reindex and interpolate
    # This gives us a value for *every* integer age, filling gaps
    interpolated_survival = survival_series.reindex(full_age_index).interpolate()

    # Return the Series indexed by integer age (e.g., 55, 56, 57...)
    return interpolated_survival

# === STEP 2: Exact Age Calculation ===
def calculate_exact_age(birth_date, current_date):
    """Calculates exact age as a float."""
    return (current_date - birth_date).days / 365.2425

# === STEP 3: Monthly Annuity Calculation ===
def calculate_monthly_annuity(final_avg_salary, service_years, benefit_rate=0.019):
    """Calculates the monthly annuity (Normal Retirement Benefit)."""
    annual_benefit = final_avg_salary * service_years * benefit_rate
    return round(annual_benefit / 12, 2)

# === STEP 4: Build *ANNUAL* Annuity & PV Stream (User Hypothesis) ===
def build_annual_stream(exact_age, monthly_annuity, segment_rates, mortality_table):
    """
    Builds a DataFrame of future *annual* payments and their present value,
    based on the user's reverse-engineered model.
    """
    annual_annuity = monthly_annuity * 12
    
    # --- START FIX: Per user's reverse-engineering ---
    # Use a max of 64 years
    total_years = 64
    years = np.arange(1, total_years + 1)
    # --- END FIX ---
    
    # Create a DataFrame for all future years
    df = pd.DataFrame(index=years)
    df.index.name = "Year"
    
    # Calculate age at each *end-of-year* payment
    df["Age"] = exact_age + df.index
    
    # === START FIX: Use np.floor for age lookup ===
    # This aligns with the integer age in mortality table
    df["Age_Int"] = np.floor(df["Age"])
    
    # Lookup cumulative survival using integer age
    df["Survival"] = mortality_table.reindex(df["Age_Int"]).values
    # === END FIX ===
    
    # Assign segment rate based on year
    df["Segment Rate (Annual)"] = segment_rates[0]  # Default to seg1
    df.loc[df.index > 5, "Segment Rate (Annual)"] = segment_rates[1]
    df.loc[df.index > 20, "Segment Rate (Annual)"] = segment_rates[2]
    
    # Calculate discount factor with offset
    df["Discount Factor"] = 1 / ((1 + df["Segment Rate (Annual)"]) ** (df.index + 0.2))
    
    # PV of each payment
    df["PV of Payment"] = annual_annuity * df["Survival"] * df["Discount Factor"]
    
    return df

# === STEP 5: Lump Sum Calculation (from Stream) ===
def calculate_lump_sum(df_stream, monthly_annuity, partial_percent=0.0):
    """Calculates the lump sum from the annuity stream."""
    lump_sum = df_stream["PV of Payment"].sum()
    
    # Handle zero case
    if lump_sum == 0:
        return 0, 0, 0, 0
    
    # PV Factor = Lump Sum / Annual Annuity
    annual_annuity = monthly_annuity * 12
    pv_factor = lump_sum / annual_annuity if annual_annuity > 0 else 0
    
    # Partial Lump and Reduced Annuity
    partial_lump = lump_sum * partial_percent
    reduced_annuity = monthly_annuity * (1 - partial_percent)
    
    return lump_sum, pv_factor, partial_lump, reduced_annuity

# === STEP 6: Adjusted Inputs (Salary, Years) ===
def get_adjusted_inputs(salary, base_years, retire_date, last_emp_date, assumed_growth):
    """
    Adjusts salary with growth and service years with buy-out.
    """
    # Salary Growth (prorated monthly)
    months_delay = (retire_date.year - 2029) * 12 + (retire_date.month - 6)  # Assuming from June 2029
    salary_adjusted = salary * (1 + assumed_growth) ** (months_delay / 12.0)
    
    # Service Years Buy-Out
    adjusted_years = base_years
    current_trigger = date(last_emp_date.year, BUY_OUT_TRIGGER_MONTH, BUY_OUT_TRIGGER_DAY)
    
    # If past this year's trigger, next trigger is next year
    if last_emp_date >= current_trigger:
        adjusted_years += 1.0
        current_trigger = date(last_emp_date.year + 1, BUY_OUT_TRIGGER_MONTH, BUY_OUT_TRIGGER_DAY)
    
    return salary_adjusted, adjusted_years

# === STEP 7: Get Rates for Year ===
def get_rates_for_year(rate_tables, retire_date):
    """
    Gets segment rates for the retirement year, with fallback to max year.
    """
    plan_year = retire_date.year
    if retire_date.month == 1:
        plan_year -= 1
    if plan_year not in rate_tables:
        plan_year = max(rate_tables.keys())
    return rate_tables[plan_year]["seg1"], rate_tables[plan_year]["seg2"], rate_tables[plan_year]["seg3"]

# === STEP 8: Segment Rate Sensitivity ===
def simulate_segment_rate_sensitivity(exact_age, monthly_annuity, mortality_table, segment_rates):
    """
    Simulates lump sum under uniform rate shifts.
    """
    rows = []
    deltas = np.arange(-2.0, 2.1, 0.5)
    
    for delta in deltas:
        new_rates = [r + delta / 100 for r in segment_rates]
        
        df_stream = build_annual_stream(exact_age, monthly_annuity, new_rates, mortality_table)
        
        lump_sum, _, _, _ = calculate_lump_sum(df_stream, monthly_annuity, 0.0)
        
        rows.append({
            "Rate Change (%)": delta,
            "Lump Sum": lump_sum
        })
    
    return pd.DataFrame(rows)

# === STEP 9: Feb 1 Projection ===
def run_feb_1_projection(birth_date, salary, base_years, partial_percent, rate_tables, assumed_growth, feb_1_date, mortality_table):
    """
    Projects for Feb 1, assuming post-buy-out, no growth for simplified, one-time calculation.
    """
    
    # --- Service Year Calculation ---
    # By definition, this date is *after* the buy-out
    adjusted_years = base_years + 1.0
    
    # --- Salary Calculation ---
    # We will *not* apply growth for this simple comparison
    salary_adjusted = salary
    
    # --- Annuity Calculation ---
    monthly_annuity = calculate_monthly_annuity(salary_adjusted, adjusted_years)
    
    # --- Lump Sum Calculation ---
    exact_age = calculate_exact_age(birth_date, feb_1_date)
    
    # Get the correct rates for this simulated year
    segment_rates = get_rates_for_year(rate_tables, feb_1_date)
    
    # *** USE ANNUAL STREAM ***
    df_stream = build_annual_stream(exact_age, monthly_annuity, segment_rates, mortality_table)
    
    # --- FIX: Correct typo calculate_lom -> calculate_lump_sum ---
    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_lump_sum(df_stream, monthly_annuity, partial_percent)
    
    return {
        "Date": feb_1_date,
        "Full Lump Sum": lump_sum,
        "Monthly Annuity": monthly_annuity,
        "PV Factor": pv_factor,
        "Partial Lump Sum": partial_lump,
        "Reduced Annuity": reduced_annuity
    }

# === STEP 10: Main Simulation Wrapper ===
def run_simulation(birth_date, retire_date, salary, base_years, partial_percent, rate_tables, assumed_growth, mortality_table_csv):
    """
    Main function to run all calculations and simulations.
    """
    
    # === Load Data ===
    mortality_table = load_irs_unisex_mortality(mortality_table_csv)
    if mortality_table is None:
        # Error was already shown by load_irs_unisex_mortality
        return None # Or raise exception

    # === Initial State Calculation (for "Current Date" summary) ===
    
    # 1. Find service years for the *initial* date
    initial_last_emp_date = retire_date - relativedelta(days=1)
    
    # === FIX: Correctly find the *next* trigger date ===
    # Find the trigger date for the *current* year
    buy_out_trigger = date(initial_last_emp_date.year, BUY_OUT_TRIGGER_MONTH, BUY_OUT_TRIGGER_DAY)
    
    # If we are already past this year's trigger date, the next trigger is *next year*
    if initial_last_emp_date >= buy_out_trigger:
        buy_out_trigger = date(initial_last_emp_date.year + 1, BUY_OUT_TRIGGER_MONTH, BUY_OUT_TRIGGER_DAY)

    # `buy_out_trigger` is now the next Jan 31st (e.g., 2030-01-31)

    # Check if our initial date is *after* this trigger
    buy_out = 1.0 if initial_last_emp_date >= buy_out_trigger else 0.0
    adjusted_years = base_years + buy_out
    
    # 2. Salary (no growth for initial date)
    salary_adjusted = salary
    
    # 3. Annuity
    monthly_annuity = calculate_monthly_annuity(salary_adjusted, adjusted_years)
    
    # 4. Lump Sum (using *ANNUAL* model)
    exact_age = calculate_exact_age(birth_date, retire_date)
    segment_rates = get_rates_for_year(rate_tables, retire_date)
    # *** USE ANNUAL STREAM ***
    df_stream = build_annual_stream(exact_age, monthly_annuity, segment_rates, mortality_table)
    lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_lump_sum(df_stream, monthly_annuity, partial_percent)
    
    # === Feb 1st Projection ===
    
    # Find the next Feb 1st *after* the initial last emp date
    feb_1_date = date(initial_last_emp_date.year, 2, 1)
    if initial_last_emp_date >= (feb_1_date - relativedelta(days=1)): # Check if last emp date is on or after Jan 31
        feb_1_date = date(initial_last_emp_date.year + 1, 2, 1)

    feb_1_summary = run_feb_1_projection(
        birth_date, 
        salary, 
        base_years, 
        partial_percent, 
        rate_tables, 
        assumed_growth,
        feb_1_date,
        mortality_table # Pass the loaded table
    )

    # === Window & Sensitivity Simulations ===
    
    # Simulate the 24-month retirement window
    df_retire_sim = simulate_retirement_window(
        birth_date, retire_date, months=24,
        salary=salary, base_years=base_years,
        rate_tables=rate_tables, mortality_table=mortality_table,
        partial_percent=partial_percent, assumed_growth=assumed_growth
    )
    
    # Simulate the rate sensitivity
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

def simulate_retirement_window(
    birth_date, retire_date, months=24,
    salary=126339.20, base_years=25.8333,
    rate_tables=None, mortality_table=None,
    partial_percent=0.0, assumed_growth=0.0
):
    """
    Simulates retirement dates over a window of months.
    """
    rows = []

    for i in range(months):
        current_retire_date = retire_date + relativedelta(months=i)
        last_emp_date = current_retire_date - relativedelta(days=1)

        # Get adjusted inputs (salary, years)
        adjusted_salary, adjusted_years = get_adjusted_inputs(
            salary, base_years, current_retire_date, last_emp_date, assumed_growth
        )

        # Calculate exact age
        exact_age = calculate_exact_age(birth_date, current_retire_date)

        # Get segment rates for the year
        segment_rates = get_rates_for_year(rate_tables, current_retire_date)

        # Calculate monthly annuity and yearly
        monthly_annuity = calculate_monthly_annuity(adjusted_salary, adjusted_years)
        yearly_annuity = monthly_annuity * 12

        # Build stream and calculate lump sum
        df_stream = build_annual_stream(
            exact_age, monthly_annuity, segment_rates, mortality_table
        )
        lump_sum, pv_factor, partial_lump, reduced_annuity = calculate_lump_sum(
            df_stream, monthly_annuity, partial_percent
        )

        # Append row
        rows.append({
            "Last Employment Date": last_emp_date,
            "Retirement Date": current_retire_date,
            "Exact Age": exact_age,
            "Full Lump Sum": lump_sum,
            "Monthly Annuity": monthly_annuity,
            "Yearly Annuity": yearly_annuity,
            "PV Factor": pv_factor,
            "Partial Lump": partial_lump,
            "Reduced Annuity": reduced_annuity,
            "Service Years": adjusted_years,
            "Adjusted Salary": adjusted_salary
        })

    df = pd.DataFrame(rows)

    # Add delta columns
    df['Δ from Prior Month Lump'] = df['Full Lump Sum'].diff()
    df['Δ from Prior Month Monthly'] = df['Monthly Annuity'].diff()
    df['Δ from Prior Month Annual'] = df['Yearly Annuity'].diff()
    df['% Different'] = df['Monthly Annuity'].pct_change() * 100

    # Set first row deltas to np.nan
    df.loc[0, ['Δ from Prior Month Lump', 'Δ from Prior Month Monthly', 'Δ from Prior Month Annual', '% Different']] = np.nan

    return df