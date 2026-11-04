# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI - Hybrid Bayesian Belief Network v3
=================================================
v2 (hybrid_bayesian_network.py) OLDUĞU GİBİ KORUNUR; bu modül v2'nin NLST
tabanını ve belgelenmiş semptom olasılıklarını yeniden kullanır, ama dört
metodolojik düzeltme ekler (gerekçe: docs/v3_tasarim.md):

  1. LATENT "SEMPTOMATİK" DÜĞÜMÜ
       LUNG_CANCER → SYMPTOMATIC → semptomlar
     NLST etiketi "~6 yıl içinde tanı" (katılımcılar başlangıçta asemptomatik);
     semptom olasılıkları ise "klinik tanı anındaki" hastalardan gelir. Araya
     P(semptomatik | kanser) = q (varsayılan 0.35) konarak iki anlam ayrılır:
     7 "hayır" cevabı artık tabanı 36 kat değil ~1.5 kat düşürür.

  2. KOAH DÜĞÜMÜ (ortak neden)
       SMOKING → COPD → {COUGHING, SHORTNESS_OF_BREATH, WHEEZING};  COPD → LUNG_CANCER
     Üç solunum semptomunun birlikte görülmesini açıklar (naive-Bayes çift
     saymayı azaltır) ve KOAH'ı gerçek bir risk faktörü olarak ekler
     (PLCOm2012: OR 1.43). Semptom CPT'leri noisy-OR ile üretilir.

  3. OR NORMALİZASYONU
     NLST hücresi "ortalama maruziyetli" kişinin riskidir; literatür OR'leri
     popülasyon ortalamasına bölünür (OR / E[OR]) ki sorulmayan/ortalama kişi
     NLST hücresine düşsün.

  4. İKİ KATMANLI ÇIKTI + KLİNİK UYARI KURALI
     • risk_6y_factors : yalnız risk faktörlerinden 6 yıllık risk (tarama katmanı)
     • risk_score      : semptomlar dahil tam sonsal (v2 ile aynı anlamda)
     • alarm           : NICE NG12 (2015/2023) acil sevk kuralı — skordan bağımsız
     Risk bantları v3'te zaman ufkuna bağlanır: Düşük <%1.5, Orta %1.5–5,
     Yüksek ≥%5 (PLCOm2012 tarama eşiği %1.51/6 yıl). Eski bantlar için
     PRAEVIDIO_BANDS=v2.

Kullanım:
  python src/model/hybrid_bayesian_network_v3.py      # kur, doğrula, demo
  from model.hybrid_bayesian_network_v3 import load_engine
  engine = load_engine("v3")   # veya "v2"
"""

import os
import sys
import json
from pathlib import Path

import pandas as pd
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.factors.discrete import TabularCPD
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))
from model.hybrid_bayesian_network import (   # v2 yeniden kullanılır, değiştirilmez
    compute_nlst_cancer_cpt, _apply_odds_ratio, build_prior_cpds,
    RISK_FACTOR_ORS as V2_RISK_FACTOR_ORS,
    HybridLungCancerEngine, NLST_CLEANED_PATH, RESULTS_DIR,
)

MODEL_VERSION = "v3"

# ==============================================================
# 1. PARAMETRELER (hepsi tek yerde; duyarlılık analizi için env ile ezilebilir)
# ==============================================================

# q = P(şu an semptomatik | ~6 yıl içinde tanı alacak).  Tarama popülasyonunda
# vakaların çoğu başlangıçta asemptomatiktir; 0.35 başlangıç değeri, uzman görüşü
# ve Hamilton PPV tutarlılık testiyle ayarlanır (docs/v3_tasarim.md §2).
SYMPTOMATIC_FRACTION = float(os.getenv("PRAEVIDIO_Q_SYMPTOMATIC", "0.35"))

# Literatür OR'leri (v2 + KOAH). KOAH: PLCOm2012 exp(0.3553)=1.43 (Tammemägi 2013)
RISK_FACTOR_ORS = {**V2_RISK_FACTOR_ORS, "COPD": {0: 1.00, 1: 1.43}}

# Faktör priorları (gözlenmediğinde marjinalizasyon + OR normalizasyonu için)
RISK_FACTOR_PRIORS = {
    "FAMILY_HISTORY": [0.90, 0.10],
    "ASBESTOS":       [0.92, 0.08],
    "AIR_POLLUTION":  [0.10, 0.70, 0.20],
}
# P(KOAH | sigara): eski içici %12, aktif içici %20 (NLST öz-bildirim KOAH/amfizem
# ~%15-18; genel nüfus ağır içicilerde %15-25)
COPD_GIVEN_SMOKING = {0: 0.12, 1: 0.20}
NORMALIZE_ORS = os.getenv("PRAEVIDIO_NORMALIZE_ORS", "1") not in ("0", "false", "False")

# Solunum semptomları: noisy-OR parametreleri.
#   P(s=1 | S, sm, copd) = 1 − (1−leak)·(1−p_smoke)^sm·(1−p_copd)^copd·(1−p_cancer)^S
#   leak   : kansersiz, içmeyen, KOAH'sız taban (v2 LC=0,SM=0 sütunu)
#   cancer : v2'nin P(s|LC=1,SM=0) değerini aynen üreten katkı
#   smoke  : KOAH DIŞI sigara katkısı (küçük); copd: KOAH katkısı (büyük)
# NHANES 2007-12 kalibrasyonu (16 Ekim 2026, docs/nhanes_semptom_tabanlari.md; 40+ yaş, kansersiz):
#   kronik öksürük  hiç %5,7 / eski %9,2 / aktif %25,1   → model (daha geniş "geçmeyen öksürük" tanımı):
#                   %10 / %16,5 / %30  (leak korundu, aktif içici katkısı NHANES oranına göre artırıldı)
#   hırıltı (12 ay) hiç %8,4 / eski %14,4 / aktif %27,2  → model %8 / %14 / %26  (leak 0.05→0.08; v3.0 ~1,8× düşüktü)
#   nefes darlığı   NHANES'te yok → literatür değeri korundu
# "cancer" katkısı, v2'nin belgelenmiş P(s | kanser, içmiyor) hedefini (0.60 / 0.50 / 0.22) aynen üretir.
NOISY_OR = {
    "COUGHING":            {"leak": 0.10, "smoke": 0.12, "copd": 0.60, "cancer": 0.556},
    "SHORTNESS_OF_BREATH": {"leak": 0.08, "smoke": 0.05, "copd": 0.50, "cancer": 0.457},
    "WHEEZING":            {"leak": 0.08, "smoke": 0.10, "copd": 0.55, "cancer": 0.152},
}
# Diğer semptomlar: (P(s|semptomatik kanser değil), P(s|semptomatik kanser)) — v2 ile aynı
SIMPLE_SYMPTOMS = {
    "CHEST_PAIN":  (0.05, 0.35),
    "FATIGUE":     (0.20, 0.50),
    "HEMOPTYSIS":  (0.01, 0.20),
    "WEIGHT_LOSS": (0.05, 0.35),
}
# v3.1 ortak neden: "başka bir hastalık" (enfeksiyon, astım, reflü, kaygı, kas-iskelet ağrısı…).
# v3.0'da yalnız KOAH, yalnız üç solunum belirtisini açıklıyordu; göğüs ağrısı, halsizlik, kilo
# kaybı ve hemoptizi kansersiz kişide birbirinden bağımsızdı → kanser olasılık oranları çarpılıyor,
# 5 belirtide ×380'e çıkıyordu (Hamilton 2005 ile tutarsız). Parametreler:
#   OTHER_PRIOR  π : P(başka bir hastalık var) — gözlenmez, yalnız belirtiler üzerinden çıkarılır
#   OTHER_SHARE  ρ : her belirtinin kansersiz taban sıklığının (leak) ortak nedenden gelen payı
# Belirti başına katkı p_o = ρ·leak/π; leak' = 1 − (1−leak)/(1−ρ·leak) → kansersiz kişide her
# belirtinin marjinal sıklığı (NHANES kalibrasyonu) DEĞİŞMEZ, yalnız belirtiler arası korelasyon eklenir.
# Kalibrasyon (Kas 2026, tests/model + docs/v3_1_duzeltme.md): NHANES 2007-12 kansersiz, 40+, hiç
# içmemiş ve KOAH/amfizem/kronik bronşit tanısı olmayanlarda OR(kronik öksürük, hırıltı) = 4,1
# (n=5053); v3.0'da bu grupta OR = 1,0 (bağımsız). p_o ≤ p_cancer kısıtıyla ulaşılabilen en yakın
# değer π=0,20, ρ=1,0 → OR 3,4 (veriden hafif düşük = açıklama etkisini abartmaz).
OTHER_PRIOR = float(os.getenv("PRAEVIDIO_OTHER_PRIOR", "0.20"))
OTHER_SHARE = float(os.getenv("PRAEVIDIO_OTHER_SHARE", "1.0"))
OTHER_CAUSE = os.getenv("PRAEVIDIO_OTHER_CAUSE", "1") not in ("0", "false", "False")

SYMPTOMS_7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING",
              "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
RISK_FACTOR_NODES = ["AGE", "GENDER", "SMOKING", "FAMILY_HISTORY", "ASBESTOS",
                     "AIR_POLLUTION", "COPD"]

# Risk bantları — 6 yıllık risk ufku.
#   v3: PLCOm2012 tarama eşiği %1.51 (USPSTF-2013 eşdeğeri) → "Orta" = tarama adayı;
#       ≥%5 (NLST taban oranının ~1.3 katı, v2'nin Orta eşiği) → "Yüksek"
#   v2: 5 / 15 (geriye dönük karşılaştırma için)
RISK_BANDS = {
    "v3": {"low": (0.0, 0.015), "moderate": (0.015, 0.05), "high": (0.05, 1.0)},
    "v2": {"low": (0.0, 0.05),  "moderate": (0.05, 0.15),  "high": (0.15, 1.0)},
}
BANDS_CHOICE = os.getenv("PRAEVIDIO_BANDS", "v3")

# Taban risk kaynağı: "nlst" (varsayılan; BBN'in NLST hücresi) | "plco" (PLCOm2012 uygulanabiliyorsa
# risk-faktörü katmanı PLCOm2012'den alınır, semptom kanıtı BBN'den türetilen olasılık oranı
# (LR = odds(tam sonsal)/odds(faktör-sonsalı)) olarak PLCO odds'una uygulanır; uygulanamıyorsa NLST).
BASE_RISK_SOURCE = os.getenv("PRAEVIDIO_BASE_RISK", "plco")      # v3.1 varsayılanı; v3.0: "nlst"

# v3.1 hiç içmemiş tabanı (base_risk="plco" ile birlikte): Wakelee 2007 (J Clin Oncol 25:472),
# altı kohort, 40–79 yaş yaşa göre standardize insidans: erkek 4,8–13,7, kadın 14,4–20,8 /100.000
# kişi-yıl → aralık ortaları (9,3 / 17,6) ~58 yaşa atanır; yaşla her 10 yılda ×2,2 artış (akciğer
# kanseri insidansının yaş eğimi). 6 yıllık risk ≈ 1 − exp(−6·oran). NLST'de hiç içmemiş yoktu;
# v3.0'daki NLST eski-içici hücresi × 0,15 yaklaşımı 60–70 yaşta 4–7 kat yüksekti.
NEVER_SMOKER_RATE_100K = {0: 17.6, 1: 9.3}      # GENDER: 0 kadın, 1 erkek (Wakelee 2007 orta değerler)
NEVER_SMOKER_REF_AGE = 58.0
NEVER_SMOKER_AGE_FACTOR_10Y = 2.2


# ==============================================================
# 2. YAPI
# ==============================================================

def get_structure_v3(other_cause: bool = False):
    edges = [(f, "LUNG_CANCER") for f in RISK_FACTOR_NODES]
    edges += [("SMOKING", "COPD"), ("LUNG_CANCER", "SYMPTOMATIC")]
    edges += [("SYMPTOMATIC", s) for s in SYMPTOMS_7]
    edges += [(p, s) for s in NOISY_OR for p in ("SMOKING", "COPD")]
    if other_cause:
        edges += [("OTHER_ILLNESS", s) for s in SYMPTOMS_7]
    return edges


def other_cause_params(prior: float = None, share: float = None) -> dict:
    """{belirti: (leak', p_o)} — marjinal kansersiz sıklığı koruyan ortak neden parametreleri."""
    prior = OTHER_PRIOR if prior is None else prior
    share = OTHER_SHARE if share is None else share
    leaks = {k: v["leak"] for k, v in NOISY_OR.items()}
    leaks.update({k: v[0] for k, v in SIMPLE_SYMPTOMS.items()})
    p_cancer = {k: v["cancer"] for k, v in NOISY_OR.items()}
    p_cancer.update({k: 1 - (1 - v[1]) / (1 - v[0]) for k, v in SIMPLE_SYMPTOMS.items()})
    out = {}
    for s, leak in leaks.items():
        # Ortak neden bir belirtiyi semptomatik kanserden daha güçlü üretemez (p_o ≤ p_cancer).
        # Aksi hâlde çok yaygın/özgül olmayan belirtiler (halsizlik, hırıltı) "başka hastalık"
        # kanıtına dönüşüp diğer belirtileri açıklar ve belirti EKLEMEK riski düşürür.
        p_o = min(share * leak / prior, p_cancer[s])
        if not 0 <= p_o <= 1:
            raise ValueError(f"{s}: p_o={p_o:.2f} — OTHER_PRIOR ≥ OTHER_SHARE·leak olmalı")
        out[s] = (1 - (1 - leak) / (1 - prior * p_o), p_o)
    return out


# ==============================================================
# 3. CPT'LER
# ==============================================================

def _mean_or(factor: str) -> float:
    """E[OR] — faktörün popülasyon priori altındaki ortalama çarpanı."""
    if factor == "COPD":
        p = 0.518 * COPD_GIVEN_SMOKING[0] + 0.482 * COPD_GIVEN_SMOKING[1]
        pri = [1 - p, p]
    else:
        pri = RISK_FACTOR_PRIORS[factor]
    return sum(w * RISK_FACTOR_ORS[factor][i] for i, w in enumerate(pri))


def effective_or(factor: str, level: int, normalize: bool = None) -> float:
    """Kullanılan çarpan: OR / E[OR] (normalize) ya da ham OR."""
    normalize = NORMALIZE_ORS if normalize is None else normalize
    orv = RISK_FACTOR_ORS[factor][level]
    return orv / _mean_or(factor) if normalize else orv


def build_cancer_cpd_v3(nlst_cpts: dict, normalize: bool = None) -> TabularCPD:
    cards = {"AGE": 5, "GENDER": 2, "SMOKING": 2, "FAMILY_HISTORY": 2,
             "ASBESTOS": 2, "AIR_POLLUTION": 3, "COPD": 2}
    p1, p0 = [], []
    for age in range(5):
        for g in range(2):
            for sm in range(2):
                base = nlst_cpts.get((age, g, sm), 0.0385)
                for fh in range(2):
                    for asb in range(2):
                        for air in range(3):
                            for copd in range(2):
                                mult = (effective_or("FAMILY_HISTORY", fh, normalize) *
                                        effective_or("ASBESTOS", asb, normalize) *
                                        effective_or("AIR_POLLUTION", air, normalize) *
                                        effective_or("COPD", copd, normalize))
                                p = min(0.999, max(0.001, _apply_odds_ratio(base, mult)))
                                p1.append(p); p0.append(1 - p)
    return TabularCPD("LUNG_CANCER", 2, [p0, p1],
                      evidence=RISK_FACTOR_NODES,
                      evidence_card=[cards[n] for n in RISK_FACTOR_NODES])


def build_copd_cpd() -> TabularCPD:
    p = [COPD_GIVEN_SMOKING[0], COPD_GIVEN_SMOKING[1]]
    return TabularCPD("COPD", 2, [[1 - p[0], 1 - p[1]], [p[0], p[1]]],
                      evidence=["SMOKING"], evidence_card=[2])


def build_symptomatic_cpd(q: float = None) -> TabularCPD:
    # Sütunlar: LC=0, LC=1.  Kanser yoksa "kanser-semptomatik" olamaz.
    q = SYMPTOMATIC_FRACTION if q is None else q
    return TabularCPD("SYMPTOMATIC", 2, [[1.0, 1 - q], [0.0, q]],
                      evidence=["LUNG_CANCER"], evidence_card=[2])


def _noisy_or(p: dict, s: int, sm: int, copd: int) -> float:
    q = (1 - p["leak"]) * (1 - p["smoke"]) ** sm * (1 - p["copd"]) ** copd * (1 - p["cancer"]) ** s
    return 1 - q


def build_other_cause_cpds(prior: float = None, share: float = None) -> list:
    """OTHER_ILLNESS düğümü + ortak nedenli 7 belirti CPT'si (noisy-OR, sıra pgmpy: ilk ebeveyn en yavaş)."""
    import itertools
    prior = OTHER_PRIOR if prior is None else prior
    par = other_cause_params(prior, share)
    cpds = [TabularCPD("OTHER_ILLNESS", 2, [[1 - prior], [prior]])]
    for name in SYMPTOMS_7:
        leak2, p_o = par[name]
        if name in NOISY_OR:
            p = NOISY_OR[name]
            yes = [1 - (1 - leak2) * (1 - p["smoke"]) ** sm * (1 - p["copd"]) ** copd
                   * (1 - p["cancer"]) ** s * (1 - p_o) ** o
                   for s, sm, copd, o in itertools.product(range(2), repeat=4)]
            ev, card = ["SYMPTOMATIC", "SMOKING", "COPD", "OTHER_ILLNESS"], [2, 2, 2, 2]
        else:
            p0, p1 = SIMPLE_SYMPTOMS[name]
            pc = 1 - (1 - p1) / (1 - p0)          # P(s|semptomatik kanser)=p1 korunur
            yes = [1 - (1 - leak2) * (1 - pc) ** s * (1 - p_o) ** o
                   for s, o in itertools.product(range(2), repeat=2)]
            ev, card = ["SYMPTOMATIC", "OTHER_ILLNESS"], [2, 2]
        cpds.append(TabularCPD(name, 2, [[1 - y for y in yes], yes], evidence=ev, evidence_card=card))
    return cpds


def build_symptom_cpds_v3() -> list:
    cpds = []
    for name, p in NOISY_OR.items():
        yes = []
        for s in range(2):            # SYMPTOMATIC en yavaş değişir (pgmpy sırası)
            for sm in range(2):
                for copd in range(2):
                    yes.append(_noisy_or(p, s, sm, copd))
        cpds.append(TabularCPD(name, 2, [[1 - y for y in yes], yes],
                               evidence=["SYMPTOMATIC", "SMOKING", "COPD"],
                               evidence_card=[2, 2, 2]))
    for name, (p0, p1) in SIMPLE_SYMPTOMS.items():
        cpds.append(TabularCPD(name, 2, [[1 - p0, 1 - p1], [p0, p1]],
                               evidence=["SYMPTOMATIC"], evidence_card=[2]))
    return cpds


def build_hybrid_model_v3(nlst_data_path: Path = NLST_CLEANED_PATH,
                          verbose: bool = True, q: float = None,
                          normalize: bool = None, other_cause: bool = None,
                          other_prior: float = None, other_share: float = None) -> DiscreteBayesianNetwork:
    """q / normalize / other_*: duyarlılık analizi için parametre geçersiz kılma (None → config)."""
    other_cause = OTHER_CAUSE if other_cause is None else other_cause
    if verbose:
        print("\n🧠 BUILDING HYBRID BBN v3 (latent semptomatik + KOAH + OR normalizasyonu)")
        print("=" * 72)
    df = pd.read_csv(nlst_data_path)
    model = DiscreteBayesianNetwork(get_structure_v3(other_cause))
    nlst_cpts = compute_nlst_cancer_cpt(df) if verbose else _quiet(compute_nlst_cancer_cpt, df)
    # v2 priorları: AGE, GENDER, SMOKING, FAMILY_HISTORY, ASBESTOS, AIR_POLLUTION
    priors = build_prior_cpds()
    model.add_cpds(build_cancer_cpd_v3(nlst_cpts, normalize), *priors, build_copd_cpd(),
                   build_symptomatic_cpd(q),
                   *(build_other_cause_cpds(other_prior, other_share) if other_cause else build_symptom_cpds_v3()))
    assert model.check_model(), "v3 model validation FAILED"
    if verbose:
        print(f"   ✅ v3 doğrulandı — {len(model.nodes())} düğüm, {len(model.edges())} kenar, "
              f"q={SYMPTOMATIC_FRACTION}, OR normalizasyonu={'açık' if NORMALIZE_ORS else 'kapalı'}")
    return model


def _quiet(fn, *a, **k):
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


# ==============================================================
# 4. KLİNİK UYARI KURALI (NICE NG12 — skordan bağımsız)
# ==============================================================

def nice_ng12_alarm(ev: dict) -> dict:
    """
    NICE NG12 "Suspected cancer: recognition and referral" (1.1.1–1.1.3):
      • ≥40 yaş ve açıklanamayan hemoptizi → acil sevk (2 hafta)
      • ≥40 yaş ve ≥2 açıklanamayan semptom (öksürük, yorgunluk, nefes darlığı,
        göğüs ağrısı, kilo kaybı, iştahsızlık) → acil göğüs röntgeni
      • ≥40 yaş, hiç sigara içmiş ve ≥1 bu semptomdan → acil göğüs röntgeni
    Kaynak: https://www.nice.org.uk/guidance/ng12
    """
    age = ev.get("_age_exact")
    if age is None:
        age_ok = True if ev.get("AGE", 0) >= 1 else None   # grup ≥1 → ≥55; <55 bilinmiyor
    else:
        age_ok = age >= 40
    ever_smoker = ev.get("SMOKING") in (0, 1) and (ev.get("_pack_years") is None or ev.get("_pack_years", 0) > 0)
    core = ["COUGHING", "FATIGUE", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WEIGHT_LOSS"]
    n_core = sum(1 for s in core if ev.get(s) == 1)
    reasons = []
    if ev.get("HEMOPTYSIS") == 1 and age_ok is not False:
        reasons.append("Hemoptizi (kan tükürme) — acil değerlendirme gerektiren alarm belirtisi")
    if age_ok and n_core >= 2:
        reasons.append(f"≥40 yaş ve {n_core} açıklanamayan semptom (NICE NG12)")
    elif age_ok and ever_smoker and n_core >= 1:
        reasons.append("≥40 yaş, sigara öyküsü ve en az bir açıklanamayan semptom (NICE NG12)")
    level = "urgent" if reasons else "none"
    return {
        "level": level,
        "reasons_tr": reasons,
        "message_tr": ("Belirtileriniz skordan bağımsız olarak kısa sürede bir hekim "
                       "değerlendirmesi (göğüs röntgeni) gerektiriyor." if reasons else ""),
        "message_en": ("Independently of the score, your symptoms warrant prompt physician "
                       "assessment (chest X-ray)." if reasons else ""),
        "source": "NICE NG12 §1.1",
    }


# ==============================================================
# 5. MOTOR
# ==============================================================

class HybridLungCancerEngineV3(HybridLungCancerEngine):
    """v2 motorunun çıktı şemasını korur; ek alanlar:
         model_version, risk_6y_factors, risk_level_factors, alarm, bands, q_symptomatic"""

    ICD10_MAP = {**HybridLungCancerEngine.ICD10_MAP, "COPD": "J44.9"}

    def __init__(self, model: DiscreteBayesianNetwork, bands: str = BANDS_CHOICE,
                 base_risk: str = BASE_RISK_SOURCE):
        self.bands = bands
        self.base_risk = base_risk
        b = RISK_BANDS[bands]
        self.RISK_LEVELS = {k: {**v, "range": b[k]}
                            for k, v in HybridLungCancerEngine.RISK_LEVELS.items()}
        super().__init__(model)

    def _posterior(self, ev: dict, never_flag: bool) -> float:
        valid = set(self.model.nodes()) - {"LUNG_CANCER", "SYMPTOMATIC", "OTHER_ILLNESS"}
        q = self.inference.query(variables=["LUNG_CANCER"],
                                 evidence={k: v for k, v in ev.items() if k in valid})
        p = float(q.values[1])
        if never_flag:
            from model.hybrid_bayesian_network import NEVER_SMOKER_OR
            o = p / max(1e-9, 1 - p) * NEVER_SMOKER_OR
            p = o / (1 + o)
        return min(0.9999, max(0.0001, p))

    def _plco_6y(self, ev: dict) -> float:
        """
        v3.1 sigara içmiş kişi tabanı: PLCOm2012 (yaş, adet/gün, süre, bırakalı yıl, KOAH, aile
        öyküsü — sürekli değişkenlerle; NLST'nin 55–74 yaş/≥30 paket-yıl kohort sınırı yok).
          • Bilinmeyen aile öyküsü / KOAH → prior üzerinden ortalama (PLCO'daki 0 varsayımı yerine)
          • PLCOm2012'de olmayan faktörler (asbest, il PM2.5) → normalize OR çarpanı (OR/E[OR]);
            bilinmiyorsa çarpan 1 (marjinal ortalama)
        """
        from model.plcom2012 import plcom2012_from_evidence
        fh = ([(ev["FAMILY_HISTORY"], 1.0)] if ev.get("FAMILY_HISTORY") is not None else
              [(0, RISK_FACTOR_PRIORS["FAMILY_HISTORY"][0]), (1, RISK_FACTOR_PRIORS["FAMILY_HISTORY"][1])])
        pc = COPD_GIVEN_SMOKING[1 if ev.get("SMOKING") == 1 else 0]
        copd = [(ev["COPD"], 1.0)] if ev.get("COPD") is not None else [(0, 1 - pc), (1, pc)]
        p = sum(wf * wc * plcom2012_from_evidence({**ev, "FAMILY_HISTORY": f, "COPD": c})["risk_6y_raw"]
                for f, wf in fh for c, wc in copd)
        mult = 1.0
        for factor in ("ASBESTOS", "AIR_POLLUTION"):
            if ev.get(factor) is not None:
                mult *= effective_or(factor, ev[factor])
        o = p / (1 - p) * mult
        return min(0.9999, max(1e-6, o / (1 + o)))

    def _never_6y(self, ev: dict) -> float:
        """v3.1 hiç içmemiş 6 yıllık taban (Wakelee 2007) × normalize OR'ler (aile, asbest, hava, KOAH)."""
        import math
        from model.plcom2012 import AGE_GROUP_MID
        age = ev.get("_age_exact") or AGE_GROUP_MID.get(ev.get("AGE", 2), 62)
        sexes = [ev["GENDER"]] if ev.get("GENDER") in (0, 1) else [0, 1]
        rate = sum(NEVER_SMOKER_RATE_100K[g] for g in sexes) / len(sexes) / 1e5
        rate *= NEVER_SMOKER_AGE_FACTOR_10Y ** ((age - NEVER_SMOKER_REF_AGE) / 10.0)
        p = 1 - math.exp(-6 * rate)
        mult = 1.0
        for factor in ("FAMILY_HISTORY", "ASBESTOS", "AIR_POLLUTION", "COPD"):
            if ev.get(factor) is not None:
                mult *= effective_or(factor, ev[factor])
        o = p / (1 - p) * mult
        return min(0.9999, max(1e-6, o / (1 + o)))

    def _factor_6y(self, evidence: dict) -> float:
        """Yalnız risk etkenlerinden 6 yıllık risk (predict_risk'teki katman 1 ile aynı yol;
        test_factor_6y_matches_predict_risk eşitliği doğrular). Göreli risk ve projeksiyon için."""
        from model.plcom2012 import plcom2012_from_evidence
        ev = dict(evidence)
        eff, never_flag, _ = self._refine_smoking(ev)
        if eff is not None:
            ev["SMOKING"] = eff
        if self.base_risk == "plco":
            if plcom2012_from_evidence(evidence)["applicable"]:
                return self._plco_6y(evidence)
            if never_flag:
                return self._never_6y(evidence)
        return self._posterior({k: v for k, v in ev.items() if k in RISK_FACTOR_NODES}, never_flag)

    @staticmethod
    def _age_group(age: float) -> int:
        return 0 if age < 55 else min(4, int((age - 55) // 5) + 1)

    def risk_context(self, evidence: dict, p6: float) -> dict:
        """
        Sayıları/bantları değiştirmeden 6 yıllık katmanı anlatan bağlam (Kas 2026):
          • göreli risk: aynı yaş/cinsiyette, hiç içmemiş ve risk etkeni olmayan kişiye göre kaç kat
          • projeksiyon (aktif içici): 50 yaşında (50+ ise 5 yıl sonra) içmeye devam / bugün bırakma
        """
        def pct(x):
            v = x * 100
            return (f"{v:.2f}" if v < 10 else f"{v:.1f}").replace(".", ",")
        out = {"relative_risk_peers": None, "peer_6y": None, "relative_message_tr": None,
               "relative_message_en": None, "projection": None}
        age = evidence.get("_age_exact")
        if age is None and evidence.get("AGE") is None:
            return out
        ref = {"SMOKING": 0, "_pack_years": 0, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0, "COPD": 0}
        for k in ("AGE", "_age_exact", "GENDER"):
            if evidence.get(k) is not None:
                ref[k] = evidence[k]
        p_ref = self._factor_6y(ref)
        rr = p6 / p_ref
        out.update(relative_risk_peers=round(rr, 2), peer_6y=round(p_ref * 100, 3))
        if rr >= 1.5:
            n = (f"{rr:.1f}".replace(".", ",") if rr < 10 else f"{rr:.0f}")
            out["relative_message_tr"] = (f"Aynı yaşta ve cinsiyette, sigara içmeyen ve risk etkeni olmayan birine "
                                          f"göre yaklaşık {n} kat.")
            out["relative_message_en"] = (f"About {n}× that of a never-smoker of the same age and sex without "
                                          f"risk factors.")
        else:
            out["relative_message_tr"] = ("Aynı yaşta ve cinsiyette, sigara içmeyen ve risk etkeni olmayan biriyle "
                                          "benzer düzeyde.")
            out["relative_message_en"] = "Similar to a never-smoker of the same age and sex without risk factors."

        # Projeksiyon: yalnız aktif içici, yaş ve doz biliniyorsa
        cigs, yrs, py = evidence.get("_cigs_per_day"), evidence.get("_years_smoked"), evidence.get("_pack_years")
        if cigs is None and py and yrs:
            cigs = py * 20.0 / yrs
        if yrs is None and py and cigs:
            yrs = py / (cigs / 20.0)
        if evidence.get("SMOKING") != 1 or age is None or not cigs or yrs is None or age >= 80:
            return out
        target = 50 if age < 50 else min(age + 5, 80)
        delta = target - age
        facts = {k: v for k, v in evidence.items() if k in RISK_FACTOR_NODES or k in ("_province",)}
        base = {**facts, "_age_exact": target, "AGE": self._age_group(target), "_cigs_per_day": cigs}
        cont = self._factor_6y({**base, "SMOKING": 1, "_years_smoked": yrs + delta,
                                "_pack_years": round(cigs / 20.0 * (yrs + delta), 1)})
        quit_ = self._factor_6y({**base, "SMOKING": 0, "_years_smoked": yrs,
                                 "_pack_years": round(cigs / 20.0 * yrs, 1), "_years_quit": delta})
        lvl_now, lvl_cont = self._level(p6), self._level(cont)
        enters = lvl_now == "low" and lvl_cont != "low"
        msg_tr = (f"Sigaraya bu şekilde devam ederseniz {target:g} yaşında 6 yıllık riskiniz yaklaşık %{pct(cont)} olur"
                  + (" ve tarama aralığına girersiniz" if enters else "")
                  + f"; bugün bırakırsanız aynı yaşta yaklaşık %{pct(quit_)}.")
        en = lambda x: pct(x).replace(",", ".")
        msg_en = (f"If you keep smoking like this, your 6-year risk at age {target:g} will be about {en(cont)}%"
                  + (", within the screening range" if enters else "")
                  + f"; if you quit today, about {en(quit_)}% at the same age.")
        out["projection"] = {"age": target, "continue_6y": round(cont * 100, 2), "quit_6y": round(quit_ * 100, 2),
                             "continue_level": lvl_cont, "enters_screening_range": enters,
                             "message_tr": msg_tr, "message_en": msg_en}
        return out

    def _level(self, p: float) -> str:
        for lvl, info in self.RISK_LEVELS.items():
            lo, hi = info["range"]
            if lo <= p < hi:
                return lvl
        return "high"

    def predict_risk(self, evidence: dict) -> dict:
        res = super().predict_risk(evidence)          # tam sonsal + v2 şeması (v3 bantlarıyla)

        ev = dict(evidence)
        eff, never_flag, _ = self._refine_smoking(ev)
        if eff is not None:
            ev["SMOKING"] = eff
        # Katman 1: yalnız risk faktörleri (semptomlar marjinalize) → 6 yıllık tarama riski
        p6 = self._posterior({k: v for k, v in ev.items() if k in RISK_FACTOR_NODES}, never_flag)
        lvl6 = self._level(p6)

        # KOAH etiketi ve OR katkısı
        if res["evidence_provided"].get("COPD") == 1:
            res["risk_factors_tr"].append("KOAH / kronik bronşit tanısı")
            res["or_contributions"]["KOAH tanısı"] = RISK_FACTOR_ORS["COPD"][1]

        from model.plcom2012 import plcom2012_from_evidence
        # Benchmark: v3.1'de özgün kanıt (v3.0'da "ağır eski içici → aktif" uyarlanmış kanıt; geriye dönük korunur)
        bm = plcom2012_from_evidence(evidence if self.base_risk == "plco" else ev)
        nlst_p6 = p6
        nlst_full = self._posterior(ev, never_flag)       # = v2 şemasındaki tam sonsal, yuvarlanmamış
        res["risk_probability"] = nlst_full
        base_used = "nlst"
        pb = None
        if self.base_risk == "plco":
            if bm["applicable"]:
                pb, base_used = self._plco_6y(evidence), "plco"     # özgün kanıt ("ağır eski → aktif" kuralı yok)
            elif never_flag:
                pb, base_used = self._never_6y(evidence), "wakelee2007"
        if pb is not None:
            # Semptom kanıtının BBN'deki etkisi = odds oranı; PLCOm2012 tabanına taşınır
            o6, ofull = nlst_p6 / (1 - nlst_p6), nlst_full / (1 - nlst_full)
            lr = ofull / o6
            ob = pb / (1 - pb)
            p6 = pb
            pfull = (ob * lr) / (1 + ob * lr)
            lvl6 = self._level(p6)
            res["risk_probability"] = pfull
            res["risk_score"] = round(pfull * 100, 2)
            res["no_cancer_probability"] = round(1 - pfull, 6)
            res["risk_level"] = self._level(pfull)
            res["risk_level_tr"] = self.RISK_LEVELS[res["risk_level"]]["label_tr"]
            res["risk_level_en"] = self.RISK_LEVELS[res["risk_level"]]["label_en"]
            res["risk_color"] = self.RISK_LEVELS[res["risk_level"]]["color"]
        res.update({
            "benchmark_plcom2012": bm,
            "base_risk_source": base_used,
            "nlst_6y_factors": round(nlst_p6 * 100, 2),
            "model_version": MODEL_VERSION,
            "model_revision": "3.1" if (self.base_risk == "plco" and "OTHER_ILLNESS" in self.model.nodes()) else (
                "3.0" if self.base_risk == "nlst" and "OTHER_ILLNESS" not in self.model.nodes() else "3.x-custom"),
            "bands": self.bands,
            "q_symptomatic": SYMPTOMATIC_FRACTION,
            "risk_6y_factors": round(p6 * 100, 2),
            "risk_6y_probability": p6,                  # yuvarlanmamış (testler/çarpan hesabı)
            "risk_level_factors": lvl6,
            "risk_level_factors_tr": self.RISK_LEVELS[lvl6]["label_tr"],
            "alarm": nice_ng12_alarm(ev),
            "horizon_note_tr": "Olasılıklar yaklaşık 6 yıllık tanı riskidir (NLST izlem ufku).",
        })
        # Öneri metni iki katmana göre: alarm yoksa "Yüksek" bile tarama dilinde konuşur
        alarm = res["alarm"]["level"] == "urgent"
        # Öneri 6 yıllık TARAMA katmanına + alarma bağlı (Kas 2026 düzeltmesi: önceden tam skora
        # bağlıydı → faktörleri "Düşük" kişiye "risk faktörleriniz riskinizi artırıyor" deniyordu).
        # Görüntüleme etiketi: 6 yıllık katman "Düşük" → "Tarama eşiğinin altında" (bant aynı; yalnız ifade).
        # Tüm risk etkenlerine sahip genç biri için yeşil "Düşük Risk" yanlış güven veriyordu.
        disp = {"low": ("Tarama eşiğinin altında", "Below screening threshold")}
        res["risk_level_factors_display_tr"], res["risk_level_factors_display_en"] = disp.get(
            lvl6, (self.RISK_LEVELS[lvl6]["label_tr"], self.RISK_LEVELS[lvl6]["label_en"]))
        res.update(self.risk_context(evidence, p6))
        has_sym = any(ev.get(s) == 1 for s in SYMPTOMS_7)
        res["recommendation_tr"] = self._recommend_v3(lvl6, alarm, "tr", has_sym)
        res["recommendation_en"] = self._recommend_v3(lvl6, alarm, "en", has_sym)
        res["data_sources"]["symptoms"] = ("Literatür (Hamilton 2005, Beckles 2003) + latent "
                                           "semptomatik düğüm; KOAH ortak neden (noisy-OR)")
        return res


    @staticmethod
    def _recommend_v3(level: str, alarm: bool, lang: str, has_symptoms: bool = False) -> str:
        tr = {
            "urgent": ("Belirtileriniz, risk skorunuzdan bağımsız olarak kısa sürede bir hekim "
                       "değerlendirmesi gerektiriyor. Lütfen en kısa sürede bir göğüs hastalıkları "
                       "uzmanına veya aile hekiminize başvurun; göğüs röntgeni ve gerekirse düşük doz "
                       "BT istenebilir. Bu bir tarama aracıdır, tanı koymaz."),
            "high": ("Risk faktörleriniz 6 yıllık akciğer kanseri riskinizi belirgin biçimde artırıyor. "
                     "Düşük doz BT taraması için en yakın KETEM'e veya göğüs hastalıkları uzmanına "
                     "başvurmanızı öneririz; sigara kullanıyorsanız bırakma desteği riskinizi en çok "
                     "düşürecek adımdır."),
            "moderate": ("Risk profiliniz düşük doz BT taramasının önerildiği aralığa yakın. "
                         "Tarama uygunluğunuzu hekiminizle görüşün ve yıllık kontrollerinizi aksatmayın."),
            "low": ("6 yıllık riskiniz şu an tarama eşiğinin altında. Bu, risk faktörlerinizin önemsiz olduğu "
                    "anlamına gelmez; sigara, yaş veya mesleki maruziyet varsa önemini korur. "
                    "Yeni bir belirti olursa hekiminize başvurun. Bu bir tarama aracıdır, tanı koymaz."),
        }
        en = {
            "urgent": ("Independently of your score, your symptoms warrant prompt physician assessment. "
                       "Please see a pulmonologist or your family physician soon; a chest X-ray and, if "
                       "needed, low-dose CT may be ordered. This is a screening tool, not a diagnosis."),
            "high": ("Your risk factors substantially raise your 6-year lung cancer risk. We recommend "
                     "low-dose CT screening via the nearest KETEM or a pulmonologist; if you smoke, "
                     "cessation support is the single most effective step."),
            "moderate": ("Your risk profile is near the range where low-dose CT screening is recommended. "
                         "Discuss screening eligibility with your physician and keep annual check-ups."),
            "low": ("Your 6-year risk is currently below the screening threshold. This does not mean your risk factors are "
                    "unimportant; smoking, age or occupational exposure remain relevant. See a physician "
                    "if new symptoms appear. This is a screening tool, not a diagnosis."),
        }
        key = "urgent" if alarm else level
        text = (tr if lang == "tr" else en)[key]
        if has_symptoms and not alarm:
            # NICE alarmı yok (ör. 40 yaş altı ya da tek, hafif belirti) ama belirti bildirilmiş
            text += (" Bildirdiğiniz şikâyetler çoğu zaman akciğer kanseri dışındaki nedenlerden kaynaklanır; "
                     "yine de birkaç haftadır sürüyor ya da artıyorsa aile hekiminize görünün."
                     if lang == "tr" else
                     " The symptoms you reported usually have causes other than lung cancer; if they have "
                     "lasted several weeks or are getting worse, please see your family physician.")
        return text


# Sürüm ön ayarları — her sürüm adıyla birebir yeniden üretilebilir (tests/model/test_baseline.py)
PRESETS = {
    "v3.0": {"base_risk": "nlst"},
    "v3.1a": {"base_risk": "plco", "other_cause": False},  # ara adım: yalnız yeni taban (A + A2)
    "v3.1": {"base_risk": "plco", "other_cause": True, "other_prior": 0.20, "other_share": 1.0},
}


def load_engine(version: str = "v3", verbose: bool = False, **overrides):
    """
    Sürüm seçici: 'v2' → eski motor (değişmedi); 'v3' → ortam değişkenleriyle varsayılan v3;
    'v3.0' … → dondurulmuş ön ayar (PRESETS). overrides ön ayarı ezer (duyarlılık analizi için).
    """
    if version == "v2":
        from model.hybrid_bayesian_network import build_hybrid_model
        m = build_hybrid_model() if verbose else _quiet(build_hybrid_model)
        return HybridLungCancerEngine(m) if verbose else _quiet(HybridLungCancerEngine, m)
    cfg = {**PRESETS.get(version, {}), **overrides}
    eng_kw = {k: cfg[k] for k in ("base_risk", "bands") if k in cfg}
    mdl_kw = {k: cfg[k] for k in ("q", "normalize", "other_cause", "other_prior", "other_share") if k in cfg}
    if version == "v3.0":
        mdl_kw.setdefault("other_cause", False)
    m = build_hybrid_model_v3(verbose=verbose, **mdl_kw)
    return HybridLungCancerEngineV3(m, **eng_kw) if verbose else _quiet(HybridLungCancerEngineV3, m, **eng_kw)


# ==============================================================
# 6. DEMO
# ==============================================================

if __name__ == "__main__":
    from model.hybrid_bayesian_network import run_demo_scenarios
    eng = HybridLungCancerEngineV3(build_hybrid_model_v3())
    results = run_demo_scenarios(eng)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "v3_demo_scenarios.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in r.items()} for r in results], f, ensure_ascii=False, indent=2, default=str)
    print(f"\n📄 v3 demo sonuçları: {out}")
