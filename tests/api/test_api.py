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
def client(tmp_path_factory):
    import conversation.transcript as tr
    saved, server.API_TOKEN = server.API_TOKEN, ""   # .env'deki PRAEVIDIO_API_TOKEN testleri etkilemesin
    saved_dir, tr.TRANSCRIPT_DIR = tr.TRANSCRIPT_DIR, tmp_path_factory.mktemp("conversations")
    with TestClient(server.app) as c:
        yield c
    server.API_TOKEN, tr.TRANSCRIPT_DIR = saved, saved_dir


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
    assert res["risk_level_factors"] in ("moderate", "high")
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


def test_pwa_is_served(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (301, 302, 307) and r.headers["location"].endswith("/app/")
    r = client.get("/app/")
    assert r.status_code == 200 and "Praevidio" in r.text and "app.js" in r.text
    for f in ("app.js", "styles.css", "sw.js", "icons/icon-192.png"):
        assert client.get(f"/app/{f}").status_code == 200, f
    m = client.get("/app/manifest.webmanifest")
    assert m.status_code == 200 and m.json()["start_url"] == "/app/"


def test_token_required_when_configured(client, monkeypatch):
    monkeypatch.setattr(server, "API_TOKEN", "gizli")
    assert client.post("/sessions", json={}).status_code == 401
    r = client.post("/sessions", json={"nlp_mode": "keyword"}, headers={"Authorization": "Bearer gizli"})
    assert r.status_code == 200


def test_side_question_is_answered_then_question_repeated(client):
    """Kullanıcının bildirdiği durum: onay sorusunda '5 paket-yıl ne demek?' → açıkla, sonra tekrar sor."""
    r = client.post("/sessions", json={"nlp_mode": "keyword"})
    sid = r.json()["session_id"]
    client.post(f"/sessions/{sid}/turn", json={"text": "45 yaşındayım erkeğim"})
    out = client.post(f"/sessions/{sid}/turn", json={"text": "günde 10 tane, yaklaşık 10 yıldır içiyorum"}).json()
    confirm = out["messages"][-1]["text"]
    assert "paket-yıl" in confirm and confirm.endswith("Doğru mu?")
    out = client.post(f"/sessions/{sid}/turn", json={"text": "5 paket-yıl ne demek ki?"}).json()
    texts = [m["text"] for m in out["messages"]]
    assert out["status"] == "awaiting_input"
    assert "20 sigara" in texts[0] and "0,5 paket" in texts[0] and "yaklaşık 5 paket-yıl hesapladım" in texts[0]   # kişiselleştirilmiş
    assert texts[-1] == confirm                                                         # aynı soru tekrar
    out = client.post(f"/sessions/{sid}/turn", json={"text": "neden soruyorsunuz?"}).json()
    assert "teyit" in out["messages"][0]["text"] and out["messages"][-1]["text"] == confirm
    out = client.post(f"/sessions/{sid}/turn", json={"text": "evet"}).json()           # akış devam eder
    complaint = out["messages"][-1]["text"]
    assert "şikâyet" in complaint and not complaint.endswith("?")
    out = client.post(f"/sessions/{sid}/turn", json={"text": "KOAH ne demek?"}).json()
    assert "solunum fonksiyon" in out["messages"][0]["text"]
    assert out["messages"][-1]["text"] == complaint          # soru işaretsiz istem de doğru tekrarlanır
    out = client.post(f"/sessions/{sid}/turn", json={"text": "şikâyetim yok"}).json()
    assert "tek tek" in out["messages"][0]["text"]
    out = client.post(f"/sessions/{sid}/turn", json={"text": "o ne demek?"}).json()      # "geçmeyen öksürük"
    assert "üç hafta" in out["messages"][0]["text"]
    s = client.get(f"/sessions/{sid}").json()
    assert s["evidence"]["_pack_years"] == 5


def test_transcript_saved_downloadable_and_replayable(client, monkeypatch):
    """Görüşme agent:/user: satırlarıyla diske yazılır, indirilebilir, yeniden oynatılınca aynı akışı verir."""
    import stt.whisper_stt as stt
    from conversation.transcript import parse
    from conversation.replay import replay
    monkeypatch.setattr(stt, "transcribe_audio", lambda path, language="tr", prompt="": {"text": "62 yaşındayım erkeğim"})
    r = client.post("/sessions", json={"nlp_mode": "keyword", "client": "pwa-voice"}).json()
    sid = r["session_id"]
    client.post(f"/sessions/{sid}/turn-audio", files={"file": ("c.m4a", b"\x00" * 2048, "audio/mp4")})
    for a in ANSWERS[1:]:
        out = client.post(f"/sessions/{sid}/turn", json={"text": a}).json()
    assert out["status"] == "finished"
    t = client.get(f"/sessions/{sid}/transcript.txt")
    assert t.status_code == 200 and "attachment" in t.headers["content-disposition"]
    txt = t.text
    assert txt.startswith("# Praevidio konuşma kaydı") and "kanal: pwa-voice" in txt
    assert "# ses → STT\nuser: 62 yaşındayım erkeğim" in txt          # sesli cevap işaretli
    assert "# --- sonuç ---" in txt and '"_pack_years": 30' in txt
    rec = parse(txt)
    assert [x["text"] for x in rec["turns"] if x["role"] == "user"] == ANSWERS
    assert sum(1 for x in rec["turns"] if x["role"] == "agent") >= len(ANSWERS)
    # diskteki dosya = indirilen metin
    import conversation.transcript as tr
    assert (tr.TRANSCRIPT_DIR / f"{sid}.txt").read_text(encoding="utf-8") == txt
    # yeniden oynatma: aynı cevaplar → birebir aynı konuşma
    rp = replay(txt + "# beklenen: _pack_years=30\n# beklenen: alarm=urgent\n# beklenen: bitti=true\n")
    assert rp["finished"] and not rp["diff"] and not rp["fails"], (rp["diff"], rp["fails"])
