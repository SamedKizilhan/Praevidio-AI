# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — PLCOm2012 benchmark (Tammemägi et al., NEJM 2013;368:728-36)
============================================================================
Akciğer kanseri taramasında referans kabul edilen 6 yıllık risk modeli; yalnız
HİÇ İÇMEMİŞ OLMAYAN (ever-smoker) kişiler için tanımlıdır. Katsayılar NEJM
makalesinin Tablo 2 / ek materyalinden; ikincil kaynak (OncoToolkit hesaplayıcısı)
ile çapraz kontrol edildi.

    logit = −4.532506
          + 0.0778868·(yaş − 62)
          − 0.0812744·(eğitim − 4)            # 1..6 ölçeği (4 = some college)
          − 0.0274194·(BKİ − 27)
          + 0.3553063·KOAH
          + 0.4589971·kişisel kanser öyküsü
          + 0.587185 ·ailede akciğer kanseri
          + ırk terimi                        # beyaz referans = 0 (Türkiye için varsayılan)
          + 0.2597431·aktif içici
          − 1.822606 ·((adet/gün ÷ 10)^−1 − 0.4021541613)
          + 0.0317321·(içilen yıl − 27)
          − 0.0308572·(bırakalı yıl − 10)     # aktif içici için 0
    risk_6y = 1 / (1 + e^−logit)

Tarama eşiği: 6 yıllık risk ≥ %1,51 (USPSTF-2013 ölçütlerine denk; Tammemägi 2013).

Kullanım amacı: v3'ün risk-faktörü katmanı (risk_6y_factors) için dış benchmark.
NLST tabanı yalnız yaş/cinsiyet/sigara(ikili) bilirken PLCOm2012 doz, süre,
bırakma, KOAH, aile öyküsü ve BKİ'yi kullanır → iki tahmin yan yana raporlanır.
"""
import math

INTERCEPT = -4.532506
B = {
    "age": 0.0778868, "educ": -0.0812744, "bmi": -0.0274194, "copd": 0.3553063,
    "pers_cancer": 0.4589971, "fam_lc": 0.587185, "current": 0.2597431,
    "intensity": -1.822606, "duration": 0.0317321, "quit": -0.0308572,
}
INTENSITY_CONST = 0.4021541613
# Irk/etnik terimler (beyaz = 0). Türkiye kullanıcıları için 0 varsayılır; diğerleri
# yalnız dokümantasyon amaçlı (ikincil kaynaklardan; NEJM ekinden doğrulanmalı).
RACE = {"white": 0.0, "black": 0.3944778, "hispanic": -0.7434744, "asian": -0.466585,
        "native_hawaiian_pacific": 1.027152, "american_indian_alaska": 0.0}
SCREEN_THRESHOLD = 0.0151

# Yaş grubu → temsilci yaş (kesin yaş yoksa). 0=<55 → 50 (model 55-74'te türetildi; dış değer)
AGE_GROUP_MID = {0: 50, 1: 57, 2: 62, 3: 67, 4: 72}


def plcom2012_risk(age, cigs_per_day, years_smoked, years_quit=0, current_smoker=False,
                   education=4, bmi=27.0, copd=0, personal_cancer=0, family_lc=0,
                   race="white") -> float:
    """6 yıllık akciğer kanseri olasılığı (0-1). Yalnız ever-smoker için geçerlidir."""
    cigs = max(float(cigs_per_day), 0.5)         # 0'a bölünmeyi önle (çok hafif içici)
    logit = (INTERCEPT
             + B["age"] * (age - 62)
             + B["educ"] * (education - 4)
             + B["bmi"] * (bmi - 27)
             + B["copd"] * int(copd)
             + B["pers_cancer"] * int(personal_cancer)
             + B["fam_lc"] * int(family_lc)
             + RACE.get(race, 0.0)
             + B["current"] * int(current_smoker)
             + B["intensity"] * ((cigs / 10.0) ** -1 - INTENSITY_CONST)
             + B["duration"] * (years_smoked - 27)
             + B["quit"] * ((0 if current_smoker else years_quit) - 10))
    return 1.0 / (1.0 + math.exp(-logit))


def plcom2012_from_evidence(ev: dict) -> dict:
    """
    Praevidio kanıt sözlüğünden PLCOm2012 hesabı. Dönen sözlük:
      {"applicable": bool, "risk_6y": % | None, "screen_eligible": bool | None,
       "reason": str, "inputs": {...}}
    Eksik girdiler için varsayımlar (inputs içinde işaretlenir):
      • yaş: _age_exact yoksa yaş grubu orta noktası
      • adet/gün: yoksa paket-yıl ve içilen yıldan türetilir; o da yoksa 20 (1 paket)
      • içilen yıl: yoksa paket-yıl / (adet/20); o da yoksa 27 (model merkezi)
      • bırakalı yıl (eski içici): yoksa 10 (model merkezi)
      • eğitim 4, BKİ 27, kişisel kanser 0, ırk beyaz (sorulmuyor → merkez değer)
    """
    smoking = ev.get("SMOKING")
    py = ev.get("_pack_years")
    if smoking is None:
        return {"applicable": False, "risk_6y": None, "screen_eligible": None,
                "reason": "sigara durumu bilinmiyor", "inputs": {}}
    if smoking == 0 and py is not None and py < 1:
        return {"applicable": False, "risk_6y": None, "screen_eligible": None,
                "reason": "hiç içmemiş — PLCOm2012 yalnız ever-smoker için tanımlı (PLCOall2014 gerekir)",
                "inputs": {}}
    assumed = []
    age = ev.get("_age_exact")
    if age is None:
        age = AGE_GROUP_MID.get(ev.get("AGE", 2), 62); assumed.append("yaş≈grup ortası")
    cigs = ev.get("_cigs_per_day")
    yrs = ev.get("_years_smoked")
    if cigs is None and py is not None and yrs:
        cigs = py * 20.0 / yrs
    if cigs is None:
        cigs = 20.0; assumed.append("adet/gün=20")
    if yrs is None and py is not None:
        yrs = py / (cigs / 20.0); assumed.append("içilen yıl≈paket-yıl/(adet/20)")
    if yrs is None:
        yrs = 27.0; assumed.append("içilen yıl=27")
    current = smoking == 1
    yq = ev.get("_years_quit")
    if not current and yq is None:
        yq = 10.0; assumed.append("bırakalı yıl=10")
    risk = plcom2012_risk(age=age, cigs_per_day=cigs, years_smoked=yrs,
                          years_quit=yq or 0, current_smoker=current,
                          copd=ev.get("COPD", 0) or 0, family_lc=ev.get("FAMILY_HISTORY", 0) or 0)
    return {"applicable": True, "risk_6y": round(risk * 100, 2),
            "screen_eligible": risk >= SCREEN_THRESHOLD,
            "reason": "; ".join(assumed) if assumed else "tüm girdiler mevcut",
            "inputs": {"age": age, "cigs_per_day": round(cigs, 1), "years_smoked": round(yrs, 1),
                       "years_quit": None if current else yq, "current": current,
                       "copd": ev.get("COPD"), "family_lc": ev.get("FAMILY_HISTORY")}}


if __name__ == "__main__":
    # NEJM örneği niteliğinde kontrol: 62 yaş, 1 paket/gün, 27 yıl, aktif, diğerleri merkez
    r = plcom2012_risk(62, 20, 27, current_smoker=True)
    print(f"62y, 20/gün, 27 yıl, aktif, diğerleri merkez → {r*100:.2f}%  (beklenen ≈ %1,4-1,5)")
    for ev in [{"AGE": 4, "GENDER": 1, "SMOKING": 1, "_age_exact": 72, "_cigs_per_day": 20, "_years_smoked": 50},
               {"AGE": 1, "GENDER": 0, "SMOKING": 0, "_age_exact": 58, "_pack_years": 15, "_years_quit": 20},
               {"AGE": 2, "GENDER": 1, "SMOKING": 0, "_pack_years": 0}]:
        print(ev, "→", plcom2012_from_evidence(ev))
