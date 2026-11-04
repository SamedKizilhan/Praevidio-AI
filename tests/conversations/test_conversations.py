# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Konuşma kaydı regresyon testleri: tests/conversations/*.txt kayıtları yeniden oynatılır (keyword modu,
OpenAI çağrısı yok); "# beklenen:" satırları tutmalı ve görüşme kayıttaki gibi akmalı.
Yeni vaka eklemek: PWA'dan "Konuşma kaydını indir" → bu klasöre kopyala → ">>" notu ve "# beklenen:" ekle.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
FILES = sorted(HERE.glob("*.txt"))


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_recorded_conversation(path):
    from conversation.replay import replay
    r = replay(path, nlp_mode="keyword")
    assert not r["fails"], "\n".join(r["fails"])
    assert not r["diff"], "akış kayıttan farklı:\n" + "\n".join(r["diff"])
    assert r["unused_answers"] == 0, "kayıttaki bazı cevaplar kullanılmadı (ajan daha az soru sordu)"
