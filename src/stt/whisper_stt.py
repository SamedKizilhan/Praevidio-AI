"""
Praevidio AI - Whisper Speech-to-Text Module
=============================================
Turkish medical speech-to-text with post-processing for
medical terminology correction.

Two modes:
  - API mode: Uses OpenAI Whisper API (requires API key + audio file)
  - Demo mode: Accepts text input directly (for testing without audio)
"""

import json
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    WHISPER_MODEL, OPENAI_API_KEY, KNOWLEDGE_BASE_DIR
)


# ──────────────────────────────────────────────
# Medical Term Correction Dictionary
# Maps common colloquial Turkish expressions to
# their proper medical equivalents
# ──────────────────────────────────────────────

MEDICAL_TERM_MAP = {
    # Hemoptysis — colloquial to medical
    "kan tükürdüm": "hemoptizi",
    "kan tükürüyorum": "hemoptizi",
    "kan tükürme": "hemoptizi",
    "öksürünce kan geliyor": "hemoptizi",
    "balgamda kan": "hemoptizi",
    "kanlı balgam": "hemoptizi",
    "kan geldi ağzımdan": "hemoptizi",
    "öksürdüğümde kan": "hemoptizi",

    # Dyspnea
    "nefes alamıyorum": "dispne, nefes darlığı",
    "nefesim kesiliyor": "dispne, nefes darlığı",
    "nefes almakta zorlanıyorum": "dispne, nefes darlığı",
    "nefes darlığı çekiyorum": "dispne, nefes darlığı",
    "soluk alamıyorum": "dispne, nefes darlığı",

    # Wheezing
    "nefes alırken ıslık sesi": "hırıltılı solunum, wheezing",
    "solunum sırasında ses": "hırıltılı solunum, wheezing",
    "hışıltı var": "hırıltılı solunum, wheezing",

    # Fatigue
    "sürekli yorgunum": "kronik yorgunluk, halsizlik",
    "enerjim yok": "kronik yorgunluk, halsizlik",
    "bitkinim": "kronik yorgunluk, halsizlik",
    "güçsüzüm": "kronik yorgunluk, halsizlik",

    # Chest pain
    "göğsüm ağrıyor": "göğüs ağrısı",
    "göğsümde baskı": "göğüs ağrısı, baskı hissi",
    "göğsümde sızı": "göğüs ağrısı",
    "ciğerlerim ağrıyor": "göğüs ağrısı",

    # Weight loss
    "kilo verdim": "kilo kaybı",
    "kilo kaybettim": "kilo kaybı",
    "zayıfladım": "kilo kaybı",
    "istemsiz kilo kaybı": "kilo kaybı",

    # Cough
    "sürekli öksürüyorum": "kronik öksürük",
    "öksürük geçmiyor": "kronik öksürük",
    "kuru öksürük": "nonprodüktif öksürük",
    "balgamlı öksürük": "prodüktif öksürük",

    # Smoking
    "sigara içiyorum": "aktif sigara kullanımı",
    "yıllardır içerim": "uzun süreli sigara kullanımı",
    "günde bir paket": "sigara kullanımı, ~20 adet/gün",
    "sigarayı bıraktım": "eski sigara kullanıcısı",
    "bırakalı 5 yıl oldu": "eski sigara kullanıcısı",
}


def load_voice_descriptors() -> dict:
    """
    Load voice_descriptors_tr from the ICD-10 knowledge base.
    Returns a mapping of ICD-10 code → list of Turkish voice terms.
    """
    icd10_path = KNOWLEDGE_BASE_DIR / "icd10_lung_codes.json"
    with open(icd10_path, "r", encoding="utf-8") as f:
        icd10_data = json.load(f)

    descriptors = {}

    for code, info in icd10_data.get("symptoms", {}).items():
        terms = info.get("voice_descriptors_tr", [])
        if terms:
            descriptors[code] = {
                "terms": terms,
                "description": info["description"],
                "description_tr": info["description_tr"],
                "dataset_mapping": info.get("dataset_mapping"),
            }

    for code, info in icd10_data.get("risk_factors", {}).items():
        terms = info.get("voice_descriptors_tr", [])
        if terms:
            descriptors[code] = {
                "terms": terms,
                "description": info["description"],
                "description_tr": info["description_tr"],
                "dataset_mapping": info.get("dataset_mapping"),
            }

    return descriptors


# Whisper'ın sessiz/çok kısa seste ürettiği tipik halüsinasyon kalıpları
# (YouTube altyazıları eğitim verisinde olduğu için). Bunlar tespit edilirse
# transkripsiyon boş kabul edilir ve ajan soruyu tekrar sorar.
HALLUCINATION_PATTERNS = [
    "abone ol", "beğen", "beğenmeyi", "yorum yap", "butona", "kanalıma",
    "altyazı", "izlediğiniz için teşekkür", "subscribe", "thanks for watching",
    "like and subscribe", "amara.org", "m.k.",
]


def _looks_like_hallucination(text: str) -> bool:
    t = text.lower().replace("̇", "")
    return any(p in t for p in HALLUCINATION_PATTERNS)


def transcribe_audio(audio_path: str, language: str = "tr", prompt: str = "") -> dict:
    """
    Transcribe audio file using OpenAI Whisper API.

    Args:
        audio_path: Path to audio file (wav, mp3, m4a, webm)
        language: ISO 639-1 language code (default: Turkish)
        prompt: Optional context hint to bias Whisper (reduces hallucination
                on short/quiet audio, e.g. "Kullanıcı bir Türkiye ilinin adını söylüyor.")

    Returns:
        dict with: text, language, duration, raw_response
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-your-api-key-here":
        raise ValueError(
            "OpenAI API key not configured. Set OPENAI_API_KEY in .env file."
        )

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    supported = {".wav", ".mp3", ".m4a", ".webm", ".mp4", ".mpeg", ".mpga", ".oga", ".ogg"}
    if audio_file.suffix.lower() not in supported:
        raise ValueError(f"Unsupported format: {audio_file.suffix}. Supported: {supported}")

    print(f"🎤 Transcribing: {audio_file.name}")
    print(f"   Model: {WHISPER_MODEL}, Language: {language}")

    with open(audio_file, "rb") as f:
        kwargs = dict(model=WHISPER_MODEL, file=f, language=language,
                      response_format="verbose_json", temperature=0)
        if prompt:
            kwargs["prompt"] = prompt
        response = client.audio.transcriptions.create(**kwargs)

    raw_text = response.text
    # Halüsinasyon kalıbı (sessiz/kısa ses) → boş kabul et, ajan tekrar sorsun
    if _looks_like_hallucination(raw_text):
        print(f"   ⚠️  Olası halüsinasyon yok sayıldı: \"{raw_text}\"")
        return {"text": "", "raw_text": raw_text, "language": language,
                "duration": getattr(response, "duration", None), "corrections_applied": False}
    corrected_text = post_process_medical_terms(raw_text)

    result = {
        "text": corrected_text,
        "raw_text": raw_text,
        "language": language,
        "duration": getattr(response, "duration", None),
        "corrections_applied": raw_text != corrected_text,
    }

    print(f"   ✅ Transcription: \"{corrected_text}\"")
    if result["corrections_applied"]:
        print(f"   🔧 Medical term corrections applied (raw: \"{raw_text}\")")

    return result


def post_process_medical_terms(text: str) -> str:
    """
    Post-process Whisper transcription to correct medical terminology.

    Applies two layers of correction:
      1. Exact phrase matching from MEDICAL_TERM_MAP
      2. Voice descriptor matching from ICD-10 knowledge base

    This ensures that colloquial expressions like "kan tükürdüm"
    are annotated with their medical equivalents like "hemoptizi".
    """
    corrected = text.lower()

    # Layer 1: Exact phrase corrections
    # Sort by length (longest first) to avoid partial matches
    sorted_terms = sorted(MEDICAL_TERM_MAP.keys(), key=len, reverse=True)
    for colloquial, medical in [(k, MEDICAL_TERM_MAP[k]) for k in sorted_terms]:
        if colloquial in corrected:
            # Annotate rather than replace — keep original + add medical term
            corrected = corrected.replace(
                colloquial,
                f"{colloquial} [{medical}]"
            )

    return corrected


def demo_mode_input() -> dict:
    """
    Demo mode: Accept text input from terminal instead of audio.
    Returns same structure as transcribe_audio().
    """
    print("\n🎤 DEMO MODE — Text Input (Whisper bypass)")
    print("   Enter symptom description in Turkish (or 'quit' to exit):")
    print("   " + "─" * 50)

    text = input("   > ").strip()
    if text.lower() in ("quit", "exit", "q", "çıkış"):
        return None

    corrected = post_process_medical_terms(text)

    result = {
        "text": corrected,
        "raw_text": text,
        "language": "tr",
        "duration": None,
        "corrections_applied": text != corrected,
        "mode": "demo",
    }

    print(f"\n   📝 Processed: \"{corrected}\"")
    if result["corrections_applied"]:
        print(f"   🔧 Medical term corrections applied")

    return result


# ==============================================================
# MAIN — Test the module
# ==============================================================

if __name__ == "__main__":
    print("🎤 PRAEVIDIO AI — Whisper STT Module Test")
    print("=" * 50)

    # Test post-processing
    test_inputs = [
        "sürekli öksürüyorum ve kan tükürdüm",
        "nefes alamıyorum, göğsüm ağrıyor",
        "sigara içiyorum, günde bir paket, kilo verdim",
        "son zamanlarda çok yorgunum, öksürük geçmiyor",
        "balgamda kan var ve nefes alırken ıslık sesi duyuyorum",
    ]

    print("\n📝 Medical Term Post-Processing Test:")
    print("-" * 50)

    for text in test_inputs:
        corrected = post_process_medical_terms(text)
        print(f"\n   Input:  \"{text}\"")
        print(f"   Output: \"{corrected}\"")

    # Demo mode
    print(f"\n{'='*50}")
    print("Interactive demo mode — type a symptom description:")
    result = demo_mode_input()
    if result:
        print(f"\n   Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
