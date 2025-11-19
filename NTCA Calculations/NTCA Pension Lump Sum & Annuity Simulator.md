📘 NTCA Pension Lump Sum & Annuity Simulator
This simulator calculates the present value of a monthly pension annuity stream using IRS §417(e) unisex mortality assumptions and segment-based discounting. It replicates NTCA’s lump sum methodology with precision and transparency.

🚀 How to Run the Program
1. Clone or Download the Project
Make sure your folder contains the following files:
```
ntca-pension-simulator/
├── app.py                  # Streamlit UI
├── pension_model.py        # Core calculation engine
├── n-24-42.csv             # IRS §417(e) mortality table (Notice 2024-42)
```
2. Install Python and Required Packages
Ensure you have Python 3.9+ installed. Then install dependencies:
```
pip install streamlit pandas numpy python-dateutil
```
3. Launch the App
From the project directory, run:
```
streamlit run app.py
```
This will open the app in your default web browser.

🧮 What the App Does
The simulator computes the lump sum equivalent of a monthly pension annuity using:
• 	IRS §417(e) unisex mortality table (Notice 2024-42)
• 	Segment-based discounting (3 IRS interest rates)
• 	Monthly interpolation of survival probabilities
• 	Present value of each monthly payment
• 	Optional partial lump sum and reduced annuity

🧮 How the Calculations Work
🎯 Goal

To compute the lump sum equivalent of a monthly pension annuity using:
- IRS §417(e) unisex mortality
- Segment-based discounting (3 IRS rates)
- Monthly interpolation and survival probabilities

🔢 Step-by-Step Breakdown
1. Mortality Table Loading
- Source:  from IRS Notice 2024-42
- Columns: ,  (probability of death within the year)
- Compute  (probability of survival)
- Cumulative survival from age 55 onward:

$\text{cum\_survival}[x] = \prod_{i=55}^{x} px[i]$

- Normalize so that survival at age 55 = 1.0

2. Monthly Interpolation
- Interpolate cumulative survival for every month from age 55 to 120
- Used to estimate survival probability at fractional ages

3. Exact Age Calculation
- Based on birth date and retirement date:

$\text{Age} = \frac{\text{days between dates}}{365.25}$

4. Monthly Annuity Calculation
- Formula:

$\text{Monthly Annuity} = \frac{0.019 \cdot \text{Salary} \cdot \text{Years of Service}}{12}$

5. Annuity Stream Construction
- For each month from retirement to age 120:
- Determine age at that month
- Apply IRS segment rate:
- Segment 1: months 1–60
- Segment 2: months 61–240
- Segment 3: months 241+
- Monthly discount rate:

$r = \frac{\text{segment rate}}{12}$

- Discount factor:

$DF = \frac{1}{(1 + r)^n}$

- Survival probability from mortality table
- Present value of payment:

$PV = \text{Annuity} \cdot \text{Survival} \cdot DF$

6. Lump Sum Calculation
- Sum all monthly PVs:

$\text{Lump Sum} = \sum PV[n]$

- PV factor:

$\text{PV Factor} = \frac{\text{Lump Sum}}{\text{Annuity} \cdot 12}$

- Partial lump sum and reduced annuity:

$\text{Partial Lump} = \text{Lump Sum} \cdot \text{Partial \%}$
$\text{Reduced Annuity} = \text{Annuity} \cdot (1 - \text{Partial \%})$

7. Retirement Window Simulation
- Simulates lump sum and annuity for 24 months starting from selected retirement date
- Useful for timing optimization

8. Segment Rate Sensitivity
- Simulates lump sum impact of ±0.25% changes in each segment rate
- Helps assess interest rate risk

📊 Inputs Required
- Date of Birth
- Retirement Date
- Final Average Salary
- Years of Service
- Partial Lump Sum %
- IRS Segment Rates (from August prior year)

📁 Output Summary
- Monthly Annuity
- Full Lump Sum
- PV Factor
- Partial Lump Sum
- Reduced Annuity
- Retirement Window (24-month simulation)
- Segment Rate Sensitivity

✅ Benchmark Alignment
This simulator matches NTCA’s published lump sum for:
- DOB: 6/10/1974
- Retirement: 6/1/2029
- Salary: $126,339.20
- Years: 26.00
- Segment Rates: 4.50%, 4.96%, 5.40%

***Expected Output:

| Metric          | Value        |
| --------------- | ------------ |
| Monthly Annuity | $5,226.71    |
| PV Factor       | ~14.36       |
| Lump Sum        | ~$900,585.06 |

---

To run this simulator with accurate data, you’ll need the IRS §417(e) unisex mortality table and segment rates. Below are direct links to the official sources.

📥 Required Data Sources
1. IRS §417(e) Unisex Mortality Table (Notice 2024-42)
This is the official mortality table used for minimum present value calculations for annuity starting dates in 2025.
- 🔗 [Download IRS Notice 2024-42 (PDF)](chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/https://www.irs.gov/pub/irs-drop/n-24-42.pdf)
- This includes the static unisex mortality table used in your  file.

2. IRS Segment Rates (Monthly Updates)
Segment rates are published monthly and used to discount future annuity payments. For a retirement in 2029, use the rates from August 2028.
- 🔗 [IRS Segment Rate Archive](https://www.irs.gov/retirement-plans/minimum-present-value-segment-rates)
- Look for the August rates from the year prior to your retirement year.

3. IRS Mortality Table Overview Page
This page provides context and links to all current and historical mortality tables used for pension calculations.
• 	[🔗 IRS Mortality Tables Overview](https://www.irs.gov/retirement-plans/pension-plan-mortality-tables)

🧮 How to Use These in Your Simulator
• 	Save the mortality table from Notice 2024-42 as  with columns: , 
• 	Use the segment rates from the August prior year in your app sidebar:
• 	Segment 1 Rate (%)
• 	Segment 2 Rate (%)
• 	Segment 3 Rate (%)

🛠 Optional Enhancements
- Add export to CSV/Excel
- Add charts for PV decay or survival curve
- Add toggle for buyout logic comparison