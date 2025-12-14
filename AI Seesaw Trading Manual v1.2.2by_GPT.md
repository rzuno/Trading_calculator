# AI Seesaw Trading Manual v1.2.2
**Seesaw System: Continuous Sell Gear + Simplified High/Low Buy Mechanics**

---

## 0. What changed in v1.2.2

- Keeps **v1.1 sell gear** (continuous sell step `s = 1 + g`, ladder `+s, +2s, +3s`).
- Keeps **v1.0 rescue layering** (Agile/Heavy/Greedy/Cautious buy models).
- Replaces the v1.2 “T/V entry formula” with a **simple 5‑day peak drawdown rule** for **Load** and **Reload**.
- Uses **High/Low** (not Close) as the practical execution reference:
  - Buy triggers by **Low ≤ buy_price**.
  - Sell triggers by **High ≥ sell_price**.

---

## 1. Core objects

Per stock (one “campaign” at a time):

- `N_units`: max units reserved for this stock (e.g., 25).
- `units_held`: current units held.
- `A`: average cost of the current position (updates after every buy).

Global:

- `C_max`: shared max capital (one number used across all stocks).
- `f_global`: global deployed fraction (how loaded you are overall).

---

## 2. Committee scores (G/L/V)

- `G ∈ [0,5]`: global AI sector environment.
- `L ∈ [0,5]`: local/stock-specific environment.
- `V ∈ [0,2]`: volatility record (kept as metadata; **not used in buy rules in v1.2.2**).

Trend score:

- `T = (3*L + 2*G) / 5`  (range 0..5)

In v1.2.2:

- **Sell gear uses T** (and global deployment penalty).
- **Buy triggers (Load/Reload) do NOT use T/V**. They are purely mechanical.

---

## 3. Sell mechanism (continuous gear, 3-tier)

### 3.1 Global deployment penalty

Let `f = f_global ∈ [0,1]`.

- If `f ≤ 0.4`: `P(f) = 0`
- If `f > 0.4`: `P(f) = -3 * (f - 0.4) / 0.6`

So `P(f)` ranges from `0` down to `-3`.

### 3.2 Gear index

- `g_raw = T + P(f)`
- `g = clamp(g_raw, 0, 5)`
- Quantize `g` to 0.1 if you want cleaner numbers on your trading screen.

### 3.3 Profit step and ladder

- `s = 1 + g`   (so `s` ranges 1% .. 6%)

From average cost `A`, the sell levels are:

- Tier 1 target: `A * (1 + s/100)`
- Tier 2 target: `A * (1 + 2s/100)`
- Tier 3 target: `A * (1 + 3s/100)`

Chunk sizes (default):

- Tier 1: sell 50% of current position
- Tier 2: sell 25% of original position (i.e., 50% of remaining)
- Tier 3: sell last 25%

Execution reference:

- Tier sells are considered “hit” when **High ≥ target** (limit orders can fill).

### 3.4 Tier‑3 expiry (anti‑linger bail‑out)

Problem: the last 25% can linger and block reset.

Rule:

- When Tier 2 executes, start a timer = **5 trading days (~1 week)**.
- If Tier 3 did not execute by expiry:
  1) Cancel Tier 3.
  2) Place a sell for the remaining shares at the **Tier 2 target** (limit/GTC).

This keeps the 3-tier structure but prevents residue.

---

## 4. Buy mechanism (v1.2.2)

There are **three buy triggers**:

1) **Load** (start a new position when flat)
2) **Reload** (tactical re-entry while still holding, above average)
3) **Rescue** (average-down compounding when price goes below average)

### 4.1 Shared parameter for Load/Reload

- Window: **5 trading days**
- Constant drawdown trigger: **X = 5%**

Define the “active peak”:

- `Peak5 = highest High during the last 5 trading days, counted **since the most recent Load/Reload**.`
  - After you Load or Reload, you “erase” the previous mountain and start a fresh 5-day peak tracking.

Define the trigger price:

- `P_trigger = Peak5 * (1 - X/100)`

Execution reference:

- A Load/Reload is considered triggered when **Low ≤ P_trigger**.

### 4.2 Trigger 1 — Load (flat entry)

Condition:

- If `units_held == 0` and `Low ≤ P_trigger`:

Action:

- Buy **1 unit** at `P_trigger` (limit).
- Set/refresh `A` (average cost).
- Reset the peak tracking epoch (the “mountain top is erased”).

### 4.3 Trigger 2 — Reload (one per dip, above-average only)

Purpose:

- Reload is for “hovering dips” that happen **above your average cost**, so you can fight more often without risking heavy averaging-up.

Condition:

- If `units_held > 0` AND `current_price ≥ A` AND `Low ≤ P_trigger`:

Action:

- Buy **1 unit** at `P_trigger` (limit).
- Update `A`.
- Reset the peak tracking epoch (this enforces “one reload per dip”).

Notes:

- Because Reload requires `current_price ≥ A`, deep drops naturally switch you into **Rescue** instead of repeated Reloads.

### 4.4 Trigger 3 — Rescue (average-down compounding)

Rescue is your main defensive engine (from v1.0).

Pick **one** rescue model per campaign:

| Model | gear_drop | r | Meaning |
|---|---:|---:|---|
| Agile (default) | 5% | 0.6 | frequent, smooth tracking |
| Heavy | 6% | 0.7 | stronger averaging, deeper support |
| Greedy | 5% | 0.7 | aggressive (use selectively) |
| Cautious | 7% | 0.65 | fewer entries, deeper spacing |

Rescue trigger price:

- `P_rescue = A * (1 - gear_drop/100)`

Condition:

- If `Low ≤ P_rescue`:

Action:

- Buy `r * units_held` (rounded to your platform’s minimum tradable unit).
- Update `A`.
- Repeat on further drops, until you reach `N_units`.

---

## 5. Campaign flow (minimal)

1) Choose `N_units` (e.g., 25).
2) Choose Rescue model (default Agile: `gear_drop=5, r=0.6`).
3) Use **Load/Reload** with `X=5` and `Peak5` (High/Low based).
4) Use sell gear ladder from §3.

---

## 6. Tiny example (logic only)

Assume:

- You sold Tier1 at 105 and Tier2 at 110, and price dips while still above average.
- Active Peak5 = 110, X = 5% → trigger = 110 * 0.95 = 104.5

Sequence:

- Day dip low hits 104.5 → **Reload 1 unit**.
- Peak epoch resets after reload → the old 110 peak is “consumed.”
- If price hovers 103~104~100 but average is near 100, Reload is blocked once price falls below average and **Rescue** takes over.

---

## 7. Versioning note

- v1.2.2 is meant to reduce cognitive load:
  - **Sell remains calculated** (continuous gear).
  - **Buy becomes mechanical** (Peak5 drawdown + Rescue).

