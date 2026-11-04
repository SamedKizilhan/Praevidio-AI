# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Klinik makullük testleri — varsayılan modelin (load_engine("v3")) uyması gereken sınırlar.

Belirti çarpanı M = odds(tam skor) / odds(6 yıllık faktör katmanı): belirtilerin riski kaç kat
artırdığı. Üst sınırlar Hamilton 2005'ten (Thorax 60:1059; ≥40 yaş birinci basamak, 2 yıllık pencere,
taban %0,18) olasılık oranına çevrilmiştir. 6 yıllık ufukta vakaların yalnız bir kısmı bugün
semptomatik olduğundan bu oranlar M için ÜST sınırdır (seyrelme yalnız aşağı çeker):
  * tek semptom (hemoptizi hariç) PPV < %2      → LR < 11,3
  * hemoptizi PPV %2,4                           → LR ≈ 13,6
  * öksürük içeren hiçbir ikili > %2            → LR < 11,3
  * en yüksek bildirilen kombinasyon "> %10"    → hemoptizisiz her kombinasyon için LR ≤ 61
  * en yüksek değer %17 (tekrarlayan hemoptizi)  → her kombinasyon için LR ≤ 114
6 yıllık katman: sigara içmiş ve girdileri tam kişilerde PLCOm2012'nin 2 katı aralığında kalmalı.
"""
import itertools
import math

import pytest

S7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING", "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
BASE_PPV = 0.0018


def lr_from_ppv(ppv):
    return (ppv / (1 - ppv)) / (BASE_PPV / (1 - BASE_PPV))


CAP_SINGLE = lr_from_ppv(0.02)       # 11,3
CAP_HEMOPTYSIS = lr_from_ppv(0.024)  # 13,6
CAP_COMBO = lr_from_ppv(0.10)        # 61,6
CAP_ANY = lr_from_ppv(0.17)          # 113,6

BASES = {
    "70+ aktif içici": {"AGE": 4, "_age_exact": 72, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 20,
                         "_years_smoked": 50, "_pack_years": 50, "FAMILY_HISTORY": 0, "ASBESTOS": 0,
                         "AIR_POLLUTION": 1},
    "45 hafif içici": {"AGE": 0, "_age_exact": 45, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 10,
                        "_years_smoked": 10, "_pack_years": 5, "FAMILY_HISTORY": 0, "ASBESTOS": 1,
                        "AIR_POLLUTION": 1},
    "60 hiç içmemiş": {"AGE": 2, "_age_exact": 60, "GENDER": 0, "SMOKING": 0, "_pack_years": 0,
                        "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 1},
}
COPD_STATES = {"KOAH yok": 0, "KOAH var": 1, "KOAH bilinmiyor": None}


@pytest.fixture(scope="module")
def eng():
    from model.hybrid_bayesian_network_v3 import load_engine
    return load_engine("v3")


def _odds(p_pct):
    p = min(max(p_pct / 100.0, 1e-6), 1 - 1e-6)
    return p / (1 - p)


def _ev(base, copd, yes):
    ev = dict(BASES[base])
    if COPD_STATES[copd] is not None:
        ev["COPD"] = COPD_STATES[copd]
    ev.update({s: (1 if s in yes else 0) for s in S7})   # uygulama 7 belirtiyi de sorar
    return ev


def _multiplier(eng, ev):
    r = eng.predict_risk(ev)
    p, p6 = r["risk_probability"], r["risk_6y_probability"]       # yuvarlanmamış
    return (p / (1 - p)) / (p6 / (1 - p6)), r


COMBOS = [c for k in range(1, 8) for c in itertools.combinations(S7, k)]


@pytest.mark.parametrize("base", list(BASES))
@pytest.mark.parametrize("copd", list(COPD_STATES))
def test_symptom_multiplier_within_hamilton_envelope(eng, base, copd):
    bad = []
    for yes in COMBOS:
        m, _ = _multiplier(eng, _ev(base, copd, set(yes)))
        if len(yes) == 1:
            cap = CAP_HEMOPTYSIS if yes[0] == "HEMOPTYSIS" else CAP_SINGLE
        elif len(yes) == 2 and "COUGHING" in yes and "HEMOPTYSIS" not in yes:
            cap = CAP_SINGLE
        elif "HEMOPTYSIS" not in yes:
            cap = CAP_COMBO
        else:
            cap = CAP_ANY
        if m > cap * 1.0001:
            bad.append(f"{'+'.join(yes)}: ×{m:.0f} > ×{cap:.0f}")
    assert not bad, f"{base}, {copd}: {len(bad)} kombinasyon sınır dışı, ör. " + "; ".join(bad[:4])


@pytest.mark.parametrize("base", list(BASES))
def test_symptoms_still_informative(eng, base):
    """Düzeltme kanıtı yok etmesin (Hamilton'daki gibi diğer belirtiler koşullanmadan):
    her belirti riski artırır, hemoptizi tek başına ≥×3, kilo kaybı/göğüs ağrısı ≥×2, 7'si ≥×10."""
    ev = dict(BASES[base])
    m = {s: _multiplier(eng, {**ev, s: 1})[0] for s in S7}
    assert all(v > 1 for v in m.values()), m
    assert m["HEMOPTYSIS"] >= 3 and m["WEIGHT_LOSS"] >= 2 and m["CHEST_PAIN"] >= 2, m
    assert m["HEMOPTYSIS"] == max(m.values()), m                 # Hamilton: en yüksek PPV hemoptizi
    assert _multiplier(eng, {**ev, **{s: 1 for s in S7}})[0] >= 10


@pytest.mark.parametrize("base", list(BASES))
@pytest.mark.parametrize("copd", list(COPD_STATES))
def test_adding_a_symptom_never_lowers_risk(eng, base, copd):
    for yes in [c for k in range(0, 7) for c in itertools.combinations(S7, k)][::3]:
        p0 = eng.predict_risk(_ev(base, copd, set(yes)))["risk_score"]   # yuvarlanmış: 0,01 tolerans
        for s in S7:
            if s not in yes:
                p1 = eng.predict_risk(_ev(base, copd, set(yes) | {s}))["risk_score"]
                if s == "WHEEZING" and COPD_STATES[copd] is None:
                    # Bilinen ve belgelenmiş istisna (v3.0'dan beri): KOAH bilinmiyorken hırıltı KOAH
                    # olasılığını artırır, KOAH da öksürük/nefes darlığını açıklar → hafif düşüş.
                    assert p1 >= 0.8 * p0 - 1e-6, (base, copd, yes, s, p0, p1)
                else:
                    assert p1 >= p0 - 1e-6, (base, copd, yes, s, p0, p1)


def test_user_reported_case_is_plausible(eng):
    """Kullanıcı denemesi (4 Kas 2026): genç hafif içici, asbest, 5 belirti, KOAH yok → %85 çıkmıştı."""
    for age in (30, 45):
        ev = {"AGE": 0, "_age_exact": age, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 10,
              "_years_smoked": 10, "_pack_years": 5, "FAMILY_HISTORY": 0, "ASBESTOS": 1,
              "AIR_POLLUTION": 1, "COPD": 0, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1,
              "CHEST_PAIN": 1, "FATIGUE": 1, "WEIGHT_LOSS": 1, "WHEEZING": 0, "HEMOPTYSIS": 0}
        r = eng.predict_risk(ev)
        assert r["risk_6y_factors"] < 0.5, (age, r["risk_6y_factors"])
        assert r["risk_score"] < 10, (age, r["risk_score"])
        assert r["alarm"]["level"] == ("urgent" if age >= 40 else "none")


SMOKERS = [  # (yaş, adet/gün, içilen yıl, aktif mi, bırakalı yıl)
    (30, 10, 10, True, None), (45, 10, 10, True, None), (45, 20, 25, True, None),
    (55, 20, 35, True, None), (62, 20, 30, True, None), (62, 10, 20, False, 15),
    (68, 30, 45, False, 5), (72, 20, 50, True, None), (58, 15, 20, False, 20),
]


@pytest.mark.parametrize("age,cigs,yrs,current,yq", SMOKERS)
def test_6y_layer_agrees_with_plcom2012(eng, age, cigs, yrs, current, yq):
    grp = 0 if age < 55 else min(4, (age - 55) // 5 + 1)
    ev = {"AGE": grp, "_age_exact": age, "GENDER": 1, "SMOKING": 1 if current else 0,
          "_cigs_per_day": cigs, "_years_smoked": yrs, "_pack_years": cigs / 20 * yrs,
          "FAMILY_HISTORY": 0, "COPD": 0}
    if yq is not None:
        ev["_years_quit"] = yq
    r = eng.predict_risk(ev)
    plco = r["benchmark_plcom2012"]["risk_6y"]
    ratio = r["risk_6y_factors"] / plco
    assert 0.5 <= ratio <= 2.0, f"6y {r['risk_6y_factors']} vs PLCOm2012 {plco} (×{ratio:.1f})"


def test_more_pack_years_and_age_never_lower_6y(eng):
    prev = 0
    for py in (5, 10, 20, 30, 45, 60):
        ev = {"AGE": 2, "_age_exact": 62, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 20,
              "_years_smoked": py, "_pack_years": py}
        p = eng.predict_risk(ev)["risk_6y_factors"]; assert p >= prev - 1e-9, (py, p, prev); prev = p
    prev = 0
    for age in (35, 45, 52, 57, 62, 67, 72, 78):
        grp = 0 if age < 55 else min(4, (age - 55) // 5 + 1)
        ev = {"AGE": grp, "_age_exact": age, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 20,
              "_years_smoked": 25, "_pack_years": 25}
        p = eng.predict_risk(ev)["risk_6y_factors"]; assert p >= prev - 1e-9, (age, p, prev); prev = p


@pytest.mark.parametrize("factor,levels", [("FAMILY_HISTORY", (0, 1)), ("ASBESTOS", (0, 1)),
                                           ("AIR_POLLUTION", (0, 1, 2)), ("COPD", (0, 1))])
def test_risk_factor_never_lowers_6y(eng, factor, levels):
    for base in BASES.values():
        ps = [eng.predict_risk({**base, factor: lv})["risk_6y_factors"] for lv in levels]
        assert ps == sorted(ps), (factor, ps)


def test_unobserved_symptoms_full_equals_6y(eng):
    for base in BASES.values():
        r = eng.predict_risk(base)
        assert r["risk_score"] == pytest.approx(r["risk_6y_factors"], abs=0.01)


@pytest.mark.parametrize("sex", [0, 1])
def test_never_smoker_not_above_smokers(eng, sex):
    """Aynı yaş/cinsiyette hiç içmemiş ≤ 5 paket-yıl aktif içici ≤ 20 paket-yıl aktif içici."""
    for age in (45, 52, 60, 66, 72):
        grp = 0 if age < 55 else min(4, (age - 55) // 5 + 1)
        base = {"AGE": grp, "_age_exact": age, "GENDER": sex}
        never = eng.predict_risk({**base, "SMOKING": 0, "_pack_years": 0})["risk_6y_factors"]
        light = eng.predict_risk({**base, "SMOKING": 1, "_cigs_per_day": 10, "_years_smoked": 10,
                                  "_pack_years": 5})["risk_6y_factors"]
        heavy = eng.predict_risk({**base, "SMOKING": 1, "_cigs_per_day": 20, "_years_smoked": 20,
                                  "_pack_years": 20})["risk_6y_factors"]
        assert never <= light <= heavy, (age, sex, never, light, heavy)


def test_never_smoker_matches_wakelee_2007(eng):
    """Hiç içmemiş 6 yıllık risk, Wakelee 2007 40–79 yaş insidans aralığından (4,8–20,8/100.000/yıl)
    türetilen aralıkta: 45–75 yaşta ≈ %0,01–%0,5."""
    for age in (45, 60, 75):
        for sex in (0, 1):
            grp = 0 if age < 55 else min(4, (age - 55) // 5 + 1)
            p = eng.predict_risk({"AGE": grp, "_age_exact": age, "GENDER": sex, "SMOKING": 0,
                                  "_pack_years": 0})["risk_6y_factors"]
            assert 0.01 <= p <= 0.5, (age, sex, p)


def test_symptom_cooccurrence_matches_nhanes(eng):
    """Kansersiz, hiç içmemiş, KOAH'sız kişide öksürük–hırıltı birlikteliği NHANES 2007-12 ile uyumlu:
    veri OR = 4,1 (n=5053, 40+ yaş). v3.0 bu grupta bağımsızlık (OR 1,0) varsayıyordu."""
    from pgmpy.inference import VariableElimination
    q = VariableElimination(eng.model).query(["COUGHING", "WHEEZING"], show_progress=False,
                                             evidence={"LUNG_CANCER": 0, "SMOKING": 0, "COPD": 0})
    v = q.values if q.variables[0] == "COUGHING" else q.values.T
    odds_ratio = v[1, 1] * v[0, 0] / (v[1, 0] * v[0, 1])
    assert 2.5 <= odds_ratio <= 5.5, odds_ratio


def test_marginal_symptom_prevalence_unchanged_without_cancer(eng):
    """Ortak neden düğümü kansersiz kişideki her belirtinin marjinal sıklığını (NHANES/literatür
    kalibrasyonu) değiştirmemeli — yalnız belirtiler arası korelasyon eklenir."""
    from pgmpy.inference import VariableElimination
    from model.hybrid_bayesian_network_v3 import NOISY_OR, SIMPLE_SYMPTOMS
    ve = VariableElimination(eng.model)
    for s in S7:
        for sm, copd in ((0, 0), (1, 0), (1, 1)):
            p = float(ve.query([s], evidence={"LUNG_CANCER": 0, "SMOKING": sm, "COPD": copd},
                               show_progress=False).values[1])
            if s in NOISY_OR:
                c = NOISY_OR[s]
                exp = 1 - (1 - c["leak"]) * (1 - c["smoke"]) ** sm * (1 - c["copd"]) ** copd
            else:
                exp = SIMPLE_SYMPTOMS[s][0]
            assert p == pytest.approx(exp, abs=1e-9), (s, sm, copd, p, exp)
