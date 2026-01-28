# Perk System Manual

## Purpose
This system converts auto + manual "perks" into buy/sell gear adjustments.
It reads configuration from `trait system/perks.json` and uses market data
from `data.csv` (updated by the UI's Refresh Market Data button).

## Files
- `trait system/perks.json`: single source of truth for perks and rules.
- `main.py`: UI + calculation logic.
- `data.csv`: cached market data and computed metrics.

## Configuration: perks.json

### system_config
- `point_to_gear_ratio`: points per 1 gear shift (default 10).
- `base_buy_gear`, `base_sell_gear`: starting gears before perks.
- `gear_min`, `gear_max`: clamp limits for final gears.
- `description`: free text.

### exclusive_groups
Defines groups that must be mutually exclusive.
Example fields:
- `description`: human-readable group name.
- `enforcement`: `auto` or `manual`.
- `ui_type`: for manual groups, use `radio`.

### perks list
Each perk uses these fields:
- `id`: unique identifier.
- `name`: label shown in UI.
- `category`: grouping label for manual lists.
- `exclusive_group`: optional group id.
- `auto`: true for auto-triggered perks.
- `auto_trigger`: boolean expression evaluated against metrics.
- `buy_points`, `sell_points`: integer adjustments.
- `description`: tooltip text (shown in UI).
- `icon`: optional prefix for the label.

## Metrics available to auto_trigger
These values are computed at refresh time:
- `roc_1d`, `roc_3d`, `roc_5d`: percent change vs prior close(s).
- `atr_3d_pct`, `atr_5d_pct`: ATR% over 3/5 sessions.
- `atr_pct`: short-term ATR% based on 5d high vs today low.
- `roc`: percent change vs recent high (5d/10d).
- `deployed_pct`: portfolio deployed percentage.
- `pnl_pct`: profit/loss percentage vs average cost.
- `fx_vs_avg`: FX percent vs moving average (USD/KRW).
- `days_idle`: trading days since last trade.

## Exclusive group behavior
- Auto groups: only one perk per group is allowed (highest priority trigger).
- Manual groups: shown as radio buttons, pick one.
- No group: treated as normal checkboxes (can stack).

## Gear calculation
1. Identify active auto perks (based on `auto_trigger`).
2. Add active manual perks (checkboxes/radios).
3. Sum buy/sell points independently.
4. Convert to gear shifts using `point_to_gear_ratio`.
5. Add shifts to base gears.
6. Clamp to `gear_min`/`gear_max`.
7. Special rule: if `black_swan` is active, sell gear forced to 0.

## UI behavior
- Auto perks are display-only with totals (bold).
- Manual perks use radios for exclusive groups and checkboxes otherwise (bold total).
- Ratio is shown under manual total (indented).
- Apply/Cancel status is stored per-stock and persisted in `data.csv`.
  - Apply computes from base gears (not from prior applied values).
  - Cancel returns to base gears.

## Data refresh pipeline
The Refresh Market Data button does:
1. Fetch current price and intraday low/high (best available).
2. Compute 1/3/5-day ROC, 3/5-day ATR%.
3. Fetch USD/KRW current + FX moving average.
4. Save results into `data.csv`.

## data.csv fields (perk-related)
Stored for speed and history:
- `current_price`, `high_5d`, `high_10d`, `low_today`, `high_today`
- `roc_1d`, `roc_3d`, `roc_5d`
- `atr_3d_pct`, `atr_5d_pct`
- `fx_rate`, `fx_avg`
- `last_update`

## Adding a new perk
1. Add a new entry in `perks.json` with unique `id`.
2. Choose `auto` + `auto_trigger` or manual only.
3. Assign `exclusive_group` if mutually exclusive.
4. Keep points as integers for clean totals.
