# Praevidio AI — Test Senaryoları Raporu

Bu rapor `make scenarios` ile otomatik üretilir. Risk eşikleri: **Düşük < %5 · Orta %5–15 · Yüksek > %15**.

## 1. Demo Senaryoları

Gerçekçi bağımsız vakalar; beklenen risk seviyesi doğrulanır (golden test).

| ID | Senaryo | Amaç | Risk | Seviye | Beklenen |
|---|---|---|---|---|---|
| D1 | Düşük risk — genç, hiç içmemiş, semptomsuz | Asemptomatik düşük-risk taban davranışı | %0.0 | Düşük Risk | low |
| D2 | Orta risk — yaşlı eski içici, hafif semptom | Eşik üstü ama yüksek değil | %12.2 | Orta Risk | moderate |
| D3 | Yüksek risk — örnek rapor vakası (PRA-3C1DEB10) | Belgede açıklanan %56.1 vakası | %56.1 | Yüksek Risk | high |
| D4 | Alarm — hemoptizi (genç ama kan tükürme) | Tek güçlü alarm semptomunun (hemoptizi) etkisi | %19.2 | Yüksek Risk | high |
| D5 | Risk faktörleri var, semptom bilgisi YOK (gözlenmemiş) | Semptomlar henüz sorulmamış → semptom öncesi taban risk (prior) | %28.9 | Yüksek Risk | high |

## 2. Kontrollü Çiftler / Gruplar (Açıklanabilirlik)

Her grupta **yalnızca belirtilen faktör** değişir; gerisi sabittir. Böylece o faktörün riske katkısı izole edilir.

### Hava kirliliği etkisi

> Diğer her şey sabitken yalnızca yaşanılan ilin PM2.5 kademesi değişiyor. Orta→Yüksek geçişinde riskin literatür temelli odds-ratio (1.15→1.30) ile arttığını gösterir.

| ID | Senaryo | Risk | Seviye | Not |
|---|---|---|---|---|
| P1a | Hava ORTA (İzmir) — diğer her şey sabit | %28.0 | Yüksek Risk | — |
| P1b | Hava YÜKSEK (Iğdır) — diğer her şey sabit | %30.5 | Yüksek Risk | — |

**Δ (P1b − P1a) = +2.5 yüzde-puan**

### Ailede öykü etkisi

> Birinci derece akrabada akciğer kanseri öyküsünün (OR≈1.70) tek başına riske katkısını izole eder.

| ID | Senaryo | Risk | Seviye | Not |
|---|---|---|---|---|
| P2a | Ailede öykü YOK | %3.7 | Düşük Risk | — |
| P2b | Ailede öykü VAR | %6.1 | Orta Risk | — |

**Δ (P2b − P2a) = +2.4 yüzde-puan**

### Sigara etkisi (solunum semptomlu)

> Aynı solunum semptomlarıyla, aktif içicinin eski içiciden DAHA yüksek risk almasını gösterir. 'Explaining-away' düzeltmesinin kanıtıdır: sigara semptomu açıklayıp kanseri bastırmaz.

| ID | Senaryo | Risk | Seviye | Not |
|---|---|---|---|---|
| P3a | ESKİ içici + nefes darlığı/göğüs/hırıltı | %61.8 | Yüksek Risk | — |
| P3b | AKTİF içici + nefes darlığı/göğüs/hırıltı | %69.3 | Yüksek Risk | — |

**Δ (P3b − P3a) = +7.5 yüzde-puan**

### Bağlam-bağımlılığı (hırıltı)

> Aynı semptom (hırıltı) farklı tabanlarda farklı yüzde-puan katkı yapar. Katkının sabit olmadığını, taban riske (yaş/cinsiyet/sigara) bağlı olduğunu gösterir (doygunluk).

| ID | Senaryo | Risk | Seviye | Not |
|---|---|---|---|---|
| P4a | Hırıltı — DÜŞÜK taban (50y kadın, hiç içmemiş) | %0.1 | Düşük Risk | — |
| P4b | Hırıltı — YÜKSEK taban (70+ erkek, aktif içici) | %1.9 | Düşük Risk | — |

**Δ (P4b − P4a) = +1.9 yüzde-puan**

### Cevapsız vs açıkça YOK (negatif kanıt)

> Aynı kişide semptomların 'cevapsız' (bilinmiyor) olması ile 'açıkça yok' olması arasındaki farkı gösterir. Açık negatif yanıtlar riski düşürür — modelin tek yönlü olmadığını kanıtlar.

| ID | Senaryo | Risk | Seviye | Not |
|---|---|---|---|---|
| P5a | Semptomlar CEVAPSIZ (gözlenmemiş) | %28.9 | Yüksek Risk | — |
| P5b | Aynı kişi, tüm semptomlar AÇIKÇA YOK (=0) | %1.1 | Düşük Risk | — |

**Δ (P5b − P5a) = -27.8 yüzde-puan**

### Sigara dozu (paket-yıl)

> Aynı yaş/cinsiyette, yalnızca sigara dozunu (paket-yıl) ve bırakma süresini değiştirir. İkili aktif/eski sınıflamanın ötesine geçip: hiç içmeyeni düşürdüğümüzü, ağır+yakın eski içiciyi aktif gibi değerlendirdiğimizi gösterir.

| ID | Senaryo | Risk | Seviye | Not |
|---|---|---|---|---|
| S1 | Hiç içmemiş (0 paket-yıl) | %0.6 | Düşük Risk | Sigara öyküsü yok/çok az: taban risk hiç-içmeyen seviyesine düşürüldü. |
| S2 | Hafif eski içici (10 paket-yıl) | %3.6 | Düşük Risk | — |
| S3 | Ağır eski içici, yakın bırakmış (30 py, 3 yıl önce) | %6.3 | Orta Risk | Ağır eski içici (30 paket-yıl, bırakalı ≤15 yıl): aktif içici gibi değerlendirildi. |
| S4 | Ağır eski içici, çok önce bırakmış (30 py, 20 yıl önce) | %3.6 | Düşük Risk | — |
| S5 | Aktif içici (30 paket-yıl) | %6.3 | Orta Risk | — |
| S6 | Eski içici, paket-yıl bilinmiyor (eski davranış) | %3.6 | Düşük Risk | — |

---
*Not: Risk skorları olasılıktır, tanı değildir. Düşük semptom-skoru, tarama uygunluğunu ortadan kaldırmaz (bkz. `screening.py`).*
