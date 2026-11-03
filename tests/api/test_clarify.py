# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""Ara soru algılama ve sözlük yanıtları (OpenAI çağrısı yok)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from conversation.clarify import is_side_question, answer_side_question, FALLBACK  # noqa: E402


@pytest.mark.parametrize("text", [
    "5 paket-yıl ne demek?", "KOAH nedir", "anlamadım", "neden soruyorsunuz?",
    "tekrar eder misiniz", "hırıltı derken ne kastediyorsunuz", "Bu ne demek?",
])
def test_detects_side_questions(text):
    assert is_side_question(text)


@pytest.mark.parametrize("text", [
    "evet", "hayır", "bilmiyorum", "62 yaşındayım erkeğim", "günde bir paket 30 yıl",
    "İzmir", "İstanbul?", "sürekli öksürüyorum, neden bilmiyorum", "60?",
])
def test_ignores_normal_answers(text):
    assert not is_side_question(text)


def test_term_from_previous_question_when_user_says_what():
    a = answer_side_question("o ne demek?", "Solunumunuzda hırıltı oluyor mu?")
    assert "ıslık" in a


def test_why_uses_question_topic():
    a = answer_side_question("bunu neden soruyorsunuz?", "Hangi ilde yaşıyorsunuz?")
    assert "hava kirliliği" in a


def test_repeat_returns_empty_and_unknown_falls_back():
    assert answer_side_question("tekrar eder misiniz?", "Göğüs ağrınız var mı?") == ""
    assert answer_side_question("hava nasıl olacak yarın ne dersin?", "Göğüs ağrınız var mı?") == FALLBACK


def test_hemoptysis_answer_points_to_doctor():
    assert "hekime" in answer_side_question("kan tükürme ne demek", "Hiç kan tükürdüğünüz oldu mu?")
