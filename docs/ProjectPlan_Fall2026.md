# Project Plan: Praevidio AI (Fall 2026)

This document is the Fall 2026 continuation of the [Spring 2026 plan](ProjectPlan.md). The spring term delivered a working prototype: a hybrid Bayesian Belief Network (NLST risk-factor CPTs + literature symptom CPTs), a cascade voice agent (STT → LLM slot filling → TTS), a screening-eligibility flag, explainability tooling and a bilingual "Doctor-Ready" PDF report. The fall term turns that prototype into a presentable MVP: a methodologically corrected risk model (v3), a more natural conversation, a Flutter mobile client backed by a FastAPI service, and the validation work promised in the spring report's *Future Work*.

---

## 1. Objectives

* **Risk model v3 (done, Oct 2026):** keep v2 intact and add, as a separate module, (i) a latent *symptomatic* node that separates the NLST "6-year diagnosis" outcome from "symptomatic-now" evidence, (ii) a COPD common-cause node for the respiratory symptoms, (iii) odds-ratio normalisation, (iv) a two-layer output — 6-year screening risk plus a score-independent NICE NG12 alarm — with bands tied to the PLCOm2012 1.51 % screening threshold; PLCOm2012 implemented as an external benchmark; sensitivity analysis over the new parameters.
* **Openly licensed data, triangulated parameters:** NLST public clinical subset (TCIA, CC BY 4.0) for the risk-factor base, the published PLCOm2012 model as an external benchmark for smoking dose, NHANES 2007–12 for no-cancer symptom baselines, and a pulmonologist's estimates for the remaining parameters; hospital contacts can contribute aggregate statistics through the prepared federated-statistics script.
* **Conversation flow v3 (done):** open-ended complaint question first, only missing symptoms asked one by one, "I don't know" accepted, demographics confirmation and correction, COPD question, two-layer spoken summary; STT moved to `gpt-4o-mini-transcribe` with a medical-term hint; TTS selected by a blind listening test (OpenAI tts-1 *nova*).
* **Mobile MVP:** FastAPI backend exposing the conversation state machine and the risk engine; Flutter app with voice recording + VAD, chat screen, report view and a KETEM map (nearest centres). App-store publication is out of scope.
* **Validation:** blind expert validation with a pulmonologist (10 vignettes, v2 vs v3), a small usability test (5–8 users, SUS), and a documented v2/v3 comparison.
* **Deliverables:** midterm report on **17 November 2026**; final report, demo video, poster, Git repository and presentation on **21 December 2026**.

---

## 2. Key Milestones

| Milestone | Date | Description |
| :--- | :--- | :--- |
| Term kickoff | 28 September 2026 | Code analysis, roadmap, uncommitted spring changes merged. |
| Model v3 + conversation v3 | 5 October 2026 | New risk model, flow, STT/TTS — delivered. |
| PLCOm2012 benchmark, sensitivity, NHANES calibration, AGPL-3.0 | 19 October 2026 | Delivered and merged to `main`. |
| Backend (FastAPI) | 1 November 2026 | `/session`, `/turn`, `/report` wrapping the agent and engine. |
| Flutter MVP end-to-end | 12 November 2026 | Voice/text conversation on the phone through the backend. |
| **Midterm report** | **17 November 2026** | Methodology review, model v3, v2/v3 comparison, PLCOm2012, NHANES calibration, conversation v3, backend + mobile architecture, remaining plan. |
| Expert + usability validation | 4 December 2026 | Pulmonologist blind scoring (10 vignettes, v2 vs v3); 5–8-person SUS test. |
| **Feature freeze** | **6 December 2026** | KETEM map, report screen and summary screens in; only fixes afterwards. |
| Release `v1.0.0` | 13 December 2026 | Final parameters frozen; model fingerprint test set; Zenodo DOI. |
| **Final submission** | **21 December 2026** | Final report, demo video, poster, Git repository, presentation. |

---

## 3. Development Schedule

### Phase 1 — Analysis and model correction (28 Sep – 19 Oct) ✅
Full code/report review; four methodological findings on the v2 score (meaning mismatch between NLST outcome and symptom CPTs, naive-Bayes over-confidence, reference-category bias, undefined time horizon). Implementation of v3 and of the v2/v3 comparison harness (`make compare`), PLCOm2012 benchmark, sensitivity analysis (`make sensitivity`), NHANES 2007–12 calibration of the no-cancer respiratory baselines (`make nhanes`), expert-validation answer key with v2/v3 side by side. Conversation flow v3, STT/TTS upgrades, blind TTS listening test. Relicensed to AGPL-3.0-or-later.

### Phase 2 — Backend and data access (19 Oct – 1 Nov)
FastAPI service: channel-independent conversation state machine, session store, STT/TTS behind the API, PDF report endpoint; Docker image. Expert-validation session scheduled with a pulmonologist.

### Phase 3 — Flutter MVP core (2 – 12 Nov)
Recording with Silero VAD (`sherpa_onnx`), playback, chat UI, backend integration; demographics → symptoms → risk factors → summary flow running end to end on a phone.

### Phase 4 — Midterm report (9 – 17 Nov)
LaTeX report on the spring template: methodology review and the four findings, model v3 design, v2/v3 comparison and sensitivity results, PLCOm2012 benchmark, NHANES calibration, conversation v3, backend/mobile architecture with screenshots, updated plan. Submitted **17 Nov**.

### Phase 5 — Mobile completion and validation (18 Nov – 6 Dec)
Report view/share and summary screens; KETEM list compiled into the knowledge base and shown on a map with the nearest centres; pulmonologist blind-prediction session (10 vignettes, v2 and v3); 5–8-person usability test (SUS); final evaluation (AUC/calibration/DCA on the NLST public subset, PLCOm2012 benchmark) and parameter adjustment from the expert's answers. Feature freeze **6 Dec**.

### Phase 6 — Release and final deliverables (7 – 21 Dec)
Bug fixes; parameter freeze and `v1.0.0` release with model fingerprint test set and Zenodo DOI (13 Dec); final report, poster, demo video (also the fallback for the live demo), presentation and repository clean-up. Submitted **21 Dec**.

---

## 4. Technical Stack (changes vs. spring)

* **Model:** pgmpy BBN v3 (`src/model/hybrid_bayesian_network_v3.py`), PLCOm2012 (`src/model/plcom2012.py`), NICE NG12 rule.
* **Speech:** OpenAI `gpt-4o-mini-transcribe` (STT, medical-term hint), OpenAI `tts-1` *nova* (TTS, disk cache + pre-warm); optional free Turkish neural voices via `edge-tts`.
* **Backend:** FastAPI + uvicorn, Docker; **Mobile:** Flutter 3.x, `record`, `sherpa_onnx` (Silero VAD), `just_audio`, `flutter_map` (OpenStreetMap), `dio`.
* **Data:** NLST public clinical subset (TCIA, CC BY 4.0), NHANES 2007–12 (public domain), published PLCOm2012 coefficients and literature parameters — see *Data Sources & Attribution* in the README.

---

## 5. Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| No symptom-level patient data available during the term | Symptom parameters triangulated from literature, NHANES baselines and the pulmonologist's estimates (expert form, part 2); limitation stated in the report. |
| No pulmonologist session before 4 Dec | Pulmonologist contact identified early; the form can be completed remotely in ~20 minutes. |
| Midterm report and Flutter work overlap (9–17 Nov) | Flutter core targeted for 12 Nov; the report reuses the auto-generated comparison, sensitivity and NHANES tables. |
| One developer across model, backend and mobile | Priority order: backend > Flutter MVP > KETEM map > polish; the map degrades to a list if needed. |
| v3 bands change spring demo results | v2 and v3 reported side by side with the reasons (a contribution in itself). |
| Live voice demo fails on presentation day | TTS cache, demo video, text channel fallback. |

*CMPE 492 Senior Project — Boğaziçi University, Fall 2026. Advisor: Prof. Dr. Şefik Şuayb Arslan.*
