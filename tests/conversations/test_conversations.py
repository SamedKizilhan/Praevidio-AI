# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Regression tests on recorded conversations: every tests/conversations/*.txt is replayed (keyword mode, no
OpenAI call); the "# beklenen:" (expected) lines must hold and the interview must flow as recorded.
To add a case: "Konuşma kaydını indir" (download transcript) in the PWA, copy the file into this folder, add
">>" notes and "# beklenen:" lines. Format: tests/conversations/README.md.
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
    assert not r["diff"], "the flow differs from the recording:\n" + "\n".join(r["diff"])
    assert r["unused_answers"] == 0, "some recorded answers were not used (the agent asked fewer questions)"
