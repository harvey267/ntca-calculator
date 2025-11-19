# Streamlit Dahboard

import streamlit as st
import pandas as pd
from datetime import date
from pension_model import run_simulation
import os # Import os to get mortality file list

st.set_page_config(page_title="NTCA Pension Dashboard", layout="wide")

st.title("📊 NTCA Pension Lump Sum & Annuity Simulator")

# === Sidebar Inputs ===
st.sidebar.header("Input Parameters")

birth_date = st.sidebar.date_input("Date of Birth", date(1974, 6, 10))
retire_date = st.sidebar.date_input(
    "Retirement Date",
    date(2029, 6, 1),
    help="This is the date you begin receiving payments. The model adjusts timing accordingly."
)

# === START FIX: Use Ground Truth Salary and re-calculated Service Years ===
salary = st.sidebar.number_input(
    "Final Average Salary ($)",
    min_value=10000.00,
    max_value=500000.00,
    value=126339.20, # Your $60.74/hr * 40 * 52 salary
    step=0.01,
    format="%.2f"
)

years = st.sidebar.number_input(
    "Years of Service (at start date)",
    min_value=1.0000,
    max_value=50.0000,
    value=26.1288, # The service years required to get $5,226.71 annuity
    step=0.0001,
    format="%.4f"
)

assumed_growth = st.sidebar.number_input(
    "Assumed Annual Salary Growth (%)",
    min_value=0.000,
    max_value=10.000,
    value=0.136, # From reverse-engineering the screenshot
    step=0.001,
    format="%.3f"
)
# === END FIX ===

partial = st.sidebar.slider("Partial Lump Sum (% of Full)", min_value=0, max_value=100, value=0, step=5) / 100.0

# === START FIX: Update mortality default ===
# Dynamically find all .csv files in the current directory
try:
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
except Exception as e:
    csv_files = ["n-23-73.csv", "n-24-42.csv", "n-25-40.csv"] # Fallback

# Set the default to the one user identified
default_mortality_csv = "n-24-42.csv"
if default_mortality_csv not in csv_files:
    # Fallback if the user's preferred file isn't found
    if "n-23-73.csv" in csv_files:
        default_mortality_csv = "n-23-73.csv"
    elif csv_files:
        default_mortality_csv = csv_files[0]
    else:
        # Absolute fallback if no CSVs are found
        default_mortality_csv = "n-24-42.csv" 

# Find the index for the default
try:
    default_index = csv_files.index(default_mortality_csv)
except ValueError:
    csv_files.append(default_mortality_csv) # Add if missing
    default_index = csv_files.index(default_mortality_csv)


mortality_table_csv = st.sidebar.selectbox(
    "Mortality Table CSV",
    options=csv_files,
    index=default_index
)
# === END FIX ===


st.sidebar.markdown("---")
show_debug = st.sidebar.checkbox("Show Debug Panel", value=True)
st.sidebar.markdown("""
*Disclaimer: This is an educational tool. All calculations are estimates based on the best available public data and reverse-engineering. Always consult NTCA for official numbers.*
""")

# === Segment Rate Inputs ===
st.sidebar.header("IRS Segment Rates (%)")
st.sidebar.markdown("Enter rates as percentages (e.g., 4.50)")

rate_tables = {}

with st.sidebar.expander("2029 Rates (Notice 2028-xx)", expanded=True):
    # === START FIX: Update 2029 defaults ===
    seg1_2029 = st.number_input("2029 Seg 1", value=4.50, step=0.01, format="%.2f") / 100.0
    seg2_2029 = st.number_input("2029 Seg 2", value=4.96, step=0.01, format="%.2f") / 100.0
    seg3_2029 = st.number_input("2029 Seg 3", value=5.40, step=0.01, format="%.2f") / 100.0
    # === END FIX ===
    rate_tables[2029] = {"seg1": seg1_2029, "seg2": seg2_2029, "seg3": seg3_2029}

with st.sidebar.expander("2030 Rates (Notice 2029-xx)"):
    # Placeholder for 2030 rates
    seg1_2030 = st.number_input("2030 Seg 1", value=4.50, step=0.01, format="%.2f") / 100.0
    seg2_2030 = st.number_input("2030 Seg 2", value=4.96, step=0.01, format="%.2f") / 100.0
    seg3_2030 = st.number_input("2030 Seg 3", value=5.40, step=0.01, format="%.2f") / 100.0
    rate_tables[2030] = {"seg1": seg1_2030, "seg2": seg2_2030, "seg3": seg3_2030}

with st.sidebar.expander("2031 Rates (Notice 2030-xx)"):
    # Placeholder for 2031 rates
    seg1_2031 = st.number_input("2031 Seg 1", value=4.50, step=0.01, format="%.2f") / 100.0
    seg2_2031 = st.number_input("2031 Seg 2", value=4.96, step=0.01, format="%.2f") / 100.0
    seg3_2031 = st.number_input("2031 Seg 3", value=5.40, step=0.01, format="%.2f") / 100.0
    rate_tables[2031] = {"seg1": seg1_2031, "seg2": seg2_2031, "seg3": seg3_2031}

# Add a fallback for 2032 to allow 24-month sim from 2031
rate_tables[2032] = rate_tables[2031] # Simple fallback

# === Main Panel ===

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
except Exception as e:
    st.error(f"An error occurred during calculation: {e}")
    st.exception(e) # Show full traceback
    st.stop()

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
    st.header("Retirement Window Simulation (24 Months)")
    
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
    st.subheader("📉 Segment Rate Sensitivity")
    st.dataframe(results["rate_chart"].style.format({
        "Lumpsum": "${:,.2f}" # Renamed from "Lump Sum" to match model output
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