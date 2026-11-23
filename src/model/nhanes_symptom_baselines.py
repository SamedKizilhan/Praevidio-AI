# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — symptom baselines in people without cancer, from NHANES
=======================================================================
The "no cancer" columns of the symptom tables (leak, smoking and COPD contributions) come from the
literature and had not been checked against any cohort. NHANES 2007–2012 (US general-population
survey, RDQ respiratory module) gives, for people without cancer,
    P(chronic cough | smoking status, age group),  P(wheeze | ...),  P(phlegm | ...)
and this script sets them beside the values implied by the noisy-OR parameters of the v3 model.

Input:   data/raw/nhanes/{RDQ,SMQ,MCQ,DEMO}_{E,F,G}.xpt   (bash tools/download_nhanes.sh)
Output:  data/processed/nhanes_symptom_baselines.json + docs/nhanes_symptom_baselines.md

Variables (NHANES codebooks):
  RDQ031  Coughing most days, 3 months or more (chronic cough)   1 = yes, 2 = no
  RDQ050  Bring up phlegm most days, 3 months or more            1/2
  RDQ070  Wheezing or whistling in chest, past 12 months          1/2
  SMQ020  Smoked at least 100 cigarettes in life                   1/2
  SMQ040  Do you now smoke: 1 every day, 2 some days, 3 not at all
  MCQ220  Ever told you had cancer                                  1/2
  MCQ230A-D  Cancer type codes (23 = lung)
  RIDAGEYR age, RIAGENDR sex (1 male, 2 female), WTINT2YR interview weight
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "nhanes"
OUT_JSON = ROOT / "data" / "processed" / "nhanes_symptom_baselines.json"
OUT_MD = ROOT / "docs" / "nhanes_symptom_baselines.md"
CYCLES = ["E", "F", "G"]

sys.path.insert(0, str(ROOT / "src"))


def load_cycle(letter: str) -> pd.DataFrame:
    frames = []
    for f in ("DEMO", "SMQ", "RDQ", "MCQ"):
        p = RAW / f"{f}_{letter}.xpt"
        if not p.exists():
            raise FileNotFoundError(f"{p} is missing; run first: bash tools/download_nhanes.sh")
        frames.append(pd.read_sas(p, format="xport"))
    df = frames[0]
    for fr in frames[1:]:
        df = df.merge(fr, on="SEQN", how="left")
    df["cycle"] = letter
    return df


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Derive smoking status, age group, cancer flags and symptoms (survey respondents)."""
    d = df.copy()
    d = d[d["RIDAGEYR"] >= 40]                                   # RDQ chronic cough is asked from age 40
    ever = d["SMQ020"] == 1
    now = d["SMQ040"].isin([1, 2])
    d["smoking"] = "never"
    d.loc[ever & ~now, "smoking"] = "former"
    d.loc[ever & now, "smoking"] = "current"
    d.loc[d["SMQ020"].isna() | ((d["SMQ020"] == 1) & d["SMQ040"].isna()), "smoking"] = None
    d["age_group"] = pd.cut(d["RIDAGEYR"], bins=[39, 54, 64, 120], labels=["40-54", "55-64", "65+"])
    cancer_cols = [c for c in ("MCQ230A", "MCQ230B", "MCQ230C", "MCQ230D") if c in d.columns]
    d["any_cancer"] = d["MCQ220"] == 1
    d["lung_cancer"] = False
    for c in cancer_cols:
        d["lung_cancer"] |= d[c] == 23
    for var, col in (("chronic_cough", "RDQ031"), ("phlegm", "RDQ050"), ("wheeze", "RDQ070")):
        d[var] = d[col].map({1: 1.0, 2: 0.0})                   # 7/9 (don't know / refused) -> NaN
    d["w"] = d["WTINT2YR"] / len(CYCLES)                         # combined weight over three cycles
    return d


def weighted_rate(sub: pd.DataFrame, var: str):
    s = sub.dropna(subset=[var, "w"])
    if len(s) < 30:
        return None, int(len(s))
    return float((s[var] * s["w"]).sum() / s["w"].sum()), int(len(s))


def implied_v3() -> dict:
    """P(symptom | smoking) implied by the v3 noisy-OR parameters for a person without cancer."""
    from model.hybrid_bayesian_network_v3 import NOISY_OR, COPD_GIVEN_SMOKING
    out = {}
    for sym, p in NOISY_OR.items():
        row = {}
        for status, sm, pc in (("never", 0, 0.0), ("former", 0, COPD_GIVEN_SMOKING[0]),
                               ("current", 1, COPD_GIVEN_SMOKING[1])):
            no_copd = 1 - (1 - p["leak"]) * (1 - p["smoke"]) ** sm
            with_copd = 1 - (1 - p["leak"]) * (1 - p["smoke"]) ** sm * (1 - p["copd"])
            row[status] = round((1 - pc) * no_copd + pc * with_copd, 3)
        out[sym] = row
    return out


def main():
    df = pd.concat([load_cycle(c) for c in CYCLES], ignore_index=True)
    d = derive(df)
    base = d[~d["any_cancer"] & d["smoking"].notna()]          # no cancer of any kind, smoking status known
    res = {"source": "NHANES 2007-2012 (E,F,G), age ≥40, no self-reported cancer, WTINT2YR/3 weighted",
           "n_total_40plus": int(len(d)), "n_no_cancer": int(len(base)),
           "n_self_reported_lung_cancer_40plus": int(d["lung_cancer"].sum()),
           "rates": {}, "implied_v3_no_cancer": implied_v3()}
    for var in ("chronic_cough", "phlegm", "wheeze"):
        res["rates"][var] = {}
        for status in ("never", "former", "current"):
            sub = base[base["smoking"] == status]
            rate, n = weighted_rate(sub, var)
            res["rates"][var][status] = {"all_40plus": rate, "n": n}
            for ag in ("40-54", "55-64", "65+"):
                r2, n2 = weighted_rate(sub[sub["age_group"] == ag], var)
                res["rates"][var][status][ag] = {"rate": r2, "n": n2}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    imp = res["implied_v3_no_cancer"]
    L = ["# Symptom baselines in people without cancer (NHANES check of the v3 model)", "",
         "*Generated by `make nhanes`; do not edit by hand.*", "",
         f"Source: {res['source']}. Respondents aged 40 or more: {res['n_total_40plus']}; without cancer: "
         f"{res['n_no_cancer']}. Self-reported lung cancer (40+): {res['n_self_reported_lung_cancer_40plus']}, too few "
         "for the cancer column, so only the baselines **without cancer** are used.", "",
         "| Symptom (NHANES definition) | Smoking | NHANES % (n) | 40-54 | 55-64 | 65+ | Implied by v3 % (no cancer) |",
         "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    label = {"chronic_cough": ("Chronic cough (most days, 3 months or more)", "COUGHING"),
             "phlegm": ("Phlegm (most days, 3 months or more)", None),
             "wheeze": ("Wheeze or whistling (past 12 months)", "WHEEZING")}
    def pct(x): return "–" if x is None else f"{x*100:.1f}"
    for var, (lbl, v3key) in label.items():
        for status in ("never", "former", "current"):
            r = res["rates"][var][status]
            v3v = pct(imp[v3key][status]) if v3key else "–"
            L.append(f"| {lbl} | {status} | {pct(r['all_40plus'])} ({r['n']}) | {pct(r['40-54']['rate'])} | "
                     f"{pct(r['55-64']['rate'])} | {pct(r['65+']['rate'])} | {v3v} |")
    L += ["", "## Notes", "",
          "- The NHANES definition of chronic cough (most days for three months or more) is narrower than the agent's "
          "question about a cough that does not go away, so the NHANES rates are expected to sit slightly below the "
          "model values. **Calibration (16 October 2026):** the wheeze baselines of the first v3 were about 1.8 times too "
          "low and `leak`, `smoke` and `copd` were updated to NHANES (never 8 %, former 14 %, current 26 %); for cough "
          "the never and former baselines were kept and the current-smoker contribution was raised toward the NHANES "
          "rate (about 30 %).",
          "- Age: chronic cough and phlegm are clearly higher at 65 or more (35 % in current smokers). Symptoms do not "
          "depend on age in the model; an edge from age to the respiratory symptoms could be considered later.",
          "- Only 37 respondents aged 40 or more reported lung cancer, all of them survivors; this cannot be used for "
          "the cancer column.",
          "- NHANES asks about wheeze over the past 12 months, which is close to the agent's question about wheezing "
          "when breathing.",
          "- Dyspnoea is not in the RDQ module of these cycles; the literature value is kept.",
          "- The smoking effect (ratio of current to never) tests the size of the COPD-mediated mechanism in v3: if "
          "the ratio in NHANES is larger than the model's, the `smoke` or `copd` contribution should be raised.",
          "- The association *between* symptoms (cough and wheeze, odds ratio 4.1 in never-smokers without COPD) was "
          "computed from the same data in November 2026 and calibrates the common-cause node of v3.1; see "
          "[`model_v3_1_calibration_fix.md`](model_v3_1_calibration_fix.md)."]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps(res["rates"], indent=1)[:1500])
    print(f"\nReport: {OUT_MD}\nData:   {OUT_JSON}")


if __name__ == "__main__":
    main()
