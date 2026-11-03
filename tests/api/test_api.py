# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — API uçtan uca testleri (OpenAI çağrısı yapmaz: keyword modu, STT taklit edilir)

Çalıştırma:  python -m pytest tests/api -q      (veya: make api-test)
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from api import server  # noqa: E402

# Ajanın sorduğu sırayla kullanıcı cevapları (CLI testindeki 62 yaş aktif içici senaryosu)
ANSWERS = [
    "62 yaşındayım erkeğim",                       # yaş + cinsiyet
    "günde bir paket 30 yıldır içiyorum",          # sigara
    "evet",                                        # demografi onayı
    "sürekli öksürüyorum ve nefes darlığım var",   # açık uçlu şikâyet
    "hayır",                                       # göğüs ağrısı
    "bilmiyorum",                                  # hırıltı → atlanır
    "evet",                                        # halsizlik
    "hayır",                                       # kan tükürme
    "hayır",                                       # kilo kaybı
    "hayır",                                       # aile öyküsü
    "hayır",                                       # meslek
    "hayır",                                       # KOAH
    "İzmir",                                       # il
]


@pytest.fixture(scope="module")
def client():
    with TestClient(server.app) as c:
        yield c


def _run_conversation(client, answers, model="v3"):
    r = client.post("/sessions", json={"model": model, "nlp_mode": "keyword"})
    assert r.status_code == 200, r.text
    out = r.json()
    sid = out["session_id"]
    assert out["status"] == "awaiting_input"
    assert "yaşınızı" in out["messages"][0]["text"]
    turns = 0
    for a in answers:
        if out["status"] != "awaiting_input":
            break
        r = client.post(f"/sessions/{sid}/turn", json={"text": a})
        assert r.status_code == 200, r.text
        out = r.json()
        turns += 1
    return sid, out, turns


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok" and "v3" in j["models"]


def test_full_conversation_v3(client):
    sid, out, turns = _run_conversation(client, ANSWERS)
    assert out["status"] == "finished", out
    assert turns == len(ANSWERS)
    res = out["result"]
    assert res["model_version"] == "v3"
    assert res["alarm"]["level"] == "urgent"            # ≥40 yaş + öksürük + nefes darlığı
    assert res["risk_6y_factors"] > 1.5                  # 62y, 30 py aktif içici → tarama adayı
    assert res["screening"]["eligible"] is True          # USPSTF: 50–80 yaş, ≥20 py
    assert "Değerlendirmeniz tamamlandı" in out["messages"][-1]["text"]
    # durum ve kanıt
    s = client.get(f"/sessions/{sid}").json()
    ev = s["evidence"]
    assert ev["AGE"] == 2 and ev["SMOKING"] == 1 and ev["_pack_years"] == 30
    assert ev["COUGHING"] == 1 and ev["SHORTNESS_OF_BREATH"] == 1 and "WHEEZING" not in ev  # "bilmiyorum"
    assert ev["COPD"] == 0 and ev["_province"] == "İzmir"
    assert len([t for t in s["transcript"] if t["role"] == "user"]) == len(ANSWERS)
    # rapor
    if res["report_url"]:
        rr = client.get(res["report_url"])
        assert rr.status_code == 200 and len(rr.content) > 1000


def test_v2_model_has_no_copd_question(client):
    answers = [a for i, a in enumerate(ANSWERS) if i != 11]   # KOAH cevabını çıkar
    sid, out, _ = _run_conversation(client, answers, model="v2")
    assert out["status"] == "finished", out
    assert out["result"]["model_version"] == "v2"
    assert out["result"]["risk_6y_factors"] is None


def test_turn_after_finish_is_rejected(client):
    sid, out, _ = _run_conversation(client, ANSWERS)
    r = client.post(f"/sessions/{sid}/turn", json={"text": "merhaba"})
    assert r.status_code == 409


def test_unknown_session_404(client):
    assert client.post("/sessions/yok/turn", json={"text": "x"}).status_code == 404
    assert client.get("/tts/0000000000000000.mp3").status_code == 404


def test_audio_turn_uses_hint(client, monkeypatch):
    import stt.whisper_stt as stt
    seen = {}

    def fake_transcribe(path, language="tr", prompt=""):
        seen["prompt"] = prompt
        seen["exists"] = Path(path).exists()
        return {"text": "62 yaşındayım erkeğim"}

    monkeypatch.setattr(stt, "transcribe_audio", fake_transcribe)
    r = client.post("/sessions", json={"nlp_mode": "keyword", "tts": True})
    out = r.json()
    assert out["messages"][0]["audio_url"].startswith("/tts/")
    r = client.post(f"/sessions/{out['session_id']}/turn-audio",
                    files={"file": ("cevap.m4a", b"\x00" * 2048, "audio/mp4")})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["heard"] == "62 yaşındayım erkeğim"
    assert seen["exists"] and "yaşını" in seen["prompt"]       # ajanın STT ipucu iletildi
    assert "Sigara" in j["messages"][0]["text"]                 # sonraki soru


def test_token_required_when_configured(client, monkeypatch):
    monkeypatch.setattr(server, "API_TOKEN", "gizli")
    assert client.post("/sessions", json={}).status_code == 401
    r = client.post("/sessions", json={"nlp_mode": "keyword"}, headers={"Authorization": "Bearer gizli"})
    assert r.status_code == 200
