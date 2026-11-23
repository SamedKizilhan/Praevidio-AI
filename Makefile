# Praevidio AI — short commands (run `make help` for the list)

# Python of the virtual environment (works without activating it); falls back to the system python3
VENV    ?= .venv
PY      := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
# NLP: answer extraction in the conversation (llm | keyword)
# HOST: address `make api` listens on (127.0.0.1 for this machine only)
# MODEL: risk model, v3 (current, v3.1) | v2 (spring term)
NLP     ?= llm
HOST    ?= 0.0.0.0
PORT    ?= 8000
MODEL   ?= v3

.DEFAULT_GOAL := help
.PHONY: help chat voice api api-test pipeline demo scenarios compare model-v3 model-test v31-diff replay conversation-test sensitivity nhanes nhanes-download tts-test expert expert-analyze sus eval calibrate explain model rag install clean

help:  ## List the commands
	@echo "Praevidio AI — commands:"
	@echo "  make api              Backend and web app (FastAPI) -> http://localhost:$(PORT)/app/"
	@echo "  make chat             Interview in the terminal, typed        [NLP=$(NLP)]"
	@echo "  make voice            Interview in the terminal, mic and TTS  [NLP=$(NLP)]"
	@echo "  make model-test       Model tests: v3.0 regression, plausibility, external references"
	@echo "  make api-test         End-to-end API tests (no OpenAI calls)"
	@echo "  make conversation-test  Replay the recorded conversations in tests/conversations"
	@echo "  make replay F=<file>  Replay one transcript against the current agent"
	@echo "  make compare          v2, v3.0 and v3.1 side by side -> docs/model_comparison_v2_v3.md"
	@echo "  make sensitivity      Sensitivity analysis -> docs/sensitivity_v3.md"
	@echo "  make v31-diff         v3.0 to v3.1 change per profile -> docs/model_v3_1_calibration_fix.md"
	@echo "  make nhanes-download  Download the NHANES 2007-12 files"
	@echo "  make nhanes           Symptom baselines without cancer -> docs/nhanes_symptom_baselines.md"
	@echo "  make expert           Expert form (10 cases) and model answer key"
	@echo "  make expert-analyze   Expert answers against the models -> expert_comparison.md"
	@echo "  make sus              Score the SUS-TR questionnaire -> tests/usability/sus_results.md"
	@echo "  make eval             Discrimination, calibration and decision-curve metrics on NLST"
	@echo "  make model-v3         Build and check the v3 network, run demo cases"
	@echo "  make tts-test         Files for the blind listening test of TTS voices"
	@echo "  make pipeline / demo  Batch pipeline with ICD-10 retrieval (spring)"
	@echo "  make scenarios / calibrate / explain / model   v2 reports -> docs/history/"
	@echo "  make rag              Build the ChromaDB ICD-10 index"
	@echo "  make install          Install the dependencies"
	@echo "  (rule-based extraction: make chat NLP=keyword;  spring model: make chat MODEL=v2)"

chat:  ## Interview in the terminal, typed
	$(PY) src/conversation/voice_agent.py --channel text --nlp-mode $(NLP) --model $(MODEL)

voice:  ## Interview in the terminal, microphone and TTS (needs sox)
	$(PY) src/conversation/voice_agent.py --channel voice --nlp-mode $(NLP) --model $(MODEL)

compare:  ## Score every scenario with v2, v3.0 and v3.1
	$(PY) tests/test_scenarios/compare_v2_v3.py

model-v3:  ## Build and check the v3 network, run demo cases
	$(PY) src/model/hybrid_bayesian_network_v3.py

replay:  ## Replay a transcript: make replay F=data/conversations/<file>.txt [ARGS="--full --nlp llm"]
	$(PY) tools/replay_conversation.py $(F) $(ARGS)

conversation-test:  ## Regression tests on recorded conversations (tests/conversations/*.txt)
	$(PY) -m pytest tests/conversations -q

model-test:  ## Model tests: v3.0 regression and clinical plausibility (Hamilton envelope, PLCOm2012, NHANES)
	$(PY) -m pytest tests/model -q

v31-diff:  ## Change per profile from v3.0 to v3.1 (docs/model_v3_1_calibration_fix.md)
	cd tests/model && $(PY) diff_report.py

sensitivity:  ## Sensitivity analysis of the v3 model
	$(PY) src/model/sensitivity_v3.py

nhanes-download:  ## NHANES RDQ/SMQ/MCQ/DEMO 2007-2012 (about 15 MB) -> data/raw/nhanes/
	bash tools/download_nhanes.sh

nhanes:  ## Symptom baselines without cancer from NHANES
	$(PY) src/model/nhanes_symptom_baselines.py

tts-test:  ## Blind listening test of TTS voices (data/processed/tts_test/)
	$(PY) tools/tts_listening_test.py

api:  ## Backend API (FastAPI) and the web app
	$(PY) -m uvicorn api.server:app --app-dir src --host $(HOST) --port $(PORT)

api-test:  ## End-to-end API tests (keyword mode, mocked STT; free)
	$(PY) -m pytest tests/api -q

pipeline:  ## Batch pipeline, interactive text
	$(PY) src/pipeline.py --interactive --nlp-mode $(NLP)

demo:  ## Batch pipeline on prepared clinical scenarios
	$(PY) src/pipeline.py --demo

scenarios:  ## v2 golden scenarios and controlled pairs -> docs/history/v2_scenario_report.md
	$(PY) tests/test_scenarios/run_scenarios.py

expert:  ## Expert validation: 10 cases -> prediction form and model answer key
	$(PY) tests/expert_validation/run_expert_validation.py

expert-analyze:  ## Compare the expert's answers (expert_answers.csv) with v2 and v3
	$(PY) tests/expert_validation/analyze_expert_validation.py

sus:  ## Score the SUS-TR usability questionnaire (tests/usability/sus_answers.csv)
	$(PY) tests/usability/score_sus.py

eval:  ## Risk-appropriate metrics (AUC, Brier, ECE, decision curve)
	$(PY) src/model/evaluation.py

calibrate:  ## v2: odds-ratio calibration of the added risk factors -> docs/history/
	$(PY) src/model/calibrate_risk_factors.py

explain:  ## v2: explainability of a score (Shapley, context dependence, waterfall) -> docs/history/
	$(PY) src/model/explainability.py

model:  ## v2: build, check and save the hybrid network
	$(PY) src/model/hybrid_bayesian_network.py

rag:  ## (Re)build the ChromaDB ICD-10 vector index
	$(PY) src/rag/rag_pipeline.py

install:  ## Install the dependencies
	$(PY) -m pip install -r requirements.txt

clean:  ## Remove temporary outputs (__pycache__)
	find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."
