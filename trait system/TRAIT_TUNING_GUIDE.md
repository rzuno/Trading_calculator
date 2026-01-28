# Point-Based Trait System - Tuning Guide

## 🎯 System Architecture

```
Traits (active) → Points → Scaling Ratio → Gear Shift → Final Gear

Example:
Active: Rocket Fuel (-12 buy, +15 sell) + High Conviction (-6 buy, +7 sell)
Points: Buy -18, Sell +22
Ratio: 10:1
Shift: Buy -1.8, Sell +2.2
Base: 3.0, 3.0
Final: 1.2, 5.0 (clamped to 1.0, 5.0)
```

---

## 📊 Point Tier System

### **Major Traits (±10 to ±20 points)**
Rare, extreme conditions that should dramatically shift gears

**Examples:**
- Black Swan: +15 buy, -20 sell (crisis mode)
- FOMO Frenzy: -15 buy, +20 sell (euphoria)
- Rocket Fuel: -12 buy, +15 sell (strong rally)
- Falling Knife: +12 buy, -15 sell (steep drop)

**When to use:** Market regime changes, crisis events, parabolic moves

---

### **Medium Traits (±4 to ±8 points)**
Common conditions that warrant gear adjustment

**Examples:**
- Raging Bull: -8 buy, +12 sell (bull market)
- Hard Shaker: +5 buy, +4 sell (high volatility)
- Heavy Artillery: +3 buy, -6 sell (heavy deployment)
- Cash Cow: -6 buy, +8 sell (big profit)

**When to use:** Trend changes, volatility shifts, position size effects

---

### **Minor Traits (±1 to ±3 points)**
Subtle adjustments, fine-tuning

**Examples:**
- Wild Mustang: +2 buy, +1 sell (mild volatility)
- Battle Weary: +3 buy, +3 sell (psychological)
- Oversold RSI: -3 buy, -2 sell (technical)
- FX Neutral: 0 buy, 0 sell (placeholder)

**When to use:** Technical signals, psychological adjustments, neutral states

---

## ⚙️ Scaling Ratio Guide

The scaling ratio controls **how reactive** the system is to trait points.

### Formula:
```
Gear Shift = Total Points / Scaling Ratio
```

### Ratio Settings:

| Ratio | Reactivity | Use Case | Example |
|-------|-----------|----------|---------|
| **5:1** | Very High | Day trading, scalping | 10 points = +2 gears |
| **7:1** | High | Aggressive swing trading | 14 points = +2 gears |
| **10:1** | **Default** | **Balanced trading** | **10 points = +1 gear** |
| **12:1** | Low | Conservative position trading | 12 points = +1 gear |
| **15:1** | Very Low | Buy & hold, low turnover | 15 points = +1 gear |
| **20:1** | Ultra Low | Barely moves, manual override heavy | 20 points = +1 gear |

### How to Choose:

**Start with 10:1 (default)** and adjust based on observation:

```python
# If gears swing too wildly (1 → 5 → 2 → 4):
engine.set_scaling_ratio(buy_ratio=15, sell_ratio=15)

# If gears barely move (stuck at 3 always):
engine.set_scaling_ratio(buy_ratio=7, sell_ratio=7)

# Asymmetric (conservative buy, aggressive sell):
engine.set_scaling_ratio(buy_ratio=12, sell_ratio=8)
```

---

## 🔧 Trait Point Balancing

### Balancing Principle:
**Opposing traits should roughly cancel out**

Good balance:
```
Raging Bull: -8 buy, +12 sell
Savage Bear: +8 buy, -12 sell
→ Cancels perfectly in neutral market
```

Bad balance:
```
Bull trait: -5 buy, +10 sell
Bear trait: +8 buy, -7 sell
→ Asymmetric, will bias the system
```

### Calibration Process:

1. **Start with symmetric values** (±same points for opposing traits)
2. **Test on historical data** (see which traits trigger together)
3. **Adjust for bias** (if you notice consistent over-buying or over-selling)

---

## 📝 JSON Configuration Tips

### Structure:
```json
{
  "id": "rocket_fuel",           // Unique identifier
  "name": "Rocket Fuel",          // Display name
  "category": "Trend",            // Grouping
  "tier": "major",                // major/medium/minor
  "auto": true,                   // Auto-detect or manual?
  "points": {
    "buy": -12,                   // Points for buy gear
    "sell": 15                    // Points for sell gear
  },
  "trigger": {                    // Auto-detection logic
    "type": "threshold",
    "metric": "roc",
    "condition": ">",
    "value": 15.0
  },
  "description": "Strong rally"
}
```

### Easy Modifications:

**Change point values:**
```json
// Before:
"points": {"buy": -12, "sell": 15}

// After (nerf):
"points": {"buy": -10, "sell": 12}
```

**Change trigger threshold:**
```json
// Before:
"value": 15.0  // Triggers at ROC > 15%

// After (more sensitive):
"value": 12.0  // Triggers at ROC > 12%
```

**Add new trait:**
```json
{
  "id": "cup_and_handle",
  "name": "Cup & Handle",
  "category": "Technical",
  "tier": "medium",
  "auto": false,
  "points": {"buy": -5, "sell": 7},
  "description": "Bullish pattern breakout"
}
```

---

## 🎮 Trait Patching Examples

### Scenario 1: Rocket Fuel Too Aggressive
**Problem:** System goes all-in on every rally  
**Diagnosis:** Rocket Fuel gives too many sell points

```json
// Before:
"rocket_fuel": {"buy": -12, "sell": 15}

// After (patch):
"rocket_fuel": {"buy": -10, "sell": 12}
```

### Scenario 2: Deployment Traits Too Weak
**Problem:** Heavy deployment doesn't force sells  
**Diagnosis:** Deployment traits need more points

```json
// Before:
"heavy_artillery": {"buy": 3, "sell": -6}
"all_in_assault": {"buy": 6, "sell": -12}

// After (buff):
"heavy_artillery": {"buy": 4, "sell": -8}
"all_in_assault": {"buy": 8, "sell": -15}
```

### Scenario 3: FX Traits Ignored
**Problem:** FX changes don't affect decisions  
**Diagnosis:** FX points too small

```json
// Before:
"fx_tailwind": {"buy": -4, "sell": 6}

// After (major impact):
"fx_tailwind": {"buy": -6, "sell": 10}
```

### Scenario 4: Gears Too Jumpy
**Problem:** Gear swings 1 → 5 → 2 too often  
**Diagnosis:** Too many major traits active at once

**Solutions:**
1. Reduce major trait points
2. Increase scaling ratio
3. Make some traits mutually exclusive

```python
# Option 1: Nerf major traits
rocket_fuel: -12 → -10
falling_knife: +12 → +10

# Option 2: Increase ratio
engine.set_scaling_ratio(15, 15)  # Was 10

# Option 3: Logic
if 'rocket_fuel' in active and 'crazy_dancer' in active:
    # Reduce crazy_dancer effect when already trending
    crazy_dancer_points *= 0.5
```

---

## 🧪 Testing Strategy

### Phase 1: Paper Testing (2 weeks)
```python
# For each trading day:
1. Calculate gears from traits
2. Record: active traits, points, final gears
3. Compare vs manual judgment
4. Note: "Would I have used this gear?"
```

### Phase 2: Trait Frequency Analysis
```python
# After 2 weeks:
- Which traits activated most? (High frequency)
- Which traits never activated? (Remove or adjust threshold)
- Which combos appear together? (Check for conflicts)
```

### Phase 3: Point Tuning
```python
# Adjust based on patterns:
- Overpowered traits → Reduce points
- Underpowered traits → Increase points
- Conflicting traits → Make mutually exclusive or adjust
```

### Phase 4: Scaling Ratio Optimization
```python
# If gears are:
- Too stable (always 3): Reduce ratio (10→7)
- Too jumpy (1-5 swing): Increase ratio (10→15)
- Biased (always high): Check trait balance
```

---

## 📊 Sample Trait Combinations

### Conservative Bear Market Setup
```
Active:
- Savage Bear (+8 buy, -12 sell)
- Falling Knife (+12 buy, -15 sell)
- Heavy Artillery (+3 buy, -6 sell)
- Low Conviction (+6 buy, -7 sell)

Points: +29 buy, -40 sell
Ratio: 10:1
Result: Buy 5.0 (maxed), Sell 1.0 (minimal)
```

### Aggressive Bull Market Setup
```
Active:
- Raging Bull (-8 buy, +12 sell)
- Rocket Fuel (-12 buy, +15 sell)
- Empty Barracks (-3 buy, -5 sell)
- High Conviction (-6 buy, +7 sell)

Points: -29 buy, +29 sell
Ratio: 10:1
Result: Buy 1.0 (easy entry), Sell 5.0 (aggressive exit)
```

### Balanced Consolidation
```
Active:
- Sideways Shuffle (0, 0)
- Steady Eddie (0, 0)
- Standard Formation (0, 0)
- Neutral Zone (0, 0)

Points: 0 buy, 0 sell
Result: Buy 3.0, Sell 3.0 (all default)
```

---

## 🚨 Common Pitfalls

### ❌ Pitfall 1: Too Many Major Traits
**Problem:** Every situation has a major trait active  
**Solution:** Reserve major (±10+) for truly rare events

### ❌ Pitfall 2: Asymmetric Pairs
**Problem:** Bull (+5 sell) vs Bear (-10 sell) → Permanent sell bias  
**Solution:** Make opposing traits symmetric

### ❌ Pitfall 3: Scaling Ratio Too Aggressive
**Problem:** 5:1 ratio makes gears swing wildly  
**Solution:** Start at 10:1, tune gradually

### ❌ Pitfall 4: Redundant Traits
**Problem:** 3 volatility traits active at once  
**Solution:** Make them mutually exclusive

### ❌ Pitfall 5: Ignoring Clamping
**Problem:** Points add to +100, but gear clamped at 5.0 anyway  
**Solution:** Don't overstack points (diminishing returns)

---

## ✅ Best Practices

1. **Start simple** - Enable 10-15 core traits first
2. **One change at a time** - Don't patch 5 traits at once
3. **Track everything** - Log active traits + results
4. **Seasonal tuning** - Market regimes change, traits should too
5. **Version control** - Keep old configs (`traits_v1.json`, `traits_v2.json`)

---

## 🎯 Quick Reference: Trait Effect Guidelines

| Situation | Buy Points | Sell Points | Logic |
|-----------|------------|-------------|-------|
| **Strong Rally** | -10 to -15 | +12 to +20 | Easy entry, aggressive exit |
| **Strong Drop** | +10 to +15 | -12 to -20 | Deep entry, quick exit |
| **High Volatility** | +5 to +8 | +4 to +6 | Wider spreads both ways |
| **Low Volatility** | -3 to -5 | -3 to -5 | Tighter spreads both ways |
| **Heavy Deployment** | +3 to +8 | -6 to -15 | Block buys, force sells |
| **Light Deployment** | -3 to -5 | -3 to -5 | Encourage entry |
| **Big Profit** | -5 to -8 | +6 to +10 | Let winners run, but take some |
| **Big Loss** | +3 to +5 | -5 to -8 | Cautious entry, patient hold |

---

## 🔄 Iterative Improvement Loop

```
Week 1: Deploy with default config
  ↓
Week 2: Analyze trait frequencies
  ↓
Week 3: Patch overpowered/underpowered traits
  ↓
Week 4: Tune scaling ratio
  ↓
Week 5: Add custom traits based on patterns
  ↓
Week 6: Remove unused traits
  ↓
Repeat every month
```

---

**The point system gives you a TUNABLE CONTROL PANEL instead of a black box formula!**
