# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — v2 ile v3 risk modelinin yan yana karşılaştırması
=================================================================
scenarios.json'daki tüm senaryolar + Bölüm-3 bulgularını sınayan "prob" vakalar
iki motorda da çalıştırılır; sonuç docs/v2_vs_v3_karsilastirma.md'ye yazılır.

Çalıştırma:  python tests/test_scenarios/compare_v2_v3.py   (veya: make compare)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from model.hybrid_bayesian_network_v3 import (load_engine, SYMPTOMATIC_FRACTION,
                                              NORMALIZE_ORS, RISK_BANDS, BANDS_CHOICE)

SCENARIOS = ROOT / "tests" / "test_scenarios" / "scenarios.json"
OUT = ROOT / "docs" / "v2_vs_v3_karsilastirma.md"

S7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING",
      "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
_B = {"AGE": 4, "GENDER": 1, "SMOKING": 1, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0}
PROBES = [
    ("B1a", "Bulgu 1 — 70+ erkek aktif içici, semptomlar sorulmamış", _B),
    ("B1b", "Bulgu 1 — aynı kişi, 7 semptoma da 'hayır'", {**_B, **{s: 0 for s in S7}}),
    ("B1c", "Bulgu 1 — aynı kişi, sadece hemoptizi 'evet', 6 'hayır'", {**_B, **{s: 0 for s in S7}, "HEMOPTYSIS": 1}),
    ("B2a", "Bulgu 2 — öksürük+nefes darlığı+hırıltı, KOAH bilinmiyor", {**_B, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("B2b", "Bulgu 2 — aynı semptomlar, KOAH tanısı VAR", {**_B, "COPD": 1, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("B2c", "Bulgu 2 — aynı semptomlar, KOAH tanısı YOK", {**_B, "COPD": 0, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1, "WHEEZING": 1}),
    ("B2d", "Bulgu 2 — 7 semptoma da 'evet'", {**_B, **{s: 1 for s in S7}}),
    ("B3a", "Bulgu 3 — 60-64 erkek aktif içici, yeni faktörler sorulmamış", {"AGE": 2, "GENDER": 1, "SMOKING": 1}),
    ("B3b", "Bulgu 3 — aynı kişi, yeni faktörlerin hepsi 'yok' (temiz)", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0, "COPD": 0}),
    ("B3c", "Bulgu 3 — aynı kişi, ortalama maruziyet (orta hava, diğerleri yok)", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 1}),
    ("B4a", "Bulgu 4 — 55-59 kadın eski içici (15 py), semptomsuz: tarama adayı mı?", {"AGE": 1, "GENDER": 0, "SMOKING": 0, "_pack_years": 15, "FAMILY_HISTORY": 1}),
    ("B4b", "Bulgu 4 — 62 yaş erkek aktif içici, sadece hemoptizi (diğerleri sorulmamış)", {"AGE": 2, "GENDER": 1, "SMOKING": 1, "HEMOPTYSIS": 1, "_age_exact": 62}),
]


AGE_LBL = {0: "55 yaş altı", 1: "55–59 yaş", 2: "60–64 yaş", 3: "65–69 yaş", 4: "70+ yaş"}
SYM_LBL = {"COUGHING": "öksürük", "SHORTNESS_OF_BREATH": "nefes darlığı", "CHEST_PAIN": "göğüs ağrısı",
           "WHEEZING": "hırıltı", "FATIGUE": "halsizlik", "HEMOPTYSIS": "kan tükürme", "WEIGHT_LOSS": "kilo kaybı"}
AIR_LBL = {0: "düşük", 1: "orta", 2: "yüksek"}


def profile(ev: dict) -> str:
    """Kanıt sözlüğünden okunur kişi profili (karşılaştırma tablosunda senaryo adının altına yazılır)."""
    age = f"{ev['_age_exact']} yaş" if ev.get("_age_exact") is not None else AGE_LBL.get(ev.get("AGE"), "yaş ?")
    sex = {0: "kadın", 1: "erkek"}.get(ev.get("GENDER"), "cinsiyet ?")
    py, sm = ev.get("_pack_years"), ev.get("SMOKING")
    if sm == 1:
        smoke = "aktif içici"
    elif sm == 0:
        smoke = "hiç içmemiş" if py == 0 else "eski içici"
    else:
        smoke = "sigara ?"
    det = []
    if ev.get("_cigs_per_day") is not None and ev.get("_years_smoked") is not None:
        det.append(f"{ev['_cigs_per_day']:g} adet/gün × {ev['_years_smoked']:g} yıl")
    elif py:
        det.append(f"{py:g} paket-yıl")
    if ev.get("_years_quit") is not None and sm == 0 and py != 0:
        det.append(f"{ev['_years_quit']:g} yıl önce bırakmış")
    if det:
        smoke += " (" + ", ".join(det) + ")"

    rf, unasked = [], []
    for key, lbl in (("FAMILY_HISTORY", "aile öyküsü"), ("ASBESTOS", "mesleki maruziyet")):
        if key in ev:
            rf.append(f"{lbl} {'var' if ev[key] == 1 else 'yok'}")
        else:
            unasked.append(lbl)
    if "AIR_POLLUTION" in ev:
        rf.append(f"hava {AIR_LBL[ev['AIR_POLLUTION']]}")
    else:
        unasked.append("hava")
    if "COPD" in ev:
        rf.append(f"KOAH {'var' if ev['COPD'] == 1 else 'yok'}")
    if unasked:
        rf.append("sorulmadı: " + ", ".join(unasked))

    yes = [SYM_LBL[k] for k in SYM_LBL if ev.get(k) == 1]
    no = sum(1 for k in SYM_LBL if ev.get(k) == 0)
    miss = sum(1 for k in SYM_LBL if k not in ev)
    if not yes and no == 0:
        sym = "belirtiler sorulmadı"
    elif not yes and miss == 0:
        sym = "belirti yok (7'si de hayır)"
    else:
        rest = []
        if no:
            rest.append(f"{no} hayır")
        if miss:
            rest.append(f"{miss} sorulmadı")
        sym = "belirti: " + (", ".join(yes) if yes else "—") + (f" (diğerleri: {', '.join(rest)})" if rest else "")
    return f"{age} {sex} · {smoke} · {', '.join(rf)} · {sym}"


def fmt(r):
    return f"{r['risk_score']:.2f}", r["risk_level_tr"]


def main():
    e2, e3 = load_engine("v2"), load_engine("v3")
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    rows = []
    for s in data["scenarios"]:
        rows.append((s["id"], s.get("name") or s.get("label", ""), s["evidence"]))
    rows += PROBES

    L = ["# v2 ile v3 risk modeli karşılaştırması", "",
         f"*Otomatik üretildi: `make compare`. v3 parametreleri: q={SYMPTOMATIC_FRACTION}, "
         f"OR normalizasyonu={'açık' if NORMALIZE_ORS else 'kapalı'}, bantlar={BANDS_CHOICE} "
         f"({RISK_BANDS[BANDS_CHOICE]}).*", "",
         "v2 bantları: Düşük <%5, Orta %5–15, Yüksek ≥%15. v3 bantları (6 yıllık ufuk): Düşük <%1,5, "
         "Orta %1,5–5 (tarama adayı), Yüksek ≥%5. **6y-faktör** = yalnız risk faktörlerinden hesaplanan "
         "tarama katmanı; **alarm** = NICE NG12 acil sevk kuralı (skordan bağımsız).", "",
         "## Nasıl okunur", "",
         "Her satır aynı kişinin (aynı cevapların) iki modeldeki sonucudur; senaryo adının altında kişinin "
         "profili (yaş, sigara, risk faktörleri, belirtiler) yazar. \"Sorulmadı\" = model o bilgiyi almadı "
         "(cevapsız); \"hayır\" = kişi açıkça yok dedi. Satır grupları: **D** demo vakaları, "
         "**P** kontrollü çiftler (yalnız bir değişken farklı), **S** sigara dozu serisi, **B** metodoloji "
         "bulgularını sınayan vakalar.", "",
         "| Sütun | Anlamı |", "| --- | --- |",
         "| v2 % / v2 bant | Bahar modeli; bantlar bir zaman ufkuna bağlı değil (<%5 / %5–15 / ≥%15). |",
         "| v3 % / v3 bant | v3 tam skoru (risk faktörleri + belirtiler) ve bu skorun 6 yıllık banda göre yeri. |",
         "| v3 6y-faktör % | Yalnız yaş, cinsiyet, sigara, aile öyküsü, meslek, hava kirliliği ve KOAH'tan 6 yıllık risk: "
         "\"taranmalı mı?\" sorusunun cevabı. Belirtiler cevaplanmamışsa v3 % ile aynıdır (D5). |",
         "| PLCOm2012 6y % | Dış karşılaştırma (Tammemägi 2013); yalnız sigara içmiş kişiler için. Günlük adet / içilen yıl "
         "verilmeyen vakalarda modelin merkez değerleri varsayılır (20/gün, 27 yıl, bırakalı 10 yıl); en anlamlı "
         "karşılaştırma S serisindedir. |",
         "| alarm | NICE NG12 kuralı, skordan bağımsız: ≥40 yaş + kan tükürme; veya ≥40 yaş + ≥2 açıklanamayan belirti "
         "(öksürük, halsizlik, nefes darlığı, göğüs ağrısı, kilo kaybı); veya ≥40 yaş + sigara öyküsü + ≥1 belirti → "
         "kısa sürede hekim değerlendirmesi (göğüs röntgeni). |", "",
         "**Örnek (D2).** 65–69 yaş erkek, eski içici, öksürük + halsizlik. v2: %12,2 \"Orta\". v3: risk faktörlerinden "
         "6 yıllık risk %4,0 (tarama adayı aralığı), belirtilerle birlikte %5,6 \"Yüksek\"; iki açıklanamayan belirti "
         "olduğu için ayrıca ACİL.", "",
         "**v3 bantlarının gerekçesi.** %1,5 alt sınırı PLCOm2012'nin tarama eşiğidir (6 yıllık risk ≥ %1,51 → düşük doz "
         "BT önerilir; USPSTF ölçütlerine denk). %5 sınırı, NLST ağır içici popülasyonunun ortalama ~6,5 yıllık tanı "
         "oranının (%3,85) belirgin üstüdür ve v2'nin \"Orta\" alt sınırıyla aynıdır. Sınırlar uzman validasyonu ve "
         "karar eğrisi analiziyle kesinleşecektir.", "",
         "## Sonuçlar", "",
         "| ID | Senaryo | v2 % | v2 bant | v3 % | v3 bant | v3 6y-faktör % | PLCOm2012 6y % | alarm |",
         "| --- | --- | ---: | --- | ---: | --- | ---: | ---: | --- |"]
    print(f"{'ID':5s} {'v2 %':>7s} {'v2 bant':10s} {'v3 %':>7s} {'v3 bant':10s} {'6y %':>6s} {'PLCO %':>7s} alarm   senaryo")
    for sid, name, ev in rows:
        r2, r3 = e2.predict_risk(ev), e3.predict_risk(ev)
        p2, l2 = fmt(r2); p3, l3 = fmt(r3)
        al = "ACİL" if r3["alarm"]["level"] == "urgent" else "—"
        bm = r3["benchmark_plcom2012"]
        plco = f"{bm['risk_6y']:.2f}" if bm["applicable"] else "n/a"
        L.append(f"| {sid} | **{name}**<br><sub>{profile(ev)}</sub> | {p2} | {l2} | {p3} | {l3} | "
                 f"{r3['risk_6y_factors']:.2f} | {plco} | {al} |")
        print(f"{sid:5s} {p2:>7s} {l2:10s} {p3:>7s} {l3:10s} {r3['risk_6y_factors']:6.2f} {plco:>7s} {al:7s} {name[:60]}")

    L += ["", "## Okuma notları", "",
          "- **PLCOm2012 sütunu:** dış benchmark (Tammemägi 2013), yalnız ever-smoker; adet/gün, içilen yıl ve "
          "bırakalı yıl verilmeyen senaryolarda model merkez değerleri varsayılır (20/gün, paket-yıl/1, 10 yıl), "
          "bu yüzden yalnız S-serisi ve _age_exact içeren vakalarda birebir karşılaştırılabilir. NLST tabanı "
          "(tüm NLST ≥30 paket-yıl ağır içici) hafif içicilerde PLCOm2012'den sistematik yüksek çıkar; "
          "iki taban raporda yan yana verilir.",
          "- **B1b vs B1a:** v2'de 7 'hayır' tabanı 36 kat düşürüp 'Düşük'e çekiyordu; v3'te 6 yıllık taban "
          "korunur (latent semptomatik düğüm), yalnızca 'şu an semptomatik' olasılığı düşer.",
          "- **B2a–c:** KOAH düğümü açıklama-giderme (explaining away) davranışını klinik yönde çalıştırır: "
          "KOAH 'yok' → semptomlar kansere daha çok yazılır (skor yükselir); KOAH 'var' → semptomlar kısmen "
          "KOAH'a yazılır ama KOAH'ın kendi OR'si tabanı yükseltir.",
          "- **B3a–c:** OR normalizasyonu ile 'sorulmamış' ve 'ortalama maruziyet' NLST hücresine düşer; "
          "'temiz' kişi NLST hücresinin altında kalır (v2'de üstündeydi).",
          "- **B4:** v3 bantları PLCOm2012 tarama eşiğine (%1,51/6 yıl) bağlıdır; hemoptizi gibi alarm "
          "belirtileri skordan bağımsız 'ACİL' bayrağıyla yüzeye çıkar.",
          "- 7 'evet' hâlâ ~%99 verir: çoklu pozitif kanıtın aşırı güveni bilinen bir naive-Bayes özelliğidir; "
          "klinik karar 'Yüksek + ACİL' olduğundan sunumda sorun yaratmaz, ileride LR kısıtlamasıyla yumuşatılabilir."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n📄 Rapor: {OUT}")


if __name__ == "__main__":
    main()
