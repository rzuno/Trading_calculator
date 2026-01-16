# AI Seesaw Trading Manual v1.4.0

**Version:** 1.4.0 (Unification Update)  
**Date:** January 2026  
**Author:** Juno  
**Status:** Automation-Ready Production System  
**Philosophy:** Pure Mean Reversion with Adaptive Entry & Strategic Exit

---

## 0. Document Overview & Philosophy

### 0.1 Purpose

This manual defines a complete, rule-based trading system for AI-sector stocks. The system is designed to:
- Operate mechanically (minimize emotional decisions)
- Scale across multiple stocks (portfolio approach)
- Adapt to market regimes (trend-responsive)
- Support full automation (every decision has a formula)

### 0.2 Core Philosophy

**"Warfare, Not Gambling"**

- **Trading = War**: Capital is your army, divided into units deployed across battlefronts.
- **Winnable Battles Only**: We fight when conditions favor us (clear trend, adequate volatility, sufficient liquidity).
- **Rest When Uncertain**: When markets are unreadable, capital rests in cash management accounts (CMA) or USD RP, earning safe returns.

**"Asymmetric Strategy"**

- **Buying is Mechanical**: We use standardized rules to enter and defend positions. We do not predict bottoms; we mechanically engage dips.
- **Selling is Strategic**: We use committee evaluation (G/L scores) and deployment penalties to optimize exit timing across different market regimes.

**"Mean Reversion Focus"**

- We buy dips and sell bounces within a broader uptrend.
- We do NOT pyramid (add to winners above cost basis).
- We enter light, defend heavy, exit clean.

### 0.3 Scope

**Target Universe**: AI-sector stocks only
- **US**: NVIDIA, Alphabet (GOOGL)
- **KR**: Samsung Electronics, SK hynix

**Strategy Type**: Swing/position trading (holding periods: days to weeks)

**Capital Allocation**: Fixed unit system (see Section 2)

---

## 1. Terminology & Core Concepts

### 1.1 Unit System

**Total Units (N)**: The maximum number of identical "units" allocated across your entire portfolio.
- Recommended: N = 20-30
- Example: If total capital = $50,000 and N = 25, each unit = $2,000

**Unit Size**: `Total Capital / N`

**Position Size**: Number of units currently held in a specific stock
- Measured in units (integer)
- Example: "Holding 7 units of Samsung" = $14,000 if unit size = $2,000

**Deployment Ratio (f)**: Total capital actively invested across all stocks
```
f = (Sum of all active position values) / (Total Capital)
```
- Range: [0, 1] (0% to 100%)
- Example: 3 stocks with 5, 3, 2 units = 10/25 = f = 0.40 (40% deployed)

### 1.2 Campaign States

**Campaign**: A complete trading cycle for one stock (entry → defense → exit)

**States**:
1. **IDLE** (position = 0): No holdings, watching for entry opportunity
2. **ACTIVE** (position > 0): Holding position, managing defense and exit
3. **EXIT** (executing sells): Unwinding position via tier targets

**State Transitions**:
```
IDLE → [LOAD trigger] → ACTIVE → [Sell tiers complete] → IDLE
```

### 1.3 Price References

**For automated trigger detection, we use intraday extremes**:

- **High5**: Highest intraday HIGH of the past 5 trading days (not including today)
- **LowToday**: Intraday LOW of current trading day
- **HighToday**: Intraday HIGH of current trading day

**Why High/Low instead of Close?**
- More sensitive to actual price action
- Matches limit order execution reality
- Captures intraday opportunities

**Example**:
```
Day 1-5 candles: [High, Low, Close]
  [102, 98, 100], [105, 101, 103], [108, 104, 106], [107, 103, 105], [110, 106, 108]

High5 = max(102, 105, 108, 107, 110) = 110

Day 6 intraday:
  Current price moves 109 → 107 → 111 → 108
  LowToday = 107
  HighToday = 111 (so far)
```

### 1.4 Average Cost Tracking

**Average Cost (avg_cost)**: Weighted average purchase price of current position
- Recalculates after every buy
- Does NOT change when selling
- Resets to 0 when position fully exits

**Formula**:
```python
new_avg_cost = (old_avg_cost × old_units + buy_price × buy_units) / (old_units + buy_units)
```

**Example**:
```
Buy 1 unit @ $100 → avg = $100
Buy 2 units @ $95 → avg = (100×1 + 95×2) / 3 = $96.67
Buy 3 units @ $90 → avg = (96.67×3 + 90×3) / 6 = $93.33
```

---

## 2. Army Structure & Portfolio Management

### 2.1 Total Capital Allocation

**Global Pool**: All capital is managed as a single pool with N total units.

**Per-Stock Concentration Limit**: 
```
Max units per stock = ceil(0.60 × N)
```

**Example** (N = 25):
- Max per stock: ceil(15) = 15 units (60% concentration)
- Typical deployment: 2-3 stocks active simultaneously
- Reserve: ~10 units in cash (40% minimum reserve)

**Rationale**: Prevents over-concentration while allowing meaningful positions.

### 2.2 State Variables (Per Stock)

Each stock campaign tracks:

```python
{
    'symbol': str,           # e.g., 'Samsung', 'NVIDIA'
    'units': int,            # Current position size (0 = idle)
    'avg_cost': float,       # Average purchase price (0 if idle)
    'V': float,              # Volatility factor [0.0, 2.0]
    'sell_targets': dict,    # Active sell limit orders
    'Q': int,                # Position snapshot for sell tiers
}
```

### 2.3 Global State Variables

Portfolio-level tracking:

```python
{
    'N': int,                    # Total units (e.g., 25)
    'unit_size': float,          # Dollars per unit
    'f_global': float,           # Deployment ratio [0, 1]
    'G': float,                  # Global AI sector score [0, 5]
    'active_campaigns': list,    # Stocks with units > 0
}
```

---

## 3. Committee Scores (G/L/V)

The **G/L/V Committee** is a structured process (human + AI assistant) for scoring market conditions. These scores drive strategy parameters.

### 3.1 Global Score (G)

**Definition**: AI sector macro environment score

**Range**: [0, 5] (float, precision to 0.1)

**Factors**:
- **Sector Momentum**: Relative strength vs. broader market (e.g., XLK, QQQ performance)
- **Macro Environment**: Fed policy stance, interest rates, liquidity conditions
- **AI Narrative**: Sentiment cycle (hype vs. skepticism), regulatory developments
- **Technical**: Sector ETFs vs. moving averages (50-day, 200-day)

**Scoring Guide**:
| Score | Regime | Description |
|-------|--------|-------------|
| 0.0-1.0 | Deep Bear | Sector in sustained decline, macro headwinds severe |
| 1.0-2.0 | Bear | Downtrend, negative sentiment, defensive posture |
| 2.0-3.0 | Neutral | Range-bound, mixed signals, no clear direction |
| 3.0-4.0 | Bull | Uptrend, positive sentiment, favorable macro |
| 4.0-5.0 | Strong Bull | Explosive rally, euphoria, strong fundamentals + momentum |

**Update Frequency**: 
- Monthly review (first Monday of month)
- Event-driven: Major Fed decisions, sector-wide crashes/rallies, regulatory changes

**Example** (January 2026):
```
G = 3.8 (Bullish)

Reasoning:
- AI sector ETFs above 50d/200d MAs (+1.0)
- Fed pause on rate hikes, stable liquidity (+0.8)
- Strong AI adoption narrative (cloud growth, enterprise AI) (+1.0)
- No major regulatory threats (+0.5)
- Some valuation concern (modest penalty -0.5)

Final: 3.8
```

### 3.2 Local Score (L)

**Definition**: Stock-specific environment score with extension check

**Range**: [0, 5] (float, precision to 0.1)

**Factors**:
- **Technical Trend**: Stock vs. its own MAs (50d, 200d), slope direction
- **Relative Strength**: Stock vs. sector peers, vs. sector ETF
- **Volume**: Accumulation/distribution patterns, breakout confirmation
- **Company Fundamentals**: Earnings quality, guidance, competitive position
- **Recent Performance**: Extension check (see below)

**Extension Check** (Critical):

To prevent overvaluing already-extended stocks, apply penalty:

```python
def compute_extension_penalty(current_price, low_20d):
    """
    Penalty for stocks that have rallied too much recently.
    """
    gain_pct = (current_price - low_20d) / low_20d * 100
    
    if gain_pct > 30:
        return -1.5
    elif gain_pct > 20:
        return -1.0
    elif gain_pct > 15:
        return -0.5
    else:
        return 0.0
```

**L Calculation**:
```python
L_technical = score_chart_and_fundamentals()  # 0-5 range
extension_penalty = compute_extension_penalty(price, low_20d)
L_final = max(0, min(5, L_technical + extension_penalty))
```

**Scoring Guide**:
| Score | Regime | Description |
|-------|--------|-------------|
| 0.0-1.0 | Breakdown | Below all MAs, negative momentum, weak fundamentals |
| 1.0-2.0 | Weak | Downtrend or failed bounce, deteriorating conditions |
| 2.0-3.0 | Neutral | Choppy, no clear trend, mixed technicals |
| 3.0-4.0 | Strong | Uptrend, above MAs, positive momentum |
| 4.0-5.0 | Very Strong | Breakout, strong volume, excellent fundamentals |

**Update Frequency**:
- Weekly review (every Monday)
- Event-driven: Earnings releases, major company news, chart breakouts/breakdowns

**Example** (Samsung, January 2026):
```
L_technical = 4.2 (Strong)

Technical factors:
- Above rising 50d/200d MAs (+1.5)
- Breakout from consolidation (+1.0)
- Strong volume on up days (+0.7)
- Positive earnings surprise (+1.0)

Extension check:
- Current: 88,000
- 20-day low: 72,000
- Gain: (88-72)/72 = 22.2%
- Penalty: -1.0

L_final = 4.2 - 1.0 = 3.2
```

### 3.3 Volatility Factor (V)

**Definition**: Stock character measurement (how choppy/smooth it trades)

**Range**: [0.0, 2.0] (float, precision to 0.5)

**Measurement Methods**:

**Method A: Observational (Current)**
```
V = 0.0-0.5 (Calm):
  - Typical daily moves < 2%
  - Rarely gaps on news
  - Smooth, predictable trends
  - Example: Alphabet, mature mega-caps

V = 0.5-1.5 (Normal):
  - Typical daily moves 2-4%
  - Occasional gaps on earnings/news
  - Clear trends with moderate pullbacks
  - Example: Samsung, NVIDIA (stable periods)

V = 1.5-2.0 (Volatile):
  - Typical daily moves > 4%
  - Frequent gaps and whipsaws
  - Hard to time, false breakouts common
  - Example: SK hynix, high-beta tech
```

**Method B: Calculated (For Future Automation)**
```python
def compute_V_from_data(price_history, period=60):
    """
    Calculate V from historical volatility.
    
    Returns V in [0, 2] based on annualized volatility.
    """
    daily_returns = price_history['close'].pct_change()
    vol_annual = daily_returns.std() * (252 ** 0.5)
    
    # Map volatility to V scale
    if vol_annual < 0.25:      # <25% annual vol
        return 0.0
    elif vol_annual < 0.30:    # 25-30%
        return 0.5
    elif vol_annual < 0.35:    # 30-35%
        return 1.0
    elif vol_annual < 0.40:    # 35-40%
        return 1.5
    else:                       # >40%
        return 2.0
```

**Update Frequency**: 
- Quarterly review
- Event-driven: Stock enters new volatility regime (e.g., merger announcement, regulatory investigation)

**Current Assignments** (Example):
```python
volatility_scores = {
    'Alphabet': 0.5,   # Calm mega-cap
    'Samsung': 1.0,    # Normal large-cap
    'NVIDIA': 1.0,     # Normal (can spike to 1.5 during earnings)
    'SK hynix': 2.0,   # Volatile cyclical
}
```

---

## 4. Buy Mechanics: Two-Phase System

The buy system has two distinct phases with different purposes and formulas.

### 4.1 Overview: LOAD vs RESCUE

```
┌─────────────────────────────────────────────────────┐
│ LOAD Phase (Entry Filter)                          │
│ Purpose: Start new campaigns                       │
│ Trigger: Volatility + Trend adaptive               │
│ Reference: Visual peak (5-day high)                │
│ Size: Always 1 unit                                │
└─────────────────────────────────────────────────────┘
                    ↓
         (Campaign becomes ACTIVE)
                    ↓
┌─────────────────────────────────────────────────────┐
│ RESCUE Phase (Position Tracker)                    │
│ Purpose: Defend underwater positions               │
│ Trigger: Position-adaptive (V-Transmission)        │
│ Reference: Average cost                            │
│ Size: Compounding (r × units)                      │
└─────────────────────────────────────────────────────┘
```

**Key Distinction**:
- **LOAD**: Stock-specific (uses V and T to filter entry quality)
- **RESCUE**: Position-specific (uses V-Transmission to adapt to commitment level)

### 4.2 LOAD (Entry Phase)

**Condition**: Position = 0 (campaign is IDLE)

**Purpose**: Filter out false entry signals, enter only on high-quality dips

**Formula**:
```
Drop_load% = 6.0 - 0.6 × T + 0.5 × V
```

**Range**: [3.0%, 7.0%]

**Coefficient Logic**:
- **T weight (-0.6)**: Trend is the primary driver
  - Bullish trend (high T) → easier entry (lower drop%)
  - Bearish trend (low T) → harder entry (higher drop%)
  - 3.0% swing across T range (0→5)
- **V weight (+0.5)**: Volatility provides minor adjustment
  - Volatile stocks require deeper dips for confirmation
  - 1.0% swing across V range (0→2)
- **Ratio**: Trend is 3× more important than volatility

**Trigger Logic**:
```python
def check_load_trigger(high_5d, low_today, T, V):
    """
    Check if LOAD should fire.
    
    Returns: (triggered: bool, trigger_price: float)
    """
    drop_load_pct = 6.0 - 0.6 * T + 0.5 * V
    drop_load_pct = max(3.0, min(7.0, drop_load_pct))  # Clamp
    
    trigger_price = high_5d * (1 - drop_load_pct / 100)
    triggered = low_today <= trigger_price
    
    return triggered, trigger_price
```

**Action**: Buy 1 unit at current price

**Visual Peak Note**: 
- `High5` is the algorithmic reference (highest HIGH of past 5 days)
- But allow manual discretion: if you see a "real" peak that's more significant than the 5-day window, you can mark it manually
- Example: A sharp reversal point with high volume might be at day 7, which won't be captured by strict 5-day rule

**Examples**:

```
Stock: Samsung
T = 4.0 (Bullish), V = 1.0 (Normal)

Drop_load = 6.0 - 0.6×4.0 + 0.5×1.0 = 6.0 - 2.4 + 0.5 = 4.1%

High5 = 88,000
Trigger = 88,000 × 0.959 = 84,392

Day 6: LowToday = 84,100
84,100 ≤ 84,392 → LOAD FIRES ✓
Buy 1 unit at 84,100
```

```
Stock: SK hynix
T = 1.5 (Bearish), V = 2.0 (Volatile)

Drop_load = 6.0 - 0.6×1.5 + 0.5×2.0 = 6.0 - 0.9 + 1.0 = 6.1%

High5 = 620,000
Trigger = 620,000 × 0.939 = 582,180

Day 6: LowToday = 585,000
585,000 > 582,180 → No LOAD (not deep enough)

Day 7: LowToday = 580,000
580,000 ≤ 582,180 → LOAD FIRES ✓
Buy 1 unit at 580,000
```

**Range Analysis**:

| Scenario | T | V | Drop% | Behavior |
|----------|---|---|-------|----------|
| Very bullish, calm | 5.0 | 0.0 | 3.0% | Aggressive entry |
| Bullish, normal | 4.0 | 1.0 | 4.1% | Standard easy entry |
| Neutral, normal | 2.5 | 1.0 | 5.0% | Balanced |
| Bearish, normal | 1.0 | 1.0 | 5.9% | Cautious |
| Very bearish, volatile | 0.0 | 2.0 | 7.0% | Very cautious |

### 4.3 RESCUE (Defense Phase)

**Condition**: Position > 0 AND price < avg_cost (underwater)

**Purpose**: Systematically average down to repair position, with size adapting to commitment level

**V-Transmission Gearbox**:

Define unit thresholds dynamically based on total N:
```python
u1 = ceil(0.10 × N)  # Ignition cap (10% of portfolio)
u2 = ceil(0.25 × N)  # Cruise cap (25% of portfolio)
```

**Example** (N = 25):
- u1 = ceil(2.5) = 3
- u2 = ceil(6.25) = 7

**Gear Table**:

| Gear | Condition (Units Held) | Drop Trigger | Buy Multiplier (r) | Purpose |
|------|----------------------|--------------|-------------------|---------|
| **1st (Ignition)** | 1 to u1 | **-4%** | **0.5** | Light tracking, prevent overcommit |
| **2nd (Cruise)** | u1+1 to u2 | **-5%** | **0.6** | Standard averaging |
| **3rd (Brake)** | > u2 | **-6%** | **0.7** | Deep defense, strong rescue |

**Trigger Logic**:
```python
def get_rescue_gear(units_held, N):
    """
    Determine current gear based on position size.
    
    Returns: (drop_pct, r)
    """
    u1 = ceil(0.10 * N)
    u2 = ceil(0.25 * N)
    
    if units_held <= u1:
        return 4.0, 0.5  # Gear 1
    elif units_held <= u2:
        return 5.0, 0.6  # Gear 2
    else:
        return 6.0, 0.7  # Gear 3

def check_rescue_trigger(avg_cost, low_today, units_held, N):
    """
    Check if RESCUE should fire.
    
    Returns: (triggered: bool, buy_qty: int, trigger_price: float)
    """
    drop_pct, r = get_rescue_gear(units_held, N)
    trigger_price = avg_cost * (1 - drop_pct / 100)
    triggered = low_today <= trigger_price
    
    if triggered:
        buy_qty_raw = units_held * r
        buy_qty = max(1, round(buy_qty_raw))
        
        # Hard cap: Never exceed N total
        max_buy = N - units_held
        buy_qty = min(buy_qty, max_buy)
    else:
        buy_qty = 0
    
    return triggered, buy_qty, trigger_price
```

**Buy Size Calculation**:
```python
buy_qty = max(1, round(units_held × r))

# Then clamp to available capacity:
buy_qty = min(buy_qty, N - units_held)
```

**No Time Limits**: RESCUE can fire on consecutive days in steep declines (this is intentional for crash protection)

**Concentration Cap**: If `units_held ≥ ceil(0.60 × N)`, stop all buying (position maxed out)

**Example Progression** (N = 25):

```
Step 0: LOAD
  Buy 1 unit @ 100 → units=1, avg=100

Step 1: RESCUE (Gear 1: -4%, r=0.5)
  Trigger: 100 × 0.96 = 96
  Price drops to 95 → RESCUE fires
  buy_qty = max(1, round(1 × 0.5)) = 1
  Buy 1 unit @ 95 → units=2, avg=97.5

Step 2: RESCUE (Gear 1: -4%, r=0.5)
  Trigger: 97.5 × 0.96 = 93.6
  Price drops to 93 → RESCUE fires
  buy_qty = max(1, round(2 × 0.5)) = 1
  Buy 1 unit @ 93 → units=3, avg=95.17

Step 3: RESCUE (Gear 1: -4%, r=0.5)
  u1 = 3, so still Gear 1
  Trigger: 95.17 × 0.96 = 91.36
  Price drops to 91 → RESCUE fires
  buy_qty = max(1, round(3 × 0.5)) = 2 (rounds 1.5)
  Buy 2 units @ 91 → units=5, avg=93.4

Step 4: RESCUE (Gear 2: -5%, r=0.6)
  units=5, u1=3, u2=7, so Gear 2 applies
  Trigger: 93.4 × 0.95 = 88.73
  Price drops to 88 → RESCUE fires
  buy_qty = max(1, round(5 × 0.6)) = 3
  Buy 3 units @ 88 → units=8, avg=91.05

Step 5: RESCUE (Gear 3: -6%, r=0.7)
  units=8 > u2(7), so Gear 3 applies
  Trigger: 91.05 × 0.94 = 85.59
  Price drops to 85 → RESCUE fires
  buy_qty = max(1, round(8 × 0.7)) = 6 (rounds 5.6)
  Buy 6 units @ 85 → units=14, avg=88.18

Position Summary:
  Total: 14 units @ avg $88.18
  Breakdown: 1+1+1+2+3+6 = 14 units
  Total cost: $1,235 (if unit_size = $100)
  Drawdown from initial LOAD: -11.82%
```

**Gear Shift Efficiency**:

The V-Transmission automatically widens rescue spacing as position grows:

```
Light position (1-3 units): -4% spacing
  → Tracks price closely, many small entries
  
Medium position (4-7 units): -5% spacing
  → Standard tracking
  
Heavy position (8+ units): -6% spacing
  → Deeper safety net, fewer but larger buys
```

This prevents overtrading when already heavily committed.

### 4.4 The "Hovering Zone"

**Situation**: Position > 0 AND price ≥ avg_cost (above water but below sell targets)

**System Response**: No automatic buy signal

**This is intentional**:
- You're not underwater (RESCUE inactive)
- You're not in profit zone (sell targets not hit)
- This is "hold and watch" territory

**Manual Options**:
1. **Hold**: Wait for sell targets or dip back to RESCUE
2. **Exit and Reset**: Sell at market if you judge trend is broken, return to IDLE
3. **Discretionary Add**: Manually buy if you have strong conviction (log as manual override)

**Example**:
```
LOAD @ 100, avg=100, units=1
Rally to 104, sell Tier 1 (50%) @ 103
Now: 0.5 units remaining, avg=100
Price hovers: 102 → 101 → 100.5 → 101.5

No automatic signal:
- LOAD disabled (position > 0)
- RESCUE disabled (price ≥ avg_cost)

You decide:
- If bullish: Hold for Tier 2 target (106)
- If unsure: Sell remaining at market, restart
```

---

## 5. Sell Mechanics: Unified 2-Tier System

### 5.1 Philosophy

**Selling is strategic, not mechanical**. We use committee scores and deployment penalties to optimize profit-taking across different market regimes.

**Key Innovation (v1.4)**: All scenarios now use the same 2-tier structure with optimized multipliers (1.25×, 2.5×) to balance fast rotation with adequate profit floor.

### 5.2 Sell Gear Calculation

**Step 1: Compute Trend Score (T)**
```
T = (3 × L + 2 × G) / 5
```

- L weight: 60% (local stock conditions dominate)
- G weight: 40% (global sector provides context)
- Range: [0, 5]

**Step 2: Compute Deployment Penalty (P)**
```python
def compute_penalty(f_global):
    """
    Penalty based on total portfolio deployment.
    
    f_global: Total deployed capital / Total capital
    """
    if f_global <= 0.4:
        return 0.0
    else:
        return -3.0 * (f_global - 0.4) / 0.6
```

**Logic**:
- Light deployment (≤40%): No penalty, allow profits to run
- Heavy deployment (>40%): Increasing penalty, prioritize liquidity
- Max penalty: -3.0 at f=1.0 (100% deployed)

**Step 3: Compute Gear (g)**
```
g_raw = T + P
g = clamp(g_raw, 0, 5)
g = round(g × 10) / 10  # Quantize to 0.1 precision
```

**Step 4: Compute Step (s)**
```
s = 1 + g  (in percent)
```

**Range**: [1%, 6%]

**Examples**:

```
Example 1: Bullish, Light Deployment
  G = 4.0, L = 4.5, f_global = 0.30
  
  T = (3×4.5 + 2×4.0) / 5 = 4.3
  P = 0 (f ≤ 0.4)
  g = clamp(4.3, 0, 5) = 4.3
  s = 1 + 4.3 = 5.3%

Example 2: Bearish, Heavy Deployment
  G = 1.5, L = 2.0, f_global = 0.75
  
  T = (3×2.0 + 2×1.5) / 5 = 1.8
  P = -3 × (0.75 - 0.4) / 0.6 = -1.75
  g = clamp(1.8 - 1.75, 0, 5) = 0.05 ≈ 0.1
  s = 1 + 0.1 = 1.1%

Example 3: Neutral, Medium Deployment
  G = 3.0, L = 3.0, f_global = 0.50
  
  T = (3×3.0 + 2×3.0) / 5 = 3.0
  P = -3 × (0.50 - 0.4) / 0.6 = -0.5
  g = clamp(3.0 - 0.5, 0, 5) = 2.5
  s = 1 + 2.5 = 3.5%
```

### 5.3 Unified 2-Tier Structure

**All scenarios use the same structure** (v1.4 simplification):

**Position Snapshot (Q)**: 
- Q = Position size immediately after the last buy
- This snapshot is used for all tier calculations until full exit

**Tier Targets**:
```
Tier 1 Target: avg_cost × (1 + 1.25 × s / 100)
Tier 2 Target: avg_cost × (1 + 2.50 × s / 100)
```

**Tier Sizes**:
```
Tier 1: Sell floor(Q × 0.50) units
Tier 2: Sell all remaining units
```

**Execution Trigger**:
- Tier executes when `HighToday ≥ Target Price`
- Use limit orders at target prices (or better)

**Why 1.25× and 2.5× multipliers?**

These preserve profit expectations compared to the old 3-tier system:

| Old System (s<3%) | New System | Average Profit |
|------------------|------------|----------------|
| 3-tier: s, 2s, 3s<br>(50%, 25%, 25%) | 2-tier: 1.25s, 2.5s<br>(50%, 50%) | Nearly identical |

**Example** (s = 2%):
```
Old 3-tier: 2%, 4%, 6% → Avg = (1 + 1 + 1.5) = 3.5%
New 2-tier: 2.5%, 5% → Avg = (1.25 + 2.5) = 3.75%

Difference: +0.25% (acceptable)
```

**Example** (s = 5%):
```
Old 2-tier: 5%, 10% → Avg = (2.5 + 5) = 7.5%
New 2-tier: 6.25%, 12.5% → Avg = (3.125 + 6.25) = 9.375%

Difference: +1.875% (more aggressive, but cleaner exit)
```

### 5.4 Complete Sell Example

```
Stock: Samsung
Position: 8 units @ avg_cost = 90,000
G = 3.5, L = 4.0, f_global = 0.45

Step 1: Calculate s
  T = (3×4.0 + 2×3.5) / 5 = 3.8
  P = -3 × (0.45 - 0.4) / 0.6 = -0.25
  g = clamp(3.8 - 0.25, 0, 5) = 3.55 ≈ 3.6
  s = 1 + 3.6 = 4.6%

Step 2: Calculate Targets
  Q = 8 (position snapshot)
  
  Tier 1: 90,000 × (1 + 1.25 × 4.6 / 100) = 90,000 × 1.0575 = 95,175
  Tier 2: 90,000 × (1 + 2.50 × 4.6 / 100) = 90,000 × 1.1150 = 100,350

Step 3: Set Limit Orders
  Tier 1: Sell 4 units (50% of 8) @ 95,175 limit
  Tier 2: Sell 4 units (remaining) @ 100,350 limit

Step 4: Execution
  Day 10: HighToday = 95,500 ≥ 95,175 → Tier 1 FILLS
    Sell 4 units @ ~95,200 (market execution near limit)
    Position: 4 units remaining @ avg 90,000
    
  Day 15: HighToday = 101,000 ≥ 100,350 → Tier 2 FILLS
    Sell 4 units @ ~100,400
    Position: 0 units (campaign complete)

Profit Analysis:
  Total cost: 90,000 × 8 = 720,000
  Total proceeds: 95,200 × 4 + 100,400 × 4 = 782,400
  Profit: 62,400 (8.67% return)
```

### 5.5 Manual Override

**When to Override**:
- Stock is "extended" (up >25% from 20-day low) but L score hasn't adjusted yet
- You have conviction that trend is weaker/stronger than committee scores suggest
- Obvious chart pattern (e.g., parabolic move topping out)

**How to Override**:
```python
# Instead of calculated s = 4.6%, manually set:
s_manual = 3.0  # More conservative exit

# Recalculate targets with manual step:
tier1_target = avg_cost * (1 + 1.25 * 3.0 / 100)
tier2_target = avg_cost * (1 + 2.50 * 3.0 / 100)
```

**Log Override**:
```python
log_manual_override(
    date = today,
    stock = 'Samsung',
    auto_s = 4.6,
    manual_s = 3.0,
    reason = 'Stock up 28% from 20d low, extended'
)
```

**Use sparingly**: Trust the system unless you have strong, specific conviction.

---

## 6. Execution Rules & Automation

### 6.1 Daily Execution Flow

**Order of Operations** (critical for automation):

```python
def daily_execution_flow(stock):
    """
    Process one stock per trading day.
    
    Call this once per stock at market open or after close.
    """
    # 1. Update price data
    update_prices(stock)  # high_5d, low_today, high_today
    
    # 2. Check SELL triggers FIRST
    if stock.units > 0:
        check_and_execute_sells(stock)
    
    # 3. After sells, check BUY triggers
    if stock.units == 0:
        # LOAD mode
        triggered, qty = check_load_trigger(stock)
        if triggered:
            execute_buy(stock, qty, 'LOAD')
    
    elif stock.units > 0 and current_price < stock.avg_cost:
        # RESCUE mode
        triggered, qty = check_rescue_trigger(stock)
        if triggered:
            execute_buy(stock, qty, 'RESCUE')
    
    # 4. Update deployment ratio
    update_global_deployment()
```

**Why sells before buys?**
- Prevents same-day churn (buy then immediately sell)
- Prioritizes capital release (exit before re-entry)
- More conservative (exits take precedence)

### 6.2 One Action Per Day Rule

**Constraint**: Maximum one BUY action per stock per day

**Rationale**:
- Prevents algorithm spam in volatile conditions
- Matches realistic manual trading cadence
- Reduces transaction costs

**Implementation**:
```python
class Stock:
    def __init__(self):
        self.last_buy_date = None
    
    def can_buy_today(self, today):
        """Check if buy is allowed today."""
        if self.last_buy_date is None:
            return True
        return today > self.last_buy_date
    
    def execute_buy(self, qty, mode, today):
        """Execute buy and update last action date."""
        # ... execute order ...
        self.last_buy_date = today
```

**Sells are NOT limited**: Multiple tiers can execute same day if price spikes

### 6.3 Rounding Rules

**Buy Quantities** (Fractional to Integer):
```python
def round_buy_qty(qty_raw):
    """
    Round fractional quantity to integer.
    
    Use round-half-up (standard rounding).
    Minimum: 1 unit
    """
    return max(1, round(qty_raw))
```

**Examples**:
```
0.4 → 1 (min 1 unit)
1.5 → 2
2.4 → 2
2.5 → 3 (round-half-up)
5.6 → 6
```

**Sell Quantities** (Percentage to Integer):
```python
def round_sell_qty(position_snapshot, tier_pct):
    """
    Calculate sell quantity from percentage.
    
    Use floor() to never oversell.
    """
    return floor(position_snapshot * tier_pct)
```

**Examples** (Q = 7 units):
```
Tier 1 (50%): floor(7 × 0.5) = 3 units
Tier 2 (remaining): 7 - 3 = 4 units
```

### 6.4 Hard Constraints

**Per-Stock Maximum**:
```python
max_units_per_stock = ceil(0.60 * N)

# Before any buy:
if units_held >= max_units_per_stock:
    cancel_buy("Position at concentration limit")
```

**Portfolio Maximum**:
```python
# Before any buy:
total_deployed = sum(stock.units for stock in portfolio)
if total_deployed >= N:
    cancel_buy("Portfolio fully deployed")
```

**Capacity Check**:
```python
def check_buy_capacity(stock, buy_qty, N):
    """
    Ensure buy doesn't exceed limits.
    """
    # Per-stock cap
    max_stock = ceil(0.60 * N)
    available_stock = max_stock - stock.units
    
    # Global cap
    total_deployed = sum(s.units for s in portfolio)
    available_global = N - total_deployed
    
    # Actual available capacity
    available = min(available_stock, available_global)
    
    # Adjust buy quantity
    final_qty = min(buy_qty, available)
    
    return final_qty
```

### 6.5 State Persistence

**Per-Stock State** (must persist across restarts):
```python
stock_state = {
    'symbol': 'Samsung',
    'units': 8,
    'avg_cost': 90000.0,
    'V': 1.0,
    'last_buy_date': '2026-01-15',
    'sell_targets': {
        'tier1': {'price': 95175, 'qty': 4, 'filled': False},
        'tier2': {'price': 100350, 'qty': 4, 'filled': False}
    },
    'Q': 8,  # Position snapshot for current sell tiers
}
```

**Global State**:
```python
portfolio_state = {
    'N': 25,
    'unit_size': 2000.0,
    'G': 3.5,
    'updated_at': '2026-01-16',
}
```

**Save to file/database after every action**.

---

## 7. FX Management: Two-Front Doctrine

### 7.1 Division Structure

**We operate two independent divisions**:

**Division KR** (Base currency: KRW):
- Samsung Electronics
- SK hynix
- Idle cash: KRW CMA (Cash Management Account)

**Division US** (Base currency: USD):
- NVIDIA
- Alphabet
- Idle cash: USD RP (Repurchase Agreement) or USD Deposit

**Independence Principle**:
- Each division's performance measured in its own currency
- We do NOT convert daily or automatically
- Currency crossing only when "worth it" (see Traffic Light)

### 7.2 Reference Rate Tracking

**Reference Rate (R_ref)**: Weighted average FX rate of current USD holdings

**Formula**:
```python
def compute_reference_rate(usd_positions):
    """
    Calculate average FX rate of all USD positions.
    """
    total_krw_cost = 0
    total_usd_value = 0
    
    for position in usd_positions:
        total_krw_cost += position.cost_krw
        total_usd_value += position.value_usd
    
    if total_usd_value == 0:
        return current_spot_rate  # No USD holdings, use spot
    
    return total_krw_cost / total_usd_value
```

**Example**:
```
NVIDIA: Bought 5 units worth $10,000 when FX = 1,450
  → Cost: 14,500,000 KRW

Alphabet: Bought 3 units worth $6,000 when FX = 1,480
  → Cost: 8,880,000 KRW

R_ref = (14,500,000 + 8,880,000) / (10,000 + 6,000)
      = 23,380,000 / 16,000
      = 1,461.25
```

### 7.3 Traffic Light Protocol

**Threshold**: ±2% from R_ref

**Decision Matrix**:

| Current FX | Condition | US → KR (Repatriate) | KR → US (Reinforce) |
|-----------|-----------|---------------------|-------------------|
| High | FX > R_ref + 2% | 🟢 **GREEN**<br>Sell USD profits<br>(Realize currency gain) | 🔴 **RED**<br>Don't buy USD<br>(Too expensive) |
| Neutral | \|FX - R_ref\| ≤ 2% | 🟡 **YELLOW**<br>Hold USD<br>(Only repatriate realized profits) | 🟡 **YELLOW**<br>Hold KRW<br>(Only send if opportunity critical) |
| Low | FX < R_ref - 2% | 🔴 **RED**<br>Don't sell USD<br>(Locks in FX loss) | 🟢 **GREEN**<br>Buy USD<br>(Favorable rate) |

**Example** (R_ref = 1,460):
```
Current FX = 1,490 (High, +2.05%)

Signals:
  US → KR: 🟢 GREEN
    → If you close NVIDIA position with profit, convert to KRW now
    → Benefit: Stock profit + currency profit
  
  KR → US: 🔴 RED
    → Don't start new US positions now
    → USD is expensive, wait for better FX

---

Current FX = 1,455 (Neutral, -0.34%)

Signals:
  US → KR: 🟡 YELLOW
    → Hold USD in RP, don't convert just to park in KRW
    → Only convert if you have specific KR opportunity
  
  KR → US: 🟡 YELLOW
    → Hold KRW in CMA
    → Only send to US if stock opportunity is compelling

---

Current FX = 1,425 (Low, -2.40%)

Signals:
  US → KR: 🔴 RED
    → Don't close profitable US positions
    → Converting now = ~2.4% FX loss
  
  KR → US: 🟢 GREEN
    → Good time to deploy KRW to US division
    → USD is "on sale"
```

### 7.4 Idle Cash Management

**When division is not fully deployed**:

**Division US** (USD idle cash):
- **Primary**: USD RP (Repurchase Agreement, ~4-5% yield)
- **Alternative**: USD Money Market Fund or High-Yield Savings
- **Never**: Convert to KRW just to earn KRW CMA rates (loses FX optionality)

**Division KR** (KRW idle cash):
- **Primary**: KRW CMA (Cash Management Account, ~3-4% yield)
- **Alternative**: Short-term KRW bonds or MMF

**Rationale**: Preserve currency positioning, earn safe returns while waiting for stock opportunities.

---

## 8. Examples & Code Reference

### 8.1 Complete Campaign Example

**Scenario**: Samsung campaign from LOAD through RESCUE to EXIT

**Initial Conditions**:
```
N = 25 units
G = 3.5 (Bullish AI sector)
L = 4.0 (Samsung strong, but checking extension)
V = 1.0 (Normal volatility)
f_global = 0.32 (8 units deployed across other stocks)
```

**Phase 1: LOAD**

```
Day 1:
  High5 = 88,000 (highest of past 5 days)
  LowToday = 84,500
  
  Calculate LOAD trigger:
    T = (3×4.0 + 2×3.5) / 5 = 3.8
    Drop_load = 6.0 - 0.6×3.8 + 0.5×1.0 = 4.22%
    Trigger = 88,000 × (1 - 0.0422) = 84,286
  
  Check: 84,500 > 84,286 → No LOAD
  
Day 2:
  High5 = 88,000 (unchanged)
  LowToday = 84,000
  
  Check: 84,000 ≤ 84,286 → LOAD FIRES ✓
  
  Action:
    Buy 1 unit @ 84,000
    units = 1, avg_cost = 84,000
```

**Phase 2: RESCUE Sequence**

```
Day 5:
  Price drops, LowToday = 80,600
  
  Current state: units=1, avg=84,000
  Gear: u1=3, units=1 ≤ 3 → Gear 1 (-4%, r=0.5)
  
  Calculate RESCUE trigger:
    Trigger = 84,000 × 0.96 = 80,640
  
  Check: 80,600 ≤ 80,640 → RESCUE FIRES ✓
  
  Action:
    buy_qty = max(1, round(1 × 0.5)) = 1
    Buy 1 unit @ 80,600
    New avg = (84,000 + 80,600) / 2 = 82,300
    units = 2

Day 8:
  Price drops, LowToday = 78,900
  
  Current state: units=2, avg=82,300
  Gear: units=2 ≤ 3 → Still Gear 1
  
  Trigger = 82,300 × 0.96 = 79,008
  
  Check: 78,900 ≤ 79,008 → RESCUE FIRES ✓
  
  Action:
    buy_qty = max(1, round(2 × 0.5)) = 1
    Buy 1 unit @ 78,900
    New avg = (82,300×2 + 78,900) / 3 = 81,167
    units = 3

Day 11:
  Price drops, LowToday = 77,800
  
  Current state: units=3, avg=81,167
  Gear: units=3 ≤ 3 → Still Gear 1 (at threshold)
  
  Trigger = 81,167 × 0.96 = 77,920
  
  Check: 77,800 ≤ 77,920 → RESCUE FIRES ✓
  
  Action:
    buy_qty = max(1, round(3 × 0.5)) = 2 (rounds 1.5)
    Buy 2 units @ 77,800
    New avg = (81,167×3 + 77,800×2) / 5 = 79,900
    units = 5

Day 15:
  Price drops, LowToday = 75,900
  
  Current state: units=5, avg=79,900
  Gear: u1=3, u2=7, units=5 → Gear 2 (-5%, r=0.6)
  
  Trigger = 79,900 × 0.95 = 75,905
  
  Check: 75,900 ≤ 75,905 → RESCUE FIRES ✓
  
  Action:
    buy_qty = max(1, round(5 × 0.6)) = 3
    Buy 3 units @ 75,900
    New avg = (79,900×5 + 75,900×3) / 8 = 78,350
    units = 8

Position Summary After RESCUE:
  Total: 8 units @ avg 78,350
  Sequence: 1+1+1+2+3 = 8 units
  Drawdown from LOAD: (78,350 - 84,000) / 84,000 = -6.73%
```

**Phase 3: SELL**

```
Day 20:
  Price rallies, HighToday = 82,000
  
  Update deployment:
    f_global = (8×78,350 + other positions) / (25×unit_size)
    Assume f_global = 0.48 (now medium deployment)
  
  Calculate sell gear:
    T = (3×4.0 + 2×3.5) / 5 = 3.8
    P = -3 × (0.48 - 0.4) / 0.6 = -0.4
    g = clamp(3.8 - 0.4, 0, 5) = 3.4
    s = 1 + 3.4 = 4.4%
  
  Calculate targets:
    Q = 8 (position snapshot)
    Tier 1 = 78,350 × (1 + 1.25×4.4/100) = 82,634
    Tier 2 = 78,350 × (1 + 2.50×4.4/100) = 86,968
  
  Check: 82,000 < 82,634 → No sell yet

Day 22:
  HighToday = 83,100
  
  Check: 83,100 ≥ 82,634 → TIER 1 FIRES ✓
  
  Action:
    Sell floor(8 × 0.5) = 4 units @ ~82,700
    units = 4 remaining
    avg_cost = 78,350 (unchanged)

Day 28:
  HighToday = 87,500
  
  Check: 87,500 ≥ 86,968 → TIER 2 FIRES ✓
  
  Action:
    Sell remaining 4 units @ ~87,100
    units = 0 → Campaign complete

Profit Analysis:
  Total cost: 78,350 × 8 = 626,800
  Total proceeds: 82,700×4 + 87,100×4 = 679,200
  Profit: 52,400
  Return: 52,400 / 626,800 = 8.36%
```

### 8.2 Code Template (Python)

```python
from dataclasses import dataclass
from typing import Optional
from math import ceil, floor
from datetime import date

@dataclass
class Stock:
    """State for one stock campaign."""
    symbol: str
    units: int = 0
    avg_cost: float = 0.0
    V: float = 1.0
    last_buy_date: Optional[date] = None
    sell_targets: dict = None
    Q: int = 0
    
    def __post_init__(self):
        if self.sell_targets is None:
            self.sell_targets = {}

@dataclass
class Portfolio:
    """Global portfolio state."""
    N: int = 25
    unit_size: float = 2000.0
    G: float = 3.0
    stocks: dict = None
    
    def __post_init__(self):
        if self.stocks is None:
            self.stocks = {}
    
    @property
    def f_global(self):
        """Calculate global deployment ratio."""
        total_value = sum(
            s.units * s.avg_cost 
            for s in self.stocks.values() 
            if s.units > 0
        )
        total_capacity = self.N * self.unit_size
        return total_value / total_capacity if total_capacity > 0 else 0.0

def compute_load_trigger(high_5d: float, T: float, V: float) -> float:
    """Calculate LOAD trigger price."""
    drop_load_pct = 6.0 - 0.6 * T + 0.5 * V
    drop_load_pct = max(3.0, min(7.0, drop_load_pct))
    return high_5d * (1 - drop_load_pct / 100)

def get_rescue_gear(units_held: int, N: int) -> tuple[float, float]:
    """Determine RESCUE gear (drop%, r) based on position."""
    u1 = ceil(0.10 * N)
    u2 = ceil(0.25 * N)
    
    if units_held <= u1:
        return 4.0, 0.5
    elif units_held <= u2:
        return 5.0, 0.6
    else:
        return 6.0, 0.7

def compute_rescue_trigger(avg_cost: float, units_held: int, N: int) -> tuple[float, int]:
    """
    Calculate RESCUE trigger and buy quantity.
    
    Returns: (trigger_price, buy_qty)
    """
    drop_pct, r = get_rescue_gear(units_held, N)
    trigger_price = avg_cost * (1 - drop_pct / 100)
    
    buy_qty_raw = units_held * r
    buy_qty = max(1, round(buy_qty_raw))
    
    # Cap at available capacity
    max_units_stock = ceil(0.60 * N)
    available = max_units_stock - units_held
    buy_qty = min(buy_qty, available)
    
    return trigger_price, buy_qty

def compute_sell_gear(G: float, L: float, f_global: float) -> float:
    """Calculate sell step percentage."""
    T = (3 * L + 2 * G) / 5
    
    if f_global <= 0.4:
        P = 0.0
    else:
        P = -3.0 * (f_global - 0.4) / 0.6
    
    g_raw = T + P
    g = max(0.0, min(5.0, g_raw))
    g = round(g * 10) / 10  # Quantize
    
    s = 1.0 + g
    return s

def compute_sell_targets(avg_cost: float, s: float) -> dict:
    """Calculate 2-tier sell targets."""
    return {
        'tier1': {
            'price': avg_cost * (1 + 1.25 * s / 100),
            'pct': 0.50
        },
        'tier2': {
            'price': avg_cost * (1 + 2.50 * s / 100),
            'pct': 1.00  # Remaining
        }
    }

def check_load(stock: Stock, high_5d: float, low_today: float, 
               T: float, portfolio: Portfolio) -> Optional[dict]:
    """
    Check if LOAD should trigger.
    
    Returns action dict or None.
    """
    if stock.units > 0:
        return None  # LOAD only when flat
    
    trigger_price = compute_load_trigger(high_5d, T, stock.V)
    
    if low_today <= trigger_price:
        return {
            'mode': 'LOAD',
            'qty': 1,
            'trigger_price': trigger_price
        }
    
    return None

def check_rescue(stock: Stock, low_today: float, 
                 current_price: float, portfolio: Portfolio) -> Optional[dict]:
    """
    Check if RESCUE should trigger.
    
    Returns action dict or None.
    """
    if stock.units == 0:
        return None  # Not in campaign
    
    if current_price >= stock.avg_cost:
        return None  # Not underwater
    
    trigger_price, buy_qty = compute_rescue_trigger(
        stock.avg_cost, stock.units, portfolio.N
    )
    
    if low_today <= trigger_price and buy_qty > 0:
        return {
            'mode': 'RESCUE',
            'qty': buy_qty,
            'trigger_price': trigger_price
        }
    
    return None

def check_sells(stock: Stock, high_today: float) -> list[dict]:
    """
    Check which sell tiers have triggered.
    
    Returns list of sell actions.
    """
    actions = []
    
    if not stock.sell_targets or stock.units == 0:
        return actions
    
    for tier_name, tier_data in stock.sell_targets.items():
        if tier_data.get('filled'):
            continue
        
        if high_today >= tier_data['price']:
            if tier_name == 'tier1':
                qty = floor(stock.Q * tier_data['pct'])
            else:  # tier2
                qty = stock.units  # Sell all remaining
            
            actions.append({
                'tier': tier_name,
                'qty': qty,
                'target_price': tier_data['price']
            })
    
    return actions

def execute_buy(stock: Stock, action: dict, execution_price: float,
                today: date, portfolio: Portfolio):
    """Execute buy action and update state."""
    qty = action['qty']
    
    # Update average cost
    old_cost = stock.avg_cost * stock.units
    new_cost = execution_price * qty
    stock.units += qty
    stock.avg_cost = (old_cost + new_cost) / stock.units
    
    # Update last action date
    stock.last_buy_date = today
    
    # Update Q (position snapshot for sells)
    stock.Q = stock.units
    
    # Recalculate sell targets
    G = portfolio.G
    L = get_L_score(stock.symbol)  # External function
    s = compute_sell_gear(G, L, portfolio.f_global)
    
    stock.sell_targets = compute_sell_targets(stock.avg_cost, s)
    
    print(f"{today} | {stock.symbol} | {action['mode']} | "
          f"Buy {qty} @ {execution_price:.2f} | "
          f"Position: {stock.units} @ avg {stock.avg_cost:.2f}")

def execute_sell(stock: Stock, action: dict, execution_price: float, today: date):
    """Execute sell action and update state."""
    qty = action['qty']
    
    # Update position
    stock.units -= qty
    
    # Mark tier as filled
    stock.sell_targets[action['tier']]['filled'] = True
    
    # If fully exited, reset campaign
    if stock.units == 0:
        stock.avg_cost = 0.0
        stock.sell_targets = {}
        stock.Q = 0
    
    print(f"{today} | {stock.symbol} | SELL {action['tier']} | "
          f"Sell {qty} @ {execution_price:.2f} | "
          f"Remaining: {stock.units}")

# Daily execution loop
def daily_execution(portfolio: Portfolio, today: date, market_data: dict):
    """
    Main execution loop (call once per trading day).
    
    market_data: {
        'Samsung': {'high_5d': ..., 'low': ..., 'high': ..., 'close': ...},
        'NVIDIA': {...},
        ...
    }
    """
    for symbol, stock in portfolio.stocks.items():
        data = market_data[symbol]
        
        # 1. Check sells first
        if stock.units > 0:
            sell_actions = check_sells(stock, data['high'])
            for action in sell_actions:
                execute_sell(stock, action, data['close'], today)
        
        # 2. Check buys
        if stock.units == 0:
            # LOAD mode
            T = compute_trend(portfolio.G, get_L_score(symbol))
            action = check_load(stock, data['high_5d'], data['low'], 
                              T, portfolio)
            if action:
                execute_buy(stock, action, data['close'], today, portfolio)
        
        elif stock.units > 0 and data['close'] < stock.avg_cost:
            # RESCUE mode
            action = check_rescue(stock, data['low'], data['close'], portfolio)
            if action:
                execute_buy(stock, action, data['close'], today, portfolio)

# Helper functions (to be implemented)
def get_L_score(symbol: str) -> float:
    """Retrieve current L score for stock (from database or manual input)."""
    # Implementation: query database or return manual score
    pass

def compute_trend(G: float, L: float) -> float:
    """Calculate Trend score T."""
    return (3 * L + 2 * G) / 5
```

### 8.3 Simulation Example

```python
# Initialize
portfolio = Portfolio(N=25, unit_size=2000, G=3.5)
portfolio.stocks = {
    'Samsung': Stock(symbol='Samsung', V=1.0),
    'SK hynix': Stock(symbol='SK hynix', V=2.0),
    'NVIDIA': Stock(symbol='NVIDIA', V=1.0),
    'Alphabet': Stock(symbol='Alphabet', V=0.5),
}

# Simulate campaign
market_data_sequence = [
    # Day 1: LOAD trigger
    {'Samsung': {'high_5d': 88000, 'low': 84000, 'high': 84500, 'close': 84200}},
    
    # Day 5: RESCUE trigger
    {'Samsung': {'high_5d': 88000, 'low': 80600, 'high': 81200, 'close': 81000}},
    
    # Day 8: RESCUE trigger
    {'Samsung': {'high_5d': 88000, 'low': 78900, 'high': 79500, 'close': 79200}},
    
    # Day 22: Tier 1 sell
    {'Samsung': {'high_5d': 88000, 'low': 82000, 'high': 83100, 'close': 82800}},
    
    # Day 28: Tier 2 sell
    {'Samsung': {'high_5d': 88000, 'low': 86500, 'high': 87500, 'close': 87200}},
]

# Run simulation
from datetime import datetime, timedelta

start_date = datetime(2026, 1, 1).date()

for day_offset, data in enumerate(market_data_sequence):
    today = start_date + timedelta(days=day_offset)
    daily_execution(portfolio, today, data)
    print(f"--- End of {today} ---\n")
```

---

## 9. Version History

### v1.0 (Conceptual Foundation)
- Introduced Seesaw concept
- Fixed buy/sell gears
- Army structure and unit system

### v1.1 (Strategic Selling)
- Introduced G/L Committee
- Continuous sell gear calculation
- Deployment penalty mechanism

### v1.2 (Systematic Buying)
- Added LOAD/RELOAD/RESCUE distinction
- Entry threshold formula (T/V based)
- Peak consumption mechanism

### v1.3 (Dynamic Transmission)
- V-Transmission gearbox (position-adaptive RESCUE)
- Removed RELOAD (simplified to LOAD + RESCUE)
- Conditional tier structure (2-tier vs 3-tier based on s)
- FX Traffic Light protocol

### v1.4.0 (Unification Update) - Current
**Major Changes**:
1. **Unified 2-Tier Selling**: All scenarios use (1.25s, 2.5s) multipliers
   - Eliminates zombie problem completely
   - Preserves profit floor vs old 3-tier system
   - Simpler logic, faster rotation

2. **Adaptive LOAD Formula**: Drop_load = 6.0 - 0.6T + 0.5V
   - Trend-responsive entry (bullish → easier, bearish → harder)
   - Volatility provides minor adjustment
   - Range: [3.0%, 7.0%]

3. **Complete Documentation**: Self-contained manual
   - All terminology defined
   - Full code examples
   - Execution flow documented

**Status**: Production-ready for gradual automation

---

## 10. Quick Reference Card

### Committee Scores (Update Schedule)
- **G** (Global): Monthly or on macro events
- **L** (Local): Weekly or on stock events (includes extension check)
- **V** (Volatility): Quarterly or on regime change

### Buy Formulas
```
LOAD Drop% = 6.0 - 0.6×T + 0.5×V  [Range: 3-7%]

RESCUE Gears:
  0-10% of N:  -4%, r=0.5
  10-25% of N: -5%, r=0.6
  >25% of N:   -6%, r=0.7
```

### Sell Formulas
```
T = (3L + 2G) / 5
P = -3 × max(0, f-0.4) / 0.6
s = 1 + clamp(T + P, 0, 5)

Tier 1: avg × (1 + 1.25s%)  [Sell 50%]
Tier 2: avg × (1 + 2.50s%)  [Sell 50%]
```

### Hard Limits
- Max per stock: 60% of N
- Max portfolio: 100% of N (all deployed)
- One buy per stock per day

### FX Triggers
- High (>R_ref + 2%): Repatriate USD ✓
- Low (<R_ref - 2%): Reinforce USD ✓
- Neutral: Hold position

---

**End of Manual v1.4.0**
