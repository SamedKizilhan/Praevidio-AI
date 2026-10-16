# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — TTS kör dinleme testi
=====================================
Aynı 3 cümleyi aday seslerle sentezler, dosyaları A/B/C/… diye anonimleştirir,
cevap anahtarını ayrı yazar. 3-5 kişiye dinletip "doğallık / anlaşılırlık / güven"
puanı (1-5) toplanır; sonuç raporda "TTS seçimi" bölümüne girer.

Çalıştırma:  python tools/tts_listening_test.py        (veya: make tts-test)
Çıktı:       data/processed/tts_test/{A,B,C,...}_{1,2,3}.mp3 + KEY.json + PUANLAMA.md
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import OPENAI_API_KEY, PROCESSED_DATA_DIR
from conversation.voice_agent import synthesize_edge

OUT = PROCESSED_DATA_DIR / "tts_test"
SENTENCES = [
    "Merhaba. Sağlıklı bir risk analizi yapabilmem için öncelikle yaşınızı ve cinsiyetinizi belirtir misiniz?",
    "Hiç kan tükürdüğünüz oldu mu? Lütfen evet ya da hayır şeklinde yanıtlayın.",
    "Değerlendirmeniz tamamlandı. Risk düzeyiniz orta; düşük doz bilgisayarlı tomografi taraması için en yakın KETEM'e başvurmanızı öneririz.",
]
CANDIDATES = [
    {"id": "openai-tts1-nova",       "provider": "openai", "model": "tts-1",           "voice": "nova"},
    {"id": "openai-4o-mini-tts-coral", "provider": "openai", "model": "gpt-4o-mini-tts", "voice": "coral"},
    {"id": "edge-emel",              "provider": "edge",   "voice": "tr-TR-EmelNeural"},
    {"id": "edge-ahmet",             "provider": "edge",   "voice": "tr-TR-AhmetNeural"},
]


def synth_openai(text, out, model, voice):
    from openai import OpenAI
    c = OpenAI(api_key=OPENAI_API_KEY, timeout=30)
    with c.audio.speech.with_streaming_response.create(model=model, voice=voice, input=text,
                                                       response_format="mp3") as r:
        r.stream_to_file(str(out))
    return out.exists() and out.stat().st_size > 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cands = [c for c in CANDIDATES
             if c["provider"] != "openai" or (OPENAI_API_KEY and not OPENAI_API_KEY.startswith("sk-your"))]
    random.seed()  # her çalıştırmada farklı harf eşlemesi
    letters = list("ABCDEFGH")[:len(cands)]
    random.shuffle(letters)
    key = {}
    for c, L in zip(cands, letters):
        key[L] = c["id"]
        for i, text in enumerate(SENTENCES, 1):
            out = OUT / f"{L}_{i}.mp3"
            ok = (synth_openai(text, out, c["model"], c["voice"]) if c["provider"] == "openai"
                  else synthesize_edge(text, out, c["voice"]))
            print(f"   {'✅' if ok else '❌'} {L}_{i}.mp3  ← {c['id']}")
    (OUT / "KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# TTS kör dinleme testi — puanlama formu", "",
          "Her sesi (A, B, C, …) 3 cümlede dinleyin; 1 (kötü) – 5 (çok iyi) puan verin.", "",
          "| Ses | Doğallık | Anlaşılırlık | Güven verme | Tercih sırası |", "| --- | --- | --- | --- | --- |"]
    md += [f"| {L} |  |  |  |  |" for L in sorted(key)]
    md += ["", "*Cevap anahtarı KEY.json içindedir; dinleyiciye gösterilmez.*"]
    (OUT / "PUANLAMA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\n📁 {OUT}  — {len(cands)} aday × {len(SENTENCES)} cümle; anahtar: KEY.json")


if __name__ == "__main__":
    main()
