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

# Automatic sell gears chosen by deployment ratio
SELL_GEARS = [
    {"name": "Gear1", "gear_num": 1, "min_u": 0.0, "max_u": 0.2, "s": 6.0},
    {"name": "Gear2", "gear_num": 2, "min_u": 0.2, "max_u": 0.4, "s": 5.0},
    {"name": "Gear3", "gear_num": 3, "min_u": 0.4, "max_u": 0.6, "s": 4.0},
    {"name": "Gear4", "gear_num": 4, "min_u": 0.6, "max_u": 0.8, "s": 3.0},
    {"name": "Gear5", "gear_num": 5, "min_u": 0.8, "max_u": 1.01, "s": 2.0},
]

# Manual sell gears selectable by toggle
MANUAL_SELL_GEARS = {
    "Gear1": {"name": "Gear1 (1/2/3%)", "s": 1.0},
    "Gear2": {"name": "Gear2 (2/4/6%)", "s": 2.0},
    "Gear3": {"name": "Gear3 (3/6/9%)", "s": 3.0},
    "Gear4": {"name": "Gear4 (4/8/12%)", "s": 4.0},
    "Gear5": {"name": "Gear5 (5/10/15%)", "s": 5.0},
    "Gear6": {"name": "Gear6 (6/12/18%)", "s": 6.0},
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
        "manual_gear": "Gear1",
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

                stock_data[name] = {
                    "avg_cost": avg_cost,
                    "num_shares": num_shares,
                    "max_volume": max_volume,
                    "market": market,
                    "fx_rate": fx_rate,
                    "buy_model": row.get("buy_model", list(BUY_MODELS.keys())[0]),
                    "manual_mode": manual_mode,
                    "manual_gear": row.get("manual_gear", "Gear1"),
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
                    "manual_gear": rec.get("manual_gear", "Gear1"),
                    "market": rec.get("market", "KR"),
                    "fx_rate": rec.get("fx_rate", GLOBAL_FX_RATE if rec.get("market", "KR") == "US" else 1.0),
                }
            )


def pick_auto_sell_gear(u):
    for gear in SELL_GEARS:
        if gear["min_u"] <= u < gear["max_u"]:
            return gear
    return SELL_GEARS[-1]


def pick_manual_sell_gear(key):
    return MANUAL_SELL_GEARS.get(key, MANUAL_SELL_GEARS["Gear1"])


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


def compute(avg_cost, num_shares, max_volume_krw, buy_model_name, manual_mode, manual_key, market, fx_rate):
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

    if manual_mode:
        sell_gear = pick_manual_sell_gear(manual_key)
    else:
        sell_gear = pick_auto_sell_gear(u)

    s = sell_gear["s"] / 100
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
        "sell_gear": sell_gear,
        "sell_targets": sell_targets,
        "mode": "Manual" if manual_mode else "Auto",
        "gear_drop_pct": gear_drop_pct,
        "buy_prop_actual": buy_prop_actual,
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
        if avg_cost <= 0 or max_volume <= 0 or num_shares < 0 or fx_rate <= 0:
            raise ValueError()
    except ValueError:
        messagebox.showerror("Input error", "Use positive numbers (shares >= 0). FX must be > 0.")
        return None

    return {
        "avg_cost": avg_cost,
        "num_shares": num_shares,
        "max_volume": max_volume,
        "market": market,
        "fx_rate": fx_rate,
        "buy_model": buy_model_var.get(),
        "manual_mode": bool(manual_sell_var.get()),
        "manual_key": manual_gear_var.get(),
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
    manual_gear_var.set(rec.get("manual_gear", "Gear1"))
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
    manual_gear_var.set("Gear1")
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
        "manual_gear": parsed["manual_key"],
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
        parsed["manual_key"],
        parsed["market"],
        parsed["fx_rate"],
    )

    sg = data["sell_gear"]
    s = sg["s"]
    if parsed["manual_mode"]:
        gear_label = f"Sell (Manual): {sg['name']} (+{s:.0f}%/+{2*s:.0f}%/+{3*s:.0f}%)"
    else:
        gear_label = f"Sell (Auto): gear {sg.get('gear_num', '?')} (+{s:.0f}%/+{2*s:.0f}%/+{3*s:.0f}%)"

    deployment_text = f"Deployment percentage: {data['u']*100:.1f}% (current), {data['new_u_actual']*100:.1f}% (if actual buy fills)"
    share_after = data["new_u_actual"] * 100
    fmt_val = lambda val: fmt_money(val, parsed["market"])

    result_lines = [
        f"Name: {name_var.get().strip() or '(none)'}",
        f"Buy model: {parsed['buy_model']}",
        f"Next buy trigger: {fmt_val(data['next_buy_price'])}",
        f"Current size: {fmt_val(data['current_volume'])}",
        f"Actual buy size: {fmt_val(data['buy_value_actual'])} (shares {int(data['buy_shares_actual'])}, proportion={data['buy_prop_actual']:.2f})",
        f"Projected avg (share = {share_after:.1f}%): {fmt_val(data['new_avg_actual'])}",
        deployment_text,
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


def update_manual_state():
    state_flag = manual_sell_var.get()
    for rb in manual_gear_buttons:
        if state_flag:
            rb.state(["!disabled"])
        else:
            rb.state(["disabled"])


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
manual_gear_var = tk.StringVar(value="Gear1")
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

manual_frame = ttk.Frame(form)
manual_frame.grid(row=7, column=0, columnspan=2, sticky="w", padx=4, pady=4)
ttk.Checkbutton(
    manual_frame,
    text="Manual sell gear",
    variable=manual_sell_var,
    command=update_manual_state,
).grid(row=0, column=0, sticky="w")
manual_gears_frame = ttk.Frame(manual_frame)
manual_gears_frame.grid(row=1, column=0, sticky="w", pady=(4, 0))
manual_gear_buttons = []
for idx, key in enumerate(MANUAL_SELL_GEARS):
    gear = MANUAL_SELL_GEARS[key]
    rb = ttk.Radiobutton(
        manual_gears_frame, text=gear["name"], value=key, variable=manual_gear_var
    )
    rb.grid(row=idx, column=0, sticky="w")
    manual_gear_buttons.append(rb)

ttk.Button(form, text="Show Result", command=on_show).grid(
    row=8, column=0, columnspan=2, pady=12, sticky="ew"
)
ttk.Button(form, text="Save Result", command=on_save).grid(
    row=9, column=0, columnspan=2, pady=(0, 12), sticky="ew"
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
