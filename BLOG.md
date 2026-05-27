# Reverse Engineering My Own Pension

*What NTCA didn’t tell me – and what I had to figure out myself.*

-----

I have been an NTCA plan participant for over 20 years. When I started getting serious about retirement planning, I did what you are supposed to do: I went to the source. I ran numbers on the NTCA Pension Point calculator. I called and asked questions.

What I got back was a number. No methodology. No formula. No explanation of how a six-figure lump sum was derived from my salary and service years.

So I reverse-engineered it.

-----

## What they told me

When I asked how NTCA calculated the lump sum, I was told it was based on treasury bonds.

That is not correct.

The NTCA defined benefit plan uses IRS §417(e) – a statutory valuation method that uses high-quality corporate bond rates, not treasuries. Specifically, it uses the IRS “HQM” (High-Quality Market) corporate bond yield curve, averaged over a 24-month stability period and applied as three separate segment rates.

The distinction matters. Corporate bond yields are higher than treasuries. Higher discount rates compress the present value of future payments. The lump sum you receive is lower under §417(e) than it would be under a treasury-based valuation. This is not a criticism of NTCA – it is the statutory method Congress set for pension plans. But if you are told “treasury bonds” and the actual rates are higher, you will build a mental model that gives you the wrong number.

-----

## How it actually works

The lump sum is the present value of your lifetime monthly annuity. To compute it, you need three things:

1. **Your monthly annuity** – benefit_rate × high-5 salary × years_of_service / 12
1. **Survival probabilities** – from the IRS §417(e) unisex mortality table (updated annually)
1. **Discount rates** – the three §417(e) segment rates

For each future payment month, the calculation asks: what is the probability you will be alive to receive this payment, and what is that payment worth in today’s dollars? Then it sums all 780 payments (65 years of monthly payments).

The three segment rates correspond to payment timing:

|Payments      |Years out |Rate used|
|--------------|----------|---------|
|Months 1-60   |0-5 years |Segment 1|
|Months 61-240 |5-20 years|Segment 2|
|Months 241-780|20+ years |Segment 3|

NTCA applies August segment rates with a one-year look-back, meaning the rates used for a 2026 plan year calculation were set in August of the prior year and held stable throughout the plan year. This is allowed under IRS rules – plans can use a stability period of up to 12 months.

-----

## How I figured it out

I had two official NTCA Pension Point outputs – lump sum estimates for two different retirement dates. The calculator produced both; I could see the results but not the formula.

I built a Python model from the IRS §417(e) spec: load the correct mortality table for the plan year, apply the three-segment discount structure, compute conditional survival probabilities from the retirement age forward, sum the present value of every payment.

My first model was off by about 1.7% consistently. The same error across both data points told me it was not a calculation logic problem – it was a parameter problem. The segment rates I was using did not match what NTCA actually used.

So I ran a grid search: try every plausible combination of segment rates in 0.01% increments, find the set that minimizes error across both official outputs simultaneously.

The rates that converged: **4.10% / 5.20% / 5.80%**.

With those rates, the model matched two official NTCA Pension Point outputs for two different retirement dates:

| | Delta |
|---|---|
| Retirement date 1 | +$33 |
| Retirement date 2 | −$31 |

**$33 on a seven-figure lump sum. That is 0.003% error.**

Residual annuity matches to within $0.02 per month.

**Why the model will never match NTCA exactly – and why that is fine.**

The errors run in opposite directions — high on one date, low on the other. Average error across both data points: $1.09. A systematic mistake would produce errors in the same direction. Bidirectional errors at this scale mean the methodology is correct and what remains is input precision.

NTCA carries their salary and service year figures to more decimal places internally than they display on the output PDF. I back-calculated the salary from the rounded monthly annuity, and read the service years from a rounded display. Those rounding differences cascade through 780 monthly payment calculations and produce a roughly $32 terminal difference — a difference that partially cancels across dates rather than compounding.

To close the last $32 you would need NTCA’s internal unrounded inputs. That data is not on the PDF. At 0.003%, the model is at the noise floor of what is observable from the outside.

-----

## The buyback years – and why they change everything

Many NTCA participants have prior industry experience that their co-op bought back when they joined the plan. Those bought-back years are credited toward your total NTCA service, and they show up in your official benefit calculation without any separate line item explaining them.

Here is how to prove whether you have them and how many.

My NTCA Pension Point output credited me with more years of service than my actual tenure at my co-op. The gap is industry experience I had before joining the plan that NTCA credited at enrollment. Using the calculator with your co-op start date, the math is straightforward:

| | Years |
|---|---|
| Actual co-op service | X.XX |
| NTCA-credited service | Y.YY |
| Bought-back years | **difference** |

In my case the gap was approximately 4 years — prior industry experience that NTCA credited when I enrolled in the plan.

**Why it matters – the Rule of 85:**

The NTCA plan allows early retirement without penalty when your age plus years of service equals 85 or more. The buyback years are included in that calculation.

| Scenario | Age | Service | Rule of 85 |
|---|---|---|---|
| With buyback | 55 | 30+ | ✓ qualifies |
| Without buyback | 55 | 26 | ✗ does not qualify — need ~4 more years |

Without those bought-back years I would not qualify for the Rule of 85 at 55. That is four additional years of work. The dollar impact of that delay compounds significantly.

The calculator can prove this for your own situation. Pass your co-op start date and it shows the breakdown.

-----

## What surprised me most

Two findings I did not expect going in.

**1. Your employer’s benefit rate may not be 1.9%.**

The NTCA plan is a multi-employer plan where each member co-op elects a benefit accrual rate in their Adoption Agreement. Common values are 1.9%, 1.7%, and 1.5%. Some employers elect lower rates.

For the same person – same salary, same service years, same retirement date – the difference between a 1.5% rate and a 1.9% rate is roughly **$138,000 in lump sum value**.

Most participants do not know their employer’s elected rate. It is in your Summary Plan Description. If you do not have that document, ask HR directly – it is a required disclosure.

**2. The partial lump sum is not a percentage of your actuarial lump sum.**

I assumed a partial lump sum election meant taking a percentage of the present value and receiving the rest as annuity. That is not how NTCA structures it.

NTCA’s partial lump sum is your employee contribution balance – the money you put in over your career, with interest. It is a fixed dollar amount, not a percentage. This changes how you model the trade-off between lump sum and annuity income. I am still working through the full implications of this and will document it further as the model matures.

To be clear, the partial lump sum is not something I have dug deeply into at this time. This may be a future refinement.

-----

## One more thing: the buy-out trigger

For participants retiring on or after February 1, 2030, there is a specific plan provision that credits one additional year of service for purposes of the lump sum calculation. This is not a calendar-year-crossing rule – it is a plan-specific provision with a fixed effective date.

The difference between a June 2029 retirement and a February 2030 retirement in my data is not just 8 months of additional accrual. The buy-out applies to the February 2030 date and not the June 2029 date. That is part of why the February 2030 number is significantly higher.

If you are within a year or two of that date, it is worth running both sides.

-----

## Can you legally do this?

Yes. And it is worth being clear about why.

**§417(e) is public law.** The methodology I implemented is written into the IRS code. Congress set this valuation method for defined benefit plans – it is not proprietary to NTCA. Anyone can read the statute, implement the formula, and run it against their own benefit data.

**The source data is government publications.** The IRS publishes the §417(e) mortality tables annually as official IRS Notices. The Treasury publishes the HQM corporate bond yield curve data publicly. Both downloaded from official government sources.

**I did not touch NTCA’s software.** I looked at outputs, compared them to what the IRS specification would produce, and adjusted until they matched. That is analysis from public data.

**ERISA gives you the right to understand your own benefit.** Federal law requires your plan to disclose the Summary Plan Description and, on request, the plan document. Building a tool to model that methodology for your own planning is well within that right.

This project exists because a plan participant could not get a straight answer about their own retirement. That is the only reason it was built.

-----

## What is available now

Two tools are on GitHub at [harvey267/ntca-calculator](https://github.com/harvey267/ntca-calculator).

**CLI calculator** – runs a single lump sum estimate from the command line. Takes your birth date, retirement date, high-5 salary, years of service, and employer benefit rate. Outputs the full annuity stream breakdown and a summary.

**Streamlit dashboard** – interactive version. Adjust inputs with sliders, see a retirement window curve showing how the lump sum changes month by month, run segment rate sensitivity analysis, and optionally add Social Security projections from an earnings CSV.

The inputs you need before running:

|Input                |Where to find it                                                                               |
|---------------------|-----------------------------------------------------------------------------------------------|
|High-5 salary        |Average of your 5 highest compensation years in the last 10 plan years – NTCA can give you this|
|Years of service     |Your total plan participation years, including fractions                                       |
|Employer benefit rate|Your Summary Plan Description or Adoption Agreement – ask HR                                   |
|Segment rates        |Built-in defaults are verified against 2026 plan year outputs                                  |

-----

*This is an educational tool. All calculations are estimates based on publicly available IRS rules and reverse-engineered NTCA methodology. Verify with NTCA directly for official benefit amounts.*

*Source code: github.com/harvey267/ntca-calculator*