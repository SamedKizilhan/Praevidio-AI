# Project Plan: Praevidio AI (Fall 2026)

This document is the Fall 2026 continuation of the [Spring 2026 plan](ProjectPlan.md). The spring term delivered a working prototype: a hybrid Bayesian Belief Network (NLST risk-factor CPTs + literature symptom CPTs), a cascade voice agent (STT → LLM slot filling → TTS), a screening-eligibility flag, explainability tooling and a bilingual "Doctor-Ready" PDF report. The fall term turns that prototype into a presentable MVP: a methodologically corrected risk model (v3), a more natural conversation, a Flutter mobile client backed by a FastAPI service, and the validation work promised in the spring report's *Future Work*.

---

## 1. Objectives

* **Risk model v3 (done, Oct 2026):** keep v2 intact and add, as a separate module, (i) a latent *symptomatic* node that separates the NLST "6-year diagnosis" outcome from "symptomatic-now" evidence, (ii) a COPD common-cause node for the respiratory symptoms, (iii) odds-ratio normalisation, (iv) a two-layer output — 6-year screening risk plus a score-independent NICE NG12 alarm — with bands tied to the PLCOm2012 1.51 % screening threshold; PLCOm2012 implemented as an external benchmark; sensitivity analysis over the new parameters.
* **Real data, larger and more informative:** request the full NLST participant file and the PLCO Lung dataset from NCI CDAS (pack-years, family history, asbestos, COPD; 65,000 never-smokers in PLCO) to re-learn the risk-factor CPTs; use NHANES 2007–12 for no-cancer symptom baselines; pursue symptom-level patient data through author requests (Karolinska PEX-LC, Cambridge SYMPTOM-Lung, Leeds CXR cohort) and Turkish chest-disease departments; keep the federated-statistics route for hospitals.
* **Conversation flow v3 (done):** open-ended complaint question first, only missing symptoms asked one by one, "I don't know" accepted, demographics confirmation and correction, COPD question, two-layer spoken summary; STT moved to `gpt-4o-mini-transcribe` with a medical-term hint; TTS selected by a blind listening test (OpenAI tts-1 *nova*).
* **Mobile MVP:** FastAPI backend exposing the conversation state machine and the risk engine; Flutter app with voice recording + VAD, chat screen, report view and a KETEM map (nearest centres). App-store publication is out of scope.
* **Validation:** blind expert validation with a pulmonologist (10 vignettes, v2 vs v3), a small usability test (5–8 users, SUS), and a documented v2/v3 comparison.
* **Final report and presentation** on 11 December 2026.

---

## 2. Key Milestones

| Milestone | Date | Description |
| :--- | :--- | :--- |
| Term kickoff | 28 September 2026 | Code analysis, roadmap, uncommitted spring changes merged. |
| Model v3 + conversation v3 | 5 October 2026 | New risk model, flow, STT/TTS — delivered. |
| PLCOm2012 benchmark, sensitivity, NHANES pipeline | 16 October 2026 | Delivered (NHANES run pending download on the development machine). |
| Backend (FastAPI) | 1 November 2026 | `/session`, `/turn`, `/report` wrapping the agent and engine. |
| Flutter MVP end-to-end | 15 November 2026 | Voice/text conversation on the phone through the backend. |
| **Feature freeze** | **22 November 2026** | KETEM map and report screen in; only fixes afterwards. |
| Expert + usability validation | 29 November 2026 | Pulmonologist blind scoring; SUS test. |
| **Final presentation** | **11 December 2026** | Report, poster, demo video, live demo. |

---

## 3. Development Schedule

### Phase 1 — Analysis and model correction (28 Sep – 18 Oct) ✅
Full code/report review; four methodological findings on the v2 score (meaning mismatch between NLST outcome and symptom CPTs, naive-Bayes over-confidence, reference-category bias, undefined time horizon). Implementation of v3 and of the v2/v3 comparison harness (`make compare`), PLCOm2012 benchmark, sensitivity analysis (`make sensitivity`), NHANES baseline pipeline (`make nhanes`), expert-validation answer key with v2/v3 side by side. Conversation flow v3, STT/TTS upgrades, blind TTS listening test.

### Phase 2 — Backend and data access (19 Oct – 1 Nov)
FastAPI service: channel-independent conversation state machine, session store, STT/TTS behind the API, PDF report endpoint; Docker image. CDAS application for full NLST + PLCO (requires an ID.me-verified NIH account for the student and the advisor as PI, plus the university signing official). Author requests for symptom-level cohorts via a physician collaborator. NHANES run and parameter check.

### Phase 3 — Flutter MVP (19 Oct – 15 Nov, overlapping)
Recording with Silero VAD (`sherpa_onnx`), playback, chat UI, backend integration; demographics → symptoms → risk factors → summary screens; report view/share.

### Phase 4 — KETEM map, validation, freeze (9 – 29 Nov)
KETEM list compiled into the knowledge base and shown on a map with the nearest centres; pulmonologist blind-prediction session (10 vignettes, v2 and v3); 5–8-person usability test; if CDAS data arrive, re-learn the risk-factor CPTs and re-run AUC/calibration/DCA with PLCOm2012 as benchmark. Feature freeze 22 Nov.

### Phase 5 — Report and presentation (23 Nov – 11 Dec)
Final report (data v2, model v3, mobile, validation), poster, 3-minute demo video as a fallback for the live demo, rehearsal.

---

## 4. Technical Stack (changes vs. spring)

* **Model:** pgmpy BBN v3 (`src/model/hybrid_bayesian_network_v3.py`), PLCOm2012 (`src/model/plcom2012.py`), NICE NG12 rule.
* **Speech:** OpenAI `gpt-4o-mini-transcribe` (STT, medical-term hint), OpenAI `tts-1` *nova* (TTS, disk cache + pre-warm); optional free Turkish neural voices via `edge-tts`.
* **Backend:** FastAPI + uvicorn, Docker; **Mobile:** Flutter 3.x, `record`, `sherpa_onnx` (Silero VAD), `just_audio`, `flutter_map` (OpenStreetMap), `dio`.
* **Data:** NLST IDC subset (current), full NLST + PLCO via CDAS (requested), NHANES 2007–12, author-provided symptom cohorts (requested).

---

## 5. Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| CDAS data arrive late or not at all (identity verification, signing official) | v3 already runs on literature parameters and the PLCOm2012 benchmark; data only refresh parameters. |
| No pulmonologist session before 29 Nov | Two candidate physicians contacted early; the form can be completed remotely. |
| One developer across model, backend and mobile | Priority order: backend > Flutter MVP > KETEM map > polish; the map degrades to a list if needed. |
| v3 bands change spring demo results | v2 and v3 reported side by side with the reasons (a contribution in itself). |
| Live voice demo fails on presentation day | TTS cache, demo video, text channel fallback. |

*CMPE 492 Senior Project — Boğaziçi University, Fall 2026. Advisor: Prof. Dr. Şefik Şuayb Arslan.*
