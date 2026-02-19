# Praevidio AI 🩺

> **Praevidio** (Latin for *foreseeing*): An Intelligent Voice-Driven Mobile Platform for Multi-Type Cancer Risk Analysis and Early Awareness.

---

## 🚀 Overview
Praevidio AI is a cutting-edge mobile application designed to bridge the gap between early symptoms and clinical diagnosis. By leveraging **Large Language Models (LLMs)** and **Retrieval-Augmented Generation (RAG)**, it transforms natural language voice inputs into structured clinical insights, specifically focusing on prevalent cancer types in Turkey.

## ✨ Key Features
* **🎙️ Voice-Activated Symptom Analysis:** High-fidelity transcription (STT) for natural symptom description, ensuring accessibility for all age groups.
* **🤖 Intelligent RAG Interviewer:** Dynamic, medical-protocol-driven interviews that adapt based on user input rather than static forms.
* **📄 Doctor-Ready PDF Reports:** Generates structured clinical summaries to optimize the first consultation and improve health literacy.
* **📍 Geospatial Triage:** Integrated mapping to direct high-risk users to the nearest **KETEM** (Early Cancer Screening Centers).

## 🛠️ Technical Stack

### **Mobile & Backend**
![Flutter](https://img.shields.io/badge/Flutter-%2302569B.svg?style=flat&logo=Flutter&logoColor=white) 
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi) 
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)

### **AI & NLP Engine**
* **STT:** OpenAI Whisper (Optimized for Turkish)
* **LLM:** GPT-4o
* **Vector DB:** Supabase (PostgreSQL + pgvector)
* **Frameworks:** LangChain / LangGraph

### **Data & Infrastructure**
* **Sources:** WHO Globocan, Turkish Cancer Statistics, ICD-10 Mapping.
* **Storage:** Supabase

---

## 📈 Motivation & Impact
Late diagnosis is the leading cause of cancer mortality. In Turkey, barriers like health literacy and anxiety often delay clinical visits. **Praevidio AI** addresses these by:
1.  **Bridging the Awareness Gap:** Actionable risk scores based on localized health data.
2.  **Reducing Clinical Load:** Structured summaries that save time for physicians.
3.  **Early Detection:** Aiming to increase "Stage 1" detection where survival rates exceed **90%**.

---

## 🏗️ Architecture (Proposed)
1. **User Input:** Voice recording sent via Flutter.
2. **Processing:** FastAPI orchestrates STT and LLM reasoning.
3. **RAG Layer:** AI queries medical protocols from the Vector Database.
4. **Output:** A personalized risk assessment and a downloadable PDF report.

---

## 📄 License

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for the full text.

