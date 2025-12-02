# AI Seesaw Trading Manual v1.1  
**Focus: Continuous Sell Gear & G/L Committee**

---

## 0. Version & Scope

- **v1.0**
  - Defined the basic Seesaw concept.
  - Army structure and buy logic.
  - Sell gears based only on capital proportion \( U \) with discrete steps (2/4/6, 3/6/9, …).

- **v1.1 (this document)**
  - **Keeps the buy/entry mechanism from v1.0 unchanged.**
  - **Replaces the sell mechanism** with a continuous, floating **gear system**.
  - Introduces the **Global/Local (G/L) Committee Meeting** to evaluate market prospects.
  - Designed to be **code-ready** for simulation and real-time use.

> For historical tracking: keep both `v1.0` and `v1.1` in the project.  
> v1.1 overwrites the sell mechanism logically, but old versions are preserved for rollback and comparison.

---

## 1. Basic Objects & Notation

Let:

- \( C_{\max} \): **Max capital** allocated to one stock in one campaign.
- \( C_{\text{deployed}} \): **Current deployed capital** in that stock.
- **Deployment fraction**:
  \[
  f = \frac{C_{\text{deployed}}}{C_{\max}} \in [0,1]
  \]
- **Scaled deployment score** (optional, for intuition):
  \[
  U = 5 \cdot f \in [0,5]
  \]
  - This is just “deployment in 0–5 units” (e.g. \( U = 4.5 \Rightarrow f = 0.9 \)).
  - In code, we mostly use \( f \); \( U \) is for mental picture.

For each stock, at any given time, we maintain:

- **Global AI sector score**: \( G \in [0,5] \) (float)
- **Local stock score**: \( L \in [0,5] \) (float)

These are provided by the **G/L Committee** (human + AI assistant) and updated periodically.

> **Important**  
> - \( G \) and \( L \) are not “truth”; they are structured, repeatable opinions.
> - Their purpose is to **discipline your anticipation** of the future, rather than relying on pure hunch.

---

## 2. Sell System Overview (v1.1)

The **sell system** has two modes:

1. **Automatic Gear (default)**
   - Fully rule-based.
   - Uses **G**, **L**, and **deployment fraction** \( f \) to compute a **continuous gear index** \( g \in [0,5] \).
   - Converts \( g \) into a take-profit ladder:  
     \[
     +s\%,\quad +2s\%,\quad +3s\%
     \]
     where \( s = 1 + g \).

2. **Manual Gear (override)**
   - After seeing the automatic gear suggestion, you may override it with your own \( g_{\text{manual}} \).
   - This is used only when you have a strong qualitative conviction (e.g. extremely bullish “exploding” move).

> **Scope of the gear system**  
> - The gear system is **only for taking profits on rebounds**.
> - **Cutting losses** (selling below your average price) is handled by **separate rules** (max loss, thesis broken, etc.).
> - In v1.1 we **clamp** the gear to \([0,5]\), so profit targets are always **positive %** above average price.

---

## 3. Automatic Gear Calculation (Continuous, 0–5 Scale)

### 3.1 Inputs

At a given moment for a particular stock:

- \( G \in [0,5] \): Global AI sector score.
- \( L \in [0,5] \): Local stock score.
- \( f \in [0,1] \): Deployment fraction:
  \[
  f = \frac{C_{\text{deployed}}}{C_{\max}}
  \]

### 3.2 Trend component (G & L, 3:2 weight)

We define a **Trend** score as:

\[
\text{Trend} = \frac{3L + 2G}{5}
\]

- Local stock \( L \): weight **3** (60%).
- Global AI sector \( G \): weight **2** (40%).
- Result: \(\text{Trend} \in [0,5]\), continuous (e.g. 3.84, 2.17, etc.).

This encodes the idea: *local behavior matters more, but global regime still influences the gear*.

### 3.3 Risk penalty from deployment \( f \)

We want heavier deployment to **force more conservative gears**.

Define the **penalty** \( P(f) \) as:

- If \( f \le 0.4 \):
  \[
  P(f) = 0
  \]
- If \( f > 0.4 \):
  \[
  P(f) = -3 \cdot \frac{f - 0.4}{0.6}
  \]

This is a linear function:

- \( f = 0.4 \Rightarrow P = 0 \)
- \( f = 0.6 \Rightarrow P = -3 \cdot \frac{0.2}{0.6} \approx -1 \)
- \( f = 0.8 \Rightarrow P = -3 \cdot \frac{0.4}{0.6} \approx -2 \)
- \( f = 1.0 \Rightarrow P = -3 \cdot \frac{0.6}{0.6} = -3 \)

Interpretation:

- **Light deployment** (≤ 40% of max) → no penalty.
- **Medium to heavy** deployment (40–100%) → progressively stronger penalty, down to −3.

### 3.4 Raw gear, clamping, and (optional) quantization

Compute:

\[
g_{\text{raw}} = \text{Trend} + P(f)
\]

Then **clamp** to \([0,5]\):

\[
g = \min\bigl(5,\ \max(0,\ g_{\text{raw}})\bigr)
\]

This prevents:

- Negative gear (which would imply planning exits below average price).
- Too aggressive gear > 5.

**Optional quantization** for psychological stability:

\[
g := \frac{\text{round}(10 \cdot g)}{10}
\]

This means:

- g is rounded to the nearest 0.1.
- You see gears like 3.7, 4.1, not random long decimals.

### 3.5 From gear to sell ladder

Define the **base step** \( s \) as:

\[
s = 1 + g
\]

So:

- \( g = 0 \Rightarrow s = 1\% \)  
- \( g = 5 \Rightarrow s = 6\% \)

**Automatic sell gear rule**:

- **Tier 1**: sell a chosen fraction (e.g. 50%) at **\(+s\%\)**  
- **Tier 2**: sell next fraction (e.g. 25%) at **\(+2s\%\)**  
- **Tier 3**: sell final fraction (e.g. 25%) at **\(+3s\%\)**  

The ratio (50/25/25) can be kept from v1.0; v1.1 focuses on how we generate **s**, not how we split units.

**Examples**

- Example 1: \( g = 0 \)
  - \( s = 1\% \)
  - Ladder: **1% / 2% / 3%**

- Example 2: \( g = 3.4 \)
  - \( s = 4.4\% \)
  - Ladder: **4.4% / 8.8% / 13.2%**

- Example 3: \( g = 5 \)
  - \( s = 6\% \)
  - Ladder: **6% / 12% / 18%**

---

## 4. Automatic Gear vs Manual Gear

### 4.1 Automatic Gear (default mode)

Workflow:

1. Evaluate or update **G** and **L**.
2. Calculate deployment fraction **f**.
3. Compute:
   - \( \text{Trend} = (3L + 2G)/5 \)
   - \( P(f) \)
   - \( g \) via clamping/quantization.
   - \( s = 1 + g \)
4. Use **\(+s\%, +2s\%, +3s\%\)** as your **default profit-taking ladder**.

This is the **discipline backbone** of the system.

### 4.2 Manual Gear (override mode)

After you see the automatic result (e.g. \( g = 3.2, s = 4.2\% \)):

- You **may override** to a manually chosen gear \( g_{\text{manual}} \), then recompute:
  - \( s_{\text{manual}} = 1 + g_{\text{manual}} \)
  - New ladder: \( +s_{\text{manual}}\%, +2s_{\text{manual}}\%, +3s_{\text{manual}}\% \)

Manual overrides are intended for rare, high-conviction situations:

- Example: very strong global + local trend, clear explosive move.
- You consciously accept more risk in exchange for higher potential.

**Discipline recommendation**:

- Allow manual overrides mainly when:
  - Trend (from G, L) is high (e.g. Trend ≥ 4), **and**
  - You have a clear, written or mental reason.
- Avoid using manual gear for small emotional nudges.

---

## 5. G/L Committee Meeting Protocol

The G/L scores are a core part of v1.1. They encode **anticipation** of the future in a structured way.

### 5.1 Frequency of evaluation

- **Global score G** (AI sector)
  - Evaluate roughly **once per month**.
  - Update sooner only on **major macro events**:
    - Big rate changes.
    - Strong sector-wide crash or melt-up.
    - Major regulatory changes, etc.

- **Local score L** (per stock)
  - Update when any of the following happens:
    - Earnings release.
    - Large gap move or regime change in chart (breaking a key level, trend reversal).
    - Major company-specific news.
  - Otherwise, review weekly or when planning new trades.

### 5.2 Committee composition

- **Human (you)**:
  - Final decision maker of \( G \) and \( L \).
  - Can accept or adjust AI proposals.

- **AI assistant (me)**:
  - Uses web search and data to propose:
    - \( G_{\text{proposal}} \in [0,5] \).
    - \( L_{\text{proposal}} \in [0,5] \).
  - Provides reasoning for each proposal.

### 5.3 How the AI proposes G (global)

When you ask:

> “Give me a G score for the AI sector now.”

The AI will:

- Check:
  - Sector/ETF charts vs moving averages (trend and volatility).
  - Macro environment: rates, liquidity, risk sentiment.
  - AI sector news: earnings, adoption, regulations, hype vs deflation cycles.
- Internally combine these into a **G proposal** in [0,5].
- Present something like:

> “My view:  
> G ≈ 3.7 (slightly bullish).  
> Reason: sector above 50d/200d MAs, earnings decent, no major negative macro shock, etc.”

You then:

- Accept \( G = 3.7 \), or
- Adjust it (e.g. “I’ll use G = 3.5”).

### 5.4 How the AI proposes L (local, per stock)

When you ask:

> “Give me an L score for stock X.”

The AI will:

- Look at:
  - The stock’s chart vs its 50d/200d MAs.
  - Relative performance vs sector/index.
  - Volume, breakouts, volatility.
  - Company-specific news (earnings, guidance, product launches, downgrades, lawsuits, etc.).
- Compress into an **L proposal** in [0,5].
- Present, for example:

> “My view:  
> L ≈ 4.2 (bullish).  
> Reason: stock above rising 50d and 200d MAs, recent earnings beat, strong volume, etc.”

You then:

- Accept \( L = 4.2 \), or
- Adjust to your own final \( L \) (e.g. 4.0, 4.5).

### 5.5 Final G and L used in the formula

- Only the **final numbers you choose**:
  - \( G_{\text{final}} \in [0,5] \)
  - \( L_{\text{final}} \in [0,5] \)
- are plugged into the gear formula.

The internal decomposition (trend, macro, news, etc.) remains **AI-side** and is not required to run your system.

---

## 6. Reference Implementation (for Code)

Below is a reference implementation of the automatic gear calculation in Python-like pseudocode.

```python
def compute_penalty(f: float) -> float:
    """
    Deployment penalty.
    f: fraction of capital deployed in [0, 1].
    For f <= 0.4: no penalty.
    For f > 0.4: linear penalty down to -3 at f = 1.0.
    """
    if f <= 0.4:
        return 0.0
    else:
        return -3.0 * (f - 0.4) / 0.6


def compute_auto_gear(G: float, L: float, f: float,
                      quantize: bool = True) -> tuple[float, float, list[float]]:
    """
    Compute continuous automatic sell gear.

    Parameters
    ----------
    G : float
        Global AI sector score in [0, 5].
    L : float
        Local stock score in [0, 5].
    f : float
        Deployment fraction in [0, 1] (deployed / max capital).
    quantize : bool
        If True, quantize gear to 0.1 steps for psychological stability.

    Returns
    -------
    g : float
        Gear index in [0, 5].
    s : float
        Base step in percent, s = 1 + g, in [1, 6].
    sell_levels : list[float]
        [s, 2s, 3s] profit targets in percent above average price.
    """
    # 1. Trend from G and L (3:2 weighting)
    trend = (3.0 * L + 2.0 * G) / 5.0  # in [0, 5]

    # 2. Risk penalty from deployment
    penalty = compute_penalty(f)

    # 3. Raw gear and clamp
    g_raw = trend + penalty
    g = max(0.0, min(5.0, g_raw))  # clamp to [0, 5]

    # 4. Optional quantization
    if quantize:
        g = round(g * 10.0) / 10.0  # 0.1 resolution

    # 5. Base step and ladder
    s = 1.0 + g
    sell_levels = [s, 2.0 * s, 3.0 * s]

    return g, s, sell_levels
