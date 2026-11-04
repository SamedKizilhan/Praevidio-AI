# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — v3 duyarlılık analizi
=====================================
q (semptomatik pay), ortak neden parametreleri (π, ρ), OR normalizasyonu değiştirildiğinde ve
v3.0'a göre kilit vakaların skoru nasıl değişiyor; Hamilton zarfı korunuyor mu? Sonuç: docs/v3_duyarlilik.md

Çalıştırma: python src/model/sensitivity_v3.py   (veya: make sensitivity)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from model.hybrid_bayesian_network_v3 import SYMPTOMATIC_FRACTION

OUT = Path(__file__).resolve().parents[2] / "docs" / "v3_duyarlilik.md"
S7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING", "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
B = {"AGE": 4, "GENDER": 1, "SMOKING": 1, "_age_exact": 72, "_cigs_per_day": 20, "_years_smoked": 50,
     "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0}
CASES = [
    ("K1", "72y erkek aktif (50 py), semptom sorulmamış", B),
    ("K2", "aynı, 7 semptom 'hayır'", {**B, **{s: 0 for s in S7}}),
    ("K3", "aynı, sadece hemoptizi 'evet' (6 hayır)", {**B, **{s: 0 for s in S7}, "HEMOPTYSIS": 1}),
    ("K4", "aynı, öksürük+nefes+hırıltı, KOAH ?", {**B, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("K5", "aynı, 7 semptom 'evet'", {**B, **{s: 1 for s in S7}}),
    ("K6", "58y kadın eski içici (15 py, 20 yıl önce), semptomsuz", {"AGE": 1, "GENDER": 0, "SMOKING": 0, "_age_exact": 58, "_pack_years": 15, "_years_quit": 20}),
    ("K7", "62y erkek aktif (30 py), sadece hemoptizi (diğerleri ?)", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "_age_exact": 62, "_cigs_per_day": 20, "_years_smoked": 30, "HEMOPTYSIS": 1}),
]
CASES.append(("K8", "45y erkek aktif (5 py), asbest, 5 belirti, KOAH yok (kullanıcı denemesi)",
              {"AGE": 0, "GENDER": 1, "SMOKING": 1, "_age_exact": 45, "_cigs_per_day": 10, "_years_smoked": 10,
               "_pack_years": 5, "FAMILY_HISTORY": 0, "ASBESTOS": 1, "AIR_POLLUTION": 1, "COPD": 0,
               "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "CHEST_PAIN": 1, "FATIGUE": 1, "WEIGHT_LOSS": 1,
               "WHEEZING": 0, "HEMOPTYSIS": 0}))

# (etiket, load_engine sürümü, ezilen parametreler)
CONFIGS = [
    ("v3.0", "v3.0", {}),
    ("v3.1 (varsayılan)", "v3.1", {}),
    ("q=0.25", "v3.1", {"q": 0.25}), ("q=0.50", "v3.1", {"q": 0.50}),
    ("π=0.15", "v3.1", {"other_prior": 0.15}), ("π=0.30", "v3.1", {"other_prior": 0.30}),
    ("ρ=0.70", "v3.1", {"other_share": 0.70}), ("ρ=0.85", "v3.1", {"other_share": 0.85}),
    ("normalizasyon kapalı", "v3.1", {"normalize": False}),
]


def envelope_worst(eng) -> float:
    """Hamilton zarfı (tests/model/test_plausibility.py): en kötü kombinasyonun çarpan/sınır oranı
    (70+ aktif içici; KOAH yok ve bilinmiyor). ≤1 → zarf içinde."""
    import itertools
    base = {"AGE": 4, "_age_exact": 72, "GENDER": 1, "SMOKING": 1, "_cigs_per_day": 20, "_years_smoked": 50,
            "_pack_years": 50, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 1}
    lr = lambda ppv: (ppv / (1 - ppv)) / (0.0018 / 0.9982)
    worst = 0.0
    for copd in (0, None):
        for k in range(1, 8):
            for yes in itertools.combinations(S7, k):
                ev = {**base, **({"COPD": copd} if copd is not None else {}), **{s: int(s in yes) for s in S7}}
                r = eng.predict_risk(ev)
                p, p6 = r["risk_probability"], r["risk_6y_probability"]
                m = (p / (1 - p)) / (p6 / (1 - p6))
                if k == 1:
                    cap = lr(0.024) if yes[0] == "HEMOPTYSIS" else lr(0.02)
                elif k == 2 and "COUGHING" in yes and "HEMOPTYSIS" not in yes:
                    cap = lr(0.02)
                else:
                    cap = lr(0.10) if "HEMOPTYSIS" not in yes else lr(0.17)
                worst = max(worst, m / cap)
    return worst


def main():
    from model.hybrid_bayesian_network_v3 import load_engine
    engines = {lbl: load_engine(ver, **kw) for lbl, ver, kw in CONFIGS}
    hdr = "| Vaka | " + " | ".join(l for l, *_ in CONFIGS) + " |"
    L = ["# v3 duyarlılık analizi", "",
         "*Otomatik üretildi: `make sensitivity`. Hücreler: tam skor % (6 yıllık faktör katmanı %). "
         f"v3.1 varsayılanı: q={SYMPTOMATIC_FRACTION}, π (başka hastalık önceliği)=0,20, ρ (ortak neden payı)=1,0, "
         "taban PLCOm2012 / Wakelee 2007.*", "",
         hdr, "| --- |" + " ---: |" * len(CONFIGS)]
    print(hdr)
    for cid, name, ev in CASES:
        cells = []
        for lbl, *_ in CONFIGS:
            r = engines[lbl].predict_risk(ev)
            cells.append(f"{r['risk_score']:.2f} ({r['risk_6y_factors']:.2f})")
        L.append(f"| {cid} {name} | " + " | ".join(cells) + " |")
        print(f"{cid} {name[:45]:45s} " + "  ".join(f"{c:>14s}" for c in cells))
    env = [envelope_worst(engines[lbl]) for lbl, *_ in CONFIGS]
    L.append("| **Hamilton zarfı: en kötü çarpan / sınır** (≤1 = içinde) | " + " | ".join(f"**{x:.2f}**" for x in env) + " |")
    print("zarf", ["%.2f" % x for x in env])
    L += ["", "## Okuma", "",
          "- **v3.0 → v3.1:** sigara içmişlerde taban PLCOm2012'ye geçtiği için 6 yıllık katman genel olarak 2–3 kat "
          "(genç/hafif içicilerde 10–35 kat) düşer; ortak neden düğümü sayesinde çoklu belirti kombinasyonları "
          "Hamilton 2005 zarfına girer (son satır).",
          "- **q (bugün semptomatik pay):** 0,25–0,50 aralığında vaka sıralaması değişmez; q büyüdükçe belirtilerin "
          "(hem 'evet' hem 'hayır') etkisi artar.",
          "- **π, ρ (ortak neden):** ρ küçüldükçe belirtiler yeniden bağımsızlaşır ve zarf aşılmaya başlar; π büyüdükçe "
          "belirti başına ortak neden katkısı azalır. Varsayılan (π=0,20, ρ=1,0), NHANES 2007–12'deki öksürük–hırıltı "
          "birlikteliğine (OR 4,1; kansersiz, hiç içmemiş, KOAH'sız) p_o ≤ p_cancer kısıtı altında en yakın değerdir "
          "(model OR 3,4).",
          "- **Normalizasyon:** v3.1'de yalnız asbest ve il PM2.5 çarpanlarını etkiler (aile öyküsü ve KOAH "
          "PLCOm2012'nin içinde)."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n📄 {OUT}")


if __name__ == "__main__":
    main()
