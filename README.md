# Praevidio AI 🩺

> **Praevidio** (Latin for *foreseeing*): An Intelligent Voice-Driven Platform for Lung Cancer Risk Analysis and Early Awareness in Turkey.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![pgmpy](https://img.shields.io/badge/pgmpy-1.0-orange?style=flat)
![License](https://img.shields.io/badge/License-AGPL_v3-blue.svg)

---

## 🚀 Overview

Praevidio AI is a hybrid AI system that combines **Large Language Models (LLMs)** with a **Bayesian Belief Network (BBN)** to perform voice-driven lung cancer risk assessment. It converts natural language symptom descriptions into structured clinical insights coded in **ICD-10** standards, generating "Doctor-Ready" reports to support early intervention.

**Why Lung Cancer?**
- Most common cancer & leading cause of cancer death among men in Turkey (ASR: 68.0/100,000)
- Over **50% of cases** are diagnosed at Stage 4 (metastatic) — early intervention is critical
- Core symptoms (cough, shortness of breath, wheezing) are highly suited for voice-based description
- **64.6%** of Turkey's population has inadequate health literacy — voice interface improves accessibility

## ✨ Key Features

* **🎙️ Voice-Activated Symptom Intake:** Turkish-optimized Speech-to-Text (Whisper) for natural symptom description, accessible to all age groups and literacy levels.
* **💬 Conversational Agent (v2):** Cascade speech pipeline (STT → LLM slot-filling → TTS) that greets the user, collects demographics, asks symptoms in sequence, gathers risk factors, then delivers a spoken risk summary and a downloadable PDF.
* **🧬 Extended Risk Factors (v2):** Adds family history, occupational/asbestos exposure, and provincial air-pollution (PM2.5) — each integrated as a literature-based odds-ratio multiplier on the NLST base, with per-factor explainability.
* **🫁 Screening Eligibility (v2):** A symptom-independent LDCT screening flag (USPSTF/NLST: age 50–80, ≥20 pack-years, current or quit ≤15y). Ensures a high-risk asymptomatic smoker is still directed to screening even when the symptom-based score is low — serving the project's "more screening, earlier diagnosis" goal.
* **🚬 Pack-Year Smoking Refinement (v2):** The risk score uses smoking *dose* (pack-years), not just current/former: never/very-light smokers are no longer pinned to the NLST heavy-former-smoker base (down-adjusted), and heavy recent quitters (≥20 pack-years, quit ≤15y) are treated like active smokers — matching NLST's own high-risk definition.
* **🧠 Hybrid Risk Engine:** Bayesian Belief Network (BBN) for explainable, probabilistic risk scoring — no black-box predictions.
* **🔍 RAG-Powered ICD-10 Mapping:** Retrieval-Augmented Generation maps verbal symptoms to international medical codes (ICD-10/ICD-O-3).
* **📄 Doctor-Ready PDF Reports:** Generates structured clinical summaries with ICD-10 coded findings, risk categories, and bilingual recommendations (TR/EN).
* **📍 KETEM Integration (Planned):** Directs high-risk users to the nearest Cancer Early Diagnosis, Screening, and Training Center.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              PRAEVIDIO AI  (v2)                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  💬 CASCADE CONVERSATIONAL AGENT  (src/conversation/voice_agent.py)        │
│  ┌────────────┐   🎤 mic    ┌──────────────┐    ┌─────────────────────┐    │
│  │ TTS prompt │ ─────────▶ │  Whisper STT  │──▶ │ GPT-4o-mini / keyword│    │
│  │ (greeting) │            │  (Turkish)    │    │  slot-filling        │    │
│  └────────────┘            └──────────────┘    └──────────┬──────────┘    │
│   greeting → demographics(age/gender/smoking) → 7 symptoms │ → risk factors │
│                                                            ▼                │
│   province ──▶ tr_il_pm25.json (IQAir) ──▶ AIR_POLLUTION   evidence dict     │
│                                                            │                │
│                                                            ▼                │
│   ┌──────────────────────────────────────────────────────────────────┐    │
│   │              HYBRID BAYESIAN BELIEF NETWORK  (pgmpy)              │    │
│   │  Part A  — Risk factors from NLST (n=53,452):                    │    │
│   │            P(Cancer | AGE, GENDER, SMOKING)                       │    │
│   │  Part A2 — New factors, literature odds-ratio × NLST base:        │    │
│   │            FAMILY_HISTORY ×1.70 · ASBESTOS ×1.50 ·                │    │
│   │            AIR_POLLUTION ×1.15/1.30  (calibrated, construct-valid)│    │
│   │  Part B  — 7 symptom CPTs from peer-reviewed literature           │    │
│   │            (SMOKING confounder on respiratory symptoms)           │    │
│   │            14 nodes, 16 edges                                     │    │
│   └───────────────────────────────┬──────────────────────────────────┘    │
│                                    ▼                                        │
│            ┌────────────────────────────────────────────┐                  │
│            │  Risk Score (0–100%) + level + ICD-10 +     │                  │
│            │  per-factor OR explainability               │                  │
│            └───────────────┬───────────────┬────────────┘                  │
│                            ▼               ▼                                │
│              🔊 Spoken summary (TTS)   📄 Doctor-Ready PDF                  │
│              (soft, screening-oriented)  (TR/EN, risk drivers)             │
│                                                                            │
│  📈 Evaluation (src/model/evaluation.py): AUC-ROC · AUPRC · calibration    │
│     (Brier/ECE/reliability) · Decision Curve Analysis  — NOT F1            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Pipeline stages:**
1. **Conversational intake:** The cascade agent greets the user (TTS), then collects demographics, symptoms (in sequence), and risk factors over multiple turns. Each answer is transcribed by Whisper and parsed into structured evidence (GPT-4o-mini or keyword).
2. **Province → air pollution:** The stated province is mapped to a provincial PM2.5 tier (`tr_il_pm25.json`, IQAir 2023–2025) → `AIR_POLLUTION` evidence.
3. **Evidence → Risk Score:** The Hybrid BBN performs probabilistic inference `P(Lung Cancer | Evidence)`. New risk factors enter as literature odds-ratio multipliers on the NLST base (no explaining-away — they are pure cancer parents).
4. **Spoken summary + report:** A soft, screening-oriented summary is spoken back (TTS), and a bilingual Doctor-Ready PDF is generated with ICD-10 findings and per-factor risk drivers.
5. **Evaluation:** Discrimination + calibration + clinical-utility metrics (AUC-ROC, AUPRC, Brier, ECE, reliability curve, Decision Curve Analysis) — replacing F1/accuracy as primary.

> *RAG (ChromaDB) still provides ICD-10 retrieval for the knowledge base; it is omitted from the diagram above for clarity.*

---

## 🛠️ Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------| 
| **Speech-to-Text** | OpenAI Whisper | Turkish voice transcription |
| **Text-to-Speech** | OpenAI TTS (`tts-1`) | Spoken prompts & risk summary (cascade agent) |
| **LLM** | GPT-4o-mini | Symptom + risk-factor slot extraction (cost-efficient) |
| **Vector DB** | ChromaDB (dev) | ICD-10 knowledge retrieval |
| **Probabilistic Model** | pgmpy (Hybrid BBN) | Explainable risk scoring |
| **Clinical Data** | NLST (n=53,452) | Real-world risk factor CPTs |
| **Data Science** | pandas, scikit-learn, seaborn | EDA & model evaluation |
| **Report Gen** | Jinja2, WeasyPrint | PDF report generation |
| **Clinical Standards** | ICD-10, ICD-O-3 | International medical coding |
| **Language** | Python 3.12 | Core development |

---

## 📂 Project Structure

```
Praevidio-AI/
├── src/
│   ├── config.py                          # Centralized configuration & model settings
│   ├── pipeline.py                        # End-to-end CLI (STT → NLP → RAG → BBN → PDF)
│   ├── data_preprocessing.py              # Kaggle data cleaning & ICD-10 mapping
│   ├── nlst_data_preprocessing.py         # NLST clinical data merge & normalization
│   ├── model/
│   │   ├── bayesian_network.py            # Original BBN (Kaggle data, 15 nodes)
│   │   ├── hybrid_bayesian_network.py     # Hybrid BBN v2 (NLST + literature + 3 new factors, 14 nodes)
│   │   ├── hybrid_bayesian_network_v3.py  # v3: latent symptomatic + COPD + OR normalisation + NICE alarm (Fall 2026)
│   │   ├── calibrate_risk_factors.py      # New-factor OR calibration & sensitivity analysis
│   │   ├── explainability.py              # Shapley contributions + context-dependence + waterfall
│   │   ├── screening.py                   # LDCT screening eligibility (USPSTF/NLST) — symptom-independent
│   │   └── evaluation.py                  # Risk-appropriate metrics (AUC, calibration, DCA) — not F1
│   ├── conversation/
│   │   └── voice_agent.py                 # Cascade conversational agent (STT→LLM→TTS state machine)
│   ├── stt/
│   │   └── whisper_stt.py                 # Whisper STT + Turkish medical term correction
│   ├── nlp/
│   │   └── symptom_extractor.py           # Keyword + GPT-4o-mini extraction (symptoms, demographics, new factors, province→PM2.5)
│   ├── rag/
│   │   └── rag_pipeline.py                # ChromaDB indexer + semantic ICD-10 retrieval
│   └── report/
│       ├── report_generator.py            # Jinja2 → WeasyPrint PDF (incl. new factors + risk drivers)
│       └── templates/
│           └── report_template.html       # Bilingual (TR/EN) A4 report template
├── data/
│   ├── raw/                               # Raw datasets (Kaggle + NLST)
│   ├── processed/
│   │   ├── lung_cancer_cleaned.csv        # Cleaned Kaggle data (3,000 samples)
│   │   ├── nlst_cleaned.csv               # Cleaned NLST data (53,452 participants)
│   │   ├── nlst_summary.json              # NLST statistics & conditional probabilities
│   │   ├── eda_plots/                     # Exploratory data analysis visualizations
│   │   ├── model_results/                 # Original BBN evaluation results
│   │   ├── hybrid_model_results/          # Hybrid BBN demo scenarios & visualizations
│   │   └── reports/                       # Generated PDF/HTML risk assessment reports
│   ├── knowledge_base/
│   │   ├── icd10_lung_codes.json          # Lung cancer ICD-10 codes & TR voice descriptors
│   │   ├── symptom_risk_factors.json      # Clinical feature-risk mappings
│   │   └── tr_il_pm25.json                # 81-province PM2.5 → air-pollution tier (IQAir 2023–2025)
│   ├── chroma_db/                         # ChromaDB vector store (auto-generated)
│   └── models/
│       ├── bbn_lung_cancer_v1.pkl         # Trained BBN model (Kaggle)
│       └── hybrid_bbn_nlst_v1.pkl         # Trained Hybrid BBN model (NLST)
├── docs/
│   ├── appendix_cpt_derivation.md         # Formal CPT derivation table & references
│   ├── sensitivity_analysis_calibration.md # Explaining-away fix & calibration report
│   ├── calibration_new_factors.md         # New-factor OR calibration & sensitivity report
│   ├── contribution_coefficients.md       # Contribution coefficients of each factor
│   ├── explainability_demo.md             # Shapley + context-dependence presentation notes
│   ├── architecture.md                    # System architecture, RAG/ChromaDB, models, make-voice flow diagram
│   ├── dictionary.md                      # Glossary (BBN, CPT, ICD-10, NLST, OR, AUC, DCA, …)
├── tests/test_scenarios/                  # Clean demo/test scenarios + golden runner (make scenarios)
│   ├── scenarios.json                     # Demo cases + controlled A/B pairs (incl. pack-year group)
│   ├── run_scenarios.py                   # Runs, verifies levels, writes SENARYO_RAPORU.md
│   └── SENARYO_RAPORU.md                  # Auto-generated, presentation-ready scenario report
├── tests/expert_validation/               # Pulmonologist blind-prediction validation (make expert)
│   ├── scenarios.json                     # 10 clinical vignettes
│   ├── run_expert_validation.py           # → uzman_tahmin_formu.md + model_sonuclari.md
│   └── model_sonuclari.md                 # Model answer key (vs expert predictions)
├── Makefile                               # Short commands: make chat / voice / pipeline / eval / calibrate
├── report/                                # CMPE 491 midterm report (LaTeX)
├── requirements.txt
└── README.md
```

---

## 📊 Current Status (Spring 2026 — Phase 4 In Progress)

### Core Components

| Component | Status | Details |
|-----------|--------|---------|
| Kaggle Data Preprocessing | ✅ Done | 3,000 samples cleaned, 13 features → ICD-10 mapped |
| NLST Data Integration | ✅ Done | 53,452 real clinical trial participants merged & normalized |
| ICD-10 Knowledge Base | ✅ Done | 6 subcodes, 8 symptoms, 5 risk factors, TR voice descriptors |
| Original BBN (Kaggle) | ✅ Done | 15 nodes, 23 edges, MLE-fitted CPTs, 5-Fold CV |
| Hybrid BBN (NLST + Lit.) | ✅ Done | 14 nodes, 16 edges — NLST + literature symptom CPTs + 3 new risk factors |
| New Risk Factors (v2) | ✅ Done | Family history (OR≈1.7), occupational/asbestos (OR≈1.5), air pollution (provincial PM2.5, OR 1.0/1.15/1.30) — literature OR-multiplied onto NLST base |
| Conversational Agent (v2) | ✅ Done | Cascade (STT→LLM→TTS) state-machine: greeting → demographics → symptoms → risk factors → voice summary → PDF |
| CPT Derivation & Calibration | ✅ Done | 7 symptom CPTs with sensitivity analysis & explaining-away fix |
| Risk Scoring Engine | ✅ Done | Evidence → risk score + ICD-10 findings + TR/EN recommendations |
| Whisper STT | ✅ Done | Turkish voice input + medical term post-processing ("kan tükürdüm" → hemoptizi) |
| NLP Symptom Extractor | ✅ Done | Dual mode: keyword matching (offline) + GPT-4o-mini (semantic) |
| RAG Pipeline | ✅ Done | ChromaDB vector store, 34 ICD-10 documents, OpenAI embeddings |
| PDF Report Generator | ✅ Done | Bilingual (TR/EN) Jinja2 → WeasyPrint, A4 doctor-ready reports |
| End-to-End Pipeline | ✅ Done | CLI: `--interactive`, `--audio`, `--record`, `--demo` modes |

### Upcoming Components

| Component | Status | Details |
|-----------|--------|---------|
| Performance Benchmarks | ✅ Done (v2) | **Risk/screening-appropriate metrics** — AUC-ROC, AUPRC, calibration (Brier, ECE, reliability curve, slope/intercept), Decision Curve Analysis, sensitivity/specificity at thresholds. See `src/model/evaluation.py`. |
| Mobile App (Flutter) | 📋 Fall 2026 | Voice UI + KETEM map integration + OpenAI Realtime |

> **Note on evaluation metric (v2 revision):** F1-Score / accuracy are **no longer primary metrics**. Praevidio is a probabilistic *risk-stratification* tool, not a binary diagnostic classifier — it never declares "cancer / not cancer," it outputs a calibrated risk probability. With a ~3.85% base rate, F1 is threshold-sensitive and misleading (a trivial "always-positive" model scored F1≈0.67). The model is now evaluated on **discrimination (AUC-ROC/AUPRC)**, **calibration (Brier, ECE, reliability)**, and **clinical utility (Decision Curve Analysis)** — directly answering "when we say 15% risk, is it really ~15%?" and "does using this score beat screen-all / screen-none?"

---

## 🆕 Fall 2026 — Model v3 and conversation flow v3

The spring model is kept intact as **v2**; `src/model/hybrid_bayesian_network_v3.py` adds, as a separate
module, (1) a latent *symptomatic* node that separates the NLST "6-year diagnosis" outcome from
"symptomatic now" symptom evidence, (2) a COPD common-cause node (noisy-OR) for the three respiratory
symptoms, (3) odds-ratio normalisation against the population mean, and (4) a two-layer output —
`risk_6y_factors` (screening layer, bands tied to the PLCOm2012 1.51 % threshold) plus a score-independent
**NICE NG12 alarm** flag. Design note: `docs/v3_tasarim.md`; side-by-side results: `make compare` →
`docs/v2_vs_v3_karsilastirma.md`. The conversational agent now asks an open-ended complaint question first,
accepts "bilmiyorum", confirms demographics, asks about COPD and speaks a two-layer summary
(`make chat` / `make voice`, old model with `MODEL=v2`). STT default is `gpt-4o-mini-transcribe` with a
medical-term context hint; a free native-Turkish TTS option (`PRAEVIDIO_TTS_PROVIDER=edge`) and a blind
listening test (`make tts-test`) were added.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/SamedKizilhan/Praevidio-AI.git
cd Praevidio-AI

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Data Preprocessing

```bash
# Run Kaggle data preprocessing
python src/data_preprocessing.py

# Run NLST data preprocessing
python src/nlst_data_preprocessing.py
```

### Model Training

```bash
# Train and evaluate the original BBN (Kaggle) - Artificial Data
python src/model/bayesian_network.py

# Build and validate the Hybrid BBN (NLST + Literature) - Real Data - RECOMMENDED
python src/model/hybrid_bayesian_network.py
```

### ⚡ Shortcuts (Makefile)

The `Makefile` wraps the common commands (it auto-detects `.venv`):

```bash
make chat        # conversational agent — text channel (type answers)
make voice       # conversational agent — voice channel (mic + TTS; needs sox)
make scenarios   # run test scenarios (golden checks + controlled pairs) → writes SENARYO_RAPORU.md
make expert      # expert-validation set: 10 vignettes → prediction form + model answer key
make eval        # risk-appropriate metrics (AUC / calibration / DCA)
make explain     # risk-score explainability (Shapley + context-dependence)
make calibrate   # new-factor OR calibration & sensitivity
make demo        # quick pipeline demo scenarios
make model       # build/validate/save the hybrid BBN
make help        # list all commands
```

> Switch slot-extraction mode with `make chat NLP=keyword` (default is `llm`).

### 🩺 Pipeline Usage (CLI)

```bash
# Conversational agent (v2) — greeting → demographics → symptoms → risk factors → spoken summary → PDF
python src/conversation/voice_agent.py --channel text              # typed (works anywhere, for testing)
python src/conversation/voice_agent.py --channel voice --nlp-mode llm  # microphone + TTS

# Risk/screening-appropriate evaluation (AUC, calibration, DCA — replaces F1)
python src/model/evaluation.py

# Explain a risk score: per-factor Shapley contributions + context-dependence + waterfall
python src/model/explainability.py

# Quick demo — runs predefined clinical scenarios
python src/pipeline.py --demo

# Interactive text mode (type symptoms in Turkish)
python src/pipeline.py --interactive

# Interactive mode with GPT-4o-mini extraction
python src/pipeline.py --interactive --nlp-mode llm

# Record from microphone → full pipeline (requires sox)
brew install sox
python src/pipeline.py --record --nlp-mode llm

# Process an existing audio file
python src/pipeline.py --audio recording.m4a --nlp-mode llm
```

### RAG Index

```bash
# Build/rebuild the ChromaDB vector index
python src/rag/rag_pipeline.py
```

---

## 📈 Motivation & Impact

Late diagnosis is the leading cause of cancer mortality. In Turkey, barriers like health literacy and psychological anxiety often delay clinical visits. **Praevidio AI** addresses these by:

1. **Bridging the Awareness Gap:** Voice-driven risk assessment accessible to low-literacy populations.
2. **Explainable AI:** Bayesian Networks provide transparent, traceable risk calculations — no black boxes.
3. **Clinical Standards:** All outputs mapped to ICD-10 codes for physician compatibility.
4. **Early Detection:** Aiming to shift diagnoses from Stage 4 to earlier stages where survival rates exceed **90%**.

---

## 📚 Data Sources & Attribution

The source code is licensed under AGPL-3.0-or-later (see below). **Data files are not covered by the AGPL; they keep their original licences and terms.**

| Source | Used for | Licence / terms | Files in this repository |
| --- | --- | --- | --- |
| NLST public clinical subset (TCIA / NCI Imaging Data Commons, release 2021-05-27) | Base CPTs P(cancer \| age, sex, smoking); evaluation (AUC, calibration, DCA) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) + [TCIA Data Usage Policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/) | `data/raw/nlst_780_*`, `data/raw/dictionary_idc_*`, `data/processed/nlst_cleaned.csv`, `data/processed/nlst_summary.json` |
| NHANES 2007–2012, RDQ/SMQ/MCQ/DEMO (CDC / NCHS) | No-cancer chronic cough and wheeze baselines (v3 calibration) | U.S. public domain; citation requested | `data/processed/nhanes_symptom_baselines.json` (raw files are downloaded by `make nhanes-download`, not redistributed) |
| PLCOm2012 model (Tammemägi et al., 2013) | External 6-year risk benchmark | Published coefficients; cite the paper | `src/model/plcom2012.py` |
| Peer-reviewed literature (Hamilton 2005, Beckles 2003, Kvale 2006, Hopwood & Stephens 2000, ILCCO, PLCOm2012, LLP …) | Symptom CPTs and risk-factor odds ratios | Cited facts | see `docs/appendix_cpt_derivation.md`, `docs/v3_tasarim.md` |
| NICE guideline NG12 — *Suspected cancer: recognition and referral* | Score-independent alarm rule | NICE guidance; cite | `src/model/hybrid_bayesian_network_v3.py` |
| IQAir *World Air Quality Report* (2023–2025 figures) | Provincial PM2.5 tiers | Figures compiled from the public report; see IQAir terms of use | `data/knowledge_base/tr_il_pm25.json` |
| SUS-TR (Demirkol & Şeneler, 2018) | Usability questionnaire | Published instrument; cite | `tests/usability/` |
| Kaggle "Lung Cancer" survey dataset (3,000 rows) | Legacy spring prototype only (`src/model/bayesian_network.py`) — **not used by v2/v3** | Provenance and licence not verified | `data/raw/lung_cancer_kaggle.csv`, `data/processed/lung_cancer_cleaned.csv` |

**Required citations**

- National Lung Screening Trial Research Team. (2013). *Data from the National Lung Screening Trial (NLST)* [Data set]. The Cancer Imaging Archive. https://doi.org/10.7937/TCIA.HMQ8-J677
- National Lung Screening Trial Research Team. Reduced lung-cancer mortality with low-dose computed tomographic screening. *N Engl J Med* 2011;365:395–409. https://doi.org/10.1056/NEJMoa1102873
- Centers for Disease Control and Prevention (CDC), National Center for Health Statistics (NCHS). *National Health and Nutrition Examination Survey Data*, 2007–2012. Hyattsville, MD: U.S. Department of Health and Human Services, CDC.
- Tammemägi MC, Katki HA, Hocking WG, et al. Selection criteria for lung-cancer screening. *N Engl J Med* 2013;368:728–736. https://doi.org/10.1056/NEJMoa1211776
- National Institute for Health and Care Excellence. *Suspected cancer: recognition and referral* (NICE guideline NG12). https://www.nice.org.uk/guidance/ng12
- Demirkol D, Şeneler Ç. A Turkish translation of the System Usability Scale: the SUS-TR. *Uşak Üniversitesi Sosyal Bilimler Dergisi* 2018;11(3):237–253.

**Conditions for the NLST files.** Anyone using or redistributing the NLST files in this repository must cite the dataset as above, follow the [TCIA Data Usage Policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/) — in particular, must not use the data, alone or combined with other information, to identify or contact trial participants — and must pass these conditions on to downstream users.

---

## 📄 License

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

Copyright (C) 2026 Samed KIZILHAN.

From the Fall 2026 term onward this project is licensed under the **GNU Affero General Public License v3.0 or later** (AGPL-3.0-or-later). You may use, study, modify and share the code, but any modified version that is distributed **or offered to users over a network** (e.g. as a web service, API or mobile-app backend) must make its complete source code available under the same license. See the [LICENSE](LICENSE) file for the full text.

> **License history:** versions published up to and including commit `4d7199f` (Spring 2026, CMPE 491, and its final corrections) were released under the Apache License 2.0 and remain available under those terms. All later work — including risk model v3, the PLCOm2012 benchmark, the NHANES calibration and conversation flow v3 — is AGPL-3.0-or-later only.

"Praevidio" and "Praevidio AI" are names of this project; the license does not grant rights to use them for derived products.

---

*CMPE 491 Senior Project — Boğaziçi University, Spring 2026*
*Advisor: Prof. Dr. Şefik Şuayb Arslan*
