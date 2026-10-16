# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — v3 duyarlılık analizi
=====================================
q (semptomatik pay), OR normalizasyonu ve taban kaynağı (NLST / PLCOm2012) değiştirildiğinde
kilit vakaların skoru nasıl değişiyor? Sonuç: docs/v3_duyarlilik.md

Çalıştırma: python src/model/sensitivity_v3.py   (veya: make sensitivity)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from model.hybrid_bayesian_network_v3 import (build_hybrid_model_v3, HybridLungCancerEngineV3,
                                              _quiet, SYMPTOMATIC_FRACTION)

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
CONFIGS = [  # (etiket, q, normalize, base)
    ("q=0.25", 0.25, True, "nlst"), ("q=0.35 (varsayılan)", 0.35, True, "nlst"), ("q=0.50", 0.50, True, "nlst"),
    ("q=0.35, normalizasyon kapalı", 0.35, False, "nlst"), ("q=0.35, taban=PLCOm2012", 0.35, True, "plco"),
]


def main():
    engines = {}
    for lbl, q, norm, base in CONFIGS:
        m = build_hybrid_model_v3(verbose=False, q=q, normalize=norm)
        engines[lbl] = _quiet(HybridLungCancerEngineV3, m, "v3", base)
    hdr = "| Vaka | " + " | ".join(l for l, *_ in CONFIGS) + " |"
    L = ["# v3 duyarlılık analizi", "",
         f"*Hücreler: tam skor % (6 yıllık faktör katmanı %). Varsayılan q={SYMPTOMATIC_FRACTION}.*", "",
         hdr, "| --- |" + " ---: |" * len(CONFIGS)]
    print(hdr)
    for cid, name, ev in CASES:
        cells = []
        for lbl, *_ in CONFIGS:
            r = engines[lbl].predict_risk(ev)
            cells.append(f"{r['risk_score']:.1f} ({r['risk_6y_factors']:.1f})")
        L.append(f"| {cid} {name} | " + " | ".join(cells) + " |")
        print(f"{cid} {name[:45]:45s} " + "  ".join(f"{c:>14s}" for c in cells))
    L += ["", "## Okuma", "",
          "- q arttıkça negatif kanıt ('hayır') daha çok düşürür, pozitif kanıt daha çok yükseltir; "
          "q=0,25–0,50 aralığında sıralama (K2 < K1 < K3 < K4 < K5) değişmez, yalnız mesafeler değişir.",
          "- Normalizasyon: K1–K5'te aile öyküsü/asbest/hava açıkça 0 verildiği için fark iki kaynaktan gelir — "
          "normalize modelde 'temiz' kişi NLST hücresinin (≈%10,9) altına iner (%8,8), normalize olmayan modelde "
          "sorulmamış KOAH prior üzerinden ×1,07 şişirir (%11,7). Sorulmamış faktör sayısı arttıkça fark ~1,3×'e çıkar.",
          "- PLCOm2012 tabanı aynı profilde NLST hücresinin ~1/3'ünü verir: NLST taban oranı (%3,85/≈6,5 yıl) "
          "yalnız ≥30 paket-yıl ağır içicilerin gözlenen oranıdır ve tarama ile saptanan kanserleri içerir; "
          "PLCOm2012 ise doz/süre/bırakma ile düzeltir. Hangi tabanın kullanılacağı uzman görüşü ve tam NLST "
          "verisiyle kararlaştırılacak; iki taban da raporlanır (`nlst_6y_factors`, `benchmark_plcom2012`)."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n📄 {OUT}")


if __name__ == "__main__":
    main()
