# Contribution Coefficients — Effect of Each Variable on the Risk Score

This document summarizes how each variable affects the lung cancer risk score in the
hybrid Bayesian Belief Network. All coefficients are multipliers applied to the cancer
**odds**: a value $>1$ increases risk, $<1$ decreases it. Risk factors act on the
**prior** odds (they are causes of cancer), while symptoms act as a **post-observation
Bayesian update** (they are evidence). The distinction is explained in §3–§4.

> Values are computed directly from the model's CPTs (`make explain` / the symptom CPDs
> in `src/model/hybrid_bayesian_network.py`).

---

## 1. Risk factors — *parents of CANCER* (OR; prior-odds multiplier)

| Variable | Type | State | Coefficient | Source |
|---|---|---|---|---|
| AGE | risk factor | (not a single multiplier) | full CPT learned from NLST | NLST data |
| GENDER | risk factor | (not a single multiplier) | NLST CPT | NLST data |
| SMOKING | risk factor | current vs former | NLST CPT (+ pack-year refinement) | NLST data |
| FAMILY_HISTORY | risk factor | yes / no | **×1.70** / ×1.00 | Literature OR (ILCCO, meta-analyses) |
| ASBESTOS | risk factor | yes / no | **×1.50** / ×1.00 | Literature OR |
| AIR_POLLUTION | risk factor | low / moderate / high | ×1.00 / **×1.15** / **×1.30** | Literature OR (PM2.5) |
| (smoking refinement) | risk factor | never-smoker | **×0.15** (down) | epidemiological |

The effect of **AGE / GENDER / SMOKING** is not a single OR but the full CPT learned
from NLST. For example, the baseline $P(\text{cancer})$ for a male current smoker is:
<55 = 1.20%, 55–59 = 2.81%, 60–64 = 4.94%, 65–69 = 8.22%, 70+ = 10.92% — i.e., risk
grows steeply (roughly exponentially) with age.

---

## 2. Symptoms — *children of CANCER* (LR; computed from the CPT)

$\text{LR} = P(\text{symptom state} \mid \text{cancer}=1) / P(\text{symptom state} \mid \text{cancer}=0)$.
These are **computed directly from the CPT cells.** "Present" ($=1$) increases the odds;
"Absent" ($=0$) decreases them.

| Symptom | Confounder | Present (=1) | Absent (=0) |
|---|---|---|---|
| COUGHING | smoking | ×6.00 (former) / ×4.67 (current) | ×0.44 / ×0.35 |
| SHORTNESS_OF_BREATH | smoking | ×6.25 / ×6.00 | ×0.54 / ×0.44 |
| WHEEZING | smoking | ×4.40 / ×4.29 | ×0.82 / ×0.75 |
| CHEST_PAIN | none | ×7.00 | ×0.68 |
| FATIGUE | none | ×2.50 | ×0.62 |
| HEMOPTYSIS | none | **×20.00** | ×0.81 |
| WEIGHT_LOSS | none | ×7.00 | ×0.68 |

> The likelihood ratio of the respiratory symptoms (cough / shortness of breath /
> wheezing) **depends on smoking status** (a confounder); for the others it is constant.
> Haemoptysis is the strongest positive evidence (×20), while its absence is weak (×0.81)
> because it is rare to begin with.

---

## 3. Are OR and LR the same thing? (a common point of confusion)

**Both are odds multipliers, but their origin and role differ:**

| | OR (risk factor, e.g. asbestos ×1.5) | LR (symptom, e.g. cough ×4.67) |
|---|---|---|
| Edge direction | Factor → CANCER (a cause) | CANCER → Symptom (an effect) |
| Acts on | the **prior** odds of cancer | a **post-observation Bayesian update** |
| Where it comes from | an **input** from the literature, used to build the cancer CPT | **computed** from the symptom CPT (ratio of two cells) |
| Interpretation | "Asbestos multiplies the cancer odds by 1.5" | "Observing cough updates the cancer odds by ×4.67" |

So **OR is a parameter (input)** — we set the cancer node's probability using the
literature — while **LR is a result (output)** — derived from the symptom CPT via Bayes.
Asbestos multiplies the odds directly because it is a *cause* of cancer; cough updates
the odds because it is *evidence* of cancer, and Bayes' rule inverts the direction.
Mathematically both behave as multipliers (hence they look similar), but conceptually one
is the "effect of a cause" and the other is the "strength of evidence."

---

## 4. How are risk factors and symptoms distinguished?

Structurally, by **edge direction**: edges pointing **into** the cancer node are risk
factors (causes); edges pointing **out of** it are symptoms (effects). Risk factors set
the prior; symptoms update it as evidence. In code, this distinction is reflected in the
edge directions defined in `get_hybrid_structure()`, and between `RISK_FACTOR_ORS` (the
ORs) and `build_symptom_cpds` (the CPTs from which the LRs are derived).
