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
NOISY_OR = {
    "COUGHING":            {"leak": 0.10, "smoke": 0.08, "copd": 0.55, "cancer": 0.556},
    "SHORTNESS_OF_BREATH": {"leak": 0.08, "smoke": 0.05, "copd": 0.50, "cancer": 0.457},
    "WHEEZING":            {"leak": 0.05, "smoke": 0.03, "copd": 0.40, "cancer": 0.179},
}
# Diğer semptomlar: (P(s|semptomatik kanser değil), P(s|semptomatik kanser)) — v2 ile aynı
SIMPLE_SYMPTOMS = {
    "CHEST_PAIN":  (0.05, 0.35),
    "FATIGUE":     (0.20, 0.50),
    "HEMOPTYSIS":  (0.01, 0.20),
    "WEIGHT_LOSS": (0.05, 0.35),
}
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


# ==============================================================
# 2. YAPI
# ==============================================================

def get_structure_v3():
    edges = [(f, "LUNG_CANCER") for f in RISK_FACTOR_NODES]
    edges += [("SMOKING", "COPD"), ("LUNG_CANCER", "SYMPTOMATIC")]
    edges += [("SYMPTOMATIC", s) for s in SYMPTOMS_7]
    edges += [(p, s) for s in NOISY_OR for p in ("SMOKING", "COPD")]
    return edges


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


def effective_or(factor: str, level: int) -> float:
    """Kullanılan çarpan: OR / E[OR] (normalize) ya da ham OR."""
    orv = RISK_FACTOR_ORS[factor][level]
    return orv / _mean_or(factor) if NORMALIZE_ORS else orv


def build_cancer_cpd_v3(nlst_cpts: dict) -> TabularCPD:
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
                                mult = (effective_or("FAMILY_HISTORY", fh) *
                                        effective_or("ASBESTOS", asb) *
                                        effective_or("AIR_POLLUTION", air) *
                                        effective_or("COPD", copd))
                                p = min(0.999, max(0.001, _apply_odds_ratio(base, mult)))
                                p1.append(p); p0.append(1 - p)
    return TabularCPD("LUNG_CANCER", 2, [p0, p1],
                      evidence=RISK_FACTOR_NODES,
                      evidence_card=[cards[n] for n in RISK_FACTOR_NODES])


def build_copd_cpd() -> TabularCPD:
    p = [COPD_GIVEN_SMOKING[0], COPD_GIVEN_SMOKING[1]]
    return TabularCPD("COPD", 2, [[1 - p[0], 1 - p[1]], [p[0], p[1]]],
                      evidence=["SMOKING"], evidence_card=[2])


def build_symptomatic_cpd(q: float = SYMPTOMATIC_FRACTION) -> TabularCPD:
    # Sütunlar: LC=0, LC=1.  Kanser yoksa "kanser-semptomatik" olamaz.
    return TabularCPD("SYMPTOMATIC", 2, [[1.0, 1 - q], [0.0, q]],
                      evidence=["LUNG_CANCER"], evidence_card=[2])


def _noisy_or(p: dict, s: int, sm: int, copd: int) -> float:
    q = (1 - p["leak"]) * (1 - p["smoke"]) ** sm * (1 - p["copd"]) ** copd * (1 - p["cancer"]) ** s
    return 1 - q


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
                          verbose: bool = True) -> DiscreteBayesianNetwork:
    if verbose:
        print("\n🧠 BUILDING HYBRID BBN v3 (latent semptomatik + KOAH + OR normalizasyonu)")
        print("=" * 72)
    df = pd.read_csv(nlst_data_path)
    model = DiscreteBayesianNetwork(get_structure_v3())
    nlst_cpts = compute_nlst_cancer_cpt(df) if verbose else _quiet(compute_nlst_cancer_cpt, df)
    # v2 priorları: AGE, GENDER, SMOKING, FAMILY_HISTORY, ASBESTOS, AIR_POLLUTION
    priors = build_prior_cpds()
    model.add_cpds(build_cancer_cpd_v3(nlst_cpts), *priors, build_copd_cpd(),
                   build_symptomatic_cpd(), *build_symptom_cpds_v3())
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

    def __init__(self, model: DiscreteBayesianNetwork, bands: str = BANDS_CHOICE):
        self.bands = bands
        b = RISK_BANDS[bands]
        self.RISK_LEVELS = {k: {**v, "range": b[k]}
                            for k, v in HybridLungCancerEngine.RISK_LEVELS.items()}
        super().__init__(model)

    def _posterior(self, ev: dict, never_flag: bool) -> float:
        valid = set(self.model.nodes()) - {"LUNG_CANCER", "SYMPTOMATIC"}
        q = self.inference.query(variables=["LUNG_CANCER"],
                                 evidence={k: v for k, v in ev.items() if k in valid})
        p = float(q.values[1])
        if never_flag:
            from model.hybrid_bayesian_network import NEVER_SMOKER_OR
            o = p / max(1e-9, 1 - p) * NEVER_SMOKER_OR
            p = o / (1 + o)
        return min(0.9999, max(0.0001, p))

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

        res.update({
            "model_version": MODEL_VERSION,
            "bands": self.bands,
            "q_symptomatic": SYMPTOMATIC_FRACTION,
            "risk_6y_factors": round(p6 * 100, 2),
            "risk_level_factors": lvl6,
            "risk_level_factors_tr": self.RISK_LEVELS[lvl6]["label_tr"],
            "alarm": nice_ng12_alarm(ev),
            "horizon_note_tr": "Olasılıklar yaklaşık 6 yıllık tanı riskidir (NLST izlem ufku).",
        })
        # Öneri metni iki katmana göre: alarm yoksa "Yüksek" bile tarama dilinde konuşur
        alarm = res["alarm"]["level"] == "urgent"
        res["recommendation_tr"] = self._recommend_v3(res["risk_level"], alarm, "tr")
        res["recommendation_en"] = self._recommend_v3(res["risk_level"], alarm, "en")
        res["data_sources"]["symptoms"] = ("Literatür (Hamilton 2005, Beckles 2003) + latent "
                                           "semptomatik düğüm; KOAH ortak neden (noisy-OR)")
        return res


    @staticmethod
    def _recommend_v3(level: str, alarm: bool, lang: str) -> str:
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
            "low": ("Tahmini riskiniz şu an düşük görünüyor. Bu, risk faktörlerinizin önemsiz olduğu "
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
            "low": ("Your estimated risk currently appears low. This does not mean your risk factors are "
                    "unimportant; smoking, age or occupational exposure remain relevant. See a physician "
                    "if new symptoms appear. This is a screening tool, not a diagnosis."),
        }
        key = "urgent" if alarm else level
        return (tr if lang == "tr" else en)[key]


def load_engine(version: str = "v3", verbose: bool = False):
    """Sürüm seçici: 'v2' → eski motor (değişmedi), 'v3' → bu modül."""
    if version == "v2":
        from model.hybrid_bayesian_network import build_hybrid_model
        m = build_hybrid_model() if verbose else _quiet(build_hybrid_model)
        return HybridLungCancerEngine(m) if verbose else _quiet(HybridLungCancerEngine, m)
    m = build_hybrid_model_v3(verbose=verbose)
    return HybridLungCancerEngineV3(m) if verbose else _quiet(HybridLungCancerEngineV3, m)


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
