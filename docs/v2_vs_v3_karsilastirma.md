# v2 ile v3 risk modeli karşılaştırması

*Otomatik üretildi: `make compare`. v3 parametreleri: q=0.35, OR normalizasyonu=açık, bantlar=v3 ({'low': (0.0, 0.015), 'moderate': (0.015, 0.05), 'high': (0.05, 1.0)}).*

v2 bantları: Düşük <%5, Orta %5–15, Yüksek ≥%15. v3 bantları (6 yıllık ufuk): Düşük <%1,5, Orta %1,5–5 (tarama adayı), Yüksek ≥%5. **6y-faktör** = yalnız risk faktörlerinden hesaplanan tarama katmanı; **alarm** = NICE NG12 acil sevk kuralı (skordan bağımsız).

| ID | Senaryo | v2 % | v2 bant | v3 % | v3 bant | v3 6y-faktör % | alarm |
| --- | --- | ---: | --- | ---: | --- | ---: | --- |
| D1 | Düşük risk — genç, hiç içmemiş, semptomsuz | 0.01 | Düşük Risk | 0.10 | Düşük Risk | 0.15 | — |
| D2 | Orta risk — yaşlı eski içici, hafif semptom | 12.18 | Orta Risk | 5.51 | Yüksek Risk | 3.99 | ACİL |
| D3 | Yüksek risk — örnek rapor vakası (PRA-3C1DEB10) | 56.12 | Yüksek Risk | 25.82 | Yüksek Risk | 6.22 | ACİL |
| D4 | Alarm — hemoptizi (genç ama kan tükürme) | 19.23 | Yüksek Risk | 5.66 | Yüksek Risk | 1.14 | ACİL |
| D5 | Risk faktörleri var, semptom bilgisi YOK (gözlenmemiş) | 28.90 | Yüksek Risk | 24.07 | Yüksek Risk | 24.07 | — |
| P1a | Hava ORTA (İzmir) — diğer her şey sabit | 28.00 | Yüksek Risk | 12.69 | Yüksek Risk | 7.46 | ACİL |
| P1b | Hava YÜKSEK (Iğdır) — diğer her şey sabit | 30.53 | Yüksek Risk | 14.12 | Yüksek Risk | 8.35 | ACİL |
| P2a | Ailede öykü YOK | 3.66 | Düşük Risk | 5.82 | Yüksek Risk | 7.46 | ACİL |
| P2b | Ailede öykü VAR | 6.07 | Orta Risk | 9.49 | Yüksek Risk | 12.04 | ACİL |
| P3a | ESKİ içici + nefes darlığı/göğüs/hırıltı | 61.83 | Yüksek Risk | 13.32 | Yüksek Risk | 3.99 | ACİL |
| P3b | AKTİF içici + nefes darlığı/göğüs/hırıltı | 69.33 | Yüksek Risk | 17.21 | Yüksek Risk | 7.46 | ACİL |
| P4a | Hırıltı — DÜŞÜK taban (50y kadın, hiç içmemiş) | 0.05 | Düşük Risk | 0.11 | Düşük Risk | 0.15 | — |
| P4b | Hırıltı — YÜKSEK taban (70+ erkek, aktif içici) | 1.91 | Düşük Risk | 6.40 | Yüksek Risk | 8.76 | — |
| P5a | Semptomlar CEVAPSIZ (gözlenmemiş) | 28.90 | Yüksek Risk | 24.07 | Yüksek Risk | 24.07 | — |
| P5b | Aynı kişi, tüm semptomlar AÇIKÇA YOK (=0) | 1.12 | Düşük Risk | 16.54 | Yüksek Risk | 24.07 | — |
| S1 | Hiç içmemiş (0 paket-yıl) | 0.56 | Düşük Risk | 0.43 | Düşük Risk | 0.43 | — |
| S2 | Hafif eski içici (10 paket-yıl) | 3.64 | Düşük Risk | 2.79 | Orta Risk | 2.79 | — |
| S3 | Ağır eski içici, yakın bırakmış (30 py, 3 yıl önce) | 6.30 | Orta Risk | 5.00 | Yüksek Risk | 5.00 | — |
| S4 | Ağır eski içici, çok önce bırakmış (30 py, 20 yıl önce) | 3.64 | Düşük Risk | 2.79 | Orta Risk | 2.79 | — |
| S5 | Aktif içici (30 paket-yıl) | 6.30 | Orta Risk | 5.00 | Yüksek Risk | 5.00 | — |
| S6 | Eski içici, paket-yıl bilinmiyor (eski davranış) | 3.64 | Düşük Risk | 2.79 | Orta Risk | 2.79 | — |
| B1a | Bulgu 1 — 70+ erkek aktif içici, semptomlar sorulmamış | 10.92 | Orta Risk | 8.76 | Yüksek Risk | 8.76 | — |
| B1b | Bulgu 1 — aynı kişi, 7 semptoma da 'hayır' | 0.34 | Düşük Risk | 5.64 | Yüksek Risk | 8.76 | — |
| B1c | Bulgu 1 — aynı kişi, sadece hemoptizi 'evet', 6 'hayır' | 7.81 | Orta Risk | 8.65 | Yüksek Risk | 8.76 | ACİL |
| B2a | Bulgu 2 — öksürük+nefes darlığı+hırıltı, KOAH bilinmiyor | 93.64 | Yüksek Risk | 19.20 | Yüksek Risk | 8.76 | ACİL |
| B2b | Bulgu 2 — aynı semptomlar, KOAH tanısı VAR | 93.64 | Yüksek Risk | 15.24 | Yüksek Risk | 11.24 | ACİL |
| B2c | Bulgu 2 — aynı semptomlar, KOAH tanısı YOK | 93.64 | Yüksek Risk | 60.49 | Yüksek Risk | 8.14 | ACİL |
| B2d | Bulgu 2 — 7 semptoma da 'evet' | 99.99 | Yüksek Risk | 99.74 | Yüksek Risk | 8.76 | ACİL |
| B3a | Bulgu 3 — 60-64 erkek aktif içici, yeni faktörler sorulmamış | 6.30 | Orta Risk | 5.00 | Yüksek Risk | 5.00 | — |
| B3b | Bulgu 3 — aynı kişi, yeni faktörlerin hepsi 'yok' (temiz) | 4.94 | Düşük Risk | 3.62 | Orta Risk | 3.62 | — |
| B3c | Bulgu 3 — aynı kişi, ortalama maruziyet (orta hava, diğerleri yok) | 5.64 | Orta Risk | 4.48 | Orta Risk | 4.48 | — |
| B4a | Bulgu 4 — 55-59 kadın eski içici (15 py), semptomsuz: tarama adayı mı? | 3.42 | Düşük Risk | 2.62 | Orta Risk | 2.62 | — |
| B4b | Bulgu 4 — 62 yaş erkek aktif içici, sadece hemoptizi (diğerleri sorulmamış) | 57.33 | Yüksek Risk | 28.72 | Yüksek Risk | 5.00 | ACİL |

## Okuma notları

- **B1b vs B1a:** v2'de 7 'hayır' tabanı 36 kat düşürüp 'Düşük'e çekiyordu; v3'te 6 yıllık taban korunur (latent semptomatik düğüm), yalnızca 'şu an semptomatik' olasılığı düşer.
- **B2a–c:** KOAH düğümü açıklama-giderme (explaining away) davranışını klinik yönde çalıştırır: KOAH 'yok' → semptomlar kansere daha çok yazılır (skor yükselir); KOAH 'var' → semptomlar kısmen KOAH'a yazılır ama KOAH'ın kendi OR'si tabanı yükseltir.
- **B3a–c:** OR normalizasyonu ile 'sorulmamış' ve 'ortalama maruziyet' NLST hücresine düşer; 'temiz' kişi NLST hücresinin altında kalır (v2'de üstündeydi).
- **B4:** v3 bantları PLCOm2012 tarama eşiğine (%1,51/6 yıl) bağlıdır; hemoptizi gibi alarm belirtileri skordan bağımsız 'ACİL' bayrağıyla yüzeye çıkar.
- 7 'evet' hâlâ ~%99 verir: çoklu pozitif kanıtın aşırı güveni bilinen bir naive-Bayes özelliğidir; klinik karar 'Yüksek + ACİL' olduğundan sunumda sorun yaratmaz, ileride LR kısıtlamasıyla yumuşatılabilir.
