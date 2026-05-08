# Praevidio AI 🩺

> **Praevidio** (Latin for *foreseeing*): An Intelligent Voice-Driven Platform for Lung Cancer Risk Analysis and Early Awareness in Turkey.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![pgmpy](https://img.shields.io/badge/pgmpy-1.0-orange?style=flat)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

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
* **🧠 Hybrid Risk Engine:** Bayesian Belief Network (BBN) for explainable, probabilistic risk scoring — no black-box predictions.
* **🔍 RAG-Powered ICD-10 Mapping:** Retrieval-Augmented Generation maps verbal symptoms to international medical codes (ICD-10/ICD-O-3).
* **📄 Doctor-Ready PDF Reports:** Generates structured clinical summaries with ICD-10 coded findings, risk categories, and bilingual recommendations (TR/EN).
* **📍 KETEM Integration (Planned):** Directs high-risk users to the nearest Cancer Early Diagnosis, Screening, and Training Center.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRAEVIDIO AI                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎤 Voice Input                                                 │
│    │                                                            │
│    ▼                                                            │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Whisper STT  │───▶│ GPT-4o-mini   │───▶│  RAG Engine   │  │
│  │  (Turkish)    │    │  Extraction   │    │  (ChromaDB)   │  │
│  └──────────────┘    └──────────────────┘    └───────┬───────┘  │
│                                                      │          │
│                              ┌──────────────────┐    │          │
│                              │  ICD-10 / KETEM   │◀───┘          │
│                              │  Knowledge Base   │              │
│                              │  (ChromaDB)       │              │
│                              └────────┬─────────┘              │
│                                       │                         │
│                                       ▼                         │
│              ┌────────────────────────────────────────┐          │
│              │     HYBRID BAYESIAN BELIEF NETWORK     │          │
│              │                                        │          │
│              │  Part A: Risk Factor CPTs              │          │
│              │  ┌────────────────────────────────┐    │          │
│              │  │ NLST Clinical Trial (n=53,452) │    │          │
│              │  │ P(Cancer | Age,Gender,Smoking)  │    │          │
│              │  └────────────────────────────────┘    │          │
│              │                                        │          │
│              │  Part B: Symptom CPTs                  │          │
│              │  ┌────────────────────────────────┐    │          │
│              │  │ Peer-Reviewed Literature        │    │          │
│              │  │ 7 symptoms, 5 references        │    │          │
│              │  └────────────────────────────────┘    │          │
│              │  11 nodes, 13 edges (pgmpy)           │          │
│              └──────────────────┬─────────────────────┘          │
│                                 │                                │
│                                 ▼                                │
│                      ┌──────────────────────┐                   │
│                      │  Risk Score (0-100%)  │                   │
│                      │  + ICD-10 Findings    │                   │
│                      └──────────┬───────────┘                   │
│                                 │                                │
│                                 ▼                                │
│                      ┌──────────────────────┐                   │
│                      │  📄 Doctor-Ready      │                   │
│                      │  PDF Report           │                   │
│                      └──────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

**Pipeline stages:**
1. **Voice → Text:** OpenAI Whisper transcribes Turkish speech to text.
2. **Text → Structured Symptoms:** GPT-4o extracts symptom data as structured JSON.
3. **Symptoms → ICD-10 Codes:** RAG retrieves relevant medical codes from the knowledge base.
4. **Evidence → Risk Score:** Hybrid BBN performs probabilistic inference: `P(Lung Cancer | Evidence)`.
5. **Result → Report:** Generates a PDF with findings, risk level, and recommendations.

---

## 🛠️ Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------| 
| **Speech-to-Text** | OpenAI Whisper | Turkish voice transcription |
| **LLM** | GPT-4o-mini | Symptom extraction (cost-efficient) |
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
│   │   └── hybrid_bayesian_network.py     # Hybrid BBN (NLST + literature, 11 nodes)
│   ├── stt/
│   │   └── whisper_stt.py                 # Whisper STT + Turkish medical term correction
│   ├── nlp/
│   │   └── symptom_extractor.py           # Keyword + GPT-4o-mini symptom extraction
│   ├── rag/
│   │   └── rag_pipeline.py                # ChromaDB indexer + semantic ICD-10 retrieval
│   └── report/
│       ├── report_generator.py            # Jinja2 → WeasyPrint PDF report generator
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
│   │   └── symptom_risk_factors.json      # Clinical feature-risk mappings
│   ├── chroma_db/                         # ChromaDB vector store (auto-generated)
│   └── models/
│       ├── bbn_lung_cancer_v1.pkl         # Trained BBN model (Kaggle)
│       └── hybrid_bbn_nlst_v1.pkl         # Trained Hybrid BBN model (NLST)
├── docs/
│   ├── appendix_cpt_derivation.md         # Formal CPT derivation table & references
│   └── sensitivity_analysis_calibration.md # Explaining-away fix & calibration report
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
| Hybrid BBN (NLST + Lit.) | ✅ Done | 11 nodes, 13 edges — NLST risk factors + literature symptom CPTs |
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
| Performance Benchmarks | 🔄 Phase 4 | Accuracy, F1-Score on hold-out test data |
| Mobile App (Flutter) | 📋 Fall 2026 | Voice UI + KETEM map integration |

---

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

### 🩺 Pipeline Usage (CLI)

```bash
# Quick demo — runs 3 predefined clinical scenarios
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

## 📄 License

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for the full text.

---

*CMPE 491 Senior Project — Boğaziçi University, Spring 2026*
*Advisor: Prof. Dr. Şefik Şuayb Arslan*
