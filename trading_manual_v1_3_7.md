# AI Seesaw Trading Manual v1.3.7 (Codify-ready)

**Version:** 1.3.7  
**Purpose:** Remove ambiguity/loopholes for automation while keeping the v1.3 philosophy.

---

## 0. Philosophy & Worldview
- This system is a **repeatable campaign machine**: enter → manage risk → exit → reset.
- The goal is **clean state transitions** (no zombie remnants, no ambiguous triggers).

---

## 1. Army Structure
- **Portfolio:** Fixed watchlist (AI core).
- **Total Units (N):** integer (e.g., 20 / 25 / 30).
- **Unit Cash Size:** `unit_cash = Total Capital / N`.

### 1.1 Important distinction: Units vs Shares (critical)
- **`units` (float):** *army units deployed* for this stock, measured in multiples of `unit_cash`.  
  - Example: `units = 3.7` means you deployed about `3.7 × unit_cash` money.
- **`shares` (int):** number of shares held (must be integer in your trading model).
- **`avg_cost` (float):** average cost **per share** = `cost_basis_cash / shares`.

### 1.2 Per-stock State Variables (must be tracked)
- `units` (float): current deployed army units (0.0 .. N).
- `shares` (int): current shares held.
- `cost_basis_cash` (float): total cash spent for the current position.
- `avg_cost` (float): `cost_basis_cash / shares` (if shares>0 else NaN).

---

## 2. Buying Mechanics (Load + Rescue)

### 2.1 Price references (High/Low-based)
- `High5` = **highest High** of the **previous 5 completed trading days** (exclude today).
- `HighToday`, `LowToday` = today’s intraday High/Low (or the best available approximation on your platform).
- `Px` = the current tradable price at decision time (real-time price).

### 2.2 Volatility score `V` (float 0.0 .. 2.0)
`V` is a **floating-point volatility score** you set (typically to one decimal place) based on your AI “committee meeting” / chart reading.

- `V = 0.0` : very calm
- `V = 2.0` : very volatile
- Examples: `V = 0.5`, `V = 1.2`, `V = 1.9`

**Rule of use (for consistency):**
- Keep `V` fixed for that stock for the current “battle” unless you intentionally revise it.
- Round to **one decimal** for stability (e.g., 1.86 → 1.9).

### 2.2.1 Trend score `T` (0.0 .. 5.0)
`T` measures trend strength (higher = stronger / more bullish in your default convention).  
You can set `T` via your AI committee evaluation mapped into 0.0–5.0.

### 2.3 LOAD (Entry / ignition)
LOAD is the **only** peak-based entry. It is allowed **only when you hold zero units**.

- **State:** `units == 0`
- **Load drop threshold:**  
  - `drop_load(%) = clamp(3.0, 6.0 - 0.6*T + 0.5*V, 7.0)`
  - Here `T` is in 0.0–5.0 and `V` is in 0.0–2.0 (float).
  - Examples: `T=5.0, V=0.0 → 3.0%`; `T=3.0, V=1.0 → 4.7%`; `T=0.0, V=2.0 → 7.0%`

> Note: this formula assumes higher `T` means stronger (more bullish) trend. If your scoring is reversed, replace `T` by `(5 - T)`.

- **Trigger (High/Low-based):**  
  - `LowToday <= High5 * (1 - drop_load/100)`

- **Action (units → shares):** deploy `buy_units_target = 1.0` unit, convert to integer shares at `Px_exec` using the same rounding rule as RESCUE.

> Philosophy: once LOAD starts a battle, you continue fighting via RESCUE until the sell ladder clears the position.

### 2.4 RESCUE (Defense / averaging-down) — Smooth gearbox
RESCUE is the main buying mechanism. It is allowed whenever you already hold units and price falls below your averaged cost by the current rescue gear.

#### 2.4.1 Smooth rescue gear (continuous)
Instead of discrete 3 gears, RESCUE uses a smooth ramp that depends on your current deployed `units`.

**Parameters (defaults):**
- `U_sat = 10.0`  (saturation unit; after this, the gear stays at max)
- `drop_min = 4.0`, `drop_span = 2.0`  → drop ranges **4.0% .. 6.0%**
- `r_min = 0.5`, `r_span = 0.2`        → r ranges **0.5 .. 0.7**

**Ramp (calibrated):**
- `t = clamp(0.0, (units - 1.0) / (U_sat - 1.0), 1.0)`  
  - Interpretation: `t=0` at `units=1` (first transmission), and `t=1` once `units >= U_sat`.

**Resulting gear:**
- `drop_rescue(%) = drop_min + drop_span * t`
- `r = r_min + r_span * t`

#### 2.4.2 RESCUE trigger (High/Low-based)
- Trigger: `LowToday <= avg_cost * (1 - drop_rescue/100)`

#### 2.4.3 RESCUE action size (units → shares)
- Compute target deployment in **army units**:
  - `buy_units_target = units * r`  *(float; this is money sizing, not shares)*
  - `buy_units_target = min(buy_units_target, N - units)`

- Convert target units to **integer shares** at execution price `Px_exec` (usually the trigger price):
  - `target_cash = buy_units_target * unit_cash`
  - `buy_shares = max(1, round_half_up(target_cash / Px_exec))`

- Because shares must be integer, the **actual** deployed units may differ slightly:
  - `actual_cash = buy_shares * Px_exec`
  - `buy_units_actual = actual_cash / unit_cash`

- Update state:
  - `shares += buy_shares`
  - `cost_basis_cash += actual_cash`
  - `units += buy_units_actual`
  - `avg_cost = cost_basis_cash / shares`

#### 2.4.4 Deterministic buy order (no double-buy)
- If `units == 0`: evaluate **LOAD** only.
- If `units > 0`: evaluate **RESCUE** only.

---

## 3. Selling Mechanics (Unified 2-tier)

Selling is always executed as a **2-tier ladder** for simplicity and full clearance.

### 3.1 Sell gear `s` (in %)
Keep your existing method to compute `s` (trend/volatility-based). The manual does not change how `s` is produced — only how it is executed.

### 3.2 2-tier ladder (always)
All tier prices are computed from `avg_cost` (per share).  
Let `Q` be the position size (**shares**) at the moment you place the ladder.

- **Tier 1:** take-profit at `+s%`  
  - sell `q1 = round_half_up(0.50 * Q)` shares
- **Tier 2:** take-profit at `+(2*s)%`  
  - sell `q2 = Q - q1` shares (the remainder)

Weighted-average profit target (if both tiers fill) is `0.5*s + 0.5*(2*s) = 1.5*s`.

### 3.3 Rounding rule (codify-ready)
Use `round_half_up(x)` for integer (share) rounding:
- `round_half_up(1.5) = 2`, `round_half_up(2.5) = 3`
This avoids “always-round-down” bias when Q is small.

### 3.4 Re-laddering
If you add units via RESCUE, you may re-compute `avg_cost` and re-place the 2-tier ladder using the updated `Q` and `avg_cost`.  
(Do not stack multiple active ladders for the same stock — keep one active ladder per stock.)

---

## 4. Notes for Automation

### 4.1 Rounding rule (important)
Use **round-half-up** (not banker's rounding) to keep behavior stable across platforms.

### 4.2 One action per cycle
For automation safety: **at most one buy action per stock per evaluation cycle**.

---

## 5. Version delta from v1.3.6
- Replaced RESCUE discrete 3-gear transmission with a **smooth gearbox**:
  - Calibrated ramp `t = clamp(0, (units-1)/(U_sat-1), 1)`
  - Defaults: `drop_rescue` in **4%..6%**, `r` in **0.5..0.7**, `U_sat=10`
- Clarified percentage usage in BUY triggers by explicitly using `/100`.
