import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


DATA_FILE = "data.csv"
DEFAULT_NAMES = [
    ("Samsung", "KR"),
    ("SK hynix", "KR"),
    ("NVIDIA", "US"),
    ("Alphabet", "US"),
]
GLOBAL_FX_RATE = 1300.0  # ₩ per $

# Buy models (gear_drop %, r)
BUY_MODELS = {
    "Agile (-5%,0.6)": {"gear_drop": 5.0, "r": 0.6},
    "Heavy (-6%,0.7)": {"gear_drop": 6.0, "r": 0.7},
    "Greedy (-4%,0.7)": {"gear_drop": 4.0, "r": 0.7},
    "Cautious (-7%,0.65)": {"gear_drop": 7.0, "r": 0.65},
}

stock_data = {}
stock_order = []


def default_record(market="KR"):
    return {
        "avg_cost": "",
        "num_shares": "",
        "max_volume": "",
        "buy_model": list(BUY_MODELS.keys())[0],
        "manual_mode": 0,
        "manual_gear": 0.0,
        "g_score": 0.0,
        "l_score": 0.0,
        "v_score": 1.0,
        "g_date": "",
        "l_date": "",
        "market": market,
        "fx_rate": GLOBAL_FX_RATE if market == "US" else 1.0,
    }


def load_data():
    global stock_order, stock_data, GLOBAL_FX_RATE
    stock_data = {}
    stock_order = []
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

                stock_data[name] = {
                    "avg_cost": avg_cost,
                    "num_shares": num_shares,
                    "max_volume": max_volume,
                    "market": market,
                    "fx_rate": fx_rate,
                    "buy_model": row.get("buy_model", list(BUY_MODELS.keys())[0]),
                    "manual_mode": manual_mode,
                    "manual_gear": manual_gear_val,
                    "g_score": g_score,
                    "l_score": l_score,
                    "v_score": v_score,
                    "g_date": g_date,
                    "l_date": l_date,
                }
                stock_order.append(name)
                if market == "US":
                    GLOBAL_FX_RATE = fx_rate
    if not stock_order:
        for nm, mk in DEFAULT_NAMES:
            stock_order.append(nm)
            stock_data[nm] = default_record(mk)


def write_data_file():
    fieldnames = [
        "name",
        "avg_cost",
        "num_shares",
        "max_volume",
        "buy_model",
        "manual_mode",
        "manual_gear",
        "g_score",
        "l_score",
        "v_score",
        "g_date",
        "l_date",
        "market",
        "fx_rate",
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
                    "buy_model": rec.get("buy_model", list(BUY_MODELS.keys())[0]),
                    "manual_mode": rec.get("manual_mode", 0),
                    "manual_gear": rec.get("manual_gear", 0.0),
                    "g_score": rec.get("g_score", ""),
                    "l_score": rec.get("l_score", ""),
                    "v_score": rec.get("v_score", ""),
                    "g_date": rec.get("g_date", ""),
                    "l_date": rec.get("l_date", ""),
                    "market": rec.get("market", "KR"),
                    "fx_rate": rec.get("fx_rate", GLOBAL_FX_RATE if rec.get("market", "KR") == "US" else 1.0),
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
    base_step = 1.0 + gear  # percent step for ladder
    ladder = [base_step, 2.0 * base_step, 3.0 * base_step]
    return {
        "gear": gear,
        "trend": trend,
        "penalty": penalty,
        "base_step": base_step,
        "ladder": ladder,
        "f": f,
    }


def compute_entry_threshold(g_score, l_score, v_score, quantize=True):
    trend = compute_trend(g_score, l_score)
    dip = 10.0 - trend + v_score
    dip = min(12.0, max(5.0, dip))
    if quantize:
        dip = round(dip * 10.0) / 10.0
    no_go = trend < 1.5
    return {
        "trend": trend,
        "dip_pct": dip,
        "no_go": no_go,
        "v": v_score,
    }


def compute(
    avg_cost,
    num_shares,
    max_volume_krw,
    buy_model_name,
    manual_mode,
    manual_step,
    market,
    fx_rate,
    g_score,
    l_score,
    v_score,
):
    model = BUY_MODELS[buy_model_name]
    gear_drop_pct = model["gear_drop"]
    gear_drop = gear_drop_pct / 100
    r = model["r"]

    if market == "US":
        max_volume = (max_volume_krw / fx_rate) if fx_rate else 0.0
    else:
        max_volume = max_volume_krw

    current_volume = avg_cost * num_shares
    u = (current_volume / max_volume) if max_volume else 0.0

    next_buy_price = avg_cost * (1 - gear_drop)
    buy_shares_calc = (r * num_shares) if num_shares > 0 else 1.0
    buy_shares_actual = max(1.0, float(int(buy_shares_calc + 0.5)))
    new_shares_actual = num_shares + buy_shares_actual

    new_avg_actual = (
        (avg_cost * num_shares + next_buy_price * buy_shares_actual) / new_shares_actual
        if new_shares_actual
        else avg_cost
    )

    new_volume_actual = new_avg_actual * new_shares_actual
    new_u_actual = new_volume_actual / max_volume if max_volume else 0.0

    auto_gear = compute_auto_gear(g_score, l_score, u)

    manual_step_val = manual_step if manual_step is not None else 0.0
    if manual_mode:
        active_step_pct = 1.0 + max(manual_step_val, 0.0)
        sell_mode = "Manual"
        ladder_pct = [active_step_pct, active_step_pct * 2, active_step_pct * 3]
    else:
        active_step_pct = auto_gear["base_step"]
        sell_mode = "Auto"
        ladder_pct = auto_gear["ladder"]

    s = active_step_pct / 100
    sell_targets = [
        avg_cost * (1 + s),
        avg_cost * (1 + 2 * s),
        avg_cost * (1 + 3 * s),
    ]

    base_denominator = num_shares if num_shares > 0 else 1.0
    buy_prop_actual = buy_shares_actual / base_denominator

    return {
        "model": model,
        "next_buy_price": next_buy_price,
        "buy_shares_actual": buy_shares_actual,
        "buy_value_actual": buy_shares_actual * next_buy_price,
        "new_avg_actual": new_avg_actual,
        "current_volume": current_volume,
        "new_volume_actual": new_volume_actual,
        "u": u,
        "new_u_actual": new_u_actual,
        "auto_gear": auto_gear,
        "manual_step": manual_step_val,
        "active_step": active_step_pct,
        "sell_targets": sell_targets,
        "ladder_pct": ladder_pct,
        "mode": sell_mode,
        "gear_drop_pct": gear_drop_pct,
        "buy_prop_actual": buy_prop_actual,
        "active_manual": manual_mode,
        "trend": auto_gear["trend"],
        "v_score": v_score,
    }


def parse_form_inputs():
    try:
        def to_float_str(val):
            return float(str(val).replace(" ", "").replace(",", ""))

        avg_cost = to_float_str(avg_cost_var.get())
        num_shares = to_float_str(num_shares_var.get())
        max_volume = to_float_str(max_volume_var.get())
        market = market_var.get()
        fx_rate = to_float_str(fx_rate_var.get()) if market == "US" else to_float_str(fx_rate_var.get() or GLOBAL_FX_RATE)
        g_score = to_float_str(g_score_var.get())
        l_score = to_float_str(l_score_var.get())
        v_score = to_float_str(v_score_var.get())
        manual_step = to_float_str(manual_gear_var.get())
        if (
            avg_cost <= 0
            or max_volume <= 0
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
            "Use positive numbers (shares >= 0). FX must be > 0. G/L must be between 0 and 5. V must be between 0 and 2. Manual gear >= 0.",
        )
        return None

    return {
        "avg_cost": avg_cost,
        "num_shares": num_shares,
        "max_volume": max_volume,
        "market": market,
        "fx_rate": fx_rate,
        "buy_model": buy_model_var.get(),
        "manual_mode": bool(manual_sell_var.get()),
        "manual_step": manual_step,
        "g_score": g_score,
        "l_score": l_score,
        "v_score": v_score,
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
    fx_rate_var.set(format_input(rec.get("fx_rate", GLOBAL_FX_RATE), "KR", decimals=2))
    buy_model_var.set(rec.get("buy_model", list(BUY_MODELS.keys())[0]))
    manual_sell_var.set(rec.get("manual_mode", 0))
    try:
        manual_gear_val = float(rec.get("manual_gear", 0.0) or 0.0)
    except (TypeError, ValueError):
        manual_gear_val = 0.0
    manual_gear_var.set(manual_gear_val)
    g_val = rec.get("g_score", "")
    l_val = rec.get("l_score", "")
    v_val = rec.get("v_score", "")
    g_score_var.set("" if g_val == "" else format_input(g_val, "KR", is_money=False, decimals=1))
    l_score_var.set("" if l_val == "" else format_input(l_val, "KR", is_money=False, decimals=1))
    v_score_var.set("" if v_val == "" else format_input(v_val, "KR", is_money=False, decimals=2))
    g_date_var.set(rec.get("g_date", ""))
    l_date_var.set(rec.get("l_date", ""))
    update_manual_state()
    update_market_state()


def clear_form_fields():
    name_var.set("")
    avg_cost_var.set("")
    num_shares_var.set("")
    max_volume_var.set("")
    fx_rate_var.set(format_input(GLOBAL_FX_RATE, "KR", decimals=2))
    market_var.set("KR")
    buy_model_var.set(list(BUY_MODELS.keys())[0])
    manual_sell_var.set(0)
    manual_gear_var.set(0.0)
    g_score_var.set("0.0")
    l_score_var.set("0.0")
    v_score_var.set("1.0")
    g_date_var.set("")
    l_date_var.set("")
    update_manual_state()
    update_market_state()


def on_select_stock(selected=None):
    choice = selected or name_choice_var.get()
    if not choice:
        clear_form_fields()
        return
    name_choice_var.set(choice)
    fill_form_from_record(choice)


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

    stock_data[selected] = {
        "avg_cost": parsed["avg_cost"],
        "num_shares": parsed["num_shares"],
        "max_volume": parsed["max_volume"],
        "buy_model": parsed["buy_model"],
        "manual_mode": 1 if parsed["manual_mode"] else 0,
        "manual_gear": parsed["manual_step"],
        "g_score": parsed["g_score"],
        "l_score": parsed["l_score"],
        "v_score": parsed["v_score"],
        "g_date": parsed["g_date"],
        "l_date": parsed["l_date"],
        "market": parsed["market"],
        "fx_rate": parsed["fx_rate"],
    }
    if parsed["market"] == "US":
        GLOBAL_FX_RATE = parsed["fx_rate"]
        for _, rec in stock_data.items():
            if rec.get("market") == "US":
                rec["fx_rate"] = GLOBAL_FX_RATE
    if selected not in stock_order:
        stock_order.append(selected)

    write_data_file()
    messagebox.showinfo("Saved", f"Saved data for '{selected}'.")


def on_show():
    parsed = parse_form_inputs()
    if parsed is None:
        return

    data = compute(
        parsed["avg_cost"],
        parsed["num_shares"],
        parsed["max_volume"],
        parsed["buy_model"],
        parsed["manual_mode"],
        parsed["manual_step"],
        parsed["market"],
        parsed["fx_rate"],
        parsed["g_score"],
        parsed["l_score"],
        parsed["v_score"],
    )

    auto_info = data["auto_gear"]
    auto_ladder_pct = auto_info["ladder"]
    auto_ladder_txt = f"+{auto_ladder_pct[0]:.1f}%/+{auto_ladder_pct[1]:.1f}%/+{auto_ladder_pct[2]:.1f}%"
    if parsed["manual_mode"]:
        ladder_pct = data["ladder_pct"]
        gear_label = (
            f"Sell (Manual): step={data['active_step']:.1f}% "
            f"-> +{ladder_pct[0]:.1f}%/+{ladder_pct[1]:.1f}%/+{ladder_pct[2]:.1f}% "
            f"(auto g={auto_info['gear']:.1f}, step={auto_info['base_step']:.1f}%)"
        )
    else:
        ladder_pct = auto_ladder_pct
        gear_label = (
            f"Sell (Auto): g={auto_info['gear']:.1f} (trend={auto_info['trend']:.1f}, penalty={auto_info['penalty']:.1f}) "
            f"step={auto_info['base_step']:.1f}% -> {auto_ladder_txt}"
        )

    deployment_text = (
        f"Deployment fraction f: {data['u']*100:.1f}% (current), {data['new_u_actual']*100:.1f}% (if actual buy fills)"
    )
    share_after = data["new_u_actual"] * 100
    fmt_val = lambda val: fmt_money(val, parsed["market"])

    gl_text = (
        f"G={parsed['g_score']:.1f} ({parsed['g_date'] or 'date n/a'}), "
        f"L={parsed['l_score']:.1f} ({parsed['l_date'] or 'date n/a'}), "
        f"V={parsed['v_score']:.2f}"
    )
    auto_text = (
        f"Auto gear -> g={auto_info['gear']:.1f} (trend={auto_info['trend']:.1f}, penalty={auto_info['penalty']:.1f}), "
        f"step={auto_info['base_step']:.1f}% ({auto_ladder_txt})"
    )

    result_lines = [
        f"Name: {name_var.get().strip() or '(none)'}",
        gl_text,
        f"Buy model: {parsed['buy_model']}",
        f"Next buy trigger: {fmt_val(data['next_buy_price'])}",
        f"Current size: {fmt_val(data['current_volume'])}",
        f"Actual buy size: {fmt_val(data['buy_value_actual'])} (shares {int(data['buy_shares_actual'])}, proportion={data['buy_prop_actual']:.2f})",
        f"Projected avg (share = {share_after:.1f}%): {fmt_val(data['new_avg_actual'])}",
        deployment_text,
        auto_text,
        gear_label,
        "Targets: " + " / ".join(fmt_val(val) for val in data["sell_targets"]),
    ]
    result_var.set("\n".join(result_lines))

    plot_levels(
        avg_cost=parsed["avg_cost"],
        next_buy_price=data["next_buy_price"],
        sell_targets=data["sell_targets"],
        current_u=data["u"],
        max_volume=parsed["max_volume"],
        buy_value=data["buy_value_actual"],
        buy_shares=data["buy_shares_actual"],
        gear_drop_pct=data["gear_drop_pct"],
        name=name_var.get().strip(),
        new_avg=data["new_avg_actual"],
        new_u=data["new_u_actual"],
        market=parsed["market"],
        fx_rate=parsed["fx_rate"],
    )


def open_entry_window():
    # Use current G/L/V and market to compute entry trigger from v1.2 rules.
    try:
        g = float(str(g_score_var.get()).replace(",", ""))
        l = float(str(l_score_var.get()).replace(",", ""))
        v = float(str(v_score_var.get()).replace(",", ""))
        if not (0 <= g <= 5) or not (0 <= l <= 5) or not (0 <= v <= 2):
            raise ValueError()
    except ValueError:
        messagebox.showerror("Input error", "Set valid G/L (0-5) and V (0-2) before opening the entry window.")
        return

    entry_info = compute_entry_threshold(g, l, v)

    top = tk.Toplevel(root)
    top.title("Entry Decider (G/L/V)")
    top.transient(root)
    top.grab_set()

    ttk.Label(top, text=f"G = {g:.1f}, L = {l:.1f}, V = {v:.2f}").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))
    ttk.Label(top, text=f"Trend T = {entry_info['trend']:.1f}").grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=2)
    ttk.Label(top, text=f"Auto entry dip: {entry_info['dip_pct']:.1f}% below 10-day high").grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=2)
    if entry_info["no_go"]:
        ttk.Label(top, foreground="red", text="No-go guard: T < 1.5 (manual check before entry).").grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=2)

    ttk.Label(top, text="10-day high price").grid(row=4, column=0, sticky="e", padx=8, pady=4)
    high_var = tk.StringVar()
    ttk.Entry(top, textvariable=high_var, width=18).grid(row=4, column=1, sticky="w", padx=4, pady=4)

    entry_result_var = tk.StringVar()

    def on_calc_entry():
        try:
            high_price = float(str(high_var.get()).replace(",", ""))
            if high_price <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Input error", "10-day high must be a positive number.")
            return
        entry_price = high_price * (1 - entry_info["dip_pct"] / 100.0)
        lines = [
            f"Trend T = {entry_info['trend']:.1f}",
            f"Entry dip threshold: {entry_info['dip_pct']:.1f}% below 10-day high",
            f"10-day high: {fmt_money(high_price, market_var.get())}",
            f"Entry price target: {fmt_money(entry_price, market_var.get())}",
        ]
        if entry_info["no_go"]:
            lines.append("No-go guard: T < 1.5 (skip new campaign).")
        entry_result_var.set("\n".join(lines))

    btn_frame = ttk.Frame(top)
    btn_frame.grid(row=5, column=0, columnspan=2, pady=6)
    ttk.Button(btn_frame, text="Show Entry Result", command=on_calc_entry).grid(row=0, column=0, padx=4)
    ttk.Button(btn_frame, text="Close", command=top.destroy).grid(row=0, column=1, padx=4)

    ttk.Label(top, textvariable=entry_result_var, justify="left").grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))


def plot_levels(avg_cost, next_buy_price, sell_targets, current_u, max_volume, buy_value, buy_shares, gear_drop_pct, name, new_avg, new_u, market, fx_rate):
    fig.clear()
    ax = fig.add_subplot(111)
    x_start, x_end = 0.0, 1.0
    volume_pct = current_u * 100
    new_volume_pct = new_u * 100

    fmt_val = lambda val: fmt_money(val, market)
    levels = [
        ("Avg cost", avg_cost, "black", "-", f"share = {volume_pct:.1f}%", f"{fmt_val(avg_cost)}", 3.6),
        ("Projected avg", new_avg, "#cccccc", "--", f"share = {new_volume_pct:.1f}%", f"{fmt_val(new_avg)}", 1.4),
        ("Next buy", next_buy_price, "red", "-", f"buy {fmt_val(buy_value)} ({int(buy_shares)} sh)", f"{fmt_val(next_buy_price)}", 2.4),
        ("Sell T1 (50%)", sell_targets[0], "#0a8f08", "-", "50%", f"{fmt_val(sell_targets[0])}", 3.0),
        ("Sell T2 (25%)", sell_targets[1], "#0066cc", "-.", "25%", f"{fmt_val(sell_targets[1])}", 2.2),
        ("Sell T3 (25%)", sell_targets[2], "#8a2be2", ":", "25%", f"{fmt_val(sell_targets[2])}", 1.6),
    ]
    for label, y, color, style, left_text, right_text, lw in levels:
        ax.plot([x_start, x_end], [y, y], color=color, linestyle=style, linewidth=lw)
        ax.text(
            x_start + 0.01,
            y,
            f"{label} ({left_text})",
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
    # Vertical gap annotations
    gap_x = 0.5
    buy_gap_pct = -gear_drop_pct
    ax.plot([gap_x, gap_x], [next_buy_price, avg_cost], color="red", linestyle="--", linewidth=1.0)
    ax.text(gap_x + 0.01, (next_buy_price + avg_cost) / 2, f"{buy_gap_pct:.1f}%", va="center", ha="left", fontsize=9, color="red")

    gap_x2 = 0.75
    proj_gap_pct = ((new_avg - next_buy_price) / next_buy_price * 100) if next_buy_price else 0
    ax.plot([gap_x2, gap_x2], [next_buy_price, new_avg], color="#777777", linestyle="--", linewidth=1.0)
    ax.text(gap_x2 + 0.01, (next_buy_price + new_avg) / 2, f"+{proj_gap_pct:.1f}%", va="center", ha="left", fontsize=9, color="#555555")

    s_pct = (sell_targets[0] / avg_cost - 1) * 100 if avg_cost else 0
    gaps = [
        (avg_cost, sell_targets[0], s_pct),
        (sell_targets[0], sell_targets[1], s_pct),
        (sell_targets[1], sell_targets[2], s_pct),
    ]
    gap_color = "#0066cc"
    for y0, y1, pct in gaps:
        ax.plot([gap_x, gap_x], [y0, y1], color=gap_color, linestyle="--", linewidth=1.0)
        ax.text(gap_x + 0.01, (y0 + y1) / 2, f"+{pct:.1f}%", va="center", ha="left", fontsize=9, color=gap_color)

    ymin = min(next_buy_price, avg_cost, new_avg, *sell_targets)
    ymax = max(next_buy_price, avg_cost, new_avg, *sell_targets)
    pad = (ymax - ymin) * 0.1 if ymax != ymin else 1
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
    label = f"Step {effective_step:.1f}% -> +{effective_step:.1f}% / +{2*effective_step:.1f}% / +{3*effective_step:.1f}%"
    manual_gear_label.config(text=label)


def update_manual_state():
    state_flag = manual_sell_var.get()
    if state_flag:
        manual_slider.state(["!disabled"])
    else:
        manual_slider.state(["disabled"])
    update_manual_label()


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
max_volume_var = tk.StringVar()
fx_rate_var = tk.StringVar()
market_var = tk.StringVar(value="KR")
buy_model_var = tk.StringVar(value=list(BUY_MODELS.keys())[0])
manual_sell_var = tk.IntVar(value=0)
g_score_var = tk.StringVar(value="0.0")
l_score_var = tk.StringVar(value="0.0")
v_score_var = tk.StringVar(value="1.0")
g_date_var = tk.StringVar()
l_date_var = tk.StringVar()
manual_gear_var = tk.DoubleVar(value=0.0)
result_var = tk.StringVar()

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

ttk.Label(form, text="Max Volume (₩)").grid(row=3, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form, textvariable=max_volume_var, width=16).grid(
    row=3, column=1, sticky="w", padx=4, pady=4
)

market_frame = ttk.Frame(form)
market_frame.grid(row=4, column=0, columnspan=2, sticky="w", padx=4, pady=4)
ttk.Label(market_frame, text="Market").grid(row=0, column=0, sticky="w", padx=(0, 8))
ttk.Radiobutton(market_frame, text="KR", value="KR", variable=market_var, command=update_market_state).grid(
    row=0, column=1, sticky="w", padx=(0, 8)
)
ttk.Radiobutton(market_frame, text="US", value="US", variable=market_var, command=update_market_state).grid(
    row=0, column=2, sticky="w"
)

fx_frame = ttk.Frame(form)
fx_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4))
ttk.Label(fx_frame, text="FX rate (₩ per $)").grid(row=0, column=0, sticky="e", padx=(0, 8))
fx_entry = ttk.Entry(fx_frame, textvariable=fx_rate_var, width=16)
fx_entry.grid(row=0, column=1, sticky="w")

ttk.Label(form, text="Buy Model").grid(row=6, column=0, sticky="ne", padx=4, pady=4)
buy_frame = ttk.Frame(form)
buy_frame.grid(row=6, column=1, sticky="w", padx=4, pady=4)
for name in BUY_MODELS:
    ttk.Radiobutton(buy_frame, text=name, value=name, variable=buy_model_var).pack(anchor="w")

gl_frame = ttk.LabelFrame(form, text="G / L inputs")
gl_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
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
manual_frame.grid(row=8, column=0, columnspan=2, sticky="w", padx=4, pady=4)
ttk.Checkbutton(
    manual_frame,
    text="Manual sell gear",
    variable=manual_sell_var,
    command=update_manual_state,
).grid(row=0, column=0, sticky="w", pady=(0, 4))
ttk.Label(manual_frame, text="Manual gear bar (0-5)").grid(row=1, column=0, sticky="w")
manual_slider = ttk.Scale(
    manual_frame,
    from_=0.0,
    to=5.0,
    orient="horizontal",
    variable=manual_gear_var,
    command=update_manual_label,
    length=220,
)
manual_slider.grid(row=2, column=0, sticky="w", pady=(0, 2))
manual_gear_label = ttk.Label(manual_frame, text="")
manual_gear_label.grid(row=3, column=0, sticky="w")
ttk.Label(manual_frame, text="Base step = 1% + slider (0 -> 1/2/3, 5 -> 6/12/18).").grid(
    row=4, column=0, sticky="w"
)

ttk.Button(form, text="New Entry (G/L/V)", command=open_entry_window).grid(
    row=9, column=0, columnspan=2, pady=(4, 4), sticky="ew"
)
ttk.Button(form, text="Show Result", command=on_show).grid(
    row=10, column=0, columnspan=2, pady=12, sticky="ew"
)
ttk.Button(form, text="Save Result", command=on_save).grid(
    row=11, column=0, columnspan=2, pady=(0, 12), sticky="ew"
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
update_market_state()

root.mainloop()
