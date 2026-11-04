# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Belirti katmanı (Kas 2026): P(şu an belirti veren akciğer kanseri | kanıt), eşik NICE NG12 PPV %3.
Tam skor (karma ufuk) artık bantlanmaz; 6 yıllık sayılar/bantlar değişmez (test_baseline.py).
"""
import pytest

S7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING", "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
M62 = {"AGE": 2, "_age_exact": 62, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 20, "_years_smoked": 40,
       "_pack_years": 40, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 1}
W35 = {"AGE": 0, "_age_exact": 35, "GENDER": 0, "SMOKING": 1, "_cigs_per_day": 20, "_years_smoked": 18,
       "_pack_years": 18, "FAMILY_HISTORY": 1, "ASBESTOS": 1, "AIR_POLLUTION": 2, "COPD": 0}


@pytest.fixture(scope="module")
def eng():
    from model.hybrid_bayesian_network_v3 import load_engine
    return load_engine("v3")


def _sa(eng, ev):
    r = eng.predict_risk(ev)
    return r, r["symptom_assessment"]


def test_symptom_layer_is_part_of_full_score(eng):
    for yes in (["COUGHING"], ["HEMOPTYSIS"], S7):
        r, sa = _sa(eng, {**M62, **{s: int(s in yes) for s in S7}})
        assert 0 < sa["probability"] <= r["risk_probability"] + 1e-12


def test_symptom_layer_share_independent_of_base():
    """P(SEMPTOMATİK | kanser, kanıt) taban riskten bağımsız: NLST ve PLCOm2012 tabanında aynı pay."""
    from model.hybrid_bayesian_network_v3 import load_engine
    a, b = load_engine("v3.1", base_risk="nlst"), load_engine("v3.1", base_risk="plco")
    ev = {**M62, **{s: 0 for s in S7}, "COUGHING": 1, "WEIGHT_LOSS": 1}
    ra, rb = a.predict_risk(ev), b.predict_risk(ev)
    share = lambda r: r["symptom_assessment"]["probability"] / r["risk_probability"]
    assert share(ra) == pytest.approx(share(rb), rel=1e-9)


def test_single_symptoms_consistent_with_hamilton(eng):
    """Hamilton 2005: hemoptizi dışındaki tek belirtiler PPV < %2 (sigara içende ~2 kat → < %4);
    hemoptizi %2,4 (70+ yaş %7,1; sigara içende ~2 kat). Uygulama 7 belirtiyi de sorar → diğerleri 'hayır'."""
    for s in S7:
        _, sa = _sa(eng, {**M62, **{x: 0 for x in S7}, s: 1})
        if s == "HEMOPTYSIS":
            assert 2.4 <= sa["percent"] <= 15, sa["percent"]
        else:
            assert sa["percent"] < 4, (s, sa["percent"])


def test_no_symptoms_means_no_symptom_message(eng):
    r, sa = _sa(eng, {**M62, **{s: 0 for s in S7}})
    assert sa["level"] == "none" and sa["message_tr"] is None and r["urgent_assessment"] is False


def test_young_woman_all_symptoms_gets_prompt_assessment_without_nice(eng):
    r, sa = _sa(eng, {**W35, **{s: 1 for s in S7}})
    assert r["alarm"]["level"] == "none"                     # NICE kuralı ≥40 yaş
    assert sa["level"] == "elevated" and r["urgent_assessment"]
    assert "kısa sürede" in r["recommendation_tr"]
    assert any("model tahmini" in x for x in r["urgent_reasons_tr"])


def test_hemoptysis_any_age_is_prompt_even_if_cancer_unlikely(eng):
    ev = {"AGE": 0, "_age_exact": 30, "GENDER": 0, "SMOKING": 0, "_pack_years": 0, **{s: 0 for s in S7},
          "HEMOPTYSIS": 1}
    r, sa = _sa(eng, ev)
    assert sa["level"] == "low"                              # kanser olasılığı düşük (dürüst sayı)
    assert r["urgent_assessment"] and any("Kan tükürme her yaşta" in x for x in r["urgent_reasons_tr"])


def test_young_light_smoker_symptoms_low_layer_advises_gp(eng):
    ev = {**W35, "_age_exact": 30, "_cigs_per_day": 10, "_years_smoked": 10, "_pack_years": 5,
          "FAMILY_HISTORY": 0, "AIR_POLLUTION": 1, **{s: 0 for s in S7},
          "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "CHEST_PAIN": 1, "FATIGUE": 1, "WEIGHT_LOSS": 1}
    r, sa = _sa(eng, ev)
    assert sa["level"] == "low" and not r["urgent_assessment"]
    assert "birkaç haftadır" in sa["message_tr"] and "birkaç haftadır" not in r["recommendation_tr"]


def test_threshold_comes_from_config(eng):
    """Eşik tek yerden (PRAEVIDIO_SYMPTOM_REFERRAL_PPV, varsayılan NICE %3) okunur ve çıktıda raporlanır."""
    from model.hybrid_bayesian_network_v3 import SYMPTOM_REFERRAL_PPV
    _, sa = _sa(eng, {**M62, "COUGHING": 1})
    assert sa["threshold"] == SYMPTOM_REFERRAL_PPV == 0.03
