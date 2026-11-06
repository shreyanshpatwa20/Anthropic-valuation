# Anthropic valuation and tokenized pre-IPO exposure vehicle

Portfolio project, valuation date **6 Nov 2026**. It has two parts: a live-formula Excel model, and a 12-slide deck generated from that model's outputs.

| File | What it is |
|---|---|
| `output/Anthropic_Valuation_Model.xlsx` | Model (openpyxl, live formulas; recalculates on open) |
| `output/recalc/Anthropic_Valuation_Model.xlsx` | Same model after a LibreOffice recalculation, with cached values (for viewers that don't recalculate) |
| `output/Anthropic_Pitch_Deck.pptx` | 12-slide deck built from the model outputs |
| `model/build_model.py` | Builds the workbook |
| `model/check_model.py` | Recalculates the workbook, scans every formula for errors, writes `output/model_values.json` |
| `deck/build_deck.py` | Builds the charts and the deck from `model_values.json` |

Rebuild: `python model/build_model.py && python model/check_model.py && python deck/build_deck.py` (needs LibreOffice, openpyxl, python-pptx and matplotlib).

Sheets: 0_ReadMe, 1_Assumptions (every input with its source, date and Reported/Estimated/Assumed tag), 2_Comps, 3_Valuation (anchor, NTM multiple, blend, football field), 3c_DCF (bear/base/bull, explicit compute lines), 4_Sensitivity, 5_Token, 6_Risks.

Many S-1 figures come from secondary coverage of the filing. Re-verify them on EDGAR before relying on them. Not investment advice.
