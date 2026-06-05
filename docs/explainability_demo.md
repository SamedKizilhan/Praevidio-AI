# Risk Skoru Açıklanabilirliği — Sunum Notları

**Modül:** `src/model/explainability.py` (`make explain`)  
**Örnek vaka:** Rapor PRA-3C1DEB10 — 55-59 erkek, aktif içici, ailede öykü + mesleki risk + İzmir (orta hava), öksürük + göğüs ağrısı + yorgunluk → **%56.1 (Yüksek)**

## 1. Shapley katkıları (sıra-bağımsız, adil)

Her bulgunun skora katkısı oyun-teorisi Shapley değeriyle hesaplanır: tüm bulgu altkümeleri üzerinden ortalama marjinal katkı. Katkılar **tam toplanır**:

> Taban (yaş/cinsiyet/sigara) **0.08%** + Σ(katkılar) = **56.12%** (kontrol: 56.13%)

| Bulgu | Katkı (yüzde-puan) |
|---|---|
| Öksürük | +18.15 |
| Göğüs ağrısı | +17.09 |
| Yorgunluk | +11.48 |
| Ailede kanser öyküsü | +4.59 |
| Mesleki maruziyet | +3.52 |
| Hava kirliliği | +1.22 |

> Bu, “şu semptom her zaman X puan ekler” demenin doğru yolu **değildir** — Shapley katkısı bu hastanın bağlamına özeldir. Aşağıda neden değiştiği gösteriliyor.

## 2. Build-up (skorun adım adım oluşumu)

| Adım | Risk (%) | Δ (yüzde-puan) |
|---|---|---|
| Referans (demografi, semptomsuz) | 0.08 |  |
| + Ailede kanser öyküsü | 0.14 | +0.06 |
| + Mesleki maruziyet | 0.21 | +0.07 |
| + Hava kirliliği | 0.24 | +0.03 |
| + Öksürük | 3.03 | +2.79 |
| + Göğüs ağrısı | 24.22 | +21.19 |
| + Yorgunluk | 56.12 | +31.89 |

*Not:* tek-tek ekleme sıraya bağlıdır; sıra-bağımsız adil pay için Shapley (§1) kullanılır.

## 3. Bağlam-bağımlılığı — “Hırıltı her seferinde aynı mı katkı yapar?”

**Hayır.** İki neden: (a) olasılık doygunluğu (lojistik eğri doğrusal değil), (b) confounder — hırıltı/öksürük/nefes darlığının olasılık oranı **sigara durumuna** bağlıdır.

### HIRILTI (confounder'lı — sigaraya bağlı)

| Bağlam | Risk (önce→sonra) | Katkı Δpp | Odds çarpanı |
|---|---|---|---|
| C1: 50y kadın, hiç içmemiş (düşük taban) | 0.3% → 1.1% | +0.87 | ×4.40 |
| C2: 55-59 erkek, aktif içici (orta taban) | 3.6% → 13.8% | +10.20 | ×4.29 |
| C3: 70+ erkek, aktif içici (yüksek taban) | 13.6% → 40.3% | +26.71 | ×4.29 |
| C4: 70+ erkek içici + hemoptizi + kilo kaybı (doyma yakın) | 95.7% → 99.0% | +3.29 | ×4.29 |

### HEMOPTİZİ (confounder'sız — kıyas için)

| Bağlam | Risk (önce→sonra) | Katkı Δpp | Odds çarpanı |
|---|---|---|---|
| C1: 50y kadın, hiç içmemiş (düşük taban) | 0.3% → 4.9% | +4.68 | ×20.00 |
| C2: 55-59 erkek, aktif içici (orta taban) | 3.6% → 42.8% | +39.16 | ×20.00 |
| C3: 70+ erkek, aktif içici (yüksek taban) | 13.6% → 75.9% | +62.31 | ×20.00 |

**Sunumda söylenecek cümle:** *Confounder'sız semptomlarda (hemoptizi, göğüs ağrısı...) odds çarpanı bağlamdan bağımsız ~sabittir; bu modelin tutarlılığını gösterir. Ancak yüzde-puan katkı, taban riske göre değişir (doygunluk). Confounder'lı solunum semptomlarında (hırıltı, öksürük, nefes darlığı) odds çarpanı bile sigara durumuna göre değişir — çünkü model, bu semptomların sigaradan da kaynaklanabileceğini biliyor. Bu, basit additif puanlamanın yakalayamadığı klinik etkileşimi yansıtır.*
