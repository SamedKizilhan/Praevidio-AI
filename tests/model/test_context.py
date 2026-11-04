# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
6 yıllık katmanı anlatan bağlam alanları (Kas 2026): görüntüleme etiketi, göreli risk, projeksiyon.
Sayılar ve bantlar değişmez (test_baseline.py); burada yalnız yeni alanların tutarlılığı sınanır.
"""
import pytest

from profiles import all_profiles

WOMAN_35 = {"AGE": 0, "_age_exact": 35, "GENDER": 0, "SMOKING": 1, "_cigs_per_day": 20, "_years_smoked": 18,
            "_pack_years": 18, "FAMILY_HISTORY": 1, "ASBESTOS": 1, "AIR_POLLUTION": 2, "COPD": 0}


@pytest.fixture(scope="module", params=["v3.0", "v3.1"])
def eng(request):
    from model.hybrid_bayesian_network_v3 import load_engine
    return load_engine(request.param)


def test_factor_6y_matches_predict_risk(eng):
    """Göreli risk/projeksiyon için kullanılan yardımcı, ana hesapla aynı 6 yıllık değeri verir."""
    for pid, ev in all_profiles().items():
        r = eng.predict_risk(ev)
        assert eng._factor_6y(ev) == pytest.approx(r["risk_6y_probability"], rel=1e-9), pid


def test_display_label_only_changes_wording(eng):
    for ev in all_profiles().values():
        r = eng.predict_risk(ev)
        if r["risk_level_factors"] == "low":
            assert r["risk_level_factors_display_tr"] == "Tarama eşiğinin altında"
        else:
            assert r["risk_level_factors_display_tr"] == r["risk_level_factors_tr"]


def test_woman_35_all_factors_context():
    from model.hybrid_bayesian_network_v3 import load_engine
    r = load_engine("v3.1").predict_risk(WOMAN_35)
    assert r["risk_level_factors"] == "low"                                # bant değişmedi
    assert 20 <= r["relative_risk_peers"] <= 60, r["relative_risk_peers"]  # yaşıtına göre onlarca kat
    p = r["projection"]
    assert p["age"] == 50 and p["continue_6y"] >= 1.5 and p["enters_screening_range"]
    assert p["quit_6y"] < p["continue_6y"] / 2
    assert "tarama aralığına girersiniz" in p["message_tr"]


def test_reference_person_is_one_and_no_projection_for_non_smokers():
    from model.hybrid_bayesian_network_v3 import load_engine
    e = load_engine("v3.1")
    ref = {"AGE": 2, "_age_exact": 60, "GENDER": 1, "SMOKING": 0, "_pack_years": 0,
           "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0, "COPD": 0}
    r = e.predict_risk(ref)
    assert r["relative_risk_peers"] == pytest.approx(1.0) and "benzer" in r["relative_message_tr"]
    assert r["projection"] is None
    former = {**ref, "SMOKING": 0, "_pack_years": 20, "_cigs_per_day": 20, "_years_smoked": 20, "_years_quit": 10}
    assert e.predict_risk(former)["projection"] is None                    # yalnız aktif içici


@pytest.mark.parametrize("age", [30, 40, 49, 50, 65, 79])
def test_projection_continue_never_below_quit(age):
    from model.hybrid_bayesian_network_v3 import load_engine
    e = load_engine("v3.1")
    ev = {**WOMAN_35, "_age_exact": age, "AGE": e._age_group(age), "_years_smoked": max(1, age - 17),
          "_pack_years": max(1, age - 17)}
    p = e.predict_risk(ev)["projection"]
    assert p["age"] == (50 if age < 50 else min(age + 5, 80))
    assert p["continue_6y"] >= p["quit_6y"]
