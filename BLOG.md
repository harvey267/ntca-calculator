# Reverse Engineering My Own Pension

*What NTCA didn't tell me — and what I had to figure out myself.*

---

I've been an NTCA plan participant for over 30 years. When I started getting serious about retirement planning, I did what you're supposed to do: I went to the source. I ran numbers on the NTCA Pension Point calculator. I called and asked questions.

What I got back was a number. No methodology. No formula. No explanation of how a six-figure lump sum was derived from my salary and service years.

So I reverse-engineered it.

---

## What they told me

When I asked NTCA how the lump sum was calculated, I was told it was based on treasury bonds.

That's not correct.

The NTCA defined benefit plan uses IRS §417(e) — a statutory valuation method that uses high-quality corporate bond rates, not treasuries. Specifically, it uses the IRS "HQM" (High-Quality Market) corporate bond yield curve, averaged over a 24-month stability period and applied as three separate segment rates.

The distinction matters. Corporate bond yields are higher than treasuries. Higher discount rates compress the present value of future payments. The lump sum you receive is lower under §417(e) than it would be under a treasury-based valuation. This isn't a criticism of NTCA — it's the statutory method Congress set for pension plans. But if you're told "treasury bonds" and the actual rates are higher, you'll build a mental model that gives you the wrong number.

---

## How it actually works

The lump sum is the present value of your lifetime monthly annuity. To compute it, you need three things:

1. **Your monthly annuity** — `benefit_rate × high-5 salary × years_of_service / 12`
2. **Survival probabilities** — from the IRS §417(e) unisex mortality table (updated annually)
3. **Discount rates** — the three §417(e) segment rates

For each future payment month, the calculator asks: what's the probability you'll be alive to receive this payment, and what's that payment worth in today's dollars? Then it sums all 780 payments (65 years of monthly payments).

The three segment rates correspond to payment timing:

| Payments | Years out | Rate used |
|----------|-----------|-----------|
| Months 1–60 | 0–5 years | Segment 1 |
| Months 61–240 | 5–20 years | Segment 2 |
| Months 241–780 | 20+ years | Segment 3 |

NTCA applies August segment rates with a one-year look-back, meaning the rates used for a 2026 plan year calculation were set in August of the prior year and held stable throughout the plan year. This is allowed under IRS rules — plans can use a stability period of up to 12 months.

---

## How I figured it out

I had two official NTCA Pension Point outputs — lump sum estimates for two different retirement dates. The calculator produced both; I could see the results but not the formula.

I built a Python model from the IRS §417(e) spec: load the correct mortality table for the plan year, apply the three-segment discount structure, compute conditional survival probabilities from the retirement age forward, sum the present value of every payment.

My first model was off by about 1.7% consistently. The same error across both data points told me it wasn't a calculation logic problem — it was a parameter problem. The segment rates I was using (sourced from published Treasury HQM data for August 2025) didn't match what NTCA actually used.

So I ran a grid search: try every plausible combination of segment rates in 0.01% increments, find the set that minimizes error across both official outputs simultaneously.

The rates that converged: **4.10% / 5.20% / 5.80%**.

With those rates, the model produces:

| Retirement date | NTCA official | My model | Delta |
|----------------|---------------|----------|-------|
| June 1, 2029 | $958,537.47 | $958,579 | $42 |
| February 1, 2030 | $1,017,636.89 | $1,017,672 | $36 |

**$36 on a $1,017,636 lump sum. That's 0.004% error.**

Residual annuity matches to within $0.02 per month.

I'm not claiming perfect — there are still two assumptions I haven't fully pinned down: the exact look-back month NTCA used for these specific calculations, and whether partial-month accrual rounding matches their internal logic exactly. But at 0.004%, the methodology is right.

---

## The buyback years — and why they change everything

Many NTCA participants have prior industry experience that their co-op bought back when they joined the plan. Those bought-back years are credited toward your total NTCA service, and they show up in your official benefit calculation without any separate line item explaining them.

Here's how to prove whether you have them and how many.

I started at my co-op in March 2003. My NTCA Pension Point output shows 30.25 years of service as of June 2029. The math:

| | Years |
|---|---|
| Actual co-op service (March 2003 → June 2029) | 26.21 |
| NTCA-credited service | 30.25 |
| Bought-back years | **4.04** |
| Buyback covers approx. | March 1999 → March 2003 |

That 4-year gap is industry experience I had before joining the plan that NTCA credited at enrollment.

**Why it matters — the Rule of 85:**

The NTCA plan allows early retirement without penalty when your age plus years of service equals 85 or more. The buyback years are included in that calculation.

| Scenario | Age | Service | Rule of 85 |
|---|---|---|---|
| With buyback | 55.00 | 30.25 | 85.25 ✓ qualifies |
| Without buyback | 55.00 | 26.21 | 81.21 ✗ does not qualify |

Without those 4 bought-back years I don't qualify for the Rule of 85 at 55. I'd need to work until age + service = 85, which means roughly age 59 with 26 years — four more years of work.

The calculator can prove this for your own situation. Pass your co-op start date and it shows the breakdown:

```bash
python3 Python/ntca_lump_sum_calculator.py \
  --birth-date 1975-03-01 \
  --retirement-date 2031-01-01 \
  --salary 75000 \
  --years 28.5 \
  --benefit-rate 0.019 \
  --coop-start-date 2002-06-01
```

If NTCA is crediting you more years than your actual co-op tenure, you have bought-back years. If the two numbers match, you don't. Either way the math is right there.

---

## Can you legally do this?

Yes. And it's worth being clear about why, because this is a question a lot of participants will ask when they see this project.

**§417(e) is public law.** The methodology I implemented is written into the IRS code. Congress set this valuation method for defined benefit plans — it's not proprietary to NTCA. Anyone can read the statute, implement the formula, and run it against their own benefit data. That's not a workaround. That's how public law works.

**The source data is government publications.** The IRS publishes the §417(e) mortality tables annually as official IRS Notices. The Treasury publishes the HQM corporate bond yield curve data publicly. I downloaded both from official government sources. There's no confidential data in this model.

**I didn't touch NTCA's software.** Reverse engineering in the legal sense — decompiling proprietary code — is a separate question with a more complex answer. That's not what happened here. I looked at outputs, compared them to what the IRS specification would produce, and adjusted until they matched. That's analysis from public data, not copying.

**ERISA gives you the right to understand your own benefit.** Federal law requires your plan to disclose the Summary Plan Description and, on request, the plan document. The calculation methodology is information you're entitled to. Building a tool to model that methodology — for your own planning — is well within that right.

**The disclaimer covers the rest.** This tool is not NTCA's calculator. It's a model built from public law and public data. The outputs are estimates. Always verify with NTCA for official amounts.

This project exists because a plan participant couldn't get a straight answer about their own retirement. That's the only reason it was built.

---

## What surprised me most

Two findings I didn't expect going in.

**1. Your employer's benefit rate is not 1.9%.**

More precisely: it might not be. The NTCA plan is a multi-employer plan where each member co-op elects a benefit accrual rate in their Adoption Agreement. Common values are 1.9%, 1.7%, and 1.5%. Some employers elect lower rates.

For the same person — same salary, same service years, same retirement date — the difference between a 1.5% rate and a 1.9% rate is roughly **$138,000 in lump sum value**.

Most participants don't know their employer's elected rate. It's in your Summary Plan Description. If you don't have that document, ask HR directly — it's a required disclosure.

**2. The "partial lump sum" is not a percentage of your actuarial lump sum.**

I assumed a partial lump sum election meant "take X% of the present value, receive the rest as annuity." That's not how NTCA does it.

NTCA's partial lump sum is your employee contribution balance — the money you put in over your career, with interest. It's a fixed dollar amount, not a percentage. The remainder of your benefit stays as a monthly annuity calculated on your full accrued benefit minus an actuarial offset for what you took out.

This matters for how you model the trade-off between lump sum and annuity income.

---

## One more thing: the buy-out trigger

For participants retiring on or after February 1, 2030, there's a specific plan provision that credits one additional year of service for purposes of the lump sum calculation. This isn't a calendar-year-crossing rule — it's a plan-specific provision with a fixed effective date.

The difference between a June 2029 retirement and a February 2030 retirement in my data isn't just 8 months of additional accrual. The buy-out applies to the February 2030 date and not the June 2029 date. That's part of why the February 2030 number is significantly higher.

If you're within a year or two of that date, it's worth running both sides.

---

## What's available now

I've built two tools:

**CLI calculator** — runs a single lump sum estimate from the command line. Takes your birth date, retirement date, high-5 salary, years of service, and employer benefit rate. Outputs the full annuity stream breakdown and a summary. If you want to see the math step by step, it's all in the spreadsheet export.

**Streamlit dashboard** — interactive version. Adjust inputs with sliders, see a retirement window curve (how the lump sum changes month by month), run segment rate sensitivity analysis, and optionally add Social Security projections from an earnings CSV.

Both tools are on GitHub: [harvey267/ntca-calculator](https://github.com/harvey267/ntca-calculator)

```bash
# CLI — quick estimate
python3 Python/ntca_lump_sum_calculator.py \
  --birth-date 1975-03-15 \
  --retirement-date 2031-01-01 \
  --salary 75000 \
  --years 28.5 \
  --benefit-rate 0.019

# Dashboard
cd Python/ntca_pension_dashboard
streamlit run app.py
```

The inputs you need to know before running:

| Input | Where to find it |
|-------|-----------------|
| High-5 salary | Average of your 5 highest compensation years in the last 10 plan years — NTCA can give you this |
| Years of service | Your total plan participation years, including fractions |
| Employer benefit rate | Your Summary Plan Description or Adoption Agreement — ask HR |
| Segment rates | Built-in defaults are verified against 2026 plan year outputs. Override if you have current data. |

---

## What's next

In July 2026, a second participant — within about a year of their eligibility date — has agreed to share their official NTCA Pension Point outputs. Near-eligibility calculations are the hard test: buy-out logic, final accrual rounding, and look-back month timing all matter most when you're close. I'll run their data through the model, document the agreement or divergence, and update the tools.

After that validation: I'll build an Excel version for participants who don't want to run Python, deploy the Streamlit app publicly, and write up a complete methodology document.

If you're an NTCA plan participant and want to run your own numbers before then — clone the repo, fill in your inputs, and let me know what you get. The more data points we have against official NTCA outputs, the tighter this gets.

---

*Tools and source code: [github.com/harvey267/ntca-calculator](https://github.com/harvey267/ntca-calculator)*

*This is an educational tool. All calculations are estimates based on publicly available IRS rules and reverse-engineered NTCA methodology. Verify with NTCA directly for official benefit amounts.*
