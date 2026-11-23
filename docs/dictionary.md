# Praevidio AI: glossary

Short definitions of the clinical, modelling and engineering terms used in the project, each with a note on how
Praevidio uses it. Parameters and sources are in [`model_parameters.md`](model_parameters.md).

## Clinical and epidemiological terms

**Lung cancer screening, LDCT (low-dose computed tomography).** A yearly low-radiation CT scan offered to people at
high risk who have no symptoms. NLST showed that it reduces lung cancer mortality. *In Praevidio:* the action
behind the 6-year layer; a result at or above the screening threshold directs the user to ask about screening.

**NLST (National Lung Screening Trial).** US trial of 53,452 people at high risk (age 55 to 74, at least 30
pack-years, current smokers or quit within 15 years). *In Praevidio:* the cancer node of the Bayesian network is
learned from its public subset. Because NLST has no never-smokers, no one under 55 and no light smokers, it no
longer sets the 6-year risk in v3.1.

**PLCOm2012.** Logistic model of the 6-year risk of lung cancer in ever-smokers (Tammemägi 2013), built on the PLCO
trial and used internationally to select people for screening; threshold 1.51 %. *In Praevidio:* the 6-year layer
for anyone who has smoked.

**Wakelee 2007.** Pooled incidence of lung cancer in never-smokers from six cohorts. *In Praevidio:* the 6-year
layer for never-smokers.

**USPSTF 2021 criteria.** US recommendation for LDCT screening: age 50 to 80, at least 20 pack-years, current
smoker or quit within 15 years. *In Praevidio:* shown as screening eligibility beside the risk.

**NICE NG12.** UK guideline on recognising and referring suspected cancer. For lung cancer it recommends an urgent
chest X-ray from age 40 for two or more unexplained symptoms, or one in an ever-smoker, and urgent referral for
haemoptysis; its general principle is to act at a positive predictive value of 3 %. *In Praevidio:* the rule is
applied as written, and 3 % is the threshold of the symptom layer.

**PPV (positive predictive value).** Among people with a given finding, the share who have the disease. *In
Praevidio:* the symptom layer is a model estimate of this quantity; Hamilton 2005 supplies measured values.

**Hamilton 2005.** Case-control study in UK primary care giving the PPV of single symptoms and pairs for lung
cancer (for example haemoptysis 2.4 %). *In Praevidio:* the source of upper bounds on how much symptoms may raise
the odds (the "Hamilton envelope", tested for all 127 symptom combinations).

**NHANES.** US national health survey. *In Praevidio:* cycles 2007 to 2012 give how common chronic cough and
wheeze are in people without cancer and how strongly they occur together.

**Pack-year.** Cumulative smoking dose: packs per day times years smoked. One pack a day for 30 years is 30
pack-years. *In Praevidio:* used for screening eligibility; the agent itself speaks in the user's terms ("10
cigarettes a day for 10 years") and explains the word on request.

**COPD (chronic obstructive pulmonary disease).** Chronic lung disease, mostly caused by smoking, that produces
cough, breathlessness and wheeze. *In Praevidio:* both a risk factor for lung cancer and an alternative
explanation for the respiratory symptoms.

**Haemoptysis.** Coughing up blood. The most specific symptom of lung cancer. *In Praevidio:* the strongest single
symptom (it multiplies the odds by about 7.7) and a reason for prompt assessment at any age.

**ASR (age-standardised rate).** Incidence adjusted for age structure so that populations can be compared, usually
per 100,000. *In Praevidio:* used to state the burden of lung cancer in Türkiye.

**KETEM.** Cancer Early Diagnosis, Screening and Training Centres of the Turkish Ministry of Health. *In
Praevidio:* where a user is directed to ask about screening.

**ICD-10.** International classification of diseases and symptoms (R05 cough, R04.2 haemoptysis, C34 malignant
neoplasm of bronchus and lung). *In Praevidio:* reported symptoms are coded in the physician report.

## The result

**6-year layer.** Probability of a lung cancer diagnosis within six years from risk factors alone. Bands: below
1.5 % (below the screening threshold), 1.5 to 5 % (moderate), 5 % or more (high). It answers "should I be
screened?".

**Symptom layer.** Probability that the present symptoms are caused by lung cancer:
P(cancer | evidence) × P(symptomatic | cancer, evidence). Compared with 3 %. It answers "should I see a doctor
about my symptoms?".

**Full score.** The posterior probability with risk factors and symptoms together. It mixes a six-year horizon
with the present, so it is reported in the physician report as a number without a band.

**Prompt physician assessment.** Advised when the NICE NG12 rule applies, or the symptom layer is 3 % or more, or
haemoptysis is reported at any age.

**Relative risk and natural frequency.** The same risk expressed against a peer ("34 times that of a never-smoker
of your age") and as a count ("about 42 in 10,000 people like you, about 1.2 among such peers"). *In Praevidio:*
both are given together, because a relative risk alone alarms and a small percentage alone is dismissed.

**Projection.** For current smokers, the 6-year risk at age 50, or five years ahead, if they continue and if they
quit today.

## Modelling

**Bayesian network (Bayesian belief network).** A graph of variables joined by directed edges, each with a table
of conditional probabilities; given evidence it computes the probability of the unobserved variables. *In
Praevidio:* risk factors point into the cancer node, the cancer node points to the symptoms through a latent
*symptomatic* node, and COPD and *other illness* are competing causes of symptoms. Missing answers are
marginalised, which is why "not asked" differs from "no".

**CPT (conditional probability table).** The table of a node's probabilities for every state of its parents.

**Latent node.** A variable that is never observed and only inferred. *In Praevidio:* `SYMPTOMATIC` (does the
future cancer cause symptoms today?) and `OTHER_ILLNESS` (is some other illness producing symptoms?).

**Symptomatic fraction, q.** P(symptomatic today | diagnosis within six years), 0.35. It reconciles the six-year
horizon of the risk factors with the present tense of the symptoms.

**Noisy-OR.** A way to combine several independent causes of one effect: the effect is absent only if every cause
fails to produce it. *In Praevidio:* each respiratory symptom has a background rate and contributions from
smoking, COPD, other illness and cancer.

**Common cause.** A shared parent that makes its children correlated. *In Praevidio:* `OTHER_ILLNESS` makes
symptoms occur together in people without cancer, so several symptoms at once are no longer treated as
independent pieces of evidence.

**Explaining away.** When an effect has two possible causes, evidence for one lowers the probability of the
other. *In Praevidio:* a COPD diagnosis explains part of a cough and lowers its weight toward cancer. In v2 this
effect acted through smoking in an uncontrolled way; from v3 on it is modelled on purpose.

**Odds, odds ratio (OR), likelihood ratio (LR).** Odds = p / (1 − p). An OR says how much a risk factor multiplies
the odds of disease; an LR says how much a finding multiplies them. *In Praevidio:* risk factors outside
PLCOm2012 enter as ORs; the effect of the symptoms is the LR computed from the network.

**Normalised odds ratio.** An OR divided by its population average, so that an average or unasked person stays at
the base rate.

**Calibration.** Agreement between predicted probabilities and observed frequencies. *In Praevidio:* the aim of
the model, since it reports a risk and not a diagnosis; checked against external references and by plausibility
tests.

**Sensitivity analysis.** Varying one parameter at a time to see how much the results depend on it
([`sensitivity_v3.md`](sensitivity_v3.md)).

**Regression baseline.** A frozen set of outputs (43 profiles under v3.0) against which every later change is
compared.

**AUC-ROC, AUPRC, Brier score, ECE, decision curve analysis.** Measures of discrimination (does a higher-risk
person get a higher score?), calibration and clinical usefulness. *In Praevidio:* computed for the risk-factor
layer on an NLST hold-out (`make eval`). Accuracy and F1 are not used, because the model does not classify.

**Shapley value.** A fair, order-independent share of a score attributed to each finding. *In Praevidio:* used in
the spring explainability notes for v2 ([`history/`](history/)).

## Conversation and engineering

**State machine.** A program that is always in one of a fixed set of states and moves between them by explicit
rules. *In Praevidio:* the interview (demographics, confirmation, symptoms, risk factors, result).

**Slot extraction.** Turning a free sentence into a fixed set of fields. *In Praevidio:* `keyword` mode does it
with Turkish rules offline, `llm` mode with GPT-4o-mini followed by guards.

**Side question.** A question the user asks in place of an answer ("what does this mean?"). The agent answers from
a fixed glossary and repeats its own question.

**STT, TTS.** Speech-to-text and text-to-speech.

**PWA (progressive web app).** A web page that can be installed on a phone's home screen and behaves like an app.

**Transcript and replay.** Every conversation is stored as `agent:` and `user:` lines and can be replayed against
the current agent; recorded cases serve as regression tests.

**SUS, SUS-TR.** System Usability Scale, a ten-item questionnaire giving a score from 0 to 100, and its validated
Turkish translation.

**Cohen's kappa (weighted).** Agreement between two raters beyond chance, with partial credit for near misses. *In
Praevidio:* agreement between the model's and the expert's recommended action.
