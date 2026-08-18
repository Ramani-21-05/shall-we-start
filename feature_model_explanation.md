# Why These Features? How Does the Model Use Them?
## Complete Interview-Ready Explanation

---

## The Core Problem First

We have **daily sales data** per drug from 2014 to 2019.  
The task: **Given today's date and past sales, predict tomorrow's demand.**

The model sees only **numbers** — it cannot read a calendar or understand "winter".  
So we must **translate real-world business signals into numbers** the model can learn from.  
That is what feature engineering is.

---

## The 5 Feature Groups — Why Each One Exists

---

### Feature Group 1: Lag Features
**Code**: `df['lag_1'], df['lag_7'], df['lag_14'], df['lag_28'], ...`

```
lag_1   = sales from yesterday (t-1)
lag_7   = sales from 7 days ago (t-7)
lag_14  = sales from 14 days ago (t-14)
lag_28  = sales from 28 days ago (t-28)
lag_365 = sales from same day last year (t-365)
```

#### Why Did We Select Lag Features?

**The business reason:**  
Pharmacy demand has memory. If a drug sold a lot yesterday, it will likely sell a lot today too (same patient cohort, same season, same prescribing behaviour).

**The statistical reason:**  
ACF (Autocorrelation Function) analysis on every drug showed **statistically significant autocorrelation at lags 1, 7, and 14**. This is mathematical proof that past sales predict future sales.

**Specific lag choices:**
| Lag | Business Meaning |
|:---:|:---|
| `lag_1` | Yesterday's demand — the single strongest predictor |
| `lag_7` | Same weekday last week — captures weekly pharmacy patterns |
| `lag_14` | Two weeks ago — captures fortnightly prescription refill cycles |
| `lag_28` | Monthly cycle — patients on monthly prescriptions |
| `lag_365` | Same day last year — captures year-over-year seasonality anchor |

> [!IMPORTANT]
> **Critical Safety Rule — `.shift(1)`**  
> Every lag feature is shifted by 1 day: `lag_1 = sales.shift(1)`.  
> This means: when forecasting for **Tuesday**, `lag_1` = Monday's sales.  
> We **never** include today's sales as a feature — that would be data leakage (cheating).

---

### Feature Group 2: Rolling Window Statistics
**Code**: `df['rolling_mean_7'], df['rolling_std_7'], df['rolling_mean_28']`

```
rolling_mean_7  = average of last 7 days of sales
rolling_std_7   = standard deviation of last 7 days (volatility)
rolling_mean_14 = average of last 14 days
rolling_mean_28 = average of last 28 days  ← TOP SHAP DRIVER for most drugs
rolling_max_7   = peak sales in last 7 days
rolling_min_7   = lowest sales in last 7 days
```

#### Why Did We Select Rolling Features?

**The business reason:**  
A single lag value is noisy (one outlier day distorts it). A rolling average is a **smoothed trend signal** that tells the model: *"What is the recent demand level for this drug?"*

**Why 7, 14, and 28 days?**
- **7-day window** = one full week cycle (accounts for weekday/weekend mix)
- **14-day window** = two weeks (covers fortnightly prescription cycles)
- **28-day window** = one month (covers monthly repeat buyers and promotion cycles)

**Why rolling_mean_28 is the #1 SHAP driver for most drugs:**  
The 28-day average captures the **stable medium-term demand level**. Daily noise cancels out over 28 days. So the model finds: *"If rolling_mean_28 is high → this drug is in a high-demand period → forecast higher."*

**The rolling_std (volatility) feature:**  
High standard deviation means demand is erratic this week.  
The model learns: *"When cv_7 (coefficient of variation) is high → widen uncertainty → don't be overconfident."*

---

### Feature Group 3: Exponentially Weighted Moving Average (EWMA)
**Code**: `df['ewm_mean_7'], df['ewm_mean_28']`

```
ewm_mean_7  = exponential weighted average, more weight on recent 7 days
ewm_mean_28 = exponential weighted average, more weight on recent 28 days
```

#### Why EWMA in addition to Rolling Mean?

**Rolling mean treats all past days equally.**  
EWMA gives **exponentially higher weight** to recent days.

```
Rolling Mean:  [1, 1, 1, 1, 1, 1, 1]  ← every day same weight
EWMA:          [0.46, 0.23, 0.12, 0.06, 0.03, 0.02, 0.01]  ← yesterday matters most
```

**Business reason:**  
A sudden demand shift 2 days ago (e.g., flu outbreak, news about a drug shortage) should dominate the forecast more than what happened 3 weeks ago. EWMA captures this **recency bias** naturally.

---

### Feature Group 4: Calendar & Cyclical Time Features
**Code**: `sin_dayofyear, cos_dayofyear, sin_dayofweek, cos_dayofweek`

```
sin_dayofyear = sin(2π × day_of_year / 365.25)
cos_dayofyear = cos(2π × day_of_year / 365.25)
sin_dayofweek = sin(2π × day_of_week / 7)
cos_dayofweek = cos(2π × day_of_week / 7)
```

#### Why Not Just Use `month=1,2,...12` or `dayofweek=0,1,...6`?

**The problem with raw integers:**  
If you pass `month=12` and `month=1` as raw numbers, the model sees them as:  
`|12 - 1| = 11` → very far apart.  
But **December and January are adjacent months** (both winter)!

**The solution — Fourier / Cyclical Encoding:**  
By mapping to a circle using `sin` and `cos`, we preserve the cyclic relationship:

```
January  1:  sin = +0.015,  cos = +1.000   ← top of the year circle
April   90:  sin = +0.999,  cos = +0.013   ← right of the circle
July   180:  sin = +0.008,  cos = −1.000   ← bottom
December 365: sin = −0.017, cos = +0.999   ← back near January ✓
```

December and January now have **nearly identical sin/cos values** → the model correctly learns they are in the same seasonal period.

**Weekly cycle:**  
- Monday (day 0): `sin_dayofweek = 0.00`, `cos_dayofweek = 1.00`
- Sunday (day 6): `sin_dayofweek = −0.78`, `cos_dayofweek = 0.62`
- The model learns: *"Sunday values are close to Saturday → weekend pattern."*

#### Why is Annual Seasonality Important for Drugs?

| Drug | Peak Season | Why |
|:---|:---|:---|
| M01AB (NSAIDs) | Winter | Arthritis flares in cold weather |
| M01AE (Ibuprofen) | Winter | Cold & flu pain relief demand |
| N02BA (Aspirin) | Jan–Feb | Post-holiday cardiovascular prevention |
| N02BE (Paracetamol) | Oct–Feb | Flu season fever management |
| R03 (Inhalers) | Nov–Jan | Cold air triggers asthma attacks |
| R06 (Antihistamines) | Apr–Jul | Spring/summer pollen season |

The `sin_dayofyear` and `cos_dayofyear` features **encode this seasonal position numerically** so the model can learn it.

---

### Feature Group 5: Binary Calendar Flags
**Code**: `is_weekend, is_month_start, is_month_end`

```
is_weekend    = 1 if Saturday or Sunday, else 0
is_month_start= 1 if first day of month
is_month_end  = 1 if last day of month
dayofweek     = raw integer 0–6 (Monday=0, Sunday=6)
month         = raw integer 1–12
```

#### Why These Binary Flags?

**is_weekend:**  
In most countries, pharmacies have **reduced hours or are closed on Sundays**. This creates a sharp, non-linear drop in Sunday sales that cannot be learned from sin/cos alone (those are smooth curves; this is a hard binary switch).

**is_month_start / is_month_end:**  
Many patients collect monthly prescriptions on the 1st of the month. This creates a **sharp spike on day 1** that rolling averages and Fourier features smooth over.

---

## How LightGBM Uses These Features: Step-by-Step

### Step 1 — Feature Matrix Construction
For each day $t$ in the training data, we build a row vector $\mathbf{x}_t$:

```
Date: 2018-01-15 (Monday, mid-January)

x_t = [
  lag_1         = 5.33    ← Sunday's sales
  lag_7         = 4.80    ← Previous Monday's sales
  lag_14        = 4.20    ← Two Mondays ago
  rolling_mean_7 = 4.92   ← Last 7-day average
  rolling_std_7  = 1.23   ← Last 7-day volatility
  rolling_mean_28 = 5.10  ← Last 28-day average
  ewm_mean_7    = 5.20    ← EWMA (recency-weighted 7-day)
  sin_dayofyear = +0.45   ← Mid-January position on year circle
  cos_dayofyear = +0.89   ← Mid-January position on year circle
  sin_dayofweek = +0.00   ← Monday position on week circle
  cos_dayofweek = +1.00   ← Monday position on week circle
  is_weekend    = 0       ← Not a weekend
  month         = 1       ← January
]
```

**Target** (what we want to predict):  
$y_t = \log(1 + \text{sales}_t) = \log(1 + 5.50) = 1.85$

> [!NOTE]
> We predict **log(1 + sales)** not raw sales.  
> This compresses large values (100 packs → 4.6), expands small values (1 pack → 0.69).  
> It prevents large-sales days from dominating the model, making it fair across all demand levels.

---

### Step 2 — Optuna Hyperparameter Selection (50 Bayesian Trials)
Before training, we ran **Optuna Bayesian Optimization** to find the best LightGBM parameters:

```
For each trial (50 total):
  → Propose: num_leaves=63, max_depth=5, learning_rate=0.005, n_estimators=424, ...
  → Train LightGBM on 2014–2017 data
  → Evaluate on 2018 Validation Set (RMSLE)
  → Bayesian optimizer updates its belief of which parameters are best
  → Repeat
Best found: num_leaves=63, max_depth=5, lr=0.00514, n_estimators=424 (RMSLE: 0.48)
```

---

### Step 3 — Decision Tree Splitting (How One Tree Works)

LightGBM builds **424 decision trees** sequentially (gradient boosting).  
Each tree is a binary question cascade. Here is how Tree #1 works conceptually:

```
              [ROOT QUESTION]
         rolling_mean_28 > 4.5?
              /            \
            YES              NO
    (High demand drug)    (Low demand)
           |                   |
    sin_dayofyear > 0.3?   is_weekend == 1?
     (Winter season?)      (Sunday closed?)
       /       \              /       \
     YES        NO          YES        NO
  Predict:   Predict:    Predict:   Predict:
    1.82       1.54        0.10       1.20
  (log-scale) (log-scale) (log-scale) (log-scale)
```

**In plain English for the interviewer:**
> *"The first question the tree asks is: Has this drug been selling above 4.5 packs per day on average over the last month?  
> If YES → it's in a high-demand period → proceed to ask about seasonality.  
> If NO → it's quiet → ask if it's a weekend (pharmacy might be closed).  
> Each question narrows down the regime until we reach a leaf node that gives our log-scale prediction."*

---

### Step 4 — Gradient Boosting: 424 Trees Combined

Gradient Boosting is **iterative error correction**:

```
Tree 1:  Predicts log(sales) = 1.50   (rough first estimate)
         Actual  = 1.85
         Error   = 1.85 - 1.50 = +0.35 (we under-predicted)

Tree 2:  Learns from the residual error of Tree 1
         Focuses on the cases where Tree 1 was wrong
         Adds correction: +0.08

Tree 3:  Learns from residuals of Tree 1+2
         Adds correction: +0.04

...

Tree 424: Final tiny correction: +0.001

TOTAL: 1.50 + 0.08 + 0.04 + ... + 0.001 = 1.83 (log-scale)
```

**The learning rate = 0.00514** shrinks each tree's contribution.  
A small learning rate means: *"Don't trust any single tree too much — take 424 small steps rather than 10 big guesses."*  
This prevents overfitting.

---

### Step 5 — Back-Transform to Real Units

```
ŷ_log   = 1.83                           (model output, log-scale)
ŷ_units = exp(1.83) - 1 = 5.24 packs    (back to real sales units)
```

---

### Step 6 — SHAP Attribution (Why Did We Predict 5.24?)

After prediction, **SHAP** decomposes the output:

```
Base Value (Expected Daily Sales) = 3.32 packs (the average over all training days)

Feature Contributions (SHAP values):
  rolling_mean_28    +0.55 packs  ← Recent demand level is above baseline
  sin_dayofyear      +0.21 packs  ← January is a high-demand month
  lag_7              +0.14 packs  ← Last Monday was also strong
  ewm_mean_7         +0.08 packs  ← Recent EWMA also elevated
  is_weekend         −0.06 packs  ← No effect (it's Monday)
  ─────────────────────────────────
  Final Prediction   = 3.32 + 0.55 + 0.21 + 0.14 + 0.08 − 0.06 = 4.24 ≈ 5.24 packs ✓
```

This is the **mathematical guarantee** of SHAP: every prediction = base value + sum of all feature contributions.

---

## The Complete Picture: One Diagram

```
REAL WORLD EVENT                FEATURE                MODEL INTERPRETATION
────────────────────────────────────────────────────────────────────────────
"It's January (winter)"    →  sin_dayofyear = +0.45  →  "High season, predict more"
"Yesterday sold 5.3 packs" →  lag_1 = 5.33           →  "Recent demand is strong"
"Last month avg = 5.1"     →  rolling_mean_28 = 5.10  →  "Stable high-demand regime"
"It's Monday (not weekend)" →  is_weekend = 0          →  "Pharmacy is open, normal day"
"Demand variance low"      →  rolling_std_7 = 1.23    →  "Predictable week, trust the signal"
                                        │
                                        ▼
                           424 Decision Trees ask
                           binary YES/NO questions
                           about these numbers
                                        │
                                        ▼
                           Sum all 424 tree votes
                           → 1.83 (log-scale)
                                        │
                                        ▼
                           exp(1.83) - 1 = 5.24 packs/day  ← FINAL FORECAST
                                        │
                                        ▼
                           SHAP Attribution: rolling_mean_28 drove most of it (+0.55)
```

---

## Interview One-Line Summary (Memorise This)

> *"We extracted 35 features from daily sales history — recent lags to capture demand memory, rolling averages to capture trend level, EWMA to give recency priority, and Fourier sin/cos calendar terms to encode seasonality cyclically without breaking the month/week boundary. LightGBM then runs 424 gradient-boosted decision trees that each ask binary YES/NO questions about these features to predict log-transformed demand, which is summed and exponentiated to get real daily packs. SHAP then mathematically decomposes each prediction back into feature contributions so we know exactly which signal drove the forecast up or down."*
