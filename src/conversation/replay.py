# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Konuşma kaydını yeniden oynatma: kayıttaki user: satırları sırayla ajana verilir, ajanın yeni cevapları
kaydedilenlerle karşılaştırılır, "# beklenen:" satırları kontrol edilir.

Beklenti anahtarları (değerler JSON gibi okunur; "yok" = alan hiç doldurulmamış):
  * kanıt alanları:     AGE, GENDER, SMOKING, _pack_years, COUGHING, COPD, _province …
  * sonuç alanları:     risk_level_factors, risk_level, alarm (NICE), belirti (none|low|elevated),
                        acil (true/false: kısa sürede hekim), bitti (true/false)
  * ajan metni:         ajan_der="…"  (herhangi bir ajan mesajında geçer)
                        ajan_demez="…" (hiçbir ajan mesajında geçmez)
"""
import contextlib
import difflib
import io
import json
from pathlib import Path

from conversation.transcript import parse, read
from conversation.voice_agent import Channel, ConversationAgent

_ENGINES = {}


class ReplayEnd(Exception):
    pass


class ScriptedChannel(Channel):
    def __init__(self, answers):
        super().__init__(mode="text")
        self._answers = list(answers)
        self.used = 0

    def say(self, text: str):
        pass

    def listen(self, stt_hint: str = "") -> str:
        if self.used >= len(self._answers):
            raise ReplayEnd()
        self.used += 1
        return self._answers[self.used - 1]


def _engine(version: str):
    if version not in _ENGINES:
        from model.hybrid_bayesian_network_v3 import load_engine
        with contextlib.redirect_stdout(io.StringIO()):
            _ENGINES[version] = load_engine(version)
    return _ENGINES[version]


def _value(v: str):
    v = v.strip()
    if v.lower() in ("yok", "none", "null"):
        return None
    try:
        return json.loads(v)
    except ValueError:
        return v.strip('"')


def check(expect, agent_msgs, evidence, result, finished) -> list:
    fails = []
    for key, raw in expect:
        want = _value(raw)
        if key == "ajan_der":
            if not any(str(want) in m for m in agent_msgs):
                fails.append(f'ajan_der="{want}": hiçbir ajan mesajında yok')
            continue
        if key == "ajan_demez":
            hit = [m for m in agent_msgs if str(want) in m]
            if hit:
                fails.append(f'ajan_demez="{want}": şu mesajda geçti → {hit[0][:90]}')
            continue
        if key == "bitti":
            got = finished
        elif key in ("risk_level_factors", "risk_level"):
            got = (result or {}).get(key)
        elif key == "alarm":
            got = ((result or {}).get("alarm") or {}).get("level")
        elif key == "belirti":
            got = ((result or {}).get("symptom_assessment") or {}).get("level")
        elif key == "acil":
            got = (result or {}).get("urgent_assessment")
        else:
            got = evidence.get(key)
        same = (got == want) or (isinstance(got, (int, float)) and isinstance(want, (int, float))
                                 and abs(got - want) < 1e-6)
        if not same:
            fails.append(f"{key}: beklenen {want!r}, bulunan {got!r}")
    return fails


def replay(source, model: str = None, nlp_mode: str = None) -> dict:
    """source: dosya yolu ya da kayıt metni. Dönüş: turns, diff, fails, evidence, result, finished."""
    rec = read(source) if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source) else parse(source)
    meta = rec["meta"]
    model = model or (meta.get("model", "v3").split()[0])
    nlp_mode = nlp_mode or meta.get("nlp", "keyword")
    answers = [t["text"] for t in rec["turns"] if t["role"] == "user"]
    ch = ScriptedChannel(answers)
    agent = ConversationAgent(ch, nlp_mode=nlp_mode, model_version=model, engine=_engine(model),
                              save_transcript=False, transcript_meta={"kanal": "replay"})
    finished = False
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            agent.run()
            finished = True
        except ReplayEnd:
            pass
    new_turns = [l for l in agent.transcript.lines if l.startswith(("agent:", "user:"))]
    old_turns = [f"{t['role']}: {t['text']}" for t in rec["turns"]]
    diff = list(difflib.unified_diff(old_turns, new_turns, "kayıt", "şimdi", lineterm="", n=1))
    agent_msgs = [l[len("agent: "):] for l in new_turns if l.startswith("agent:")]
    fails = check(rec["expect"], agent_msgs, agent.evidence, agent.result, finished)
    if not finished and ch.used >= len(answers):
        unused = 0
    else:
        unused = len(answers) - ch.used
    return {"meta": meta, "model": model, "nlp_mode": nlp_mode, "record": rec, "new_turns": new_turns,
            "diff": diff, "fails": fails, "evidence": agent.evidence, "result": agent.result,
            "finished": finished, "unused_answers": unused}
