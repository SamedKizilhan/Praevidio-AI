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

# ──────────────────────────────────────────────
# Yeni risk faktörleri (v2)
# ──────────────────────────────────────────────

# Ailede 1. derece akraba kanser öyküsü
FAMILY_HISTORY_KEYWORDS = [
    "ailemde kanser", "ailede kanser", "ailemde akciğer kanseri",
    "annemde kanser", "babamda kanser", "kardeşimde kanser",
    "annem kanser", "babam kanser", "kardeşim kanser",
    "ailede akciğer", "ailemde akciğer", "ailede öykü",
    "birinci derece", "kalıtsal", "genetik yatkınlık",
]

# Mesleki asbest/risk maruziyeti proxy'si (riskli meslek grupları)
ASBESTOS_OCCUPATION_KEYWORDS = [
    "asbest", "inşaat", "yıkım", "tersane", "gemi söküm",
    "yalıtım", "izolasyon", "maden", "madenci", "fren balata",
    "oto tamir", "araba tamir", "çimento", "eternit", "fabrika",
    "tesisat", "kazan", "boru işçi", "tadilat", "işçilik",
]


def resolve_air_pollution(province: str) -> dict:
    """
    İl adını al → tr_il_pm25.json'dan PM2.5 kademesini döndür.

    Returns:
        {"AIR_POLLUTION": 0/1/2, "province": "...", "pm25": .., "tier_label": ".."}
        veya il bulunamazsa boş katkı (None AIR_POLLUTION).
    """
    if not province:
        return {}
    table_path = KNOWLEDGE_BASE_DIR / "tr_il_pm25.json"
    if not table_path.exists():
        return {}
    with open(table_path, encoding="utf-8") as f:
        table = json.load(f)
    provinces = table.get("provinces", {})

    # Türkçe normalize + kelime-sınırı eşleştirmesi (alt-dize yanlış eşleşmesini önler)
    target = _norm_tr(province)
    for il, info in provinces.items():
        nil = _norm_tr(il)
        if nil == target or re.search(r"\b" + re.escape(nil) + r"\b", target):
            return {
                "AIR_POLLUTION": info["tier"],
                "province": il,
                "pm25": info["pm25"],
                "tier_label": info["tier_label"],
            }
    return {}


# Cümleden il adı yakalama. KELİME-SINIRI eşleştirmesi kullanılır; aksi halde
# "içiyordum" içindeki "ordu" gibi alt-dizeler yanlış ile eşleşir.
def _norm_tr(s: str) -> str:
    return (s.lower().replace("̇", "").replace("ı", "i")
            .replace("ş", "s").replace("ğ", "g").replace("ü", "u")
            .replace("ö", "o").replace("ç", "c").strip())


def extract_province(text: str) -> str:
    table_path = KNOWLEDGE_BASE_DIR / "tr_il_pm25.json"
    if not table_path.exists():
        return ""
    with open(table_path, encoding="utf-8") as f:
        provinces = json.load(f).get("provinces", {})
    tl = _norm_tr(text)
    for il in provinces:
        if re.search(r"\b" + re.escape(_norm_tr(il)) + r"\b", tl):
            return il
    return ""

# Smoking status detection keywords
CURRENT_SMOKER_KEYWORDS = [
    "sigara içiyorum", "sigara kullanıyorum", "içici",
    "günde bir paket", "yıllardır içerim", "hala içiyorum",
]
FORMER_SMOKER_KEYWORDS = [
    "sigarayı bıraktım", "bırakalı", "eski içici",
    "artık içmiyorum", "bırakmış",
    # Hiç içmeyenler de bu modelde 0 (former/non-smoker) kovasına düşer
    "içmiyorum", "sigara içmiyorum", "içmem", "kullanmıyorum",
    "sigara kullanmıyorum", "hiç içmedim", "içmedim", "içmeyen",
    "kullanmadım", "kullanmam", "sigara kullanmam", "içmemiş",
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
    # Türkçe büyük "İ".lower() => "i̇" (i + U+0307 birleşik nokta) sorununu gider;
    # ayrıca "altmış beş" gibi sayı kelimelerini rakama çevirir (Whisper sık üretir).
    from model.screening import normalize_tr_numbers
    text_lower = normalize_tr_numbers(text.lower().replace("̇", ""))
    evidence = {}

    # --- Extract symptoms ---
    for var in SYMPTOM_VARIABLES:
        keywords = EXTENDED_KEYWORDS.get(var, [])
        found = any(kw.lower() in text_lower for kw in keywords)
        evidence[var] = 1 if found else 0

    # --- Extract smoking status ---
    # Açık bırakma ifadesi, "günde bir paket içtim" gibi miktar ifadelerini EZER
    # (geçmişte içmiş ama bırakmış → eski içici).
    quit_signal = any(w in text_lower for w in
                      ["bıraktım", "bırakalı", "bıraktı", "önce bırak",
                       "bırakmış", "bırakmıştım", "eski içici"])
    is_current = any(kw.lower() in text_lower for kw in CURRENT_SMOKER_KEYWORDS)
    is_former = any(kw.lower() in text_lower for kw in FORMER_SMOKER_KEYWORDS)

    if quit_signal:
        evidence["SMOKING"] = 0  # Bırakmış → eski içici (miktar ifadesi olsa bile)
    elif is_current:
        evidence["SMOKING"] = 1  # Current smoker
    elif is_former:
        evidence["SMOKING"] = 0  # Former smoker
    # else: don't include SMOKING in evidence (unknown)

    # --- Extract age (grup + kesin yaş) ---
    for pattern, _ in AGE_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            age = int(match.group(1))
            evidence["AGE"] = _age_to_group(age)
            evidence["_age_exact"] = age
            break

    # --- Extract gender (Türkçe ekler: erkek/erkeğim/erkeyim, kadın/kadınım) ---
    if any(w in text_lower for w in ["erkek", "erkeğ", "erkeg", "erkeyim", "bay "]):
        evidence["GENDER"] = 1
    elif any(w in text_lower for w in ["kadın", "kadin", "bayan"]):
        evidence["GENDER"] = 0

    # --- Yeni risk faktörleri ---
    # Ailede kanser öyküsü (olumsuzlama varsa atla)
    neg = any(n in text_lower for n in ["yok", "bulunmuyor", "değil"])
    if any(kw.lower() in text_lower for kw in FAMILY_HISTORY_KEYWORDS):
        evidence["FAMILY_HISTORY"] = 0 if neg else 1

    # Mesleki asbest/risk maruziyeti proxy
    if any(kw.lower() in text_lower for kw in ASBESTOS_OCCUPATION_KEYWORDS):
        evidence["ASBESTOS"] = 0 if neg else 1

    # Hava kirliliği: cümlede il adı geçiyorsa lookup'tan kademe çıkar
    province = extract_province(text)
    if province:
        air = resolve_air_pollution(province)
        if "AIR_POLLUTION" in air:
            evidence["AIR_POLLUTION"] = air["AIR_POLLUTION"]
            evidence["_province"] = air["province"]

    # Paket-yıl / sigara sıklığı (tarama uygunluğu için)
    from model.screening import parse_pack_years
    evidence.update(parse_pack_years(text))

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
  "WEIGHT_LOSS": 0 or 1,
  "FAMILY_HISTORY": 0 or 1 (1=first-degree relative had lung/other cancer, null=unknown),
  "ASBESTOS": 0 or 1 (1=worked in high-risk occupation, null=unknown),
  "PROVINCE": "Turkish province name as written, or null",
  "AGE_EXACT": integer age if stated, else null,
  "CIGARETTES_PER_DAY": integer (e.g. "bir paket"=20, "yarım paket"=10, "iki paket"=40), else null,
  "YEARS_SMOKED": integer years smoked if stated, else null,
  "YEARS_SINCE_QUIT": integer years since quitting if stated, else null
}

Important clinical mappings:
- "kan tükürdüm", "balgamda kan", "kanlı balgam" → HEMOPTYSIS = 1
- "nefes darlığı", "nefes alamıyorum" → SHORTNESS_OF_BREATH = 1
- "hırıltı", "ıslık sesi" → WHEEZING = 1
- "göğüs ağrısı", "göğsüm ağrıyor" → CHEST_PAIN = 1
- "yorgunluk", "halsizlik" → FATIGUE = 1
- "kilo verdim", "zayıfladım" → WEIGHT_LOSS = 1
- "ailemde/annemde/babamda/kardeşimde kanser", "genetik yatkınlık" → FAMILY_HISTORY = 1
- meslek: inşaat, yıkım, tersane, maden, yalıtım, oto tamir, çimento, eternit, fabrika işçiliği → ASBESTOS = 1
- "İstanbul'da/Konya'da yaşıyorum" gibi il adı → PROVINCE = "İstanbul"/"Konya"

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

    # PROVINCE → AIR_POLLUTION kademesine çevir (lookup tablosu)
    province = evidence.pop("PROVINCE", None)
    if province:
        air = resolve_air_pollution(str(province))
        if "AIR_POLLUTION" in air:
            evidence["AIR_POLLUTION"] = air["AIR_POLLUTION"]
            evidence["_province"] = air["province"]

    # Sigara sıklığı → paket-yıl; kesin yaş; bırakma süresi (tarama uygunluğu için)
    cigs = evidence.pop("CIGARETTES_PER_DAY", None)
    yrs = evidence.pop("YEARS_SMOKED", None)
    age_exact = evidence.pop("AGE_EXACT", None)
    quit_yrs = evidence.pop("YEARS_SINCE_QUIT", None)
    if age_exact is not None:
        evidence["_age_exact"] = age_exact
    if quit_yrs is not None:
        evidence["_years_quit"] = quit_yrs
    if cigs is not None:
        evidence["_cigs_per_day"] = cigs
    if yrs is not None:
        evidence["_years_smoked"] = yrs
    if cigs is not None and yrs is not None:
        evidence["_pack_years"] = round((cigs / 20.0) * yrs, 1)

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
