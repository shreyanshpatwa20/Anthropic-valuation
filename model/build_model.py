"""Build the Anthropic valuation + tokenized pre-IPO vehicle model (openpyxl, live formulas).

Every number typed into the workbook is an input (blue font) with a source, date and
confidence tag. Every output is an Excel formula. Run:  python model/build_model.py
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.chart.series import SeriesLabel
from openpyxl.utils import get_column_letter as L

OUT = Path(__file__).resolve().parents[1] / "output" / "Anthropic_Valuation_Model.xlsx"

BLUE = Font(name="Calibri", size=10, color="0000FF")
BLACK = Font(name="Calibri", size=10, color="000000")
BOLD = Font(name="Calibri", size=10, bold=True)
HDR = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
TITLE = Font(name="Calibri", size=14, bold=True, color="1F2A44")
NOTE = Font(name="Calibri", size=9, italic=True, color="666666")
HDR_FILL = PatternFill("solid", fgColor="1F2A44")
SEC_FILL = PatternFill("solid", fgColor="E8ECF4")
OUT_FILL = PatternFill("solid", fgColor="FFF4D6")
THIN = Border(bottom=Side(style="thin", color="BBBBBB"))
WRAP = Alignment(wrap_text=True, vertical="top")

USD_B = '#,##0.0;[Red](#,##0.0)'
USD_0 = '#,##0;[Red](#,##0)'
PCT = '0.0%;[Red]-0.0%'
MULT = '0.0"x"'
USD_TOK = '$#,##0.00;[Red]($#,##0.00)'

wb = Workbook()
REF = {}  # key -> {"one": addr} or {"bear":..,"base":..,"bull":..}
SCEN = ["bear", "base", "bull"]
SCOL = {"bear": "C", "base": "D", "bull": "E"}


def setw(ws, widths):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def header(ws, row, labels, start_col=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font, c.fill = HDR, HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def section(ws, row, text, ncols=10):
    for col in range(1, ncols + 1):
        ws.cell(row=row, column=col).fill = SEC_FILL
    ws.cell(row=row, column=1, value=text).font = BOLD


def put(ws, addr, value, fmt=None, font=BLACK, fill=None):
    c = ws[addr]
    c.value = value
    c.font = font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    return c


# =============================================================================
# 1. ASSUMPTIONS
# =============================================================================
A = wb.active
A.title = "1_Assumptions"
A["A1"] = "1. Assumptions: every input, with source, date and confidence"
A["A1"].font = TITLE
A["A2"] = ("Blue = typed input. Black = formula. Units: $B unless stated. Confidence: Reported = disclosed by "
           "company/filing or reported by a named outlet; Estimated = derived or single secondary source; "
           "Assumed = analyst judgement (no source exists).")
A["A2"].font = NOTE
header(A, 4, ["Key", "Input", "Value / Bear", "Base", "Bull", "Unit", "Source", "Source date", "Confidence", "Note"])
setw(A, {"A": 16, "B": 46, "C": 12, "D": 10, "E": 10, "F": 9, "G": 52, "H": 12, "I": 11, "J": 50})
A.freeze_panes = "C5"
arow = [5]


def sec(text):
    section(A, arow[0], text)
    arow[0] += 1


def inp(key, desc, vals, unit, src, sdate, conf, note="", fmt=USD_B):
    r = arow[0]
    A.cell(row=r, column=1, value=key).font = NOTE
    A.cell(row=r, column=2, value=desc).font = BLACK
    if isinstance(vals, (list, tuple)):
        REF[key] = {}
        for s, v in zip(SCEN, vals):
            put(A, f"{SCOL[s]}{r}", v, fmt, BLUE)
            REF[key][s] = f"'1_Assumptions'!${SCOL[s]}${r}"
    else:
        put(A, f"C{r}", vals, fmt, BLUE)
        REF[key] = {"one": f"'1_Assumptions'!$C${r}"}
        wb.defined_names[key] = DefinedName(key, attr_text=f"'1_Assumptions'!$C${r}")
    for col, v in zip("FGHIJ", [unit, src, sdate, conf, note]):
        c = A[f"{col}{r}"]
        c.value = v
        c.font = BLACK if col != "J" else NOTE
        c.alignment = WRAP
    arow[0] += 1


def R(key, s=None):
    d = REF[key]
    return d["one"] if "one" in d else d[s]


S_TC = "TechCrunch 28-May-26; Orrick deal note 'Anthropic Raises $65B Series H at $965B Post-Money'"
S_CNBC_G = "CNBC 12-Feb-26 'Anthropic closes $30B round at $380B valuation'"
S_S1 = "Anthropic PBC Form S-1 (SEC EDGAR CIK 0002130357), via Tunguz / Motley Fool S-1 coverage"
S_S1A = "Amended S-1 filed 2-Nov-26, as reported by CNBC/Reuters (via trendingtopics.eu, mlq.ai)"

sec("Valuation date")
inp("val_date", "Valuation date", date(2026, 11, 6), "date", "Analyst", "2026-11-06", "Assumed",
    "Today. Drives time adjustment and DCF stub period.", fmt="dd-mmm-yy")

sec("Primary rounds, tender and secondary marks")
inp("seriesH_post", "Series H post-money valuation", 965, "$B", S_TC, "2026-05-28", "Reported",
    "Led by Altimeter, Dragoneer, Greenoaks, Sequoia.")
inp("seriesH_raise", "Series H amount raised", 65, "$B", S_TC, "2026-05-28", "Reported")
inp("seriesH_date", "Series H announcement date", date(2026, 5, 28), "date", S_TC, "2026-05-28", "Reported",
    fmt="dd-mmm-yy")
inp("seriesG_post", "Series G post-money valuation", 380, "$B", S_CNBC_G, "2026-02-12", "Reported",
    "$30B, led by Coatue and GIC; Microsoft and Nvidia participated.")
inp("seriesF_post", "Series F post-money valuation", 183, "$B", "Sacra / intellizence funding history", "2025-09",
    "Reported", "Aggregator source.")
inp("seriesE_post", "Series E post-money valuation", 61.5, "$B", "Sacra / intellizence funding history", "2025-03",
    "Reported", "Aggregator source.")
inp("tender_pre", "Employee tender offer (pre-money)", 350, "$B", "tech-insider.org; augment.market", "2026-04",
    "Reported", "Tender undersubscribed by sellers: employees preferred to wait for IPO.")
inp("sec_forge", "Secondary mark: Forge Global implied valuation", 1000, "$B",
    "Decrypt / Quartz / Yahoo Finance citing Forge CEO", "2026-04-23", "Reported", "Thin trading.")
inp("sec_caplight", "Secondary mark: Caplight implied valuation", 1200, "$B", "Yahoo Finance citing Caplight",
    "2026-07-09", "Reported", "Closings described as rare.")
inp("sec_npm", "Secondary mark: Nasdaq Private Market", 1410, "$B", "Secondary reports citing Nasdaq Private Market",
    "2026-11", "Reported", "Most recent private mark found.")
inp("ipo_low", "IPO valuation talk: low", 1500, "$B", "WSJ via graniteshares / shattered.io", "2026-11-04",
    "Reported", "Not a filed price range; no range on EDGAR as of 5-Nov-26.")
inp("ipo_mid", "IPO valuation: investor-advised midpoint", 1550, "$B",
    "WSJ: institutions advise $1.5-1.6T", "2026-11-04", "Reported")
inp("ipo_high", "IPO valuation talk: high", 2000, "$B", "Bloomberg/WSJ via financefeeds.com", "2026-10",
    "Reported", "Earlier target, since walked back.")

sec("Revenue and operating results")
inp("rr_may", "Annualized run-rate revenue, May-26 (at Series H)", 47, "$B",
    "CNBC 17-Aug-26 (Bloomberg first reported)", "2026-05", "Reported")
inp("rr_jul", "Annualized run-rate revenue, end Jul-26", 65, "$B", "CNBC 17-Aug-26", "2026-07-31", "Reported",
    "Cross-check only; model uses Q3 actual x4.")
inp("rev_fy25", "FY2025 revenue", 4.6, "$B", "valueaddvc.com (citing S-1)", "2026-10", "Estimated",
    "Secondary source.")
inp("rev_h1_26", "H1 2026 revenue", 16.3, "$B", S_S1, "2026-10-26", "Reported")
inp("rev_q2_26", "Q2 2026 revenue", 11.555, "$B", S_S1, "2026-10-26", "Reported", "+144% QoQ.")
inp("rev_q3_26", "Q3 2026 revenue", 16.962, "$B", S_S1A, "2026-11-02", "Reported", "+47% QoQ: sharp deceleration.")
inp("cor_h1_26", "H1 2026 cost of revenue (customer-serving compute)", 2.4, "$B", S_S1 + "; Motley Fool 31-Oct-26",
    "2026-10-26", "Reported", "Implies ~85% gross margin. S-1 warns it will not last; marketplace revenue booked gross.")
inp("opinc_q2", "Q2 2026 operating income", 0.974, "$B", S_S1A, "2026-11-02", "Reported")
inp("opinc_q3", "Q3 2026 operating income", -0.567, "$B", S_S1A, "2026-11-02", "Reported",
    "Opex rose to $17.5B from $10.6B QoQ.")
inp("netloss_q3", "Q3 2026 net loss (incl. $21.9B non-cash fair-value loss)", -23.29, "$B", S_S1A, "2026-11-02",
    "Reported", "Not used in valuation: non-cash, driven by valuation step-up.")
inp("mkt_share", "Share of revenue via Amazon + Google cloud marketplaces (H1-26)", 0.48, "%",
    "Fortune 4-Jun-26 / S-1 via leverageshares", "2026-10", "Reported", "Channel concentration.", fmt=PCT)
inp("headcount", "Headcount", 5300, "people", "S-1 (via public S-1 commentary)", "2026-10", "Reported", fmt=USD_0)

sec("Compute commitments and strategic investors")
inp("commit_total", "Total purchase and lease commitments (substantially all compute)", 895.4, "$B", S_S1A,
    "2026-11-02", "Reported")
inp("commit_pre2030", "Commitments due before 2030", 447.5, "$B", "datastudios.org (single source)", "2026-11",
    "Estimated", "Could not corroborate; used for coverage check only.")
inp("msft_azure", "Azure compute purchase commitment", 30, "$B", "Microsoft blog 18-Nov-25", "2025-11-18", "Reported",
    "Plus up to 1 GW of Nvidia Grace Blackwell / Vera Rubin capacity.")
inp("nvda_inv", "Nvidia investment commitment (up to)", 10, "$B", "Microsoft / Nvidia blogs 18-Nov-25", "2025-11-18",
    "Reported")
inp("msft_inv", "Microsoft investment commitment (up to)", 5, "$B", "Microsoft blog 18-Nov-25", "2025-11-18", "Reported")
inp("goog_commit", "Google investment commitment for 2026 (up to)", 40, "$B", "catenaa.com; Fortune", "2026",
    "Reported", "Google also supplies up to 1M TPUs (CNBC 23-Oct-25); Broadcom multi-GW TPU deal from 2027.")
inp("goog_stake", "Google ownership", 0.14, "%", "Court documents; S-1 cap 14.99% (via officechai/leverageshares)",
    "2026", "Reported", fmt=PCT)
inp("amzn_stake", "Amazon ownership (midpoint of 12-21% range)", 0.15, "%", "leverageshares; plus500", "2026",
    "Estimated", "Sources disagree; S-1 reportedly caps at 12%.", fmt=PCT)

sec("Balance sheet and capital structure (gaps: not found in sources)")
inp("net_cash", "Net cash at valuation date", 80, "$B", "Analyst", "2026-11-06", "Assumed",
    "GAP. Raised $95B in Series G+H during 2026; Q3 reported near cash-flow breakeven. Verify in S-1 balance sheet.")
inp("dilution", "Dilution to existing holders (option refresh, IPO grants)", 0.03, "%", "Analyst", "2026-11-06",
    "Assumed", "Primary IPO proceeds at fair value are value-neutral, so only comp dilution is deducted.", fmt=PCT)

sec("Near-term revenue path (quarterly QoQ growth)")
inp("g_q4_26", "Q4 2026 QoQ growth", 0.25, "%", "Analyst", "2026-11-06", "Assumed",
    "Q1 +132%, Q2 +144%, Q3 +47%: continue deceleration.", fmt=PCT)
inp("g_q1_27", "Q1 2027 QoQ growth", 0.18, "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("g_q2_27", "Q2 2027 QoQ growth", 0.14, "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("g_q3_27", "Q3 2027 QoQ growth", 0.11, "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)

sec("Scenario drivers (Bear | Base | Bull)")
inp("anchor_capture", "(a) Share of post-round run-rate step-up a buyer pays for", [0.0, 0.4, 1.0], "%", "Analyst",
    "2026-11-06", "Assumed", "0% = Series H price unchanged; 100% = Series H multiple re-applied to Q3 run-rate.",
    fmt=PCT)
inp("ntm_mult", "(b) EV / NTM revenue multiple", [9, 13, 17], "x", "Analyst, framed by 2_Comps", "2026-11-06",
    "Assumed", "Bear = Microsoft-like 9.4x; Bull = halfway to private frontier run-rate multiples.", fmt=MULT)
inp("rev_g1", "(c) 2027 revenue growth", [0.45, 0.75, 1.00], "%", "Analyst", "2026-11-06", "Assumed",
    "Base ~= NTM build. Bear = price war / share loss.", fmt=PCT)
inp("g_decay", "(c) Annual growth decay factor (g_t = g_1 x decay^(t-1))", [0.65, 0.72, 0.70], "x", "Analyst",
    "2026-11-06", "Assumed", fmt='0.00')
inp("inf_start", "(c) Inference compute (cost of revenue), % rev, 2027", [0.25, 0.18, 0.15], "%",
    "Anchored on H1-26 actual (~15%)", "2026-11-06", "Assumed", fmt=PCT)
inp("inf_end", "(c) Inference compute, % rev, 2036", [0.40, 0.30, 0.25], "%", "Analyst", "2026-11-06", "Assumed",
    "Pricing pressure + net revenue accounting push COGS up.", fmt=PCT)
inp("trn_start", "(c) Training + research compute, % rev, 2027", [0.50, 0.42, 0.38], "%", "Analyst", "2026-11-06",
    "Assumed", "Q3-26 opex $17.5B on $17.0B revenue implies very high non-COGS compute.", fmt=PCT)
inp("trn_end", "(c) Training + research compute, % rev, 2036", [0.25, 0.20, 0.15], "%", "Analyst", "2026-11-06",
    "Assumed", fmt=PCT)
inp("opx_start", "(c) Other opex (people, S&M, G&A), % rev, 2027", [0.32, 0.28, 0.26], "%", "Analyst",
    "2026-11-06", "Assumed", fmt=PCT)
inp("opx_end", "(c) Other opex, % rev, 2036", [0.20, 0.18, 0.15], "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("capex", "(c) Owned capex, % rev (= D&A; compute mostly leased)", [0.04, 0.03, 0.03], "%", "Analyst",
    "2026-11-06", "Assumed", fmt=PCT)
inp("wacc", "(c) WACC", [0.13, 0.12, 0.11], "%", "Analyst (high-beta mega-cap tech + execution premium)",
    "2026-11-06", "Assumed", fmt=PCT)
inp("tg", "(c) Terminal growth", [0.025, 0.03, 0.035], "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("tax", "(c) Cash tax rate on positive EBIT", 0.21, "%", "US federal statutory rate", "2026", "Reported",
    "Ignores NOLs (conservative).", fmt=PCT)
inp("w_anchor", "Blend weight: (a) last-round anchor", 0.30, "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("w_mult", "Blend weight: (b) forward multiple", 0.30, "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("w_dcf", "Blend weight: (c) DCF", 0.40, "%", "Analyst", "2026-11-06", "Assumed", fmt=PCT)

sec("Token vehicle (SPV) terms")
inp("spv_raise", "SPV capital raised from token holders", 100, "$M", "Analyst (illustrative)", "2026-11-06",
    "Assumed", fmt=USD_0)
inp("tok_issue", "Token issue price", 10, "$/token", "Analyst", "2026-11-06", "Assumed", fmt=USD_TOK)
inp("fee_upfront", "Upfront structuring / placement fee", 0.02, "% raise", "Analyst; typical SPV 1-3%",
    "2026-11-06", "Assumed", fmt=PCT)
inp("reserve", "Expense reserve held in cash", 0.02, "% raise", "Analyst", "2026-11-06", "Assumed", fmt=PCT)
inp("broker_fee", "Secondary broker commission on purchase", 0.03, "% purchase", "Analyst; typical 2-5%",
    "2026-11-06", "Assumed", fmt=PCT)
inp("purchase_val", "Secondary purchase valuation paid by SPV", 1300, "$B",
    "Analyst: between Caplight $1.2T and Nasdaq Private Market $1.41T", "2026-11-06", "Assumed")
inp("mgmt_fee", "Management fee", 0.015, "%/yr", "Analyst; typical SPV 0-2%", "2026-11-06", "Assumed", fmt=PCT)
inp("carry", "Carried interest on gains (no hurdle)", 0.15, "%", "Analyst; typical SPV 10-20%", "2026-11-06",
    "Assumed", fmt=PCT)
inp("hold_yrs", "Holding period to lock-up expiry", 1.0, "yrs", "Analyst: IPO late-Nov-26 + 180-day lock-up + slip",
    "2026-11-06", "Assumed", fmt='0.00')
inp("dlom_pre", "Discount for lack of marketability, pre-IPO", 0.15, "%", "Analyst; restricted-stock studies 10-30%",
    "2026-11-06", "Assumed", fmt=PCT)
inp("dlom_post", "Discount for lack of marketability, post-IPO in lock-up", 0.07, "%", "Analyst", "2026-11-06",
    "Assumed", fmt=PCT)
inp("xfer_disc", "Secondary / transfer-risk discount (ROFR, void-transfer risk)", 0.10, "%",
    "Analyst; Anthropic May-26 notice: unapproved transfers void", "2026-11-06", "Assumed", fmt=PCT)

# =============================================================================
# 2. COMPS
# =============================================================================
C = wb.create_sheet("2_Comps")
C["A1"] = "2. Comparable companies: frontier-AI privates and listed AI / cloud names"
C["A1"].font = TITLE
C["A2"] = ("Listed: EV / NTM revenue. Private: post-money / run-rate revenue at round date. Blue = input. "
           "Growth rates for listed names are Assumed (sourced multiples did not carry growth).")
C["A2"].font = NOTE
header(C, 4, ["Company", "Type", "EV / post-money ($B)", "Revenue basis ($B)", "EV / Revenue", "Revenue growth",
              "Growth-adj. multiple", "Include?", "Why in peer set (one line)", "Source", "Date", "Confidence"])
setw(C, {"A": 18, "B": 12, "C": 12, "D": 12, "E": 10, "F": 10, "G": 11, "H": 8, "I": 56, "J": 42, "K": 10, "L": 22})
comps = [
    # name, type, EV, rev basis (None -> derive from multiple), mult(if given), growth, include, why, src, date, conf
    ("OpenAI", "Private", 852, 25, None, 1.00, "Y",
     "Closest peer: same product, same buyers, same compute constraint.",
     "tech-insider.org; luminix fact sheet (Mar-26 round, ~$25B ARR)", "2026-03-31", "Reported EV / Est. rev & growth"),
    ("Mistral AI", "Private", 24, 0.4, None, 1.50, "Y",
     "Independent frontier lab; shows private multiple for sub-scale labs.",
     "multiples.vc / autobound (Series D); gradually.ai ($400M ARR)", "2026-09", "Estimated"),
    ("xAI (last standalone)", "Private", 230, 0.5, None, None, "N",
     "Excluded: revenue too small for a meaningful multiple; now inside SpaceX.",
     "valueaddvc.com (Series E, Jan-26)", "2026-01", "Estimated"),
    ("Nvidia", "Listed", 4400, None, 7.0, 0.40, "Y",
     "Captures AI-infrastructure profit pool; Anthropic's key supplier.",
     "multiples.vc 'Public AI Valuation Multiples - Oct 2026'", "2026-10", "Reported mult / Assumed growth"),
    ("Microsoft", "Listed", 4000, None, 9.4, 0.15, "Y",
     "Enterprise AI distribution + Azure; partner and investor.",
     "multiples.vc Oct-26", "2026-10", "Reported mult / Assumed growth"),
    ("Alphabet", "Listed", 3400, None, 5.5, 0.14, "Y",
     "Owns Gemini (direct competitor) and TPUs; ~14% Anthropic holder.",
     "multiples.vc Oct-26", "2026-10", "Reported mult / Assumed growth"),
    ("CoreWeave", "Listed", 70.1, None, 2.9, 0.80, "Y",
     "Pure-play AI compute: shows how the market prices capex-heavy AI growth.",
     "multiples.vc Oct-26 (Nov-26 page conflicts: 6.6x on $28B)", "2026-10", "Reported mult / Assumed growth"),
    ("Palantir", "Listed", 429, None, 56.9, 0.50, "N",
     "Excluded from median: trailing basis and an outlier; shows ceiling for AI-software sentiment.",
     "multiples.vc Nov-26 (trailing)", "2026-11", "Reported mult / Assumed growth"),
]
first = 5
for i, (nm, typ, ev, rev, mult, g, inc, why, src, dt, conf) in enumerate(comps):
    r = first + i
    C[f"A{r}"], C[f"B{r}"] = nm, typ
    put(C, f"C{r}", ev, USD_B, BLUE)
    if rev is not None:
        put(C, f"D{r}", rev, USD_B, BLUE)
        put(C, f"E{r}", f"=C{r}/D{r}", MULT)
    else:
        put(C, f"E{r}", mult, MULT, BLUE)
        put(C, f"D{r}", f"=C{r}/E{r}", USD_B)
    if g is not None:
        put(C, f"F{r}", g, PCT, BLUE)
        put(C, f"G{r}", f"=E{r}/(F{r}*100)", '0.00')
    else:
        C[f"F{r}"] = "n/a"
        C[f"G{r}"] = "n/a"
    put(C, f"H{r}", inc, None, BLUE)
    for col, v in zip("IJKL", [why, src, dt, conf]):
        C[f"{col}{r}"] = v
        C[f"{col}{r}"].alignment = WRAP
last = first + len(comps) - 1
r = last + 1
C[f"A{r}"] = "Oracle"; C[f"B{r}"] = "Listed"; C[f"C{r}"] = "n/a"; C[f"E{r}"] = "n/a"
put(C, f"D{r}", 67.4, USD_B, BLUE)
put(C, f"F{r}", "=90/D{0}-1".format(r), PCT)
C[f"H{r}"] = "N"
C[f"I{r}"] = "Reference only: OCI is the fastest-growing AI cloud (+77% IaaS) but no sourced EV found."
C[f"J{r}"] = "Oracle FY26 results; FY27 revenue guide $90B (lambdafin / Zacks)"; C[f"K{r}"] = "2026"
C[f"L{r}"] = "Reported"
oracle_row = r
r += 1
C[f"A{r}"] = "Anthropic @ Series H"; C[f"B{r}"] = "Subject"
put(C, f"C{r}", f"={R('seriesH_post')}", USD_B); put(C, f"D{r}", f"={R('rr_may')}", USD_B)
put(C, f"E{r}", f"=C{r}/D{r}", MULT)
C[f"I{r}"] = "Subject company: primary-round multiple of run-rate."
anth_h = r
r += 1
C[f"A{r}"] = "Anthropic @ NPM mark"; C[f"B{r}"] = "Subject"
put(C, f"C{r}", f"={R('sec_npm')}", USD_B); put(C, f"D{r}", "='3_Valuation'!C12", USD_B)
put(C, f"E{r}", f"=C{r}/D{r}", MULT)
C[f"I{r}"] = "Subject company: latest secondary mark on Q3-26 run-rate."
anth_n = r
r += 2
stats_r = r
section(C, r, "Peer statistics (included names only)", 12)
lst = f"$B${first}:$B${last}"; inc = f"$H${first}:$H${last}"; ev_m = f"$E${first}:$E${last}"
ga = f"$G${first}:$G${last}"
rows = [
    ("Listed median EV / NTM revenue", f'=MEDIAN(IF(({lst}="Listed")*({inc}="Y"),{ev_m}))', MULT),
    ("Listed max EV / NTM revenue", f'=MAX(IF(({lst}="Listed")*({inc}="Y"),{ev_m}))', MULT),
    ("Private median post-money / run-rate", f'=MEDIAN(IF(({lst}="Private")*({inc}="Y"),{ev_m}))', MULT),
    ("Listed median growth-adjusted multiple", f'=MEDIAN(IF(({lst}="Listed")*({inc}="Y"),{ga}))', '0.00'),
    ("Anthropic NTM growth (vs Q3-26 run-rate)", "='3_Valuation'!C14", PCT),
    ("Growth-adjusted implied multiple for Anthropic", f"=C{r+4}*C{r+5}*100", MULT),
]
for j, (lab, f, fmt) in enumerate(rows, start=1):
    C[f"A{r+j}"] = lab
    if f.startswith("=MEDIAN(IF") or f.startswith("=MAX(IF"):
        C[f"C{r+j}"] = ArrayFormula(f"C{r+j}", f)
    else:
        C[f"C{r+j}"] = f
    C[f"C{r+j}"].number_format = fmt
    C[f"C{r+j}"].fill = OUT_FILL
C[f"A{r+8}"] = ("Read-across: listed peers trade at 3-9x NTM; private frontier labs at 20-60x run-rate. The selected "
                "9x / 13x / 17x range sits between them because Anthropic's growth is private-like but its scale "
                "and S-1 disclosure are public-like.")
C[f"A{r+8}"].font = NOTE
COMPS_STATS = {"listed_med": f"'2_Comps'!$C${r+1}", "listed_max": f"'2_Comps'!$C${r+2}",
               "priv_med": f"'2_Comps'!$C${r+3}", "ga_implied": f"'2_Comps'!$C${r+6}"}

# =============================================================================
# 3. VALUATION (revenue build, anchor, multiple, blend, football field)
# =============================================================================
V = wb.create_sheet("3_Valuation")
V["A1"] = "3. Valuation: three methods and football field ($B equity value)"
V["A1"].font = TITLE
setw(V, {"A": 4, "B": 50, "C": 13, "D": 13, "E": 13, "F": 13, "G": 13, "H": 13, "I": 13, "J": 40})
section(V, 3, "Revenue build ($B)", 10)
header(V, 4, ["", "", "Q1-26A", "Q2-26A", "Q3-26A", "Q4-26E", "Q1-27E", "Q2-27E", "Q3-27E"])
V["B5"] = "QoQ growth"
V["B6"] = "Quarterly revenue"
put(V, "C6", f"={R('rev_h1_26')}-{R('rev_q2_26')}", USD_B)
put(V, "D6", f"={R('rev_q2_26')}", USD_B)
put(V, "E6", f"={R('rev_q3_26')}", USD_B)
put(V, "D5", "=D6/C6-1", PCT)
put(V, "E5", "=E6/D6-1", PCT)
for col, key in zip("FGHI", ["g_q4_26", "g_q1_27", "g_q2_27", "g_q3_27"]):
    put(V, f"{col}5", f"={R(key)}", PCT)
    prev = chr(ord(col) - 1)
    put(V, f"{col}6", f"={prev}6*(1+{col}5)", USD_B)
V["J6"] = "Q1 derived = H1 - Q2 (Estimated)."
V["J6"].font = NOTE
V["B8"] = "9M-26 revenue (check vs S-1 $33.242B)"; put(V, "C8", "=SUM(C6:E6)", USD_B)
V["B9"] = "FY2026E revenue"; put(V, "C9", "=SUM(C6:F6)", USD_B, fill=OUT_FILL)
V["B10"] = "FY2026E growth vs FY2025"; put(V, "C10", f"=C9/{R('rev_fy25')}-1", PCT)
V["B11"] = "NTM revenue (Q4-26 to Q3-27)"; put(V, "C11", "=SUM(F6:I6)", USD_B, fill=OUT_FILL)
V["B12"] = "Q3-26 annualized run-rate"; put(V, "C12", "=E6*4", USD_B)
V["B13"] = "Cross-check: reported Jul-26 run-rate"; put(V, "C13", f"={R('rr_jul')}", USD_B)
V["B14"] = "NTM growth vs Q3-26 run-rate"; put(V, "C14", "=C11/C12-1", PCT)

section(V, 16, "(a) Last-round anchor, adjusted for time and dilution", 10)
header(V, 17, ["", "", "Bear", "Base", "Bull"])
anchor_rows = [
    ("Series H post-money", lambda s: f"={R('seriesH_post')}", USD_B),
    ("Run-rate revenue at round", lambda s: f"={R('rr_may')}", USD_B),
    ("Implied post-money / run-rate", lambda s: f"={{c}}18/{{c}}19", MULT),
    ("Q3-26 run-rate (now)", lambda s: "=$C$12", USD_B),
    ("Run-rate step-up since round", lambda s: f"={{c}}21/{{c}}19-1", PCT),
    ("Share of step-up captured", lambda s: f"={R('anchor_capture', s)}", PCT),
    ("Months elapsed since round", lambda s: f"=({R('val_date')}-{R('seriesH_date')})/30.4", '0.0'),
    ("Time-adjusted value", lambda s: f"={{c}}18*(1+{{c}}22*{{c}}23)", USD_B),
    ("Less: dilution", lambda s: f"=-{{c}}25*{R('dilution')}", USD_B),
    ("(a) Equity value, existing holders", lambda s: f"={{c}}25+{{c}}26", USD_B),
]
for j, (lab, fn, fmt) in enumerate(anchor_rows):
    r = 18 + j
    V[f"B{r}"] = lab
    for s in SCEN:
        c = SCOL[s]
        put(V, f"{c}{r}", fn(s).replace("{c}", c), fmt, fill=OUT_FILL if r == 27 else None)
V["J25"] = "Value = post x (1 + capture x step-up). Time captured via run-rate growth, not a hurdle rate."
V["J25"].font = NOTE

section(V, 29, "(b) Forward revenue multiple from comps", 10)
header(V, 30, ["", "", "Bear", "Base", "Bull"])
mult_rows = [
    ("NTM revenue", lambda s: "=$C$11", USD_B),
    ("EV / NTM revenue multiple", lambda s: f"={R('ntm_mult', s)}", MULT),
    ("Enterprise value", lambda s: "={c}31*{c}32", USD_B),
    ("Plus: net cash", lambda s: f"={R('net_cash')}", USD_B),
    ("Less: dilution", lambda s: f"=-({{c}}33+{{c}}34)*{R('dilution')}", USD_B),
    ("(b) Equity value", lambda s: "={c}33+{c}34+{c}35", USD_B),
]
for j, (lab, fn, fmt) in enumerate(mult_rows):
    r = 31 + j
    V[f"B{r}"] = lab
    for s in SCEN:
        c = SCOL[s]
        put(V, f"{c}{r}", fn(s).replace("{c}", c), fmt, fill=OUT_FILL if r == 36 else None)
V["B37"] = "Comps cross-check: listed median / max / private median multiple"
put(V, "C37", f"={COMPS_STATS['listed_med']}", MULT)
put(V, "D37", f"={COMPS_STATS['listed_max']}", MULT)
put(V, "E37", f"={COMPS_STATS['priv_med']}", MULT)

section(V, 39, "(c) 10-year scenario DCF (detail on 3c_DCF)", 10)
header(V, 40, ["", "", "Bear", "Base", "Bull"])
V["B41"] = "(c) Equity value"  # filled after DCF build

section(V, 43, "Blended fair value (weights on 1_Assumptions)", 10)
header(V, 44, ["", "", "Bear", "Base", "Bull"])
V["B45"] = "Blended equity value"
for s in SCEN:
    c = SCOL[s]
    put(V, f"{c}45", f"={c}27*{R('w_anchor')}+{c}36*{R('w_mult')}+{c}41*{R('w_dcf')}", USD_B, fill=OUT_FILL)
V["B46"] = "vs Series H post-money"
V["B47"] = "vs IPO investor-advised midpoint"
for s in SCEN:
    c = SCOL[s]
    put(V, f"{c}46", f"={c}45/{R('seriesH_post')}-1", PCT)
    put(V, f"{c}47", f"={c}45/{R('ipo_mid')}-1", PCT)
V["B48"] = "Weights sum check (must be 100%)"
put(V, "C48", f"={R('w_anchor')}+{R('w_mult')}+{R('w_dcf')}", PCT)
V["B49"] = "Base implied EV / NTM revenue"
put(V, "C49", f"=(D45-{R('net_cash')})/C11", MULT)

section(V, 51, "Football field ($B equity value)", 10)
header(V, 52, ["", "Method", "Low", "Base", "High", "Bar start", "Bar length"])
ff = [
    ("(a) Last-round anchor", "=C27", "=D27", "=E27"),
    ("(b) Forward NTM multiple", "=C36", "=D36", "=E36"),
    ("(c) 10-yr DCF", "=C41", "=D41", "=E41"),
    ("Blended fair value", "=C45", "=D45", "=E45"),
    ("Secondary marks (Forge / Caplight / NPM)", f"={R('sec_forge')}", f"={R('sec_caplight')}", f"={R('sec_npm')}"),
    ("IPO valuation talk", f"={R('ipo_low')}", f"={R('ipo_mid')}", f"={R('ipo_high')}"),
]
for j, (lab, lo, mid, hi) in enumerate(ff):
    r = 53 + j
    V[f"B{r}"] = lab
    put(V, f"C{r}", lo, USD_0); put(V, f"D{r}", mid, USD_0); put(V, f"E{r}", hi, USD_0)
    put(V, f"F{r}", f"=MIN(C{r}:E{r})", USD_0); put(V, f"G{r}", f"=MAX(C{r}:E{r})-F{r}", USD_0)
ch = BarChart()
ch.type, ch.grouping, ch.overlap = "bar", "stacked", 100
ch.title = "Football field: Anthropic equity value ($B)"
ch.add_data(Reference(V, min_col=6, min_row=52, max_row=58), titles_from_data=True)
ch.add_data(Reference(V, min_col=7, min_row=52, max_row=58), titles_from_data=True)
ch.set_categories(Reference(V, min_col=2, min_row=53, max_row=58))
ch.series[0].graphicalProperties.noFill = True
ch.series[0].graphicalProperties.line.noFill = True
ch.series[1].graphicalProperties.solidFill = "1F2A44"
ch.legend = None
ch.height, ch.width = 8, 18
ch.y_axis.title = "$B"
ch.x_axis.scaling.orientation = "maxMin"
V.add_chart(ch, "B61")

# =============================================================================
# 3c. DCF
# =============================================================================
D = wb.create_sheet("3c_DCF")
D["A1"] = "3c. 10-year scenario DCF, FY2027-FY2036 ($B). Compute cost shown as an explicit line."
D["A1"].font = TITLE
D["A2"] = ("Mid-year discounting from the valuation date. Compute is mostly leased (S-1 commitments are purchase and "
           "lease obligations), so it runs through opex, not capex. Taxes on positive EBIT only; NOLs ignored.")
D["A2"].font = NOTE
setw(D, {"A": 4, "B": 44, **{L(c): 11 for c in range(3, 14)}, "N": 4, "O": 46, "P": 13})
YC = [L(c) for c in range(3, 14)]  # C..M = 2026..2036
header(D, 4, ["", "Fiscal year"] + [f"FY{y}{'E'}" for y in range(2026, 2037)])
D["B5"] = "Year index"
for i, col in enumerate(YC):
    put(D, f"{col}5", i, '0')
D["B6"] = "Stub: valuation date to 31-Dec-26 (yrs)"
put(D, "C6", f"=(DATE(2026,12,31)-{R('val_date')})/365", '0.000')
STUB = "'3c_DCF'!$C$6"

lines = ["Revenue growth", "Revenue", "Inference compute, % rev", "Inference compute (cost of revenue)",
         "Training + research compute, % rev", "Training + research compute", "TOTAL COMPUTE COST",
         "Other opex, % rev", "Other opex", "EBIT", "EBIT margin", "Cash taxes", "NOPAT", "Plus: D&A", "Less: capex",
         "Unlevered FCF", "Discount period t (yrs)", "Discount factor", "PV of FCF"]
DCF = {}
blk = 8
for s in SCEN:
    R0 = blk
    section(D, R0, f"{s.upper()} scenario", 13)
    rr = {name: R0 + 1 + k for k, name in enumerate(lines)}
    DCF[s] = rr
    for name, r in rr.items():
        D[f"B{r}"] = name
        if name in ("TOTAL COMPUTE COST", "EBIT", "Unlevered FCF"):
            D[f"B{r}"].font = BOLD
    put(D, f"C{rr['Revenue']}", "='3_Valuation'!$C$9", USD_B)
    for col in YC[1:]:
        p = chr(ord(col) - 1)
        idx = f"{col}$5"
        interp = lambda a, b: f"={R(a, s)}+({R(b, s)}-{R(a, s)})*({idx}-1)/9"
        put(D, f"{col}{rr['Revenue growth']}", f"={R('rev_g1', s)}*{R('g_decay', s)}^({idx}-1)", PCT)
        put(D, f"{col}{rr['Revenue']}", f"={p}{rr['Revenue']}*(1+{col}{rr['Revenue growth']})", USD_B)
        put(D, f"{col}{rr['Inference compute, % rev']}", interp("inf_start", "inf_end"), PCT)
        put(D, f"{col}{rr['Inference compute (cost of revenue)']}",
            f"=-{col}{rr['Revenue']}*{col}{rr['Inference compute, % rev']}", USD_B)
        put(D, f"{col}{rr['Training + research compute, % rev']}", interp("trn_start", "trn_end"), PCT)
        put(D, f"{col}{rr['Training + research compute']}",
            f"=-{col}{rr['Revenue']}*{col}{rr['Training + research compute, % rev']}", USD_B)
        put(D, f"{col}{rr['TOTAL COMPUTE COST']}",
            f"={col}{rr['Inference compute (cost of revenue)']}+{col}{rr['Training + research compute']}", USD_B)
        put(D, f"{col}{rr['Other opex, % rev']}", interp("opx_start", "opx_end"), PCT)
        put(D, f"{col}{rr['Other opex']}", f"=-{col}{rr['Revenue']}*{col}{rr['Other opex, % rev']}", USD_B)
        put(D, f"{col}{rr['EBIT']}",
            f"={col}{rr['Revenue']}+{col}{rr['TOTAL COMPUTE COST']}+{col}{rr['Other opex']}", USD_B)
        put(D, f"{col}{rr['EBIT margin']}", f"={col}{rr['EBIT']}/{col}{rr['Revenue']}", PCT)
        put(D, f"{col}{rr['Cash taxes']}", f"=-MAX(0,{col}{rr['EBIT']})*{R('tax')}", USD_B)
        put(D, f"{col}{rr['NOPAT']}", f"={col}{rr['EBIT']}+{col}{rr['Cash taxes']}", USD_B)
        put(D, f"{col}{rr['Plus: D&A']}", f"={col}{rr['Revenue']}*{R('capex', s)}", USD_B)
        put(D, f"{col}{rr['Less: capex']}", f"=-{col}{rr['Revenue']}*{R('capex', s)}", USD_B)
        put(D, f"{col}{rr['Unlevered FCF']}",
            f"={col}{rr['NOPAT']}+{col}{rr['Plus: D&A']}+{col}{rr['Less: capex']}", USD_B)
        put(D, f"{col}{rr['Discount period t (yrs)']}", f"={STUB}+{idx}-0.5", '0.00')
        put(D, f"{col}{rr['Discount factor']}",
            f"=1/(1+{R('wacc', s)})^{col}{rr['Discount period t (yrs)']}", '0.000')
        put(D, f"{col}{rr['PV of FCF']}", f"={col}{rr['Unlevered FCF']}*{col}{rr['Discount factor']}", USD_B)
    # summary in O/P
    sr = R0 + 1
    fcf, pv, rev, comp = (rr["Unlevered FCF"], rr["PV of FCF"], rr["Revenue"], rr["TOTAL COMPUTE COST"])
    summ = [
        ("Sum of PV of FCF (2027-36)", f"=SUM(D{pv}:M{pv})", USD_B),
        ("Terminal value at end-2036 (Gordon growth)",
         f"=M{fcf}*(1+{R('tg', s)})/({R('wacc', s)}-{R('tg', s)})", USD_B),
        ("PV of terminal value", f"=P{sr+1}/(1+{R('wacc', s)})^({STUB}+10)", USD_B),
        ("Enterprise value", f"=P{sr}+P{sr+2}", USD_B),
        ("Plus: net cash", f"={R('net_cash')}", USD_B),
        ("Less: dilution", f"=-(P{sr+3}+P{sr+4})*{R('dilution')}", USD_B),
        ("(c) Equity value", f"=P{sr+3}+P{sr+4}+P{sr+5}", USD_B),
        ("Terminal value as % of EV", f"=P{sr+2}/P{sr+3}", PCT),
        ("Implied TV / FY2036 revenue", f"=P{sr+1}/M{rev}", MULT),
        ("FY2036 revenue", f"=M{rev}", USD_B),
        ("Revenue CAGR FY26-36", f"=(M{rev}/C{rev})^(1/10)-1", PCT),
        ("Compute spend FY27-29", f"=-SUM(D{comp}:F{comp})", USD_B),
        ("  Coverage of commitments due pre-2030", f"=P{sr+11}/{R('commit_pre2030')}", PCT),
        ("Compute spend FY27-36", f"=-SUM(D{comp}:M{comp})", USD_B),
        ("  Coverage of $895B total commitments", f"=P{sr+13}/{R('commit_total')}", PCT),
    ]
    for k, (lab, f, fmt) in enumerate(summ):
        D[f"O{sr+k}"] = lab
        put(D, f"P{sr+k}", f, fmt, fill=OUT_FILL if lab.startswith("(c)") else None)
    DCF[s]["equity_cell"] = f"'3c_DCF'!$P${sr+6}"
    DCF[s]["summ0"] = sr
    blk = R0 + len(lines) + 3

for s in SCEN:
    put(V, f"{SCOL[s]}41", f"={DCF[s]['equity_cell']}", USD_B, fill=OUT_FILL)

# revenue chart
lc = LineChart()
lc.title = "Revenue by scenario ($B)"
for s in SCEN:
    r = DCF[s]["Revenue"]
    lc.add_data(Reference(D, min_col=3, max_col=13, min_row=r), from_rows=True, titles_from_data=False)
for k, s in enumerate(SCEN):
    lc.series[k].tx = SeriesLabel(v=s.title())
lc.set_categories(Reference(D, min_col=3, max_col=13, min_row=4))
lc.height, lc.width = 8, 18
D.add_chart(lc, f"B{blk + 1}")

# =============================================================================
# 4. SENSITIVITY
# =============================================================================
S = wb.create_sheet("4_Sensitivity")
S["A1"] = "4. Sensitivity (base-case DCF, $B equity value after dilution)"
S["A1"].font = TITLE
setw(S, {"A": 4, "B": 22, **{L(c): 11 for c in range(3, 12)}})
b = DCF["base"]
fcf_rng = f"'3c_DCF'!$D${b['Unlevered FCF']}:$M${b['Unlevered FCF']}"
t_rng = f"'3c_DCF'!$D${b['Discount period t (yrs)']}:$M${b['Discount period t (yrs)']}"
fcf_last = f"'3c_DCF'!$M${b['Unlevered FCF']}"
S["B3"] = "Table 1: WACC (rows) x terminal growth (columns)"; S["B3"].font = BOLD
waccs = [0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15]
tgs = [0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045]
put(S, "B4", "WACC \\ g", None, BOLD)
for j, g in enumerate(tgs):
    put(S, f"{L(3+j)}4", g, PCT, BLUE)
for i, w in enumerate(waccs):
    r = 5 + i
    put(S, f"B{r}", w, PCT, BLUE)
    for j in range(len(tgs)):
        col = L(3 + j)
        f = (f"=(SUMPRODUCT({fcf_rng}/(1+$B{r})^{t_rng})"
             f"+{fcf_last}*(1+{col}$4)/($B{r}-{col}$4)/(1+$B{r})^({STUB}+10)"
             f"+{R('net_cash')})*(1-{R('dilution')})")
        put(S, f"{col}{r}", f, USD_0)
S["B13"] = "Check: base WACC / g cell should equal 3c_DCF base equity"
put(S, "C13", f"={DCF['base']['equity_cell']}", USD_0)
put(S, "D13", "=F8", USD_0)
put(S, "E13", '=IF(ABS(C13-D13)<0.5,"OK","CHECK")')

S["B16"] = "Table 2: revenue CAGR FY26-31 (rows) x exit EV / revenue multiple at end-2031 (columns)"
S["B16"].font = BOLD
S["B17"] = "Value = (FY26 revenue x (1+CAGR)^5 x multiple) discounted at base WACC to today, + net cash, less dilution."
S["B17"].font = NOTE
cagrs = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]
mults = [5, 7, 9, 11, 13, 15, 18]
put(S, "B18", "CAGR \\ multiple", None, BOLD)
for j, m in enumerate(mults):
    put(S, f"{L(3+j)}18", m, MULT, BLUE)
for i, cg in enumerate(cagrs):
    r = 19 + i
    put(S, f"B{r}", cg, PCT, BLUE)
    for j in range(len(mults)):
        col = L(3 + j)
        f = (f"=('3_Valuation'!$C$9*(1+$B{r})^5*{col}$18/(1+{R('wacc','base')})^({STUB}+5)"
             f"+{R('net_cash')})*(1-{R('dilution')})")
        put(S, f"{col}{r}", f, USD_0)
S["B28"] = "Base-case FY26-31 revenue CAGR (from 3c_DCF)"
put(S, "C28", f"=('3c_DCF'!H{b['Revenue']}/'3c_DCF'!C{b['Revenue']})^(1/5)-1", PCT)
S["B29"] = "Base-case implied EV / revenue at end-2031 (TV-free check: forward multiple)"
put(S, "C29", f"=(SUMPRODUCT('3c_DCF'!I{b['Unlevered FCF']}:M{b['Unlevered FCF']}"
              f"/(1+{R('wacc','base')})^('3c_DCF'!I{b['Discount period t (yrs)']}:M{b['Discount period t (yrs)']}-5))"
              f"+'3c_DCF'!P{b['summ0']+1}/(1+{R('wacc','base')})^5)/'3c_DCF'!H{b['Revenue']}", MULT)
S["B31"] = "IPO-talk cross-check: cells >= investor-advised midpoint are shaded."
S["B31"].font = NOTE
from openpyxl.formatting.rule import CellIsRule
S.conditional_formatting.add("C19:I26", CellIsRule(operator="greaterThanOrEqual", formula=[R('ipo_mid')],
                                                   fill=PatternFill("solid", fgColor="D9EAD3")))
S.conditional_formatting.add("C5:I11", CellIsRule(operator="greaterThanOrEqual", formula=[R('ipo_mid')],
                                                  fill=PatternFill("solid", fgColor="D9EAD3")))

# =============================================================================
# 5. TOKEN STRUCTURE
# =============================================================================
T = wb.create_sheet("5_Token")
T["A1"] = "5. Token structure: SPV holding secondary shares, NAV per token, layered discounts"
T["A1"].font = TITLE
T["A2"] = ("Structure: token holders -> (DIFC/ADGM) SPV -> board-approved secondary purchase of Anthropic shares. "
           "One token = pro-rata claim on SPV NAV. $M unless stated.")
T["A2"].font = NOTE
setw(T, {"A": 4, "B": 54, "C": 14, "D": 14, "E": 14, "F": 14, "G": 44})
section(T, 4, "SPV capitalization", 7)
cap = [
    ("Capital raised from token holders ($M)", f"={R('spv_raise')}", USD_B),
    ("Tokens issued (M)", f"={R('spv_raise')}/{R('tok_issue')}", '#,##0.00'),
    ("Upfront structuring fee ($M)", f"=C5*{R('fee_upfront')}", USD_B),
    ("Expense reserve held in cash ($M)", f"=C5*{R('reserve')}", USD_B),
    ("Cash available for purchase incl. commission ($M)", "=C5-C7-C8", USD_B),
    ("Broker commission ($M)", f"=C9*{R('broker_fee')}/(1+{R('broker_fee')})", USD_B),
    ("Shares purchased at cost ($M)", "=C9-C10", USD_B),
    ("Secondary purchase valuation ($B)", f"={R('purchase_val')}", USD_B),
    ("SPV ownership of Anthropic", "=C11/(C12*1000)", '0.00000%'),
    ("Effective entry valuation paid by token holders ($B)", "=(C5/1000)/C13", USD_B),
    ("Entry premium vs Series H post-money", f"=C14/{R('seriesH_post')}-1", PCT),
]
for j, (lab, f, fmt) in enumerate(cap):
    r = 5 + j
    T[f"B{r}"] = lab
    put(T, f"C{r}", f, fmt, fill=OUT_FILL if r in (13, 14) else None)
T["G14"] = "Fees + reserve mean holders pay more than the SPV's purchase price."
T["G14"].font = NOTE

section(T, 17, "NAV and implied token price by scenario", 7)
header(T, 18, ["", "$ per token unless stated", "Bear", "Base", "Bull", "IPO midpoint"])
TC = ["C", "D", "E", "F"]
fv_src = ["='3_Valuation'!C45", "='3_Valuation'!D45", "='3_Valuation'!E45", f"={R('ipo_mid')}"]
trows = [
    ("Anthropic fair equity value ($B)", lambda c, k: fv_src[k], USD_B),
    ("Look-through NAV ($M)", lambda c, k: f"=$C$13*{c}19*1000+$C$8", USD_B),
    ("Gross NAV per token (fair value)", lambda c, k: f"={c}20/$C$6", USD_TOK),
    ("Less: management fee drag over holding period", lambda c, k: f"=-$C$5*{R('mgmt_fee')}*{R('hold_yrs')}/$C$6", USD_TOK),
    ("Less: carry on gains above issue price",
     lambda c, k: f"=-{R('carry')}*MAX(0,{c}21+{c}22-{R('tok_issue')})", USD_TOK),
    ("Net NAV per token (after fees)", lambda c, k: f"={c}21+{c}22+{c}23", USD_TOK),
    ("Less: DLOM (pre-IPO)", lambda c, k: f"=-{c}24*{R('dlom_pre')}", USD_TOK),
    ("Less: secondary / transfer-risk discount", lambda c, k: f"=-({c}24+{c}25)*{R('xfer_disc')}", USD_TOK),
    ("IMPLIED TOKEN PRICE, pre-IPO", lambda c, k: f"={c}24+{c}25+{c}26", USD_TOK),
    ("Token price discount to gross NAV, pre-IPO", lambda c, k: f"=1-{c}27/{c}21", PCT),
    ("Return vs $ issue price, pre-IPO", lambda c, k: f"={c}27/{R('tok_issue')}-1", PCT),
    ("IMPLIED TOKEN PRICE, post-IPO in lock-up (transfer risk falls away)",
     lambda c, k: f"={c}24*(1-{R('dlom_post')})", USD_TOK),
    ("Return vs issue price, post-IPO", lambda c, k: f"={c}30/{R('tok_issue')}-1", PCT),
]
for j, (lab, fn, fmt) in enumerate(trows):
    r = 19 + j
    T[f"B{r}"] = lab
    if lab.isupper() or lab.startswith("IMPLIED"):
        T[f"B{r}"].font = BOLD
    for k, c in enumerate(TC):
        put(T, f"{c}{r}", fn(c, k), fmt, fill=OUT_FILL if r in (27, 30) else None)

section(T, 33, "Discount waterfall, base case ($ per token)", 7)
wf = [("Gross NAV (fair value)", "=D21"), ("Management fee", "=D22"), ("Carry", "=D23"), ("DLOM", "=D25"),
      ("Transfer-risk discount", "=D26"), ("Implied token price", "=D27")]
for j, (lab, f) in enumerate(wf):
    T[f"B{34+j}"] = lab
    put(T, f"C{34+j}", f, USD_TOK)
T["B40"] = "Reconciliation check (sum of layers = price)"
put(T, "C40", "=IF(ABS(SUM(C34:C38)-C39)<0.0001,\"OK\",\"CHECK\")")

section(T, 42, "Break-even: Anthropic valuation at which token is worth its issue price", 7)
k_pre = f"((1-{R('dlom_pre')})*(1-{R('xfer_disc')}))"
fee_t = f"($C$5*{R('mgmt_fee')}*{R('hold_yrs')}/$C$6)"
iss = R('tok_issue'); cr = R('carry')
T["B43"] = "Required gross NAV per token, pre-IPO"
put(T, "C43", f"=({iss}/{k_pre}-{cr}*{iss})/(1-{cr})+{fee_t}", USD_TOK)
T["B44"] = "Break-even Anthropic valuation, pre-IPO ($B)"
put(T, "C44", "=(C43*$C$6-$C$8)/($C$13*1000)", USD_B, fill=OUT_FILL)
T["B45"] = "Required gross NAV per token, post-IPO lock-up"
put(T, "C45", f"=({iss}/(1-{R('dlom_post')})-{cr}*{iss})/(1-{cr})+{fee_t}", USD_TOK)
T["B46"] = "Break-even Anthropic valuation, post-IPO ($B)"
put(T, "C46", "=(C45*$C$6-$C$8)/($C$13*1000)", USD_B, fill=OUT_FILL)
T["B47"] = "Break-even vs IPO investor-advised midpoint"
put(T, "C47", f"=C44/{R('ipo_mid')}-1", PCT)
T["B48"] = "Check: base price at break-even valuation equals issue price (see note)"
T["G48"] = "Algebra holds while net NAV > issue price (carry is on)."
T["G48"].font = NOTE

# =============================================================================
# 6. RISKS
# =============================================================================
K = wb.create_sheet("6_Risks")
K["A1"] = "6. Risk register: tokenized pre-IPO Anthropic exposure"
K["A1"].font = TITLE
setw(K, {"A": 4, "B": 26, "C": 58, "D": 10, "E": 10, "F": 58, "G": 40})
header(K, 3, ["#", "Risk", "What goes wrong", "Likelihood", "Impact", "Structural response", "Source / model link"])
risks = [
    ("Transfer restrictions / void transfers",
     "Anthropic's May-26 notice: any share transfer not approved by the board is void; named Forge and Hiive as "
     "unauthorized venues. A token over an unapproved transfer may own nothing.",
     "High", "Severe", "Buy only via company-approved transfer (or primary allocation); obtain issuer consent letter; "
     "no forward contracts or synthetic 'pre-stock' claims.", "tech-insider.org; coinmarketcap academy (May-26)"),
    ("Right of first refusal (ROFR)",
     "Company or existing investors can match and take the shares, killing the deal after fees are sunk.",
     "Medium", "High", "Close only after ROFR window lapses; escrow investor cash until then.", "Standard private-co bylaws"),
    ("Investor eligibility",
     "Tokens over unlisted shares are securities: only Professional Clients (DFSA/FSRA) or VARA qualified investors "
     "(AED 3.5M net assets or AED 700k income).", "High", "Medium",
     "Whitelisted wallets, KYC at token level, transfer agent checks on every on-chain transfer.",
     "zamanathq.com; neolegal.ae (2026)"),
    ("Jurisdiction / regulator perimeter",
     "Tokenized securities sit with DFSA (DIFC), FSRA (ADGM) or federal CMA (mainland), not VARA. Wrong licence "
     "= unauthorized offering.", "Medium", "Severe",
     "Structure SPV and token in ADGM (FSRA digital securities + MTF) or DIFC (DFSA QIF / Investment Token).",
     "blockhertz.com; zamanathq.com (2026)"),
    ("Custody",
     "Two custody legs: share register (off-chain) and token ledger (on-chain). A mismatch breaks the 1:1 claim.",
     "Medium", "High", "Regulated custodian holds share certificates; daily register-to-token reconciliation; "
     "proof-of-reserve attestation.", "Analyst"),
    ("Liquidity",
     "Only active UAE venue for tokenized securities is an ADGM-supervised MTF; in practice bilateral transfers "
     "between whitelisted holders.", "High", "Medium",
     "Price in DLOM; set redemption only at IPO + lock-up expiry; market-maker agreement on the MTF.",
     "zamanathq.com (2026)"),
    ("NAV vs token price mismatch",
     "Pre-IPO tokens historically traded 20-40% above NAV (scarcity) and fell 38-46% in a day on company warnings.",
     "High", "High", "Publish NAV daily from the model; cap issuance premium; disclose break-even valuation.",
     "Pantera research; coinmarketcap academy"),
    ("Entry price above fair value",
     "SPV buys at ~$1.3T; model base fair value is below that, so holders start underwater.",
     "High", "High", "Negotiate entry at or below Series H + run-rate uplift; or buy at IPO and tokenize lock-up shares.",
     "='5_Token'!D29"),
    ("IPO timing / window",
     "Roadshow reportedly from 9-Nov-26. The pre-IPO window is weeks long: a token launched now is really a "
     "lock-up / post-IPO vehicle.", "High", "Medium",
     "Design the token to convert into listed shares at lock-up expiry; disclose conversion mechanics up front.",
     "financefeeds.com; leverageshares IPO tracker"),
    ("Valuation / growth deceleration",
     "Q3-26 revenue growth fell to +47% QoQ from +144%; $895B of compute commitments are fixed while revenue is not.",
     "Medium", "Severe", "Show bear case; size position as satellite; disclose commitment coverage.",
     "Amended S-1 (2-Nov-26)"),
]
for j, row in enumerate(risks):
    r = 4 + j
    K[f"A{r}"] = j + 1
    for col, v in zip("BCDEFG", row):
        K[f"{col}{r}"] = v
        K[f"{col}{r}"].alignment = WRAP
        K[f"{col}{r}"].border = THIN
    K.row_dimensions[r].height = 62
K["G11"].number_format = PCT
r = 4 + len(risks) + 1
K[f"B{r}"] = "Quantified links"; K[f"B{r}"].font = BOLD
links = [("Base pre-IPO token discount to NAV", "='5_Token'!D28", PCT),
         ("Base pre-IPO token return vs issue", "='5_Token'!D29", PCT),
         ("Break-even Anthropic valuation, pre-IPO ($B)", "='5_Token'!C44", USD_B),
         ("Bear-case compute FY27-29 / commitments due pre-2030",
          f"='3c_DCF'!P{DCF['bear']['summ0']+12}", PCT)]
for j, (lab, f, fmt) in enumerate(links):
    K[f"B{r+1+j}"] = lab
    put(K, f"C{r+1+j}", f, fmt, fill=OUT_FILL)

# =============================================================================
# README sheet first
# =============================================================================
M = wb.create_sheet("0_ReadMe", 0)
M["A1"] = "Anthropic valuation and tokenized pre-IPO vehicle: model map"
M["A1"].font = TITLE
notes = [
    "Valuation date 6-Nov-2026. All values in $B unless stated. Blue = input, black = formula, yellow = key output.",
    "1_Assumptions: every input with source, date, confidence (Reported / Estimated / Assumed).",
    "2_Comps: peer multiples and one-line rationale; stats feed the 3_Valuation cross-check.",
    "3_Valuation: revenue build, (a) last-round anchor, (b) NTM multiple, blended value, football field.",
    "3c_DCF: 10-year bear / base / bull DCF with explicit compute-cost lines and commitment coverage.",
    "4_Sensitivity: WACC x terminal growth; revenue CAGR x exit multiple.",
    "5_Token: SPV capitalization, NAV per token, layered discounts, break-even valuation.",
    "6_Risks: transfer restrictions, eligibility, UAE jurisdiction, custody, liquidity, NAV mismatch.",
    "Not investment advice. Figures from secondary reporting of the S-1 should be re-checked against EDGAR.",
]
for i, n in enumerate(notes):
    M[f"A{3+i}"] = n
M.column_dimensions["A"].width = 120

wb.calculation.fullCalcOnLoad = True
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("saved", OUT)
