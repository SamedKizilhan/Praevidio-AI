"""
Praevidio AI - NLP Symptom Extractor
=====================================
Extracts structured symptom evidence from Turkish text for BBN inference.

Two modes:
  - Keyword mode: Matches voice_descriptors_tr from ICD-10 knowledge base (free, offline)
  - LLM mode: Uses GPT-4o-mini for semantic extraction (requires API key)

Both modes output a standardized evidence dict compatible with
HybridLungCancerEngine.predict_risk().
"""

import json
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    KNOWLEDGE_BASE_DIR, OPENAI_API_KEY, LLM_MODEL, NLP_MODE
)


# ──────────────────────────────────────────────
# Keyword-Based Symptom Extraction
# ──────────────────────────────────────────────

# Mapping from dataset variable names to the BBN evidence keys
# used by HybridLungCancerEngine
SYMPTOM_VARIABLES = [
    "COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN",
    "WHEEZING", "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"
]

RISK_FACTOR_VARIABLES = ["SMOKING", "AGE", "GENDER"]

# Extended keyword mappings beyond voice_descriptors_tr
# for terms that don't appear in the knowledge base
EXTENDED_KEYWORDS = {
    "HEMOPTYSIS": [
        "kan tükürdüm", "kan tükürme", "kan tükürüyorum",
        "öksürünce kan", "kan geldi", "hemoptizi",
        "kanlı balgam", "balgamda kan", "ağzımdan kan",
    ],
    "WEIGHT_LOSS": [
        "kilo verdim", "kilo kaybı", "kilo kaybettim",
        "zayıfladım", "istemsiz kilo", "kilo düştü",
    ],
    "FATIGUE": [
        "yorgunum", "yorgunluk", "halsizlik", "bitkinlik",
        "enerjim yok", "güçsüzüm", "bitkinim", "halsizim",
        "takatsiz", "dermansız",
    ],
    "COUGHING": [
        "öksürük", "öksürüyorum", "öksürük geçmiyor",
        "sürekli öksürük", "kuru öksürük", "balgamlı öksürük",
        "kronik öksürük",
    ],
    "SHORTNESS_OF_BREATH": [
        "nefes darlığı", "nefes alamıyorum", "nefesim kesiliyor",
        "nefes almakta zorlanıyorum", "soluk alamıyorum",
        "dispne", "nefes darlığı çekiyorum",
    ],
    "CHEST_PAIN": [
        "göğüs ağrısı", "göğsüm ağrıyor", "göğsümde baskı",
        "göğsümde sızı", "ciğerlerim ağrıyor", "göğüs bölgesinde ağrı",
    ],
    "WHEEZING": [
        "hırıltı", "hışıltı", "hırıltılı solunum",
        "nefes alırken ıslık sesi", "solunum sırasında ses",
    ],
    "SMOKING": [
        "sigara içiyorum", "sigara kullanıyorum", "içici",
        "günde bir paket", "yıllardır içerim", "sigara",
        "sigarayı bıraktım", "bırakalı", "eski içici",
    ],
}

# Smoking status detection keywords
CURRENT_SMOKER_KEYWORDS = [
    "sigara içiyorum", "sigara kullanıyorum", "içici",
    "günde bir paket", "yıllardır içerim", "hala içiyorum",
]
FORMER_SMOKER_KEYWORDS = [
    "sigarayı bıraktım", "bırakalı", "eski içici",
    "artık içmiyorum", "bırakmış",
]

# Age group detection patterns
AGE_PATTERNS = [
    (r"(\d{2,3})\s*yaşında", None),  # "65 yaşındayım"
    (r"yaşım\s*(\d{2,3})", None),     # "yaşım 65"
]


def extract_keywords(text: str) -> dict:
    """
    Extract symptom evidence from Turkish text using keyword matching.

    Args:
        text: Turkish text (possibly post-processed by Whisper STT)

    Returns:
        dict compatible with HybridLungCancerEngine.predict_risk()
        e.g., {"SMOKING": 1, "COUGHING": 1, "AGE": 3, ...}
    """
    text_lower = text.lower()
    evidence = {}

    # --- Extract symptoms ---
    for var in SYMPTOM_VARIABLES:
        keywords = EXTENDED_KEYWORDS.get(var, [])
        found = any(kw.lower() in text_lower for kw in keywords)
        evidence[var] = 1 if found else 0

    # --- Extract smoking status ---
    is_current = any(kw.lower() in text_lower for kw in CURRENT_SMOKER_KEYWORDS)
    is_former = any(kw.lower() in text_lower for kw in FORMER_SMOKER_KEYWORDS)

    if is_current:
        evidence["SMOKING"] = 1  # Current smoker
    elif is_former:
        evidence["SMOKING"] = 0  # Former smoker
    # else: don't include SMOKING in evidence (unknown)

    # --- Extract age ---
    for pattern, _ in AGE_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            age = int(match.group(1))
            evidence["AGE"] = _age_to_group(age)
            break

    # --- Extract gender ---
    if any(w in text_lower for w in ["erkek", "erkeyim", "bay"]):
        evidence["GENDER"] = 1
    elif any(w in text_lower for w in ["kadın", "kadınım", "bayan"]):
        evidence["GENDER"] = 0

    return evidence


def _age_to_group(age: int) -> int:
    """Convert raw age to NLST age group encoding."""
    if age < 55:
        return 0
    elif age < 60:
        return 1
    elif age < 65:
        return 2
    elif age < 70:
        return 3
    else:
        return 4


# ──────────────────────────────────────────────
# LLM-Based Symptom Extraction (GPT-4o-mini)
# ──────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a medical NLP system for the Praevidio AI lung cancer screening tool.
Extract structured clinical findings from the following Turkish patient statement.

Return a JSON object with these exact keys. Use 1 for present, 0 for absent, null if not mentioned:
{
  "SMOKING": 0 or 1 (0=former, 1=current, null=unknown),
  "AGE": 0-4 (0=<55, 1=55-59, 2=60-64, 3=65-69, 4=70+, null=unknown),
  "GENDER": 0 or 1 (0=Female, 1=Male, null=unknown),
  "COUGHING": 0 or 1,
  "SHORTNESS_OF_BREATH": 0 or 1,
  "CHEST_PAIN": 0 or 1,
  "WHEEZING": 0 or 1,
  "FATIGUE": 0 or 1,
  "HEMOPTYSIS": 0 or 1,
  "WEIGHT_LOSS": 0 or 1
}

Important clinical mappings:
- "kan tükürdüm", "balgamda kan", "kanlı balgam" → HEMOPTYSIS = 1
- "nefes darlığı", "nefes alamıyorum" → SHORTNESS_OF_BREATH = 1
- "hırıltı", "ıslık sesi" → WHEEZING = 1
- "göğüs ağrısı", "göğsüm ağrıyor" → CHEST_PAIN = 1
- "yorgunluk", "halsizlik" → FATIGUE = 1
- "kilo verdim", "zayıfladım" → WEIGHT_LOSS = 1

Return ONLY the JSON object, no explanation.

Patient statement: "{text}"
"""


def extract_with_llm(text: str) -> dict:
    """
    Extract symptom evidence using GPT-4o-mini.

    Args:
        text: Turkish text (possibly post-processed by Whisper STT)

    Returns:
        dict compatible with HybridLungCancerEngine.predict_risk()
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-your-api-key-here":
        print("   ⚠️  No API key — falling back to keyword mode")
        return extract_keywords(text)

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    print(f"   🤖 Extracting symptoms with {LLM_MODEL}...")

    prompt = EXTRACTION_PROMPT.replace("{text}", text)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a medical NLP extraction system. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=300,
    )

    raw_json = response.choices[0].message.content.strip()

    # Clean markdown code fences if present
    if raw_json.startswith("```"):
        raw_json = re.sub(r"```(?:json)?\n?", "", raw_json).strip()

    try:
        extracted = json.loads(raw_json)
    except json.JSONDecodeError:
        print(f"   ❌ Failed to parse LLM response: {raw_json}")
        print("   ⚠️  Falling back to keyword mode")
        return extract_keywords(text)

    # Filter out null values — only include what was mentioned
    evidence = {k: v for k, v in extracted.items() if v is not None}

    print(f"   ✅ Extracted {len(evidence)} clinical findings")
    return evidence


def extract_symptoms(text: str, mode: str = None) -> dict:
    """
    Main entry point: extract symptom evidence from text.

    Args:
        text: Turkish patient statement
        mode: "keyword" or "llm" (defaults to config.NLP_MODE)

    Returns:
        dict compatible with HybridLungCancerEngine.predict_risk()
    """
    mode = mode or NLP_MODE

    if mode == "llm":
        return extract_with_llm(text)
    else:
        return extract_keywords(text)


# ==============================================================
# MAIN — Test the module
# ==============================================================

if __name__ == "__main__":
    print("🧠 PRAEVIDIO AI — NLP Symptom Extractor Test")
    print("=" * 50)

    test_inputs = [
        "65 yaşındayım, erkeyim, sigara içiyorum. Sürekli öksürüyorum ve kan tükürdüm.",
        "Kadınım, 58 yaşındayım, sigarayı bıraktım. Nefes darlığı ve göğüs ağrısı var.",
        "Yorgunum, kilo verdim, balgamda kan var.",
        "Hırıltılı solunum var, öksürük geçmiyor, göğsümde baskı hissediyorum.",
        "70 yaşında erkeyim, günde bir paket sigara içiyorum.",
    ]

    for text in test_inputs:
        print(f"\n{'─'*50}")
        print(f"   📝 Input: \"{text}\"")

        # Keyword mode
        kw_result = extract_symptoms(text, mode="keyword")
        print(f"   📋 Keyword: {kw_result}")

    # Test LLM mode if API key available
    if OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-api-key-here":
        print(f"\n{'='*50}")
        print("🤖 LLM Mode Test (GPT-4o-mini):")
        for text in test_inputs[:2]:
            print(f"\n   📝 Input: \"{text}\"")
            llm_result = extract_symptoms(text, mode="llm")
            print(f"   📋 LLM: {llm_result}")
