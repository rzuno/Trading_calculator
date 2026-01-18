import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from math import ceil
from datetime import datetime

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not installed. Price fetching disabled.")


DATA_FILE = "data.csv"
DEFAULT_NAMES = [
    ("Samsung", "KR"),
    ("SK hynix", "KR"),
    ("NVIDIA", "US"),
    ("Alphabet", "US"),
]
GLOBAL_FX_RATE = 1300.0  # ₩ per $
PORTFOLIO_N = 25  # Total units across all stocks
LOAD_REF_DAYS = 5
HIGH_CONTEXT_DAYS = 10

RESCUE_GEAR_COLORS = {
    1: "#ff9800",  # orange
    2: "#d32f2f",  # red
    3: "#8b5a2b",  # brown
}

RESCUE_U_SAT = 10.0
RESCUE_DROP_MIN = 4.0
RESCUE_DROP_SPAN = 2.0
RESCUE_R_MIN = 0.5
RESCUE_R_SPAN = 0.2

# Ticker mappings for Yahoo Finance
TICKER_MAP = {
    "Samsung": "005930.KS",      # Samsung Electronics on KRX
    "SK hynix": "000660.KS",     # SK hynix on KRX
    "NVIDIA": "NVDA",            # NVIDIA on NASDAQ
    "Alphabet": "GOOGL"          # Alphabet on NASDAQ
}

# Buy models (gear_drop %, r) - DEPRECATED, kept for backward compatibility
# v1.4 uses dynamic LOAD/RESCUE formulas instead
BUY_MODELS = {
    "Agile (-5%,0.6)": {"gear_drop": 5.0, "r": 0.6},
    "Heavy (-6%,0.7)": {"gear_drop": 6.0, "r": 0.7},
    "Greedy (-4%,0.7)": {"gear_drop": 4.0, "r": 0.7},
    "Cautious (-7%,0.65)": {"gear_drop": 7.0, "r": 0.65},
}

stock_data = {}
stock_order = []
GLOBAL_MAX_VOLUME_KRW = 0.0


def default_record(market="KR"):
    return {
        "avg_cost": "",
        "num_shares": "",
        "max_volume": "",
        "g_score": 0.0,
        "l_score": 0.0,
        "v_score": 1.0,
        "g_date": "",
        "l_date": "",
        "market": market,
        "fx_rate": GLOBAL_FX_RATE if market == "US" else 1.0,
        # v1.4 new fields
        "units_held": 0,  # Position size for RESCUE gear calculation
        "current_price": "",  # Latest fetched price
        "high_5d": "",  # 5-day high for LOAD calculation
        "high_10d": "",  # 10-day high for context display
        "low_today": "",  # Today's low
        "high_today": "",  # Today's high
        "last_update": "",  # Timestamp of last price fetch
        "manual_sell_mode": 0,  # 0=auto, 1=manual
        "manual_sell_step": 0.0,  # Manual override value if enabled
        "manual_load_mode": 0,  # 0=auto, 1=manual
        "manual_load_drop": 0.0,  # Manual load drop override (3-7%)
        # Deprecated fields (kept for backward compatibility)
        "buy_model": list(BUY_MODELS.keys())[0],
        "manual_mode": 0,
        "manual_gear": 0.0,
    }


def load_data():
    global stock_order, stock_data, GLOBAL_FX_RATE, GLOBAL_MAX_VOLUME_KRW
    stock_data = {}
    stock_order = []
    GLOBAL_MAX_VOLUME_KRW = 0.0
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue

                def to_float(val):
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return ""

                avg_cost = to_float(row.get("avg_cost", ""))
                num_shares = to_float(row.get("num_shares", ""))
                max_volume = to_float(row.get("max_volume", ""))
                market = (row.get("market") or "KR").strip().upper()
                if market not in ("KR", "US"):
                    market = "KR"
                fx_rate = to_float(row.get("fx_rate", GLOBAL_FX_RATE))
                if fx_rate == "":
                    fx_rate = GLOBAL_FX_RATE if market == "US" else 1.0
                manual_mode = int(row.get("manual_mode", 0)) if str(row.get("manual_mode", "0")).isdigit() else 0
                g_score = to_float(row.get("g_score", ""))
                l_score = to_float(row.get("l_score", ""))
                if g_score == "":
                    g_score = 0.0
                if l_score == "":
                    l_score = 0.0
                v_score = to_float(row.get("v_score", ""))
                if v_score == "":
                    v_score = 1.0
                g_date = (row.get("g_date") or "").strip()
                l_date = (row.get("l_date") or "").strip()

                def parse_manual_gear(val):
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        pass
                    if isinstance(val, str) and val.lower().startswith("gear"):
                        digits = "".join(ch for ch in val if ch.isdigit())
                        if digits:
                            try:
                                return float(int(digits))
                            except ValueError:
                                return 0.0
                    return 0.0

                manual_gear_val = parse_manual_gear(row.get("manual_gear", 0.0))

                # v1.4 new fields
                units_held = to_float(row.get("units_held", 0))
                if units_held == "":
                    units_held = 0
                current_price = to_float(row.get("current_price", ""))
                high_5d = to_float(row.get("high_5d", ""))
                high_10d = to_float(row.get("high_10d", ""))
                low_today = to_float(row.get("low_today", ""))
                high_today = to_float(row.get("high_today", ""))
                last_update = (row.get("last_update") or "").strip()
                manual_sell_mode = int(row.get("manual_sell_mode", 0)) if str(row.get("manual_sell_mode", "0")).isdigit() else 0
                manual_sell_step = to_float(row.get("manual_sell_step", 0.0))
                if manual_sell_step == "":
                    manual_sell_step = 0.0
                manual_load_mode = int(row.get("manual_load_mode", 0)) if str(row.get("manual_load_mode", "0")).isdigit() else 0
                manual_load_drop = to_float(row.get("manual_load_drop", 0.0))
                if manual_load_drop == "":
                    manual_load_drop = 0.0

                stock_data[name] = {
                    "avg_cost": avg_cost,
                    "num_shares": num_shares,
                    "max_volume": max_volume,
                    "market": market,
                    "fx_rate": fx_rate,
                    "g_score": g_score,
                    "l_score": l_score,
                    "v_score": v_score,
                    "g_date": g_date,
                    "l_date": l_date,
                    # v1.4 fields
                    "units_held": units_held,
                    "current_price": current_price,
                    "high_5d": high_5d,
                    "high_10d": high_10d,
                    "low_today": low_today,
                    "high_today": high_today,
                    "last_update": last_update,
                    "manual_sell_mode": manual_sell_mode,
                    "manual_sell_step": manual_sell_step,
                    "manual_load_mode": manual_load_mode,
                    "manual_load_drop": manual_load_drop,
                    # Deprecated (backward compatibility)
                    "buy_model": row.get("buy_model", list(BUY_MODELS.keys())[0]),
                    "manual_mode": manual_mode,
                    "manual_gear": manual_gear_val,
                }
                stock_order.append(name)
                # Allow FX to be set from any row if a realistic value is present (>10 avoids overwriting with 1)
                if fx_rate and fx_rate > 10:
                    GLOBAL_FX_RATE = fx_rate
                if max_volume and max_volume > 0:
                    GLOBAL_MAX_VOLUME_KRW = max_volume
    if not stock_order:
        for nm, mk in DEFAULT_NAMES:
            stock_order.append(nm)
            stock_data[nm] = default_record(mk)

    # After loading, propagate global FX to all records
    for rec in stock_data.values():
        rec["fx_rate"] = GLOBAL_FX_RATE


def write_data_file():
    fieldnames = [
        "name",
        "avg_cost",
        "num_shares",
        "max_volume",
        "g_score",
        "l_score",
        "v_score",
        "g_date",
        "l_date",
        "market",
        "fx_rate",
        # v1.4 new fields
        "units_held",
        "current_price",
        "high_5d",
        "high_10d",
        "low_today",
        "high_today",
        "last_update",
        "manual_sell_mode",
        "manual_sell_step",
        "manual_load_mode",
        "manual_load_drop",
        # Deprecated (backward compatibility)
        "buy_model",
        "manual_mode",
        "manual_gear",
    ]
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for name in stock_order:
            rec = stock_data.get(name, default_record())
            writer.writerow(
                {
                    "name": name,
                    "avg_cost": rec.get("avg_cost", ""),
                    "num_shares": rec.get("num_shares", ""),
                    "max_volume": rec.get("max_volume", ""),
                    "g_score": rec.get("g_score", ""),
                    "l_score": rec.get("l_score", ""),
                    "v_score": rec.get("v_score", ""),
                    "g_date": rec.get("g_date", ""),
                    "l_date": rec.get("l_date", ""),
                    "market": rec.get("market", "KR"),
                    "fx_rate": rec.get("fx_rate", GLOBAL_FX_RATE if rec.get("market", "KR") == "US" else 1.0),
                    # v1.4 fields
                    "units_held": rec.get("units_held", 0),
                    "current_price": rec.get("current_price", ""),
                    "high_5d": rec.get("high_5d", ""),
                    "high_10d": rec.get("high_10d", ""),
                    "low_today": rec.get("low_today", ""),
                    "high_today": rec.get("high_today", ""),
                    "last_update": rec.get("last_update", ""),
                    "manual_sell_mode": rec.get("manual_sell_mode", 0),
                    "manual_sell_step": rec.get("manual_sell_step", 0.0),
                    "manual_load_mode": rec.get("manual_load_mode", 0),
                    "manual_load_drop": rec.get("manual_load_drop", 0.0),
                    # Deprecated
                    "buy_model": rec.get("buy_model", list(BUY_MODELS.keys())[0]),
                    "manual_mode": rec.get("manual_mode", 0),
                    "manual_gear": rec.get("manual_gear", 0.0),
                }
            )


def fmt_money(val, market="KR"):
    try:
        val = float(val)
        if market == "US":
            return f"${val:,.2f}"
        return f"₩{val:,.0f}"
    except (TypeError, ValueError):
        return ""


def fmt_or_na(val, market="KR"):
    formatted = fmt_money(val, market)
    return formatted if formatted else "N/A"


def compute_unit_size_krw(max_volume_krw):
    return (max_volume_krw / PORTFOLIO_N) if max_volume_krw and PORTFOLIO_N else 0.0


def compute_position_value_krw(avg_cost, num_shares, market, fx_rate):
    if market == "US":
        return avg_cost * num_shares * fx_rate
    return avg_cost * num_shares


def compute_units_held(avg_cost, num_shares, max_volume_krw, market, fx_rate):
    unit_size_krw = compute_unit_size_krw(max_volume_krw)
    position_krw = compute_position_value_krw(avg_cost, num_shares, market, fx_rate)
    units = position_krw / unit_size_krw if unit_size_krw else 0.0
    return units, unit_size_krw, position_krw


def format_input(val, market="KR", is_money=True, decimals=2):
    try:
        val = float(val)
        if is_money:
            if market == "US":
                return f"{val:,.{decimals}f}"
            return f"{val:,.0f}"
        return f"{val:,.{decimals}f}"
    except (TypeError, ValueError):
        return ""


# ===== v1.4 CALCULATION FUNCTIONS =====

def compute_load_trigger(T, V):
    """
    LOAD entry threshold based on trend and volatility (v1.4).

    T = (3*L + 2*G) / 5 (Trend score)
    Drop% = 6.0 - 0.6*T + 0.5*V  [clamped to 3-8%]

    Returns: drop percentage (float)
    """
    drop_pct = 6.0 - 0.6 * T + 0.5 * V
    drop_pct = max(3.0, min(8.0, drop_pct))
    return drop_pct


def compute_load_entry_price(high_5d, T, V):
    """
    Calculate LOAD entry price from 5-day high.

    Entry price = high_5d * (1 - drop_pct/100)

    Returns: entry trigger price (float)
    """
    drop_pct = compute_load_trigger(T, V)
    return high_5d * (1 - drop_pct / 100)


def round_half_up(val):
    return int(val + 0.5)


def get_rescue_gear(units_held, N):
    """
    Determine RESCUE gear based on position size (v1.3.7 smooth transmission).

    Smooth ramp based on deployed units:
      - U_sat=10.0 (or N if smaller)
      - drop_pct = 4.0 + 2.0 * t
      - r = 0.5 + 0.2 * t
      - gear = 1.0 + 2.0 * t
      - t = clamp(0, (units-1)/(U_sat-1), 1)

    Returns: (drop_pct, r, gear) tuple
    """
    u_sat = RESCUE_U_SAT
    if N and N > 0:
        u_sat = min(RESCUE_U_SAT, float(N))
    if u_sat <= 1.0:
        t = 1.0
    else:
        t = (units_held - 1.0) / (u_sat - 1.0)
    t = max(0.0, min(1.0, t))

    drop_pct = RESCUE_DROP_MIN + RESCUE_DROP_SPAN * t
    r = RESCUE_R_MIN + RESCUE_R_SPAN * t
    gear = 1.0 + 2.0 * t
    return drop_pct, r, gear


def compute_rescue_trigger(avg_cost, units_held, total_units, N):
    """
    RESCUE trigger price and buy quantity (v1.4).

    Returns: (trigger_price, buy_units, gear, drop_pct, r) tuple
    """
    if units_held <= 0:
        return avg_cost, 0, 0, 0.0, 0.0  # LOAD only when empty

    drop_pct, r, gear = get_rescue_gear(units_held, N)
    trigger_price = avg_cost * (1 - drop_pct / 100)

    buy_units = units_held * r
    if N and N > 0:
        remaining_units = max(0.0, N - total_units)
        buy_units = min(buy_units, remaining_units)

    return trigger_price, buy_units, gear, drop_pct, r


def compute_sell_targets_v1_4(avg_cost, s):
    """
    Unified 2-tier sell system (v1.4).

    Tier 1: avg_cost * (1 + 1*s/100) - Sell 50%
    Tier 2: avg_cost * (1 + 2*s/100) - Sell 50%

    Returns: list of [tier1_price, tier2_price]
    """
    tier1 = avg_cost * (1 + 1.0 * s / 100)
    tier2 = avg_cost * (1 + 2.0 * s / 100)
    return [tier1, tier2]


# ===== END v1.4 FUNCTIONS =====


# ===== YAHOO FINANCE DATA FETCHING =====

def fetch_current_price(stock_name):
    """
    Fetch current price and recent highs for stock from Yahoo Finance.

    Returns: dict with keys:
        'current': float - current/close price
        'high_5d': float - highest high of past 5 days (excluding today when possible)
        'high_10d': float - highest high of past 10 days (excluding today when possible)
        'low_today': float - today's low
        'high_today': float - today's high
        'timestamp': datetime - fetch time
    Returns None if fetch fails or yfinance not available.
    """
    if not YFINANCE_AVAILABLE:
        return None

    ticker = TICKER_MAP.get(stock_name)
    if not ticker:
        return None

    try:
        stock = yf.Ticker(ticker)

        # Get recent history for highs (exclude today when possible)
        hist_days = HIGH_CONTEXT_DAYS + 1
        hist = stock.history(period=f"{hist_days}d")
        if hist.empty:
            return None

        hist_completed = hist.iloc[:-1] if len(hist) > 1 else hist
        if hist_completed.empty:
            hist_completed = hist
        high_10d = hist["High"].tail(HIGH_CONTEXT_DAYS).max()
        high_5d = hist_completed["High"].tail(LOAD_REF_DAYS).max()

        # Get today's data
        today = stock.history(period="1d")
        if today.empty:
            return None

        return {
            'current': today['Close'].iloc[-1],
            'high_5d': high_5d,
            'high_10d': high_10d,
            'low_today': today['Low'].iloc[-1],
            'high_today': today['High'].iloc[-1],
            'timestamp': datetime.now()
        }
    except Exception as e:
        print(f"Error fetching {stock_name}: {e}")
        return None


def fetch_fx_rate():
    """
    Fetch USD/KRW exchange rate from Yahoo Finance.

    Returns: float or None
    """
    if not YFINANCE_AVAILABLE:
        return None

    try:
        fx = yf.Ticker("KRW=X")
        hist = fx.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except Exception as e:
        print(f"Error fetching FX rate: {e}")
    return None


# ===== END YAHOO FINANCE FUNCTIONS =====


def refresh_market_data():
    global GLOBAL_FX_RATE
    if not YFINANCE_AVAILABLE:
        messagebox.showerror("Unavailable", "yfinance is not installed. Price fetching disabled.")
        return

    new_fx = fetch_fx_rate()
    if new_fx and new_fx > 10:
        GLOBAL_FX_RATE = new_fx
        fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))

    for stock_name in stock_order:
        price_data = fetch_current_price(stock_name)
        if not price_data:
            continue
        rec = stock_data.get(stock_name, default_record())
        rec["current_price"] = price_data["current"]
        rec["high_5d"] = price_data["high_5d"]
        rec["high_10d"] = price_data["high_10d"]
        rec["low_today"] = price_data["low_today"]
        rec["high_today"] = price_data["high_today"]
        rec["last_update"] = price_data["timestamp"].strftime("%Y-%m-%d %H:%M")
        rec["fx_rate"] = GLOBAL_FX_RATE
        stock_data[stock_name] = rec

    write_data_file()
    update_display()
    messagebox.showinfo("Market data", "Prices and FX updated.")


def compute_penalty(f):
    if f <= 0.4:
        return 0.0
    return -3.0 * (f - 0.4) / 0.6


def compute_trend(g_score, l_score):
    return (3.0 * l_score + 2.0 * g_score) / 5.0


def compute_auto_gear(g_score, l_score, f, quantize=True):
    trend = compute_trend(g_score, l_score)
    penalty = compute_penalty(f)
    raw_gear = trend + penalty
    gear = max(0.0, min(5.0, raw_gear))
    if quantize:
        gear = round(gear * 10.0) / 10.0
    base_step = 1.0 + gear  # percent step for 2-tier ladder
    return {
        "gear": gear,
        "trend": trend,
        "penalty": penalty,
        "base_step": base_step,
        "f": f,
    }


def compute_total_deployment(current_name, cur_avg_cost, cur_num_shares, cur_max_volume_krw, cur_market, cur_fx_rate):
    def current_volume_krw(avg_cost, num_shares, market, fx_rate):
        if market == "US":
            return avg_cost * num_shares * fx_rate
        return avg_cost * num_shares

    total_current = current_volume_krw(cur_avg_cost, cur_num_shares, cur_market, cur_fx_rate)

    for name, rec in stock_data.items():
        if name == current_name:
            continue
        try:
            avg = float(rec.get("avg_cost", 0) or 0)
            shares = float(rec.get("num_shares", 0) or 0)
            fx = float(rec.get("fx_rate", GLOBAL_FX_RATE) or 0)
        except (TypeError, ValueError):
            avg = shares = fx = 0.0
        market = rec.get("market", "KR")
        total_current += current_volume_krw(avg, shares, market, fx)

    global_max = GLOBAL_MAX_VOLUME_KRW if GLOBAL_MAX_VOLUME_KRW else cur_max_volume_krw
    return total_current, global_max


def select_load_reference(high_5d, high_10d):
    if high_10d and high_10d > 0:
        return high_10d, "High 10d"
    return 0.0, "High 10d"


def compute_state(parsed, rec, current_name):
    avg_cost = parsed["avg_cost"]
    num_shares = parsed["num_shares"]
    max_volume_krw = parsed["max_volume"]
    market = parsed["market"]
    fx_rate = parsed["fx_rate"]
    g_score = parsed["g_score"]
    l_score = parsed["l_score"]
    v_score = parsed["v_score"]
    units_held = parsed["units_held"]
    unit_size_local = parsed["unit_size_local"]
    manual_load_mode = parsed["manual_load_mode"]
    manual_load_drop = parsed["manual_load_drop"]

    try:
        current_price = float(rec.get("current_price", 0) or 0)
        high_5d = float(rec.get("high_5d", 0) or 0)
        high_10d = float(rec.get("high_10d", 0) or 0)
        low_today = float(rec.get("low_today", 0) or 0)
        high_today = float(rec.get("high_today", 0) or 0)
    except (TypeError, ValueError):
        current_price = high_5d = high_10d = low_today = high_today = 0.0
    last_update = rec.get("last_update", "")

    trend = compute_trend(g_score, l_score)
    auto_load_drop_pct = compute_load_trigger(trend, v_score)
    if manual_load_mode and manual_load_drop > 0:
        load_drop_pct = max(3.0, min(7.0, manual_load_drop))
        load_mode = "Manual"
    else:
        load_drop_pct = auto_load_drop_pct
        load_mode = "Auto"
    high_ref, high_ref_label = select_load_reference(high_5d, high_10d)
    load_trigger = high_ref * (1 - load_drop_pct / 100) if high_ref else 0.0

    total_current, total_max = compute_total_deployment(
        current_name, avg_cost, num_shares, max_volume_krw, market, fx_rate
    )
    total_u = total_current / total_max if total_max else 0.0
    total_units = total_u * PORTFOLIO_N if PORTFOLIO_N else 0.0
    remaining_units = max(0.0, PORTFOLIO_N - total_units) if PORTFOLIO_N else 0.0

    if high_ref <= 0:
        load_status = "Waiting for high"
    elif units_held > 0:
        load_status = "Blocked (units>0)"
    elif remaining_units <= 0:
        load_status = "Blocked (portfolio full)"
    elif remaining_units < 1.0:
        load_status = "Blocked (capacity<1u)"
    else:
        price_check = low_today if low_today > 0 else current_price
        if price_check > 0 and load_trigger > 0 and price_check <= load_trigger:
            load_status = "ACTIVE"
        else:
            load_status = "Watching"

    rescue_trigger, rescue_qty, rescue_gear, rescue_drop_pct, rescue_r = compute_rescue_trigger(
        avg_cost, units_held, total_units, PORTFOLIO_N
    )

    auto_gear = compute_auto_gear(g_score, l_score, total_u)
    manual_step_val = parsed["manual_step"]
    if parsed["manual_mode"]:
        active_step_pct = 1.0 + max(manual_step_val, 0.0)
        sell_mode = "Manual"
    else:
        active_step_pct = auto_gear["base_step"]
        sell_mode = "Auto"

    sell_targets = compute_sell_targets_v1_4(avg_cost, active_step_pct)

    buy_units = 0
    buy_price = 0.0
    buy_drop_pct = 0.0
    buy_r = 0.0
    buy_gear = 0
    buy_label = ""
    if units_held <= 0:
        buy_units = 1 if load_trigger > 0 and remaining_units >= 1.0 else 0
        buy_price = load_trigger
        buy_drop_pct = load_drop_pct
        buy_label = "LOAD"
    else:
        buy_units = rescue_qty
        buy_price = rescue_trigger
        buy_drop_pct = rescue_drop_pct
        buy_r = rescue_r
        buy_gear = rescue_gear
        buy_label = f"G{rescue_gear:.1f}" if rescue_gear else "RESCUE"

    buy_value_local = buy_units * unit_size_local if unit_size_local else 0.0
    if buy_price and buy_units > 0 and buy_value_local > 0:
        buy_shares = max(1, round_half_up(buy_value_local / buy_price))
    else:
        buy_shares = 0
    total_shares = num_shares + buy_shares
    projected_units = units_held + buy_units
    projected_avg = (
        (avg_cost * num_shares + buy_price * buy_shares) / total_shares
        if buy_shares and total_shares
        else 0.0
    )

    return {
        "trend": trend,
        "load_drop_pct": load_drop_pct,
        "load_mode": load_mode,
        "high_5d": high_5d,
        "high_10d": high_10d,
        "high_ref": high_ref,
        "high_ref_label": high_ref_label,
        "load_trigger": load_trigger,
        "load_status": load_status,
        "current_price": current_price,
        "low_today": low_today,
        "high_today": high_today,
        "last_update": last_update,
        "rescue_trigger": rescue_trigger,
        "rescue_qty": rescue_qty,
        "rescue_gear": rescue_gear,
        "rescue_drop_pct": rescue_drop_pct,
        "rescue_r": rescue_r,
        "buy_units": buy_units,
        "buy_price": buy_price,
        "buy_drop_pct": buy_drop_pct,
        "buy_r": buy_r,
        "buy_gear": buy_gear,
        "buy_label": buy_label,
        "buy_value_local": buy_value_local,
        "buy_shares": buy_shares,
        "projected_avg": projected_avg,
        "projected_units": projected_units,
        "projected_shares": int(total_shares) if total_shares else 0,
        "auto_gear": auto_gear,
        "sell_mode": sell_mode,
        "active_step": active_step_pct,
        "sell_targets": sell_targets,
        "total_u": total_u,
        "total_units": total_units,
    }


def parse_form_inputs():
    try:
        def to_float_str(val, default=0.0):
            text = str(val).strip().replace(" ", "").replace(",", "")
            if not text:
                return default
            return float(text)

        avg_cost = to_float_str(avg_cost_var.get(), 0.0)
        num_shares = to_float_str(num_shares_var.get(), 0.0)
        max_volume = to_float_str(max_volume_var.get(), GLOBAL_MAX_VOLUME_KRW or 0.0)
        market = market_var.get()
        fx_rate = to_float_str(fx_rate_var.get(), GLOBAL_FX_RATE) if market == "US" else to_float_str(fx_rate_var.get() or GLOBAL_FX_RATE, GLOBAL_FX_RATE)
        g_score = to_float_str(g_score_var.get())
        l_score = to_float_str(l_score_var.get())
        v_score = to_float_str(v_score_var.get())
        manual_step = to_float_str(manual_gear_var.get(), 0.0)
        manual_load_drop = to_float_str(manual_load_gear_var.get(), 0.0)
        if (
            avg_cost < 0
            or max_volume < 0
            or num_shares < 0
            or fx_rate <= 0
            or not (0 <= g_score <= 5)
            or not (0 <= l_score <= 5)
            or not (0 <= v_score <= 2)
            or manual_step < 0
        ):
            raise ValueError()
    except ValueError:
        messagebox.showerror(
            "Input error",
            "Use non-negative numbers (avg/shares). FX must be > 0. G/L must be between 0 and 5. V must be between 0 and 2. Manual gear >= 0.",
        )
        return None

    units_held, unit_size_krw, position_krw = compute_units_held(
        avg_cost, num_shares, max_volume, market, fx_rate
    )
    unit_size_local = (unit_size_krw / fx_rate) if market == "US" and fx_rate else unit_size_krw

    return {
        "avg_cost": avg_cost,
        "num_shares": num_shares,
        "max_volume": max_volume,
        "market": market,
        "fx_rate": fx_rate,
        "manual_mode": bool(manual_sell_var.get()),
        "manual_step": manual_step,
        "manual_load_mode": bool(manual_load_var.get()),
        "manual_load_drop": manual_load_drop,
        "g_score": g_score,
        "l_score": l_score,
        "v_score": v_score,
        "units_held": units_held,
        "unit_size_krw": unit_size_krw,
        "unit_size_local": unit_size_local,
        "position_krw": position_krw,
        "g_date": g_date_var.get().strip(),
        "l_date": l_date_var.get().strip(),
    }


def fill_form_from_record(name):
    rec = stock_data.get(name, default_record())
    name_var.set(name)
    market_var.set(rec.get("market", "KR"))
    avg_cost_var.set("" if rec["avg_cost"] == "" else format_input(rec["avg_cost"], rec.get("market", "KR")))
    num_shares_var.set("" if rec["num_shares"] == "" else format_input(rec["num_shares"], rec.get("market", "KR"), is_money=False))
    max_volume_var.set("" if rec["max_volume"] == "" else format_input(rec["max_volume"], "KR"))
    fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
    manual_sell_var.set(rec.get("manual_sell_mode", rec.get("manual_mode", 0)))
    try:
        manual_gear_val = float(rec.get("manual_sell_step", rec.get("manual_gear", 0.0)) or 0.0)
    except (TypeError, ValueError):
        manual_gear_val = 0.0
    manual_gear_var.set(manual_gear_val)
    manual_load_var.set(rec.get("manual_load_mode", 0))
    try:
        manual_load_val = float(rec.get("manual_load_drop", 0.0) or 0.0)
    except (TypeError, ValueError):
        manual_load_val = 0.0
    manual_load_gear_var.set(manual_load_val)
    g_val = rec.get("g_score", "")
    l_val = rec.get("l_score", "")
    v_val = rec.get("v_score", "")
    g_score_var.set("" if g_val == "" else format_input(g_val, "KR", is_money=False, decimals=1))
    l_score_var.set("" if l_val == "" else format_input(l_val, "KR", is_money=False, decimals=1))
    v_score_var.set("" if v_val == "" else format_input(v_val, "KR", is_money=False, decimals=2))
    g_date_var.set(rec.get("g_date", ""))
    l_date_var.set(rec.get("l_date", ""))
    update_manual_state()
    update_manual_load_state()
    update_market_state()


def clear_form_fields():
    name_var.set("")
    avg_cost_var.set("")
    num_shares_var.set("")
    units_held_var.set(f"0.00/0.00/{PORTFOLIO_N} units")
    max_volume_var.set("")
    fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
    market_var.set("KR")
    manual_sell_var.set(0)
    manual_gear_var.set(0.0)
    manual_load_var.set(0)
    manual_load_gear_var.set(0.0)
    g_score_var.set("0.0")
    l_score_var.set("0.0")
    v_score_var.set("1.0")
    g_date_var.set("")
    l_date_var.set("")
    update_manual_state()
    update_manual_load_state()
    update_market_state()


def on_select_stock(selected=None):
    choice = selected or name_choice_var.get()
    if not choice:
        clear_form_fields()
        return
    name_choice_var.set(choice)
    fill_form_from_record(choice)
    update_display()


def refresh_name_list(selected=None):
    for child in name_radio_frame.winfo_children():
        child.destroy()
    if not stock_order:
        for nm, mk in DEFAULT_NAMES:
            stock_order.append(nm)
            stock_data[nm] = default_record(mk)
    for nm in stock_order:
        rec = stock_data.get(nm, default_record())
        lbl = f"{nm} ({rec.get('market','KR')})"
        ttk.Radiobutton(
            name_radio_frame,
            text=lbl,
            value=nm,
            variable=name_choice_var,
            command=lambda n=nm: on_select_stock(n),
        ).pack(anchor="w")
    choice = selected if selected and selected in stock_order else (stock_order[0] if stock_order else "")
    if choice:
        name_choice_var.set(choice)
        on_select_stock(choice)
    else:
        clear_form_fields()


def prompt_market_choice():
    dlg = tk.Toplevel(root)
    dlg.title("Select Market")
    dlg.transient(root)
    dlg.grab_set()
    choice_var = tk.StringVar(value="KR")
    ttk.Label(dlg, text="Choose market").grid(row=0, column=0, columnspan=2, pady=6, padx=10)
    ttk.Radiobutton(dlg, text="KR", value="KR", variable=choice_var).grid(row=1, column=0, sticky="w", padx=10)
    ttk.Radiobutton(dlg, text="US", value="US", variable=choice_var).grid(row=1, column=1, sticky="w", padx=10)

    result = {"val": None}

    def ok():
        result["val"] = choice_var.get()
        dlg.destroy()

    def cancel():
        dlg.destroy()

    btn_frame = ttk.Frame(dlg)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=8)
    ttk.Button(btn_frame, text="OK", command=ok).grid(row=0, column=0, padx=6)
    ttk.Button(btn_frame, text="Cancel", command=cancel).grid(row=0, column=1, padx=6)
    dlg.wait_window()
    return result["val"]


def on_add_new():
    new_name = simpledialog.askstring("Add stock", "Enter stock name:", parent=root)
    if not new_name:
        return
    new_name = new_name.strip()
    if not new_name:
        return
    market_choice = prompt_market_choice()
    if not market_choice:
        return
    if new_name in stock_data:
        messagebox.showerror("Duplicate name", f"'{new_name}' already exists.")
        return
    stock_order.append(new_name)
    stock_data[new_name] = default_record(market_choice)
    refresh_name_list(selected=new_name)


def on_delete_stock():
    selected = name_choice_var.get()
    if not selected:
        messagebox.showerror("No selection", "Select a stock to delete.")
        return
    if selected in stock_data:
        del stock_data[selected]
    if selected in stock_order:
        stock_order.remove(selected)
    write_data_file()
    next_sel = stock_order[0] if stock_order else ""
    refresh_name_list(selected=next_sel)


def on_save():
    global GLOBAL_FX_RATE
    parsed = parse_form_inputs()
    if parsed is None:
        return
    selected = name_choice_var.get()
    if not selected:
        messagebox.showerror("No selection", "Select or add a stock before saving.")
        return

    rec = stock_data.get(selected, default_record(parsed["market"]))
    rec.update(
        {
            "avg_cost": parsed["avg_cost"],
            "num_shares": parsed["num_shares"],
            "max_volume": parsed["max_volume"],
            "g_score": parsed["g_score"],
            "l_score": parsed["l_score"],
            "v_score": parsed["v_score"],
            "g_date": parsed["g_date"],
            "l_date": parsed["l_date"],
            "market": parsed["market"],
            "fx_rate": parsed["fx_rate"],
            "units_held": parsed["units_held"],
            "manual_sell_mode": 1 if parsed["manual_mode"] else 0,
            "manual_sell_step": parsed["manual_step"],
            "manual_load_mode": 1 if parsed["manual_load_mode"] else 0,
            "manual_load_drop": parsed["manual_load_drop"],
            # Deprecated fields for backward compatibility
            "manual_mode": 1 if parsed["manual_mode"] else 0,
            "manual_gear": parsed["manual_step"],
        }
    )
    rec["buy_model"] = rec.get("buy_model", list(BUY_MODELS.keys())[0])
    stock_data[selected] = rec
    GLOBAL_FX_RATE = parsed["fx_rate"]
    for _, rec in stock_data.items():
        rec["fx_rate"] = GLOBAL_FX_RATE
    global GLOBAL_MAX_VOLUME_KRW
    GLOBAL_MAX_VOLUME_KRW = parsed["max_volume"]
    for _, rec in stock_data.items():
        rec["max_volume"] = GLOBAL_MAX_VOLUME_KRW
    fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
    max_volume_var.set(format_input(GLOBAL_MAX_VOLUME_KRW, "KR"))
    if selected not in stock_order:
        stock_order.append(selected)

    write_data_file()
    update_display()
    messagebox.showinfo("Saved", f"Saved data for '{selected}'.")


def update_display():
    parsed = parse_form_inputs()
    if parsed is None:
        return

    current_name = name_var.get().strip() or name_choice_var.get()
    if not current_name:
        return
    rec = stock_data.get(current_name, default_record(parsed["market"]))
    data = compute_state(parsed, rec, current_name)

    market = parsed["market"]
    fmt_val = lambda val: fmt_or_na(val, market)
    fmt_price = lambda val: fmt_or_na(val, market) if val and val > 0 else "N/A"
    units_held_var.set(
        f"{parsed['units_held']:.2f}/{data['total_units']:.2f}/{PORTFOLIO_N} units"
    )
    show_load_context = parsed["units_held"] <= 0
    high_context = data["high_ref"] if show_load_context else 0.0
    high_context_label = data["high_ref_label"]

    if parsed["units_held"] > 0 and data["rescue_gear"] > 0:
        rescue_summary = (
            f"Rescue G{data['rescue_gear']:.1f} "
            f"(-{data['rescue_drop_pct']:.1f}%, r={data['rescue_r']:.2f})"
        )
    else:
        drop_pct, r, gear = get_rescue_gear(max(parsed["units_held"], 1.0), PORTFOLIO_N)
        rescue_summary = f"Rescue G{gear:.1f} (-{drop_pct:.1f}%, r={r:.2f})"
    buy_info_var.set(f"Load drop {data['load_drop_pct']:.1f}% ({data['load_mode']}) | {rescue_summary}")

    sell_info_var.set(
        f"{data['sell_mode']} g={data['auto_gear']['gear']:.1f} "
        f"step={data['active_step']:.1f}% -> +{data['active_step']:.1f}%/+{2*data['active_step']:.1f}%"
    )

    gl_text = (
        f"G={parsed['g_score']:.1f} ({parsed['g_date'] or 'date n/a'}), "
        f"L={parsed['l_score']:.1f} ({parsed['l_date'] or 'date n/a'}), "
        f"V={parsed['v_score']:.2f}, T={data['trend']:.2f}"
    )

    result_lines = [
        f"Name: {current_name}",
        gl_text,
        f"Units: {units_held_var.get()} | Avg cost: {fmt_val(parsed['avg_cost'])}",
        f"Current: {fmt_price(data['current_price'])} | Low/High: {fmt_price(data['low_today'])}/{fmt_price(data['high_today'])}",
        f"LOAD: drop {data['load_drop_pct']:.1f}% ({data['load_mode']}) -> {fmt_price(data['load_trigger'])} | Status: {data['load_status']}",
    ]
    if show_load_context:
        result_lines.insert(
            4,
            f"{high_context_label}: {fmt_price(high_context)}",
        )

    if parsed["units_held"] > 0 and data["rescue_gear"] > 0:
        result_lines.append(
            f"RESCUE G{data['rescue_gear']:.1f}: -{data['rescue_drop_pct']:.1f}% "
            f"(r={data['rescue_r']:.2f}) -> {fmt_price(data['rescue_trigger'])} | Buy {data['rescue_qty']:.2f}u"
        )
    else:
        result_lines.append("RESCUE: N/A (no units)")
    if data["buy_shares"] and data["buy_price"]:
        buy_tag = data["buy_label"]
        buy_detail = f"{buy_tag} @ {fmt_price(data['buy_price'])}: {data['buy_units']:.2f}u ~ {data['buy_shares']} sh"
        result_lines.append(buy_detail)

    sell_line = (
        f"SELL {data['sell_mode']}: g={data['auto_gear']['gear']:.1f} "
        f"(T={data['auto_gear']['trend']:.1f}, P={data['auto_gear']['penalty']:.1f}), "
        f"step={data['active_step']:.1f}% (f={data['total_u']*100:.1f}%)"
    )
    result_lines.append(sell_line)
    if parsed["avg_cost"] > 0:
        result_lines.append(f"Tier 1 (50%): {fmt_val(data['sell_targets'][0])} (+{data['active_step']:.1f}%)")
        result_lines.append(f"Tier 2 (50%): {fmt_val(data['sell_targets'][1])} (+{2*data['active_step']:.1f}%)")
    else:
        result_lines.append("Tier targets: N/A (no position)")

    if market == "US":
        result_lines.append(f"FX: {parsed['fx_rate']:.2f}")
    if data["last_update"]:
        result_lines.append(f"Last update: {data['last_update']}")

    result_var.set("\n".join(result_lines))

    plot_levels(
        name=current_name,
        market=market,
        avg_cost=parsed["avg_cost"],
        units_held=parsed["units_held"],
        current_price=data["current_price"],
        high_context=high_context,
        high_context_label=high_context_label,
        rescue_gear=data["rescue_gear"],
        rescue_r=data["rescue_r"],
        buy_price=data["buy_price"],
        buy_label=data["buy_label"],
        buy_drop_pct=data["buy_drop_pct"],
        buy_units=data["buy_units"],
        buy_shares=data["buy_shares"],
        projected_avg=data["projected_avg"],
        projected_units=data["projected_units"],
        projected_shares=data["projected_shares"],
        sell_targets=data["sell_targets"],
        sell_step=data["active_step"],
    )


def on_show():
    update_display()


def plot_levels(
    name,
    market,
    avg_cost,
    units_held,
    current_price,
    high_context,
    high_context_label,
    rescue_gear,
    rescue_r,
    buy_price,
    buy_label,
    buy_drop_pct,
    buy_units,
    buy_shares,
    projected_avg,
    projected_units,
    projected_shares,
    sell_targets,
    sell_step,
):
    fig.clear()
    ax = fig.add_subplot(111)
    x_start, x_end = 0.0, 1.0

    fmt_val = lambda val: fmt_or_na(val, market)
    levels = []

    if high_context and high_context > 0:
        levels.append((high_context_label, high_context, "#777777", ":", "", fmt_val(high_context), 1.4))
    if current_price and current_price > 0:
        levels.append(("Current", current_price, "#333333", "--", "", fmt_val(current_price), 2.0))
    if avg_cost and avg_cost > 0:
        levels.append(("Avg cost", avg_cost, "black", "-", f"units {units_held:.2f}", fmt_val(avg_cost), 3.0))
    if buy_price and buy_price > 0 and buy_units > 0:
        if units_held <= 0:
            color = "#c62828"
            left_text = f"-{buy_drop_pct:.1f}% {buy_units:.2f}u ~ {buy_shares} sh"
            label = "LOAD"
        else:
            gear_key = int(round(rescue_gear)) if rescue_gear else 0
            color = RESCUE_GEAR_COLORS.get(gear_key, "#d32f2f")
            left_text = (
                f"G{rescue_gear:.1f} (-{buy_drop_pct:.1f}%, r={rescue_r:.2f}) "
                f"{buy_units:.2f}u ~ {buy_shares} sh"
            )
            label = f"Buy {buy_label}"
        levels.append((label, buy_price, color, "-", left_text, fmt_val(buy_price), 2.6))
    if projected_avg and projected_avg > 0 and avg_cost and avg_cost > 0:
        proj_text = f"units {projected_units:.2f}, sh {projected_shares}" if projected_shares else ""
        levels.append(("Projected avg", projected_avg, "#999999", "--", proj_text, fmt_val(projected_avg), 1.6))
    if avg_cost and avg_cost > 0 and sell_targets:
        levels.append(("Sell T1 (50%)", sell_targets[0], "#0a8f08", "-", f"+{sell_step:.1f}%", fmt_val(sell_targets[0]), 2.6))
        levels.append(("Sell T2 (50%)", sell_targets[1], "#0066cc", "-.", f"+{2*sell_step:.1f}%", fmt_val(sell_targets[1]), 2.2))

    for label, y, color, style, left_text, right_text, lw in levels:
        ax.plot([x_start, x_end], [y, y], color=color, linestyle=style, linewidth=lw)
        left_label = f"{label} ({left_text})" if left_text else label
        ax.text(
            x_start + 0.01,
            y,
            left_label,
            va="center",
            ha="left",
            fontsize=9,
            color=color,
            backgroundcolor="white",
        )
        ax.text(
            x_end - 0.01,
            y,
            right_text,
            va="center",
            ha="right",
            fontsize=9,
            color=color,
            backgroundcolor="white",
        )

    gap_x = 0.5
    if avg_cost and avg_cost > 0 and buy_price and buy_price > 0:
        ax.plot([gap_x, gap_x], [buy_price, avg_cost], color="#c62828", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x + 0.01,
            (buy_price + avg_cost) / 2,
            f"-{buy_drop_pct:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#c62828",
        )

    if buy_price and projected_avg and projected_avg > 0 and buy_price != projected_avg:
        gap_x2 = 0.72
        proj_gap_pct = ((projected_avg - buy_price) / buy_price * 100) if buy_price else 0.0
        ax.plot([gap_x2, gap_x2], [buy_price, projected_avg], color="#777777", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x2 + 0.01,
            (buy_price + projected_avg) / 2,
            f"+{proj_gap_pct:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#777777",
        )

    if avg_cost and avg_cost > 0 and sell_targets:
        gap_x3 = 0.85
        ax.plot([gap_x3, gap_x3], [avg_cost, sell_targets[0]], color="#0066cc", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x3 + 0.01,
            (avg_cost + sell_targets[0]) / 2,
            f"+{sell_step:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#0066cc",
        )
        ax.plot([gap_x3, gap_x3], [sell_targets[0], sell_targets[1]], color="#0066cc", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x3 + 0.01,
            (sell_targets[0] + sell_targets[1]) / 2,
            f"+{sell_step:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#0066cc",
        )

    if levels:
        prices = [lvl[1] for lvl in levels]
        ymin = min(prices)
        ymax = max(prices)
        pad = (ymax - ymin) * 0.1 if ymax != ymin else max(1, ymax * 0.1)
        ax.set_ylim(ymin - pad, ymax + pad)

    ax.set_xlim(x_start, x_end)
    ax.set_xticks([])
    ax.set_title(name or "")
    ax.set_ylabel("Price")
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    canvas.draw()


def update_manual_label(*args):
    # Update slider label to reflect ladder the user will get
    try:
        step_val = float(manual_gear_var.get())
    except (TypeError, ValueError):
        step_val = 0.0
    effective_step = 1.0 + max(step_val, 0.0)
    label = f"Step {effective_step:.1f}% -> +{effective_step:.1f}% / +{2*effective_step:.1f}%"
    manual_gear_label.config(text=label)
    update_display()


def update_manual_state():
    state_flag = manual_sell_var.get()
    if state_flag:
        manual_slider.state(["!disabled"])
    else:
        manual_slider.state(["disabled"])
    update_manual_label()


def update_manual_load_label(*args):
    try:
        drop_val = float(manual_load_gear_var.get())
    except (TypeError, ValueError):
        drop_val = 0.0
    clamped = max(3.0, min(7.0, drop_val))
    if manual_load_var.get() and abs(clamped - drop_val) > 1e-6:
        manual_load_gear_var.set(clamped)
    manual_load_label.config(text=f"Load drop {clamped:.1f}%")
    update_display()


def update_manual_load_state():
    state_flag = manual_load_var.get()
    if state_flag:
        manual_load_slider.state(["!disabled"])
    else:
        manual_load_slider.state(["disabled"])
    update_manual_load_label()


def update_market_state():
    # Always show FX and keep it editable for both KR and US; for KR it still stores a value.
    fx_entry.state(["!disabled"])
    if not fx_rate_var.get():
        fx_rate_var.set(f"{GLOBAL_FX_RATE:,.2f}")
    if market_var.get() == "US":
        avg_cost_label.config(text="Average Cost ($)")
    else:
        avg_cost_label.config(text="Average Cost (₩)")


# ---------------- UI ----------------
root = tk.Tk()
root.title("AI Seesaw Trading Calculator")

main = ttk.Frame(root, padding=12)
main.grid(sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
main.columnconfigure(0, weight=0)
main.columnconfigure(1, weight=1)
main.rowconfigure(0, weight=1)

name_choice_var = tk.StringVar()
name_var = tk.StringVar()
avg_cost_var = tk.StringVar()
num_shares_var = tk.StringVar()
units_held_var = tk.StringVar(value=f"0.00/0.00/{PORTFOLIO_N} units")
max_volume_var = tk.StringVar()
fx_rate_var = tk.StringVar()
market_var = tk.StringVar(value="KR")
manual_sell_var = tk.IntVar(value=0)
g_score_var = tk.StringVar(value="0.0")
l_score_var = tk.StringVar(value="0.0")
v_score_var = tk.StringVar(value="1.0")
g_date_var = tk.StringVar()
l_date_var = tk.StringVar()
manual_gear_var = tk.DoubleVar(value=0.0)
manual_load_var = tk.IntVar(value=0)
manual_load_gear_var = tk.DoubleVar(value=3.0)
result_var = tk.StringVar()
buy_info_var = tk.StringVar()
sell_info_var = tk.StringVar()

form = ttk.Frame(main)
form.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

ttk.Label(form, text="Stock").grid(row=0, column=0, sticky="ne", padx=4, pady=4)
name_frame = ttk.Frame(form)
name_frame.grid(row=0, column=1, sticky="w", padx=4, pady=4)
name_radio_frame = ttk.Frame(name_frame)
name_radio_frame.grid(row=0, column=0, sticky="w")
name_btn_frame = ttk.Frame(name_frame)
name_btn_frame.grid(row=1, column=0, sticky="w", pady=(6, 0))
ttk.Button(name_btn_frame, text="Add New", command=on_add_new).grid(row=0, column=0, sticky="w", padx=(0, 6))
ttk.Button(name_btn_frame, text="Delete", command=on_delete_stock).grid(row=0, column=1, sticky="w")

avg_cost_label = ttk.Label(form, text="Average Cost (₩)")
avg_cost_label.grid(row=1, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form, textvariable=avg_cost_var, width=16).grid(
    row=1, column=1, sticky="w", padx=4, pady=4
)
ttk.Label(form, text="Number of Stocks").grid(row=2, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form, textvariable=num_shares_var, width=16).grid(
    row=2, column=1, sticky="w", padx=4, pady=4
)

ttk.Label(form, text="stock/deployed/total").grid(row=3, column=0, sticky="e", padx=4, pady=4)
ttk.Label(form, textvariable=units_held_var).grid(
    row=3, column=1, sticky="w", padx=4, pady=4
)

ttk.Label(form, text="Max Volume (₩)").grid(row=4, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form, textvariable=max_volume_var, width=16).grid(
    row=4, column=1, sticky="w", padx=4, pady=4
)

market_frame = ttk.Frame(form)
market_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=4)
ttk.Label(market_frame, text="Market").grid(row=0, column=0, sticky="w", padx=(0, 8))
ttk.Radiobutton(market_frame, text="KR", value="KR", variable=market_var, command=update_market_state).grid(
    row=0, column=1, sticky="w", padx=(0, 8)
)
ttk.Radiobutton(market_frame, text="US", value="US", variable=market_var, command=update_market_state).grid(
    row=0, column=2, sticky="w"
)

fx_frame = ttk.Frame(form)
fx_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4))
ttk.Label(fx_frame, text="FX rate (₩ per $)").grid(row=0, column=0, sticky="e", padx=(0, 8))
fx_entry = ttk.Entry(fx_frame, textvariable=fx_rate_var, width=16)
fx_entry.grid(row=0, column=1, sticky="w")

buy_frame = ttk.LabelFrame(form, text="Buy (Auto)")
buy_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(buy_frame, textvariable=buy_info_var, justify="left").grid(row=0, column=0, sticky="w")

sell_frame = ttk.LabelFrame(form, text="Sell")
sell_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(sell_frame, textvariable=sell_info_var, justify="left").grid(row=0, column=0, sticky="w")

gl_frame = ttk.LabelFrame(form, text="G / L inputs")
gl_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(gl_frame, text="Global G (0-5)").grid(row=0, column=0, sticky="e", padx=4, pady=2)
ttk.Entry(gl_frame, textvariable=g_score_var, width=8).grid(row=0, column=1, sticky="w", padx=4, pady=2)
ttk.Label(gl_frame, text="As-of date").grid(row=0, column=2, sticky="e", padx=4, pady=2)
ttk.Entry(gl_frame, textvariable=g_date_var, width=12).grid(row=0, column=3, sticky="w", padx=4, pady=2)
ttk.Label(gl_frame, text="Local L (0-5)").grid(row=1, column=0, sticky="e", padx=4, pady=2)
ttk.Entry(gl_frame, textvariable=l_score_var, width=8).grid(row=1, column=1, sticky="w", padx=4, pady=2)
ttk.Label(gl_frame, text="As-of date").grid(row=1, column=2, sticky="e", padx=4, pady=2)
ttk.Entry(gl_frame, textvariable=l_date_var, width=12).grid(row=1, column=3, sticky="w", padx=4, pady=2)
ttk.Label(gl_frame, text="Volatility V (0-2)").grid(row=2, column=0, sticky="e", padx=4, pady=2)
ttk.Entry(gl_frame, textvariable=v_score_var, width=8).grid(row=2, column=1, sticky="w", padx=4, pady=2)

manual_frame = ttk.Frame(form)
manual_frame.grid(row=10, column=0, columnspan=2, sticky="w", padx=4, pady=4)
ttk.Checkbutton(
    manual_frame,
    text="Manual load gear",
    variable=manual_load_var,
    command=update_manual_load_state,
).grid(row=0, column=0, sticky="w", pady=(0, 4))
ttk.Label(manual_frame, text="Load drop bar (3-7%)").grid(row=1, column=0, sticky="w")
manual_load_slider = ttk.Scale(
    manual_frame,
    from_=3.0,
    to=7.0,
    orient="horizontal",
    variable=manual_load_gear_var,
    command=update_manual_load_label,
    length=220,
)
manual_load_slider.grid(row=2, column=0, sticky="w", pady=(0, 2))
manual_load_label = ttk.Label(manual_frame, text="")
manual_load_label.grid(row=3, column=0, sticky="w")
ttk.Checkbutton(
    manual_frame,
    text="Manual sell gear",
    variable=manual_sell_var,
    command=update_manual_state,
).grid(row=4, column=0, sticky="w", pady=(6, 4))
ttk.Label(manual_frame, text="Manual gear bar (0-5)").grid(row=5, column=0, sticky="w")
manual_slider = ttk.Scale(
    manual_frame,
    from_=0.0,
    to=5.0,
    orient="horizontal",
    variable=manual_gear_var,
    command=update_manual_label,
    length=220,
)
manual_slider.grid(row=6, column=0, sticky="w", pady=(0, 2))
manual_gear_label = ttk.Label(manual_frame, text="")
manual_gear_label.grid(row=7, column=0, sticky="w")
ttk.Label(manual_frame, text="Base step = 1% + slider (0 -> 1/2, 5 -> 6/12).").grid(
    row=8, column=0, sticky="w"
)

ttk.Button(form, text="Refresh Market Data", command=refresh_market_data).grid(
    row=11, column=0, columnspan=2, pady=(4, 4), sticky="ew"
)
ttk.Button(form, text="Show Result", command=on_show).grid(
    row=12, column=0, columnspan=2, pady=12, sticky="ew"
)
ttk.Button(form, text="Save Result", command=on_save).grid(
    row=13, column=0, columnspan=2, pady=(0, 12), sticky="ew"
)

output = ttk.Frame(main)
output.grid(row=0, column=1, sticky="nsew")
output.columnconfigure(0, weight=1)
output.rowconfigure(1, weight=1)

ttk.Label(output, textvariable=result_var, justify="left").grid(
    row=0, column=0, sticky="nw", pady=(0, 8), padx=(0, 8)
)

fig = Figure(figsize=(6.5, 4.0), dpi=100)
canvas = FigureCanvasTkAgg(fig, master=output)
canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

main.rowconfigure(0, weight=1)
main.columnconfigure(1, weight=1)

load_data()
refresh_name_list()
update_manual_state()
update_manual_load_state()
update_market_state()

root.mainloop()
