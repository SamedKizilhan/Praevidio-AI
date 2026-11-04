# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — Konuşma kaydı (agent: / user: etiketli düz metin)
================================================================
Her görüşme (CLI ya da API/PWA) data/conversations/ altına satır satır yazılır:

    # Praevidio konuşma kaydı
    # oturum: 20261104-213015_ab12cd  ·  model: v3 (3.1)  ·  nlp: keyword  ·  kanal: pwa-voice
    agent: Merhaba. Sağlıklı bir risk analizi yapabilmem için …
    user: 45 yaşındayım erkeğim                      ← sesli cevaplar ayrıca "# ses → STT" ile işaretlenir
    agent: Sigara kullanıyor musunuz? …
    # --- sonuç ---
    # 6 yıllık: %0,14 (Düşük) · tam: %0,84 (Düşük) · alarm: urgent
    # kanıt: {"AGE": 0, ...}

Hata bildirmek için kaydın istediğiniz yerine ">>" ile başlayan not satırı ekleyin:

    agent: Şunları not ettim: … yaklaşık 5 paket-yıl. Doğru mu?
    user: 5 paket-yıl ne demek ki?
    >> burada açıklamadan bir sonraki soruya geçti

Kayıt tools/replay_conversation.py ile yeniden oynatılır (aynı user: satırları ajana verilir,
yeni ajan cevapları eskileriyle karşılaştırılır). "# beklenen: ANAHTAR=DEĞER" satırları
otomatik kontrol olur → tests/conversations/ altındaki kayıtlar regresyon testidir.

Gizlilik: kayıtlar sağlık verisidir; data/conversations/ .gitignore'dadır, ses saklanmaz.
Kapatmak için PRAEVIDIO_SAVE_TRANSCRIPTS=0.
"""
import json
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT_DIR = Path(os.getenv("PRAEVIDIO_TRANSCRIPT_DIR", ROOT / "data" / "conversations"))
SAVE_TRANSCRIPTS = os.getenv("PRAEVIDIO_SAVE_TRANSCRIPTS", "1") not in ("0", "false", "False")


def _one_line(text: str) -> str:
    return re.sub(r"\s*\n\s*", " ⏎ ", (text or "").strip())


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + uuid.uuid4().hex[:6]


class TranscriptWriter:
    """Satırları anında diske yazar (yarıda kalan/çöken görüşmeler de kayıtlı kalır)."""

    def __init__(self, session_id: str, meta: dict, directory: Path = None, enabled: bool = None):
        self.enabled = SAVE_TRANSCRIPTS if enabled is None else enabled
        self.session_id = session_id
        self.lines = []
        self.path = None
        self._lock = threading.Lock()
        if self.enabled:
            d = Path(directory or TRANSCRIPT_DIR)
            d.mkdir(parents=True, exist_ok=True)
            self.path = d / f"{session_id}.txt"
        head = ["# Praevidio konuşma kaydı",
                "# oturum: " + session_id + "  ·  " + "  ·  ".join(f"{k}: {v}" for k, v in meta.items() if v),
                "# Hata notu için ilgili satırın altına \">>\" ile başlayan satır ekleyin."]
        for h in head:
            self._write(h)

    def _write(self, line: str):
        with self._lock:
            self.lines.append(line)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

    def agent(self, text: str):
        self._write("agent: " + _one_line(text))

    def user(self, text: str, kind: str = None):
        if kind == "audio":
            self._write("# ses → STT")
        self._write("user: " + _one_line(text))

    def note(self, text: str):
        self._write("# " + _one_line(text))

    def finish(self, result: dict = None, evidence: dict = None, report_path=None):
        self._write("# --- sonuç ---")
        if result and result.get("model_revision"):
            self._write(f"# model sürümü: {result['model_revision']}")
        if result:
            def pct(x):
                return (f"{x:.2f}" if x < 10 else f"{x:.1f}").replace(".", ",")
            if result.get("risk_6y_factors") is not None:
                self._write(f"# 6 yıllık: %{pct(result['risk_6y_factors'])} "
                            f"({result.get('risk_level_factors_display_tr') or result.get('risk_level_factors_tr')})"
                            f" · tam: %{pct(result['risk_score'])} ({result.get('risk_level_tr')})"
                            f" · alarm: {(result.get('alarm') or {}).get('level')}")
            else:
                self._write(f"# skor: %{pct(result['risk_score'])} ({result.get('risk_level_tr')})")
        sa = (result or {}).get("symptom_assessment")
        if sa:
            self._write(f"# belirti katmanı: %{pct(sa['percent'])} ({sa['level']}, eşik %{sa['threshold'] * 100:g})"
                        f" · kısa sürede hekim: {result.get('urgent_assessment')}")
        if result and result.get("relative_risk_peers") is not None:
            self._write(f"# göreli risk: ×{result['relative_risk_peers']}"
                        + (f" · projeksiyon: {result['projection']['message_tr']}" if result.get("projection") else ""))
        if evidence is not None:
            self._write("# kanıt: " + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        if report_path:
            self._write(f"# rapor: {Path(report_path).name}")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


class LoggingChannel:
    """Ajanın kanalını sarar: say() → agent:, listen() → user:. Diğer her şey aynen geçer."""

    def __init__(self, channel, writer: TranscriptWriter):
        self._ch = channel
        self._w = writer

    def say(self, text: str):
        self._w.agent(text)
        return self._ch.say(text)

    def listen(self, stt_hint: str = "") -> str:
        ans = self._ch.listen(stt_hint)
        kind = getattr(self._ch, "last_input_kind", None)
        if kind is None and getattr(self._ch, "mode", None) == "voice":
            kind = "audio"
        self._w.user(ans or "", kind=kind)
        return ans

    def __getattr__(self, name):
        return getattr(self._ch, name)


# ──────────────────────────────────────────────
# Okuma (yeniden oynatma / regresyon testleri)
# ──────────────────────────────────────────────

def parse(text: str) -> dict:
    """
    Kaydı ayrıştırır → {"meta": {...}, "turns": [{"role", "text", "notes": [...]}],
                        "expect": [(anahtar, değer)], "notes": [(tur_indeksi, not)]}
    ">>" satırları önceki tura not olarak bağlanır; "# beklenen: A=B" beklenti olur.
    """
    meta, turns, expect, notes = {}, [], [], []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        s = line.strip()
        if s.startswith(">>"):
            note = s[2:].strip()
            notes.append((len(turns) - 1, note))
            if turns:
                turns[-1]["notes"].append(note)
            continue
        if s.startswith("#"):
            body = s[1:].strip()
            if body.startswith("oturum:"):
                for part in body.split("  ·  "):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        meta[k.strip()] = v.strip()
            m = re.match(r"beklenen:\s*([^=]+?)\s*=\s*(.+)$", body)
            if m:
                expect.append((m.group(1).strip(), m.group(2).strip()))
            continue
        m = re.match(r"(agent|user)\s*:\s?(.*)$", s, re.I)
        if m:
            turns.append({"role": m.group(1).lower(), "text": m.group(2), "notes": []})
    return {"meta": meta, "turns": turns, "expect": expect, "notes": notes}


def read(path) -> dict:
    return parse(Path(path).read_text(encoding="utf-8"))
