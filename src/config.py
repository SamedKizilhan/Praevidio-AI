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

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Model Settings ---
LLM_MODEL = "gpt-4o"
WHISPER_MODEL = "whisper-1"
EMBEDDING_MODEL = "text-embedding-3-small"

# --- ChromaDB (Local Vector Store) ---
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")
CHROMA_COLLECTION_NAME = "lung_cancer_knowledge"

# --- Risk Engine ---
RISK_THRESHOLDS = {
    "low": 0.3,       # < 30%
    "moderate": 0.6,   # 30-60%
    "high": 1.0        # > 60%
}

# --- Dataset ---
RAW_DATASET_PATH = RAW_DATA_DIR / "lung_cancer_kaggle.csv"
CLEANED_DATASET_PATH = PROCESSED_DATA_DIR / "lung_cancer_cleaned.csv"

# --- Debug ---
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
