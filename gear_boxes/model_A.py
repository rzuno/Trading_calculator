"""
Model A: momentum + volatility (lightweight context-based version).

This adapts the provided snippet to the data available in main.py
without requiring full OHLC series.
"""

from __future__ import annotations

from datetime import date, timedelta


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def _parse_yymmdd(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 8:
        digits = digits[2:]
    if len(digits) != 6:
        return None
    try:
        yy = int(digits[:2])
        mm = int(digits[2:4])
        dd = int(digits[4:6])
        return date(2000 + yy, mm, dd)
    except ValueError:
        return None


def _trading_days_since(d):
    if not d:
        return 0
    today = date.today()
    if d >= today:
        return 0
    days = 0
    cursor = d + timedelta(days=1)
    while cursor <= today:
        if cursor.weekday() < 5:
            days += 1
        cursor += timedelta(days=1)
    return days


def _atr_pct(context):
    current = float(context.get("current_price", 0) or 0)
    high_5d = float(context.get("high_5d", 0) or 0)
    low_today = float(context.get("low_today", 0) or 0)
    if current <= 0 or high_5d <= 0 or low_today <= 0:
        return 0.0
    return max(0.0, (high_5d - low_today) / current * 100.0)


def _roc_pct(context):
    current = float(context.get("current_price", 0) or 0)
    ref = float(context.get("high_5d", 0) or 0)
    if ref <= 0:
        ref = float(context.get("high_10d", 0) or 0)
    if current <= 0 or ref <= 0:
        return 0.0
    return (current - ref) / ref * 100.0


def calculate_sell_gear(context):
    """
    Sell gear with momentum + volatility.
    Returns: 1-5 (higher = higher profit targets)
    """
    atr_pct = _atr_pct(context)
    roc = _roc_pct(context)

    if roc > 10:
        base = 5
    elif roc > 5:
        base = 4
    elif roc > 0:
        base = 3
    elif roc > -5:
        base = 2
    else:
        base = 1

    if atr_pct > 4.0:
        base -= 1

    return _clamp(base, 1, 5)


def calculate_buy_gear(context):
    """
    Buy gear with trend adjustment.
    Returns: 1-5 (higher = deeper entry)
    """
    atr_pct = _atr_pct(context)
    roc = _roc_pct(context)

    if atr_pct < 2.5:
        base = 2
    elif atr_pct < 4.5:
        base = 3
    else:
        base = 4

    if roc > 12.0:
        adj = -2
    elif roc > 6.0:
        adj = -1
    elif roc < -12.0:
        adj = 2
    elif roc < -6.0:
        adj = 1
    else:
        adj = 0

    return _clamp(base + adj, 1, 5)


def _apply_sell_delta(rec, context, delta, source):
    current_sell = int(context.get("sell_gear", 3) or 3)
    total_delta = int(rec.get("delta_sell", 0)) + int(delta)
    proposed = current_sell + total_delta
    clamped = _clamp(proposed, 1, 5)
    rec["sell_gear"] = int(clamped)
    rec["delta_sell"] = int(clamped - current_sell)
    rec.setdefault("adjustments", []).append((source, int(delta)))
    if clamped != proposed:
        rec["clamped"] = True
    return rec


def _apply_idle_breaker(rec, context):
    last_trade = _parse_yymmdd(context.get("latest_trading_day", ""))
    idle_days = _trading_days_since(last_trade)
    if idle_days >= 10:
        _apply_sell_delta(rec, context, -1, "idle")
        rec["status"] = "IDLE"
        extra = f"Idle {idle_days} trading days -> sell -1."
        notes = rec.get("notes", "")
        rec["notes"] = f"{notes} {extra}".strip()
    return rec


def _apply_deployment_breaker(rec, context):
    try:
        ratio = float(context.get("deployment_ratio", 0.0) or 0.0)
    except (TypeError, ValueError):
        ratio = 0.0
    if ratio >= 0.7:
        _apply_sell_delta(rec, context, -2, "size")
        rec["status"] = "WARNING"
        extra = f"Deployment {ratio*100:.0f}% -> sell -2."
        notes = rec.get("notes", "")
        rec["notes"] = f"{notes} {extra}".strip()
    elif ratio >= 0.4:
        _apply_sell_delta(rec, context, -1, "size")
        rec["status"] = "WARNING"
        extra = f"Deployment {ratio*100:.0f}% -> sell -1."
        notes = rec.get("notes", "")
        rec["notes"] = f"{notes} {extra}".strip()
    return rec


def recommend_model_a(context):
    buy_gear = calculate_buy_gear(context)
    sell_gear = calculate_sell_gear(context)
    current_buy = int(context.get("buy_gear", 3) or 3)
    current_sell = int(context.get("sell_gear", 3) or 3)
    atr_pct = _atr_pct(context)
    roc = _roc_pct(context)
    rec = {
        "model": "Model A",
        "buy_gear": int(_clamp(buy_gear, 1, 5)),
        "sell_gear": int(_clamp(sell_gear, 1, 5)),
        "delta_buy": int(buy_gear - current_buy),
        "delta_sell": int(sell_gear - current_sell),
        "status": "OK",
        "confidence": 0.55,
        "notes": f"ATR% {atr_pct:.1f}, ROC% {roc:.1f}.",
        "adjustments": [("gearbox", int(sell_gear - current_sell))],
    }
    rec = _apply_idle_breaker(rec, context)
    rec = _apply_deployment_breaker(rec, context)
    return rec


GEARBOX_MODELS = {
    "Model A": {"name": "Model A", "fn": recommend_model_a},
}

DEFAULT_MODEL = "Model A"


def recommend(model_name, context):
    model = GEARBOX_MODELS.get(model_name) or GEARBOX_MODELS.get(DEFAULT_MODEL)
    if not model:
        return {
            "model": "Unavailable",
            "buy_gear": int(context.get("buy_gear", 3) or 3),
            "sell_gear": int(context.get("sell_gear", 3) or 3),
            "delta_buy": 0,
            "delta_sell": 0,
            "status": "NEEDS DATA",
            "confidence": 0.0,
            "notes": "No gearbox models loaded.",
            "adjustments": [],
        }
    return model["fn"](context)
