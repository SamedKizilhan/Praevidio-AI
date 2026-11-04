# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Regresyon: v3.0 ayarları (NLST tabanı, ortak neden düğümü kapalı) dondurulmuş referansı
(baseline_v3_0.json, 43 profil) birebir üretmeli. Düzeltmeler v3.0'ı sessizce değiştiremez.
"""
import json
from pathlib import Path

import pytest

from profiles import all_profiles, summarize

BASE = json.loads(Path(__file__).with_name("baseline_v3_0.json").read_text(encoding="utf-8"))["profiles"]
PROFILES = all_profiles()


@pytest.fixture(scope="module")
def engine_v30():
    from model.hybrid_bayesian_network_v3 import load_engine
    return load_engine("v3.0")


def test_profile_set_unchanged():
    assert set(PROFILES) == set(BASE), "profil kümesi değişti — make_baseline.py bilinçli olarak yeniden çalıştırılmalı"


@pytest.mark.parametrize("pid", sorted(BASE))
def test_v30_reproduces_baseline(engine_v30, pid):
    got = summarize(engine_v30.predict_risk(PROFILES[pid]))
    exp = BASE[pid]
    for k, v in exp.items():
        if isinstance(v, float):
            assert got[k] == pytest.approx(v, abs=0.011), (pid, k)
        else:
            assert got[k] == v, (pid, k)
