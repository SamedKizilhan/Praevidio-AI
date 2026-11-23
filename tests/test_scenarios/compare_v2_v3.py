# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — side-by-side comparison of the risk models (v2, v3.0, v3.1)
===========================================================================
Every scenario in scenarios.json plus the probe cases for the review findings is run through
the spring model (v2), the October model (v3.0) and the current model (v3.1). The result is
written to docs/model_comparison_v2_v3.md.

Run:  python tests/test_scenarios/compare_v2_v3.py   (or: make compare)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from model.hybrid_bayesian_network_v3 import load_engine, SYMPTOMATIC_FRACTION, NORMALIZE_ORS, PRESETS

SCENARIOS = ROOT / "tests" / "test_scenarios" / "scenarios.json"
OUT = ROOT / "docs" / "model_comparison_v2_v3.md"

S7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING",
      "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
_B = {"AGE": 4, "GENDER": 1, "SMOKING": 1, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0}
# (id, name, evidence) — ids and evidence are part of the frozen baseline (tests/model/profiles.py)
PROBES = [
    ("B1a", "Finding 1: man 70+, current smoker, symptoms not asked", _B),
    ("B1b", "Finding 1: same person, all seven symptoms 'no'", {**_B, **{s: 0 for s in S7}}),
    ("B1c", "Finding 1: same person, haemoptysis 'yes', six 'no'", {**_B, **{s: 0 for s in S7}, "HEMOPTYSIS": 1}),
    ("B2a", "Finding 2: cough, dyspnoea and wheeze; COPD unknown", {**_B, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("B2b", "Finding 2: same symptoms, COPD diagnosed", {**_B, "COPD": 1, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("B2c", "Finding 2: same symptoms, COPD denied", {**_B, "COPD": 0, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("B2d", "Finding 2: all seven symptoms 'yes'", {**_B, **{s: 1 for s in S7}}),
    ("B3a", "Finding 3: man 60-64, current smoker, other factors not asked", {"AGE": 2, "GENDER": 1, "SMOKING": 1}),
    ("B3b", "Finding 3: same person, every other factor absent", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0, "COPD": 0}),
    ("B3c", "Finding 3: same person, average exposure (moderate air pollution)", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 1}),
    ("B4a", "Finding 4: woman 55-59, former smoker (15 pack-years), no symptoms", {"AGE": 1, "GENDER": 0, "SMOKING": 0, "_pack_years": 15, "FAMILY_HISTORY": 1}),
    ("B4b", "Finding 4: man 62, current smoker, haemoptysis only (others not asked)", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "HEMOPTYSIS": 1, "_age_exact": 62}),
]

AGE_LBL = {0: "under 55", 1: "55-59", 2: "60-64", 3: "65-69", 4: "70+"}
SYM_LBL = {"COUGHING": "cough", "SHORTNESS_OF_BREATH": "dyspnoea", "CHEST_PAIN": "chest pain",
           "WHEEZING": "wheeze", "FATIGUE": "fatigue", "HEMOPTYSIS": "haemoptysis", "WEIGHT_LOSS": "weight loss"}
AIR_LBL = {0: "low", 1: "moderate", 2: "high"}
BAND_EN = {"low": "below threshold", "moderate": "moderate", "high": "high"}


def profile(ev: dict) -> str:
    """Readable description of a case, built from its evidence (shown under the scenario name)."""
    age = f"age {ev['_age_exact']}" if ev.get("_age_exact") is not None else "age " + AGE_LBL.get(ev.get("AGE"), "?")
    sex = {0: "woman", 1: "man"}.get(ev.get("GENDER"), "sex ?")
    py, sm = ev.get("_pack_years"), ev.get("SMOKING")
    smoke = "current smoker" if sm == 1 else ("never-smoker" if py == 0 else "former smoker") if sm == 0 else "smoking ?"
    det = []
    if ev.get("_cigs_per_day") is not None and ev.get("_years_smoked") is not None:
        det.append(f"{ev['_cigs_per_day']:g}/day for {ev['_years_smoked']:g} years")
    elif py:
        det.append(f"{py:g} pack-years")
    if ev.get("_years_quit") is not None and sm == 0 and py != 0:
        det.append(f"quit {ev['_years_quit']:g} years ago")
    if det:
        smoke += " (" + ", ".join(det) + ")"

    rf, unasked = [], []
    for key, lbl in (("FAMILY_HISTORY", "family history"), ("ASBESTOS", "occupational exposure")):
        if key in ev:
            rf.append(f"{lbl} {'yes' if ev[key] == 1 else 'no'}")
        else:
            unasked.append(lbl)
    if "AIR_POLLUTION" in ev:
        rf.append(f"air pollution {AIR_LBL[ev['AIR_POLLUTION']]}")
    else:
        unasked.append("air pollution")
    if "COPD" in ev:
        rf.append(f"COPD {'yes' if ev['COPD'] == 1 else 'no'}")
    if unasked:
        rf.append("not asked: " + ", ".join(unasked))

    yes = [SYM_LBL[k] for k in SYM_LBL if ev.get(k) == 1]
    no = sum(1 for k in SYM_LBL if ev.get(k) == 0)
    miss = sum(1 for k in SYM_LBL if k not in ev)
    if not yes and no == 0:
        sym = "symptoms not asked"
    elif not yes and miss == 0:
        sym = "no symptoms (all seven 'no')"
    else:
        rest = ([f"{no} 'no'"] if no else []) + ([f"{miss} not asked"] if miss else [])
        sym = "symptoms: " + (", ".join(yes) if yes else "none") + (f" (others: {', '.join(rest)})" if rest else "")
    return f"{sex}, {age} · {smoke} · {', '.join(rf)} · {sym}"


def main():
    e2, e30, e3 = load_engine("v2"), load_engine("v3.0"), load_engine("v3.1")
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    rows = [(s["id"], s.get("name_en") or s["name"], s["evidence"]) for s in data["scenarios"]] + PROBES
    d2_ev = next(s["evidence"] for s in data["scenarios"] if s["id"] == "D2")
    d2_2, d2_30, d2 = e2.predict_risk(d2_ev), e30.predict_risk(d2_ev), e3.predict_risk(d2_ev)
    p31 = PRESETS["v3.1"]

    L = ["# Risk model comparison: v2, v3.0 and v3.1", "",
         f"*Generated by `make compare`; do not edit by hand. Parameters: q = {SYMPTOMATIC_FRACTION}, odds-ratio "
         f"normalisation {'on' if NORMALIZE_ORS else 'off'}; v3.1 common-cause prior π = {p31['other_prior']:g}, "
         f"share ρ = {p31['other_share']:g}.*", "",
         "| Model | When | What it is |", "| --- | --- | --- |",
         "| **v2** | Spring 2026 | One Bayesian network: NLST risk factors and literature symptom probabilities on a single "
         "cancer node. Bands 5 % / 15 % with no time horizon. |",
         "| **v3.0** | October 2026 | Latent *symptomatic now* node, COPD as a common cause of respiratory symptoms, normalised "
         "odds ratios, 6-year layer with bands tied to the PLCOm2012 screening threshold, NICE NG12 rule. NLST base. |",
         "| **v3.1** | November 2026 | 6-year base from PLCOm2012 (ever-smokers) and Wakelee 2007 (never-smokers); latent *other "
         "illness* as a common cause of all seven symptoms, calibrated to NHANES. **Current model.** |", "",
         "Why v3.1 exists and how every profile changed: [`model_v3_1_calibration_fix.md`](model_v3_1_calibration_fix.md). "
         "Design of v3: [`model_v3_design.md`](model_v3_design.md).", "",
         "## Two questions, two layers", "",
         "The current model answers two separate questions (see [`symptom_layer.md`](symptom_layer.md)):", "",
         "* **Should I be screened?** The *6-year layer*: risk from risk factors alone. Below 1.5 % is below the screening "
         "threshold, 1.5–5 % is moderate, 5 % or more is high.",
         "* **Should I see a doctor about my symptoms?** The *symptom layer*: probability that the current symptoms are due "
         "to lung cancer, with a 3 % threshold, together with the NICE NG12 rule and a haemoptysis rule for any age.", "",
         "The full score mixes both and is therefore reported without a band.", "",
         "## How to read the table", "",
         "Each row is one person, with the same answers given to all three models; the profile is written under the "
         "scenario name. \"Not asked\" means the model did not receive that information; \"no\" means the person denied it. "
         "Rows: **D** demonstration cases, **P** controlled pairs (one variable differs), **S** smoking-dose series, "
         "**B** probes for the findings of the model review.", "",
         "| Column | Meaning |", "| --- | --- |",
         "| v2 % (band) | Spring model; bands below 5 % low, 5–15 % moderate, 15 % or more high. |",
         "| v3.0 full / 6y | October model: full score and 6-year layer. |",
         "| v3.1 full | Current full score (risk factors and symptoms; mixed horizon, not banded). |",
         "| v3.1 symptom layer | Probability that the current symptoms are due to lung cancer. ⚠ marks 3 % or more. "
         "A dash means no symptom was reported. |",
         "| v3.1 6y (band) | Current 6-year layer and its band. Equal to the full score when no symptom was asked (D5). |",
         "| PLCOm2012 | External benchmark (Tammemägi 2013), ever-smokers only. Where the scenario gives no daily amount "
         "or duration, the model's central values are assumed (20 a day, 27 years, quit 10 years ago); the S series is the "
         "most meaningful comparison. |",
         "| Prompt | \"yes\" = prompt physician assessment is advised. Any one of: the NICE NG12 rule (age 40 or more with "
         "haemoptysis, or with two or more unexplained symptoms, or an ever-smoker with one), a symptom layer of 3 % or more, "
         "or haemoptysis at any age. |", "",
         f"**Example (D2).** Man aged 65-69, former smoker, cough and fatigue. v2: {d2_2['risk_score']:.1f} % (moderate). "
         f"v3.0: 6-year layer {d2_30['risk_6y_factors']:.1f} %, full {d2_30['risk_score']:.1f} %. v3.1: 6-year layer "
         f"{d2['risk_6y_factors']:.1f} % ({BAND_EN[d2['risk_level_factors']]}); symptom layer "
         f"{d2['symptom_assessment']['percent']:.1f} % (below 3 %); full score {d2['risk_score']:.1f} %. Prompt assessment is "
         f"advised by the NICE rule: older than 40 with two unexplained symptoms.", "",
         "## Results", "",
         "| ID | Scenario | v2 % (band) | v3.0 full | v3.0 6y | v3.1 full | v3.1 symptom layer | v3.1 6y (band) | PLCOm2012 | Prompt |",
         "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    print(f"{'ID':5s} {'v2':>7s} {'v3.0':>7s} {'v3.1':>7s} {'sym':>6s} {'6y':>6s} {'PLCO':>6s} prompt  scenario")
    for sid, name, ev in rows:
        r2, r30, r3 = e2.predict_risk(ev), e30.predict_risk(ev), e3.predict_risk(ev)
        sa = r3.get("symptom_assessment") or {}
        sl = "–" if sa.get("level") in (None, "none") else f"{sa['percent']:.2f}" + (" ⚠" if sa["level"] == "elevated" else "")
        bm = r3["benchmark_plcom2012"]
        plco = f"{bm['risk_6y']:.2f}" if bm["applicable"] else "n/a"
        prompt = "yes" if r3.get("urgent_assessment") else "–"
        L.append(f"| {sid} | **{name}**<br><sub>{profile(ev)}</sub> | {r2['risk_score']:.2f} ({r2['risk_level']}) | "
                 f"{r30['risk_score']:.2f} | {r30['risk_6y_factors']:.2f} | {r3['risk_score']:.2f} | {sl} | "
                 f"{r3['risk_6y_factors']:.2f} ({BAND_EN[r3['risk_level_factors']]}) | {plco} | {prompt} |")
        print(f"{sid:5s} {r2['risk_score']:7.2f} {r30['risk_score']:7.2f} {r3['risk_score']:7.2f} {sl:>6s} "
              f"{r3['risk_6y_factors']:6.2f} {plco:>6s} {prompt:7s} {name[:60]}")

    L += ["", "## Notes", "",
          "- **B1a and B1b (Finding 1).** In v2, seven \"no\" answers cut the odds 36-fold and labelled a heavy smoker low risk. "
          "From v3 on, the 6-year layer is untouched by symptom answers; only the probability of being symptomatic today falls.",
          "- **B1c.** In v3.0 six denials cancelled the one alarm symptom. In v3.1 haemoptysis alone raises the score.",
          "- **B2a to B2c (Finding 2).** COPD explains part of the respiratory symptoms when present. When COPD is denied the "
          "symptoms count more toward cancer; in v3.1 the *other illness* node limits this.",
          "- **B2d.** All seven symptoms gave 99.7 % in v3.0. This had been accepted because the NICE rule also fired; a trial "
          "with a person under 40, where it does not fire, showed that the number itself was wrong. In v3.1 the symptom "
          "multiplier of every combination stays inside the bounds derived from Hamilton et al. 2005 "
          "(`tests/model/test_plausibility.py`).",
          "- **B3a to B3c (Finding 3).** With normalised odds ratios a person who is not asked about a factor, or has average "
          "exposure, stays at the base rate; a person without the factor falls below it.",
          "- **B4 (Finding 4).** The bands of the 6-year layer are tied to the PLCOm2012 screening threshold of 1.51 % over "
          "six years.",
          "- **PLCOm2012 column.** Plain PLCOm2012 with unknown family history and COPD set to zero and without occupational "
          "exposure or air pollution. The v3.1 6-year layer for ever-smokers is built on it; differences come from averaging "
          "unknown family history and COPD over their priors and from the two extra factors. The NLST base of v3.0 was 2 to 35 "
          "times higher for young or light smokers, because every NLST participant was aged 55-74 with at least 30 pack-years."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {OUT}")


if __name__ == "__main__":
    main()
