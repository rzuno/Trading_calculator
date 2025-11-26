# AI Seesaw Trading Manual v1.0

Author: Juno  
Scope: AI-sector stocks (US: NVIDIA, Alphabet; KR: Samsung Electronics, SK hynix)  
Style: **Rule-based, algorithmic trading metaphor = war/armies**

---

## 0. Philosophy & Worldview

- We treat trading as **warfare**, not gambling.
- Capital = **army** divided into small **units** (20–25 recommended per stock).
- We only fight battles that are **winnable** (clear trend, volatility, liquidity).
- When there is no good fight, money rests in **CMA / cash** (training camp).
- We accept that we cannot catch all opportunities; we choose one **complementary** strategy and live with its trade-offs.

Macro worldview:

- Long-term AI trend is **bullish** (tide up).
- Short- to mid-term (weeks–months) has **non-linear waves**:
  - Tides (multi-year)
  - Swells (months)
  - Waves (days–weeks)
  - Rollers (intraday)
- Strategy targets mainly **waves** (weekly/monthly up-and-down) while respecting the big tide.
- We operate within a small battlefield:  
  - **US:** NVIDIA, Alphabet (GOOGL/GOOG)  
  - **KR:** Samsung Electronics, SK hynix  
- For US, FX is a major factor. Frequent short-term trading is less attractive unless FX is favorable.

---

## 1. Army Structure

- For each stock, total capital allocated = **N units** (e.g. 20 or 25 units).
- Units are conceptual; actual order size is `total_capital / N`.
- All operations (buy, sell) are defined in **percentages**, not raw KRW or unit count.

Key variable:

- **U = deployed_ratio = (units currently in the stock) / (max units for that stock)**  
  - 0 ≤ U ≤ 1  
  - U drives **sell behavior** (gears) automatically.

---

## 2. Buy Models (Intro Gears)

We use **average-based triggers** with compounding size.

### 2.1 General buy rule

Let:

- `gear_drop` = X% (e.g. 5, 6, 7)
- `r` = fraction of current total units to buy on each additional layer

Then:

1. First buy:
   - Buy `1 unit` at current price `P0`.
   - Initial average cost `A0 = P0`.

2. For each next layer:
   - When market price drops to  
     `Next buy price = current_avg * (1 - gear_drop / 100)`,
     we place a new buy.
   - Buy size = `r × current_total_units`.
   - Recalculate new average cost after buy.
   - **New average = (old_avg × old_units + buy_price × new_units) / (old_units + new_units)**
   - Repeat as long as we want to keep layering.

Effect:

- The **gap between average cost and next buy price** is essentially stable in **percentage**, so we are **tracking the price with a fixed proportional distance** (e.g. ~3–4% above the trigger).
- Higher `gear_drop` = fewer but deeper buys.  
- Higher `r` = faster growth of position size.

---

### 2.2 Named buy models

We have four canonical buy models:

| Name        | gear_drop (X%) | r     | Character / Usage |
|-------------|----------------|-------|-------------------|
| **Agile**   | –5%            | 0.6   | **Main default.** Close tracking, many small entries, good for frequent scalping around trend. |
| **Heavy**   | –6%            | 0.7   | Strong averaging, deeper rescue, for volatile and explosive stocks or stronger conviction. |
| **Greedy**  | –5%            | 0.7   | Very aggressive; strong rescue but can overcommit in deep dips. Use only when expecting sharp rebounds. |
| **Cautious**| –7%            | 0.65 | Deep but light layering; fewer buys, smaller total position even at –15%. For scary markets but still wanting to enter. |

**Campaign rule:**  
For each “campaign” (stock + time window, e.g. 4–6 weeks):

- Choose exactly **one buy model**.
- Stick to it until you explicitly **reset** the campaign.

Practical advice:

- With 20–25 units total:
  - **Agile (–5%, 0.6)** is the **primary working model**.
  - **Heavy (–6%, 0.7)** is your **strong defense / high-volatility** model.
  - Greedy and Cautious are **special modes**, not daily defaults.

---

## 3. Sell Mechanics (Outro Gears)

We want sell logic to be:

- **Automatic**, not hunch-based.
- Responsive to how much army is already committed.

We do this by:

1. Using **deployment ratio U** to pick a **sell gear**.
2. Using **3-tier profit targets** for each gear.
3. Always selling in the same pattern:  
   - 50% at first target  
   - 25% at second target  
   - 25% at final target

### 3.1 General sell rule

Let:

- `A` = current average cost after latest buy.
- Sell gear = (s%, 2s%, 3s%), where `s` depends on U.

Then:

- **Tier 1**: when price reaches `A × (1 + s/100)` → sell **50%** of current position.
- **Tier 2**: when price reaches `A × (1 + 2s/100)` → sell **50% of remaining** (i.e. 25% of original).
- **Tier 3**: when price reaches `A × (1 + 3s/100)` → sell all remaining (last 25%).

We always think in **percentage of current position**, so it works even after partial exits and new buys.

---

### 3.2 Sell gears by deployment stage (U-based)

Let:

- `U = deployed_units / max_units_for_this_stock`

We map U to sell gears as:

| Stage | U (Deployed ratio) | Sell Gear (s, 2s, 3s) | Action Pattern |
|-------|---------------------|------------------------|----------------|
| **0 – Emergency** | any U, but macro shock (war, crash, sudden policy) | **1% / 2% / 3%** | Panic-light exit: 50% at +1%, 25% at +2%, 25% at +3%. |
| **1 – Very Light** | 0–20% | **6% / 12% / 18%** | High reward, low risk (only scouts in). |
| **2 – Light** | 20–40% | **5% / 10% / 15%** | Still optimistic; let the position breathe. |
| **3 – Medium** | 40–60% | **4% / 8% / 12%** | Balanced: normal profit targets. |
| **4 – Heavy** | 60–80% | **3% / 6% / 9%** | Priority shifts to liquidity and safety. |
| **5 – Very Heavy** | 80–100% | **2% / 4% / 6%** | Almost all army deployed; escape quickly with small profits. |

Interpretation:

- When **few units are committed**, we allow **higher profit targets**.
- When **most units are stuck**, we prioritize **getting out** and freeing capital, not squeezing every last percent.

Note: Emergency gear (1/2/3) is a **manual override** used only when macro conditions break our assumptions.

---

## 4. Putting It All Together: Campaign Flow

### 4.1 Defining a campaign

For a given stock (e.g. Samsung Electronics):

1. Decide **time window** (e.g. 4–6 weeks).
2. Choose **buy model**: Agile / Heavy / Greedy / Cautious.
3. Set **max units** for this campaign: e.g. 20 or 25.
4. Optionally, write down:
   - Macro stance (bullish / neutral / defensive).
   - Key macro dates (e.g. FOMC, earnings, big AI events).

### 4.2 During the campaign

**Buys**:

- First buy: 1 unit at current price.
- Then:
  - Wait until price hits `A × (1 - gear_drop/100)`.
  - Buy `r × current_units`.
  - Recalculate average `A`.
  - Repeat as long as:
    - You’re within max units, and
    - Macro stance has not fundamentally changed.

**Sells**:

- After each buy, compute `U = deployed_units / max_units`.
- From the table in §3.2, pick sell gear (s, 2s, 3s) based on U.
- Set three profit targets from the current average:
  - Tier 1: `A × (1 + s/100)` → sell 50%.
  - Tier 2: `A × (1 + 2s/100)` → sell 25%.
  - Tier 3: `A × (1 + 3s/100)` → sell 25%.
- If a macro shock occurs (war, massive crash, policy surprise):
  - Override to **Emergency sell gear**: 1/2/3.

After full exit:

- You may:
  - End the campaign and move battlefield (other stock), or
  - Restart a fresh campaign with new averages and possibly a different buy model (if macro/trend changed).

---

## 5. Practical Notes & Psychology

- **Sleeping money is not evil.**  
  Money in CMA is not “wasted”; it is your rested army, ready for **high-probability battles**.
- **We do not have to fight every day.**  
  In frozen or directionless markets, you shrink campaigns and stay mostly in cash.
- **US vs KR difference:**  
  - KR: better for more active trading (no FX noise, smaller taxes).  
  - US: more long-term, FX-aware, with fewer but larger campaigns.
- **Your edge is discipline, not prediction.**  
  Strategy assumes:
  - We **can’t** predict exact turning points.
  - But we **can** control entry spacing, size growth, and exit targets.

---

## 6. Versioning

**Version:** 1.0  
**Status:** Stable conceptual manual (buy + sell fully specified).  
**Next steps (future versions):**

- v1.1:  
  - Implement Python helper that, given `(gear_drop, r, avg_price, current_units, max_units, current_price)`, outputs:
    - Next buy trigger
    - New average if triggered
    - Deployed ratio U
    - Current sell gear and target prices
- v2.0:  
  - Connect this logic to an API for semi-automatic alerts or full algorithmic trading (paper trading first).

This document is the canonical reference for your AI seesaw trading system v1.0.  
All future discussions and tweaks should **start from here** and then adjust version numbers.
