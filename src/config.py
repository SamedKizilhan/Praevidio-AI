"""
Praevidio AI - Configuration Module
Loads environment variables and provides centralized config.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
MODELS_DIR = DATA_DIR / "models"
REPORTS_OUTPUT_DIR = PROCESSED_DATA_DIR / "reports"

# --- NLST Data ---
NLST_CLEANED_PATH = PROCESSED_DATA_DIR / "nlst_cleaned.csv"
NLST_SUMMARY_PATH = PROCESSED_DATA_DIR / "nlst_summary.json"
HYBRID_MODEL_PATH = MODELS_DIR / "hybrid_bbn_nlst_v1.pkl"

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Model Settings ---
LLM_MODEL = "gpt-4o-mini"           # Cost-efficient for symptom extraction
WHISPER_MODEL = "whisper-1"
EMBEDDING_MODEL = "text-embedding-3-small"

# --- TTS (sesli yanıt) ---
# Model: "tts-1" = en düşük gecikme (demo için önerilir),
#        "tts-1-hd" = daha yüksek kalite ama daha yavaş,
#        "gpt-4o-mini-tts" = en yeni/doğal, gecikme tts-1'e yakın.
TTS_MODEL = os.getenv("PRAEVIDIO_TTS_MODEL", "tts-1")
# Ses: alloy, echo, fable, onyx, nova, shimmer, ash, ballad, coral, sage, verse.
# "nova"/"shimmer"/"coral"/"sage" daha doğal/sıcak tonludur.
TTS_VOICE = os.getenv("PRAEVIDIO_TTS_VOICE", "nova")
TTS_SPEED = float(os.getenv("PRAEVIDIO_TTS_SPEED", "1.0"))   # 0.25–4.0
# Kayıt bitişi: varsayılan = ENTER (en güvenilir, baş kısmı KIRPILMAZ).
# Otomatik durma (sessizlik/VAD) istersen: PRAEVIDIO_REC_AUTOSTOP=1
REC_AUTOSTOP = os.getenv("PRAEVIDIO_REC_AUTOSTOP", "0") not in ("0", "", "false", "False")
REC_SILENCE_THRESHOLD = os.getenv("PRAEVIDIO_REC_SILENCE", "1.5%")  # düşük = daha hassas başlangıç
REC_SILENCE_SECONDS = os.getenv("PRAEVIDIO_REC_SILENCE_SEC", "2.5")  # bu kadar sessizlikte dur
REC_WARMUP_SEC = float(os.getenv("PRAEVIDIO_REC_WARMUP", "0.4"))     # mikrofon açılış gecikmesi

# --- ChromaDB (Local Vector Store) ---
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")
CHROMA_COLLECTION_NAME = "lung_cancer_knowledge"

# --- Report Templates ---
REPORT_TEMPLATE_DIR = Path(__file__).parent / "report" / "templates"
REPORT_TEMPLATE_PATH = REPORT_TEMPLATE_DIR / "report_template.html"

# --- Risk Engine (calibrated to NLST base rate 3.85%) ---
RISK_THRESHOLDS = {
    "low": 0.05,       # < 5%  (≤1.3× base rate)
    "moderate": 0.15,  # 5-15% (1.3-3.9× base rate)
    "high": 1.0        # > 15% (≥3.9× base rate)
}

# --- NLP Mode ---
# "keyword" = voice_descriptors_tr matching (free, offline)
# "llm"     = GPT-4o-mini extraction (requires API key)
NLP_MODE = os.getenv("NLP_MODE", "keyword")

# --- Dataset ---
RAW_DATASET_PATH = RAW_DATA_DIR / "lung_cancer_kaggle.csv"
CLEANED_DATASET_PATH = PROCESSED_DATA_DIR / "lung_cancer_cleaned.csv"

# --- Debug ---
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

