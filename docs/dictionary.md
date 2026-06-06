# Praevidio AI — Glossary of Terms

Short definitions of the technical and clinical terms used in the project, plus
**how we use each one** in Praevidio.

---

## Clinical / Epidemiological

**LDCT (Low-Dose Computed Tomography)**
The gold-standard lung cancer screening test, using a low radiation dose. NLST
showed that LDCT screening reduces mortality in high-risk individuals.
*In Praevidio:* the target action — when risk is high or the screening flag fires,
we direct the user to LDCT via a physician / KETEM.

**NLST (National Lung Screening Trial)**
A large US screening trial of 53,452 participants, all high-risk (age 55–74,
≥30 pack-years, current or recent former smokers).
*In Praevidio:* we learn the risk-factor base (age, gender, smoking → cancer
probability) from real NLST data. **Key limitation:** NLST has no never-smokers
and no one under 55, so we add epidemiological estimates for those groups.

**ASR (Age-Standardized Rate)**
An incidence/mortality rate adjusted for age structure so different populations
can be compared fairly (usually per 100,000). *In Praevidio:* used in the
motivation to state Turkey's lung cancer burden (male ASR ~68/100,000).

**Pack-year**
Cumulative smoking dose = (cigarettes per day / 20) × years smoked. E.g. 1 pack/day
× 30 years = 30 pack-years. *In Praevidio:* used for (1) screening eligibility
(≥20 pack-years) and (2) smoking refinement of the risk score (down-adjust
never-smokers; treat heavy recent quitters like active smokers).

**Hemoptysis**
Coughing up blood / blood-streaked sputum. One of the most specific (alarm)
symptoms of lung cancer. *In Praevidio:* the strongest positive symptom
(likelihood ratio ≈ ×20).

**KETEM**
Cancer Early Diagnosis, Screening and Training Center (Turkish Ministry of Health).
*In Praevidio:* the referral destination for high-risk / screening-eligible users.

---

## Coding Standards

**ICD-10 (International Classification of Diseases, 10th revision)**
International standard codes for diseases and symptoms (e.g. R05 = cough,
C34 = malignant neoplasm of bronchus/lung). *In Praevidio:* we map every symptom
and finding to ICD-10 to produce a "doctor-ready" report; RAG maps free text to codes.

**ICD-O-3 (ICD for Oncology, 3rd revision)**
Oncology-specific coding for tumor topography (site) and morphology (cell type).
*In Praevidio:* referenced for oncology-standard compatibility of the report; not
used directly in the risk score.

---

## Modeling

**BBN (Bayesian Belief Network)**
A probabilistic graphical model that represents causal relationships between
variables with directed edges and conditional probabilities, and computes outcome
probabilities via Bayes' rule given evidence. *In Praevidio:* the core engine.
Structure: risk factors → CANCER → symptoms. The cancer node is latent; we compute
P(cancer | evidence). Advantage: not a black box — every relationship is explainable.

**CPT (Conditional Probability Table)**
A table holding a node's probabilities for each state of its parents
(e.g. P(cough | cancer, smoking)). *In Praevidio:* risk-factor CPTs are learned
from NLST data; symptom CPTs are derived from peer-reviewed literature via expert
elicitation.

**Odds**
The ratio of "happening / not happening": odds = p / (1 − p). Ranges 0 to ∞ and can
be multiplied freely. *In Praevidio:* the mathematical basis for combining evidence
— since probabilities can't be multiplied directly, we multiply in odds space.

**Odds Ratio (OR) / Likelihood Ratio (LR)**
How much a factor/finding multiplies the cancer odds. OR is typically used for risk
factors (e.g. family history OR≈1.70); LR for diagnostic findings. *In Praevidio:*
new risk factors enter as literature ORs multiplied onto the NLST base; each symptom's
LR updates the odds. (OR is an **input parameter** on the prior; LR is **computed from
the symptom CPT** as evidence — see `proje_sorulari_cevaplari.md` §L.)

**Generative structure / Naive-Bayes direction**
Modeling in the disease → symptom direction ("if cancer, the probability of cough
is …"). *In Praevidio:* the medical-BBN standard; at inference we run Bayes in reverse.

**Explaining-away**
When a symptom has two causes, observing one cause lowers the probability of the
other. *In Praevidio:* since smoking causes both cancer and cough, a smoker's cough
could be "explained" by smoking and wrongly lower cancer probability; we fixed this
by calibrating the CPTs via sensitivity analysis. (The 3 new factors don't have this
issue — they connect only to cancer, not to symptoms.)

**Shapley value**
A game-theory method that assigns each factor an **order-independent, fair
contribution**, averaged over all factor orderings. *In Praevidio:* used to fairly
answer "how much did each finding contribute to this patient's score?" (explainability).

**Calibration**
Agreement between predicted probability and observed frequency ("when we say 15%,
is it really ~15%?"). *In Praevidio:* the primary goal, since we produce a calibrated
risk, not a diagnosis.

---

## Performance Metrics (instead of F1)

> Why not F1? The goal is not diagnosis (a binary class) but a **calibrated risk**.
> F1 forces the continuous probability onto a threshold and is misleading under the
> ~3.85% base-rate imbalance.

**AUC-ROC (Area Under the ROC Curve)**
Discrimination: the model's ability to **rank** a higher-risk case above a lower-risk
one. 0.5 = chance, 1.0 = perfect; threshold-independent. *In Praevidio:* primary
discrimination metric.

**AUPRC / PR-AUC (Area Under the Precision-Recall Curve)**
A discrimination metric more informative than AUC-ROC under class imbalance (focused
on the positive class). *In Praevidio:* reported alongside AUC-ROC because the base
rate is 3.85%.

**Brier score**
Mean squared error of the probability prediction (0 = perfect, lower = better).
Summarizes both discrimination and calibration. *In Praevidio:* the single-number
summary of calibration.

**ECE (Expected Calibration Error)**
The weighted average gap between predicted probability and observed frequency.
*In Praevidio:* reduces the calibration curve to a single number.

**Reliability curve (calibration curve)**
x: predicted risk, y: observed frequency. Ideal = the 45° line. *In Praevidio:*
visualizes whether the model is systematically over- or under-confident.

**DCA (Decision Curve Analysis) / Net Benefit**
"Does using this score provide net benefit over screen-everyone / screen-no-one?"
The modern clinical-utility standard for screening tools. *In Praevidio:* used to
justify threshold choice and clinical value.

**Sensitivity / Specificity**
Sensitivity = catching true positives; specificity = excluding true negatives.
*In Praevidio:* reported as operating points at the chosen thresholds (5%, 15%);
given the screening goal, sensitivity is prioritized.
