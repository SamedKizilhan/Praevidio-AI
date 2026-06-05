"""
Praevidio AI - Cascade Konuşmalı Risk Değerlendirme Ajanı
==========================================================
Etkileşimli (karşılıklı konuşmalı) bir oturum yürütür:

  Karşılama → Demografi (yaş/cinsiyet/sigara) → Semptomlar (sırayla)
  → Yeni risk faktörleri (aile öyküsü / meslek / il) → Risk skoru
  → Sesli özet → PDF rapor

Mimari: CASCADE (STT → LLM/keyword slot çıkarımı → TTS).
OpenAI Realtime yerine cascade tercih edildi; yapılandırılmış anket için
daha kontrollü, loglanabilir, ucuz ve demo'da tekrarlanabilir
(gerekçe: docs/v2_genisletme_tasarim.md §4).

İki kanal:
  --channel text   : klavyeden yaz / ekrana yazdır (her ortamda çalışır, test için)
  --channel voice  : mikrofondan kaydet (Whisper STT) + OpenAI TTS ile seslendir

Kullanım:
  python src/conversation/voice_agent.py --channel text
  python src/conversation/voice_agent.py --channel voice --nlp-mode llm
"""

import sys
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OPENAI_API_KEY, NLP_MODE, PROCESSED_DATA_DIR
from nlp.symptom_extractor import (
    extract_symptoms, resolve_air_pollution, extract_province
)
from stt.whisper_stt import post_process_medical_terms


# ──────────────────────────────────────────────
# Sesli/Yazılı kanal soyutlaması
# ──────────────────────────────────────────────

class Channel:
    """Konuşma kanalı: say() = sistemin konuşması, listen() = kullanıcıdan girdi."""

    def __init__(self, mode: str = "text"):
        self.mode = mode  # "text" | "voice"

    def say(self, text: str):
        print(f"\n🤖 {text}")
        if self.mode == "voice":
            self._tts(text)

    def listen(self, prompt_hint: str = "") -> str:
        if self.mode == "voice":
            return self._record_and_transcribe()
        # text kanal
        try:
            return input("   🗣️  > ").strip()
        except EOFError:
            return ""

    # --- Voice yardımcıları ---
    def _tts(self, text: str):
        """OpenAI tts-1 ile seslendir, macOS'ta afplay ile oynat."""
        if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
            return
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            out = PROCESSED_DATA_DIR / "tts_tmp.mp3"
            with client.audio.speech.with_streaming_response.create(
                model="tts-1", voice="alloy", input=text
            ) as resp:
                resp.stream_to_file(str(out))
            subprocess.run(["afplay", str(out)], check=False)
        except Exception as e:
            print(f"   ⚠️  TTS atlandı: {e}")

    def _record_and_transcribe(self) -> str:
        from stt.whisper_stt import transcribe_audio
        audio = self._record_until_enter()
        if not audio:
            return input("   🗣️  (ses alınamadı, yazınız) > ").strip()
        try:
            return transcribe_audio(audio)["text"]
        except Exception as e:
            print(f"   ⚠️  STT hatası: {e}")
            return ""

    def _record_until_enter(self, max_seconds: int = 60) -> str:
        """
        Soru sorulur sorulmaz kaydı OTOMATİK başlatır; kullanıcı ENTER'a basınca durdurur.
        (Eski akış: ENTER ile başlat + Ctrl+C ile durdur — değiştirildi.)
        sox 'rec' arka planda başlatılır, ENTER'da SIGINT ile temiz kapatılır.
        """
        import os
        import shutil
        import signal
        import subprocess
        from datetime import datetime
        from config import PROCESSED_DATA_DIR

        if shutil.which("rec") is None:
            print("   ⚠️  Ses kaydı için 'sox' gerekli (brew install sox). Şimdilik yazınız.")
            return ""

        rec_dir = PROCESSED_DATA_DIR / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        out = str(rec_dir / f"rec_{datetime.now():%Y%m%d_%H%M%S}.wav")

        print("   🔴 Kaydediliyor… bitirince ENTER'a basın.")
        proc = subprocess.Popen(
            ["rec", "-q", out, "rate", "16000", "channels", "1",
             "trim", "0", str(max_seconds)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            input()  # ENTER → kaydı durdur
        except (EOFError, KeyboardInterrupt):
            pass
        proc.send_signal(signal.SIGINT)   # sox dosyayı temiz sonlandırır
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        if os.path.exists(out) and os.path.getsize(out) > 1000:
            print("   ⏹️  Kayıt alındı.")
            return out
        print("   ⚠️  Kayıt çok kısa/boş.")
        return ""


# ──────────────────────────────────────────────
# Yes/No (evet/hayır) Türkçe ayrıştırma
# ──────────────────────────────────────────────

_YES = ["evet", "var", "oluyor", "olur", "doğru", "öyle", "hı hı", "tabii",
        "kesinlikle", "aynen", "mevcut", "çalıştım", "çalışıyorum"]
_NO = ["hayır", "yok", "olmuyor", "değil", "yoktur", "asla", "hiç",
       "bulunmuyor", "çalışmadım"]


def parse_yes_no(text: str):
    """'evet' → True, 'hayır' → False, belirsiz → None."""
    t = text.lower().replace("̇", "")
    yes = any(w in t for w in _YES)
    no = any(w in t for w in _NO)
    if yes and not no:
        return True
    if no and not yes:
        return False
    return None


# ──────────────────────────────────────────────
# Sıralı semptom soruları
# ──────────────────────────────────────────────

SYMPTOM_QUESTIONS = [
    ("COUGHING", "Son zamanlarda geçmeyen bir öksürük şikâyetiniz var mı?"),
    ("SHORTNESS_OF_BREATH", "Nefes darlığı yaşıyor musunuz?"),
    ("CHEST_PAIN", "Göğüs ağrınız var mı?"),
    ("WHEEZING", "Solunumunuzda hırıltı oluyor mu?"),
    ("FATIGUE", "Sık sık yorgunluk veya halsizlik hissediyor musunuz?"),
    ("HEMOPTYSIS", "Hiç kan tükürdüğünüz oldu mu?"),
    ("WEIGHT_LOSS", "Son dönemde istemsiz kilo kaybınız oldu mu?"),
]


# ──────────────────────────────────────────────
# Ajan
# ──────────────────────────────────────────────

class ConversationAgent:
    def __init__(self, channel: Channel, nlp_mode: str = "keyword"):
        self.ch = channel
        self.nlp_mode = nlp_mode
        self.evidence = {}
        self._load_engine()

    def _load_engine(self):
        from model.hybrid_bayesian_network import (
            build_hybrid_model, HybridLungCancerEngine
        )
        print("📦 Model yükleniyor...")
        self.engine = HybridLungCancerEngine(build_hybrid_model())
        print("   ✅ Hazır\n")

    # Çıkarımdan taşınacak tüm anahtarlar (model + meta)
    _CARRY = ("AGE", "GENDER", "SMOKING", "FAMILY_HISTORY", "ASBESTOS", "AIR_POLLUTION",
              "_province", "_age_exact", "_pack_years", "_cigs_per_day",
              "_years_smoked", "_years_quit")

    def _absorb(self, text):
        ext = extract_symptoms(text, mode=self.nlp_mode)
        for k in self._CARRY:
            if k in ext:
                self.evidence[k] = ext[k]
        return ext

    # --- Stage 1: Karşılama + demografi (İKİ soru) ---
    def collect_demographics(self):
        # Soru 1: yaş + cinsiyet
        self.ch.say("Merhaba. Sağlıklı bir risk analizi yapabilmem için öncelikle "
                    "yaşınızı ve cinsiyetinizi belirtir misiniz?")
        for attempt in range(3):
            self._absorb(self._heard())
            missing = [k for k in ("AGE", "GENDER") if k not in self.evidence]
            if not missing:
                break
            labels = {"AGE": "yaşınızı", "GENDER": "cinsiyetinizi"}
            if attempt < 2:
                self.ch.say("Şunu tam alamadım: " + ", ".join(labels[m] for m in missing)
                            + ". Tekrar belirtir misiniz?")

        # Soru 2: sigara durumu + sıklık/süre (paket-yıl)
        self.ch.say("Sigara kullanıyor musunuz? Kullanıyorsanız ya da bıraktıysanız, "
                    "günde kaç adet ve kaç yıl içtiğinizi de söyler misiniz?")
        for attempt in range(3):
            self._absorb(self._heard())
            if "SMOKING" in self.evidence:
                break
            if attempt < 2:
                self.ch.say("Sigara kullanım durumunuzu tam alamadım. İçiyor musunuz, "
                            "bıraktınız mı, yoksa hiç içmediniz mi?")

    # --- Stage 2: Semptomlar (sırayla) ---
    def collect_symptoms(self):
        self.ch.say("Teşekkürler. Şimdi size bazı belirtileri sırayla soracağım. "
                    "Lütfen 'evet' ya da 'hayır' şeklinde yanıtlayın.")
        for var, question in SYMPTOM_QUESTIONS:
            self.ch.say(question)
            ans = self._heard()
            yn = parse_yes_no(ans)
            if yn is None:
                # serbest cümleden çıkarmayı dene
                ext = extract_symptoms(post_process_medical_terms(ans), mode=self.nlp_mode)
                self.evidence[var] = 1 if ext.get(var) == 1 else 0
            else:
                self.evidence[var] = 1 if yn else 0

    # --- Stage 3: Yeni risk faktörleri ---
    def collect_risk_factors(self):
        # Aile öyküsü
        self.ch.say("Birinci derece akrabalarınızda (anne, baba, kardeş) "
                    "akciğer kanseri öyküsü var mı?")
        yn = parse_yes_no(self._heard())
        if yn is not None:
            self.evidence["FAMILY_HISTORY"] = 1 if yn else 0

        # Mesleki risk (asbest proxy)
        self.ch.say("Şu meslek gruplarından birinde uzun süre çalıştınız mı: "
                    "inşaat, yıkım, tersane, maden, yalıtım, oto tamir, "
                    "çimento veya eternit fabrikası?")
        yn = parse_yes_no(self._heard())
        if yn is not None:
            self.evidence["ASBESTOS"] = 1 if yn else 0

        # Hava kirliliği — il bazlı
        if "AIR_POLLUTION" not in self.evidence:
            self.ch.say("Hangi ilde yaşıyorsunuz?")
            ans = self._heard()
            prov = extract_province(ans)
            air = resolve_air_pollution(prov) if prov else {}
            if "AIR_POLLUTION" in air:
                self.evidence["AIR_POLLUTION"] = air["AIR_POLLUTION"]
                self.evidence["_province"] = air["province"]

    # --- Stage 4-5: Değerlendirme + sesli özet ---
    def assess_and_summarize(self):
        clean = {k: v for k, v in self.evidence.items() if not k.startswith("_")}
        # Tam kanıtı geçir (paket-yıl sigara düzeltmesi için); predict_risk içeride filtreler
        result = self.engine.predict_risk(self.evidence)
        score = result["risk_score"]
        level = result["risk_level_tr"]

        # Açıklanabilir özet (yumuşak dil — korkutmadan taramaya yönlendir)
        prov = self.evidence.get("_province")
        loc = f" {prov} ilinde yaşıyor olmanız" if prov else ""
        summary = (f"Değerlendirmeniz tamamlandı. Risk düzeyiniz: {level}, "
                   f"tahmini risk skoru yüzde {score:.0f}. ")
        if result.get("or_contributions"):
            etk = ", ".join(result["or_contributions"].keys())
            summary += f"Riskinizi artıran etkenler: {etk}.{(' ' + loc.strip() + ' bunlardan biri.') if loc else ''} "
        if result.get("smoking_adjustment"):
            summary += " " + result["smoking_adjustment"]
        summary += " " + result["recommendation_tr"]

        # Tarama uygunluğu (semptom skorundan BAĞIMSIZ) — düşük skor olsa bile önemli
        from model.screening import assess_screening_eligibility
        elig = assess_screening_eligibility(self.evidence)
        result["screening"] = elig
        if elig["eligible"] in (True, None):
            summary += " Ayrıca önemli bir not: " + elig["message_tr"]

        summary += (" Unutmayın, bu bir tarama ve farkındalık aracıdır, kesin tanı koymaz. "
                    "Ne kadar erken tarama, o kadar erken teşhis. "
                    "Detaylı raporunuzu indirmek için rapor butonuna basabilirsiniz.")
        self.ch.say(summary)
        return result, clean

    def _generate_report(self, result, clean):
        try:
            from report.report_generator import generate_report
            path = generate_report(result, clean, format="pdf")
            print(f"\n   📄 Rapor hazır: {path}")
            return path
        except Exception as e:
            print(f"   ⚠️  Rapor oluşturulamadı: {e}")
            return None

    def _heard(self) -> str:
        ans = self.ch.listen()
        if ans:
            print(f"   📝 Algılanan: \"{ans}\"")
        return ans or ""

    # --- Tüm akış ---
    def run(self):
        print("╔══════════════════════════════════════════════════════╗")
        print("║   🩺 PRAEVIDIO AI — Konuşmalı Risk Değerlendirme    ║")
        print("╚══════════════════════════════════════════════════════╝")
        self.collect_demographics()
        self.collect_symptoms()
        self.collect_risk_factors()
        result, clean = self.assess_and_summarize()
        # Rapora il adını da geçir (etiket için); model girişi 'clean' kalır
        self._generate_report(result, self.evidence)
        print(f"\n   📋 Toplanan kanıtlar: {clean}")
        return result


def main():
    p = argparse.ArgumentParser(description="Praevidio AI Konuşmalı Ajan")
    p.add_argument("--channel", choices=["text", "voice"], default="text")
    p.add_argument("--nlp-mode", choices=["keyword", "llm"], default=NLP_MODE)
    args = p.parse_args()

    agent = ConversationAgent(Channel(args.channel), nlp_mode=args.nlp_mode)
    agent.run()


if __name__ == "__main__":
    main()
