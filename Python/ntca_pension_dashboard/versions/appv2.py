# Streamlit Dahboard

import streamlit as st
import pandas as pd
from datetime import date
from pension_model import run_simulation
import os
from ssa_model import ss_benefits

st.set_page_config(page_title="NTCA Pension Dashboard", layout="wide")
st.title("📊 Tom's Retirement Simulator")

# === Sidebar Inputs ===

# 🏛 NTCA Pension Inputs
with st.sidebar.expander("🏛 NTCA Pension Inputs", expanded=True):
    birth_date = st.date_input("Date of Birth", date(1974, 6, 10))
    retire_date = st.date_input("Retirement Date", date(2029, 6, 1))
    salary = st.number_input("Final Average Salary ($)", min_value=10000.00, max_value=500000.00, value=126339.20, step=0.01, format="%.2f")
    years = st.number_input("Years of Service", min_value=1.0000, max_value=50.0000, value=26.1288, step=0.0001, format="%.4f")
    assumed_growth = st.number_input("Annual Salary Growth (%)", min_value=0.000, max_value=10.000, value=0.136, step=0.001, format="%.3f")
    partial = st.slider("Partial Lump Sum (% of Full)", min_value=0, max_value=100, value=0, step=5) / 100.0

# 📈 IRS Segment Rates
with st.sidebar.expander("📈 IRS Segment Rates"):
    st.markdown("Enter rates as percentages (e.g., 4.50)")
    rate_tables = {}

    with st.expander("2029 Rates (Notice 2028-xx)", expanded=True):
        seg1_2029 = st.number_input("2029 Seg 1", value=4.50, step=0.01, format="%.2f") / 100.0
        seg2_2029 = st.number_input("2029 Seg 2", value=4.96, step=0.01, format="%.2f") / 100.0
        seg3_2029 = st.number_input("2029 Seg 3", value=5.40, step=0.01, format="%.2f") / 100.0
        rate_tables[2029] = {"seg1": seg1_2029, "seg2": seg2_2029, "seg3": seg3_2029}

    with st.expander("2030 Rates (Notice 2029-xx)"):
        seg1_2030 = st.number_input("2030 Seg 1", value=4.50, step=0.01, format="%.2f") / 100.0
        seg2_2030 = st.number_input("2030 Seg 2", value=4.96, step=0.01, format="%.2f") / 100.0
        seg3_2030 = st.number_input("2030 Seg 3", value=5.40, step=0.01, format="%.2f") / 100.0
        rate_tables[2030] = {"seg1": seg1_2030, "seg2": seg2_2030, "seg3": seg3_2030}

    with st.expander("2031 Rates (Notice 2030-xx)"):
        seg1_2031 = st.number_input("2031 Seg 1", value=4.50, step=0.01, format="%.2f") / 100.0
        seg2_2031 = st.number_input("2031 Seg 2", value=4.96, step=0.01, format="%.2f") / 100.0
        seg3_2031 = st.number_input("2031 Seg 3", value=5.40, step=0.01, format="%.2f") / 100.0
        rate_tables[2031] = {"seg1": seg1_2031, "seg2": seg2_2031, "seg3": seg3_2031}

    rate_tables[2032] = rate_tables[2031]

# ⚰️ Mortality Table
with st.sidebar.expander("⚰️ Mortality Table"):
    try:
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    except Exception:
        csv_files = ["n-23-73.csv", "n-24-42.csv", "n-25-40.csv"]

    default_mortality_csv = "n-24-42.csv"
    if default_mortality_csv not in csv_files:
        default_mortality_csv = csv_files[0] if csv_files else "n-24-42.csv"

    try:
        default_index = csv_files.index(default_mortality_csv)
    except ValueError:
        csv_files.append(default_mortality_csv)
        default_index = csv_files.index(default_mortality_csv)

    mortality_table_csv = st.selectbox("Mortality Table CSV", options=csv_files, index=default_index)

# 🧓 Social Security Earnings
with st.sidebar.expander("🧓 Social Security Earnings"):
    st.markdown("Upload a CSV with columns: `year`, `income`")
    st.markdown("""
    ### 📄 SSA Earnings CSV Format

    Your uploaded CSV should contain two columns:

    | year | income   |
    |------|----------|
    | 1995 | 32000.00 |
    | 1996 | 34000.00 |
    | ...  | ...      |
    | 2024 | 168600.00 |

    **Requirements:**
    - Column headers must be exactly `year` and `income` (case-sensitive).
    - `year` must be a 4-digit number (e.g. 1995).
    - `income` should be a numeric value (e.g. 42000.00).
    - No blank rows or missing values.

    **Optional Tip:** You can create this in Excel or Google Sheets and export as `.csv`.
    """)
    uploaded_file = st.file_uploader("Choose SSA earnings CSV", type=["csv"])
    income_by_year = {}

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "year" in df.columns and "income" in df.columns:
            df = df.dropna(subset=["year", "income"])
            for _, row in df.iterrows():
                try:
                    year = int(row["year"])
                    income = float(row["income"])
                    income_by_year[year] = income
                except:
                    continue
        else:
            st.warning("CSV must contain 'year' and 'income' columns.")

    # Fill in all years from age 18 to 70
    start_year = birth_date.year + 18
    end_year = birth_date.year + 70
    current_year = date.today().year

    from datetime import date

    start_year = birth_date.year + 18
    end_year = birth_date.year + 70
    current_year = date.today().year

    editable_rows = []
    previous_income = None

    for year in range(start_year, end_year + 1):
        age = year - birth_date.year

        # Use uploaded or manually entered income if available
        if year in income_by_year:
            income = income_by_year[year]
        else:
            # If current year, use previous year's income
            if year == current_year and previous_income is not None:
                income = previous_income
            else:
                income = 116755 if year > current_year else 0

        editable_rows.append({"Age": age, "Year": year, "Income": income})
        previous_income = income  # Track for next iteration

    editable_df = pd.DataFrame(editable_rows)
    st.markdown("### ✏️ Editable SSA Earnings Table")
    edited_df = st.data_editor(editable_df, num_rows="fixed", use_container_width=True)

    # Build final income_by_year dictionary
    income_by_year = {int(row["Year"]): float(row["Income"]) for _, row in edited_df.iterrows()}




# 💼 Future 401(k) & Investments
with st.sidebar.expander("💼 Future 401(k) & Investments"):
    st.markdown("Coming soon: add projected balances, growth rates, and withdrawal plans.")
    st.markdown("Enter projected annual withdrawals by year:")
    future_401k = {}
    for year in range(retire_date.year, birth_date.year + 91):
        amt = st.number_input(f"401(k) Withdrawal for {year}", min_value=0, value=0, key=f"k401_{year}")
        future_401k[year] = amt

# 🛠️ Debug + Disclaimer
st.sidebar.markdown("---")
show_debug = st.sidebar.checkbox("Show Debug Panel", value=True)
st.sidebar.markdown("""
*Disclaimer: This is an educational tool. All calculations are estimates based on the best available public data and reverse-engineering. Always consult NTCA for official numbers.*
""")

try:
    results = run_simulation(
        birth_date,
        retire_date,
        salary,
        years,
        partial,
        rate_tables,
        assumed_growth / 100.0,
        mortality_table_csv
    )
    ss_results = ss_benefits(birth_date.year, income_by_year)
except Exception as e:
    st.error(f"An error occurred during calculation: {e}")
    st.exception(e)
    st.stop()

# === Main Panel ===

# === Unified Retirement Income Forecast ===
def build_income_timeline(birth_year, retire_year, pension_monthly, ss_results, future_401k=None):
    start_year = retire_year
    end_year = birth_year + 90
    rows = []
    for year in range(start_year, end_year + 1):
        age = year - birth_year
        pension = pension_monthly * 12 if year >= retire_year else 0
        ss = 0
        if age >= 62:
            if age >= 70:
                ss = ss_results.get(70, 0) * 12
            elif age >= 67:
                ss = ss_results.get(67, 0) * 12
            else:
                ss = ss_results.get(62, 0) * 12
        k401 = future_401k.get(year, 0) if future_401k else 0
        rows.append({
            "Year": year,
            "Age": age,
            "Pension": pension,
            "Social Security": ss,
            "401(k)": k401,
            "Total Income": pension + ss + k401
        })
    return pd.DataFrame(rows)

try:
    # === FIX: Pass the corrected 'years' variable ===
    results = run_simulation(
        birth_date, 
        retire_date, 
        salary, 
        years, # Use the corrected variable name
        partial, 
        rate_tables, 
        assumed_growth / 100.0, # Convert growth % to decimal
        mortality_table_csv
    )
    ss_results = ss_benefits(birth_date.year, income_by_year)
except Exception as e:
    st.error(f"An error occurred during calculation: {e}")
    st.exception(e) # Show full traceback
    st.stop()

# === Unified Retirement Income Chart ===
income_df = build_income_timeline(
    birth_year=birth_date.year,
    retire_year=retire_date.year,
    pension_monthly=results["summary"]["Monthly Annuity"],
    ss_results=ss_results,
    future_401k=future_401k  # make sure this exists from sidebar
)

st.header("📊 Unified Retirement Income Forecast")
st.line_chart(income_df, x="Year", y=["Pension", "Social Security", "401(k)", "Total Income"], use_container_width=True)

with st.expander("View Income Table"):
    st.dataframe(income_df.style.format({
        "Pension": "${:,.2f}",
        "Social Security": "${:,.2f}",
        "401(k)": "${:,.2f}",
        "Total Income": "${:,.2f}"
    }))

if results:
    # === Summary Panel ===
    st.header("Summary Panel")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Date Projection")
        st.metric("Retirement Date", retire_date.strftime("%Y-%m-%d"))
        st.metric("Full Lump Sum", f"${results['summary']['Full Lump Sum']:,.2f}")
        st.metric("Monthly Annuity", f"${results['summary']['Monthly Annuity']:,.2f}")
        st.metric("Present Value Factor", f"{results['summary']['PV Factor']:.4f}")
        if partial > 0:
            st.metric("Partial Lump Sum", f"${results['summary']['Partial Lump Sum']:,.2f}")
            st.metric("Reduced Monthly Annuity", f"${results['summary']['Reduced Annuity']:,.2f}")

    with col2:
        st.subheader("Next Feb 1st Projection")
        st.metric("Retirement Date", results['feb_1_summary']['Date'].strftime("%Y-%m-%d"))
        st.metric("Full Lump Sum", f"${results['feb_1_summary']['Full Lump Sum']:,.2f}")
        st.metric("Monthly Annuity", f"${results['feb_1_summary']['Monthly Annuity']:,.2f}")
        st.metric("Present Value Factor", f"{results['feb_1_summary']['PV Factor']:.4f}")
        if partial > 0:
            st.metric("Partial Lump Sum", f"${results['feb_1_summary']['Partial Lump Sum']:,.2f}")
            st.metric("Reduced Monthly Annuity", f"${results['feb_1_summary']['Reduced Annuity']:,.2f}")
    with st.expander("ℹ️ How Timing Affects Lump Sum Calculations"):
        st.markdown("""
        **Discount Offset Logic**

        NTCA allows retirees to select the exact date they begin receiving payments.  
        This model reflects that by adjusting the timing of each payment in the present value stream.

        **How It Works:**
        - The discount offset is calculated based on your selected retirement date.
        - It shifts the discount curve to reflect when payments begin.
        - Earlier payment dates result in slightly higher lump sums.

        **Formula Used:**
        ```
        offset = ((month - 1) + (day - 1) / 30) / 12
        ```

        This ensures actuarial-grade precision and alignment with NTCA’s calculator.
        """)

    # === Retirement Window Chart ===
    st.header("NTCA Retirement Window Simulation (24 Months)")
    
    # Format the DataFrame for display
    chart_data = results["retire_chart"].copy()
    chart_data["Full Lump Sum"] = chart_data["Full Lump Sum"].round(2)
    chart_data["Monthly Annuity"] = chart_data["Monthly Annuity"].round(2)
    
    st.line_chart(
        chart_data,
        x="Retirement Date",
        y=["Full Lump Sum", "Monthly Annuity"],
        use_container_width=True
    )
    
    with st.expander("View 24-Month Data Table"):
        st.dataframe(chart_data.style.format({
            "Exact Age": "{:,.4f}",
            "Service Years": "{:,.4f}",
            "Adjusted Salary": "${:,.2f}",
            "Monthly Annuity": "${:,.2f}",
            "Full Lump Sum": "${:,.2f}",
            # === START FIX: Corrected format string ===
            "Partial Lump": "${:,.2f}", 
            # === END FIX ===
            "Reduced Annuity": "${:,.2f}"
        }))
        
        # CSV Export
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(chart_data)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name=f"{date.today().isoformat()}_export.csv",
            mime='text/csv',
        )


    # === Rate Sensitivity Table ===
    with st.expander("📉 Segment Rate Sensitivity"):
        st.dataframe(results["rate_chart"].style.format({
            "Lumpsum": "${:,.2f}"
        }))

    # === Optional Debug Panel ===
    if show_debug:
        with st.expander("🧮 Calculation Details (Based on Initial Inputs)"):
            st.markdown("**Annuity Stream (First 12 Years)**")
            st.dataframe(results["stream"].head(12).style.format({
                "Age": "{:,.4f}",
                # "Annuity": "${:,.2f}", # This column doesn't exist in the annual stream
                "Survival": "{:.5f}",
                "Segment Rate (Annual)": "{:.4f}",
                "Discount Factor": "{:.6f}",
                "PV of Payment": "${:,.2f}"
            }))
            
            st.markdown("**Full Stream Data (for export)**")
            st.dataframe(results["stream"].style.format({
                "Age": "{:,.4f}",
                # "Annuity": "${:,.2f}",
                "Survival": "{:.5f}",
                "Segment Rate (Annual)": "{:.4f}",
                "Discount Factor": "{:.6f}",
                "PV of Payment": "${:,.2f}"
            }))
    # === SSA Table ===
    st.header("🧓 Social Security Estimates")

    col_ss1, col_ss2, col_ss3 = st.columns(3)

    with col_ss1:
        st.metric("Age 62 Benefit", f"${ss_results[62]:,.2f}/mo")

    with col_ss2:
        st.metric("Age 67 Benefit", f"${ss_results[67]:,.2f}/mo")

    with col_ss3:
        st.metric("Age 70 Benefit", f"${ss_results[70]:,.2f}/mo")

    with st.expander("ℹ️ How Social Security Is Calculated"):
        st.markdown("""
        Social Security benefits are based on your **highest 35 years of indexed earnings**. Here's how the math works:

        ### 🧮 Step 1: AIME (Average Indexed Monthly Earnings)
        - Add up your top 35 years of indexed earnings.
        - Divide the total by 420 months (35 years × 12 months).
        - **Example:**  
          If your top 35 years total \\$2,100,000:  
          AIME = \\$2,100,000 ÷ 420 = **\\$5,000/month**

        ### 🧮 Step 2: PIA (Primary Insurance Amount)
        Apply the SSA bend points (2025 values) to your AIME:
        - 90% of the first \\$1,174  
        - 32% of the amount between \\$1,175 and \\$7,078  
        - 15% of the amount above \\$7,078

        **Example for AIME = \\$5,000:**
        - 90% × \\$1,174 = \\$1,056.60  
        - 32% × (\\$5,000 − \\$1,174) = \\$1,222.08  
        - Total PIA ≈ **\\$2,278.68/month**

        ### 🧮 Step 3: Benefit by Retirement Age
        - Age 62: ~70% of PIA  
        - Age 67: 100% of PIA  
        - Age 70: ~124% of PIA

        These adjustments reflect early retirement reductions and delayed retirement credits.
        """)

