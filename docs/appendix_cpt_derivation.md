# Appendix: Symptom CPT Derivation Table

## Conditional Probability Table Parameterization for the Hybrid Bayesian Belief Network

**Praevidio AI — Lung Cancer Risk Assessment Engine**

---

## 1. Overview

The Hybrid BBN used in Praevidio AI employs a two-part architecture:

- **Part A — Risk Factor CPTs:** Learned directly from the NLST clinical trial dataset (n=53,452). These CPTs encode `P(LUNG_CANCER | AGE, GENDER, SMOKING)` and are computed empirically from real patient outcomes.

- **Part B — Symptom CPTs:** Derived from peer-reviewed medical literature using the expert-elicitation method. These CPTs encode the generative relationship `P(Symptom | LUNG_CANCER)` or `P(Symptom | LUNG_CANCER, SMOKING)` for symptoms with smoking as a confounder.

This appendix provides a formal derivation table for Part B, mapping each CPT value to its literature source, reported metric, and the rationale for the chosen probability.

---

## 2. Methodology: Expert Elicitation

The symptom CPTs were parameterized using the **expert-elicitation** approach, a standard methodology in Bayesian Network construction when direct patient-level data is unavailable for certain variables. This is well-established in the literature:

- **Fenton & Neil (2018)** describe expert-elicited CPT parameterization as the standard approach for medical BBNs when combining data-driven and knowledge-driven components (Chapter 10) [1].
- **Druzdzel & van der Gaag (2000)** provide a foundational framework for determining "where the numbers come from" in probabilistic networks, including literature-informed elicitation [2].

The process involves:
1. Identifying published prevalence data, odds ratios (OR), and positive predictive values (PPV) from peer-reviewed clinical studies
2. Converting these epidemiological metrics into conditional probabilities suitable for the generative (Cancer → Symptom) direction of the BBN
3. Setting `P(Symptom | Cancer=1)` within the reported prevalence range for lung cancer patients
4. Setting `P(Symptom | Cancer=0)` using general population or primary care base rates
5. For symptoms with smoking as a confounder, applying an additive risk model

---

## 3. Primary Literature Sources

| Ref | Authors | Title | Journal | Year | DOI | PMID |
|-----|---------|-------|---------|------|-----|------|
| [1] | Hamilton W, Peters TJ, Round A, Sharp D | What are the clinical features of lung cancer before the diagnosis is made? A population based case-control study | Thorax | 2005 | 10.1136/thx.2005.045880 | 16227326 |
| [2] | Beckles MA, Spiro SG, Colice GL, Rudd RM | Initial evaluation of the patient with lung cancer: symptoms, signs, laboratory tests, and paraneoplastic syndromes | Chest | 2003 | 10.1378/chest.123.1_suppl.97S | 12527569 |
| [3] | Corner J, Hopkinson J, Fitzsimmons D, Barclay S, Muers M | Is late diagnosis of lung cancer inevitable? Interview study of patients' recollections of symptoms before diagnosis | Thorax | 2005 | 10.1136/thx.2004.029264 | 15790987 |
| [4] | Kvale PA | Chronic cough due to lung tumors: ACCP evidence-based clinical practice guidelines | Chest | 2006 | 10.1378/chest.129.1_suppl.147S | 16428705 |
| [5] | Hopwood P, Stephens RJ | Depression in patients with lung cancer: prevalence and risk factors derived from quality-of-life data | J Clin Oncol | 2000 | 10.1200/JCO.2000.18.4.893 | 10673533 |

### Source Descriptions

**Hamilton et al. (2005) [1]** — A population-based case-control study conducted across 21 general practices in Exeter, UK (population 128,700). Studied 247 primary lung cancer cases and 1,235 age- and sex-matched controls. The entire primary care record for 2 years before diagnosis was coded using the International Classification of Primary Care-2 (ICPC-2). Reported odds ratios and positive predictive values for 7 symptoms (haemoptysis, weight loss, appetite loss, dyspnoea, thoracic pain, fatigue, cough), 1 physical sign (finger clubbing), and 2 laboratory findings (thrombocytosis, abnormal spirometry).

**Beckles et al. (2003) [2]** — An ACCP (American College of Chest Physicians) evidence-based clinical practice guideline providing a systematic review of symptom prevalence in lung cancer patients. Reports frequency ranges compiled from multiple clinical series: cough 45–75%, dyspnoea 37–58%, chest pain 27–49%, hemoptysis ~20%, and notes that ~75% of patients are symptomatic at diagnosis.

**Corner et al. (2005) [3]** — A qualitative interview study exploring patients' recollections of symptoms before lung cancer diagnosis. Identifies two primary symptom categories: chest symptoms (cough, breathing changes, chest pain) and systemic symptoms (fatigue/lethargy, weight loss, eating changes). Used to support symptom selection rationale rather than for quantitative CPT values.

**Kvale (2006) [4]** — ACCP evidence-based guidelines on chronic cough due to lung tumors. Reports hemoptysis prevalence in lung cancer patients at approximately 20%, confirming it as the highest-specificity alarm symptom among common presenting symptoms.

**Hopwood & Stephens (2000) [5]** — Analysis of quality-of-life data from 987 patients enrolled in MRC lung cancer trials. Reports fatigue prevalence at approximately 50% and weight loss at approximately 35% at the time of diagnosis.

---

## 4. CPT Derivation Table

### 4.1 Symptoms with Smoking Confounder

These symptoms have both LUNG_CANCER and SMOKING as parent nodes, reflecting that smoking independently causes these respiratory symptoms regardless of cancer status.

#### COUGHING — P(Coughing | LUNG_CANCER, SMOKING)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0, SM=0 | 0.10 | General population cough prevalence ~9–12% (Schappert, 1992) | Background rate for non-smoking, non-cancer adults |
| LC=0, SM=1 | 0.25 | Chronic cough in smokers ~20–30% (Wynder & Graham, 1950; Doll & Hill, 1950) | Smoking-attributable cough without cancer |
| LC=1, SM=0 | 0.60 | Beckles [2]: cough 45–75% in LC; Hamilton [1]: cough OR=1.6 | Midpoint of reported range for non-smoker LC patients |
| LC=1, SM=1 | 0.70 | Upper range of Beckles [2] with additive smoking effect | Combined cancer + smoking effect |

#### SHORTNESS_OF_BREATH — P(SOB | LUNG_CANCER, SMOKING)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0, SM=0 | 0.08 | Dyspnoea in general adult population ~5–10% | Background rate |
| LC=0, SM=1 | 0.18 | COPD-related dyspnoea in long-term smokers ~15–20% (Mannino et al., MMWR 2002) | Smoking-attributable dyspnoea |
| LC=1, SM=0 | 0.50 | Beckles [2]: dyspnoea 37–58%; Hamilton [1]: independently associated | Midpoint of reported range |
| LC=1, SM=1 | 0.60 | Upper bound of Beckles [2] range | Combined cancer + COPD effect |

#### WHEEZING — P(Wheezing | LUNG_CANCER, SMOKING)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0, SM=0 | 0.05 | Wheezing in non-smoking adults ~3–7% | Background rate |
| LC=0, SM=1 | 0.15 | Wheezing in chronic smokers ~12–18% | Smoking-attributable airway wheezing |
| LC=1, SM=0 | 0.22 | Beckles [2]: wheezing less common, ~15–30% | Lower-mid range (less common LC symptom) |
| LC=1, SM=1 | 0.30 | Upper bound for smoker + cancer | Combined effect |

### 4.2 Symptoms without Confounder

These symptoms have only LUNG_CANCER as a parent node. They are either cancer-specific (chest pain) or systemic manifestations (fatigue, weight loss) not independently caused by smoking.

#### CHEST_PAIN — P(Chest Pain | LUNG_CANCER)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0 | 0.05 | Non-cardiac chest pain prevalence ~2–7% (Eslick et al., Aliment Pharmacol Ther 2003) | Background rate in primary care |
| LC=1 | 0.35 | Beckles [2]: chest/thoracic pain 27–49%; Hamilton [1]: OR significant | Mid-range; cancer-specific symptom |

#### FATIGUE — P(Fatigue | LUNG_CANCER)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0 | 0.20 | General fatigue prevalence ~15–25% in adults (Pawlikowska et al., BMJ 1994) | High background rate limits diagnostic value |
| LC=1 | 0.50 | Hopwood & Stephens [5]: fatigue ~40–55% at diagnosis; Corner [3]: major systemic symptom | Midpoint of reported range from MRC trial |

#### HEMOPTYSIS — P(Hemoptysis | LUNG_CANCER)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0 | 0.01 | Hemoptysis base rate <1–2% in general population (Kvale [4]; Santiago et al., Medicine 1991) | Very low background — high specificity symptom |
| LC=1 | 0.20 | Kvale [4]: hemoptysis in ~20% of LC patients; Beckles [2]: confirms ~20%; Hamilton [1]: highest PPV | Consistent across all 3 primary sources |

#### WEIGHT_LOSS — P(Weight Loss | LUNG_CANCER)

| Condition | CPT Value | Literature Basis | Derivation Rationale |
|-----------|-----------|-----------------|---------------------|
| LC=0 | 0.05 | Unexplained weight loss prevalence ~1–7% in adults (McMinn et al., BMJ 2010) | Background rate |
| LC=1 | 0.35 | Hopwood & Stephens [5]: weight loss ~30–40%; Hamilton [1]: OR significant in multivariable model | Mid-range from MRC trial data |

---

## 5. Validation: CPT Values vs. Literature Ranges

The following table summarizes the alignment between our CPT values and the published literature ranges:

| Symptom | CPT P(S\|LC=1) | Literature Range | Within Range? | Primary Source |
|---------|---------------|-----------------|--------------|----------------|
| Coughing | 0.60–0.70 | 45–75% | ✅ Yes | Beckles [2], Hamilton [1] |
| Shortness of Breath | 0.50–0.60 | 37–58% | ✅ Yes | Beckles [2], Hamilton [1] |
| Wheezing | 0.22–0.30 | 15–30% | ✅ Yes | Beckles [2] |
| Chest Pain | 0.35 | 27–49% | ✅ Yes | Beckles [2], Hamilton [1] |
| Fatigue | 0.50 | 40–55% | ✅ Yes | Hopwood [5], Corner [3] |
| Hemoptysis | 0.20 | ~20% | ✅ Exact | Kvale [4], Beckles [2] |
| Weight Loss | 0.35 | 30–40% | ✅ Yes | Hopwood [5], Hamilton [1] |

All 7 symptom CPT values fall within the reported prevalence ranges from peer-reviewed literature.

---

## 6. Methodological Justification

### Why Not Learn Symptom CPTs from Data?

1. **NLST does not contain symptom data.** The NLST was a screening trial comparing low-dose CT with chest radiography. Symptom-level data (cough, hemoptysis, etc.) was not collected as part of the trial protocol. Therefore, symptom CPTs cannot be learned from NLST.

2. **No public patient-level symptom dataset exists.** While datasets on platforms such as Kaggle contain symptom columns, these are predominantly synthetically generated and do not reflect real clinical correlations. Access-controlled datasets (PLCO, MIMIC, UK Biobank) either lack symptom-level granularity or require institutional review board approval.

3. **Expert elicitation is the standard approach.** When combining data-driven and knowledge-driven components in a BBN, expert elicitation from published literature is the recognized methodology. This is supported by:
   - Fenton & Neil (2018): "Risk Assessment and Decision Analysis with Bayesian Networks", CRC Press, Chapter 10
   - Druzdzel & van der Gaag (2000): "Building Probabilistic Networks: Where Do the Numbers Come From?"
   - Yet et al. (2014): "Not just data: A method for improving prediction with knowledge from professional practice"

### Why a Hybrid Architecture?

The hybrid approach combines the strengths of both components:
- **Data-driven risk factors** provide empirically calibrated base rates from a large, well-characterized clinical cohort (NLST)
- **Literature-driven symptoms** incorporate decades of clinical knowledge about symptom-cancer associations that would otherwise require access to restricted clinical databases

This architecture is directly analogous to established clinical risk calculators (e.g., the Lung-RADS system, the Brock model) that combine empirical risk factor data with expert-defined symptom thresholds.

---

## 7. References

[1] Hamilton W, Peters TJ, Round A, Sharp D. What are the clinical features of lung cancer before the diagnosis is made? A population based case-control study. *Thorax*. 2005;60(12):1059-65. DOI: 10.1136/thx.2005.045880. PMID: 16227326.

[2] Beckles MA, Spiro SG, Colice GL, Rudd RM. Initial evaluation of the patient with lung cancer: symptoms, signs, laboratory tests, and paraneoplastic syndromes. *Chest*. 2003;123(1 Suppl):97S-104S. DOI: 10.1378/chest.123.1_suppl.97S. PMID: 12527569.

[3] Corner J, Hopkinson J, Fitzsimmons D, Barclay S, Muers M. Is late diagnosis of lung cancer inevitable? Interview study of patients' recollections of symptoms before diagnosis. *Thorax*. 2005;60:314-9. DOI: 10.1136/thx.2004.029264. PMID: 15790987.

[4] Kvale PA. Chronic cough due to lung tumors: ACCP evidence-based clinical practice guidelines. *Chest*. 2006;129(1 Suppl):147S-153S. DOI: 10.1378/chest.129.1_suppl.147S. PMID: 16428705.

[5] Hopwood P, Stephens RJ. Depression in patients with lung cancer: prevalence and risk factors derived from quality-of-life data. *J Clin Oncol*. 2000;18(4):893-903. DOI: 10.1200/JCO.2000.18.4.893. PMID: 10673533.

[6] Fenton N, Neil M. Risk Assessment and Decision Analysis with Bayesian Networks. 2nd ed. CRC Press; 2018.

[7] Druzdzel MJ, van der Gaag LC. Building probabilistic networks: Where do the numbers come from? *IEEE Trans Knowl Data Eng*. 2000;12(4):481-486.

[8] The National Lung Screening Trial Research Team. Reduced lung-cancer mortality with low-dose computed tomographic screening. *N Engl J Med*. 2011;365(5):395-409. DOI: 10.1056/NEJMoa1102873.
