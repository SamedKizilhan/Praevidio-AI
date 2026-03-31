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
│  │  Whisper STT  │───▶│  GPT-4o Symptom  │───▶│  RAG Engine   │  │
│  │  (Turkish)    │    │  Extractor       │    │  (LangChain)  │  │
│  └──────────────┘    └──────────────────┘    └───────┬───────┘  │
│                                                      │          │
│                              ┌──────────────────┐    │          │
│                              │  ICD-10 / KETEM   │◀───┘          │
│                              │  Knowledge Base   │              │
│                              │  (ChromaDB)       │              │
│                              └────────┬─────────┘              │
│                                       │                         │
│                                       ▼                         │
│                         ┌──────────────────────┐                │
│                         │  Bayesian Belief      │                │
│                         │  Network (pgmpy)      │                │
│                         │  15 nodes, 23 edges   │                │
│                         └──────────┬───────────┘                │
│                                    │                            │
│                                    ▼                            │
│                         ┌──────────────────────┐                │
│                         │  Risk Score (0-100%)  │                │
│                         │  + ICD-10 Findings    │                │
│                         └──────────┬───────────┘                │
│                                    │                            │
│                                    ▼                            │
│                         ┌──────────────────────┐                │
│                         │  📄 Doctor-Ready      │                │
│                         │  PDF Report           │                │
│                         └──────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

**Pipeline stages:**
1. **Voice → Text:** OpenAI Whisper transcribes Turkish speech to text.
2. **Text → Structured Symptoms:** GPT-4o extracts symptom data as structured JSON.
3. **Symptoms → ICD-10 Codes:** RAG retrieves relevant medical codes from the knowledge base.
4. **Evidence → Risk Score:** BBN performs probabilistic inference: `P(Lung Cancer | Evidence)`.
5. **Result → Report:** Generates a PDF with findings, risk level, and recommendations.

---

## 🛠️ Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Speech-to-Text** | OpenAI Whisper | Turkish voice transcription |
| **LLM** | GPT-4o | Symptom extraction & report generation |
| **Vector DB** | ChromaDB (dev) | ICD-10 knowledge retrieval |
| **Probabilistic Model** | pgmpy (BBN) | Explainable risk scoring |
| **Data Science** | pandas, scikit-learn, seaborn | EDA & model evaluation |
| **Report Gen** | Jinja2, WeasyPrint | PDF report generation |
| **Clinical Standards** | ICD-10, ICD-O-3 | International medical coding |
| **Language** | Python 3.12 | Core development |

---

## 📂 Project Structure

```
Praevidio-AI/
├── src/
│   ├── config.py                          # Centralized configuration
│   ├── data_preprocessing.py              # Data cleaning & ICD-10 mapping pipeline
│   ├── model/
│   │   └── bayesian_network.py            # BBN model, risk engine, evaluation
│   ├── stt/                               # Whisper STT integration (WIP)
│   ├── nlp/                               # GPT-4o symptom extractor (WIP)
│   ├── rag/                               # RAG pipeline (WIP)
│   └── report/                            # PDF report generator (WIP)
├── data/
│   ├── raw/                               # Raw datasets
│   ├── processed/                         # Cleaned data, EDA plots, model results
│   ├── knowledge_base/
│   │   ├── icd10_lung_codes.json          # Lung cancer ICD-10 codes & TR descriptors
│   │   └── symptom_risk_factors.json      # Clinical feature-risk mappings
│   └── models/
│       └── bbn_lung_cancer_v1.pkl         # Trained BBN model
├── report/                                # CMPE 491 midterm report (LaTeX)
├── requirements.txt
└── README.md
```

---

## 📊 Current Status (Spring 2026 — Midterm)

| Component | Status | Details |
|-----------|--------|---------|
| Data Preprocessing | ✅ Done | 3,000 samples cleaned, 13 features → ICD-10 mapped |
| ICD-10 Knowledge Base | ✅ Done | 6 subcodes, 8 symptoms, 5 risk factors, TR voice descriptors |
| Bayesian Belief Network | ✅ Done | 15 nodes, 23 edges, MLE-fitted CPTs |
| Model Evaluation | ✅ Done | 5-Fold CV: Recall 97.2%, F1 66.6% |
| Risk Scoring Engine | ✅ Done | Evidence → risk score + ICD-10 findings |
| EDA Visualizations | ✅ Done | 6 plots (correlation, feature impact, distributions) |
| RAG Pipeline | 🔄 In Progress | LangChain + ChromaDB |
| Whisper STT | 📋 Planned | Turkish-optimized voice input |
| PDF Report Generator | 📋 Planned | Jinja2 templates + WeasyPrint |
| Mobile App (Flutter) | 📋 Fall 2026 | Voice UI + KETEM map |

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

# Run data preprocessing pipeline
python src/data_preprocessing.py

# Train and evaluate the Bayesian Network
python src/model/bayesian_network.py
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
