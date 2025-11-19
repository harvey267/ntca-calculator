🧮 Pension Modeling for Clarity: A Network Engineer’s Side Project
As a network integration engineer, I spend most of my time designing systems, troubleshooting infrastructure, and making sure things work reliably. But as I started thinking seriously about retirement — now just 3.5 years away — I realized I didn’t fully understand how my pension lump sum was calculated.
There were a lot of assumptions floating around: some said it was based on federal interest rates, others pointed to GATT-era logic. None of it added up.
So I did what I’d do with any system I don’t trust: I built my own.

🔍 What I Found
I cross-referenced Summary Plan Descriptions and internal documentation, then mapped those against IRS guidance — specifically §417(e) and Notice 2024-42. That’s when the real structure emerged:
• 	Lump sums are discounted using IRS segment rates tied to corporate bond yields
• 	Mortality assumptions follow the IRS unisex table (RP-2014 base with MP-2021 projection)
• 	Timing matters — down to the day payments begin
• 	Salary growth and service buy-outs shift the entire stream
When I shared what I found, I got skepticism. So I decided to test it.

🧰 What I Built
I built a pension simulator from scratch using Python and Streamlit — not as a financial expert, but as a systems guy who wanted clarity. The model:
• 	Matches annuity values with <0.01% error
• 	Achieves lump sum accuracy within <0.5% drift across a 24-month simulation window
• 	Applies day-level discount offsets
• 	Simulates retirement timing and rate sensitivity
• 	Aligns with IRS methodology and actuarial standards

⚙️ Parameters I Added (Not Available in the Official Calculator)
To make the model truly teachable and exploratory, I added the ability to adjust parameters that aren’t exposed in the official calculator:
• 	Salary Growth Rate: Simulates future earnings trajectory
• 	Buy-Out Service Credit Logic: Models how service years are adjusted for lump sum eligibility
• 	Mortality Table Selection: Allows switching between IRS tables for audit and sensitivity
• 	Segment Rate Overrides: Lets users test alternate IRS rate scenarios
• 	Partial Lump Sum Slider: Models hybrid payout strategies
• 	Exact Retirement Date: Applies day-level discount offset for timing precision
These additions make the simulator a powerful tool for planning, auditing, and understanding how each variable affects the outcome.

🔮 My Next Goal: Forecasting Segment Rates
My next goal is to see if I can predict — with some level of confidence — what the next year’s IRS segment rates might be before they’re published.
To explore this, I:
• 	Analyzed historical trends and rate behavior across Segment 1, 2, and 3
• 	Built sensitivity tables to test how rate shifts impact lump sum values
• 	Created toggles to simulate future scenarios and stress-test assumptions
This helps me plan ahead and understand how rate volatility could affect retirement timing — not just for myself, but for anyone trying to make informed decisions.

📐 Core Math
Monthly Annuity
\text{Monthly Annuity} = \text{Final Avg Salary} \times \text{Service Years} \times \text{Plan Multiplier}
Discount Offset
\text{Offset} = \frac{(\text{Month} - 1) + (\text{Day} - 1)/30}{12}
Present Value of Annuity Stream
\text{PV}_t = \text{Annual Payment} \times \text{Survival}_t \times \frac{1}{(1 + r_t)^{t - \text{Offset}}}

🎯 Why I Did This
This wasn’t about building a product — it was about understanding a system that affects my future. I wanted to know how it works, test my assumptions, and build something I could trust.

#### Suggested CTAs (Pick one):

- **For Engagement:** "What's a complex 'black box' system (financial or otherwise) that you've always wanted to reverse-engineer?"
    
- **For Sharing Knowledge:** "Have other engineers/pre-retirees found themselves digging into these same IRS tables? I’d be curious to compare notes on your findings."
    
- **For Connection:** "This was a fascinating dive into the intersection of systems logic and actuarial science. Always happy to connect with other folks who love to build models to find clarity."