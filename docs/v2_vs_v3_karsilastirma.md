# v2 ile v3 risk modeli karşılaştırması

*Otomatik üretildi: `make compare`. v3 parametreleri: q=0.35, OR normalizasyonu=açık, bantlar=v3 ({'low': (0.0, 0.015), 'moderate': (0.015, 0.05), 'high': (0.05, 1.0)}).*

v2 bantları: Düşük <%5, Orta %5–15, Yüksek ≥%15. v3 bantları (6 yıllık ufuk): Düşük <%1,5, Orta %1,5–5 (tarama adayı), Yüksek ≥%5. **6y-faktör** = yalnız risk faktörlerinden hesaplanan tarama katmanı; **alarm** = NICE NG12 acil sevk kuralı (skordan bağımsız).

## Nasıl okunur

Her satır aynı kişinin (aynı cevapların) iki modeldeki sonucudur; senaryo adının altında kişinin profili (yaş, sigara, risk faktörleri, belirtiler) yazar. "Sorulmadı" = model o bilgiyi almadı (cevapsız); "hayır" = kişi açıkça yok dedi. Satır grupları: **D** demo vakaları, **P** kontrollü çiftler (yalnız bir değişken farklı), **S** sigara dozu serisi, **B** metodoloji bulgularını sınayan vakalar.

| Sütun | Anlamı |
| --- | --- |
| v2 % / v2 bant | Bahar modeli; bantlar bir zaman ufkuna bağlı değil (<%5 / %5–15 / ≥%15). |
| v3 % / v3 bant | v3 tam skoru (risk faktörleri + belirtiler) ve bu skorun 6 yıllık banda göre yeri. |
| v3 6y-faktör % | Yalnız yaş, cinsiyet, sigara, aile öyküsü, meslek, hava kirliliği ve KOAH'tan 6 yıllık risk: "taranmalı mı?" sorusunun cevabı. Belirtiler cevaplanmamışsa v3 % ile aynıdır (D5). |
| PLCOm2012 6y % | Dış karşılaştırma (Tammemägi 2013); yalnız sigara içmiş kişiler için. Günlük adet / içilen yıl verilmeyen vakalarda modelin merkez değerleri varsayılır (20/gün, 27 yıl, bırakalı 10 yıl); en anlamlı karşılaştırma S serisindedir. |
| alarm | NICE NG12 kuralı, skordan bağımsız: ≥40 yaş + kan tükürme; veya ≥40 yaş + ≥2 açıklanamayan belirti (öksürük, halsizlik, nefes darlığı, göğüs ağrısı, kilo kaybı); veya ≥40 yaş + sigara öyküsü + ≥1 belirti → kısa sürede hekim değerlendirmesi (göğüs röntgeni). |

**Örnek (D2).** 65–69 yaş erkek, eski içici, öksürük + halsizlik. v2: %12,2 "Orta". v3: risk faktörlerinden 6 yıllık risk %4,0 (tarama adayı aralığı), belirtilerle birlikte %5,6 "Yüksek"; iki açıklanamayan belirti olduğu için ayrıca ACİL.

**v3 bantlarının gerekçesi.** %1,5 alt sınırı PLCOm2012'nin tarama eşiğidir (6 yıllık risk ≥ %1,51 → düşük doz BT önerilir; USPSTF ölçütlerine denk). %5 sınırı, NLST ağır içici popülasyonunun ortalama ~6,5 yıllık tanı oranının (%3,85) belirgin üstüdür ve v2'nin "Orta" alt sınırıyla aynıdır. Sınırlar uzman validasyonu ve karar eğrisi analiziyle kesinleşecektir.

## Sonuçlar

| ID | Senaryo | v2 % | v2 bant | v3 % | v3 bant | v3 6y-faktör % | PLCOm2012 6y % | alarm |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | --- |
| D1 | **Düşük risk — genç, hiç içmemiş, semptomsuz**<br><sub>55 yaş altı kadın · hiç içmemiş · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti yok (7'si de hayır)</sub> | 0.01 | Düşük Risk | 0.01 | Düşük Risk | 0.02 | n/a | — |
| D2 | **Orta risk — yaşlı eski içici, hafif semptom**<br><sub>65–69 yaş erkek · eski içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: öksürük, halsizlik (diğerleri: 5 hayır)</sub> | 12.18 | Orta Risk | 5.63 | Yüksek Risk | 3.99 | 1.31 | ACİL |
| D3 | **Yüksek risk — örnek rapor vakası (PRA-3C1DEB10)**<br><sub>55–59 yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava orta · belirti: öksürük, göğüs ağrısı, halsizlik (diğerleri: 4 hayır)</sub> | 56.12 | Yüksek Risk | 24.26 | Yüksek Risk | 6.22 | 1.90 | ACİL |
| D4 | **Alarm — hemoptizi (genç ama kan tükürme)**<br><sub>55–59 yaş erkek · eski içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: öksürük, kan tükürme (diğerleri: 5 hayır)</sub> | 19.23 | Yüksek Risk | 5.91 | Yüksek Risk | 1.14 | 0.61 | ACİL |
| D5 | **Risk faktörleri var, semptom bilgisi YOK (gözlenmemiş)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava yüksek · belirtiler sorulmadı</sub> | 28.90 | Yüksek Risk | 24.07 | Yüksek Risk | 24.07 | 5.86 | — |
| P1a | **Hava ORTA (İzmir) — diğer her şey sabit**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: öksürük, göğüs ağrısı (diğerleri: 5 hayır)</sub> | 28.00 | Yüksek Risk | 11.97 | Yüksek Risk | 7.46 | 2.29 | ACİL |
| P1b | **Hava YÜKSEK (Iğdır) — diğer her şey sabit**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava yüksek · belirti: öksürük, göğüs ağrısı (diğerleri: 5 hayır)</sub> | 30.53 | Yüksek Risk | 13.33 | Yüksek Risk | 8.35 | 2.29 | ACİL |
| P2a | **Ailede öykü YOK**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: öksürük (diğerleri: 6 hayır)</sub> | 3.66 | Düşük Risk | 5.64 | Yüksek Risk | 7.46 | 2.29 | ACİL |
| P2b | **Ailede öykü VAR**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet yok, hava orta · belirti: öksürük (diğerleri: 6 hayır)</sub> | 6.07 | Orta Risk | 9.22 | Yüksek Risk | 12.04 | 4.05 | ACİL |
| P3a | **ESKİ içici + nefes darlığı/göğüs/hırıltı**<br><sub>65–69 yaş erkek · eski içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: nefes darlığı, göğüs ağrısı, hırıltı (diğerleri: 4 hayır)</sub> | 61.83 | Yüksek Risk | 11.31 | Yüksek Risk | 3.99 | 1.31 | ACİL |
| P3b | **AKTİF içici + nefes darlığı/göğüs/hırıltı**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: nefes darlığı, göğüs ağrısı, hırıltı (diğerleri: 4 hayır)</sub> | 69.33 | Yüksek Risk | 14.92 | Yüksek Risk | 7.46 | 2.29 | ACİL |
| P4a | **Hırıltı — DÜŞÜK taban (50y kadın, hiç içmemiş)**<br><sub>50 yaş kadın · hiç içmemiş · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: hırıltı (diğerleri: 6 hayır)</sub> | 0.01 | Düşük Risk | 0.02 | Düşük Risk | 0.02 | n/a | — |
| P4b | **Hırıltı — YÜKSEK taban (70+ erkek, aktif içici)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: hırıltı (diğerleri: 6 hayır)</sub> | 1.91 | Düşük Risk | 6.04 | Yüksek Risk | 8.76 | 3.35 | — |
| P5a | **Semptomlar CEVAPSIZ (gözlenmemiş)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava yüksek · belirtiler sorulmadı</sub> | 28.90 | Yüksek Risk | 24.07 | Yüksek Risk | 24.07 | 5.86 | — |
| P5b | **Aynı kişi, tüm semptomlar AÇIKÇA YOK (=0)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava yüksek · belirti yok (7'si de hayır)</sub> | 1.12 | Düşük Risk | 16.49 | Yüksek Risk | 24.07 | 5.86 | — |
| S1 | **Hiç içmemiş (0 paket-yıl)**<br><sub>60–64 yaş erkek · hiç içmemiş · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 0.56 | Düşük Risk | 0.43 | Düşük Risk | 0.43 | n/a | — |
| S2 | **Hafif eski içici (10 paket-yıl)**<br><sub>60–64 yaş erkek · eski içici (10 paket-yıl) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.64 | Düşük Risk | 2.79 | Orta Risk | 2.79 | 0.52 | — |
| S3 | **Ağır eski içici, yakın bırakmış (30 py, 3 yıl önce)**<br><sub>60–64 yaş erkek · eski içici (30 paket-yıl, 3 yıl önce bırakmış) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 6.30 | Orta Risk | 5.00 | Yüksek Risk | 5.00 | 1.72 | — |
| S4 | **Ağır eski içici, çok önce bırakmış (30 py, 20 yıl önce)**<br><sub>60–64 yaş erkek · eski içici (30 paket-yıl, 20 yıl önce bırakmış) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.64 | Düşük Risk | 2.79 | Orta Risk | 2.79 | 0.72 | — |
| S5 | **Aktif içici (30 paket-yıl)**<br><sub>60–64 yaş erkek · aktif içici (30 paket-yıl) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 6.30 | Orta Risk | 5.00 | Yüksek Risk | 5.00 | 1.72 | — |
| S6 | **Eski içici, paket-yıl bilinmiyor (eski davranış)**<br><sub>60–64 yaş erkek · eski içici · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.64 | Düşük Risk | 2.79 | Orta Risk | 2.79 | 0.89 | — |
| B1a | **Bulgu 1 — 70+ erkek aktif içici, semptomlar sorulmamış**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirtiler sorulmadı</sub> | 10.92 | Orta Risk | 8.76 | Yüksek Risk | 8.76 | 3.35 | — |
| B1b | **Bulgu 1 — aynı kişi, 7 semptoma da 'hayır'**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti yok (7'si de hayır)</sub> | 0.34 | Düşük Risk | 5.62 | Yüksek Risk | 8.76 | 3.35 | — |
| B1c | **Bulgu 1 — aynı kişi, sadece hemoptizi 'evet', 6 'hayır'**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: kan tükürme (diğerleri: 6 hayır)</sub> | 7.81 | Orta Risk | 8.72 | Yüksek Risk | 8.76 | 3.35 | ACİL |
| B2a | **Bulgu 2 — öksürük+nefes darlığı+hırıltı, KOAH bilinmiyor**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: öksürük, nefes darlığı, hırıltı (diğerleri: 4 sorulmadı)</sub> | 93.64 | Yüksek Risk | 17.15 | Yüksek Risk | 8.76 | 3.35 | ACİL |
| B2b | **Bulgu 2 — aynı semptomlar, KOAH tanısı VAR**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük, KOAH var · belirti: öksürük, nefes darlığı, hırıltı (diğerleri: 4 sorulmadı)</sub> | 93.64 | Yüksek Risk | 14.14 | Yüksek Risk | 11.24 | 4.71 | ACİL |
| B2c | **Bulgu 2 — aynı semptomlar, KOAH tanısı YOK**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük, KOAH yok · belirti: öksürük, nefes darlığı, hırıltı (diğerleri: 4 sorulmadı)</sub> | 93.64 | Yüksek Risk | 43.03 | Yüksek Risk | 8.14 | 3.35 | ACİL |
| B2d | **Bulgu 2 — 7 semptoma da 'evet'**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: öksürük, nefes darlığı, göğüs ağrısı, hırıltı, halsizlik, kan tükürme, kilo kaybı</sub> | 99.99 | Yüksek Risk | 99.68 | Yüksek Risk | 8.76 | 3.35 | ACİL |
| B3a | **Bulgu 3 — 60-64 erkek aktif içici, yeni faktörler sorulmamış**<br><sub>60–64 yaş erkek · aktif içici · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 6.30 | Orta Risk | 5.00 | Yüksek Risk | 5.00 | 1.56 | — |
| B3b | **Bulgu 3 — aynı kişi, yeni faktörlerin hepsi 'yok' (temiz)**<br><sub>60–64 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük, KOAH yok · belirtiler sorulmadı</sub> | 4.94 | Düşük Risk | 3.62 | Orta Risk | 3.62 | 1.56 | — |
| B3c | **Bulgu 3 — aynı kişi, ortalama maruziyet (orta hava, diğerleri yok)**<br><sub>60–64 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirtiler sorulmadı</sub> | 5.64 | Orta Risk | 4.48 | Orta Risk | 4.48 | 1.56 | — |
| B4a | **Bulgu 4 — 55-59 kadın eski içici (15 py), semptomsuz: tarama adayı mı?**<br><sub>55–59 yaş kadın · eski içici (15 paket-yıl) · aile öyküsü var, sorulmadı: mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.42 | Düşük Risk | 2.62 | Orta Risk | 2.62 | 0.74 | — |
| B4b | **Bulgu 4 — 62 yaş erkek aktif içici, sadece hemoptizi (diğerleri sorulmamış)**<br><sub>62 yaş erkek · aktif içici · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirti: kan tükürme (diğerleri: 6 sorulmadı)</sub> | 57.33 | Yüksek Risk | 28.72 | Yüksek Risk | 5.00 | 1.56 | ACİL |

## Okuma notları

- **PLCOm2012 sütunu:** dış benchmark (Tammemägi 2013), yalnız ever-smoker; adet/gün, içilen yıl ve bırakalı yıl verilmeyen senaryolarda model merkez değerleri varsayılır (20/gün, paket-yıl/1, 10 yıl), bu yüzden yalnız S-serisi ve _age_exact içeren vakalarda birebir karşılaştırılabilir. NLST tabanı (tüm NLST ≥30 paket-yıl ağır içici) hafif içicilerde PLCOm2012'den sistematik yüksek çıkar; iki taban raporda yan yana verilir.
- **B1b vs B1a:** v2'de 7 'hayır' tabanı 36 kat düşürüp 'Düşük'e çekiyordu; v3'te 6 yıllık taban korunur (latent semptomatik düğüm), yalnızca 'şu an semptomatik' olasılığı düşer.
- **B2a–c:** KOAH düğümü açıklama-giderme (explaining away) davranışını klinik yönde çalıştırır: KOAH 'yok' → semptomlar kansere daha çok yazılır (skor yükselir); KOAH 'var' → semptomlar kısmen KOAH'a yazılır ama KOAH'ın kendi OR'si tabanı yükseltir.
- **B3a–c:** OR normalizasyonu ile 'sorulmamış' ve 'ortalama maruziyet' NLST hücresine düşer; 'temiz' kişi NLST hücresinin altında kalır (v2'de üstündeydi).
- **B4:** v3 bantları PLCOm2012 tarama eşiğine (%1,51/6 yıl) bağlıdır; hemoptizi gibi alarm belirtileri skordan bağımsız 'ACİL' bayrağıyla yüzeye çıkar.
- 7 'evet' hâlâ ~%99 verir: çoklu pozitif kanıtın aşırı güveni bilinen bir naive-Bayes özelliğidir; klinik karar 'Yüksek + ACİL' olduğundan sunumda sorun yaratmaz, ileride LR kısıtlamasıyla yumuşatılabilir.
