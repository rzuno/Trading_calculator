# AI Seesaw Trading Manual v1.4

**Version:** 1.4  
**Status:** Unified Sell / Trend-Adaptive Load  
**Date:** January 2026  
**Philosophy:** Pure Mean Reversion. Clean Exits.

---

## 1. Army Structure

- **Portfolio:** Fixed watchlist (AI core).
- **Total Units (N):** Integer (e.g., 20, 25, 30).
- **Unit Size:** `Total Capital / N`.
- **State Variables (Per Stock):**
  - `units` (int): Current units held.
  - `avg_cost` (float): Average cost of current position.
  - `V` (float): Volatility score [0.0, 2.0] (Set manually/periodically).
  - `T` (float): Trend score [0.0, 5.0] (Derived from G/L Committee).

---

## 2. Buying Mechanics

**Logic Gate:**
- If `units == 0` → Evaluate **LOAD** (2.1).
- If `units > 0` → Evaluate **RESCUE** (2.2).

### 2.1 LOAD (Ignition)
*Only allowed when the position is empty.*

**Concept:** The entry dip must adapt to the Trend. A strong trend demands an easier entry (shallow dip), while a weak trend requires patience (deep dip).

- **Drop Formula:**
  \[ \text{drop\_load}\% = 6.0 - (0.6 \times T) + (0.5 \times V) \]
  *(Clamped Min 3.0%, Max 8.0%)*

- **Trigger:**
  \[ \text{LowToday} \le \text{High5} \times (1 - \text{drop\_load}/100) \]

- **Action:** Buy **1 Unit**.

### 2.2 RESCUE (Defense)
*Only allowed when holding units and price is below average cost.*

**Gearbox Definition:**
Define unit thresholds based on total `N`:
- `u1 = ceil(0.10 * N)`
- `u2 = ceil(0.25 * N)`

| Gear Phase | Condition (Units Held) | Drop Trigger (from Avg) | Buy Size ($r$) |
|:---|:---|:---|:---|
| **1st (Ignition)** | `1` to `u1` | **-4%** | **0.5x** |
| **2nd (Cruise)** | `u1+1` to `u2` | **-5%** | **0.6x** |
| **3rd (Brake)** | `> u2` | **-6%** | **0.7x** |

- **Trigger:**
  \[ \text{LowToday} \le \text{avg\_cost} \times (1 - \text{Drop Trigger}) \]
- **Action Size:**
  \[ \text{buy\_qty} = \text{round}(\text{units} \times r) \]
  *(Clamp: Min 1 unit, Max up to N)*

---

## 3. Selling Mechanics (Unified 2-Tier)

We use a unified **50/50** exit strategy to prioritize liquidity and campaign turnover over theoretical maximum profit.

### 3.1 Gear & Step Calculation
1.  **Trend ($T$):** `(3*L + 2*G) / 5`
2.  **Penalty ($P$):** If global deployment `f > 0.4`, apply `P = -3 * (f - 0.4) / 0.6`.
3.  **Gear ($g$):** `clamp(T + P, 0, 5)`
4.  **Step ($s$):** `1% + g%` (Range: 1%–6%)

### 3.2 Structure & Targets
Use `entry_avg` (Average Cost at the moment the ladder is set).

- **Structure:** Always **2-Tier**.
- **Tier 1:** Sell **50%** (of total) @ `entry_avg * (1 + s)`
- **Tier 2:** Sell **100%** (of remaining) @ `entry_avg * (1 + 2s)`

*Note: This ensures the position is fully cleared at +2s, allowing an immediate "Load" reset.*

---

## 4. Logistics (FX)
- **Reference Rate ($R_{ref}$):** Average FX rate of current USD holdings.
- **Traffic Light:**
  - **Green (Reinforce):** If FX < $R_{ref}$ - 2% → Buy USD.
  - **Green (Repatriate):** If FX > $R_{ref}$ + 2% → Sell USD.
  - **Yellow:** Hold position in native currency.