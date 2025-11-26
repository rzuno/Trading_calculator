import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Buy models (gear_drop %, r)
BUY_MODELS = {
    "Agile": {"gear_drop": 5.0, "r": 0.6},
    "Heavy": {"gear_drop": 6.0, "r": 0.7},
    "Greedy": {"gear_drop": 4.0, "r": 0.7},
    "Cautious": {"gear_drop": 7.0, "r": 0.65},
}

# Automatic sell gears chosen by deployment U
SELL_GEARS = [
    {"name": "Very Light", "min_u": 0.0, "max_u": 0.2, "s": 6.0},
    {"name": "Light", "min_u": 0.2, "max_u": 0.4, "s": 5.0},
    {"name": "Medium", "min_u": 0.4, "max_u": 0.6, "s": 4.0},
    {"name": "Heavy", "min_u": 0.6, "max_u": 0.8, "s": 3.0},
    {"name": "Very Heavy", "min_u": 0.8, "max_u": 1.01, "s": 2.0},
]

# Manual sell gears selectable by toggle
MANUAL_SELL_GEARS = {
    "Gear1": {"name": "Gear1 (6/12/18)", "s": 6.0},
    "Gear2": {"name": "Gear2 (5/10/15)", "s": 5.0},
    "Gear3": {"name": "Gear3 (4/8/12)", "s": 4.0},
    "Gear4": {"name": "Gear4 (3/6/9)", "s": 3.0},
    "Gear5": {"name": "Gear5 (2/4/6)", "s": 2.0},
}


def pick_auto_sell_gear(u):
    for gear in SELL_GEARS:
        if gear["min_u"] <= u < gear["max_u"]:
            return gear
    return SELL_GEARS[-1]


def pick_manual_sell_gear(key):
    return MANUAL_SELL_GEARS.get(key, MANUAL_SELL_GEARS["Gear1"])


def compute(avg_cost, current_units, max_units, buy_model_name, emergency, manual_mode, manual_key):
    model = BUY_MODELS[buy_model_name]
    gear_drop = model["gear_drop"] / 100
    r = model["r"]
    u = (current_units / max_units) if max_units else 0.0

    next_buy_price = avg_cost * (1 - gear_drop)
    buy_units = (r * current_units) if current_units > 0 else 1.0
    new_units = current_units + buy_units
    new_avg = (
        (avg_cost * current_units + next_buy_price * buy_units) / new_units
        if new_units
        else avg_cost
    )
    new_u = new_units / max_units if max_units else 0.0

    if emergency:
        sell_gear = {"name": "Emergency", "s": 1.0}
    elif manual_mode:
        sell_gear = pick_manual_sell_gear(manual_key)
    else:
        sell_gear = pick_auto_sell_gear(u)

    s = sell_gear["s"] / 100
    sell_targets = [
        avg_cost * (1 + s),
        avg_cost * (1 + 2 * s),
        avg_cost * (1 + 3 * s),
    ]

    return {
        "model": model,
        "next_buy_price": next_buy_price,
        "buy_units": buy_units,
        "new_avg": new_avg,
        "u": u,
        "new_u": new_u,
        "sell_gear": sell_gear,
        "sell_targets": sell_targets,
        "mode": "Emergency" if emergency else ("Manual" if manual_mode else "Auto"),
    }


def on_show():
    try:
        avg_cost = float(avg_cost_var.get())
        current_units = float(current_units_var.get())
        max_units = float(max_units_var.get())
        if avg_cost <= 0 or max_units <= 0 or current_units < 0:
            raise ValueError()
    except ValueError:
        messagebox.showerror("Input error", "Use positive numbers (units >= 0).")
        return

    emergency = bool(emergency_var.get())
    manual_mode = bool(manual_sell_var.get())
    manual_key = manual_gear_var.get()
    buy_model = buy_model_var.get()

    data = compute(
        avg_cost,
        current_units,
        max_units,
        buy_model,
        emergency,
        manual_mode,
        manual_key,
    )

    sg = data["sell_gear"]
    s = sg["s"]
    mode_text = f"Sell gear ({data['mode']})"
    result_lines = [
        f"Buy model: {buy_model} (drop {data['model']['gear_drop']}%, r {data['model']['r']})",
        f"Next buy trigger: {data['next_buy_price']:.2f}",
        f"Buy size: {data['buy_units']:.3f} units (from {current_units:.3f} -> {data['new_u']*100:.1f}% of max)",
        f"Projected avg after buy: {data['new_avg']:.2f}",
        f"Deployment U: {data['u']*100:.1f}% (current), {data['new_u']*100:.1f}% (if next buy fills)",
        f"{mode_text}: {sg['name']} (+{s:.0f}%/+{2*s:.0f}%/+{3*s:.0f}%)",
        f"Targets: {data['sell_targets'][0]:.2f} / {data['sell_targets'][1]:.2f} / {data['sell_targets'][2]:.2f}",
    ]
    result_var.set("\n".join(result_lines))

    plot_levels(avg_cost, data["next_buy_price"], data["sell_targets"])


def plot_levels(avg_cost, next_buy_price, sell_targets):
    fig.clear()
    ax = fig.add_subplot(111)
    levels = [
        ("Avg cost", avg_cost, "gray", ":"),
        ("Next buy", next_buy_price, "green", "--"),
        ("Sell T1", sell_targets[0], "orange", "-"),
        ("Sell T2", sell_targets[1], "red", "-."),
        ("Sell T3", sell_targets[2], "purple", "-"),
    ]
    for label, y, color, style in levels:
        ax.axhline(y, color=color, linestyle=style, label=f"{label} {y:.2f}")
    ymin = min(next_buy_price, avg_cost, *sell_targets)
    ymax = max(next_buy_price, avg_cost, *sell_targets)
    pad = (ymax - ymin) * 0.1 if ymax != ymin else 1
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_title("Seesaw Targets")
    ax.set_ylabel("Price")
    ax.legend(loc="best", fontsize="small")
    canvas.draw()


def update_manual_state():
    state_flag = manual_sell_var.get()
    for rb in manual_gear_buttons:
        if state_flag:
            rb.state(["!disabled"])
        else:
            rb.state(["disabled"])


root = tk.Tk()
root.title("AI Seesaw Trading Calculator")

main = ttk.Frame(root, padding=12)
main.grid(sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

avg_cost_var = tk.StringVar()
current_units_var = tk.StringVar()
max_units_var = tk.StringVar()
buy_model_var = tk.StringVar(value="Agile")
emergency_var = tk.IntVar(value=0)
manual_sell_var = tk.IntVar(value=0)
manual_gear_var = tk.StringVar(value="Gear1")
result_var = tk.StringVar()

ttk.Label(main, text="Average Cost").grid(row=0, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(main, textvariable=avg_cost_var, width=14).grid(
    row=0, column=1, sticky="w", padx=4, pady=4
)

ttk.Label(main, text="Current Units").grid(row=1, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(main, textvariable=current_units_var, width=14).grid(
    row=1, column=1, sticky="w", padx=4, pady=4
)

ttk.Label(main, text="Max Units").grid(row=2, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(main, textvariable=max_units_var, width=14).grid(
    row=2, column=1, sticky="w", padx=4, pady=4
)

ttk.Label(main, text="Buy Model").grid(row=3, column=0, sticky="ne", padx=4, pady=4)
buy_frame = ttk.Frame(main)
buy_frame.grid(row=3, column=1, sticky="w", padx=4, pady=4)
for name in BUY_MODELS:
    ttk.Radiobutton(buy_frame, text=name, value=name, variable=buy_model_var).pack(
        anchor="w"
    )

ttk.Checkbutton(main, text="Emergency sell gear (1/2/3%)", variable=emergency_var).grid(
    row=4, column=0, columnspan=2, sticky="w", padx=4, pady=4
)

manual_frame = ttk.Frame(main)
manual_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=4)
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

ttk.Button(main, text="Show Result", command=on_show).grid(
    row=6, column=0, columnspan=2, pady=10
)
ttk.Label(main, textvariable=result_var, justify="left").grid(
    row=7, column=0, columnspan=2, sticky="w"
)

fig = Figure(figsize=(5.5, 3.5), dpi=100)
canvas = FigureCanvasTkAgg(fig, master=main)
canvas.get_tk_widget().grid(row=8, column=0, columnspan=2, pady=10, sticky="nsew")

main.rowconfigure(8, weight=1)
main.columnconfigure(1, weight=1)

update_manual_state()

root.mainloop()
