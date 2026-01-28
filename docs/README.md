# AI Seesaw Trading - Semi-Autonomous Trading Machine (Living Docs)

Educational and experimental trading assistant for rule-based, mechanical trading.
Goal: a clean state machine that recommends next buy/sell points and gear settings.
You decide execution (semi-autonomous). Full autonomy is a later milestone.

## Scope
- Focus: AI-sector stocks only.
- Current universe: Samsung Electronics, SK hynix, NVIDIA, Alphabet (GOOGL/GOOG).
- This is not financial advice.

## The Three Living Docs (Only These)
- **README.md**: overview and workflow
- **manual.md**: codify-ready strategy spec (state machine)
- **changelog.md**: versioned design history

Git history holds older manual versions; we do not keep them as separate files anymore.

## Strategy Summary
- Capital is divided into **N units** (army units).
- Each stock position has a state (units deployed, shares, avg_cost, anchor_high, ladder state, last action time).
- Buying modes:
  - **LOAD** (first entry on pullback from recent peak)
  - **RELOAD** (offensive add on pullback while above avg_cost; semi-manual)
  - **RESCUE** (defensive averaging-down below avg_cost using smooth gearbox sizing)
  - **RESET** (small re-arm buy after Tier 1 fill when price returns to avg_cost)
- Selling is a **3-tier ladder** (50% / 25% / 25%) using a 5-gear table.
- Gear selection is guided by a **point-based perk system** with optional macro context (G/L/V, FX).

## Semi-Autonomous Blueprint
The program is not an auto-trader yet. It is a trading machine that shows:
1) Next buy triggers (LOAD/RELOAD/RESCUE/RESET)
2) Next sell ladder prices and quantities
3) Recommended gear adjustments via perks (auto + manual)
4) Idle warnings (5-day yellow, 10-day red)

## Safety Notes
- This is not financial advice.
- Even rule-based systems can lose money.
- Start small and treat early versions as training and simulation tools.

## Repo Hygiene
- Keep only the three docs in `docs/`.
- If you reorganize files, prefer `git mv` (history stays clean).
- Keep commits small and descriptive; commit history is the manual version archive.

---

Possible future additions:
- `docs/` for images only (charts, screenshots)
- `configs/trait_system_v0.2.json` for perk definitions
- `src/` for engine and UI code
