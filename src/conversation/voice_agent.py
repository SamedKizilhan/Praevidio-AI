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
  python src/conversation/voice_agent.py --channel text --model v2   # eski model

v3 akışı (Güz 2026): açık uçlu şikâyet sorusu → yalnız eksik belirtiler tek tek,
"bilmiyorum" ile atlama, demografi onayı/düzeltme, KOAH sorusu, iki katmanlı
sesli özet (6 yıllık tarama riski + belirti alarmı). Model: hybrid_bayesian_network_v3.
"""

import sys
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    OPENAI_API_KEY, NLP_MODE, PROCESSED_DATA_DIR,
    TTS_MODEL, TTS_VOICE, TTS_SPEED, TTS_PROVIDER, EDGE_TTS_VOICE,
    REC_AUTOSTOP, REC_SILENCE_THRESHOLD, REC_SILENCE_SECONDS, REC_WARMUP_SEC,
)
from nlp.symptom_extractor import (
    extract_symptoms, resolve_air_pollution, extract_province
)
from stt.whisper_stt import post_process_medical_terms


# ──────────────────────────────────────────────
# Ücretsiz Türkçe nöral TTS (Microsoft Edge sesleri) — opsiyonel sağlayıcı
# ──────────────────────────────────────────────

def synthesize_edge(text: str, out: Path, voice: str = "tr-TR-EmelNeural") -> bool:
    """edge-tts ile sentez (pip install edge-tts). Anahtar gerektirmez, ana dili Türkçe sesler.
    Not: resmî olmayan bir istemcidir; demo/dinleme testi için uygundur, üretimde Azure Speech."""
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("   ⚠️  edge-tts kurulu değil: pip install edge-tts  (ya da PRAEVIDIO_TTS_PROVIDER=openai)")
        return False
    try:
        asyncio.run(edge_tts.Communicate(text, voice).save(str(out)))
        return out.exists() and out.stat().st_size > 0
    except Exception as e:
        print(f"   ⚠️  Edge TTS sentez atlandı: {e}", flush=True)
        return False


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
    def _cache_path(self, text: str) -> Path:
        import hashlib
        voice_id = EDGE_TTS_VOICE if TTS_PROVIDER == "edge" else f"{TTS_MODEL}|{TTS_VOICE}|{TTS_SPEED}"
        key = hashlib.sha1(
            f"{TTS_PROVIDER}|{voice_id}|{text}".encode("utf-8")
        ).hexdigest()[:16]
        d = PROCESSED_DATA_DIR / "tts_cache"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{key}.mp3"

    def _synthesize(self, text: str, out: Path) -> bool:
        """Metni seçili TTS sağlayıcısıyla sentezleyip `out` dosyasına yazar. Başarı: True.
        Sağlayıcı config.TTS_PROVIDER: "openai" | "edge" (ücretsiz Türkçe nöral ses)."""
        if TTS_PROVIDER == "edge":
            return synthesize_edge(text, out, EDGE_TTS_VOICE)
        try:
            kwargs = dict(model=TTS_MODEL, voice=TTS_VOICE, input=text,
                          response_format="mp3")
            if TTS_MODEL.startswith("tts-1") and abs(TTS_SPEED - 1.0) > 1e-6:
                kwargs["speed"] = TTS_SPEED   # speed yalnızca tts-1/tts-1-hd'de var
            with self._client().audio.speech.with_streaming_response.create(**kwargs) as resp:
                resp.stream_to_file(str(out))
            return out.exists() and out.stat().st_size > 0
        except Exception as e:
            print(f"   ⚠️  TTS sentez atlandı: {e}", flush=True)
            return False

    def prewarm(self, texts):
        """Sabit istemleri önceden sentezleyip diske önbellekler (demo'da anında oynar).
        Zoom/yavaş internet gecikmesini ve takılmaları büyük ölçüde ortadan kaldırır."""
        if self.mode != "voice":
            return
        if TTS_PROVIDER == "openai" and (not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your")):
            return
        missing = [t for t in dict.fromkeys(texts) if t and not self._cache_path(t).exists()]
        if not missing:
            return
        print(f"   🔥 TTS önbelleği ısıtılıyor ({len(missing)} istem)…", flush=True)
        for t in missing:
            self._synthesize(t, self._cache_path(t))
        print("   ✅ TTS önbelleği hazır.", flush=True)

    def _tts(self, text: str):
        """Doğal sesle seslendir. Sabit istemler diskten ANINDA oynar; yenileri
        bir kez sentezlenip önbelleğe alınır. macOS'ta afplay ile çalınır."""
        if TTS_PROVIDER == "openai" and (not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your")):
            return
        try:
            cached = self._cache_path(text)
            if not cached.exists():
                if not self._synthesize(text, cached):
                    return
            subprocess.run(["afplay", str(cached)], check=False, timeout=120)
        except Exception as e:
            print(f"   ⚠️  TTS atlandı (akış sürüyor): {e}", flush=True)

    def _record_and_transcribe(self, stt_hint: str = "") -> str:
        from stt.whisper_stt import transcribe_audio
        audio = self._record()
        if not audio:
            return input("   🗣️  (ses alınamadı, yazınız) > ").strip()
        try:
            return transcribe_audio(audio, prompt=stt_hint)["text"]
        except Exception as e:
            print(f"   ⚠️  STT hatası: {e}")
            return ""

    def _record(self, max_seconds: int = 60) -> str:
        """
        Mikrofondan kaydeder. İKİ mod:
          • Varsayılan (güvenilir): baştan SONUNA kadar TAM kaydeder, ses HİÇ kırpılmaz;
            kullanıcı ENTER'a basınca durur. Mikrofon açılış gecikmesi için kısa ısınma
            payı bırakılır, böylece "Konuşabilirsiniz" yazısı çıkınca kayıt gerçekten açıktır.
          • Otomatik durma (PRAEVIDIO_REC_AUTOSTOP=1): konuşma bitince sessizlikte kendi durur.
            (Baş kırpmasını önlemek için hassas eşik kullanılır; gürültülü ortamda Whisper'ı
            zorlayabilir, o yüzden varsayılan KAPALI.)
        """
        import os
        import time
        import shutil
        import signal
        import sys
        import select
        import subprocess
        from datetime import datetime
        from config import PROCESSED_DATA_DIR

        if shutil.which("rec") is None:
            print("   ⚠️  Ses kaydı için 'sox' gerekli (brew install sox). Şimdilik yazınız.")
            return ""

        rec_dir = PROCESSED_DATA_DIR / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        out = str(rec_dir / f"rec_{datetime.now():%Y%m%d_%H%M%S}.wav")

        cmd = ["rec", "-q", out, "rate", "16000", "channels", "1", "trim", "0", str(max_seconds)]
        if REC_AUTOSTOP:
            # baştan TAM kaydet; yalnızca SONDA uzun sessizlikte dur (baş KIRPILMAZ)
            cmd = ["rec", "-q", out, "rate", "16000", "channels", "1",
                   "silence", "1", "0.1", "0%",
                   "1", str(REC_SILENCE_SECONDS), REC_SILENCE_THRESHOLD,
                   "trim", "0", str(max_seconds)]

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Mikrofon gerçekten açılana kadar kısa bekle (sync sorununu önler)
        time.sleep(REC_WARMUP_SEC)
        if REC_AUTOSTOP:
            print("   🔴 Konuşabilirsiniz… bitince kendi duracak (ya da ENTER).", flush=True)
        else:
            print("   🔴 Konuşabilirsiniz… bitince ENTER'a basın.", flush=True)

        stdin_ok = sys.stdin is not None and sys.stdin.isatty()
        while proc.poll() is None:
            if stdin_ok and select.select([sys.stdin], [], [], 0.2)[0]:
                sys.stdin.readline()                 # ENTER → durdur/erken bitir
                proc.send_signal(signal.SIGINT)
                break
            elif not stdin_ok:
                try:
                    proc.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        if os.path.exists(out) and os.path.getsize(out) > 1000:
            print("   ⏹️  Kayıt alındı.", flush=True)
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


# "Bilmiyorum / emin değilim / geç" → alan GÖZLENMEMİŞ bırakılır, tekrar sorulmaz
_SKIP = ["bilmiyorum", "bilemiyorum", "emin değilim", "hatırlamıyorum", "geç", "atla",
         "cevap vermek istemiyorum", "söylemek istemiyorum", "fikrim yok"]


def is_skip(text: str) -> bool:
    t = text.lower().replace("̇", "")
    return any(w in t for w in _SKIP)


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
_SYMPTOM_LABELS = {
    "COUGHING": "öksürük", "SHORTNESS_OF_BREATH": "nefes darlığı", "CHEST_PAIN": "göğüs ağrısı",
    "WHEEZING": "hırıltı", "FATIGUE": "halsizlik", "HEMOPTYSIS": "kan tükürme",
    "WEIGHT_LOSS": "kilo kaybı",
}

# Demo'da değişmeyen istemler — başlangıçta önceden seslendirilip önbelleğe alınır
# (string'ler say() çağrılarıyla birebir aynı olmalı ki önbelleğe düşsünler).
STATIC_TTS_PROMPTS = [q for _, q in SYMPTOM_QUESTIONS] + [
    "Merhaba. Sağlıklı bir risk analizi yapabilmem için öncelikle "
    "yaşınızı ve cinsiyetinizi belirtir misiniz?",
    "Sigara kullanıyor musunuz? Kullanıyorsanız ya da bıraktıysanız, "
    "günde kaç adet ve kaç yıl içtiğinizi de söyler misiniz?",
    "Yaklaşık kaç yıl boyunca sigara içtiniz?",
    "Teşekkürler. Şimdi size bazı belirtileri sırayla soracağım. "
    "Lütfen 'evet' ya da 'hayır' şeklinde yanıtlayın.",
    "Sizi tam anlayamadım; lütfen 'evet' ya da 'hayır' deyin.",
    "Birinci derece akrabalarınızda (anne, baba, kardeş) "
    "akciğer kanseri öyküsü var mı?",
    "Şu meslek gruplarından birinde uzun süre çalıştınız mı: "
    "inşaat, yıkım, tersane, maden, yalıtım, oto tamir, "
    "çimento veya eternit fabrikası?",
    "Hangi ilde yaşıyorsunuz?",
    "İlinizi tam alamadım; yaşadığınız ili tekrar söyler misiniz?",
    "Sigarayı kaç yıl önce bıraktınız?",
    "Sigara kullanım durumunuzu tam alamadım. İçiyor musunuz, "
    "bıraktınız mı, yoksa hiç içmediniz mi?",
    "Kaç yıl önce bıraktığınızı tam alamadım; tekrar söyler misiniz?",
    # v3 akışı
    "Teşekkürler. Son haftalarda sizi rahatsız eden şikâyetleriniz neler? "
    "Örneğin öksürük, nefes darlığı, göğüs ağrısı, halsizlik gibi; "
    "yoksa 'şikâyetim yok' diyebilirsiniz.",
    "Şimdi birkaç belirtiyi tek tek soracağım. Lütfen 'evet', 'hayır' ya da "
    "'bilmiyorum' şeklinde yanıtlayın.",
    "Doktorunuz size KOAH, amfizem veya kronik bronşit tanısı koydu mu?",
    "Peki, hangisi yanlıştı? Doğrusunu söyler misiniz?",
    "Anladım, düzelttim.",
    "Peki daha önce hiç sigara içtiniz mi?",
    "Sizi tam anlayamadım; daha önce içtiniz mi, hiç içmediniz mi?",
    "Günde ortalama kaç adet sigara içiyorsunuz ya da içiyordunuz?",
]


# ──────────────────────────────────────────────
# Ajan
# ──────────────────────────────────────────────

class ConversationAgent:
    def __init__(self, channel: Channel, nlp_mode: str = "keyword", model_version: str = "v3"):
        self.ch = channel
        self.nlp_mode = nlp_mode
        self.model_version = model_version
        self.evidence = {}
        self._load_engine()

    def _load_engine(self):
        from model.hybrid_bayesian_network_v3 import load_engine
        print(f"📦 Model yükleniyor ({self.model_version})...")
        self.engine = load_engine(self.model_version)
        print("   ✅ Hazır\n")
        # Sabit istemleri önceden seslendirip önbelleğe al → demo'da anında oynar,
        # Zoom/yavaş internet gecikmesi ve takılmalar ortadan kalkar.
        self.ch.prewarm(STATIC_TTS_PROMPTS)

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
            heard = self._heard(stt_hint)
            if is_skip(heard):          # "bilmiyorum" → gözlenmemiş bırak, bezdirme
                return None
            val = parse(heard)
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
            yn = parse_yes_no(smoke_ans)         # yalın "evet" → aktif içici
            if yn is True:
                self.evidence["SMOKING"] = 1
                break
            if yn is False:                      # yalın "hayır" → eski mi, hiç mi?
                before = self._ask("Peki daha önce hiç sigara içtiniz mi?", self._yn,
                                   "Sizi tam anlayamadım; daha önce içtiniz mi, hiç içmediniz mi?",
                                   "Kullanıcı evet veya hayır diyor.")
                self.evidence["SMOKING"] = 0
                if before == 0:
                    self.evidence["_pack_years"] = 0
                break
            if attempt < 2:
                self.ch.say("Sigara kullanım durumunuzu tam alamadım. İçiyor musunuz, "
                            "bıraktınız mı, yoksa hiç içmediniz mi?")

        # Hiç içmemiş → paket-yıl 0; "kaç yıl içtiniz / kaç yıl önce bıraktınız" SORULMAZ
        if self._is_never_smoker(smoke_ans):
            self.evidence["SMOKING"] = 0
            self.evidence["_pack_years"] = 0

        # Günlük adet eksikse sor (paket-yıl = adet/20 × yıl; tarama uygunluğu için gerekli)
        if (self.evidence.get("SMOKING") is not None
                and self.evidence.get("_pack_years") is None
                and self.evidence.get("_cigs_per_day") is None):
            from model.screening import parse_pack_years
            got = parse_pack_years(self._heard_after(
                "Günde ortalama kaç adet sigara içiyorsunuz ya da içiyordunuz?",
                "Kullanıcı günde kaç sigara içtiğini söylüyor, örneğin günde bir paket, on tane."))
            if got.get("_cigs_per_day") is not None:
                self.evidence["_cigs_per_day"] = got["_cigs_per_day"]

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

        # Onay: yanlış anlaşılan yaş/cinsiyet/sigara bilgisi tüm skoru bozar → kısa teyit
        self.confirm_demographics()

    # --- Stage 1b: Demografi onayı (düzeltme imkânı) ---
    _AGE_LBL = {0: "55 yaş altı", 1: "55-59 yaş", 2: "60-64 yaş", 3: "65-69 yaş", 4: "70 yaş ve üzeri"}

    def _demographics_sentence(self) -> str:
        e = self.evidence
        parts = []
        if "_age_exact" in e:
            parts.append(f"{e['_age_exact']} yaşında")
        elif "AGE" in e:
            parts.append(self._AGE_LBL[e["AGE"]])
        if "GENDER" in e:
            parts.append("erkek" if e["GENDER"] == 1 else "kadın")
        if e.get("SMOKING") == 1:
            parts.append("aktif sigara içiyor")
        elif e.get("SMOKING") == 0:
            parts.append("hiç içmemiş" if e.get("_pack_years") == 0 else "sigarayı bırakmış")
        if e.get("_pack_years"):
            parts.append(f"yaklaşık {e['_pack_years']:.0f} paket-yıl")
        if e.get("_years_quit") is not None:
            parts.append(f"{e['_years_quit']} yıl önce bırakmış")
        return ", ".join(parts)

    def confirm_demographics(self):
        sent = self._demographics_sentence()
        if not sent:
            return
        ans = self._heard_after(f"Şunları not ettim: {sent}. Doğru mu?",
                                "Kullanıcı evet veya hayır diyor.")
        if parse_yes_no(ans) is False:
            self.ch.say("Peki, hangisi yanlıştı? Doğrusunu söyler misiniz?")
            fix = self._heard("Kullanıcı yaşını, cinsiyetini veya sigara kullanımını düzeltiyor.")
            # Düzeltme cümlesinde ne geçiyorsa yalnız onu güncelle (diğer alanlar korunur)
            ext = extract_symptoms(fix, mode=self.nlp_mode)
            for k in self._CARRY:
                if k in ext:
                    self.evidence[k] = ext[k]
            if self._is_never_smoker(fix):
                self.evidence["SMOKING"] = 0
                self.evidence["_pack_years"] = 0
            if "_cigs_per_day" in ext or "_years_smoked" in ext:
                c = self.evidence.get("_cigs_per_day"); y = self.evidence.get("_years_smoked")
                if c is not None and y is not None:
                    self.evidence["_pack_years"] = round(c / 20.0 * y, 1)
            self.ch.say("Anladım, düzelttim.")

    def _heard_after(self, question: str, hint: str = "") -> str:
        self.ch.say(question)
        return self._heard(hint)

    # --- Stage 2: Semptomlar — önce AÇIK soru, sonra yalnız eksikler tek tek ---
    def collect_symptoms(self):
        # 2a) Açık uçlu: kullanıcı kendi kelimeleriyle anlatır; LLM/keyword çıkarımı
        ans = self._heard_after(
            "Teşekkürler. Son haftalarda sizi rahatsız eden şikâyetleriniz neler? "
            "Örneğin öksürük, nefes darlığı, göğüs ağrısı, halsizlik gibi; "
            "yoksa 'şikâyetim yok' diyebilirsiniz.",
            "Kullanıcı şikâyetlerini anlatıyor: öksürük, balgam, kan tükürme, nefes darlığı, "
            "hırıltı, göğüs ağrısı, halsizlik, kilo kaybı; ya da şikâyeti yok diyor.")
        if ans and not is_skip(ans):
            ext = extract_symptoms(post_process_medical_terms(ans), mode=self.nlp_mode)
            for var, _ in SYMPTOM_QUESTIONS:
                v = ext.get(var)
                # keyword modu bahsedilmeyeni 0 döndürür → yalnız 1'leri al;
                # llm modu açık inkârı 0, bahsedilmeyeni null döndürür → 0'ı da al
                if v == 1 or (v == 0 and self.nlp_mode == "llm"):
                    self.evidence[var] = v
            found = [q for v, q in _SYMPTOM_LABELS.items() if self.evidence.get(v) == 1]
            if found:
                self.ch.say("Şunları not ettim: " + ", ".join(found) + ".")

        # 2b) Söylenmeyenleri tek tek sor ("bilmiyorum" → atlanır, gözlenmemiş kalır)
        remaining = [(v, q) for v, q in SYMPTOM_QUESTIONS if v not in self.evidence]
        if remaining:
            self.ch.say("Şimdi birkaç belirtiyi tek tek soracağım. Lütfen 'evet', 'hayır' ya da "
                        "'bilmiyorum' şeklinde yanıtlayın.")
        hint = "Kullanıcı evet, hayır veya bilmiyorum diyor."
        reask = "Sizi tam anlayamadım; lütfen 'evet' ya da 'hayır' deyin."
        for var, question in remaining:
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

        # KOAH / kronik bronşit tanısı (yalnız v3 modelinde düğüm var)
        if self.model_version != "v2":
            copd = self._ask("Doktorunuz size KOAH, amfizem veya kronik bronşit tanısı koydu mu?",
                             self._yn, yn_reask, yn_hint)
            if copd is not None:
                self.evidence["COPD"] = copd

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
        if result.get("model_version") == "v3":
            p6 = result["risk_6y_factors"]
            summary = (f"Değerlendirmeniz tamamlandı. Risk faktörlerinize göre önümüzdeki altı yıl "
                       f"için tahmini riskiniz yüzde {p6:.1f}; bu, {result['risk_level_factors_tr'].lower()} "
                       f"grubuna giriyor. ")
            if abs(score - p6) >= 0.5:
                summary += f"Belirtilerinizle birlikte skor yüzde {score:.1f} ({level.lower()}). "
            # (alarm varsa recommendation_tr zaten acil sevk dilinde — tekrar edilmez)
        else:
            summary = (f"Değerlendirmeniz tamamlandı. Risk düzeyiniz: {level}, "
                       f"tahmini risk skoru yüzde {score:.0f}. ")
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
    p.add_argument("--model", choices=["v2", "v3"], default="v3",
                   help="risk modeli: v3 (latent semptomatik + KOAH) | v2 (geçen dönem)")
    args = p.parse_args()

    agent = ConversationAgent(Channel(args.channel), nlp_mode=args.nlp_mode,
                              model_version=args.model)
    agent.run()


if __name__ == "__main__":
    main()
