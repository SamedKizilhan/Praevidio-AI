# Yeni Risk Faktörü Kalibrasyon Raporu

**Modül:** `src/model/calibrate_risk_factors.py`  
**Kapsam:** FAMILY_HISTORY, ASBESTOS, AIR_POLLUTION odds-ratio kalibrasyonu

## Yöntem
Bu faktörler yalnızca `LUNG_CANCER`'ın ebeveynidir; semptomlara doğrudan ok yoktur, dolayısıyla **explaining-away oluşmaz** (sigaradan farklı). Kalibrasyon (1) OR'ın odds-uzayında sadık uygulandığını (construct validity) ve (2) literatür güven aralığı boyunca davranışın monoton ve sınırlı kaldığını (OAT duyarlılık) doğrular.

## 1. Construct Validity (realize OR ≈ hedef OR)

| Faktör | Durum | Hedef OR | Realize OR | Hata |
|---|---|---|---|---|
| FAMILY_HISTORY | 1 | 1.70 | 1.70 | 0.002 |
| ASBESTOS | 1 | 1.50 | 1.50 | 0.002 |
| AIR_POLLUTION | 1 | 1.15 | 1.15 | 0.001 |
| AIR_POLLUTION | 2 | 1.30 | 1.30 | 0.001 |

Realize edilen OR, hedefe çok yakındır → OR odds-uzayında doğru uygulanmıştır.

## 2. Duyarlılık (OAT) — risk skoru %, low→point→high

**FAMILY_HISTORY=1** — OR ∈ [1.51, 1.7, 1.88]

| Senaryo | low | point | high |
|---|---|---|---|
| Orta yaş, eski içici, semptomsuz | 5.06 | 5.66 | 6.22 |
| Yaşlı, aktif içici, semptomsuz | 18.27 | 20.10 | 21.76 |
| Yaşlı, aktif içici, öksürük | 51.05 | 54.00 | 56.48 |

**ASBESTOS=1** — OR ∈ [1.24, 1.5, 2.04]

| Senaryo | low | point | high |
|---|---|---|---|
| Orta yaş, eski içici, semptomsuz | 4.31 | 5.16 | 6.89 |
| Yaşlı, aktif içici, semptomsuz | 15.85 | 18.54 | 23.60 |
| Yaşlı, aktif içici, öksürük | 46.78 | 51.51 | 59.05 |

**AIR_POLLUTION=1** — OR ∈ [1.08, 1.15, 1.2]

| Senaryo | low | point | high |
|---|---|---|---|
| Orta yaş, eski içici, semptomsuz | 3.38 | 3.59 | 3.74 |
| Yaşlı, aktif içici, semptomsuz | 12.77 | 13.48 | 13.98 |
| Yaşlı, aktif içici, öksürük | 40.59 | 42.10 | 43.14 |

**AIR_POLLUTION=2** — OR ∈ [1.16, 1.3, 1.45]

| Senaryo | low | point | high |
|---|---|---|---|
| Orta yaş, eski içici, semptomsuz | 3.62 | 4.04 | 4.49 |
| Yaşlı, aktif içici, semptomsuz | 13.58 | 14.97 | 16.40 |
| Yaşlı, aktif içici, öksürük | 42.31 | 45.10 | 47.80 |

## 3. Birleşik Etki (hepsi kapalı vs açık)

| Senaryo | Hepsi kapalı | Hepsi açık | Oran |
|---|---|---|---|
| Orta yaş, eski içici, semptomsuz | 2.83% | 8.82% | ×3.12 |
| Yaşlı, aktif içici, semptomsuz | 10.92% | 28.90% | ×2.65 |
| Yaşlı, aktif içici, öksürük | 36.40% | 65.48% | ×1.8 |

## Sonuç (kalibre edilen değerler)

- FAMILY_HISTORY (var): **OR = 1.7** 
- ASBESTOS (riskli meslek): **OR = 1.5** 
- AIR_POLLUTION (orta/yüksek): **OR = 1.15 / 1.3** 

Değerler literatür nokta-tahminleridir; duyarlılık analizi monoton ve makul (doygunluğa gitmeyen) davranışı doğrulamıştır. Explaining-away kalibrasyonu gerekmez (yapısal olarak oluşmaz).
