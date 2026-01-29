# AI Seesaw Trading Manual (v1.4.3)
**Current spec:** Semi-autonomous trading machine + point-based perk system (v0.2)
**Execution:** Human decides; machine calculates triggers, ladders, and gear recommendations.
**Scope:** AI-sector stocks (KR: Samsung Electronics, SK hynix; US: NVIDIA, Alphabet/Google) + USD/KRW wallet panel.

---

## 0) Philosophy and Scope
- Non-predictive, mechanical responses to price and position state.
- Focus on mean reversion within an overall AI-sector uptrend.
- Capital is an "army" divided into N units; position size is measured in units.
- Human-in-the-loop: recommendations are advisory; execution is manual.

---

## 1) Core Definitions

### 1.1 Units vs Shares (Critical)
- **N (int):** total army units for the whole portfolio (e.g., 20 / 25 / 30).
- **unit_cash (float):** `total_capital / N`
- **units (float):** money deployed into a stock measured in unit_cash.
- **shares (int):** number of shares held (must be integer).
- **cost_basis_cash (float):** total cash spent for current position.
- **avg_cost (float):** `cost_basis_cash / shares` (if shares > 0)

### 1.2 Campaign States
- **IDLE:** `shares == 0` (no position, watch for entry)
- **ACTIVE:** `shares > 0` (position held, buys and sells active)
- **EXIT:** ladder orders working to unwind the position

State transition:
`IDLE -> LOAD -> ACTIVE -> (tier fills) -> IDLE`

### 1.3 Per-stock State Variables (Track These)
Minimum state per stock:
- `units` (float)
- `shares` (int)
- `cost_basis_cash` (float)
- `avg_cost` (float)
- `anchor_high` (float): local peak anchor for LOAD/RELOAD
- `ladder_state` (enum/flags): which sell tiers are filled
- `last_action_date` (date): last buy/sell/reset execution date
- `idle_days` (int): trading days since last action (computed)

### 1.4 Global State Variables (Portfolio)
- `N` (int): total units across the portfolio
- `unit_cash` (float)
- `G` (float): global score (optional)
- `fx_ref_rate` (float): reference FX rate for USD holdings (optional)
- `updated_at` (date)

---

## 2) Price References and Data Inputs
We use daily OHLCV (and intraday high/low if available):
- **High5:** highest High of the previous 5 completed trading days (exclude today)
- **High10:** highest High of the last 10 trading days (includes today's high when available)
- **HighToday / LowToday:** today's intraday high/low (or close in backtests)
- **Px:** current tradable price at decision time
- **FX:** USD/KRW rate (tracked separately in the Dollar panel)

**Anchor High:**
- After any buy event, set `anchor_high = HighToday`.
- Each cycle, update `anchor_high = max(anchor_high, HighToday)`.

---

## 3) Context Inputs (Optional)

### 3.1 Committee Scores (G/L/V)
Human + AI assistant scores that summarize macro and stock context.
- **G (Global):** AI-sector macro score, range 0.0 to 5.0
- **L (Local):** stock-specific score, range 0.0 to 5.0
- **V (Volatility):** stock volatility regime, range 0.0 to 2.0

Typical update cadence:
- **G:** monthly or major macro events
- **L:** weekly or earnings/news events
- **V:** quarterly or volatility regime change

**Usage:** These scores can drive perk activation (market regime, trend, volatility) or
bias base gears when you want a manual override.

### 3.2 FX Traffic Light (Dollar Panel)
FX is tracked as its own USD/KRW wallet panel, separate from stock perks.

Inputs:
- **FX avg cost:** your average KRW per USD basis
- **USD holdings:** total USD in the wallet

Traffic light (current FX vs avg cost):
- **Green**: FX <= -2% (USD cheap)
- **Yellow**: -2% .. +2% (neutral)
- **Red**: +2% .. +5% (USD expensive)
- **Premium**: > +5% (very expensive)

The Dollar panel draws reference tiers at **+3% / +5% / +7%** above your FX avg cost.
FX perks are shown only in this panel and are not applied to stock recommendations.
The Dollar panel is informational only (no buy/sell gears or manual perks).

---

## 4) Gears (5-Gear System + Emergency)

### 4.1 Buy Gear (LOAD/RELOAD only)
- Base buy gear: **3.0 (default)**
- Gear range: **1.0 .. 5.0** (smooth decimal allowed)
- Mapping to pullback threshold (from peak):
  - `drop_load_pct = 2.0 + buy_gear`
  - Examples:
    - buy_gear 1.0 -> -3.0%
    - buy_gear 3.0 -> -5.0%
    - buy_gear 5.0 -> -7.0%

### 4.2 Sell Gear (3-tier ladder)
- Base sell gear: **3.0 (default)**
- Gear range: **1.0 .. 5.0** (smooth decimal allowed)
- Ladder rungs use constant spacing (+2%, +4%):
  - `tier1_pct = 1.0 + sell_gear`
  - `tier2_pct = tier1_pct + 2.0`
  - `tier3_pct = tier1_pct + 4.0`

Discrete 5-gear table:
- Gear 1: 2 / 4 / 6
- Gear 2: 3 / 5 / 7
- Gear 3: 4 / 6 / 8 (default)
- Gear 4: 5 / 7 / 9
- Gear 5: 6 / 8 / 10

### 4.3 Emergency Sell Gear (Gear 0)
Emergency exit ladder:
- Gear 0: 1 / 2 / 3 (same split 50/25/25)
Used only when an evacuation condition is active (manual or auto).

---

## 5) Rounding Rules (Codify-Ready)
Use **round-half-up** for share rounding:
- `round_half_up(1.5)=2`, `round_half_up(2.5)=3`
Avoid bias of always-round-down.

---

## 6) Core Trading Rules (State Machine)

### 6.1 Buy Order of Precedence (No Double-Buy)
Each evaluation cycle, allow **at most one buy action**:
1) If `shares == 0`: evaluate **LOAD** only.
2) If `shares > 0`:
   - Evaluate **RESCUE** first (defense below avg_cost).
   - If RESCUE not triggered, evaluate **RESET** (if armed).
   - If RESET not triggered, evaluate **RELOAD** (offense above avg_cost).
   - If none triggered, no buy.

### 6.2 LOAD (Entry / ignition)
**Permission:** `shares == 0`
**Trigger:**
- `LowToday <= High5 * (1 - drop_load_pct/100)`
**Action:** buy exactly **1.0 unit** worth of shares.

After LOAD:
- set `anchor_high = HighToday`
- place fresh sell ladder (Section 7)

### 6.3 RELOAD (Offense add on pullback above avg_cost)
RELOAD exists to prevent idling in bullish / choppy markets.

**Permission:**
- `shares > 0`
- `Px >= avg_cost` (profit-zone; otherwise RESCUE territory)

**Anchor update:**
- After any buy event (LOAD/RELOAD/RESCUE/RESET): `anchor_high = HighToday`
- Each cycle: `anchor_high = max(anchor_high, HighToday)`

**Trigger (same pullback threshold as LOAD):**
- `LowToday <= anchor_high * (1 - drop_load_pct/100)`

**Action:**
- buy exactly **1.0 unit** worth of shares
- re-calc avg_cost
- **cancel old ladder, place new ladder** (Section 7)

### 6.4 RESCUE (Defense / averaging-down, smooth gearbox)
RESCUE is only for dips below avg_cost.

**Trigger price:**
- `LowToday <= avg_cost * (1 - drop_rescue_pct/100)`

**Smooth gearbox (defaults):**
- `U_sat = 10.0` (saturation units)
- `drop_min = 4.0`, `drop_span = 2.0`  (drop 4%..6%)
- `r_min = 0.5`, `r_span = 0.2`       (r 0.5..0.7)
- `t = clamp(0, (units - 1)/(U_sat - 1), 1)`
- `drop_rescue_pct = drop_min + drop_span * t`
- `r = r_min + r_span * t`

**Action size (in units):**
- `buy_units_target = units * r`
- cap: `buy_units_target <= (N - units)`

Convert to shares:
- `target_cash = buy_units_target * unit_cash`
- `buy_shares = max(1, round_half_up(target_cash / Px_exec))`

Update:
- `shares += buy_shares`
- `cost_basis_cash += buy_shares * Px_exec`
- `units += (buy_shares * Px_exec) / unit_cash`
- `avg_cost = cost_basis_cash / shares`

After RESCUE:
- `anchor_high = HighToday`
- **re-ladder** sell orders

### 6.5 RESET (Re-arm after Tier 1 fill, then price returns to avg_cost)
RESET handles the half-sold then returned to break-even situation.

**Armed when:**
- Tier 1 executed for the current ladder, but Tier 2 not executed yet.

**Trigger:**
- `LowToday <= avg_cost`
- and dip is NOT deep enough for RESCUE:
  - `LowToday > avg_cost * (1 - drop_rescue_pct/100)`

**Action:**
- buy exactly **1.0 unit**
- update avg_cost
- re-ladder

**Anti-spam:** only one RESET per ladder cycle.

---

## 7) Selling Mechanics (3-tier Ladder)

When a ladder is placed, define `Q = shares` at that moment.

### 7.1 Ladder Prices
Let `p0 = avg_cost`.
- Tier 1 price: `p1 = p0 * (1 + tier1_pct/100)`
- Tier 2 price: `p2 = p0 * (1 + tier2_pct/100)`
- Tier 3 price: `p3 = p0 * (1 + tier3_pct/100)`

### 7.2 Tier Quantities
- `q1 = round_half_up(0.50 * Q)`
- `q2 = round_half_up(0.25 * Q)`
- `q3 = Q - q1 - q2`  (remainder)

### 7.3 Re-laddering Rule (One Ladder Only)
Any buy changes `avg_cost` and `Q`.
So after **LOAD / RELOAD / RESCUE / RESET**:
- cancel existing ladder
- place a fresh ladder

### 7.4 Fill Detection
- Tier executes when `HighToday >= Target Price`
- Use limit orders at target prices (or better)

---

## 8) Idle Engine (Flags, Not Forced Action)
We track inactivity:
- **Yellow flag:** `idle_days >= 5`
- **Red flag:** `idle_days >= 10`

Current policy:
- Idle does NOT force a buy.
- Idle suggests **lower sell gear** (exit sooner) and/or reset posture.

This is implemented as auto-traits:
- `yellow_idle` lowers sell points modestly
- `red_idle` lowers sell points more strongly

---

## 9) Execution Rules and Constraints
- **One action per trading day per stock.** (Sell tiers and buy actions are mutually exclusive.)
- **Order of operations:**
  1) Update price references and `anchor_high`.
  2) Check sell tier fills (using HighToday).
  3) If no sell executed, evaluate one buy action (Section 6.1).
  4) If a buy executed, re-ladder.
- **Hard cap per stock:** `max_units_per_stock = ceil(0.60 * N)`
- **Never exceed total units:** `units <= N`
- **State persistence:** store per-stock state and global state across restarts.
- **Manual override:** allowed for exceptional macro conditions or obvious chart anomalies.

---

## 10) Point-Based Perk System (v0.2)

### 10.1 Why Perks Instead of Raw Gearbox Formulas
- Formula-only gearboxes felt too reactive and non-intuitive.
- Perks are:
  - visible (why gear moved),
  - patchable (change points like game balance),
  - scalable (ratio knob),
  - fun (Fallout style).

### 10.2 How Points Become Smooth Gears
Base:
- `buy_gear_base = 3.0`
- `sell_gear_base = 3.0`

Sum points:
- `buy_points_total = sum(buy_points of active perks)`
- `sell_points_total = sum(sell_points of active perks)`

Convert with ratio **R = 10 points per 1 gear**:
- `buy_shift = buy_points_total / R`
- `sell_shift = sell_points_total / R`

Final:
- `buy_gear = clamp(1.0, buy_gear_base + buy_shift, 5.0)`
- `sell_gear = clamp(1.0, sell_gear_base + sell_shift, 5.0)`
- Emergency: if **Black Swan / Evacuation** active, force sell gear 0.

### 10.3 Stability Controls (Keep Default Most of the Time)
To get your desired distribution (mostly default):
- Keep R=10 (or raise to 12-15 if too reactive)
- Use **exclusive groups** (only 1 volatility trait active, etc.)
- Optional deadzone:
  - if `abs(points_total) < 3`, treat as 0 shift

---

## 11) Perk Library v0.2 (JSON Template)

> This JSON is designed so the engine can load it later.
> `mode="auto"` means it can be auto-checked by conditions.
> `mode="manual"` means it appears as a user checkbox (or radio button if exclusive_group).

```json
{
  "version": "0.2",
  "point_to_gear_ratio": { "buy": 10, "sell": 10 },
  "base_gears": { "buy": 3.0, "sell": 3.0 },
  "gear_limits": { "buy": [1.0, 5.0], "sell": [0.0, 5.0] },
  "notes": {
    "buy_gear_mapping": "drop_load_pct = 2 + buy_gear (so 3.0 -> 5%)",
    "sell_gear_mapping": "tier1 = 1 + sell_gear, tier2 = tier1 + 2, tier3 = tier1 + 4; gear0 = 1/2/3"
  },
  "traits": [
    {
      "id": "gentle_breeze",
      "name": "Gentle Breeze",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "volatility",
      "buy_points": -4,
      "sell_points": -4,
      "auto_trigger": "atr_pct_14 < 2.0",
      "description": "Very low volatility; easier entry, quicker exit."
    },
    {
      "id": "steady_drummer",
      "name": "Steady Drummer",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "volatility",
      "buy_points": -2,
      "sell_points": -2,
      "auto_trigger": "2.0 <= atr_pct_14 && atr_pct_14 < 3.0",
      "description": "Low volatility."
    },
    {
      "id": "hard_shaker",
      "name": "Hard Shaker",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "volatility",
      "buy_points": 6,
      "sell_points": 4,
      "auto_trigger": "3.0 <= atr_pct_14 && atr_pct_14 < 5.0",
      "description": "High volatility; demand deeper buy and aim higher sell."
    },
    {
      "id": "crazy_dancer",
      "name": "Crazy Dancer",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "volatility",
      "buy_points": 10,
      "sell_points": 6,
      "auto_trigger": "5.0 <= atr_pct_14 && atr_pct_14 < 7.0",
      "description": "Very volatile stock."
    },
    {
      "id": "earthquake",
      "name": "Earthquake",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "volatility",
      "buy_points": 14,
      "sell_points": 10,
      "auto_trigger": "atr_pct_14 >= 7.0",
      "description": "Extreme volatility; very defensive entry and ambitious ladder."
    },

    {
      "id": "rocket_fuel",
      "name": "Rocket Fuel",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "trend",
      "buy_points": -12,
      "sell_points": 12,
      "auto_trigger": "roc_5d >= 10.0 && slope_pct_per_day_5d > 0.3",
      "description": "Strong up impulse; easier entry, higher take-profit."
    },
    {
      "id": "tailwind",
      "name": "Tailwind",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "trend",
      "buy_points": -6,
      "sell_points": 6,
      "auto_trigger": "5.0 <= roc_5d && roc_5d < 10.0",
      "description": "Moderate up trend."
    },
    {
      "id": "sideways_fog",
      "name": "Sideways Fog",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "trend",
      "buy_points": 0,
      "sell_points": 0,
      "auto_trigger": "-2.0 < roc_5d && roc_5d < 2.0",
      "description": "No clear short-term direction; default."
    },
    {
      "id": "headwind",
      "name": "Headwind",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "trend",
      "buy_points": 6,
      "sell_points": -6,
      "auto_trigger": "-10.0 < roc_5d && roc_5d <= -5.0",
      "description": "Moderate down drift; avoid over-buying, exit earlier."
    },
    {
      "id": "falling_knife",
      "name": "Falling Knife",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "trend",
      "buy_points": 12,
      "sell_points": -12,
      "auto_trigger": "roc_5d <= -10.0 && slope_pct_per_day_5d < -0.3",
      "description": "Sharp down move; defensive buy and fast exit."
    },

    {
      "id": "oversold_beacon",
      "name": "Oversold Beacon",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "rsi",
      "buy_points": -8,
      "sell_points": -2,
      "auto_trigger": "rsi_14 < 30",
      "description": "Oversold; more willing to enter."
    },
    {
      "id": "overbought_alarm",
      "name": "Overbought Alarm",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "rsi",
      "buy_points": 2,
      "sell_points": 8,
      "auto_trigger": "rsi_14 > 70",
      "description": "Overbought; avoid chasing, raise ladder."
    },

    {
      "id": "empty_barracks",
      "name": "Empty Barracks",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "deployment",
      "buy_points": -8,
      "sell_points": 0,
      "auto_trigger": "deployed_pct < 5",
      "description": "Under-allocated; easier entry allowed."
    },
    {
      "id": "scout_team",
      "name": "Scout Team",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "deployment",
      "buy_points": -4,
      "sell_points": 0,
      "auto_trigger": "5 <= deployed_pct && deployed_pct < 15",
      "description": "Light position."
    },
    {
      "id": "balanced_front",
      "name": "Balanced Front",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "deployment",
      "buy_points": 0,
      "sell_points": 0,
      "auto_trigger": "15 <= deployed_pct && deployed_pct < 35",
      "description": "Normal allocation."
    },
    {
      "id": "heavy_artillery",
      "name": "Heavy Artillery",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "deployment",
      "buy_points": 4,
      "sell_points": -4,
      "auto_trigger": "35 <= deployed_pct && deployed_pct < 55",
      "description": "Getting heavy; be cautious on adding, exit earlier."
    },
    {
      "id": "overextended",
      "name": "Overextended",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "deployment",
      "buy_points": 8,
      "sell_points": -8,
      "auto_trigger": "55 <= deployed_pct && deployed_pct < 75",
      "description": "Oversized; strong caution."
    },
    {
      "id": "maxed_out",
      "name": "Maxed Out",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "deployment",
      "buy_points": 12,
      "sell_points": -12,
      "auto_trigger": "deployed_pct >= 75",
      "description": "Near max exposure; prepare evacuation posture."
    },

    {
      "id": "green_shoots",
      "name": "Green Shoots",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "pnl",
      "buy_points": -2,
      "sell_points": 2,
      "auto_trigger": "0 <= pnl_pct && pnl_pct < 5",
      "description": "Small profit zone."
    },
    {
      "id": "slightly_underwater",
      "name": "Slightly Underwater",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "pnl",
      "buy_points": 2,
      "sell_points": -2,
      "auto_trigger": "-5 < pnl_pct && pnl_pct < 0",
      "description": "Small loss zone."
    },
    {
      "id": "deep_underwater",
      "name": "Deep Underwater",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "pnl",
      "buy_points": 6,
      "sell_points": -6,
      "auto_trigger": "pnl_pct <= -10",
      "description": "Deep loss; defensive posture and faster exit."
    },

    {
      "id": "fx_green_light",
      "name": "FX Green Light",
      "icon": "",
      "mode": "auto",
      "scope": "global",
      "exclusive_group": "fx",
      "buy_points": -6,
      "sell_points": 0,
      "auto_trigger": "is_us_stock && fx_dev_pct <= -2.0",
      "description": "USD cheap vs your average; easier US entry."
    },
    {
      "id": "fx_red_light",
      "name": "FX Red Light",
      "icon": "",
      "mode": "auto",
      "scope": "global",
      "exclusive_group": "fx",
      "buy_points": 0,
      "sell_points": 6,
      "auto_trigger": "is_us_stock && fx_dev_pct >= 2.0 && fx_dev_pct < 5.0",
      "description": "USD expensive; raise selling motivation."
    },
    {
      "id": "fx_premium_zone",
      "name": "FX Premium Zone",
      "icon": "",
      "mode": "auto",
      "scope": "global",
      "exclusive_group": "fx",
      "buy_points": 2,
      "sell_points": 12,
      "auto_trigger": "is_us_stock && fx_dev_pct >= 5.0",
      "description": "Very strong USD; strong sell bias."
    },

    {
      "id": "gap_storm",
      "name": "Gap Storm",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "gap",
      "buy_points": 4,
      "sell_points": 4,
      "auto_trigger": "abs(gap_pct) >= 2.0",
      "description": "Big gap day; widen both gears slightly."
    },

    {
      "id": "yellow_idle",
      "name": "Yellow Idle Flag",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "idle",
      "buy_points": 0,
      "sell_points": -4,
      "auto_trigger": "idle_days >= 5 && idle_days < 10",
      "description": "No action for 5+ days; lower sell gear a bit."
    },
    {
      "id": "red_idle",
      "name": "Red Idle Flag",
      "icon": "",
      "mode": "auto",
      "scope": "local",
      "exclusive_group": "idle",
      "buy_points": 0,
      "sell_points": -8,
      "auto_trigger": "idle_days >= 10",
      "description": "No action for 10+ days; lower sell gear more."
    },

    {
      "id": "raging_bull",
      "name": "Raging Bull",
      "icon": "",
      "mode": "manual",
      "scope": "global",
      "exclusive_group": "market_regime",
      "buy_points": -10,
      "sell_points": 10,
      "auto_trigger": null,
      "description": "Manual market regime: bullish."
    },
    {
      "id": "choppy_range",
      "name": "Choppy Range",
      "icon": "",
      "mode": "manual",
      "scope": "global",
      "exclusive_group": "market_regime",
      "buy_points": 0,
      "sell_points": 0,
      "auto_trigger": null,
      "description": "Manual market regime: sideways."
    },
    {
      "id": "cautious_bear",
      "name": "Cautious Bear",
      "icon": "",
      "mode": "manual",
      "scope": "global",
      "exclusive_group": "market_regime",
      "buy_points": 10,
      "sell_points": -10,
      "auto_trigger": null,
      "description": "Manual market regime: bearish caution."
    },
    {
      "id": "savage_bear",
      "name": "Savage Bear",
      "icon": "",
      "mode": "manual",
      "scope": "global",
      "exclusive_group": "market_regime",
      "buy_points": 14,
      "sell_points": -14,
      "auto_trigger": null,
      "description": "Manual market regime: heavy risk-off."
    },

    {
      "id": "earnings_roulette",
      "name": "Earnings Roulette",
      "icon": "",
      "mode": "manual",
      "scope": "local",
      "exclusive_group": "event_risk",
      "buy_points": 6,
      "sell_points": -6,
      "auto_trigger": null,
      "description": "Pre-earnings uncertainty: defensive."
    },
    {
      "id": "news_minefield",
      "name": "News Minefield",
      "icon": "",
      "mode": "manual",
      "scope": "local",
      "exclusive_group": "event_risk",
      "buy_points": 8,
      "sell_points": -8,
      "auto_trigger": null,
      "description": "Headline risk: defensive."
    },
    {
      "id": "product_launch",
      "name": "Product Launch",
      "icon": "",
      "mode": "manual",
      "scope": "local",
      "exclusive_group": "event_risk",
      "buy_points": -4,
      "sell_points": 4,
      "auto_trigger": null,
      "description": "Positive catalyst expectation; posture only."
    },

    {
      "id": "busy_day_protocol",
      "name": "Busy Day Protocol",
      "icon": "",
      "mode": "manual",
      "scope": "local",
      "exclusive_group": "psych",
      "buy_points": 2,
      "sell_points": -8,
      "auto_trigger": null,
      "description": "You cannot manage actively today; lower sell gear for quicker exit."
    },
    {
      "id": "patience_mode",
      "name": "Patience Mode",
      "icon": "",
      "mode": "manual",
      "scope": "local",
      "exclusive_group": "psych",
      "buy_points": 2,
      "sell_points": 6,
      "auto_trigger": null,
      "description": "You accept longer hold; slightly raise sell ladder."
    },
    {
      "id": "high_conviction",
      "name": "High Conviction",
      "icon": "",
      "mode": "manual",
      "scope": "local",
      "exclusive_group": "psych",
      "buy_points": -6,
      "sell_points": 6,
      "auto_trigger": null,
      "description": "You trust this setup more than usual."
    },

    {
      "id": "black_swan",
      "name": "Black Swan (Evacuation)",
      "icon": "",
      "mode": "manual",
      "scope": "global",
      "exclusive_group": "evac",
      "buy_points": 15,
      "sell_points": -15,
      "auto_trigger": null,
      "description": "Emergency override: force sell gear 0 posture."
    }
  ]
}
```
