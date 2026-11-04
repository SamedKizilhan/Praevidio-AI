# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Model regresyon/klinik makullük testlerinin ortak profil kümesi.

  * scenarios.json (demo + kontrollü A/B çiftleri)
  * compare_v2_v3.py PROBES (Bulgu 1–4 sınama vakaları)
  * uzman doğrulama vakaları (E1–E10)

Hepsi tek sözlükte: {profil_id: evidence}. Kimlikler kaynağa göre önekli (S:, P:, E:).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "test_scenarios"))

KEYS = ("risk_score", "risk_6y_factors", "nlst_6y_factors", "risk_level", "risk_level_factors")


def all_profiles() -> dict:
    out = {}
    for s in json.loads((ROOT / "tests/test_scenarios/scenarios.json").read_text(encoding="utf-8"))["scenarios"]:
        out[f"S:{s['id']}"] = s["evidence"]
    from compare_v2_v3 import PROBES
    for pid, _, ev in PROBES:
        out[f"P:{pid}"] = ev
    for s in json.loads((ROOT / "tests/expert_validation/scenarios.json").read_text(encoding="utf-8"))["scenarios"]:
        out[f"E:{s['id']}"] = s["evidence"]
    return out


def summarize(res: dict) -> dict:
    d = {k: res.get(k) for k in KEYS}
    d["alarm"] = res.get("alarm", {}).get("level")
    bm = res.get("benchmark_plcom2012") or {}
    d["plcom2012_6y"] = bm.get("risk_6y") if bm.get("applicable") else None
    return d
