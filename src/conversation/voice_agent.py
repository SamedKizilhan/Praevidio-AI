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
        self._oai = None  # tek seferlik OpenAI istemcisi (bağlantı havuzu sızmasın)

    def _client(self):
        if self._oai is None:
            from openai import OpenAI
            self._oai = OpenAI(api_key=OPENAI_API_KEY, timeout=20)
        return self._oai

    def say(self, text: str):
        print(f"\n🤖 {text}", flush=True)
        if self.mode == "voice":
            self._tts(text)

    def listen(self, stt_hint: str = "") -> str:
        if self.mode == "voice":
            return self._record_and_transcribe(stt_hint)
        # text kanal
        try:
            return input("   🗣️  > ").strip()
        except EOFError:
            return ""

    # --- Voice yardımcıları ---
    def _tts(self, text: str):
        """OpenAI tts-1 ile seslendir, macOS'ta afplay ile oynat. Asla akışı kilitlemez."""
        if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
            return
        try:
            out = PROCESSED_DATA_DIR / "tts_tmp.mp3"
            with self._client().audio.speech.with_streaming_response.create(
                model="tts-1", voice="alloy", input=text
            ) as resp:
                resp.stream_to_file(str(out))
            subprocess.run(["afplay", str(out)], check=False, timeout=60)
        except Exception as e:
            print(f"   ⚠️  TTS atlandı (akış sürüyor): {e}", flush=True)

    def _record_and_transcribe(self, stt_hint: str = "") -> str:
        from stt.whisper_stt import transcribe_audio
        audio = self._record_until_enter()
        if not audio:
            return input("   🗣️  (ses alınamadı, yazınız) > ").strip()
        try:
            return transcribe_audio(audio, prompt=stt_hint)["text"]
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

    @staticmethod
    def _yn(text):
        """parse_yes_no'yu 1/0/None'a çevirir (belirsiz → None → tekrar sor)."""
        yn = parse_yes_no(text)
        return None if yn is None else (1 if yn else 0)

    @staticmethod
    def _is_never_smoker(text):
        """
        Hiç içmemiş mi? 'hayır kullanmıyorum / hiç içmedim' gibi olumsuzluk VAR ama
        bırakma ifadesi ('bıraktım', 'artık') ve miktar ('paket/adet') YOKSA → hiç içmemiş.
        """
        import re
        from model.screening import normalize_tr_numbers
        t = normalize_tr_numbers(text.lower().replace("̇", ""))
        if not t.strip():
            return False
        quit_signal = any(w in t for w in
                          ["bıraktım", "bırakalı", "bıraktı", "önce bırak", "bırakmış",
                           "eski içici", "artık", "önceden", "eskiden", "içerdim"])
        has_qty = bool(re.search(r"\d+\s*(?:paket|adet|tane|dal)", t)) or "paket" in t
        never = any(w in t for w in
                    ["içmedim", "içmemiş", "kullanmadım", "kullanmıyorum", "içmiyorum",
                     "içmem", "kullanmam", "hiç içme", "hiç kullan", "hiç sigara"])
        return never and not quit_signal and not has_qty

    @staticmethod
    def _parse_years(text):
        """Metinden yıl sayısı çıkarır ('on yıl önce' -> 10). Bulamazsa None."""
        import re
        from model.screening import normalize_tr_numbers
        m = re.search(r"(\d+)\s*(?:yıl|sene|yil)", normalize_tr_numbers(text.lower().replace("̇", "")))
        return int(m.group(1)) if m else None

    def _ask(self, question, parse, reask, stt_hint="", attempts=3):
        """
        Soruyu sorar; parse(metin) -> değer veya None. None ise (istenen türde
        cevap yok / sessizlik / halüsinasyon) en fazla `attempts` kez tekrar sorar.
        Hâlâ alınamazsa None döner (ilgili alan gözlenmemiş bırakılır).
        """
        self.ch.say(question)
        for i in range(attempts):
            val = parse(self._heard(stt_hint))
            if val is not None:
                return val
            if i < attempts - 1:
                self.ch.say(reask)
        return None

    # --- Stage 1: Karşılama + demografi (İKİ soru) ---
    def collect_demographics(self):
        demo_hint = "Kullanıcı yaşını ve cinsiyetini söylüyor, örneğin altmış yaşında erkek."
        smoke_hint = ("Kullanıcı sigara kullanımını anlatıyor, örneğin günde bir paket, "
                      "yirmi yıl, on yıl önce bıraktım, hiç içmedim.")

        # Soru 1: yaş + cinsiyet (eksikse tekrar sor)
        self.ch.say("Merhaba. Sağlıklı bir risk analizi yapabilmem için öncelikle "
                    "yaşınızı ve cinsiyetinizi belirtir misiniz?")
        for attempt in range(3):
            self._absorb(self._heard(demo_hint))
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
        smoke_ans = ""
        for attempt in range(3):
            smoke_ans = self._heard(smoke_hint)
            self._absorb(smoke_ans)
            if "SMOKING" in self.evidence:
                break
            if attempt < 2:
                self.ch.say("Sigara kullanım durumunuzu tam alamadım. İçiyor musunuz, "
                            "bıraktınız mı, yoksa hiç içmediniz mi?")

        # Hiç içmemiş → paket-yıl 0; "kaç yıl içtiniz / kaç yıl önce bıraktınız" SORULMAZ
        if self._is_never_smoker(smoke_ans):
            self.evidence["SMOKING"] = 0
            self.evidence["_pack_years"] = 0

        # Paket-yıl için "kaç yıl içtiniz" eksikse bir kez daha sor (içici/eski içici ise)
        if (self.evidence.get("SMOKING") is not None
                and self.evidence.get("_pack_years") is None
                and self.evidence.get("_years_smoked") is None):
            self.ch.say("Yaklaşık kaç yıl boyunca sigara içtiniz?")
            self._absorb(self._heard("Kullanıcı kaç yıl sigara içtiğini söylüyor, örneğin yirmi yıl."))
        # Günlük adet + içilen yıl varsa paket-yılı hesapla
        if (self.evidence.get("_pack_years") is None
                and "_cigs_per_day" in self.evidence and "_years_smoked" in self.evidence):
            self.evidence["_pack_years"] = round(
                self.evidence["_cigs_per_day"] / 20.0 * self.evidence["_years_smoked"], 1)

        # Eski içiciyse, kaç yıl önce bıraktığını sor (tarama uygunluğu + doz düzeltmesi için)
        smoked_before = (self.evidence.get("_pack_years") or 0) > 0 or "_cigs_per_day" in self.evidence
        if (self.evidence.get("SMOKING") == 0 and smoked_before
                and self.evidence.get("_years_quit") is None):
            ans = self._ask("Sigarayı kaç yıl önce bıraktınız?",
                            self._parse_years, "Kaç yıl önce bıraktığınızı tam alamadım; tekrar söyler misiniz?",
                            "Kullanıcı sigarayı kaç yıl önce bıraktığını söylüyor, örneğin on yıl önce.")
            if ans is not None:
                self.evidence["_years_quit"] = ans

    # --- Stage 2: Semptomlar (sırayla; belirsizse tekrar sor) ---
    def collect_symptoms(self):
        self.ch.say("Teşekkürler. Şimdi size bazı belirtileri sırayla soracağım. "
                    "Lütfen 'evet' ya da 'hayır' şeklinde yanıtlayın.")
        hint = "Kullanıcı evet veya hayır diyor."
        reask = "Sizi tam anlayamadım; lütfen 'evet' ya da 'hayır' deyin."
        for var, question in SYMPTOM_QUESTIONS:
            def parse(text, _var=var):
                v = self._yn(text)
                if v is not None:
                    return v
                ext = extract_symptoms(post_process_medical_terms(text), mode=self.nlp_mode)
                return 1 if ext.get(_var) == 1 else None
            val = self._ask(question, parse, reask, hint)
            if val is not None:
                self.evidence[var] = val
            # belirsiz kalırsa: gözlenmemiş bırakılır (nötr — 0 varsaymıyoruz)

    # --- Stage 3: Yeni risk faktörleri ---
    def collect_risk_factors(self):
        yn_hint = "Kullanıcı evet veya hayır diyor."
        yn_reask = "Sizi tam anlayamadım; lütfen 'evet' ya da 'hayır' deyin."

        fam = self._ask("Birinci derece akrabalarınızda (anne, baba, kardeş) "
                        "akciğer kanseri öyküsü var mı?", self._yn, yn_reask, yn_hint)
        if fam is not None:
            self.evidence["FAMILY_HISTORY"] = fam

        asb = self._ask("Şu meslek gruplarından birinde uzun süre çalıştınız mı: "
                        "inşaat, yıkım, tersane, maden, yalıtım, oto tamir, "
                        "çimento veya eternit fabrikası?", self._yn, yn_reask, yn_hint)
        if asb is not None:
            self.evidence["ASBESTOS"] = asb

        # Hava kirliliği — il bazlı (tanınan bir il gelene kadar tekrar sor)
        if "AIR_POLLUTION" not in self.evidence:
            prov = self._ask(
                "Hangi ilde yaşıyorsunuz?",
                lambda t: extract_province(t) or None,
                "İlinizi tam alamadım; yaşadığınız ili tekrar söyler misiniz?",
                "Kullanıcı bir Türkiye ilinin adını söylüyor, örneğin Manisa, Ankara, İzmir.")
            if prov:
                air = resolve_air_pollution(prov)
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

    def _generate_report(self, result, evidence):
        try:
            from report.report_generator import generate_report
            path = generate_report(result, evidence, format="pdf", engine=self.engine)
            print(f"\n   📄 Rapor hazır: {path}")
            return path
        except Exception as e:
            print(f"   ⚠️  Rapor oluşturulamadı: {e}")
            return None

    def _heard(self, stt_hint: str = "") -> str:
        ans = self.ch.listen(stt_hint)
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
