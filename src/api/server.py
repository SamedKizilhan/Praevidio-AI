# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — FastAPI backend
==============================
Mobil/web istemcinin konuşmalı risk değerlendirmesini yürüttüğü HTTP API.
Konuşma mantığı CLI ile aynıdır (conversation/voice_agent.py); bkz. api/sessions.py.

Uç noktalar
  GET  /health                       sürüm, model, STT/TTS ayarları, aktif oturumlar
  POST /sessions                     yeni oturum → ilk mesajlar (karşılama + ilk soru)
  POST /sessions/{id}/turn           metin cevabı → sonraki mesajlar (ya da sonuç)
  POST /sessions/{id}/turn-audio     ses dosyası (m4a/wav/webm…) → STT → /turn ile aynı
  GET  /sessions/{id}                durum, transkript, toplanan kanıt, sonuç
  GET  /sessions/{id}/report         PDF (WeasyPrint yoksa HTML) rapor
  GET  /tts/{key}.mp3                mesajın sesli hâli (önbellekli; tts=true ile istenir)

Çalıştırma
  make api            (veya)  uvicorn api.server:app --app-dir src --host 0.0.0.0 --port 8000
  Belgeler: http://localhost:8000/docs

Ortam değişkenleri
  PRAEVIDIO_API_TOKEN   ayarlıysa her istekte  Authorization: Bearer <token>  zorunlu
  NLP_MODE              varsayılan slot çıkarımı (keyword | llm)
  PRAEVIDIO_TTS_*, PRAEVIDIO_STT_MODEL  ses ayarları (config.py)
"""
import hashlib
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import NLP_MODE, STT_MODEL, TTS_MODEL, TTS_PROVIDER, TTS_VOICE, EDGE_TTS_VOICE  # noqa: E402
from api.sessions import SessionManager, Session  # noqa: E402

API_VERSION = "0.1.0"
API_TOKEN = os.getenv("PRAEVIDIO_API_TOKEN", "")
STATE: dict = {}


# ──────────────────────────────────────────────
# Uygulama yaşam döngüsü: modeller bir kez yüklenir
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from model.hybrid_bayesian_network_v3 import load_engine
    from conversation.voice_agent import Channel
    STATE["manager"] = SessionManager({"v3": load_engine("v3"), "v2": load_engine("v2")})
    STATE["tts_channel"] = Channel(mode="voice")       # yalnız sentez + önbellek için
    STATE["tts_texts"] = {}                           # key → metin
    yield
    STATE.clear()


app = FastAPI(title="Praevidio AI API", version=API_VERSION, lifespan=lifespan,
              description="Sesli/yazılı akciğer kanseri risk farkındalığı görüşmesi. Tanı aracı değildir.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def require_token(authorization: Optional[str] = Header(default=None)):
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Geçersiz ya da eksik API anahtarı.")


# ──────────────────────────────────────────────
# Şemalar
# ──────────────────────────────────────────────
class CreateSession(BaseModel):
    model: Literal["v3", "v2"] = "v3"
    nlp_mode: Optional[Literal["keyword", "llm"]] = None
    tts: bool = Field(False, description="Mesajlar için audio_url üretilsin mi?")


class TurnIn(BaseModel):
    text: str = Field(..., max_length=2000)


class Message(BaseModel):
    text: str
    audio_url: Optional[str] = None


class Alarm(BaseModel):
    level: str
    reasons_tr: List[str] = []
    message_tr: str = ""


class Screening(BaseModel):
    eligible: Optional[bool] = None
    label_tr: str = ""
    message_tr: str = ""


class Result(BaseModel):
    model_version: str
    risk_score: float = Field(..., description="Tam skor (belirtiler dahil), %")
    risk_level: str
    risk_level_tr: str
    risk_6y_factors: Optional[float] = Field(None, description="Yalnız risk faktörlerinden 6 yıllık risk, % (v3)")
    risk_level_factors_tr: Optional[str] = None
    plcom2012_6y: Optional[float] = None
    alarm: Optional[Alarm] = None
    screening: Optional[Screening] = None
    recommendation_tr: str
    report_url: Optional[str] = None


class TurnOut(BaseModel):
    session_id: str
    status: Literal["awaiting_input", "processing", "finished", "error", "expired"]
    messages: List[Message]
    hint: str = Field("", description="Beklenen cevap için ipucu (STT bağlamı)")
    heard: Optional[str] = Field(None, description="Ses turunda STT'nin anladığı metin")
    result: Optional[Result] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Yardımcılar
# ──────────────────────────────────────────────
def _tts_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _messages(sess: Session, msgs: list) -> List[Message]:
    out = []
    for m in msgs:
        url = None
        if getattr(sess, "tts", False):
            k = _tts_key(m)
            STATE["tts_texts"][k] = m
            url = f"/tts/{k}.mp3"
        out.append(Message(text=m, audio_url=url))
    return out


def _result(sess: Session) -> Optional[Result]:
    r = sess.agent.result
    if not r:
        return None
    alarm = r.get("alarm")
    scr = r.get("screening") or {}
    bm = r.get("benchmark_plcom2012") or {}
    return Result(
        model_version=r.get("model_version", "v2"),
        risk_score=float(r["risk_score"]), risk_level=r["risk_level"], risk_level_tr=r["risk_level_tr"],
        risk_6y_factors=(float(r["risk_6y_factors"]) if "risk_6y_factors" in r else None),
        risk_level_factors_tr=r.get("risk_level_factors_tr"),
        plcom2012_6y=(float(bm["risk_6y"]) if bm.get("applicable") else None),
        alarm=(Alarm(level=alarm["level"], reasons_tr=alarm.get("reasons_tr", []),
                     message_tr=alarm.get("message_tr", "")) if alarm else None),
        screening=Screening(eligible=scr.get("eligible"), label_tr=scr.get("label_tr", ""),
                            message_tr=scr.get("message_tr", "")),
        recommendation_tr=r.get("recommendation_tr", ""),
        report_url=(f"/sessions/{sess.id}/report" if sess.agent.report_path else None),
    )


def _turn_out(sess: Session, msgs: list, heard: Optional[str] = None) -> TurnOut:
    return TurnOut(session_id=sess.id, status=sess.status, messages=_messages(sess, msgs),
                   hint=sess.channel.hint if sess.status == "awaiting_input" else "",
                   heard=heard, result=_result(sess) if sess.status == "finished" else None,
                   error=sess.error or None)


def _session(sid: str) -> Session:
    sess = STATE["manager"].get(sid)
    if sess is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı ya da süresi doldu.")
    return sess


def _ensure_open(sess: Session):
    if sess.status != "awaiting_input":
        raise HTTPException(status_code=409, detail=f"Oturum cevap beklemiyor (durum: {sess.status}).")


# ──────────────────────────────────────────────
# Uç noktalar
# ──────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "api_version": API_VERSION, "models": ["v3", "v2"],
            "default_nlp_mode": NLP_MODE, "stt_model": STT_MODEL,
            "tts": {"provider": TTS_PROVIDER, "model": TTS_MODEL,
                    "voice": EDGE_TTS_VOICE if TTS_PROVIDER == "edge" else TTS_VOICE},
            "auth_required": bool(API_TOKEN), "sessions": STATE["manager"].stats()}


@app.post("/sessions", response_model=TurnOut, dependencies=[Depends(require_token)])
def create_session(body: CreateSession = CreateSession()):
    try:
        sess, msgs = STATE["manager"].create(model_version=body.model, nlp_mode=body.nlp_mode or NLP_MODE)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    sess.tts = body.tts
    return _turn_out(sess, msgs)


@app.post("/sessions/{sid}/turn", response_model=TurnOut, dependencies=[Depends(require_token)])
def turn(sid: str, body: TurnIn):
    sess = _session(sid)
    _ensure_open(sess)
    msgs = STATE["manager"].turn(sess, body.text.strip())
    return _turn_out(sess, msgs)


@app.post("/sessions/{sid}/turn-audio", response_model=TurnOut, dependencies=[Depends(require_token)])
def turn_audio(sid: str, file: UploadFile = File(...)):
    from stt.whisper_stt import transcribe_audio
    sess = _session(sid)
    _ensure_open(sess)
    suffix = Path(file.filename or "audio.m4a").suffix.lower() or ".m4a"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        heard = transcribe_audio(path, prompt=sess.channel.hint)["text"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ses yazıya çevrilemedi: {e}")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    msgs = STATE["manager"].turn(sess, heard or "")
    return _turn_out(sess, msgs, heard=heard)


@app.get("/sessions/{sid}", dependencies=[Depends(require_token)])
def get_session(sid: str):
    sess = _session(sid)
    ev = {k: v for k, v in sess.agent.evidence.items()}
    res = _result(sess) if sess.status == "finished" else None
    return {"session_id": sess.id, "status": sess.status, "model": sess.model_version,
            "nlp_mode": sess.nlp_mode, "transcript": sess.transcript, "evidence": ev,
            "result": res.model_dump() if res else None, "error": sess.error or None}


@app.get("/sessions/{sid}/report", dependencies=[Depends(require_token)])
def get_report(sid: str):
    sess = _session(sid)
    path = sess.agent.report_path
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Rapor henüz hazır değil.")
    media = "application/pdf" if str(path).endswith(".pdf") else "text/html"
    return FileResponse(path, media_type=media, filename=Path(path).name)


@app.get("/tts/{key}.mp3")
def tts(key: str):
    text = STATE["tts_texts"].get(key)
    if text is None:
        raise HTTPException(status_code=404, detail="Bilinmeyen ses anahtarı.")
    ch = STATE["tts_channel"]
    out = ch._cache_path(text)
    if not out.exists() and not ch._synthesize(text, out):
        raise HTTPException(status_code=502, detail="Ses sentezlenemedi (TTS sağlayıcısı/anahtar).")
    return FileResponse(out, media_type="audio/mpeg")
