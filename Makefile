# Praevidio AI — kısa komutlar
# Kullanım örnekleri:
#   make chat        → metin tabanlı konuşmalı ajan (klavyeden)
#   make voice       → sesli konuşmalı ajan (mikrofon + TTS)
#   make pipeline    → uçtan uca pipeline (etkileşimli metin)
#   make demo        → hazır senaryolarla hızlı demo
#   make eval        → risk-uygun performans metrikleri (AUC, kalibrasyon, DCA)
#   make calibrate   → yeni faktör OR kalibrasyonu & duyarlılık analizi
#   make model       → hibrit BBN'i kur, doğrula, kaydet
#   make install     → bağımlılıkları kur

# Sanal ortam Python'u (aktive etmeden de çalışır); yoksa sistem python3'üne düşer
VENV    ?= .venv
PY      := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
NLP     ?= llm        # konuşmada slot çıkarımı: llm | keyword
MODEL   ?= v3         # risk modeli: v3 (latent semptomatik + KOAH) | v2 (bahar dönemi)

.DEFAULT_GOAL := help
.PHONY: help chat voice pipeline demo scenarios compare model-v3 sensitivity nhanes nhanes-download tts-test expert expert-analyze sus eval calibrate explain model rag install clean

help:  ## Komut listesini göster
	@echo "Praevidio AI — komutlar:"
	@echo "  make chat       Konuşmalı ajan (metin)        [NLP=$(NLP)]"
	@echo "  make voice      Konuşmalı ajan (ses, mic+TTS) [NLP=$(NLP)]"
	@echo "  make pipeline   Uçtan uca pipeline (etkileşimli)"
	@echo "  make demo       Hazır senaryolarla demo (pipeline)"
	@echo "  make scenarios  Temiz test senaryoları (golden + çiftler, v2)"
	@echo "  make compare    v2 ile v3 modelini yan yana karşılaştır → docs/v2_vs_v3_karsilastirma.md"
	@echo "  make model-v3   v3 BBN'i kur/doğrula + demo senaryolar"
	@echo "  make sensitivity v3 duyarlılık analizi (q, normalizasyon, PLCOm2012 tabanı) → docs/v3_duyarlilik.md"
	@echo "  make nhanes-download  NHANES 2007-12 dosyalarını indir (Mac'te çalıştır)"
	@echo "  make nhanes     NHANES ile kansersiz semptom tabanları → docs/nhanes_semptom_tabanlari.md"
	@echo "  make tts-test   TTS kör dinleme testi dosyalarını üret (OpenAI + Edge sesleri)"
	@echo "  make expert     Uzman formu (10 vaka: 6y risk % + A/B/C eylem) + v2/v3 cevap anahtarı"
	@echo "  make expert-analyze  Uzman cevapları ↔ v2/v3 (eylem kappa, Spearman) → uzman_karsilastirma.md"
	@echo "  make sus        SUS-TR kullanılabilirlik puanları → tests/usability/sus_sonuclari.md"
	@echo "  make eval       Performans metrikleri (AUC / kalibrasyon / DCA)"
	@echo "  make calibrate  Yeni faktör OR kalibrasyonu + duyarlılık"
	@echo "  make explain    Risk skoru açıklanabilirliği (Shapley + bağlam)"
	@echo "  make model      Hibrit BBN kur/doğrula/kaydet"
	@echo "  make rag        ChromaDB ICD-10 indeksini kur"
	@echo "  make install    Bağımlılıkları kur"
	@echo "  (NLP modunu değiştir: make chat NLP=keyword;  eski model: make chat MODEL=v2)"

chat:  ## Konuşmalı ajan — metin kanalı
	$(PY) src/conversation/voice_agent.py --channel text --nlp-mode $(NLP) --model $(MODEL)

voice:  ## Konuşmalı ajan — ses kanalı (mikrofon + TTS, sox gerekir)
	$(PY) src/conversation/voice_agent.py --channel voice --nlp-mode $(NLP) --model $(MODEL)

compare:  ## v2 ile v3 risk modelini tüm senaryolarda karşılaştır
	$(PY) tests/test_scenarios/compare_v2_v3.py

model-v3:  ## v3 BBN'i kur, doğrula, demo senaryoları çalıştır
	$(PY) src/model/hybrid_bayesian_network_v3.py

sensitivity:  ## v3 duyarlılık analizi
	$(PY) src/model/sensitivity_v3.py

nhanes-download:  ## NHANES RDQ/SMQ/MCQ/DEMO 2007-2012 (≈15 MB) → data/raw/nhanes/
	bash tools/download_nhanes.sh

nhanes:  ## NHANES ile kansersiz semptom tabanları (v3 leak/smoke doğrulaması)
	$(PY) src/model/nhanes_symptom_baselines.py

tts-test:  ## TTS kör dinleme testi (data/processed/tts_test/)
	$(PY) tools/tts_listening_test.py

pipeline:  ## Uçtan uca pipeline (etkileşimli metin)
	$(PY) src/pipeline.py --interactive --nlp-mode $(NLP)

demo:  ## Hazır klinik senaryolarla hızlı demo (pipeline)
	$(PY) src/pipeline.py --demo

scenarios:  ## Temiz test senaryoları (golden doğrulama + kontrollü çiftler + rapor)
	$(PY) tests/test_scenarios/run_scenarios.py

expert:  ## Uzman doğrulama: 10 vaka → tahmin formu + model sonuç tablosu
	$(PY) tests/expert_validation/run_expert_validation.py

expert-analyze:  ## Uzman cevapları (uzman_cevaplari.csv) ile v2/v3 karşılaştırması
	$(PY) tests/expert_validation/analyze_expert_validation.py

sus:  ## SUS-TR kullanılabilirlik anketi puanlama (tests/usability/sus_cevaplari.csv)
	$(PY) tests/usability/score_sus.py

eval:  ## Risk-uygun performans metrikleri (AUC, Brier, ECE, DCA)
	$(PY) src/model/evaluation.py

calibrate:  ## Yeni faktör OR kalibrasyonu & duyarlılık analizi
	$(PY) src/model/calibrate_risk_factors.py

explain:  ## Risk skoru açıklanabilirliği (Shapley + bağlam-bağımlılığı + waterfall)
	$(PY) src/model/explainability.py

model:  ## Hibrit BBN'i kur, doğrula, kaydet (+ demo senaryolar & grafikler)
	$(PY) src/model/hybrid_bayesian_network.py

rag:  ## ChromaDB ICD-10 vektör indeksini (yeniden) kur
	$(PY) src/rag/rag_pipeline.py

install:  ## Bağımlılıkları kur (.venv aktif olmalı veya $(VENV) mevcut olmalı)
	$(PY) -m pip install -r requirements.txt

clean:  ## Geçici çıktıları temizle (raporlar/kayıtlar hariç model artefaktları)
	find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Temizlendi."
