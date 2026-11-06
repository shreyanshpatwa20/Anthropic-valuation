"""Recalculate the workbook with LibreOffice, scan every cell for formula errors, dump key outputs.

Usage: python model/check_model.py   (writes output/recalc/Anthropic_Valuation_Model.xlsx and output/model_values.json)
"""
import json
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output" / "Anthropic_Valuation_Model.xlsx"
RECALC_DIR = ROOT / "output" / "recalc"
RECALC = RECALC_DIR / SRC.name
ERRORS = ("#REF!", "#DIV/0!", "#NAME?", "#VALUE!", "#N/A", "#NUM!", "#NULL!", "Err:")

subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(RECALC_DIR), str(SRC)],
               check=True, capture_output=True)

f_wb = load_workbook(SRC)
v_wb = load_workbook(RECALC, data_only=True)
n_formulas, errors, empty = 0, [], []
for ws in f_wb.worksheets:
    vws = v_wb[ws.title]
    for row in ws.iter_rows():
        for c in row:
            val = c.value
            is_f = (isinstance(val, str) and val.startswith("=")) or type(val).__name__ == "ArrayFormula"
            if not is_f:
                continue
            n_formulas += 1
            out = vws[c.coordinate].value
            if out is None:
                empty.append(f"{ws.title}!{c.coordinate}")
            elif isinstance(out, str) and any(out.startswith(e) for e in ERRORS):
                errors.append(f"{ws.title}!{c.coordinate} -> {out}")

print(f"Formulas checked: {n_formulas}; errors: {len(errors)}; empty results: {len(empty)}")
for e in errors[:50]:
    print("  ERROR", e)
for e in empty[:20]:
    print("  EMPTY", e)


def g(sheet, addr):
    return v_wb[sheet][addr].value


V, T, D, S = "3_Valuation", "5_Token", "3c_DCF", "4_Sensitivity"
vals = {
    "fy26": g(V, "C9"), "ntm": g(V, "C11"), "rr_q3": g(V, "C12"), "nine_m": g(V, "C8"), "ntm_growth": g(V, "C14"),
    "fy26_growth": g(V, "C10"),
    "anchor": [g(V, f"{c}27") for c in "CDE"], "mult": [g(V, f"{c}36") for c in "CDE"],
    "dcf": [g(V, f"{c}41") for c in "CDE"], "blend": [g(V, f"{c}45") for c in "CDE"],
    "blend_vs_h": [g(V, f"{c}46") for c in "CDE"], "blend_vs_ipo": [g(V, f"{c}47") for c in "CDE"],
    "base_ev_ntm": g(V, "C49"),
    "ff": [[g(V, f"B{r}"), g(V, f"C{r}"), g(V, f"D{r}"), g(V, f"E{r}")] for r in range(53, 59)],
    "ntm_mults": [g(V, f"{c}32") for c in "CDE"],
    "comps_cross": [g(V, f"{c}37") for c in "CDE"],
    "tok": {lab: [g(T, f"{c}{r}") for c in "CDEF"] for lab, r in
            [("fv", 19), ("nav", 21), ("fee", 22), ("carry", 23), ("net", 24), ("dlom", 25), ("xfer", 26),
             ("price_pre", 27), ("disc_pre", 28), ("ret_pre", 29), ("price_post", 30), ("ret_post", 31)]},
    "own": g(T, "C13"), "entry_val": g(T, "C14"), "entry_prem": g(T, "C15"),
    "be_pre": g(T, "C44"), "be_post": g(T, "C46"), "be_vs_ipo": g(T, "C47"), "wf_check": g(T, "C40"),
    "sens_check": g(S, "E13"), "base_cagr_5y": g(S, "C28"),
}
# DCF scenario detail
for s, start in (("bear", 8), ("base", 30), ("bull", 52)):
    pass
dcf = {}
for ws_row in range(1, 120):
    lab = v_wb[D][f"O{ws_row}"].value
    if lab:
        dcf.setdefault(lab, []).append(v_wb[D][f"P{ws_row}"].value)
vals["dcf_summary"] = dcf
rows = {}
for r in range(1, 120):
    lab = v_wb[D][f"B{r}"].value
    if lab in ("Revenue", "EBIT margin", "TOTAL COMPUTE COST", "Unlevered FCF"):
        rows.setdefault(lab, []).append([v_wb[D].cell(row=r, column=c).value for c in range(3, 14)])
vals["dcf_rows"] = rows
vals["sens1"] = [[v_wb[S].cell(row=r, column=c).value for c in range(2, 10)] for r in range(4, 12)]
vals["sens2"] = [[v_wb[S].cell(row=r, column=c).value for c in range(2, 10)] for r in range(18, 27)]
(ROOT / "output" / "model_values.json").write_text(json.dumps(vals, indent=1, default=str))
print(json.dumps({k: vals[k] for k in vals if k not in ("dcf_rows", "sens1", "sens2", "ff")}, indent=1, default=str))
sys.exit(1 if errors or empty else 0)
