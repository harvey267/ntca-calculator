# ============================================
# 📦 SECTION 1: Imports and Setup
# ============================================

import streamlit as st
import pandas as pd
from datetime import date
import os

# === Import core simulation logic ===
from pension_model import run_simulation
from ssa_model import ss_benefits  # SSA logic assumed to be modular

# === CSV Export Utility ===
@st.cache_data
def convert_df(df):
    """
    Converts a DataFrame to downloadable CSV format.
    Cached for performance.
    """
    return df.to_csv(index=False).encode('utf-8')

# === Streamlit Page Configuration ===
st.set_page_config(page_title="NTCA Pension Dashboard", layout="wide")
st.title("NTCA Pension Calculator")

# ============================================
# 🧮 SECTION 2: Sidebar Inputs
# ============================================

# === NTCA Pension Inputs ===
with st.sidebar.expander("🏛 NTCA Pension Inputs", expanded=True):
    birth_date = st.date_input("Date of Birth", date(1970, 1, 1))
    retire_date = st.date_input(
        "Retirement Date", date(2030, 1, 1),
        help="Set to your intended retirement date. "
             "If your employer has elected the Rule-of-85 Provision (optional — check your Summary Plan Description), "
             "penalty-free early retirement applies when your age plus Rule-of-85 Service equals or exceeds 85. "
             "With 30 credited years, the earliest qualifying age is 55. "
             "Not all NTCA member employers have elected this provision."
    )
    salary = st.number_input("High-5 Salary ($)", min_value=10000.00, max_value=500000.00, value=80000.00, step=0.01, format="%.2f")
    years = st.number_input("Years of Service", min_value=1.0000, max_value=50.0000, value=25.0000, step=0.0001, format="%.4f")
    benefit_rate_pct = st.number_input(
        "Employer Benefit Rate (%)",
        min_value=0.5, max_value=3.0, value=1.9, step=0.1, format="%.1f",
        help="Your employer's elected accrual rate from the NTCA Adoption Agreement. "
             "Common values: 1.9%, 1.7%, 1.5%. Not the same for all NTCA member employers — "
             "check your Summary Plan Description or ask your HR/benefits contact."
    )
    benefit_rate = benefit_rate_pct / 100.0
    assumed_growth = st.number_input("Annual Salary Growth (%)", min_value=0.000, max_value=10.000, value=0.000, step=0.001, format="%.3f")
    partial = st.slider("Partial Lump Sum (% of Full)", min_value=0, max_value=100, value=0, step=5) / 100.0

# === IRS Segment Rates ===
with st.sidebar.expander("📈 IRS Segment Rates"):
    st.markdown(
        "Enter rates as percentages (e.g., 4.50). "
        "Per NTCA plan document Article IV.C(3)(f), the applicable rate is the **§417(e)(3) rate "
        "for August immediately preceding the calendar year of your retirement date** — not the "
        "current month's rate. For a 2029 retirement, use August 2028 rates. "
        "Look up the correct month at the "
        "[IRS minimum present value segment rates table](https://www.irs.gov/retirement-plans/minimum-present-value-segment-rates)."
    )
    rate_tables = {}

    # Define rates for 2029–2031
    for year in [2029, 2030, 2031]:
        with st.expander(f"{year} Rates — use August {year - 1} §417(e)(3) rates", expanded=(year == 2029)):
            seg1 = st.number_input(f"{year} Seg 1 (%)", value=4.50, step=0.01, format="%.2f") / 100.0
            seg2 = st.number_input(f"{year} Seg 2 (%)", value=4.96, step=0.01, format="%.2f") / 100.0
            seg3 = st.number_input(f"{year} Seg 3 (%)", value=5.40, step=0.01, format="%.2f") / 100.0
            rate_tables[year] = {"seg1": seg1, "seg2": seg2, "seg3": seg3}

    # Extend 2032 using 2031 rates
    rate_tables[2032] = rate_tables[2031]

# === Mortality Table Selection ===
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

# === NTCA Comparison Upload ===
with st.sidebar.expander("📥 Upload NTCA Official Comparison"):
    ntca_file = st.file_uploader("Upload NTCA Excel File", type=["xlsx"])

# === SSA Earnings Upload and Editor ===
with st.sidebar.expander("🧓 Social Security Earnings"):
    st.markdown("Upload a CSV with columns: `year`, `income`")
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

    editable_rows = []
    previous_income = None

    for year in range(start_year, end_year + 1):
        age = year - birth_date.year
        income = income_by_year.get(year, previous_income if year >= current_year else 0)
        editable_rows.append({"Age": age, "Year": year, "Income": income})
        previous_income = income

    editable_df = pd.DataFrame(editable_rows)
    st.markdown("### ✏️ Editable SSA Earnings Table")
    edited_df = st.data_editor(editable_df, num_rows="fixed", width='stretch')
    income_by_year = {int(row["Year"]): float(row["Income"]) for _, row in edited_df.iterrows()}

# === 401(k) Withdrawal Planning ===
with st.sidebar.expander("💼 Future 401(k) & Investments"):
    st.markdown("Enter projected annual withdrawals by year:")
    future_401k = {}
    for year in range(retire_date.year, birth_date.year + 91):
        amt = st.number_input(f"401(k) Withdrawal for {year}", min_value=0, value=0, key=f"k401_{year}")
        future_401k[year] = amt

# === S&P 500 Comparison Inputs ===
with st.sidebar.expander("📈 S&P 500 Comparison"):
    contribution_rate_pct = st.number_input(
        "Employee Contribution Rate (%)",
        min_value=0.0, max_value=20.0, value=4.0, step=0.5, format="%.1f",
        help="Your annual contribution to the pension plan as a % of salary. "
             "Common NTCA values: 3% or 4%. Check your plan documents."
    )
    contribution_rate = contribution_rate_pct / 100.0
    sp500_return_pct = st.slider(
        "Assumed Annual Return (%)",
        min_value=4.0, max_value=14.0, value=10.0, step=0.5,
        help="S&P 500 long-run nominal average: ~10%. Use 7% for inflation-adjusted real returns."
    )
    sp500_return = sp500_return_pct / 100.0

# === Debug and Disclaimer ===
st.sidebar.markdown("---")
show_debug = st.sidebar.checkbox("Show Debug Panel", value=True)
st.sidebar.markdown("""
*Disclaimer: This is an educational tool. All calculations are estimates based on the best available public data and reverse-engineering. Always consult NTCA for official numbers.*
""")

# === Discount Offset Mode ===
with st.sidebar.expander("🧮 Discount Offset Logic"):
    offset_mode = st.selectbox("Offset Mode", [
        "Dynamic (Day-Level)",
        "Fixed (NTCA-style)",
        "Custom"
    ])

    # Default values
    fixed_offset = 0.0674083
    custom_offset = 0.0674

    # Allow adjustment of fixed offset
    if offset_mode == "Fixed (NTCA-style)":
        fixed_offset = st.number_input(
            "Fixed Offset Value (fractional years)",
            min_value=0.0000, max_value=1.0000, value=0.0674083, step=0.0001, format="%.6f"
        )

    # Allow adjustment of custom offset
    elif offset_mode == "Custom":
        custom_offset = st.number_input(
            "Custom Offset Value (fractional years)",
            min_value=0.0000, max_value=1.0000, value=0.0674, step=0.0001, format="%.4f"
        )

    # Final offset value passed to model
    discount_offset = (
        fixed_offset if offset_mode == "Fixed (NTCA-style)"
        else custom_offset if offset_mode == "Custom"
        else None  # Dynamic mode will calculate internally
    )

# ============================================
# 🧠 SECTION 3: Run Simulation
# ============================================

try:
    results = run_simulation(
        birth_date,
        retire_date,
        salary,
        years,
        partial,
        rate_tables,
        assumed_growth / 100.0,
        mortality_table_csv,
        offset_mode,
        discount_offset  # ✅ Unified offset value passed correctly
    )
    ss_results = ss_benefits(birth_date.year, income_by_year)
except Exception as e:
    st.error(f"An error occurred during calculation: {e}")
    st.exception(e)
    st.stop()

# ============================================
# 📊 SECTION 4: Unified Retirement Income Forecast
# ============================================

def build_income_timeline(birth_year, retire_year, pension_monthly, ss_results, future_401k=None):
    rows = []
    for year in range(retire_year, birth_year + 91):
        age = year - birth_year
        pension = pension_monthly * 12 if year >= retire_year else 0
        ss = 0
        if age >= 62:
            ss = ss_results.get(min(age, 70), 0) * 12
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

income_df = build_income_timeline(
    birth_year=birth_date.year,
    retire_year=retire_date.year,
    pension_monthly=results["summary"]["Monthly Annuity"],
    ss_results=ss_results,
    future_401k=future_401k
)

# === Display Unified Income Forecast ===
st.header("📊 Unified Retirement Income Forecast")
st.line_chart(income_df, x="Year", y=["Pension", "Social Security", "401(k)", "Total Income"], width='stretch')

with st.expander("View Income Table"):
    st.dataframe(income_df.style.format({
        "Pension": "${:,.2f}",
        "Social Security": "${:,.2f}",
        "401(k)": "${:,.2f}",
        "Total Income": "${:,.2f}"
    }))

# ============================================
# 📋 SECTION 5: Summary Panel
# ============================================

if results:
    st.header("Summary Panel")
    col1, col2 = st.columns(2)

    # === Current Retirement Date Projection ===
    with col1:
        st.subheader("Current Date Projection")
        st.metric("Retirement Date", retire_date.strftime("%Y-%m-%d"))
        st.metric("Full Lump Sum", f"${results['summary']['Full Lump Sum']:,.2f}")
        st.metric("Monthly Annuity", f"${results['summary']['Monthly Annuity']:,.2f}")
        st.metric("Present Value Factor", f"{results['summary']['PV Factor']:.4f}")
        if partial > 0:
            st.metric("Partial Lump Sum", f"${results['summary']['Partial Lump Sum']:,.2f}")
            st.metric("Reduced Monthly Annuity", f"${results['summary']['Reduced Annuity']:,.2f}")

    # === Feb 1st Projection (Buy-Out Trigger) ===
    with col2:
        st.subheader("Feb 1, 2030 Projection (Buy-Out Trigger)")
        st.metric("Retirement Date", results['feb_1_summary']['Date'].strftime("%Y-%m-%d"))
        st.metric("Full Lump Sum", f"${results['feb_1_summary']['Full Lump Sum']:,.2f}")
        st.metric("Monthly Annuity", f"${results['feb_1_summary']['Monthly Annuity']:,.2f}")
        st.metric("Present Value Factor", f"{results['feb_1_summary']['PV Factor']:.4f}")
        if partial > 0:
            st.metric("Partial Lump Sum", f"${results['feb_1_summary']['Partial Lump Sum']:,.2f}")
            st.metric("Reduced Monthly Annuity", f"${results['feb_1_summary']['Reduced Annuity']:,.2f}")

    with st.expander("ℹ️ How Timing Affects Lump Sum Calculations"):
        st.markdown("""
        **Segment rates and the August lookback**

        Per NTCA R&S Program Specifications Article IV.C(3)(f), the applicable interest rate is the
        §417(e)(3) rate for **August immediately preceding the calendar year of your retirement date** —
        not the current month. For a 2029 retirement, enter August 2028 rates in the sidebar.
        Look these up at the [IRS minimum present value segment rates table](https://www.irs.gov/retirement-plans/minimum-present-value-segment-rates).

        **The Feb 1, 2030 buy-out trigger**

        A plan-specific provision (Article IV of the NTCA R&S Specifications) credits one additional
        year of service for lump sum purposes for retirements on or after February 1, 2030.
        This is not a standard IRS rule. The right column above shows what your benefit would be
        under that provision. Verify this provision applies to your plan year before relying on it.

        **Rule-of-85 Provision**

        The Rule-of-85 (penalty-free early retirement when age + service ≥ 85) is an **optional
        provision** that each NTCA member employer must elect in their Adoption Agreement
        (Definition 33, NTCA R&S Specifications). Check your Summary Plan Description or contact
        HR to confirm whether your employer has elected it before setting your retirement date.

        **Discount Offset Logic**

        NTCA allows retirees to select the exact date they begin receiving payments.
        This model reflects that by adjusting the timing of each payment in the present value stream.

        **How It Works:**
        - The discount offset is calculated based on your selected retirement date.
        - It shifts the discount curve to reflect when payments begin.
        - Earlier payment dates result in slightly higher lump sums.

        **Formula Used:**
        ```
        offset = ((month - 1) + (day - 1) / 30.0) / 12.0
        ```

        This ensures actuarial-grade precision and alignment with NTCA’s calculator.
        """)

# ============================================
# 📆 SECTION 6: Retirement Window Simulation
# ============================================

# === NTCA Comparison Panel ===
if ntca_file:
    compare_with_ntca(results["retire_chart"], ntca_file)

# === Display Retirement Window Chart ===
chart_data = results["retire_chart"].copy()
chart_data["Full Lump Sum"] = chart_data["Full Lump Sum"].round(2)
chart_data["Monthly Annuity"] = chart_data["Monthly Annuity"].round(2)

st.line_chart(
    chart_data,
    x="Retirement Date",
    y=["Full Lump Sum", "Monthly Annuity"],
    width='stretch'
)

with st.expander("View 24-Month Data Table"):
    st.dataframe(chart_data.style.format({
        "Exact Age": "{:,.4f}",
        "Service Years": "{:,.4f}",
        "Adjusted Salary": "${:,.2f}",
        "Monthly Annuity": "${:,.2f}",
        "Full Lump Sum": "${:,.2f}",
        "Partial Lump": "${:,.2f}",
        "Reduced Annuity": "${:,.2f}"
    }))

    csv = convert_df(chart_data)
    st.download_button(
        label="Download Data as CSV",
        data=csv,
        file_name=f"{date.today().isoformat()}_export.csv",
        mime='text/csv',
    )

# ============================================
# 📉 SECTION 7: Segment Rate Sensitivity
# ============================================

with st.expander("📉 Segment Rate Sensitivity"):
    st.dataframe(results["rate_chart"].style.format({
        "Lumpsum": "${:,.2f}",
        "Change from Base": "${:,.2f}"
    }))

# ============================================
# 🧮 SECTION 8: Debug Panel (Optional)
# ============================================

if show_debug:
    with st.expander("🧮 Calculation Details (Based on Initial Inputs)"):
        st.markdown("**Annuity Stream (First 12 Years)**")
        st.dataframe(results["stream"].head(12).style.format({
            "Age": "{:,.4f}",
            "Survival": "{:.5f}",
            "Segment Rate (Annual)": "{:.4f}",
            "Discount Factor": "{:.6f}",
            "PV of Payment": "${:,.2f}"
        }))

        st.markdown("**Full Stream Data (for export)**")
        st.dataframe(results["stream"].style.format({
            "Age": "{:,.4f}",
            "Survival": "{:.5f}",
            "Segment Rate (Annual)": "{:.4f}",
            "Discount Factor": "{:.6f}",
            "PV of Payment": "${:,.2f}"
        }))

# ============================================
# 🧓 SECTION 9: Social Security Summary
# ============================================

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

# ============================================
# 📊 SECTION 10: S&P 500 Comparison
# ============================================

st.header("📊 Pension vs. S&P 500 Investment Comparison")
st.markdown(
    f"What if you invested your **{contribution_rate_pct:.1f}% annual contribution** in the S&P 500 "
    f"instead of the pension? Modeled over **{years:.2f} years** at **{sp500_return_pct:.1f}% annual return**."
)

# The pension lump sum scales linearly with salary (same PV factor, same years, same benefit rate)
# so we can derive lump sum for any salary tier from the current simulation result.
pv_factor_per_salary_dollar = results["summary"]["Full Lump Sum"] / salary

salary_tiers = [60_000, 80_000, 100_000]
comparison_rows = []
for tier_salary in salary_tiers:
    annual_contribution = tier_salary * contribution_rate
    # Future value of end-of-year contributions: FV = PMT × [(1+r)^n - 1] / r
    n = years
    r = sp500_return
    if r == 0:
        sp500_portfolio = annual_contribution * n
    else:
        sp500_portfolio = annual_contribution * ((1 + r) ** n - 1) / r

    pension_lump = pv_factor_per_salary_dollar * tier_salary
    pension_monthly = (benefit_rate * tier_salary * years) / 12
    diff = sp500_portfolio - pension_lump

    comparison_rows.append({
        "Salary":                  f"${tier_salary:,}",
        "Annual Contribution":     f"${annual_contribution:,.0f}",
        "S&P 500 Portfolio":       f"${sp500_portfolio:,.0f}",
        "Pension Lump Sum":        f"${pension_lump:,.0f}",
        "Difference (S&P – Pension)": f"${diff:+,.0f}",
        "Pension Monthly Annuity": f"${pension_monthly:,.2f}",
    })

comparison_df = pd.DataFrame(comparison_rows)
st.dataframe(comparison_df, hide_index=True, use_container_width=True)

# Year-by-year growth chart for user's actual salary
growth_rows = []
portfolio_value = 0.0
annual_contribution_actual = salary * contribution_rate
pension_lump_actual = results["summary"]["Full Lump Sum"]

for yr in range(1, int(years) + 2):
    portfolio_value = portfolio_value * (1 + sp500_return) + annual_contribution_actual
    growth_rows.append({
        "Year of Service": yr,
        "S&P 500 Portfolio": round(portfolio_value, 2),
        "Pension Lump Sum":  round(pension_lump_actual, 2),
    })

growth_df = pd.DataFrame(growth_rows)

st.markdown(f"**Your salary (${salary:,.0f}) — portfolio growth vs. pension lump sum target:**")
st.line_chart(growth_df, x="Year of Service", y=["S&P 500 Portfolio", "Pension Lump Sum"])

st.info(
    "**What this comparison doesn't capture:** The pension lump sum is funded by both your contributions "
    "and your employer's contributions — the employer absorbs the actuarial risk. "
    "The S&P 500 scenario models only your employee contributions with no employer match. "
    "Market returns also vary year to year — a bad sequence of returns near retirement can significantly "
    "reduce the final portfolio value."
)

# ============================================
# 📊 SECTION 11: Career Trajectory Comparison
# ============================================

st.header("📈 Career Trajectory Comparison")
st.markdown(
    "The pension benefit is based on your **High-5 salary of your last 10 years** — not your career average. "
    "This section models how the pension compares to a 401k when contributions and salary grow together over a career."
)

col_traj1, col_traj2, col_traj3 = st.columns(3)
with col_traj1:
    traj_start_salary = st.number_input(
        "Starting Salary ($)", min_value=20000, max_value=200000, value=30000, step=5000,
        help="Salary in year 1 of plan participation."
    )
with col_traj2:
    traj_end_salary = st.number_input(
        "Ending Salary ($)", min_value=20000, max_value=500000, value=70000, step=5000,
        help="Salary at final year of service."
    )
with col_traj3:
    traj_years = st.number_input(
        "Years of Service", min_value=5, max_value=45, value=30, step=1,
        help="Total plan participation years."
    )

traj_benefit_rate = st.number_input(
    "Benefit Rate (%)", min_value=1.0, max_value=3.0, value=1.9, step=0.1,
    format="%.1f",
    key="traj_benefit_rate",
    help="Employer's elected accrual rate from Adoption Agreement."
) / 100.0

traj_contrib_rate = st.number_input(
    "Employer Contribution Rate (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.5,
    format="%.1f",
    key="traj_contrib_rate",
    help="The percentage of salary directed to the pension (or hypothetical 401k)."
) / 100.0

# Derive annual growth rate from start/end salary and years
if traj_years > 1 and traj_end_salary > traj_start_salary:
    traj_growth = (traj_end_salary / traj_start_salary) ** (1.0 / (traj_years - 1)) - 1.0
else:
    traj_growth = 0.0

traj_salaries = [traj_start_salary * (1 + traj_growth) ** i for i in range(int(traj_years))]

# High-5 of last 10 years
traj_last10 = traj_salaries[-10:] if len(traj_salaries) >= 10 else traj_salaries
traj_high5 = sum(sorted(traj_last10, reverse=True)[:5]) / min(5, len(traj_last10))
traj_career_avg = sum(traj_salaries) / len(traj_salaries)
traj_monthly_annuity = traj_benefit_rate * traj_high5 * traj_years / 12

# Lump sum using PV factor from current simulation (scales with salary)
if salary > 0 and results["summary"]["Full Lump Sum"] > 0:
    pv_factor_traj = results["summary"]["Full Lump Sum"] / (
        benefit_rate * salary * years / 12 * 12
    )
    traj_lump = traj_monthly_annuity * 12 * pv_factor_traj
else:
    traj_lump = 0.0

# 401k balances at multiple return rates
traj_return_scenarios = [
    ("Conservative bonds", 0.05),
    ("Target date fund", 0.065),
    ("S&P 500 historical", 0.10),
]

# Salary basis comparison
st.subheader("Salary basis: High-5 vs career average")
salary_basis_data = {
    "Metric": ["Career average salary", "High-5 of last 10 years", "Difference", "Monthly annuity (career avg)", "Monthly annuity (High-5)", "Monthly benefit gain"],
    "Value": [
        f"${traj_career_avg:,.0f}",
        f"${traj_high5:,.0f}",
        f"+${traj_high5 - traj_career_avg:,.0f} ({(traj_high5/traj_career_avg - 1)*100:.1f}% higher)" if traj_career_avg > 0 else "N/A",
        f"${traj_benefit_rate * traj_career_avg * traj_years / 12:,.2f}/month",
        f"${traj_monthly_annuity:,.2f}/month",
        f"+${traj_monthly_annuity - traj_benefit_rate * traj_career_avg * traj_years / 12:,.2f}/month",
    ]
}
st.dataframe(pd.DataFrame(salary_basis_data), hide_index=True, use_container_width=True)

# Full comparison table
st.subheader("Pension vs. 401k across return scenarios")
traj_rows = []
for label, ret in traj_return_scenarios:
    k401 = sum(
        traj_salaries[i] * traj_contrib_rate * (1 + ret) ** (int(traj_years) - 1 - i)
        for i in range(int(traj_years))
    )
    swr_monthly = k401 * 0.04 / 12
    traj_rows.append({
        "Investment scenario":    label,
        "Return rate":            f"{ret*100:.1f}%",
        "401k balance":           f"${k401:,.0f}",
        "401k monthly (4% SWR)":  f"${swr_monthly:,.0f}",
        "Pension lump sum":       f"${traj_lump:,.0f}",
        "Pension monthly":        f"${traj_monthly_annuity:,.0f}",
        "Pension / 401k ratio":   f"{traj_lump / k401:.1f}x" if k401 > 0 else "N/A",
    })

st.dataframe(pd.DataFrame(traj_rows), hide_index=True, use_container_width=True)

st.caption(
    f"Salary growth rate: {traj_growth*100:.2f}% per year | "
    f"Starting salary: ${traj_start_salary:,} | "
    f"Final salary: ${traj_salaries[-1]:,.0f} | "
    f"High-5: ${traj_high5:,.0f} | "
    f"Career average: ${traj_career_avg:,.0f}"
)

