# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — API oturum yöneticisi
====================================
CLI'daki konuşma ajanı (conversation/voice_agent.py) OLDUĞU GİBİ kullanılır; akış
yeniden yazılmaz. Her oturum kendi iş parçacığında bir ConversationAgent çalıştırır.
Ajan bir şey söylediğinde (say) mesaj kutusuna düşer; kullanıcıdan cevap beklediğinde
(listen) iş parçacığı durur ve API isteği o ana kadarki mesajlarla geri döner. Bir
sonraki /turn isteği cevabı kuyruğa koyar, ajan kaldığı yerden devam eder.

    istemci ──POST /sessions──────────▶ yeni oturum, ajan ilk soruyu sorup bekler
           ◀── {messages, awaiting_input, hint}
    istemci ──POST /sessions/{id}/turn─▶ cevap kuyruğa → ajan ilerler → tekrar bekler
           ◀── {messages, awaiting_input | finished + result}

Böylece CLI (metin/ses) ve API (Flutter/web) AYNI durum makinesini paylaşır.
"""
import threading
import time
import uuid
import queue
from dataclasses import dataclass, field

from conversation.voice_agent import Channel, ConversationAgent

IDLE_TIMEOUT_S = 15 * 60       # bu kadar cevapsız kalan oturum kapanır
TURN_TIMEOUT_S = 90            # bir turda ajanın bir sonraki soruya ulaşması için azami süre
MAX_SESSIONS = 50              # bellek koruması (MVP)


class SessionExpired(Exception):
    """Kullanıcı IDLE_TIMEOUT_S boyunca cevap vermedi."""


class QueueChannel(Channel):
    """Ajanın say/listen çağrılarını iş parçacıkları arası kuyruğa çeviren kanal."""

    def __init__(self):
        super().__init__(mode="api")        # 'api': CLI'daki mikrofon/afplay yok; TTS'i API sunar
        self._inbox: "queue.Queue[str]" = queue.Queue()
        self._out: list = []
        self._cv = threading.Condition()
        self.waiting = False                # ajan şu an kullanıcı cevabı mı bekliyor?
        self.hint = ""                      # beklenen cevap için STT ipucu
        self.finished = False
        self.last_input_kind = None         # "audio" → kayıtta "# ses → STT" işareti

    # --- ajan tarafı (oturum iş parçacığı) ---
    def say(self, text: str):
        print(f"\n🤖 {text}", flush=True)
        with self._cv:
            self._out.append(text)

    def listen(self, stt_hint: str = "") -> str:
        with self._cv:
            self.hint = stt_hint
            self.waiting = True
            self._cv.notify_all()
        try:
            text = self._inbox.get(timeout=IDLE_TIMEOUT_S)
        except queue.Empty:
            raise SessionExpired()
        with self._cv:
            self.waiting = False
        return text

    def close(self):
        with self._cv:
            self.finished = True
            self.waiting = False
            self._cv.notify_all()

    # --- API tarafı (istek iş parçacığı) ---
    def submit(self, text: str):
        with self._cv:
            self.waiting = False
        self._inbox.put(text)

    def wait_turn(self, timeout: float = TURN_TIMEOUT_S) -> list:
        """Ajan tekrar cevap bekleyene ya da bitene kadar bekler; biriken mesajları döndürür."""
        with self._cv:
            self._cv.wait_for(lambda: self.waiting or self.finished, timeout=timeout)
            msgs, self._out = self._out, []
        return msgs


class LockedEngine:
    """Paylaşılan risk motoru için kilit: pgmpy çıkarımı oturumlar arasında sıralı çalışsın."""

    def __init__(self, engine):
        self._engine = engine
        self._lock = threading.Lock()

    def predict_risk(self, evidence: dict) -> dict:
        with self._lock:
            return self._engine.predict_risk(evidence)

    def __getattr__(self, name):            # model, inference, RISK_LEVELS … aynen geçer
        return getattr(self._engine, name)


@dataclass
class Session:
    id: str
    channel: QueueChannel
    agent: ConversationAgent
    model_version: str
    nlp_mode: str
    created: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    error: str = ""
    expired: bool = False
    thread: threading.Thread = None
    transcript: list = field(default_factory=list)   # [{"role": "agent"|"user", "text": ...}]

    @property
    def status(self) -> str:
        if self.error:
            return "error"
        if self.expired:
            return "expired"
        if self.channel.finished:
            return "finished"
        return "awaiting_input" if self.channel.waiting else "processing"


class SessionManager:
    def __init__(self, engines: dict):
        self.engines = {k: LockedEngine(v) for k, v in engines.items()}
        self._sessions: dict = {}
        self._lock = threading.Lock()

    def _purge(self):
        now = time.time()
        with self._lock:
            for sid in [s.id for s in self._sessions.values()
                        if s.status in ("finished", "error", "expired") and now - s.last_active > 3600
                        or now - s.last_active > IDLE_TIMEOUT_S + 60]:
                self._sessions.pop(sid, None)

    def create(self, model_version: str = "v3", nlp_mode: str = "keyword", client: str = None) -> Session:
        self._purge()
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                raise RuntimeError("Sunucu meşgul: aktif oturum sınırına ulaşıldı.")
        ch = QueueChannel()
        from conversation.transcript import new_session_id
        sid = new_session_id()                           # = kayıt dosyasının adı (data/conversations/<sid>.txt)
        agent = ConversationAgent(ch, nlp_mode=nlp_mode, model_version=model_version,
                                  engine=self.engines[model_version], session_id=sid,
                                  transcript_meta={"kanal": client or "api"})
        sess = Session(id=sid, channel=ch, agent=agent,
                       model_version=model_version, nlp_mode=nlp_mode)

        def _run():
            try:
                agent.run()
            except SessionExpired:
                sess.expired = True
                agent.transcript.note("oturum yarıda kaldı: süre aşımı (kullanıcı cevap vermedi)")
            except Exception as e:                       # ajan hatası istemciye raporlanır
                sess.error = f"{type(e).__name__}: {e}"
                agent.transcript.note(f"HATA: {sess.error}")
            finally:
                ch.close()

        sess.thread = threading.Thread(target=_run, name=f"session-{sess.id}", daemon=True)
        with self._lock:
            self._sessions[sess.id] = sess
        sess.thread.start()
        msgs = ch.wait_turn()
        sess.transcript += [{"role": "agent", "text": m} for m in msgs]
        return sess, msgs

    def get(self, sid: str) -> Session:
        with self._lock:
            return self._sessions.get(sid)

    def turn(self, sess: Session, text: str, kind: str = None) -> list:
        sess.last_active = time.time()
        sess.transcript.append({"role": "user", "text": text})
        sess.channel.last_input_kind = kind
        sess.channel.submit(text)
        msgs = sess.channel.wait_turn()
        sess.transcript += [{"role": "agent", "text": m} for m in msgs]
        return msgs

    def stats(self) -> dict:
        with self._lock:
            by = {}
            for s in self._sessions.values():
                by[s.status] = by.get(s.status, 0) + 1
            return {"total": len(self._sessions), **by}
