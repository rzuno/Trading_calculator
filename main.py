import csv
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.font as tkfont
from math import ceil
from datetime import datetime, timedelta

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

TRAIT_CONFIG_PATH = os.path.join("trait system", "perks.json")
TRAIT_CONFIG = None
TRAIT_SYSTEM = {}
EXCLUSIVE_GROUPS = {}
TRAITS = []
AUTO_TRAITS = []
MANUAL_TRAITS = []
perk_font = None
perk_check_style = None
perk_radio_style = None
bold_label_style = None


def load_trait_config():
    global TRAIT_CONFIG, TRAIT_SYSTEM, EXCLUSIVE_GROUPS, TRAITS, AUTO_TRAITS, MANUAL_TRAITS
    if not os.path.exists(TRAIT_CONFIG_PATH):
        raise FileNotFoundError(f"Missing perk config: {TRAIT_CONFIG_PATH}")
    with open(TRAIT_CONFIG_PATH, "r", encoding="utf-8") as f:
        TRAIT_CONFIG = json.load(f)
    TRAIT_SYSTEM = TRAIT_CONFIG.get("system_config", {})
    EXCLUSIVE_GROUPS = TRAIT_CONFIG.get("exclusive_groups", {})
    TRAITS = TRAIT_CONFIG.get("traits") or TRAIT_CONFIG.get("perks", [])
    AUTO_TRAITS = []
    MANUAL_TRAITS = []
    for trait in TRAITS:
        auto_flag = bool(trait.get("auto", False))
        auto_trigger = trait.get("auto_trigger")
        if auto_flag and auto_trigger:
            AUTO_TRAITS.append(trait)
        else:
            MANUAL_TRAITS.append(trait)


load_trait_config()


DATA_FILE = "data.csv"
DEFAULT_NAMES = [
    ("Samsung", "KR"),
    ("SK hynix", "KR"),
    ("NVIDIA", "US"),
    ("Alphabet", "US"),
]
GLOBAL_FX_RATE = 1300.0  # ₩ per $
GLOBAL_FX_AVG_RATE = GLOBAL_FX_RATE
FX_AVG_DAYS = 20
PORTFOLIO_N = 25  # Total units across all stocks
LOAD_REF_DAYS = 5
HIGH_CONTEXT_DAYS = 10
CURRENCY_NAME = "Dollar"
CURRENCY_MARKET = "FX"

BUY_GEAR_DROPS = {
    1: 3.0,
    2: 4.0,
    3: 5.0,
    4: 6.0,
    5: 7.0,
}

SELL_GEAR_TIERS = {
    0: (1.0, 2.0, 3.0),
    1: (2.0, 4.0, 6.0),
    2: (3.0, 5.0, 7.0),
    3: (4.0, 6.0, 8.0),
    4: (5.0, 7.0, 9.0),
    5: (6.0, 8.0, 10.0),
}

SELL_TIER_WEIGHTS = (0.5, 0.25, 0.25)
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
        "fx_hold_usd": 0.0,
        "max_volume": "",
        "g_score": 0.0,
        "l_score": 0.0,
        "v_score": 1.0,
        "g_date": "",
        "l_date": "",
        "market": market,
        "fx_rate": GLOBAL_FX_RATE if market == "US" else 1.0,
        "latest_trading_day": "",
        "buy_mode": "LOAD",
        "buy_gear": 3,
        "sell_gear": 3,
        # v1.4 new fields
        "units_held": 0,  # Position size for RESCUE gear calculation
        "current_price": "",  # Latest fetched price
        "high_5d": "",  # 5-day high for LOAD calculation
        "high_10d": "",  # 10-day high for context display
        "low_today": "",  # Today's low
        "high_today": "",  # Today's high
        "last_update": "",  # Timestamp of last price fetch
        "roc_1d": 0.0,
        "roc_3d": 0.0,
        "roc_5d": 0.0,
        "atr_3d_pct": 0.0,
        "atr_5d_pct": 0.0,
        "fx_avg": GLOBAL_FX_AVG_RATE,
        "fx_avg_10d": 0.0,
        "fx_slope_10d": 0.0,
        "applied_buy_gear": "",
        "applied_sell_gear": "",
        "applied_buy_points": "",
        "applied_sell_points": "",
        "applied_buy_shift": "",
        "applied_sell_shift": "",
        "applied_action": "",
        "applied_timestamp": "",
        "manual_sell_mode": 0,  # 0=auto, 1=manual
        "manual_sell_step": 0.0,  # Manual override value if enabled
        "manual_load_mode": 0,  # 0=auto, 1=manual
        "manual_load_drop": 0.0,  # Manual load drop override (3-7%)
        "manual_rescue_mode": "AUTO",  # AUTO/DEFAULT/HEAVY/LIGHT
        # Deprecated fields (kept for backward compatibility)
        "buy_model": list(BUY_MODELS.keys())[0],
        "manual_mode": 0,
        "manual_gear": 0.0,
    }


def is_currency_name(name):
    return (name or "").strip().lower() == CURRENCY_NAME.lower()


def load_data():
    global stock_order, stock_data, GLOBAL_FX_RATE, GLOBAL_FX_AVG_RATE, GLOBAL_MAX_VOLUME_KRW
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
                fx_hold_usd = to_float(row.get("fx_hold_usd", 0.0))
                max_volume = to_float(row.get("max_volume", ""))
                market = (row.get("market") or "KR").strip().upper()
                if market not in ("KR", "US", "FX"):
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
                latest_trading_day = (row.get("latest_trading_day") or "").strip()
                buy_mode = (row.get("buy_mode") or "LOAD").strip().upper()
                if buy_mode not in ("LOAD", "RELOAD"):
                    buy_mode = "LOAD"
                buy_gear = to_float(row.get("buy_gear", 3.0))
                if buy_gear == "":
                    buy_gear = 3.0
                buy_gear = clamp_gear(buy_gear, 1.0, 5.0)
                sell_gear = to_float(row.get("sell_gear", 3.0))
                if sell_gear == "":
                    sell_gear = 3.0
                sell_gear = clamp_gear(sell_gear, 1.0, 5.0)

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
                if fx_hold_usd == "":
                    fx_hold_usd = 0.0
                if market == CURRENCY_MARKET and not fx_hold_usd and num_shares not in ("", 0):
                    fx_hold_usd = float(num_shares or 0)

                # v1.4 new fields
                units_held = to_float(row.get("units_held", 0))
                if units_held == "":
                    units_held = 0
                current_price = to_float(row.get("current_price", ""))
                high_5d = to_float(row.get("high_5d", ""))
                high_10d = to_float(row.get("high_10d", ""))
                low_today = to_float(row.get("low_today", ""))
                high_today = to_float(row.get("high_today", ""))
                roc_1d = to_float(row.get("roc_1d", 0.0))
                roc_3d = to_float(row.get("roc_3d", 0.0))
                roc_5d = to_float(row.get("roc_5d", 0.0))
                atr_3d_pct = to_float(row.get("atr_3d_pct", 0.0))
                atr_5d_pct = to_float(row.get("atr_5d_pct", 0.0))
                fx_avg = to_float(row.get("fx_avg", GLOBAL_FX_AVG_RATE))
                fx_avg_10d = to_float(row.get("fx_avg_10d", 0.0))
                fx_slope_10d = to_float(row.get("fx_slope_10d", 0.0))
                applied_buy_gear = to_float(row.get("applied_buy_gear", ""))
                applied_sell_gear = to_float(row.get("applied_sell_gear", ""))
                applied_buy_points = to_float(row.get("applied_buy_points", ""))
                applied_sell_points = to_float(row.get("applied_sell_points", ""))
                applied_buy_shift = to_float(row.get("applied_buy_shift", ""))
                applied_sell_shift = to_float(row.get("applied_sell_shift", ""))
                applied_action = (row.get("applied_action") or "").strip()
                applied_timestamp = (row.get("applied_timestamp") or "").strip()
                last_update = (row.get("last_update") or "").strip()
                manual_sell_mode = int(row.get("manual_sell_mode", 0)) if str(row.get("manual_sell_mode", "0")).isdigit() else 0
                manual_sell_step = to_float(row.get("manual_sell_step", 0.0))
                if manual_sell_step == "":
                    manual_sell_step = 0.0
                manual_load_mode = int(row.get("manual_load_mode", 0)) if str(row.get("manual_load_mode", "0")).isdigit() else 0
                manual_load_drop = to_float(row.get("manual_load_drop", 0.0))
                if manual_load_drop == "":
                    manual_load_drop = 0.0
                manual_rescue_mode = (row.get("manual_rescue_mode") or "AUTO").strip().upper()
                if manual_rescue_mode not in ("AUTO", "DEFAULT", "HEAVY", "LIGHT"):
                    manual_rescue_mode = "AUTO"

                stock_data[name] = {
                    "avg_cost": avg_cost,
                    "num_shares": num_shares,
                    "fx_hold_usd": fx_hold_usd,
                    "max_volume": max_volume,
                    "market": market,
                    "fx_rate": fx_rate,
                    "g_score": g_score,
                    "l_score": l_score,
                    "v_score": v_score,
                    "g_date": g_date,
                    "l_date": l_date,
                    "latest_trading_day": latest_trading_day,
                    "buy_mode": buy_mode,
                    "buy_gear": buy_gear,
                    "sell_gear": sell_gear,
                    # v1.4 fields
                    "units_held": units_held,
                    "current_price": current_price,
                    "high_5d": high_5d,
                    "high_10d": high_10d,
                    "low_today": low_today,
                    "high_today": high_today,
                    "roc_1d": roc_1d if roc_1d != "" else 0.0,
                    "roc_3d": roc_3d if roc_3d != "" else 0.0,
                    "roc_5d": roc_5d if roc_5d != "" else 0.0,
                    "atr_3d_pct": atr_3d_pct if atr_3d_pct != "" else 0.0,
                    "atr_5d_pct": atr_5d_pct if atr_5d_pct != "" else 0.0,
                    "fx_avg": fx_avg if fx_avg != "" else GLOBAL_FX_AVG_RATE,
                    "fx_avg_10d": fx_avg_10d if fx_avg_10d != "" else 0.0,
                    "fx_slope_10d": fx_slope_10d if fx_slope_10d != "" else 0.0,
                    "applied_buy_gear": applied_buy_gear,
                    "applied_sell_gear": applied_sell_gear,
                    "applied_buy_points": applied_buy_points,
                    "applied_sell_points": applied_sell_points,
                    "applied_buy_shift": applied_buy_shift,
                    "applied_sell_shift": applied_sell_shift,
                    "applied_action": applied_action,
                    "applied_timestamp": applied_timestamp,
                    "last_update": last_update,
                    "manual_sell_mode": manual_sell_mode,
                    "manual_sell_step": manual_sell_step,
                    "manual_load_mode": manual_load_mode,
                    "manual_load_drop": manual_load_drop,
                    "manual_rescue_mode": manual_rescue_mode,
                    # Deprecated (backward compatibility)
                    "buy_model": row.get("buy_model", list(BUY_MODELS.keys())[0]),
                    "manual_mode": manual_mode,
                    "manual_gear": manual_gear_val,
                }
                stock_order.append(name)
                # Allow FX to be set from any row if a realistic value is present (>10 avoids overwriting with 1)
                if fx_rate and fx_rate > 10:
                    GLOBAL_FX_RATE = fx_rate
                if fx_avg and fx_avg > 10:
                    GLOBAL_FX_AVG_RATE = fx_avg
                if max_volume and max_volume > 0:
                    GLOBAL_MAX_VOLUME_KRW = max_volume
    if not stock_order:
        for nm, mk in DEFAULT_NAMES:
            stock_order.append(nm)
            stock_data[nm] = default_record(mk)

    # After loading, propagate global FX to all records
    if not GLOBAL_FX_AVG_RATE or GLOBAL_FX_AVG_RATE <= 0:
        GLOBAL_FX_AVG_RATE = GLOBAL_FX_RATE
    for rec in stock_data.values():
        rec["fx_rate"] = GLOBAL_FX_RATE
        rec["fx_avg"] = GLOBAL_FX_AVG_RATE

    if CURRENCY_NAME not in stock_data:
        stock_data[CURRENCY_NAME] = default_record(CURRENCY_MARKET)
    if CURRENCY_NAME in stock_order:
        stock_order = [name for name in stock_order if name != CURRENCY_NAME]
    stock_order.append(CURRENCY_NAME)


def write_data_file():
    fieldnames = [
        "name",
        "avg_cost",
        "num_shares",
        "fx_hold_usd",
        "max_volume",
        "g_score",
        "l_score",
        "v_score",
        "g_date",
        "l_date",
        "market",
        "fx_rate",
        "latest_trading_day",
        "buy_mode",
        "buy_gear",
        "sell_gear",
        # v1.4 new fields
        "units_held",
        "current_price",
        "high_5d",
        "high_10d",
        "low_today",
        "high_today",
        "roc_1d",
        "roc_3d",
        "roc_5d",
        "atr_3d_pct",
        "atr_5d_pct",
        "fx_avg",
        "fx_avg_10d",
        "fx_slope_10d",
        "applied_buy_gear",
        "applied_sell_gear",
        "applied_buy_points",
        "applied_sell_points",
        "applied_buy_shift",
        "applied_sell_shift",
        "applied_action",
        "applied_timestamp",
        "last_update",
        "manual_sell_mode",
        "manual_sell_step",
        "manual_load_mode",
        "manual_load_drop",
        "manual_rescue_mode",
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
                    "fx_hold_usd": rec.get("fx_hold_usd", 0.0),
                    "max_volume": rec.get("max_volume", ""),
                    "g_score": rec.get("g_score", ""),
                    "l_score": rec.get("l_score", ""),
                    "v_score": rec.get("v_score", ""),
                    "g_date": rec.get("g_date", ""),
                    "l_date": rec.get("l_date", ""),
                    "market": rec.get("market", "KR"),
                    "fx_rate": rec.get("fx_rate", GLOBAL_FX_RATE if rec.get("market", "KR") == "US" else 1.0),
                    "latest_trading_day": rec.get("latest_trading_day", ""),
                    "buy_mode": rec.get("buy_mode", "LOAD"),
                    "buy_gear": rec.get("buy_gear", 3),
                    "sell_gear": rec.get("sell_gear", 3),
                    # v1.4 fields
                    "units_held": rec.get("units_held", 0),
                    "current_price": rec.get("current_price", ""),
                    "high_5d": rec.get("high_5d", ""),
                    "high_10d": rec.get("high_10d", ""),
                    "low_today": rec.get("low_today", ""),
                    "high_today": rec.get("high_today", ""),
                    "roc_1d": rec.get("roc_1d", 0.0),
                    "roc_3d": rec.get("roc_3d", 0.0),
                    "roc_5d": rec.get("roc_5d", 0.0),
                    "atr_3d_pct": rec.get("atr_3d_pct", 0.0),
                    "atr_5d_pct": rec.get("atr_5d_pct", 0.0),
                    "fx_avg": rec.get("fx_avg", GLOBAL_FX_AVG_RATE),
                    "fx_avg_10d": rec.get("fx_avg_10d", 0.0),
                    "fx_slope_10d": rec.get("fx_slope_10d", 0.0),
                    "applied_buy_gear": rec.get("applied_buy_gear", ""),
                    "applied_sell_gear": rec.get("applied_sell_gear", ""),
                    "applied_buy_points": rec.get("applied_buy_points", ""),
                    "applied_sell_points": rec.get("applied_sell_points", ""),
                    "applied_buy_shift": rec.get("applied_buy_shift", ""),
                    "applied_sell_shift": rec.get("applied_sell_shift", ""),
                    "applied_action": rec.get("applied_action", ""),
                    "applied_timestamp": rec.get("applied_timestamp", ""),
                    "last_update": rec.get("last_update", ""),
                    "manual_sell_mode": rec.get("manual_sell_mode", 0),
                    "manual_sell_step": rec.get("manual_sell_step", 0.0),
                    "manual_load_mode": rec.get("manual_load_mode", 0),
                    "manual_load_drop": rec.get("manual_load_drop", 0.0),
                    "manual_rescue_mode": rec.get("manual_rescue_mode", "AUTO"),
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
        if market == "FX":
            return f"₩{val:,.0f}"
        return f"₩{val:,.0f}"
    except (TypeError, ValueError):
        return ""


def fmt_or_na(val, market="KR"):
    formatted = fmt_money(val, market)
    return formatted if formatted else "N/A"


def fmt_compact(val):
    try:
        text = f"{float(val):.2f}"
        return text.rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return ""


def fmt_points(val):
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "0"
    if abs(val - round(val)) < 1e-6:
        return f"{int(round(val)):+d}"
    return f"{val:+.1f}"


def fmt_ratio(val):
    try:
        ratio = float(val)
    except (TypeError, ValueError):
        return "0:1"
    if abs(ratio - round(ratio)) < 1e-6:
        return f"{int(round(ratio))}:1"
    return f"{ratio:.1f}:1"


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
            if market == "FX":
                return f"{val:,.{decimals}f}"
            return f"{val:,.0f}"
        return f"{val:,.{decimals}f}"
    except (TypeError, ValueError):
        return ""


def parse_yymmdd(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 8:
        digits = digits[2:]
    if len(digits) != 6:
        return None
    try:
        yy = int(digits[:2])
        mm = int(digits[2:4])
        dd = int(digits[4:6])
        return datetime(2000 + yy, mm, dd).date()
    except ValueError:
        return None


def trading_days_since(value):
    last = parse_yymmdd(value)
    if not last:
        return 0
    today = datetime.now().date()
    if last >= today:
        return 0
    days = 0
    cursor = last
    while cursor < today:
        cursor = cursor + timedelta(days=1)
        if cursor.weekday() < 5:
            days += 1
    return days


def safe_eval(expr, metrics):
    if not expr:
        return False
    try:
        return bool(eval(expr, {"__builtins__": {}}, metrics))
    except Exception:
        return False


def clamp_gear(val, lo=1.0, hi=5.0):
    return max(lo, min(hi, val))


def compute_trait_metrics(parsed, data):
    current = float(data.get("current_price", 0) or 0)
    high_5d = float(data.get("high_5d", 0) or 0)
    high_10d = float(data.get("high_10d", 0) or 0)
    low_today = float(data.get("low_today", 0) or 0)
    roc_1d = float(data.get("roc_1d", 0) or 0)
    roc_3d = float(data.get("roc_3d", 0) or 0)
    roc_5d = float(data.get("roc_5d", 0) or 0)
    atr_3d_pct = float(data.get("atr_3d_pct", 0) or 0)
    atr_5d_pct = float(data.get("atr_5d_pct", 0) or 0)
    avg_cost = float(parsed.get("avg_cost", 0) or 0)
    if float(parsed.get("num_shares", 0) or 0) <= 0:
        avg_cost = 0.0

    ref = high_5d if high_5d > 0 else high_10d
    atr_pct = ((high_5d - low_today) / current * 100) if current > 0 and high_5d > 0 and low_today > 0 else 0.0
    roc = ((current - ref) / ref * 100) if current > 0 and ref > 0 else 0.0
    deployed_pct = float(data.get("total_u", 0) or 0) * 100.0
    pnl_pct = ((current - avg_cost) / avg_cost * 100) if avg_cost > 0 and current > 0 else 0.0
    fx_current = float(parsed.get("fx_rate", 0) or 0)
    fx_avg = float(GLOBAL_FX_AVG_RATE or fx_current)
    fx_vs_avg = ((fx_current - fx_avg) / fx_avg * 100) if fx_avg > 0 else 0.0
    is_us_stock = parsed.get("market") == "US"
    is_fx = parsed.get("market") == CURRENCY_MARKET
    idle_days = trading_days_since(parsed.get("latest_trading_day", ""))

    return {
        "atr_pct": atr_pct,
        "roc": roc,
        "roc_1d": roc_1d,
        "roc_3d": roc_3d,
        "roc_5d": roc_5d,
        "atr_3d_pct": atr_3d_pct,
        "atr_5d_pct": atr_5d_pct,
        "deployed_pct": deployed_pct,
        "pnl_pct": pnl_pct,
        "fx_current": fx_current,
        "fx_avg": fx_avg,
        "fx_vs_avg": fx_vs_avg,
        "is_us_stock": is_us_stock,
        "is_fx": is_fx,
        "idle_days": idle_days,
        "days_idle": idle_days,
    }


def evaluate_traits(metrics, manual_states):
    active_auto = []
    active_manual = []
    is_fx = bool(metrics.get("is_fx", False))
    for trait in AUTO_TRAITS:
        is_fx_trait = trait.get("exclusive_group") == "fx" or trait.get("category") == "fx"
        if is_fx:
            if not is_fx_trait:
                continue
        else:
            if is_fx_trait:
                continue
        if safe_eval(trait.get("auto_trigger"), metrics):
            active_auto.append(trait)
    if not is_fx:
        for trait in MANUAL_TRAITS:
            if manual_states.get(trait["id"], False):
                active_manual.append(trait)
    return active_auto, active_manual


def compute_perk_gears(metrics, manual_states):
    buy_points = 0.0
    sell_points = 0.0
    active_auto, active_manual = evaluate_traits(metrics, manual_states)
    filtered_auto = []
    seen_groups = set()
    for trait in active_auto:
        group = trait.get("exclusive_group")
        if group and group in seen_groups:
            continue
        if group:
            seen_groups.add(group)
        filtered_auto.append(trait)
    active_auto = filtered_auto
    active = active_auto + active_manual
    for trait in active:
        buy_points += trait.get("buy_points", 0)
        sell_points += trait.get("sell_points", 0)

    ratio = float(TRAIT_SYSTEM.get("point_to_gear_ratio", 10.0))
    base_buy = float(TRAIT_SYSTEM.get("base_buy_gear", 3.0))
    base_sell = float(TRAIT_SYSTEM.get("base_sell_gear", 3.0))
    gear_min = float(TRAIT_SYSTEM.get("gear_min", 1.0))
    gear_max = float(TRAIT_SYSTEM.get("gear_max", 5.0))

    buy_shift = buy_points / ratio if ratio else 0.0
    sell_shift = sell_points / ratio if ratio else 0.0
    raw_buy = base_buy + buy_shift
    raw_sell = base_sell + sell_shift
    buy_gear = clamp_gear(raw_buy, gear_min, gear_max)
    sell_gear = clamp_gear(raw_sell, gear_min, gear_max)

    if manual_states.get("black_swan"):
        sell_gear = 0.0

    return {
        "buy_points": buy_points,
        "sell_points": sell_points,
        "buy_shift": buy_shift,
        "sell_shift": sell_shift,
        "buy_gear": buy_gear,
        "sell_gear": sell_gear,
        "active_auto": active_auto,
        "active_manual": active_manual,
        "ratio": ratio,
        "base_buy": base_buy,
        "base_sell": base_sell,
    }


def normalize_last_trade(value):
    text = str(value).strip()
    if not text:
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 8:
        digits = digits[2:]
    if len(digits) == 6:
        return digits
    return text


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


def compute_rescue_trigger(avg_cost, units_held, total_units, N, drop_pct=None, r=None, gear=None):
    """
    RESCUE trigger price and buy quantity (v1.4).

    Returns: (trigger_price, buy_units, gear, drop_pct, r) tuple
    """
    if units_held <= 0:
        return avg_cost, 0, 0, 0.0, 0.0  # LOAD only when empty

    if drop_pct is None or r is None:
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


def compute_buy_drop_pct(buy_gear):
    try:
        gear = float(buy_gear)
    except (TypeError, ValueError):
        gear = 3.0
    return 2.0 + gear


def compute_sell_targets_3tier(avg_cost, sell_gear):
    try:
        gear = float(sell_gear)
    except (TypeError, ValueError):
        gear = 3.0
    if gear <= 0:
        tiers = (1.0, 2.0, 3.0)
    else:
        tier1 = 1.0 + gear
        tiers = (tier1, tier1 + 2.0, tier1 + 4.0)
    targets = [avg_cost * (1 + pct / 100) for pct in tiers]
    return targets, tiers


# ===== YAHOO FINANCE DATA FETCHING =====

def fetch_current_price(stock_name):
    """
    Fetch current price and recent highs for stock from Yahoo Finance.

    Returns: dict with keys:
        'current': float - current/close price
        'high_5d': float - highest high of past 5 days (excluding today when possible)
        'high_10d': float - highest high of past 10 days (includes today's high when available)
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

        # Get recent history for highs and indicators
        hist_days = HIGH_CONTEXT_DAYS + 5
        hist = stock.history(period=f"{hist_days}d", interval="1d", prepost=True)
        if hist.empty:
            return None

        def compute_roc(close_series, periods):
            if close_series is None or len(close_series) <= periods:
                return 0.0
            current = float(close_series.iloc[-1])
            past = float(close_series.iloc[-1 - periods])
            if past == 0:
                return 0.0
            return (current - past) / past * 100.0

        def compute_atr_pct(hist_frame, periods):
            if hist_frame is None or hist_frame.empty:
                return 0.0
            highs = hist_frame["High"]
            lows = hist_frame["Low"]
            closes = hist_frame["Close"]
            prev_close = closes.shift(1)
            tr = (highs - lows).to_frame("hl")
            tr["hc"] = (highs - prev_close).abs()
            tr["lc"] = (lows - prev_close).abs()
            tr_val = tr.max(axis=1).dropna()
            if len(tr_val) < periods:
                return 0.0
            atr = float(tr_val.tail(periods).mean())
            last_close = float(closes.iloc[-1]) if len(closes) else 0.0
            return (atr / last_close * 100.0) if last_close > 0 else 0.0

        def as_float(value):
            try:
                if hasattr(value, "size") and value.size == 1 and hasattr(value, "item"):
                    return float(value.item())
            except Exception:
                pass
            try:
                if hasattr(value, "iloc"):
                    return float(value.iloc[0])
            except Exception:
                pass
            return float(value)

        hist_completed = hist.iloc[:-1] if len(hist) > 1 else hist
        if hist_completed.empty:
            hist_completed = hist
        high_10d = hist["High"].tail(HIGH_CONTEXT_DAYS).max()
        high_5d = hist_completed["High"].tail(LOAD_REF_DAYS).max()
        atr_3d_pct = compute_atr_pct(hist, 3)
        atr_5d_pct = compute_atr_pct(hist, 5)

        current = None
        low_today = None
        high_today = None

        intraday = yf.download(
            ticker,
            period="1d",
            interval="1m",
            prepost=True,
            progress=False,
            auto_adjust=False,
        )
        if not intraday.empty:
            current = as_float(intraday["Close"].iloc[-1])
            low_today = as_float(intraday["Low"].min())
            high_today = as_float(intraday["High"].max())

        if current is None:
            intraday_5m = yf.download(
                ticker,
                period="5d",
                interval="5m",
                prepost=True,
                progress=False,
                auto_adjust=False,
            )
            if not intraday_5m.empty:
                current = as_float(intraday_5m["Close"].iloc[-1])
                low_today = as_float(intraday_5m["Low"].iloc[-1])
                high_today = as_float(intraday_5m["High"].iloc[-1])

        if current is None:
            try:
                fast = stock.fast_info
                if fast:
                    current = fast.get("last_price") or fast.get("regular_market_price")
                    low_today = fast.get("day_low")
                    high_today = fast.get("day_high")
            except Exception:
                pass

        if current is None:
            current = float(hist["Close"].iloc[-1])

        if low_today is None:
            low_today = as_float(hist["Low"].iloc[-1])
        if high_today is None:
            high_today = as_float(hist["High"].iloc[-1])

        if high_today is not None and high_today > 0:
            high_10d = max(high_10d, float(high_today))

        close_series = hist["Close"].copy()
        if not close_series.empty and current:
            close_series.iloc[-1] = float(current)

        roc_1d = 0.0
        if len(close_series) >= 2:
            prev_close = float(close_series.iloc[-2])
            roc_1d = ((float(current) - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
        roc_3d = compute_roc(close_series, 3)
        roc_5d = compute_roc(close_series, 5)

        return {
            'current': float(current),
            'high_5d': high_5d,
            'high_10d': high_10d,
            'low_today': float(low_today),
            'high_today': float(high_today),
            'roc_1d': roc_1d,
            'roc_3d': roc_3d,
            'roc_5d': roc_5d,
            'atr_3d_pct': atr_3d_pct,
            'atr_5d_pct': atr_5d_pct,
            'timestamp': datetime.now()
        }
    except Exception as e:
        print(f"Error fetching {stock_name}: {e}")
        return None


def fetch_fx_rate():
    """
    Fetch USD/KRW exchange rate from Yahoo Finance.

    Returns: dict with keys: current, avg, avg_10d, slope_10d (or None on failure)
    """
    if not YFINANCE_AVAILABLE:
        return None

    try:
        fx = yf.Ticker("KRW=X")
        hist = fx.history(period="30d", interval="1d", prepost=True)
        if hist.empty:
            return None
        current = None
        intraday = fx.history(period="1d", interval="1m", prepost=True)
        if not intraday.empty:
            current = float(intraday["Close"].iloc[-1])
        if current is None:
            current = float(hist["Close"].iloc[-1])
        close_series = hist["Close"]
        avg_series = close_series.tail(FX_AVG_DAYS) if len(close_series) >= FX_AVG_DAYS else close_series
        avg = float(avg_series.mean()) if not avg_series.empty else float(current)
        tail_10d = close_series.tail(10)
        avg_10d = float(tail_10d.mean()) if not tail_10d.empty else float(current)
        slope_10d = 0.0
        if len(tail_10d) >= 2:
            first = float(tail_10d.iloc[0])
            last = float(tail_10d.iloc[-1])
            if first > 0:
                slope_10d = (last - first) / first * 100.0
        return {
            "current": float(current),
            "avg": avg,
            "avg_10d": avg_10d,
            "slope_10d": slope_10d,
        }
    except Exception as e:
        print(f"Error fetching FX rate: {e}")
    return None


# ===== END YAHOO FINANCE FUNCTIONS =====


def refresh_market_data():
    global GLOBAL_FX_RATE, GLOBAL_FX_AVG_RATE
    if not YFINANCE_AVAILABLE:
        messagebox.showerror("Unavailable", "yfinance is not installed. Price fetching disabled.")
        return

    current_name = get_current_stock_name()

    new_fx = fetch_fx_rate()
    if new_fx and new_fx.get("current", 0) > 10:
        GLOBAL_FX_RATE = new_fx["current"]
        GLOBAL_FX_AVG_RATE = new_fx.get("avg", GLOBAL_FX_RATE)
        fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))

    for stock_name in stock_order:
        if is_currency_name(stock_name) or stock_data.get(stock_name, {}).get("market") == CURRENCY_MARKET:
            continue
        price_data = fetch_current_price(stock_name)
        if not price_data:
            continue
        rec = stock_data.get(stock_name, default_record())
        rec["current_price"] = price_data["current"]
        rec["high_5d"] = price_data["high_5d"]
        rec["high_10d"] = price_data["high_10d"]
        rec["low_today"] = price_data["low_today"]
        rec["high_today"] = price_data["high_today"]
        rec["roc_1d"] = price_data.get("roc_1d", 0.0)
        rec["roc_3d"] = price_data.get("roc_3d", 0.0)
        rec["roc_5d"] = price_data.get("roc_5d", 0.0)
        rec["atr_3d_pct"] = price_data.get("atr_3d_pct", 0.0)
        rec["atr_5d_pct"] = price_data.get("atr_5d_pct", 0.0)
        rec["last_update"] = price_data["timestamp"].strftime("%Y-%m-%d %H:%M")
        rec["fx_rate"] = GLOBAL_FX_RATE
        rec["fx_avg"] = GLOBAL_FX_AVG_RATE
        stock_data[stock_name] = rec

    if is_currency_name(CURRENCY_NAME):
        fx_rec = stock_data.get(CURRENCY_NAME, default_record(CURRENCY_MARKET))
        if new_fx and new_fx.get("current", 0) > 0:
            fx_rec["current_price"] = new_fx["current"]
            fx_rec["fx_avg"] = new_fx.get("avg", GLOBAL_FX_AVG_RATE)
            fx_rec["fx_avg_10d"] = new_fx.get("avg_10d", 0.0)
            fx_rec["fx_slope_10d"] = new_fx.get("slope_10d", 0.0)
            fx_rec["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        stock_data[CURRENCY_NAME] = fx_rec

    write_data_file()
    load_data()
    if current_name:
        refresh_name_list(selected=current_name)
    else:
        refresh_name_list()
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
        if name == current_name or is_currency_name(name) or rec.get("market") == CURRENCY_MARKET:
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


def select_buy_reference(high_5d, high_10d, buy_mode):
    if buy_mode == "LOAD":
        if high_10d and high_10d > 0:
            return high_10d, "High 10d"
        if high_5d and high_5d > 0:
            return high_5d, "High 5d"
        return 0.0, "High 10d"
    if high_5d and high_5d > 0:
        return high_5d, "High 5d"
    if high_10d and high_10d > 0:
        return high_10d, "High 10d"
    return 0.0, "High 5d"


def compute_state(parsed, rec, current_name):
    avg_cost = parsed["avg_cost"]
    num_shares = parsed["num_shares"]
    max_volume_krw = parsed["max_volume"]
    market = parsed["market"]
    fx_rate = parsed["fx_rate"]
    units_held = parsed["units_held"]
    unit_size_local = parsed["unit_size_local"]
    manual_rescue_mode = parsed["manual_rescue_mode"]
    buy_gear = parsed["buy_gear"]
    sell_gear = parsed["sell_gear"]

    if num_shares <= 0:
        avg_cost = 0.0

    try:
        current_price = float(rec.get("current_price", 0) or 0)
        high_5d = float(rec.get("high_5d", 0) or 0)
        high_10d = float(rec.get("high_10d", 0) or 0)
        low_today = float(rec.get("low_today", 0) or 0)
        high_today = float(rec.get("high_today", 0) or 0)
        roc_1d = float(rec.get("roc_1d", 0) or 0)
        roc_3d = float(rec.get("roc_3d", 0) or 0)
        roc_5d = float(rec.get("roc_5d", 0) or 0)
        atr_3d_pct = float(rec.get("atr_3d_pct", 0) or 0)
        atr_5d_pct = float(rec.get("atr_5d_pct", 0) or 0)
    except (TypeError, ValueError):
        current_price = high_5d = high_10d = low_today = high_today = 0.0
        roc_1d = roc_3d = roc_5d = 0.0
        atr_3d_pct = atr_5d_pct = 0.0
    last_update = rec.get("last_update", "")

    buy_mode = "LOAD" if num_shares <= 0 else "RELOAD"
    buy_drop_pct = compute_buy_drop_pct(buy_gear)
    high_ref, high_ref_label = select_buy_reference(high_5d, high_10d, buy_mode)
    buy_trigger = high_ref * (1 - buy_drop_pct / 100) if high_ref else 0.0

    total_current, total_max = compute_total_deployment(
        current_name, avg_cost, num_shares, max_volume_krw, market, fx_rate
    )
    total_u = total_current / total_max if total_max else 0.0
    total_units = total_u * PORTFOLIO_N if PORTFOLIO_N else 0.0
    remaining_units = max(0.0, PORTFOLIO_N - total_units) if PORTFOLIO_N else 0.0

    if high_ref <= 0:
        buy_status = "Waiting for high"
    elif buy_mode == "LOAD" and num_shares > 0:
        buy_status = "Blocked (shares>0)"
    elif buy_mode == "RELOAD" and num_shares <= 0:
        buy_status = "Blocked (shares=0)"
    elif remaining_units <= 0:
        buy_status = "Blocked (portfolio full)"
    elif remaining_units < 1.0:
        buy_status = "Blocked (capacity<1u)"
    else:
        price_check = low_today if low_today > 0 else current_price
        if price_check > 0 and buy_trigger > 0 and price_check <= buy_trigger:
            buy_status = "ACTIVE"
        else:
            buy_status = "Watching"

    rescue_override = None
    rescue_label = "Auto"
    if manual_rescue_mode != "AUTO":
        if manual_rescue_mode == "LIGHT":
            rescue_override = (4.0, 0.5, 1)
            rescue_label = "Light"
        elif manual_rescue_mode == "HEAVY":
            rescue_override = (6.0, 0.7, 3)
            rescue_label = "Heavy"
        else:
            rescue_override = (5.0, 0.6, 2)
            rescue_label = "Default"

    if rescue_override:
        rescue_drop_pct, rescue_r, rescue_gear = rescue_override
        rescue_trigger, rescue_qty, _, _, _ = compute_rescue_trigger(
            avg_cost, units_held, total_units, PORTFOLIO_N, rescue_drop_pct, rescue_r, rescue_gear
        )
    else:
        rescue_trigger, rescue_qty, rescue_gear, rescue_drop_pct, rescue_r = compute_rescue_trigger(
            avg_cost, units_held, total_units, PORTFOLIO_N
        )

    sell_targets, sell_tiers = compute_sell_targets_3tier(avg_cost, sell_gear)

    buy_units = 0
    buy_price = 0.0
    buy_label = buy_mode
    if buy_mode == "LOAD" and num_shares <= 0:
        if buy_trigger > 0:
            buy_price = buy_trigger
            buy_units = 1 if remaining_units >= 1.0 else 0
        buy_label = "LOAD"
    elif buy_mode == "RELOAD" and num_shares > 0:
        if buy_trigger > 0:
            buy_price = buy_trigger
            buy_units = 1 if remaining_units >= 1.0 else 0
        buy_label = "RELOAD"

    buy_value_local = buy_units * unit_size_local if unit_size_local else 0.0
    if buy_price and buy_units > 0 and buy_value_local > 0:
        buy_shares = max(1, round_half_up(buy_value_local / buy_price))
    else:
        buy_shares = 0
    projected_avg = 0.0
    projected_units = units_held
    projected_shares = int(num_shares) if num_shares else 0
    rescue_shares = 0
    if rescue_trigger and rescue_qty > 0 and unit_size_local:
        rescue_value_local = rescue_qty * unit_size_local
        rescue_shares = max(1, round_half_up(rescue_value_local / rescue_trigger))
    if rescue_shares and num_shares:
        total_shares = num_shares + rescue_shares
        projected_units = units_held + rescue_qty
        projected_avg = (avg_cost * num_shares + rescue_trigger * rescue_shares) / total_shares
        projected_shares = int(total_shares)

    return {
        "buy_mode": buy_mode,
        "buy_drop_pct": buy_drop_pct,
        "high_5d": high_5d,
        "high_10d": high_10d,
        "high_ref": high_ref,
        "high_ref_label": high_ref_label,
        "buy_trigger": buy_trigger,
        "buy_status": buy_status,
        "current_price": current_price,
        "low_today": low_today,
        "high_today": high_today,
        "roc_1d": roc_1d,
        "roc_3d": roc_3d,
        "roc_5d": roc_5d,
        "atr_3d_pct": atr_3d_pct,
        "atr_5d_pct": atr_5d_pct,
        "last_update": last_update,
        "rescue_trigger": rescue_trigger,
        "rescue_qty": rescue_qty,
        "rescue_gear": rescue_gear,
        "rescue_drop_pct": rescue_drop_pct,
        "rescue_r": rescue_r,
        "rescue_mode": rescue_label if rescue_override else "Auto",
        "buy_units": buy_units,
        "buy_price": buy_price,
        "buy_drop_pct": buy_drop_pct,
        "buy_gear": buy_gear,
        "buy_label": buy_label,
        "buy_value_local": buy_value_local,
        "buy_shares": buy_shares,
        "projected_avg": projected_avg,
        "projected_units": projected_units,
        "projected_shares": projected_shares,
        "rescue_shares": rescue_shares,
        "sell_targets": sell_targets,
        "sell_tiers": sell_tiers,
        "sell_gear": sell_gear,
        "total_u": total_u,
        "total_units": total_units,
    }


def format_delta(delta):
    if delta > 0:
        return f"+{delta}"
    if delta < 0:
        return f"{delta}"
    return "0"


def format_recommendation_text(rec, current_buy_gear, current_sell_gear):
    if not rec:
        return "No recommendation available."
    buy_delta = format_delta(rec.get("delta_buy", 0))
    sell_delta = format_delta(rec.get("delta_sell", 0))
    confidence = rec.get("confidence", 0.0)
    adjustments = rec.get("adjustments", [])
    total_sell = 0
    adj_parts = []
    for source, delta in adjustments:
        if delta:
            total_sell += delta
            adj_parts.append(f"{source} {format_delta(delta)}")
    if adj_parts:
        adj_line = f"Sell adj total {format_delta(total_sell)} ({', '.join(adj_parts)})"
    else:
        adj_line = "Sell adj total 0"
    if rec.get("clamped"):
        adj_line = f"{adj_line} [clamped]"
    return "\n".join(
        [
            f"Model: {rec.get('model', 'N/A')}",
            f"Status: {rec.get('status', 'N/A')} (conf {confidence:.2f})",
            adj_line,
            f"Sell gear: {current_sell_gear} -> {rec.get('sell_gear', current_sell_gear)} ({sell_delta})",
            f"Buy gear: {current_buy_gear} -> {rec.get('buy_gear', current_buy_gear)} ({buy_delta})",
            f"Notes: {rec.get('notes', '')}",
        ]
    )


def get_current_stock_name():
    return name_var.get().strip() or name_choice_var.get()

def get_rec_state(stock_name):
    if stock_name not in rec_states:
        rec_states[stock_name] = {"latest": None}
    return rec_states[stock_name]


def get_base_gears():
    base_buy = float(TRAIT_SYSTEM.get("base_buy_gear", 3.0))
    base_sell = float(TRAIT_SYSTEM.get("base_sell_gear", 3.0))
    return base_buy, base_sell


def update_apply_status_display(stock_name):
    if not stock_name or stock_name not in stock_data:
        apply_status_var.set("")
        apply_status_label.config(fg="#b71c1c")
        return
    rec = stock_data[stock_name]
    action = rec.get("applied_action", "")
    ts = rec.get("applied_timestamp", "")
    if not action:
        apply_status_var.set("No change has been made.")
        apply_status_label.config(fg="#b71c1c")
        return
    if action == "applied":
        buy_pts = fmt_points(rec.get("applied_buy_points", 0))
        sell_pts = fmt_points(rec.get("applied_sell_points", 0))
        buy_shift = rec.get("applied_buy_shift", 0)
        sell_shift = rec.get("applied_sell_shift", 0)
        msg = (
            f"Applied {ts} | buy {buy_pts}, sell {sell_pts} "
            f"=> shift {buy_shift:+.1f}/{sell_shift:+.1f}"
        )
        apply_status_var.set(msg)
        apply_status_label.config(fg="#2e7d32")
    elif action == "canceled":
        apply_status_var.set(f"Canceled {ts} | back to base gears")
        apply_status_label.config(fg="#f57c00")
    else:
        apply_status_var.set(f"No change applied. Updated {ts}")
        apply_status_label.config(fg="#b71c1c")


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
        buy_gear = to_float_str(buy_gear_var.get(), 3.0)
        sell_gear = to_float_str(sell_gear_var.get(), 3.0)
        buy_gear = round(clamp_gear(buy_gear, 1.0, 5.0), 1)
        sell_gear = round(clamp_gear(sell_gear, 1.0, 5.0), 1)
        last_trade = normalize_last_trade(latest_trading_day_var.get())
        if (
            avg_cost < 0
            or max_volume < 0
            or num_shares < 0
            or fx_rate <= 0
        ):
            raise ValueError()
    except ValueError:
        messagebox.showerror(
            "Input error",
            "Use non-negative numbers (avg/shares). FX must be > 0.",
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
        "manual_rescue_mode": manual_rescue_var.get().strip().upper() or "AUTO",
        "buy_gear": buy_gear,
        "sell_gear": sell_gear,
        "latest_trading_day": last_trade,
        "units_held": units_held,
        "unit_size_krw": unit_size_krw,
        "unit_size_local": unit_size_local,
        "position_krw": position_krw,
    }


def parse_currency_inputs():
    try:
        def to_float_str(val, default=0.0):
            text = str(val).strip().replace(" ", "").replace(",", "")
            if not text:
                return default
            return float(text)

        avg_cost = to_float_str(avg_cost_var.get(), 0.0)
        usd_hold = to_float_str(num_shares_var.get(), 0.0)
        if avg_cost < 0 or usd_hold < 0:
            raise ValueError()
    except ValueError:
        messagebox.showerror(
            "Input error",
            "Use non-negative numbers (FX avg / USD holdings).",
        )
        return None

    return {
        "avg_cost": avg_cost,
        "usd_hold": usd_hold,
    }


def fill_form_from_record(name):
    if is_currency_name(name):
        rec = stock_data.get(name, default_record(CURRENCY_MARKET))
        name_var.set(name)
        market_var.set(CURRENCY_MARKET)
        avg_cost_var.set("" if rec["avg_cost"] == "" else format_input(rec["avg_cost"], "FX", decimals=0))
        fx_hold = rec.get("fx_hold_usd", rec.get("num_shares", 0))
        num_shares_var.set("" if fx_hold == "" else format_input(fx_hold, "KR", is_money=False, decimals=0))
        max_volume_var.set("")
        fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
        latest_trading_day_var.set("")
        buy_gear_var.set(3.0)
        sell_gear_var.set(3.0)
        manual_rescue_var.set("AUTO")
        update_buy_gear_label()
        update_sell_gear_label()
        return

    rec = stock_data.get(name, default_record())
    name_var.set(name)
    market_var.set(rec.get("market", "KR"))
    avg_cost_var.set("" if rec["avg_cost"] == "" else format_input(rec["avg_cost"], rec.get("market", "KR")))
    num_shares_var.set("" if rec["num_shares"] == "" else format_input(rec["num_shares"], rec.get("market", "KR"), is_money=False))
    max_volume_var.set("" if rec["max_volume"] == "" else format_input(rec["max_volume"], "KR"))
    fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
    latest_trading_day_var.set(rec.get("latest_trading_day", ""))
    buy_gear_var.set(float(rec.get("buy_gear", 3.0) or 3.0))
    sell_gear_var.set(float(rec.get("sell_gear", 3.0) or 3.0))
    manual_rescue_mode = (rec.get("manual_rescue_mode", "AUTO") or "AUTO").strip().upper()
    if manual_rescue_mode not in ("AUTO", "DEFAULT", "HEAVY", "LIGHT"):
        manual_rescue_mode = "AUTO"
    manual_rescue_var.set(manual_rescue_mode)
    update_buy_gear_label()
    update_sell_gear_label()
    update_market_state()


def clear_form_fields():
    name_var.set("")
    avg_cost_var.set("")
    num_shares_var.set("")
    units_held_var.set(f"0.00/0.00/{PORTFOLIO_N} units")
    max_volume_var.set("")
    fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
    market_var.set("KR")
    latest_trading_day_var.set("")
    buy_gear_var.set(3.0)
    sell_gear_var.set(3.0)
    manual_rescue_var.set("AUTO")
    update_buy_gear_label()
    update_sell_gear_label()
    update_market_state()


def set_currency_view(is_currency):
    if is_currency:
        avg_cost_label.config(text="FX Avg Cost (₩ per $)")
        num_shares_label.config(text="USD Holdings ($)")
        units_label.grid_remove()
        units_value_label.grid_remove()
        max_volume_label.grid_remove()
        max_volume_entry.grid_remove()
        market_frame.grid_remove()
        fx_frame.grid_remove()
        latest_frame.grid_remove()
        gear_frame.grid_remove()
        buy_frame.grid_remove()
        sell_frame.grid_remove()
        rescue_frame.grid_remove()
        recommend.grid_remove()
        fx_panel.grid()
    else:
        num_shares_label.config(text="Number of Stocks")
        units_label.grid()
        units_value_label.grid()
        max_volume_label.grid()
        max_volume_entry.grid()
        market_frame.grid()
        fx_frame.grid()
        latest_frame.grid()
        gear_frame.grid()
        buy_frame.grid()
        sell_frame.grid()
        rescue_frame.grid()
        fx_panel.grid_remove()
        recommend.grid()
        update_market_state()


def on_select_stock(selected=None):
    choice = selected or name_choice_var.get()
    if not choice:
        clear_form_fields()
        return
    name_choice_var.set(choice)
    set_currency_view(is_currency_name(choice))
    fill_form_from_record(choice)
    update_display()
    if not is_currency_name(choice):
        update_apply_status_display(choice)


def refresh_name_list(selected=None):
    for child in name_radio_frame.winfo_children():
        child.destroy()
    if not stock_order:
        for nm, mk in DEFAULT_NAMES:
            stock_order.append(nm)
            stock_data[nm] = default_record(mk)
    currency_label_added = False
    for nm in stock_order:
        rec = stock_data.get(nm, default_record())
        if is_currency_name(nm) and not currency_label_added:
            ttk.Label(name_radio_frame, text="Currency").pack(anchor="w", pady=(6, 0))
            currency_label_added = True
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
    if is_currency_name(new_name):
        messagebox.showerror("Reserved name", f"'{CURRENCY_NAME}' is reserved for the FX panel.")
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
    if is_currency_name(selected):
        messagebox.showerror("No selection", "Currency panel cannot be deleted.")
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
    selected = name_choice_var.get()
    if not selected:
        messagebox.showerror("No selection", "Select or add a stock before saving.")
        return
    if is_currency_name(selected):
        parsed_fx = parse_currency_inputs()
        if parsed_fx is None:
            return
        rec = stock_data.get(selected, default_record(CURRENCY_MARKET))
        rec.update(
            {
                "avg_cost": parsed_fx["avg_cost"],
                "num_shares": 0,
                "fx_hold_usd": parsed_fx["usd_hold"],
                "market": CURRENCY_MARKET,
            }
        )
        stock_data[selected] = rec
        write_data_file()
        update_display()
        messagebox.showinfo("Saved", f"Saved FX data for '{selected}'.")
        return

    parsed = parse_form_inputs()
    if parsed is None:
        return

    rec = stock_data.get(selected, default_record(parsed["market"]))
    rec.update(
        {
            "avg_cost": "" if parsed["num_shares"] <= 0 else parsed["avg_cost"],
            "num_shares": parsed["num_shares"],
            "max_volume": parsed["max_volume"],
            "market": parsed["market"],
            "fx_rate": parsed["fx_rate"],
            "units_held": parsed["units_held"],
            "manual_rescue_mode": parsed["manual_rescue_mode"],
            "latest_trading_day": parsed["latest_trading_day"],
            "buy_mode": "LOAD" if parsed["num_shares"] <= 0 else "RELOAD",
            "buy_gear": parsed["buy_gear"],
            "sell_gear": parsed["sell_gear"],
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


def update_display(force_recommendation=False):
    current_name = name_var.get().strip() or name_choice_var.get()
    if not current_name:
        return
    if is_currency_name(current_name):
        parsed_fx = parse_currency_inputs()
        if parsed_fx is None:
            return
        rec = stock_data.get(current_name, default_record(CURRENCY_MARKET))
        current_fx = float(rec.get("current_price", 0) or GLOBAL_FX_RATE)
        avg_cost = float(parsed_fx.get("avg_cost", 0) or 0)
        usd_hold = float(parsed_fx.get("usd_hold", 0) or 0)
        fx_pnl_pct = ((current_fx - avg_cost) / avg_cost * 100.0) if avg_cost > 0 else 0.0
        value_krw = usd_hold * current_fx if usd_hold > 0 and current_fx > 0 else 0.0
        krw_pnl = (current_fx - avg_cost) * usd_hold if avg_cost > 0 and usd_hold > 0 else 0.0

        if avg_cost > 0:
            if fx_pnl_pct <= -2.0:
                status_label = "Green Light (USD cheap)"
                status_color = "#2e7d32"
            elif fx_pnl_pct <= 2.0:
                status_label = "Yellow Light (neutral)"
                status_color = "#f9a825"
            elif fx_pnl_pct <= 5.0:
                status_label = "Red Light (USD expensive)"
                status_color = "#c62828"
            else:
                status_label = "Premium Zone (very expensive)"
                status_color = "#6a1b9a"
            fx_status_var.set(f"FX status: {status_label} ({fx_pnl_pct:+.1f}%)")
        else:
            status_label = "N/A"
            status_color = "#616161"
            fx_status_var.set("FX status: N/A (set FX avg cost)")

        fx_status_label.configure(foreground=status_color)

        tier_prices = []
        tier_lines = []
        if avg_cost > 0:
            for tier in (3.0, 5.0, 7.0):
                price = avg_cost * (1 + tier / 100)
                tier_prices.append(price)
                tier_lines.append(f"Tier +{tier:.0f}%: {fmt_or_na(price, 'FX')}")

        fx_avg_10d = float(rec.get("fx_avg_10d", 0) or 0)
        fx_slope_10d = float(rec.get("fx_slope_10d", 0) or 0)
        info_lines = [
            f"FX current: {fmt_or_na(current_fx, 'FX')}",
            f"FX avg cost: {fmt_or_na(avg_cost, 'FX')}",
            f"USD holdings: {usd_hold:,.0f}" if usd_hold > 0 else "USD holdings: 0",
        ]
        if avg_cost > 0:
            info_lines.append(f"FX vs avg: {fx_pnl_pct:+.2f}%")
        if fx_avg_10d > 0:
            info_lines.append(f"FX 10d avg: {fmt_or_na(fx_avg_10d, 'FX')}")
            info_lines.append(f"FX 10d slope: {fx_slope_10d:+.2f}%")
        if krw_pnl != 0:
            info_lines.append(f"KRW change: {fmt_or_na(krw_pnl, 'KR')}")
        if value_krw > 0:
            info_lines.append(f"KRW value: {fmt_or_na(value_krw, 'KR')}")
        if tier_lines:
            info_lines.extend(tier_lines)
        if rec.get("last_update"):
            info_lines.append(f"Last update: {rec['last_update']}")
        fx_info_var.set("\n".join(info_lines))

        result_lines = [
            f"Name: {current_name} (USD/KRW)",
            f"USD holdings: {usd_hold:,.0f}" if usd_hold > 0 else "USD holdings: 0",
            f"FX avg cost: {fmt_or_na(avg_cost, 'FX')}",
            f"FX current: {fmt_or_na(current_fx, 'FX')}",
        ]
        if avg_cost > 0:
            result_lines.append(f"FX status: {status_label} ({fx_pnl_pct:+.1f}%)")
        if avg_cost > 0:
            result_lines.append(f"FX vs avg: {fx_pnl_pct:+.2f}%")
        else:
            result_lines.append("FX vs avg: N/A (set avg cost)")
        if fx_avg_10d > 0:
            result_lines.append(f"FX 10d avg: {fmt_or_na(fx_avg_10d, 'FX')}")
            result_lines.append(f"FX 10d slope: {fx_slope_10d:+.2f}%")
        if krw_pnl != 0:
            result_lines.append(f"KRW change: {fmt_or_na(krw_pnl, 'KR')}")
        if value_krw > 0:
            result_lines.append(f"KRW value: {fmt_or_na(value_krw, 'KR')}")
        if rec.get("last_update"):
            result_lines.append(f"Last update: {rec['last_update']}")
        result_var.set("\n".join(result_lines))

        plot_currency_levels(
            name=current_name,
            avg_cost=avg_cost,
            current_price=current_fx,
            tier_prices=tier_prices,
        )
        return

    parsed = parse_form_inputs()
    if parsed is None:
        return

    rec = stock_data.get(current_name, default_record(parsed["market"]))
    data = compute_state(parsed, rec, current_name)

    market = parsed["market"]
    effective_avg_cost = parsed["avg_cost"] if parsed["num_shares"] > 0 else 0.0
    fmt_val = lambda val: fmt_or_na(val, market)
    fmt_price = lambda val: fmt_or_na(val, market) if val and val > 0 else "N/A"
    units_held_var.set(
        f"{parsed['units_held']:.2f}/{data['total_units']:.2f}/{PORTFOLIO_N} units"
    )
    show_buy_context = data["buy_mode"] == "LOAD" and data["high_ref"] > 0
    high_context = data["high_ref"] if show_buy_context else 0.0
    high_context_label = data["high_ref_label"]

    if parsed["units_held"] > 0 and data["rescue_gear"] > 0:
        rescue_tag = (
            f"Rescue {data['rescue_mode']}"
            if data["rescue_mode"] != "Auto"
            else f"Rescue G{data['rescue_gear']:.1f}"
        )
        rescue_summary = (
            f"{rescue_tag} (-{fmt_compact(data['rescue_drop_pct'])}%, r={fmt_compact(data['rescue_r'])})"
        )
    else:
        if parsed["manual_rescue_mode"] != "AUTO":
            if parsed["manual_rescue_mode"] == "LIGHT":
                drop_pct, r, gear = 4.0, 0.5, 1
                rescue_tag = "Rescue Light"
            elif parsed["manual_rescue_mode"] == "HEAVY":
                drop_pct, r, gear = 6.0, 0.7, 3
                rescue_tag = "Rescue Heavy"
            else:
                drop_pct, r, gear = 5.0, 0.6, 2
                rescue_tag = "Rescue Default"
        else:
            drop_pct, r, gear = get_rescue_gear(max(parsed["units_held"], 1.0), PORTFOLIO_N)
            rescue_tag = f"Rescue G{gear:.1f}"
        rescue_summary = f"{rescue_tag} (-{fmt_compact(drop_pct)}%, r={fmt_compact(r)})"
    buy_info_var.set(
        f"{data['buy_mode']} gear {parsed['buy_gear']:.1f} (-{data['buy_drop_pct']:.1f}%)\n{rescue_summary}"
    )

    sell_info_var.set(
        f"Sell gear {data['sell_gear']:.1f}: +{data['sell_tiers'][0]:.1f}%/"
        f"+{data['sell_tiers'][1]:.1f}%/+{data['sell_tiers'][2]:.1f}%"
    )

    result_lines = [
        f"Name: {current_name}",
        f"Last trade (YYMMDD): {parsed['latest_trading_day'] or 'N/A'}",
        f"Units: {units_held_var.get()} | Avg cost: {fmt_val(effective_avg_cost)}",
        f"Current: {fmt_price(data['current_price'])} | Low/High: {fmt_price(data['low_today'])}/{fmt_price(data['high_today'])}",
        f"{data['buy_mode']} gear {parsed['buy_gear']:.1f}: -{data['buy_drop_pct']:.1f}% -> {fmt_price(data['buy_trigger'])} | Status: {data['buy_status']}",
    ]
    if show_buy_context:
        result_lines.insert(
            4,
            f"{high_context_label}: {fmt_price(high_context)}",
        )

    if parsed["units_held"] > 0 and data["rescue_gear"] > 0:
        rescue_title = (
            f"RESCUE {data['rescue_mode'].upper()}"
            if data["rescue_mode"] != "Auto"
            else f"RESCUE G{data['rescue_gear']:.1f}"
        )
        result_lines.append(
            f"{rescue_title}: -{fmt_compact(data['rescue_drop_pct'])}% "
            f"(r={fmt_compact(data['rescue_r'])}) -> {fmt_price(data['rescue_trigger'])} | Buy {data['rescue_qty']:.2f}u"
        )
    else:
        result_lines.append("RESCUE: N/A (no units)")

    if parsed["num_shares"] > 0:
        sell_line = f"SELL gear {data['sell_gear']:.1f} (deployment {data['total_u']*100:.1f}%)"
        result_lines.append(sell_line)
        result_lines.append(
            f"Tier 1 (50%): {fmt_val(data['sell_targets'][0])} (+{data['sell_tiers'][0]:.1f}%)"
        )
        result_lines.append(
            f"Tier 2 (25%): {fmt_val(data['sell_targets'][1])} (+{data['sell_tiers'][1]:.1f}%)"
        )
        result_lines.append(
            f"Tier 3 (25%): {fmt_val(data['sell_targets'][2])} (+{data['sell_tiers'][2]:.1f}%)"
        )
    else:
        result_lines.append("SELL: N/A (no position)")

    if data["last_update"]:
        result_lines.append(f"Last update: {data['last_update']}")

    result_var.set("\n".join(result_lines))

    metrics = compute_trait_metrics(parsed, data)
    manual_states = {trait_id: bool(var.get()) for trait_id, var in manual_trait_vars.items()}
    for group_var in manual_group_vars.values():
        selected = group_var.get()
        if selected:
            manual_states[selected] = True

    state = get_rec_state(current_name)
    perk = state.get("latest")
    if force_recommendation or perk is None:
        perk = compute_perk_gears(metrics, manual_states)
        state["latest"] = perk

    if perk:
        recommendation_warning_var.set("")
        ratio_var.set(f"  Ratio {fmt_ratio(perk['ratio'])}")

        auto_buy = sum(trait.get("buy_points", 0) for trait in perk["active_auto"])
        auto_sell = sum(trait.get("sell_points", 0) for trait in perk["active_auto"])
        manual_buy = sum(trait.get("buy_points", 0) for trait in perk["active_manual"])
        manual_sell = sum(trait.get("sell_points", 0) for trait in perk["active_manual"])
        auto_points_var.set(
            f"Auto total: buy {fmt_points(auto_buy)} / sell {fmt_points(auto_sell)}"
        )
        manual_points_var.set(
            f"Manual total: buy {fmt_points(manual_buy)} / sell {fmt_points(manual_sell)}"
        )

        auto_lines = []
        for trait in perk["active_auto"]:
            icon = trait.get("icon", "") or ""
            desc = trait.get("description", "") or ""
            line = (
                f"- {icon} {trait['name']} "
                f"({fmt_points(trait.get('buy_points', 0))}/{fmt_points(trait.get('sell_points', 0))})"
            )
            if desc:
                line = f"{line} - {desc}"
            auto_lines.append(line.strip())
        if not auto_lines:
            auto_lines = ["(none)"]
        auto_traits_text.config(state="normal")
        auto_traits_text.delete("1.0", tk.END)
        auto_traits_text.insert("1.0", "\n".join(auto_lines))
        auto_traits_text.config(state="disabled")

        summary_lines = [
            f"Buy points: {fmt_points(perk['buy_points'])} -> shift {perk['buy_shift']:+.1f}",
            f"Sell points: {fmt_points(perk['sell_points'])} -> shift {perk['sell_shift']:+.1f}",
            f"Base gears: {perk['base_buy']:.1f} / {perk['base_sell']:.1f}",
            f"Final gears: {perk['buy_gear']:.1f} / {perk['sell_gear']:.1f}",
        ]
        if any(trait.get("id") == "black_swan" for trait in perk["active_manual"]):
            summary_lines.append("Black Swan active: sell gear forced to 0.0")
        recommendation_var.set("\n".join(summary_lines))
    else:
        auto_points_var.set("Auto total: buy +0 / sell +0")
        manual_points_var.set("Manual total: buy +0 / sell +0")
        ratio_var.set("  Ratio 0:1")
        auto_traits_text.config(state="normal")
        auto_traits_text.delete("1.0", tk.END)
        auto_traits_text.insert("1.0", "(none)")
        auto_traits_text.config(state="disabled")
    update_apply_status_display(current_name)

    plot_levels(
        name=current_name,
        market=market,
        avg_cost=effective_avg_cost,
        units_held=parsed["units_held"],
        num_shares=parsed["num_shares"],
        current_price=data["current_price"],
        high_context=high_context,
        high_context_label=high_context_label,
        buy_price=data["buy_price"],
        buy_label=data["buy_label"],
        buy_drop_pct=data["buy_drop_pct"],
        rescue_trigger=data["rescue_trigger"],
        rescue_qty=data["rescue_qty"],
        rescue_drop_pct=data["rescue_drop_pct"],
        rescue_r=data["rescue_r"],
        rescue_gear=data["rescue_gear"],
        rescue_shares=data["rescue_shares"],
        projected_avg=data["projected_avg"],
        projected_units=data["projected_units"],
        projected_shares=data["projected_shares"],
        sell_targets=data["sell_targets"],
        sell_tiers=data["sell_tiers"],
    )


def on_show():
    update_display()


def apply_recommendation():
    stock_name = get_current_stock_name()
    if not stock_name:
        messagebox.showinfo("Recommendation", "No stock selected.")
        return
    if is_currency_name(stock_name):
        messagebox.showinfo("Recommendation", "FX panel does not use stock perks.")
        return
    state = get_rec_state(stock_name)
    perk = state.get("latest")
    if not perk:
        update_display(force_recommendation=True)
        perk = state.get("latest")
    if not perk:
        messagebox.showinfo("Recommendation", "No recommendation available.")
        return

    base_buy, base_sell = get_base_gears()
    target_buy = round(base_buy + float(perk.get("buy_shift", 0)), 1)
    target_sell = round(base_sell + float(perk.get("sell_shift", 0)), 1)
    current_buy = float(buy_gear_var.get())
    current_sell = float(sell_gear_var.get())

    now_ts = datetime.now().strftime("%y%m%d %H:%M")
    rec = stock_data.get(stock_name, default_record())
    rec["applied_buy_points"] = perk.get("buy_points", 0)
    rec["applied_sell_points"] = perk.get("sell_points", 0)
    rec["applied_buy_shift"] = perk.get("buy_shift", 0)
    rec["applied_sell_shift"] = perk.get("sell_shift", 0)
    rec["applied_buy_gear"] = target_buy
    rec["applied_sell_gear"] = target_sell
    rec["applied_timestamp"] = now_ts

    if abs(target_buy - current_buy) < 1e-6 and abs(target_sell - current_sell) < 1e-6:
        rec["applied_action"] = "no_change"
        stock_data[stock_name] = rec
        write_data_file()
        update_apply_status_display(stock_name)
        messagebox.showinfo("Recommendation", "No change applied.")
        return

    buy_gear_var.set(target_buy)
    sell_gear_var.set(target_sell)
    rec["applied_action"] = "applied"
    stock_data[stock_name] = rec
    write_data_file()
    update_display()
    update_apply_status_display(stock_name)
    messagebox.showinfo("Recommendation", "Change is applied.")


def cancel_recommendation():
    stock_name = get_current_stock_name()
    if not stock_name:
        messagebox.showinfo("Recommendation", "No stock selected.")
        return
    if is_currency_name(stock_name):
        messagebox.showinfo("Recommendation", "FX panel does not use stock perks.")
        return
    base_buy, base_sell = get_base_gears()
    buy_gear_var.set(round(base_buy, 1))
    sell_gear_var.set(round(base_sell, 1))
    rec = stock_data.get(stock_name, default_record())
    rec["applied_action"] = "canceled"
    rec["applied_timestamp"] = datetime.now().strftime("%y%m%d %H:%M")
    stock_data[stock_name] = rec
    write_data_file()
    update_display(force_recommendation=True)
    update_apply_status_display(stock_name)


def toggle_apply():
    apply_recommendation()


def refresh_recommendation():
    stock_name = get_current_stock_name()
    if not stock_name:
        messagebox.showinfo("Recommendation", "No stock selected.")
        return
    if is_currency_name(stock_name):
        messagebox.showinfo("Recommendation", "FX panel does not use stock perks.")
        return
    update_display(force_recommendation=True)


def plot_currency_levels(
    name,
    avg_cost,
    current_price,
    tier_prices,
):
    fig.clear()
    ax = fig.add_subplot(111)
    x_start, x_end = 0.0, 1.0

    fmt_val = lambda val: fmt_or_na(val, "FX")
    levels = []

    if current_price and current_price > 0:
        levels.append(("FX Now", current_price, "#333333", "--", "", fmt_val(current_price), 2.0))
    if avg_cost and avg_cost > 0:
        levels.append(("FX Avg", avg_cost, "black", "-", "", fmt_val(avg_cost), 2.6))
    if tier_prices:
        colors = ["#0a8f08", "#0066cc", "#7b1fa2"]
        for idx, price in enumerate(tier_prices):
            label = f"Tier +{[3, 5, 7][idx]}%"
            levels.append((label, price, colors[idx % len(colors)], "-", "", fmt_val(price), 2.4))

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

    def draw_gap(x, base, other, color):
        if not base or not other or base <= 0 or other <= 0 or base == other:
            return
        ax.plot([x, x], [base, other], color=color, linestyle="--", linewidth=1.0)
        pct = (other - base) / base * 100.0
        ax.text(
            x + 0.01,
            (base + other) / 2,
            f"{pct:+.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color=color,
        )

    if avg_cost and avg_cost > 0 and current_price and current_price > 0:
        draw_gap(0.55, avg_cost, current_price, "#616161")

    if avg_cost and avg_cost > 0 and tier_prices:
        draw_gap(0.65, avg_cost, tier_prices[0], "#0066cc")
        if len(tier_prices) > 1:
            draw_gap(0.75, tier_prices[0], tier_prices[1], "#0066cc")
        if len(tier_prices) > 2:
            draw_gap(0.85, tier_prices[1], tier_prices[2], "#0066cc")

    if levels:
        prices = [lvl[1] for lvl in levels]
        ymin = min(prices)
        ymax = max(prices)
        pad = (ymax - ymin) * 0.1 if ymax != ymin else max(1, ymax * 0.1)
        ax.set_ylim(ymin - pad, ymax + pad)

    ax.set_xlim(x_start, x_end)
    ax.set_xticks([])
    ax.set_title(name or "")
    ax.set_ylabel("FX (₩ per $)")
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    canvas.draw()


def plot_levels(
    name,
    market,
    avg_cost,
    units_held,
    num_shares,
    current_price,
    high_context,
    high_context_label,
    buy_price,
    buy_label,
    buy_drop_pct,
    rescue_trigger,
    rescue_qty,
    rescue_drop_pct,
    rescue_r,
    rescue_gear,
    rescue_shares,
    projected_avg,
    projected_units,
    projected_shares,
    sell_targets,
    sell_tiers,
):
    fig.clear()
    ax = fig.add_subplot(111)
    x_start, x_end = 0.0, 1.0

    fmt_val = lambda val: fmt_or_na(val, market)
    levels = []

    show_load = buy_label == "LOAD"

    if current_price and current_price > 0:
        levels.append(("Current", current_price, "#333333", "--", "", fmt_val(current_price), 2.0))
    if not show_load and avg_cost and avg_cost > 0:
        left_text = f"u {units_held:.2f}, sh {int(num_shares)}" if num_shares else ""
        levels.append(("Avg cost", avg_cost, "black", "-", left_text, fmt_val(avg_cost), 2.6))
    if show_load and high_context and high_context > 0:
        levels.append((high_context_label, high_context, "#777777", ":", "", fmt_val(high_context), 1.4))
    if show_load and buy_price and buy_price > 0:
        levels.append((buy_label, buy_price, "#c62828", "-", "", fmt_val(buy_price), 2.6))
    if not show_load and rescue_trigger and rescue_trigger > 0 and rescue_gear > 0:
        gear_key = int(round(rescue_gear)) if rescue_gear else 0
        color = RESCUE_GEAR_COLORS.get(gear_key, "#d32f2f")
        rescue_text = f"-{fmt_compact(rescue_drop_pct)}%, r={fmt_compact(rescue_r)}"
        if rescue_shares:
            rescue_text = f"{rescue_text} {rescue_qty:.2f}u ~ {rescue_shares} sh"
        levels.append(("RESCUE", rescue_trigger, color, "-", rescue_text, fmt_val(rescue_trigger), 2.6))
    if not show_load and projected_avg and projected_avg > 0:
        proj_text = f"units {projected_units:.2f}, sh {projected_shares}" if projected_shares else ""
        levels.append(("Projected avg", projected_avg, "#999999", "--", proj_text, fmt_val(projected_avg), 1.6))
    if (not show_load) and avg_cost and avg_cost > 0 and sell_targets and sell_targets[0] > 0:
        colors = ["#0a8f08", "#0066cc", "#7b1fa2"]
        for idx, target in enumerate(sell_targets):
            label = f"Sell T{idx+1}"
            levels.append((label, target, colors[idx % len(colors)], "-", "", fmt_val(target), 2.4))

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

    gap_x_buy = 0.5
    if show_load and high_context and high_context > 0 and buy_price and buy_price > 0:
        ax.plot([gap_x_buy, gap_x_buy], [buy_price, high_context], color="#c62828", linestyle="--", linewidth=1.0)
        gap_pct = (buy_price - high_context) / high_context * 100 if high_context else 0.0
        ax.text(
            gap_x_buy + 0.01,
            (buy_price + high_context) / 2,
            f"{gap_pct:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#c62828",
        )

    if not show_load and rescue_trigger and projected_avg and projected_avg > 0 and rescue_trigger != projected_avg:
        gap_x2 = 0.7
        proj_gap_pct = ((projected_avg - rescue_trigger) / rescue_trigger * 100) if rescue_trigger else 0.0
        ax.plot([gap_x2, gap_x2], [rescue_trigger, projected_avg], color="#777777", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x2 + 0.01,
            (rescue_trigger + projected_avg) / 2,
            f"+{proj_gap_pct:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#777777",
        )

    if not show_load and avg_cost and avg_cost > 0 and rescue_trigger and rescue_trigger > 0:
        gap_x_rescue = 0.4
        rescue_gap_pct = ((rescue_trigger - avg_cost) / avg_cost * 100) if avg_cost else 0.0
        ax.plot([gap_x_rescue, gap_x_rescue], [rescue_trigger, avg_cost], color="#c62828", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x_rescue + 0.01,
            (rescue_trigger + avg_cost) / 2,
            f"{rescue_gap_pct:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#c62828",
        )

    if (not show_load) and avg_cost and avg_cost > 0 and sell_targets and sell_tiers and sell_targets[0] > 0:
        gap_x3 = 0.5
        ax.plot([gap_x3, gap_x3], [avg_cost, sell_targets[0]], color="#0066cc", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x3 + 0.01,
            (avg_cost + sell_targets[0]) / 2,
            f"+{sell_tiers[0]:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#0066cc",
        )
        ax.plot([gap_x3, gap_x3], [sell_targets[0], sell_targets[1]], color="#0066cc", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x3 + 0.01,
            (sell_targets[0] + sell_targets[1]) / 2,
            f"+{(sell_tiers[1] - sell_tiers[0]):.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color="#0066cc",
        )
        ax.plot([gap_x3, gap_x3], [sell_targets[1], sell_targets[2]], color="#0066cc", linestyle="--", linewidth=1.0)
        ax.text(
            gap_x3 + 0.01,
            (sell_targets[1] + sell_targets[2]) / 2,
            f"+{(sell_tiers[2] - sell_tiers[1]):.1f}%",
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


def update_manual_rescue_state(*args):
    update_display()


def update_buy_gear_label(*args):
    if "buy_gear_label" not in globals():
        return
    try:
        val = float(buy_gear_var.get())
    except (TypeError, ValueError):
        val = 3.0
    buy_gear_label.config(text=f"{val:.1f}")
    update_display()


def update_sell_gear_label(*args):
    if "sell_gear_label" not in globals():
        return
    try:
        val = float(sell_gear_var.get())
    except (TypeError, ValueError):
        val = 3.0
    sell_gear_label.config(text=f"{val:.1f}")
    update_display()


def update_market_state():
    if is_currency_name(get_current_stock_name()):
        avg_cost_label.config(text="FX Avg Cost (₩ per $)")
        return
    # Always show FX and keep it editable for both KR and US; for KR it still stores a value.
    fx_entry.state(["!disabled"])
    if not fx_rate_var.get():
        fx_rate_var.set(f"{GLOBAL_FX_RATE:,.2f}")
    if market_var.get() == "US":
        avg_cost_label.config(text="Average Cost ($)")
    else:
        avg_cost_label.config(text="Average Cost (₩)")


def center_window(window):
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


# ---------------- UI ----------------
root = tk.Tk()
root.title("AI Seesaw Trading Calculator")
try:
    if "Segoe UI Emoji" in tkfont.families(root):
        perk_font = tkfont.Font(root=root, family="Segoe UI Emoji", size=12)
        perk_check_style = "Perk.TCheckbutton"
        perk_radio_style = "Perk.TRadiobutton"
        ttk.Style(root).configure(perk_check_style, font=perk_font)
        ttk.Style(root).configure(perk_radio_style, font=perk_font)
    bold_font = tkfont.nametofont("TkDefaultFont").copy()
    bold_font.configure(weight="bold")
    bold_label_style = "RecBold.TLabel"
    ttk.Style(root).configure(bold_label_style, font=bold_font)
except tk.TclError:
    perk_font = None
    perk_check_style = None
    perk_radio_style = None
    bold_label_style = None

main = ttk.Frame(root, padding=12)
main.grid(sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
main.columnconfigure(0, weight=0)
main.columnconfigure(1, weight=1)
main.columnconfigure(2, weight=0)
main.rowconfigure(0, weight=1)

name_choice_var = tk.StringVar()
name_var = tk.StringVar()
avg_cost_var = tk.StringVar()
num_shares_var = tk.StringVar()
units_held_var = tk.StringVar(value=f"0.00/0.00/{PORTFOLIO_N} units")
max_volume_var = tk.StringVar()
fx_rate_var = tk.StringVar()
market_var = tk.StringVar(value="KR")
latest_trading_day_var = tk.StringVar()
buy_gear_var = tk.DoubleVar(value=3.0)
sell_gear_var = tk.DoubleVar(value=3.0)
manual_rescue_var = tk.StringVar(value="AUTO")
result_var = tk.StringVar()
buy_info_var = tk.StringVar()
sell_info_var = tk.StringVar()
recommendation_var = tk.StringVar()
recommendation_warning_var = tk.StringVar()
auto_points_var = tk.StringVar()
manual_points_var = tk.StringVar()
manual_trait_vars = {}
manual_group_vars = {}
rec_states = {}
apply_btn = None
cancel_btn = None
apply_status_var = tk.StringVar()
ratio_var = tk.StringVar()
fx_status_var = tk.StringVar()
fx_info_var = tk.StringVar()

buy_gear_var.trace_add("write", lambda *_: update_buy_gear_label())
sell_gear_var.trace_add("write", lambda *_: update_sell_gear_label())

form = ttk.Frame(main)
form.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

ttk.Label(form, text="Stock").grid(row=0, column=0, sticky="ne", padx=4, pady=4)
name_frame = ttk.Frame(form)
name_frame.grid(row=0, column=1, sticky="w", padx=4, pady=4)
name_radio_frame = ttk.Frame(name_frame)
name_radio_frame.grid(row=0, column=0, sticky="w")

avg_cost_label = ttk.Label(form, text="Average Cost (₩)")
avg_cost_label.grid(row=1, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form, textvariable=avg_cost_var, width=16).grid(
    row=1, column=1, sticky="w", padx=4, pady=4
)
num_shares_label = ttk.Label(form, text="Number of Stocks")
num_shares_label.grid(row=2, column=0, sticky="e", padx=4, pady=4)
num_shares_entry = ttk.Entry(form, textvariable=num_shares_var, width=16)
num_shares_entry.grid(row=2, column=1, sticky="w", padx=4, pady=4)

units_label = ttk.Label(form, text="stock/deployed/total")
units_label.grid(row=3, column=0, sticky="e", padx=4, pady=4)
units_value_label = ttk.Label(form, textvariable=units_held_var)
units_value_label.grid(row=3, column=1, sticky="w", padx=4, pady=4)

max_volume_label = ttk.Label(form, text="Max Volume (₩)")
max_volume_label.grid(row=4, column=0, sticky="e", padx=4, pady=4)
max_volume_entry = ttk.Entry(form, textvariable=max_volume_var, width=16)
max_volume_entry.grid(row=4, column=1, sticky="w", padx=4, pady=4)

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

latest_frame = ttk.Frame(form)
latest_frame.grid(row=7, column=0, columnspan=2, sticky="w", padx=4, pady=4)
ttk.Label(latest_frame, text="Last trade (YYMMDD)").grid(row=0, column=0, sticky="w", padx=(0, 8))
ttk.Entry(latest_frame, textvariable=latest_trading_day_var, width=16).grid(row=0, column=1, sticky="w")

gear_frame = ttk.LabelFrame(form, text="Gears")
gear_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(gear_frame, text="Buy gear (1-5)").grid(row=0, column=0, sticky="w", padx=(0, 8))
buy_gear_slider = ttk.Scale(
    gear_frame,
    from_=1.0,
    to=5.0,
    orient="horizontal",
    variable=buy_gear_var,
    command=update_buy_gear_label,
    length=160,
)
buy_gear_slider.grid(row=0, column=1, sticky="w")
buy_gear_label = ttk.Label(gear_frame, text="3.0")
buy_gear_label.grid(row=0, column=2, sticky="w", padx=(6, 0))

ttk.Label(gear_frame, text="Sell gear (1-5)").grid(row=1, column=0, sticky="w", padx=(0, 8))
sell_gear_slider = ttk.Scale(
    gear_frame,
    from_=1.0,
    to=5.0,
    orient="horizontal",
    variable=sell_gear_var,
    command=update_sell_gear_label,
    length=160,
)
sell_gear_slider.grid(row=1, column=1, sticky="w")
sell_gear_label = ttk.Label(gear_frame, text="3.0")
sell_gear_label.grid(row=1, column=2, sticky="w", padx=(6, 0))

buy_frame = ttk.LabelFrame(form, text="Buy")
buy_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(buy_frame, textvariable=buy_info_var, justify="left").grid(row=0, column=0, sticky="w")

sell_frame = ttk.LabelFrame(form, text="Sell")
sell_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(sell_frame, textvariable=sell_info_var, justify="left").grid(row=0, column=0, sticky="w")

rescue_frame = ttk.LabelFrame(form, text="Rescue")
rescue_frame.grid(row=11, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Label(rescue_frame, text="Rescue mode").grid(row=0, column=0, sticky="w", padx=4, pady=(4, 2))
manual_rescue_frame = ttk.Frame(rescue_frame)
manual_rescue_frame.grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))
ttk.Radiobutton(
    manual_rescue_frame,
    text="Auto (-4~-6%, 0.5~0.7)",
    value="AUTO",
    variable=manual_rescue_var,
    command=update_manual_rescue_state,
).grid(row=0, column=0, sticky="w")
ttk.Radiobutton(
    manual_rescue_frame,
    text="Default (-5%, 0.6)",
    value="DEFAULT",
    variable=manual_rescue_var,
    command=update_manual_rescue_state,
).grid(row=1, column=0, sticky="w")
ttk.Radiobutton(
    manual_rescue_frame,
    text="Heavy (-6%, 0.7)",
    value="HEAVY",
    variable=manual_rescue_var,
    command=update_manual_rescue_state,
).grid(row=2, column=0, sticky="w")
ttk.Radiobutton(
    manual_rescue_frame,
    text="Light (-4%, 0.5)",
    value="LIGHT",
    variable=manual_rescue_var,
    command=update_manual_rescue_state,
).grid(row=3, column=0, sticky="w")

ttk.Button(form, text="Refresh Market Data", command=refresh_market_data).grid(
    row=12, column=0, columnspan=2, pady=(4, 4), sticky="ew"
)
ttk.Button(form, text="Show Result", command=on_show).grid(
    row=13, column=0, columnspan=2, pady=12, sticky="ew"
)
ttk.Button(form, text="Save Result", command=on_save).grid(
    row=14, column=0, columnspan=2, pady=(0, 12), sticky="ew"
)

output = ttk.Frame(main)
output.grid(row=0, column=1, sticky="nsew")
output.columnconfigure(0, weight=1)
output.rowconfigure(1, weight=1)

ttk.Label(output, textvariable=result_var, justify="left").grid(
    row=0, column=0, sticky="nw", pady=(0, 8), padx=(0, 8)
)

fig = Figure(figsize=(7.8, 4.0), dpi=100)
canvas = FigureCanvasTkAgg(fig, master=output)
canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

recommend = ttk.LabelFrame(main, text="Perk Recommendation")
recommend.grid(row=0, column=2, sticky="n", padx=(12, 0))
recommend.columnconfigure(0, weight=1)

ttk.Label(recommend, text="Auto Traits").grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
auto_traits_kwargs = {"width": 38, "height": 12, "wrap": "word"}
if perk_font:
    auto_traits_kwargs["font"] = perk_font
auto_traits_text = tk.Text(recommend, **auto_traits_kwargs)
auto_traits_text.grid(row=1, column=0, sticky="ew", padx=6)
auto_traits_text.config(state="disabled")

auto_points_label = ttk.Label(recommend, textvariable=auto_points_var, justify="left")
if bold_label_style:
    auto_points_label.configure(style=bold_label_style)
auto_points_label.grid(
    row=2, column=0, sticky="w", padx=6, pady=(0, 2)
)

ttk.Label(recommend, text="Manual Traits").grid(row=3, column=0, sticky="w", padx=6, pady=(6, 2))
manual_canvas = tk.Canvas(recommend, height=200)
manual_canvas.grid(row=4, column=0, sticky="ew", padx=6)
manual_scroll = ttk.Scrollbar(recommend, orient="vertical", command=manual_canvas.yview)
manual_scroll.grid(row=4, column=1, sticky="ns")
manual_canvas.configure(yscrollcommand=manual_scroll.set)
manual_frame = ttk.Frame(manual_canvas)
manual_canvas.create_window((0, 0), window=manual_frame, anchor="nw")

def _manual_scroll_region(event):
    manual_canvas.configure(scrollregion=manual_canvas.bbox("all"))

manual_frame.bind("<Configure>", _manual_scroll_region)

def _manual_on_mousewheel(event):
    manual_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def _bind_manual_mousewheel(_):
    manual_canvas.bind_all("<MouseWheel>", _manual_on_mousewheel)

def _unbind_manual_mousewheel(_):
    manual_canvas.unbind_all("<MouseWheel>")

manual_canvas.bind("<Enter>", _bind_manual_mousewheel)
manual_canvas.bind("<Leave>", _unbind_manual_mousewheel)

manual_exclusive = {}
manual_nonexclusive = []
for trait in MANUAL_TRAITS:
    group = trait.get("exclusive_group")
    group_info = EXCLUSIVE_GROUPS.get(group, {})
    if group and group_info.get("enforcement") == "manual":
        manual_exclusive.setdefault(group, []).append(trait)
    else:
        manual_nonexclusive.append(trait)

for group, perks in manual_exclusive.items():
    group_title = group.replace("_", " ").title()
    ttk.Label(manual_frame, text=f"{group_title} (pick one)").pack(anchor="w", pady=(2, 0))
    group_var = tk.StringVar(value="")
    manual_group_vars[group] = group_var
    for perk in perks:
        icon = perk.get("icon", "") or ""
        desc = perk.get("description", "") or ""
        label = (
            f"{icon} {perk['name']} "
            f"({fmt_points(perk.get('buy_points', 0))}/{fmt_points(perk.get('sell_points', 0))})"
        )
        if desc:
            label = f"{label} - {desc}"
        radio_kwargs = {
            "text": label,
            "value": perk["id"],
            "variable": group_var,
            "command": update_display,
        }
        if perk_radio_style:
            radio_kwargs["style"] = perk_radio_style
        ttk.Radiobutton(manual_frame, **radio_kwargs).pack(anchor="w")
    ttk.Label(manual_frame, text="").pack(anchor="w")

manual_nonexclusive_by_category = {}
for trait in manual_nonexclusive:
    category = trait.get("category") or "Other"
    manual_nonexclusive_by_category.setdefault(category, []).append(trait)

for category, perks in manual_nonexclusive_by_category.items():
    category_title = category.replace("_", " ").title()
    ttk.Label(manual_frame, text=f"{category_title} (multi)").pack(anchor="w", pady=(2, 0))
    for perk in perks:
        icon = perk.get("icon", "") or ""
        desc = perk.get("description", "") or ""
        label = (
            f"{icon} {perk['name']} "
            f"({fmt_points(perk.get('buy_points', 0))}/{fmt_points(perk.get('sell_points', 0))})"
        )
        if desc:
            label = f"{label} - {desc}"
        var = tk.IntVar(value=0)
        manual_trait_vars[perk["id"]] = var
        check_kwargs = {
            "text": label,
            "variable": var,
            "command": update_display,
        }
        if perk_check_style:
            check_kwargs["style"] = perk_check_style
        ttk.Checkbutton(manual_frame, **check_kwargs).pack(anchor="w")
    ttk.Label(manual_frame, text="").pack(anchor="w")

ttk.Label(recommend, textvariable=recommendation_warning_var, justify="left").grid(
    row=5, column=0, sticky="w", padx=6, pady=(6, 2)
)
manual_points_label = ttk.Label(recommend, textvariable=manual_points_var, justify="left")
if bold_label_style:
    manual_points_label.configure(style=bold_label_style)
manual_points_label.grid(
    row=6, column=0, sticky="w", padx=6, pady=(0, 2)
)
ttk.Label(recommend, textvariable=ratio_var, justify="left").grid(
    row=7, column=0, sticky="w", padx=6, pady=(0, 2)
)
ttk.Label(
    recommend,
    textvariable=recommendation_var,
    justify="left",
    wraplength=240,
).grid(row=8, column=0, sticky="nw", padx=6, pady=(0, 6))
ttk.Button(recommend, text="Refresh", command=refresh_recommendation).grid(
    row=9, column=0, sticky="ew", padx=6, pady=(0, 4)
)
apply_btn = tk.Button(
    recommend,
    text="Apply",
    command=lambda: toggle_apply(),
    bg="#2e7d32",
    fg="white",
    activebackground="#1b5e20",
    activeforeground="white",
)
apply_btn.grid(row=10, column=0, sticky="ew", padx=6, pady=(0, 4))
cancel_btn = tk.Button(
    recommend,
    text="Cancel",
    command=lambda: cancel_recommendation(),
    bg="#9e9e9e",
    fg="white",
    activebackground="#757575",
    activeforeground="white",
)
cancel_btn.grid(row=11, column=0, sticky="ew", padx=6, pady=(0, 4))
apply_status_label = tk.Label(
    recommend,
    textvariable=apply_status_var,
    anchor="w",
    justify="left",
    fg="#b71c1c",
)
apply_status_label.grid(row=12, column=0, sticky="ew", padx=6, pady=(0, 6))

fx_panel = ttk.LabelFrame(main, text="Dollar (FX)")
fx_panel.grid(row=0, column=2, sticky="n", padx=(12, 0))
fx_panel.columnconfigure(0, weight=1)
fx_status_label = ttk.Label(fx_panel, textvariable=fx_status_var, justify="left")
fx_status_label.grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
ttk.Label(fx_panel, textvariable=fx_info_var, justify="left").grid(
    row=1, column=0, sticky="w", padx=6, pady=(0, 6)
)
fx_panel.grid_remove()

main.rowconfigure(0, weight=1)
main.columnconfigure(1, weight=1)

load_data()
refresh_name_list()
update_market_state()
center_window(root)

root.mainloop()
