"""Generate the 12-slide pitch deck from recalculated model outputs (output/model_values.json).

Run after model/check_model.py:  python deck/build_deck.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
IMG = OUT / "charts"
IMG.mkdir(parents=True, exist_ok=True)
v = json.loads((OUT / "model_values.json").read_text())

NAVY, SLATE, GREY, LIGHT = "1F2A44", "4A5568", "8A94A6", "EEF1F6"
ACCENT, GREEN, RED = "C8553D", "2F855A", "B83232"
rgb = lambda h: RGBColor.from_string(h)
hexc = lambda h: "#" + h

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#BBBBBB", "axes.labelcolor": hexc(SLATE),
                     "xtick.color": hexc(SLATE), "ytick.color": hexc(SLATE)})

B = lambda x: f"${x/1000:.2f}T" if x >= 1000 else f"${x:,.0f}B"
P = lambda x: f"{x*100:.0f}%"
bear, base, bull = v["blend"]
tok = v["tok"]


# ---------------------------------------------------------------- charts
def save(fig, name):
    path = IMG / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", transparent=False, facecolor="white")
    plt.close(fig)
    return path


def chart_quarters():
    labels = ["Q1-26", "Q2-26", "Q3-26", "Q4-26E", "Q1-27E", "Q2-27E", "Q3-27E"]
    vals = [v["nine_m"] - 11.555 - 16.962, 11.555, 16.962]
    g = [0.25, 0.18, 0.14, 0.11]
    for x in g:
        vals.append(vals[-1] * (1 + x))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    cols = [hexc(NAVY)] * 3 + [hexc(GREY)] * 4
    bars = ax.bar(labels, vals, color=cols, width=0.62)
    for b_, x in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, x + 0.4, f"{x:.1f}", ha="center", fontsize=10, color=hexc(SLATE))
    ax.set_ylabel("Quarterly revenue ($B)")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.text(2, vals[2] + 3.2, "+47% QoQ", ha="center", color=hexc(ACCENT), fontsize=10, weight="bold")
    return save(fig, "quarters")


def chart_cost_stack():
    rows = v["dcf_rows"]
    years = list(range(2027, 2037))
    rev = rows["Revenue"][1][1:]
    comp = [-c / r for c, r in zip(rows["TOTAL COMPUTE COST"][1][1:], rev)]
    ebit = rows["EBIT margin"][1][1:]
    opex = [1 - c - e for c, e in zip(comp, ebit)]
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    ax.stackplot(years, comp, opex, ebit, colors=[hexc(NAVY), hexc(GREY), hexc(GREEN)],
                 labels=["Compute (inference + training)", "Other opex", "EBIT margin"], alpha=0.95)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Base case: share of each revenue dollar", fontsize=11, color=hexc(SLATE), loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False, fontsize=9)
    return save(fig, "cost_stack")


def chart_football():
    ff = v["ff"]
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    for i, (lab, lo, mid, hi) in enumerate(ff):
        lo_, hi_ = min(lo, mid, hi), max(lo, mid, hi)
        color = hexc(ACCENT) if lab.startswith("Blended") else (hexc(GREY) if i >= 4 else hexc(NAVY))
        ax.barh(i, hi_ - lo_, left=lo_, color=color, height=0.55)
        ax.plot([mid, mid], [i - 0.32, i + 0.32], color="white" if i < 4 else hexc(NAVY), lw=2)
        ax.text(lo_ - 25, i, f"{lo_/1000:.2f}", va="center", ha="right", fontsize=9, color=hexc(SLATE))
        ax.text(hi_ + 25, i, f"{hi_/1000:.2f}", va="center", ha="left", fontsize=9, color=hexc(SLATE))
    ax.set_yticks(range(len(ff)))
    ax.set_yticklabels([r[0] for r in ff])
    ax.invert_yaxis()
    ax.axvline(965, color=hexc(SLATE), ls="--", lw=1)
    ax.text(965, -0.75, "Series H $0.97T", ha="center", fontsize=9, color=hexc(SLATE))
    ax.set_xlabel("Equity value ($T); tick = base case")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x/1000:.1f}"))
    ax.set_xlim(0, 2300)
    return save(fig, "football")


def chart_scenarios():
    rows = v["dcf_rows"]["Revenue"]
    years = list(range(2026, 2037))
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    for r, lab, c in zip(rows, ["Bear", "Base", "Bull"], [GREY, NAVY, ACCENT]):
        ax.plot(years, r, color=hexc(c), lw=2.4, label=lab)
        ax.text(2036.2, r[-1], f"{lab} ${r[-1]:.0f}B", va="center", fontsize=9, color=hexc(c))
    ax.set_ylabel("Revenue ($B)")
    ax.set_xlim(2026, 2038.3)
    ax.set_xticks(range(2026, 2037, 2))
    return save(fig, "scenarios")


def chart_waterfall():
    t = tok
    steps = [("Gross NAV\n(fair value)", t["nav"][1]), ("Mgmt fee", t["fee"][1]), ("Carry", t["carry"][1]),
             ("DLOM 15%", t["dlom"][1]), ("Transfer\nrisk 10%", t["xfer"][1])]
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    run = 0
    for i, (lab, x) in enumerate(steps):
        if i == 0:
            ax.bar(i, x, color=hexc(NAVY), width=0.6)
            run = x
            ax.text(i, x + 0.2, f"${x:.2f}", ha="center", fontsize=10)
        else:
            ax.bar(i, x, bottom=run, color=hexc(ACCENT), width=0.6)
            ax.text(i, run + 0.2, f"{x:+.2f}", ha="center", fontsize=10, color=hexc(ACCENT))
            run += x
    ax.bar(len(steps), run, color=hexc(GREY), width=0.6)
    ax.text(len(steps), run + 0.2, f"${run:.2f}", ha="center", fontsize=10, weight="bold")
    ax.axhline(10, color=hexc(RED), ls="--", lw=1.2)
    ax.text(len(steps) + 0.35, 10.15, "$10 issue price", ha="right", fontsize=9, color=hexc(RED))
    ax.set_xticks(range(len(steps) + 1))
    ax.set_xticklabels([s[0] for s in steps] + ["Token\nprice"], fontsize=9)
    ax.set_ylabel("$ per token (base case)")
    ax.set_ylim(0, 11.5)
    return save(fig, "waterfall")


charts = {"quarters": chart_quarters(), "cost": chart_cost_stack(), "ff": chart_football(),
          "scen": chart_scenarios(), "wf": chart_waterfall()}

# ---------------------------------------------------------------- deck helpers
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
SN = [0]


def text(slide, x, y, w, h, s, size=14, color=SLATE, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = s if isinstance(s, list) else [s]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), bold, rgb(color), "Calibri"
        p.space_after = Pt(6)
    return tb


def bullets(slide, x, y, w, h, items, size=15):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        head, _, rest = it.partition("|")
        r = p.add_run()
        r.text = "▪  " + head
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bool(rest), rgb(NAVY)
        if rest:
            r2 = p.add_run()
            r2.text = " " + rest
            r2.font.size, r2.font.color.rgb = Pt(size), rgb(SLATE)
        p.space_after = Pt(10)
    return tb


def slide(headline, sub=None, source=None):
    s = prs.slides.add_slide(BLANK)
    SN[0] += 1
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), prs.slide_height)
    bar.fill.solid(); bar.fill.fore_color.rgb = rgb(NAVY); bar.line.fill.background()
    text(s, 0.6, 0.35, 12.1, 1.1, headline, 26, NAVY, True)
    if sub:
        text(s, 0.6, 1.35, 12.1, 0.5, sub, 14, GREY)
    if source:
        text(s, 0.6, 6.95, 11.0, 0.4, "Source: " + source, 9, GREY)
    text(s, 12.2, 6.95, 0.8, 0.4, str(SN[0]), 9, GREY, align=PP_ALIGN.RIGHT)
    return s


def tile(s, x, y, w, h, big, small, color=NAVY):
    box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid(); box.fill.fore_color.rgb = rgb(LIGHT); box.line.fill.background()
    text(s, x + 0.15, y + 0.12, w - 0.3, 0.6, big, 24, color, True)
    text(s, x + 0.15, y + 0.75, w - 0.3, h - 0.8, small, 11, SLATE)


def table(s, x, y, w, rows, col_w=None, size=12, h_row=0.42):
    n_r, n_c = len(rows), len(rows[0])
    shp = s.shapes.add_table(n_r, n_c, Inches(x), Inches(y), Inches(w), Inches(h_row * n_r))
    tb = shp.table
    for j in range(n_c):
        if col_w:
            tb.columns[j].width = Inches(col_w[j])
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tb.cell(i, j)
            cell.text = str(val)
            para = cell.text_frame.paragraphs[0]
            para.font.size = Pt(size)
            para.font.bold = i == 0
            para.font.color.rgb = rgb("FFFFFF" if i == 0 else SLATE)
            para.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(NAVY if i == 0 else ("FFFFFF" if i % 2 else LIGHT))
    return tb


# ---------------------------------------------------------------- slides
# 1 Thesis
s = slide(f"Anthropic is worth ~{B(base)} in our base case; IPO talk of $1.5T+ already prices in the bull case",
          "Valuation of Anthropic PBC and design of a tokenized exposure vehicle  |  6 November 2026")
tile(s, 0.6, 2.1, 3.9, 1.6, f"{B(bear)} – {B(bull)}", "Blended equity value range, bear to bull (3 methods)")
tile(s, 4.7, 2.1, 3.9, 1.6, f"${tok['price_pre'][1]:.2f}", "Base-case implied token price vs $10.00 issue", ACCENT)
tile(s, 8.8, 2.1, 3.9, 1.6, B(v["be_pre"]), "Anthropic valuation needed for a pre-IPO token to break even")
bullets(s, 0.6, 4.1, 12.1, 2.7, [
    "Fundamentals support ~$1.1T.|Q3-26 revenue of $17.0B and ~85% gross margin justify a premium, but growth fell "
    "from +144% to +47% QoQ and $895B of compute is already committed.",
    "A token bought at today's secondary price starts underwater.|Entry at ~$1.3T plus fees means holders pay an "
    f"effective {B(v['entry_val'])}, {P(v['entry_prem'])} above the Series H.",
    "Recommendation:|tokenize post-IPO lock-up shares (or primary allocation) rather than pre-IPO secondaries; "
    "the pre-IPO window closes with the November roadshow.",
], 15)

# 2 Business snapshot
s = slide("Revenue grew ~12x year on year to a $68B run-rate, but Q3 growth slowed to 47% quarter on quarter",
          source="Anthropic S-1 (26-Oct-26) and amended S-1 (2-Nov-26) via CNBC/Reuters; CNBC 17-Aug-26; Fortune 4-Jun-26.")
s.shapes.add_picture(str(charts["quarters"]), Inches(0.6), Inches(1.6), width=Inches(6.6))
tiles = [("$17.0B", "Q3-26 revenue (Reported)"), (f"${v['rr_q3']:.0f}B", "Q3 run-rate, x4 (Estimated)"),
         ("~85%", "H1-26 gross margin; S-1 warns it won't last"), ("$895B", "Compute purchase + lease commitments"),
         ("48%", "Revenue via Amazon + Google marketplaces"), ("–$0.6B", "Q3-26 operating loss (Q2: +$1.0B)")]
for i, (bg, sm) in enumerate(tiles):
    tile(s, 7.5 + (i % 2) * 2.7, 1.7 + (i // 2) * 1.6, 2.55, 1.45, bg, sm)

# 3 Revenue and cost drivers
cov = v["dcf_summary"]["  Coverage of commitments due pre-2030"][1]
s = slide("Compute is the cost base: it absorbs ~60% of revenue in 2027 and still ~50% in 2036",
          source="Model 3c_DCF (base). Commitments: amended S-1; pre-2030 split from a single secondary source (Estimated).")
s.shapes.add_picture(str(charts["cost"]), Inches(0.6), Inches(1.5), width=Inches(6.9))
bullets(s, 7.8, 1.7, 5.0, 5.0, [
    "Revenue driver:|enterprise API + Claude Code; growth path decays from +75% (2027) at 0.72x per year.",
    "Inference compute|(cost of revenue) rises from 18% to 30% of revenue as pricing normalizes.",
    "Training + research compute|falls from 42% to 20% as revenue scales over fixed frontier-model runs.",
    f"Commitment check:|base-case compute 2027-29 covers only {P(cov)} of the ~$448B reportedly due before "
    "2030: either revenue must beat our base or capacity is stranded.",
], 14)

# 4 Valuation methods
a, m, d = v["anchor"], v["mult"], v["dcf"]
s = slide(f"Three methods put base-case value between {B(d[1])} and {B(m[1])}; the DCF is the most conservative",
          source="Model 3_Valuation, 3c_DCF. Equity value after 3% dilution; net cash $80B (Assumed).")
table(s, 0.6, 1.7, 12.1, [
    ["Method", "Bear", "Base", "Bull", "What drives it"],
    ["(a) Last-round anchor", B(a[0]), B(a[1]), B(a[2]), "Series H $965B + 0/40/100% of run-rate step-up since May"],
    ["(b) Forward NTM multiple", B(m[0]), B(m[1]), B(m[2]),
     f"NTM revenue ${v['ntm']:.0f}B x 9x / 13x / 17x (listed peers 3-9x, private labs 34-60x)"],
    ["(c) 10-year DCF", B(d[0]), B(d[1]), B(d[2]), "WACC 13/12/11%, g 2.5/3.0/3.5%, explicit compute lines"],
    ["Blended (30 / 30 / 40)", B(bear), B(base), B(bull), "DCF weighted highest: only method that prices compute"],
], col_w=[2.8, 1.3, 1.3, 1.3, 5.4], size=13, h_row=0.6)
text(s, 0.6, 5.6, 12.1, 1.0,
     f"Base blend implies {v['base_ev_ntm']:.1f}x EV / NTM revenue: in line with Microsoft today, for a company "
     f"growing ~{P(v['ntm_growth'])} over its current run-rate.", 15, NAVY)

# 5 Football field
s = slide("Fundamentals support ~$1.1T; secondary marks and IPO talk sit above our base case",
          source="Model 3_Valuation football field. Forge (Apr-26), Caplight (Jul-26), Nasdaq Private Market (Nov-26); WSJ (4-Nov-26).")
s.shapes.add_picture(str(charts["ff"]), Inches(0.9), Inches(1.6), width=Inches(11.3))

# 6 Scenarios
dsum = v["dcf_summary"]
s = slide("The range comes down to growth durability: 2036 revenue of $168B in the bear case vs $714B in the bull",
          source="Model 3c_DCF; 4_Sensitivity.")
s.shapes.add_picture(str(charts["scen"]), Inches(0.6), Inches(1.6), width=Inches(6.6))
table(s, 7.5, 1.8, 5.3, [
    ["", "Bear", "Base", "Bull"],
    ["2027 growth", "45%", "75%", "100%"],
    ["Rev CAGR 26-36", *[P(x) for x in dsum["Revenue CAGR FY26-36"]]],
    ["2036 EBIT margin", *[P(x[-1]) for x in v["dcf_rows"]["EBIT margin"]]],
    ["DCF equity", *[B(x) for x in d]],
    ["TV % of EV", *[P(x) for x in dsum["Terminal value as % of EV"]]],
    ["Blended value", B(bear), B(base), B(bull)],
], col_w=[1.9, 1.13, 1.13, 1.13], size=12, h_row=0.5)
text(s, 7.5, 5.6, 5.3, 1.2, "Bear = price war and share loss to OpenAI / Gemini; Bull = Claude becomes the default "
     "enterprise agent platform. A $1.55T IPO needs roughly bull-case growth.", 12, SLATE)

# 7 Why tokenize
prem = 1410 / 965 - 1
s = slide(f"Demand for AI exposure exceeds access: secondary marks ran {P(prem)} above the last primary round",
          source="Nasdaq Private Market (Nov-26), Series H (TechCrunch 28-May-26), employee tender (Apr-26), Pantera research.")
bullets(s, 0.6, 1.7, 7.4, 5.0, [
    "Scarce supply.|Employees under-sold into the $350B tender; Caplight calls Anthropic the most sought-after "
    "name the venture secondary market has seen.",
    "Access gap.|Primary rounds go to ~10 mega-funds and strategics; Gulf private-wealth and family offices "
    "get no direct allocation.",
    "Fractional + programmable.|$10 tokens vs $1M+ SPV minimums; on-chain cap table, automated transfer checks.",
    "But the window is short.|With the S-1 public and a roadshow from ~9-Nov, the durable product is a token over "
    "lock-up shares that converts to listed stock.",
], 15)
tile(s, 8.5, 1.8, 4.2, 1.5, "$0.97T → $1.41T", "Series H (May) to Nasdaq Private Market mark (Nov)")
tile(s, 8.5, 3.5, 4.2, 1.5, "20-40%", "Typical premium of pre-IPO tokens to NAV (Pantera)", ACCENT)
tile(s, 8.5, 5.2, 4.2, 1.5, "–38 to –46%", "One-day drop in pre-IPO tokens after company warnings", RED)

# 8 Structure diagram
s = slide("A ring-fenced ADGM SPV holds board-approved shares; each token is a pro-rata claim on its NAV",
          source="Illustrative structure. FSRA digital-securities regime; ADGM-supervised MTF for secondary trading.")


def box(x, y, w, h, title, sub, fill=LIGHT, color=NAVY):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = rgb(fill); shp.line.color.rgb = rgb(color)
    tf = shp.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = title; r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = rgb(color)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run(); r2.text = sub; r2.font.size = Pt(10); r2.font.color.rgb = rgb(SLATE)
    return shp


def arrow(x1, y1, x2, y2, label=None):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(SLATE); c.line.width = Pt(1.5)
    c.line._get_or_add_ln().append(
        __import__("lxml.etree", fromlist=["etree"]).fromstring(
            '<a:tailEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" type="triangle"/>'))
    if label:
        text(s, min(x1, x2) + 0.05, (y1 + y2) / 2 - 0.35, 2.6, 0.4, label, 10, GREY)


box(0.7, 1.9, 2.8, 1.3, "Token holders", "Professional / qualified investors, KYC'd, whitelisted wallets")
box(5.2, 1.9, 2.9, 1.3, "ADGM SPV", "Issues 10M tokens at $10; holds shares + cash reserve",
    fill="FFFFFF")
box(9.8, 1.9, 2.8, 1.3, "Anthropic PBC", f"SPV owns {v['own']*100:.4f}% via board-approved transfer")
box(0.7, 4.4, 2.8, 1.3, "ADGM MTF", "Secondary trading of tokens between whitelisted holders")
box(5.2, 4.4, 2.9, 1.3, "Regulated custodian", "Holds share certificates; daily register-to-token reconciliation")
box(9.8, 4.4, 2.8, 1.3, "Fund manager", "1.5% mgmt fee, 15% carry; NAV published from the model")
arrow(3.5, 2.55, 5.2, 2.55, "$100M subscription")
arrow(8.1, 2.55, 9.8, 2.55, "Purchase at ~$1.3T")
arrow(2.1, 3.2, 2.1, 4.4, "trade")
arrow(6.65, 3.2, 6.65, 4.4, "custody")
arrow(9.8, 5.05, 8.1, 5.05, "manages")
text(s, 0.7, 6.0, 12.0, 0.8, "Exit: at IPO + 180-day lock-up the SPV either distributes listed shares to holders or "
     "sells and redeems tokens at NAV. Token supply is fixed; no synthetic or forward-contract exposure.", 12, SLATE)

# 9 Token pricing
s = slide(f"At a $1.3T entry, the base-case token is worth ${tok['price_pre'][1]:.2f} against a $10 issue price",
          source="Model 5_Token. All discount and fee inputs Assumed (see 1_Assumptions).")
s.shapes.add_picture(str(charts["wf"]), Inches(0.6), Inches(1.6), width=Inches(6.9))
table(s, 7.8, 1.8, 5.0, [
    ["$ / token", "Bear", "Base", "Bull", "IPO mid"],
    ["Gross NAV", *[f"{x:.2f}" for x in tok["nav"]]],
    ["Pre-IPO price", *[f"{x:.2f}" for x in tok["price_pre"]]],
    ["Post-IPO (lock-up)", *[f"{x:.2f}" for x in tok["price_post"]]],
    ["Discount to NAV", *[P(x) for x in tok["disc_pre"]]],
], col_w=[1.6, 0.85, 0.85, 0.85, 0.85], size=11, h_row=0.48)
text(s, 7.8, 4.5, 5.0, 2.2, [
    f"Layered discounts take ~{P(tok['disc_pre'][1])} off NAV pre-IPO.",
    f"Break-even Anthropic value: {B(v['be_pre'])} pre-IPO, {B(v['be_post'])} once listed and in lock-up.",
    "Fix: buy closer to fair value, cut fees, or launch post-IPO when transfer risk falls away."], 13, NAVY)

# 10 Regulatory path
s = slide("Tokens over unlisted shares are securities: the path runs through ADGM FSRA or DIFC DFSA, not VARA",
          source="zamanathq.com, blockhertz.com, neolegal.ae (2026 summaries; verify against FSRA / DFSA rulebooks).")
steps = [("1. Choose the perimeter", "Tokenized securities: FSRA (ADGM) or DFSA (DIFC); mainland CMA. VARA covers "
          "virtual assets, not security tokens."),
         ("2. Licence and vehicle", "ADGM SPV or DIFC QIF / Exempt Fund; manager with FSRA/DFSA licence; "
          "QIF min. subscription $500k, Exempt Fund $50k."),
         ("3. Eligibility", "Professional Clients only; VARA-style qualified test is AED 3.5M net assets or "
          "AED 700k income. Whitelisted wallets."),
         ("4. Issuer consent", "Board-approved transfer + ROFR waiver from Anthropic before closing; without it the "
          "transfer is void."),
         ("5. Trading and exit", "Admission to ADGM-supervised MTF; bilateral whitelist transfers; distribute or "
          "redeem at lock-up expiry.")]
for i, (h, b_) in enumerate(steps):
    x = 0.6 + i * 2.5
    box_ = s.shapes.add_shape(MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON, Inches(x), Inches(1.9),
                              Inches(2.4), Inches(0.8))
    box_.fill.solid(); box_.fill.fore_color.rgb = rgb(NAVY if i != 3 else ACCENT); box_.line.fill.background()
    tf = box_.text_frame; tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    r = tf.paragraphs[0].add_run(); r.text = h; r.font.size = Pt(11); r.font.bold = True
    r.font.color.rgb = rgb("FFFFFF")
    text(s, x + 0.05, 2.9, 2.3, 3.0, b_, 12, SLATE)
text(s, 0.6, 5.8, 12.1, 0.8, "Step 4 is the gating item: regulators can licence the token, but only Anthropic's "
     "board can make the underlying transfer valid.", 15, NAVY, True)

# 11 Risks
s = slide("Transfer restrictions, not price volatility, are the risk that can take the token to zero",
          source="Model 6_Risks; Anthropic May-26 notice on unauthorized transfers (as reported).")
table(s, 0.6, 1.7, 12.1, [
    ["Risk", "Likelihood", "Impact", "Response"],
    ["Void transfer / ROFR", "High", "Severe", "Issuer consent letter; escrow until ROFR lapses"],
    ["Entry above fair value", "High", "High", f"Entry {B(v['entry_val'])} effective vs {B(base)} base fair value"],
    ["NAV vs token price gap", "High", "High", "Daily NAV; cap premium at issue; disclose break-even"],
    ["Liquidity (single MTF)", "High", "Medium", "Market-maker; redemption at lock-up expiry"],
    ["Custody mismatch", "Medium", "High", "Regulated custodian; register-to-ledger reconciliation"],
    ["Wrong regulator / eligibility", "Medium", "Severe", "FSRA / DFSA perimeter; Professional Clients only"],
    ["Growth deceleration vs $895B commitments", "Medium", "Severe", "Bear case shown; satellite sizing"],
], col_w=[3.6, 1.4, 1.3, 5.8], size=12, h_row=0.55)

# 12 Sources
s = slide("Sources: every figure is tagged Reported, Estimated or Assumed in the model")
src = [
    "Anthropic PBC Form S-1, SEC EDGAR CIK 0002130357 (26-Oct-26); amended S-1 (2-Nov-26) via CNBC / Reuters.",
    "TechCrunch (28-May-26) and Orrick: Series H $65B at $965B post-money.  CNBC (12-Feb-26): Series G $30B at $380B.",
    "CNBC (17-Aug-26): $65B run-rate end-Jul; $47B in May.  Motley Fool (31-Oct-26), Tomasz Tunguz: S-1 margins.",
    "Microsoft / Nvidia blogs (18-Nov-25): $30B Azure commitment; up to $10B / $5B investment. CNBC (23-Oct-25): 1M TPUs.",
    "Decrypt / Quartz (Apr-26, Forge ~$1T); Yahoo Finance (Jul-26, Caplight $1.2T); Nasdaq Private Market $1.41T (Nov-26).",
    "WSJ via graniteshares / shattered.io (Nov-26): IPO talk $1.5-2.0T, investors advise $1.5-1.6T.",
    "multiples.vc (Oct / Nov-26) listed EV / revenue; tech-insider.org (OpenAI $852B); autobound / gradually.ai (Mistral).",
    "Fortune (4-Jun-26), leverageshares: Google ~14% stake, Amazon 12-21%, 48% of revenue via marketplaces.",
    "zamanathq.com, blockhertz.com, neolegal.ae: FSRA / DFSA / VARA tokenized-securities summaries (2026).",
    "Pantera Capital, CoinMarketCap Academy: pre-IPO token premiums and void-transfer warnings.",
    "Caveat: many S-1 figures come from secondary coverage, not the filing itself. Re-verify on EDGAR before use.",
]
text(s, 0.6, 1.5, 12.1, 5.3, src, 12, SLATE)

path = OUT / "Anthropic_Pitch_Deck.pptx"
prs.save(path)
print("saved", path, "slides:", len(prs.slides))
