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

.DEFAULT_GOAL := help
.PHONY: help chat voice pipeline demo scenarios eval calibrate explain model rag install clean

help:  ## Komut listesini göster
	@echo "Praevidio AI — komutlar:"
	@echo "  make chat       Konuşmalı ajan (metin)        [NLP=$(NLP)]"
	@echo "  make voice      Konuşmalı ajan (ses, mic+TTS) [NLP=$(NLP)]"
	@echo "  make pipeline   Uçtan uca pipeline (etkileşimli)"
	@echo "  make demo       Hazır senaryolarla demo (pipeline)"
	@echo "  make scenarios  Temiz test senaryoları (golden + çiftler)"
	@echo "  make expert     Uzman doğrulama seti (10 vaka + sonuç tablosu)"
	@echo "  make eval       Performans metrikleri (AUC / kalibrasyon / DCA)"
	@echo "  make calibrate  Yeni faktör OR kalibrasyonu + duyarlılık"
	@echo "  make explain    Risk skoru açıklanabilirliği (Shapley + bağlam)"
	@echo "  make model      Hibrit BBN kur/doğrula/kaydet"
	@echo "  make rag        ChromaDB ICD-10 indeksini kur"
	@echo "  make install    Bağımlılıkları kur"
	@echo "  (NLP modunu değiştir: make chat NLP=keyword)"

chat:  ## Konuşmalı ajan — metin kanalı
	$(PY) src/conversation/voice_agent.py --channel text --nlp-mode $(NLP)

voice:  ## Konuşmalı ajan — ses kanalı (mikrofon + OpenAI TTS, sox gerekir)
	$(PY) src/conversation/voice_agent.py --channel voice --nlp-mode $(NLP)

pipeline:  ## Uçtan uca pipeline (etkileşimli metin)
	$(PY) src/pipeline.py --interactive --nlp-mode $(NLP)

demo:  ## Hazır klinik senaryolarla hızlı demo (pipeline)
	$(PY) src/pipeline.py --demo

scenarios:  ## Temiz test senaryoları (golden doğrulama + kontrollü çiftler + rapor)
	$(PY) tests/test_scenarios/run_scenarios.py

expert:  ## Uzman doğrulama: 10 vaka → tahmin formu + model sonuç tablosu
	$(PY) tests/expert_validation/run_expert_validation.py

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
