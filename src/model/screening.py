"""
Praevidio AI - LDCT Tarama Uygunluğu (semptomdan BAĞIMSIZ)
==========================================================
Neden ayrı bir modül? Çünkü "tarama adayı mıyım?" sorusu, "şu an semptom-temelli
kanser olasılığım ne?" sorusundan FARKLIDIR. Erken akciğer kanseri genellikle
BELİRTİSİZDİR; tarama (düşük doz BT / LDCT) tam da bu yüzden yaş + sigara geçmişi
olan yüksek-riskli kişilere, semptom olmasa bile önerilir.

BBN semptom skoru düşük olsa dahi, kişi yaş/sigara kriterlerini karşılıyorsa
"tarama adayı" olarak işaretlenir. Bu, projenin "ne kadar çok tarama, o kadar
erken teşhis" amacını doğrudan destekler ve göğüs hastalıkları uzmanının
"insanları taramaya yönlendir" tavsiyesiyle uyumludur.

Kriter (USPSTF 2021 / NLST temelli, uyarlanmış):
  - Yaş 50–80
  - ≥ 20 paket-yıl sigara öyküsü
  - Halen içiyor VEYA bırakalı ≤ 15 yıl
Paket-yıl = (günlük adet / 20) × içilen yıl.
"""


def _resolve_age(ev):
    """Kesin yaş varsa onu, yoksa yaş grubundan temsili (alt sınır) yaşı döndür."""
    if ev.get("_age_exact") is not None:
        return int(ev["_age_exact"]), True
    grp = ev.get("AGE")
    # grup → o grubun ALT sınırı (muhafazakâr): 0=<55, 1=55, 2=60, 3=65, 4=70
    grp_min = {0: None, 1: 55, 2: 60, 3: 65, 4: 70}
    return (grp_min.get(grp), False) if grp is not None else (None, False)


def assess_screening_eligibility(ev: dict) -> dict:
    """
    Args: tam kanıt sözlüğü (AGE, SMOKING ve varsa _age_exact, _pack_years, _years_quit).
    Returns: uygunluk durumu + TR/EN mesajları.
        eligible: True / False / None (bilgi eksik → "olası")
    """
    age, age_exact = _resolve_age(ev)
    smoking = ev.get("SMOKING")           # 0=eski/hiç, 1=aktif
    pack_years = ev.get("_pack_years")    # float | None
    years_quit = ev.get("_years_quit")    # int | None

    reasons = []

    # --- Yaş kriteri ---
    if age is None:
        return _result(None, "Yaş bilgisi tarama değerlendirmesi için yetersiz.",
                       "Age information insufficient for screening assessment.")
    age_ok = 50 <= age <= 80
    if not age_ok:
        return _result(False,
                       f"Yaş ({age}) LDCT tarama aralığı (50–80) dışında.",
                       f"Age ({age}) is outside the LDCT screening range (50–80).")

    # --- Sigara durumu ---
    if smoking is None:
        return _result(None, "Sigara durumu bilinmiyor; tarama uygunluğu belirsiz.",
                       "Smoking status unknown; screening eligibility indeterminate.")
    # Hiç içmemiş (paket-yıl 0) → uygun değil
    if pack_years is not None and pack_years == 0:
        return _result(False, "Sigara öyküsü yok; LDCT taraması önerilmez.",
                       "No smoking history; LDCT screening not indicated.")
    # Eski içici + 15 yıldan fazla önce bırakmış → uygun değil
    if smoking == 0 and years_quit is not None and years_quit > 15:
        return _result(False,
                       f"Sigarayı bırakalı {years_quit} yıl (>15) olmuş; tarama aralığı dışında.",
                       f"Quit smoking {years_quit} years ago (>15); outside screening window.")

    # --- Paket-yıl kriteri ---
    if pack_years is None:
        # Yaş uygun + içici/yakın-eski içici ama paket-yıl bilinmiyor → OLASI
        return _result(None,
                       "Yaş ve sigara profiliniz tarama için uygun aralıkta; kesin değerlendirme "
                       "için paket-yıl (günlük adet × yıl) bilgisi gerekir. ≥20 paket-yıl ise adaysınız.",
                       "Your age and smoking profile fall in the screening range; pack-year detail "
                       "is needed to confirm. If ≥20 pack-years, you are a candidate.")
    if pack_years < 20:
        return _result(False,
                       f"Sigara öyküsü ({pack_years:.0f} paket-yıl) 20 paket-yıl eşiğinin altında.",
                       f"Smoking history ({pack_years:.0f} pack-years) is below the 20 pack-year threshold.")

    # --- Tüm kriterler sağlandı ---
    qd = "halen içici" if smoking == 1 else (f"bırakalı {years_quit} yıl" if years_quit is not None else "eski içici")
    return _result(True,
                   f"Yaş {age}, {pack_years:.0f} paket-yıl, {qd}: LDCT taraması için ADAYSINIZ. "
                   f"Belirtiniz olmasa dahi hekiminizle düşük doz akciğer tomografisini görüşün.",
                   f"Age {age}, {pack_years:.0f} pack-years: you are a CANDIDATE for LDCT screening. "
                   f"Even without symptoms, discuss low-dose CT with your physician.")


def _result(eligible, msg_tr, msg_en):
    label = {True: ("Tarama Adayı", "Screening Candidate"),
             False: ("Tarama Aralığı Dışı", "Outside Screening Range"),
             None: ("Olası — Bilgi Eksik", "Possible — More Info Needed")}[eligible]
    return {
        "eligible": eligible,
        "label_tr": label[0], "label_en": label[1],
        "message_tr": msg_tr, "message_en": msg_en,
    }


def parse_pack_years(text: str) -> dict:
    """
    Serbest Türkçe metinden günlük adet, içilen yıl, paket-yıl ve bırakma süresini çıkarır.
    Örn: "günde bir paket, 30 yıldır içiyorum" → 20 adet × 30 yıl = 30 paket-yıl.
    """
    import re
    t = text.lower().replace("̇", "")
    out = {}

    # Hiç içmemiş → paket-yıl 0 (tarama için sigara öyküsü yok)
    if (re.search(r"hiç\s*(?:içme|kullanma|sigara)", t) or "içmedim" in t
            or "içmemiş" in t or "kullanmadım" in t or "sigara içmem" in t):
        out["_pack_years"] = 0
        return out

    # Bırakma süresini önce yakala ve metinden çıkar (içme yılıyla karışmasın)
    mq = re.search(r"(\d+)\s*(?:yıl|sene)\s*önce\s*bırak", t) or re.search(r"bırak\w*\s*(\d+)\s*(?:yıl|sene)", t)
    if mq:
        out["_years_quit"] = int(mq.group(1))
        t = t.replace(mq.group(0), " ")   # "5 yıl önce bıraktım" ifadesini kaldır

    # Günlük adet
    cigs = None
    word_paket = {"yarım": 10, "bir": 20, "iki": 40, "üç": 60, "dört": 80}
    for w, val in word_paket.items():
        if re.search(rf"{w}\s*paket", t):
            cigs = val
            break
    if cigs is None:
        m = re.search(r"(\d+)\s*paket", t)
        if m:
            cigs = int(m.group(1)) * 20
    if cigs is None:
        m = re.search(r"günde\s*(\d+)", t) or re.search(r"(\d+)\s*(?:adet|tane|dal|sigara)", t)
        if m:
            cigs = int(m.group(1))

    # İçilen yıl (bırakma ifadesi çıkarıldıktan sonra)
    years = None
    m = re.search(r"(\d+)\s*(?:yıl|sene|yildir|senedir|yıldır)", t)
    if m:
        years = int(m.group(1))

    if cigs is not None:
        out["_cigs_per_day"] = cigs
    if years is not None:
        out["_years_smoked"] = years
    if cigs is not None and years is not None:
        out["_pack_years"] = round((cigs / 20.0) * years, 1)
    return out
