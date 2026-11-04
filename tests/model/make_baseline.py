# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
v3.0 referans kaydı: bugünkü modelin tüm profil çıktılarını dondurur.
  python tests/model/make_baseline.py   →  tests/model/baseline_v3_0.json
Bu dosya yalnız bilinçli olarak yeniden üretilir; test_baseline.py v3.0 ayarlarının
bu sayıları birebir ürettiğini doğrular (düzeltmeler v3.0'ı sessizce bozmasın diye).
"""
import json
import subprocess
from datetime import date
from pathlib import Path

from profiles import ROOT, all_profiles, summarize

OUT = Path(__file__).with_name("baseline_v3_0.json")


def main():
    from model.hybrid_bayesian_network_v3 import load_engine
    eng = load_engine("v3")
    rows = {pid: summarize(eng.predict_risk(ev)) for pid, ev in all_profiles().items()}
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "?"
    OUT.write_text(json.dumps({"_meta": {"model": "v3.0", "created": str(date.today()), "git": commit,
                                         "n_profiles": len(rows)}, "profiles": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} profil → {OUT}")


if __name__ == "__main__":
    main()
