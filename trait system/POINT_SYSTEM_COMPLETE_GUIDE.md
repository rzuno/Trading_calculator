# AI Seesaw Trading v2.0 - Point-Based Trait System  
**The Complete Guide**

---

## 🎯 What You Just Built

You've created a **Fallout-style perk system** for trading that is:

✅ **Transparent** - See exactly why gear changed  
✅ **Tunable** - One master knob (ratio) + individual trait points  
✅ **Patchable** - Edit JSON to buff/nerf traits like game balance  
✅ **Smooth** - Decimal gears (3.4 = 3.4% sell step)  
✅ **Fun** - Cool names with icons 🚀🐻💎  

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TRAIT EVALUATION                          │
│  Each trait = Buy Points + Sell Points                      │
│                                                               │
│  Auto Traits:    Check conditions → Activate if true        │
│  Manual Traits:  Check checkbox → Activate if checked       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   POINT ACCUMULATION                         │
│  Total Buy Points = Σ(all active trait buy_points)          │
│  Total Sell Points = Σ(all active trait sell_points)        │
│                                                               │
│  Example:                                                     │
│   Rocket Fuel: -12 buy, +15 sell                            │
│   High Conviction: -7 buy, +7 sell                          │
│   → Total: -19 buy, +22 sell                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 GEAR SHIFT CALCULATION                       │
│  Buy Shift = Total Buy Points / Point-to-Gear Ratio         │
│  Sell Shift = Total Sell Points / Point-to-Gear Ratio       │
│                                                               │
│  With 10:1 ratio:                                            │
│   Buy Shift = -19 / 10 = -1.9                               │
│   Sell Shift = +22 / 10 = +2.2                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    FINAL GEAR OUTPUT                         │
│  Final Buy Gear = Base (3.0) + Buy Shift (-1.9) = 1.1       │
│  Final Sell Gear = Base (3.0) + Sell Shift (+2.2) = 5.2     │
│                                                               │
│  Clamped to [1.0, 5.0]:                                      │
│   Buy: 1.1 ✓                                                 │
│   Sell: 5.2 → 5.0 (clamped)                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  TRADING THRESHOLDS                          │
│  Buy Gear 1.1 → Entry at -(3 + 2×1.1) = -5.2% from peak    │
│  Sell Gear 5.0 → Profit ladder: 6% / 12% / 18%             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Trait Inventory (45 Traits)

### 🤖 AUTO TRAITS (25 traits) - Calculated from data

| Category | Count | Trigger | Examples |
|----------|-------|---------|----------|
| **Volatility** | 5 | ATR% | Gentle Breeze → Crazy Dancer |
| **Trend** | 5 | ROC | Rocket Fuel → Falling Knife |
| **Deployment** | 6 | Deployed% | Empty Barracks → Maxed Out |
| **P&L** | 4 | Profit% | Deep Underwater → Cash Cow |
| **FX** | 4 | FX vs Avg | Green Light → Premium Zone |
| **Technical** | 1 | Custom | Zombie Position |

### 👤 MANUAL TRAITS (20 traits) - Your judgment

| Category | Count | When to Use | Examples |
|----------|-------|-------------|----------|
| **Market Regime** | 5 | Monthly | Raging Bull → Savage Bear |
| **Events** | 6 | Earnings, news | Beat Street, Product Launch |
| **Special** | 4 | Rare events | Black Swan, FOMO Frenzy, Fed |
| **Conviction** | 5 | Your psychology | High/Low, Diamond/Paper Hands |

---

## 🎮 Point Tier System

### **Major Traits (±8 to ±15 points)**  
Extreme conditions, rare events

```json
"rocket_fuel": {
  "buy_points": -15,
  "sell_points": 12,
  "description": "Strong rally"
}
```

**Examples:**  
- Rocket Fuel: -15 buy, +12 sell  
- Falling Knife: +15 buy, -12 sell  
- Black Swan: +15 buy, -15 sell  
- FOMO Frenzy: -15 buy, +15 sell  

**10:1 ratio → ±1.2 to ±1.5 gear shift alone**

---

### **Moderate Traits (±5 to ±8 points)**  
Common conditions, standard signals

```json
"hard_shaker": {
  "buy_points": 5,
  "sell_points": 3,
  "description": "High volatility"
}
```

**Examples:**  
- Hard Shaker: +5 buy, +3 sell  
- Tailwind: -6 buy, +6 sell  
- Heavy Artillery: +3 buy, -6 sell  
- High Conviction: -7 buy, +7 sell  

**10:1 ratio → ±0.5 to ±0.8 gear shift alone**

---

### **Minor Traits (±1 to ±5 points)**  
Subtle adjustments, fine-tuning

```json
"green_shoots": {
  "buy_points": -2,
  "sell_points": 3,
  "description": "Small profit"
}
```

**Examples:**  
- Gentle Breeze: -3 buy, -5 sell  
- Scout Team: 0 buy, 0 sell  
- Green Shoots: -2 buy, +3 sell  
- Battle Weary: +3 buy, +3 sell  

**10:1 ratio → ±0.2 to ±0.5 gear shift alone**

---

## ⚙️ The Master Knob: Point-to-Gear Ratio

This is your **global sensitivity control**.

### How It Works:

```
Gear Shift = Points / Ratio

Example with +20 sell points:
- Ratio 5:1  → +20/5  = +4.0 gears (VERY reactive)
- Ratio 7:1  → +20/7  = +2.9 gears (Reactive)
- Ratio 10:1 → +20/10 = +2.0 gears (DEFAULT)
- Ratio 15:1 → +20/15 = +1.3 gears (Conservative)
- Ratio 20:1 → +20/20 = +1.0 gear  (Very conservative)
```

### When to Adjust:

**Increase ratio (10→15) if:**
- Gears swing too wildly (1→5→2→4)
- Too many traits trigger at once
- You want slower reactions

**Decrease ratio (10→7) if:**
- Gears barely move (stuck at 3.0)
- Signals feel too weak
- You want faster reactions

**Code:**
```python
engine.set_scaling_ratio(buy_ratio=15, sell_ratio=15)
```

---

## 💡 Real Examples

### Example 1: Samsung Bear Market
```
Stock Data:
  ATR: 5.5% (volatile)
  ROC: -10% (downtrend)
  Deployed: 72% (heavy)
  P&L: -8% (slight loss)

Active Traits:
🟡 Hard Shaker: +5 buy, +3 sell
🟡 Headwind: +6 buy, -7 sell
🟡 Heavy Artillery: +3 buy, -6 sell
👤 Cautious Bear: +4 buy, -5 sell
👤 Battle Weary: +3 buy, +3 sell

Total Points: +21 buy, -12 sell
Ratio: 10:1
Gear Shift: +2.1 buy, -1.2 sell

Final Gears:
  Buy: 3.0 + 2.1 = 5.1 → 5.0 (clamped)
  Sell: 3.0 - 1.2 = 1.8

Meaning:
  Entry: -13% (very defensive)
  Profit: 2.8% / 5.6% / 8.4% (quick exit)
```

### Example 2: NVIDIA Rally
```
Stock Data:
  ATR: 8.5% (crazy volatile)
  ROC: +18% (strong rally)
  Deployed: 15% (light)
  P&L: +22% (big profit)
  FX: +3.5% vs avg (strong dollar)

Active Traits:
🔴 Rocket Fuel: -12 buy, +15 sell
🟡 Crazy Dancer: +10 buy, +5 sell
🟡 Cash Cow: -6 buy, +8 sell
🔴 Raging Bull: -8 buy, +10 sell
🟡 FX Red Light: 0 buy, +6 sell
👤 High Conviction: -7 buy, +7 sell

Total Points: -23 buy, +51 sell
Ratio: 10:1
Gear Shift: -2.3 buy, +5.1 sell

Final Gears:
  Buy: 3.0 - 2.3 = 0.7 → 1.0 (clamped)
  Sell: 3.0 + 5.1 = 8.1 → 5.0 (clamped)

Meaning:
  Entry: -5% (easy entry, catch momentum)
  Profit: 6% / 12% / 18% (aggressive harvest)
```

---

## 🔧 JSON Editing Workflow

### 1. Open `trait_system_v2_points.json`

### 2. Edit Point Values

**Before:**
```json
{
  "id": "raging_bull",
  "buy_points": -8,
  "sell_points": 10
}
```

**After (nerf):**
```json
{
  "id": "raging_bull",
  "buy_points": -6,  // Less aggressive entry
  "sell_points": 8   // Less aggressive exit
}
```

### 3. Edit Trigger Conditions

**Before:**
```json
{
  "id": "rocket_fuel",
  "auto_trigger": "roc > 15"
}
```

**After (more sensitive):**
```json
{
  "id": "rocket_fuel",
  "auto_trigger": "roc > 12"  // Triggers earlier
}
```

### 4. Add New Trait

```json
{
  "id": "gap_up_morning",
  "name": "Gap Up Morning",
  "category": "special",
  "tier": "minor",
  "buy_points": 3,
  "sell_points": 4,
  "auto_trigger": "gap_pct > 2",
  "description": "Pre-market pump",
  "icon": "🌅"
}
```

### 5. Save & Reload

```python
# Python will automatically load the updated JSON
engine = PointBasedTraitEngine('trait_system_v2_points.json')
```

---

## 🎯 FX Trait System (US Stocks Only)

Special category for exchange rate considerations:

```json
{
  "id": "fx_green_light",
  "buy_points": -5,
  "sell_points": 0,
  "auto_trigger": "fx_current < fx_avg * 0.98",
  "description": "USD cheap (-2%), buy opportunity"
}

{
  "id": "fx_red_light",
  "buy_points": 0,
  "sell_points": 6,
  "auto_trigger": "fx_current > fx_avg * 1.02",
  "description": "USD expensive (+2%), sell profit"
}

{
  "id": "fx_premium_zone",
  "buy_points": 3,
  "sell_points": 10,
  "auto_trigger": "fx_current > fx_avg * 1.05",
  "description": "Very strong dollar (+5%), SELL"
}
```

**Calculation:**
```python
fx_avg = 1450  # Your average USD entry rate
fx_current = 1480  # Today's rate
fx_pct = (fx_current / fx_avg - 1) * 100  # +2.07%

# Triggers FX Red Light (+6 sell points)
```

**Logic:**
- **Green Light** (FX < -2%): Dollar weak → Buy US stocks cheap
- **Yellow** (FX ±2%): Normal → No effect
- **Red Light** (FX > +2%): Dollar strong → Sell US stocks, lock in FX profit
- **Premium** (FX > +5%): Very strong → URGENT sell signal

---

## 📋 Integration Checklist

### Phase 1: JSON Setup ✓
- [x] Load `trait_system_v2_points.json`
- [x] Verify all traits
- [x] Set default ratio (10:1)

### Phase 2: Calculator Integration
```python
from point_trait_engine import PointBasedTraitEngine

engine = PointBasedTraitEngine('trait_system_v2_points.json')

# For each stock:
stock_data = {
    'atr_pct': calculate_atr_pct(stock),
    'roc': calculate_roc(stock),
    'deployed_pct': get_deployed_pct(stock),
    'pnl_pct': get_pnl_pct(stock),
    'fx_current': get_fx_rate(),  # US stocks only
    'fx_avg': get_average_fx(),   # US stocks only
}

# Manual traits (from UI checkboxes)
engine.set_manual_trait('raging_bull', True)
engine.set_manual_trait('high_conviction', True)

# Calculate
buy_gear, sell_gear, active_traits, debug = engine.calculate_gears(stock_data)

# Display
print(f"Buy Gear: {buy_gear:.1f}")
print(f"Sell Gear: {sell_gear:.1f}")
print(f"Active Traits: {len(active_traits)}")
```

### Phase 3: UI Design
```
┌─────────────────────────────────────────┐
│ SAMSUNG ELECTRONICS                     │
├─────────────────────────────────────────┤
│ 🤖 AUTO TRAITS (calculated)             │
│ ☑ 📳 Hard Shaker        +5 / +3        │
│ ☑ 🌪️ Headwind          +6 / -7        │
│ ☑ 🎯 Heavy Artillery    +3 / -6        │
│ ☐ 🚀 Rocket Fuel       -12 / +12       │
├─────────────────────────────────────────┤
│ 👤 MANUAL TRAITS (checkboxes)           │
│ ☑ 🐻 Cautious Bear      +4 / -5        │
│ ☑ 😰 Battle Weary       +3 / +3        │
│ ☐ 💪 High Conviction    -7 / +7        │
│ ☐ 🦢 Black Swan        +15 / -15       │
├─────────────────────────────────────────┤
│ 📊 CALCULATION                          │
│ Buy Points: +21 → +2.1 gears            │
│ Sell Points: -12 → -1.2 gears           │
│                                          │
│ Base: 3.0 / 3.0                         │
│ Final: 5.0 / 1.8                        │
│                                          │
│ Entry: -13.0% from 5-day high           │
│ Profit: 2.8% / 5.6% / 8.4%             │
└─────────────────────────────────────────┘
```

### Phase 4: Testing (2 weeks)
- [ ] Log all gear calculations
- [ ] Track which traits activate most
- [ ] Compare auto vs manual judgment
- [ ] Note: "Would I use this gear?"

### Phase 5: Tuning
- [ ] Identify overpowered traits (always maxing gears)
- [ ] Identify underpowered traits (never changing gears)
- [ ] Adjust points in JSON
- [ ] Test new ratio if needed (10→12 or 10→8)

---

## 🚨 Common Scenarios

### "Gears are swinging 1→5→2 too much"

**Diagnosis:** Too reactive  
**Solutions:**
1. Increase ratio: `10:1 → 15:1`
2. Reduce major trait points: `-15 → -12`
3. Remove conflicting traits

### "Gears stuck at 3.0 always"

**Diagnosis:** Not reactive enough  
**Solutions:**
1. Decrease ratio: `10:1 → 7:1`
2. Increase trait points: `+5 → +7`
3. Check if traits are triggering (debug log)

### "FX traits not working"

**Diagnosis:** Only for US stocks  
**Solutions:**
1. Verify `fx_current` and `fx_avg` in stock_data
2. Check KR stocks don't use FX traits
3. Ensure FX calculation: `(current/avg - 1) * 100`

### "Too many traits active at once"

**Diagnosis:** Overlapping conditions  
**Solutions:**
1. Make some traits mutually exclusive
2. Tighten trigger conditions
3. Review tier balance (too many minors?)

---

## 🎮 Trait Patching Strategy

### Week 1-2: Baseline
- Use default points from JSON
- Log everything
- Don't adjust yet

### Week 3: First Patch
```
Observed:
- Rocket Fuel triggers 40% of days → Too often
- Falling Knife only triggers 5% → OK
- Heavy Artillery weak effect → Need buff

Patch:
- Rocket Fuel: roc > 15 → roc > 18 (less frequent)
- Heavy Artillery: +3/-6 → +4/-8 (stronger)
```

### Week 4: Ratio Tuning
```
Observed:
- Even with patches, gears swing 1→4→2
- Too many major traits stacking

Adjust:
- Ratio: 10:1 → 12:1 (reduce sensitivity)
```

### Week 5: Custom Traits
```
Discovered pattern:
- Monday mornings often gap down
- Creates buy opportunity

Add:
{
  "id": "monday_dip",
  "buy_points": -3,
  "sell_points": 0,
  "description": "Monday weakness"
}
```

---

## 📈 Success Metrics

After 1 month, you should see:

✅ **Gear distribution:**
- 30-40% at base (3.0)
- 20-30% at ±1 (2.0-4.0)
- 10-20% at ±2 (1.0-5.0)

✅ **Trait usage:**
- 80%+ auto traits work correctly
- Manual traits used 10-20% of trades
- No unused traits (remove them!)

✅ **Confidence:**
- You understand why each gear changed
- You can explain point totals
- Rare overrides needed

---

## 🎯 Next Steps

1. **Review JSON** - Do all 45 traits make sense?
2. **Plan UI** - Where to show trait checkboxes?
3. **Calculate metrics** - How to get ATR%, ROC, etc?
4. **Test one stock** - Samsung first, full workflow
5. **Iterate** - Adjust points based on results

---

**Files:**
1. `trait_system_v2_points.json` - Complete 45-trait library
2. `point_trait_engine.py` - Working Python implementation  
3. `TRAIT_TUNING_GUIDE.md` - How to adjust points and ratio

**You now have a production-ready trait system!** 🎮📈

This is **WAY more fun and controllable** than fighting with formulas. Time to integrate into your calculator and start checking those boxes! 🚀
