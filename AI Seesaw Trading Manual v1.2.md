# AI Seesaw Trading Manual v1.2  
**Seesaw System: Buy & Sell Gear with G/L/V Committee**

---

## 0. Version & Scope

- **v1.0**
  - Defined Seesaw concept.
  - Army structure and buy layering.
  - Sell gears based only on capital proportion (U) with fixed steps (2/4/6, 3/6/9, …).

- **v1.1**
  - Kept buy/entry from v1.0.
  - Replaced sell mechanism with **continuous sell gear** driven by:
    - Global score G  
    - Local score L  
    - Deployment fraction f

- **v1.2 (this document)**
  - Keeps the **sell mechanism from v1.1**.
  - **Adds a systematic Buy Initiation Gear**:
    - First entry when you hold zero units is triggered by:
      - Trend factor **T** from G & L.
      - Volatility factor **V** (per stock).
      - Local dip from a recent high.
  - Uses the same **G/L committee** idea plus an extra factor **V** for volatility.

> For history: keep v1.0, v1.1, v1.2 all in the project.  
> v1.2 is the current “live spec” (buy + sell), but older versions remain for rollback and comparison.

---

## 1. Basic Objects & Notation

Let:

- \( C_{\max} \): **Shared max capital** (one number used for every stock/campaign).
- \( C_{\text{deployed}} \): Current deployed capital in that stock.
- **Deployment fraction (global)**:
  \[
  f_{\text{global}} = \frac{\sum_i C_{\text{deployed}, i}}{\sum_i C_{\max, i}} \in [0,1]
  \]
- Optional **scaled deployment** (for intuition only):
  \[
  U = 5 \cdot f_{\text{global}} \in [0,5]
  \]

**FX note**: A single FX rate is shared globally. Updating FX anywhere updates the shared rate used for all US valuations.

Per stock we maintain:

- **Global AI sector score**: \( G \in [0,5] \) (float)
- **Local stock score**: \( L \in [0,5] \) (float)
- **Volatility factor**: \( V \in [0,2] \) (float)  
  - Higher V → more volatile → deeper entry triggers.

These are decided by the **G/L/V Committee** (you + AI).

---

## 2. G/L/V Committee Protocol

### 2.1 Scores

- \( G \in [0,5] \): Global AI sector environment.
- \( L \in [0,5] \): Stock-specific environment.
- \( V \in [0,2] \): Volatility factor.

The **Trend** score used on both buy and sell side is:

\[
T = \frac{3L + 2G}{5} \in [0,5]
\]

- Local L weight 3 (60%)
- Global G weight 2 (40%)

### 2.2 Committee workflow

For each stock:

1. **AI proposes**:
   - A G proposal in [0,5] from macro + sector + narrative.
   - An L proposal in [0,5] from chart + relative performance + company news.
   - A V proposal in [0,2] from its volatility profile (e.g. beta, typical daily range).
2. **You review & finalize**:
   - Choose \( G_{\text{final}}, L_{\text{final}}, V_{\text{final}} \).  
   - These are the values fed into the gear formulas.

You don’t need to worry about the AI’s internal weighting; you only decide whether to accept or tweak the proposed numbers.

---

## 3. Sell Mechanism (v1.1 – Continuous Sell Gear)

### 3.1 Inputs

At any moment:

- \( G \in [0,5] \)
- \( L \in [0,5] \)
- **Global deployment fraction** \( f_{\text{global}} \in [0,1] \)
  - Uses the single shared \( C_{\max} \) for all stocks.

Compute Trend:

\[
T = \frac{3L + 2G}{5}
\]

### 3.2 Deployment penalty (global)

Heavier **global** deployment → more conservative sell gear across every stock.

Define penalty \( P(f_{\text{global}}) \):

- If \( f_{\text{global}} \le 0.4 \):  
  \[
  P(f) = 0
  \]
- If \( f_{\text{global}} > 0.4 \):  
  \[
  P(f) = -3 \cdot \frac{f_{\text{global}} - 0.4}{0.6}
  \]

So:

- \( f_{\text{global}} = 0.6 \Rightarrow P \approx -1 \)  
- \( f_{\text{global}} = 0.8 \Rightarrow P \approx -2 \)  
- \( f_{\text{global}} = 1.0 \Rightarrow P = -3 \)

### 3.3 Gear index and clamping

Raw gear:

\[
g_{\text{raw}} = T + P(f_{\text{global}})
\]

Clamp to \([0,5]\):

\[
g = \min\bigl(5,\ \max(0,\ g_{\text{raw}})\bigr)
\]

Optional 0.1 quantization:

\[
g := \frac{\text{round}(10 \cdot g)}{10}
\]

### 3.4 From gear to ladder

Base step:

\[
s = 1 + g
\]

So:

- \( g = 0 \Rightarrow s = 1\% \)
- \( g = 5 \Rightarrow s = 6\% \)

Automatic sell ladder:

- **Tier 1**: sell first chunk at **\(+s\%\)**  
- **Tier 2**: sell next chunk at **\(+2s\%\)**  
- **Tier 3**: sell final chunk at **\(+3s\%\)**  

(Chunk sizes e.g. 50% / 25% / 25% from v1.0.)

### 3.5 Manual Sell Gear

After computing \( g \) (and s):

- You may **override** with a manual gear \( g_{\text{manual}} \) if you consciously want:
  - More aggressive take-profit (higher g).
  - More conservative take-profit (lower g).

Then:

\[
s_{\text{manual}} = 1 + g_{\text{manual}}
\]

Ladder: \( +s_{\text{manual}}\%, +2s_{\text{manual}}\%, +3s_{\text{manual}}\% \).

Manual overrides should be reserved for rare, high-conviction situations, not small emotional tweaks.

---

## 4. Buy Initiation Mechanism (v1.2 – Entry Gear)

This governs **the first buy** when you currently hold **zero units** of a stock.

### 4.1 Local dip from N-day high

For a given stock:

- Let \( N \) = 10 trading days (default, can be parameterized).
- \( H_N \): highest close in last N days.
- \( P \): current price.

Define **drawdown from N-day high**:

\[
\text{DD} = \frac{H_N - P}{H_N} \times 100\%
\]

We will compare DD to an **entry dip threshold** determined by T and V.

### 4.2 Entry dip formula from T & V

You want to think:

> “Start from base **–10%**, then add the trend effect and subtract volatility.”

In terms of **magnitude** (positive % dip), define:

- Trend factor \( T \in [0,5] \) as before:
  \[
  T = \frac{3L + 2G}{5}
  \]
- Volatility factor \( V \in [0,2] \), where:
  - Bigger V → more volatile → require **deeper** entry.

Then the **dip magnitude** (positive %) is:

\[
D(T, V) = 10 - T + V
\]

Interpretation:

- Signed threshold as “–(10 – T + V)%” from recent high.
- \( T = 5, V = 0 \Rightarrow D = 5\% \) (entry at –5%).  
- \( T = 0, V = 2 \Rightarrow D = 12\% \) (entry at –12%).

So the **automatic entry dip range** is:

- Floor near **–5%** (best trend, calm stock).
- Ceiling near **–12%** (worst trend, very volatile stock).

Optionally clamp:

\[
D_{\text{threshold}} = \min(12,\ \max(5,\ D(T,V)))
\]

Optional 0.1 quantization:

\[
D_{\text{threshold}} := \frac{\text{round}(10 \cdot D_{\text{threshold}})}{10}
\]

So you get thresholds like **7.3%** rather than only integers.

> Mental picture:  
> Start at –10%.  
> - Trend **T** shifts entry **shallower** (add T).  
> - Volatility **V** shifts entry **deeper** (subtract V in signed form, equivalently +V in magnitude).

### 4.3 No-go safety (optional trend floor)

You may optionally impose:

- If \( T < 1.5 \) (very bad environment), you **do not** start new campaigns at all, even if DD ≥ D_threshold.

This is a coarse “no-go zone” for extreme crash regimes.

### 4.4 Technical sanity

Even if DD ≥ D_threshold, you also want basic technical sanity, e.g.:

- Price P is not in a multi-month death spiral.
- Example conditions (choose your favorite):
  - P ≥ 200-day moving average, or
  - 200-day MA is flat or rising (not sharply falling).

This is flexible; you can refine it later.

### 4.5 Automatic Buy Initiation Rule

When you currently hold **zero units** of a stock:

1. Committee sets:
   - \( G \in [0,5] \), \( L \in [0,5] \), \( V \in [0,2] \).
2. Compute Trend:
   \[
   T = \frac{3L + 2G}{5}
   \]
   (Optionally: if T < 1.5 → no-go, skip.)
3. Compute entry dip magnitude:
   \[
   D_{\text{threshold}} = 10 - T + V
   \]
   Clamp to [5, 12] and optionally round to 0.1.
4. Compute drawdown:
   \[
   \text{DD} = \frac{H_N - P}{H_N} \times 100\%
   \]
5. Check **technical sanity**.
6. **Automatic entry trigger**:
   - If **DD ≥ D_threshold** AND technical sanity is OK → **start campaign**:
     - Buy 1 unit (or your chosen initial size).
     - Set average price \( A_0 = P \).
     - From then on, use existing v1.0 layering / averaging rules.

### 4.6 Manual Buy Gear

Just like manual sell gear:

- You see the **automatic entry threshold** (e.g. 7.3% below 10-day high).
- You may override it with a **manual entry threshold** if:
  - You have a clear reason (e.g. visible support below, special news).
  - You consciously accept being more conservative or more aggressive.

Example:

- Auto suggested D = 6.8%.
- You decide: “This looks fragile, I’ll wait until ~8.5% dip.”
- You use –8.5% as your **manual buy gear**, and only initiate when DD ≥ 8.5%.

---

## 5. Reference Code Snippets

### 5.1 Sell gear (v1.1)

```python
def compute_penalty(f: float) -> float:
    """
    Deployment penalty.
    f: **global** fraction of capital deployed in [0, 1].
    For f <= 0.4: no penalty.
    For f > 0.4: linear penalty down to -3 at f = 1.0.
    """
    if f <= 0.4:
        return 0.0
    else:
        return -3.0 * (f - 0.4) / 0.6


def compute_trend(G: float, L: float) -> float:
    """Trend score T in [0,5] from G and L."""
    return (3.0 * L + 2.0 * G) / 5.0


def compute_auto_sell_gear(G: float, L: float, f: float,
                           quantize: bool = True):
    """
    Continuous automatic sell gear.

    Returns
    -------
    g : float
        Gear index in [0, 5].
    s : float
        Base step in percent, s = 1 + g, in [1, 6].
    sell_levels : list[float]
        [s, 2s, 3s] profit targets in percent above average price.
    """
    T = compute_trend(G, L)
    penalty = compute_penalty(f)  # f = global deployment fraction

    g_raw = T + penalty
    g = max(0.0, min(5.0, g_raw))

    if quantize:
        g = round(g * 10.0) / 10.0

    s = 1.0 + g
    sell_levels = [s, 2.0 * s, 3.0 * s]

    return g, s, sell_levels
