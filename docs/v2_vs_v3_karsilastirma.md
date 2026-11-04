# v2 ile v3 risk modeli karşılaştırması

*Otomatik üretildi: `make compare`. v3 parametreleri: q=0.35, OR normalizasyonu=açık, bantlar=v3 ({'low': (0.0, 0.015), 'moderate': (0.015, 0.05), 'high': (0.05, 1.0)}); v3.0 = {'base_risk': 'nlst'}, v3.1 = {'base_risk': 'plco', 'other_cause': True, 'other_prior': 0.2, 'other_share': 1.0}.*

**v3.1 (Kasım 2026):** sigara içmişlerde 6 yıllık taban PLCOm2012, hiç içmemişlerde Wakelee 2007; yedi belirtiye ortak neden "başka bir hastalık" düğümü (NHANES belirti birlikteliğine kalibre). Gerekçe ve satır satır değişim: `docs/v3_1_duzeltme.md`. Aşağıdaki **v3 %/bant/6y** sütunları v3.1'dir; **v3.0 %** ve **v3.0 6y** karşılaştırma için korunmuştur.

v2 bantları: Düşük <%5, Orta %5–15, Yüksek ≥%15. v3 bantları (6 yıllık ufuk): Düşük <%1,5, Orta %1,5–5 (tarama adayı), Yüksek ≥%5. **6y-faktör** = yalnız risk faktörlerinden hesaplanan tarama katmanı; **alarm** = NICE NG12 acil sevk kuralı (skordan bağımsız).

## Nasıl okunur

Her satır aynı kişinin (aynı cevapların) iki modeldeki sonucudur; senaryo adının altında kişinin profili (yaş, sigara, risk faktörleri, belirtiler) yazar. "Sorulmadı" = model o bilgiyi almadı (cevapsız); "hayır" = kişi açıkça yok dedi. Satır grupları: **D** demo vakaları, **P** kontrollü çiftler (yalnız bir değişken farklı), **S** sigara dozu serisi, **B** metodoloji bulgularını sınayan vakalar.

| Sütun | Anlamı |
| --- | --- |
| v2 % / v2 bant | Bahar modeli; bantlar bir zaman ufkuna bağlı değil (<%5 / %5–15 / ≥%15). |
| v3.0 % / v3.0 6y | Ekim 2026 sürümü (NLST tabanı, ortak neden yok) — tam skor ve 6 yıllık katman. |
| v3 % | v3.1 tam skoru (risk faktörleri + belirtiler; karma ufuk, **bantlanmaz** — ek bilgi). |
| v3 belirti katmanı % | Bugünkü belirtilerin akciğer kanserine bağlı olma olasılığı; ≥ %3 (NICE NG12 PPV eşiği) → kısa sürede hekim (⚠). Belirti bildirilmemişse —. |
| v3 6y-faktör % | Yalnız yaş, cinsiyet, sigara, aile öyküsü, meslek, hava kirliliği ve KOAH'tan 6 yıllık risk: "taranmalı mı?" sorusunun cevabı. Belirtiler cevaplanmamışsa v3 % ile aynıdır (D5). |
| PLCOm2012 6y % | Dış karşılaştırma (Tammemägi 2013); yalnız sigara içmiş kişiler için. Günlük adet / içilen yıl verilmeyen vakalarda modelin merkez değerleri varsayılır (20/gün, 27 yıl, bırakalı 10 yıl); en anlamlı karşılaştırma S serisindedir. |
| alarm | NICE NG12 kuralı, skordan bağımsız: ≥40 yaş + kan tükürme; veya ≥40 yaş + ≥2 açıklanamayan belirti (öksürük, halsizlik, nefes darlığı, göğüs ağrısı, kilo kaybı); veya ≥40 yaş + sigara öyküsü + ≥1 belirti → kısa sürede hekim değerlendirmesi (göğüs röntgeni). |

**Örnek (D2).** 65–69 yaş erkek, eski içici, öksürük + halsizlik. v2: %12,2 "Orta". v3.0: 6 yıllık %4,0, tam %5,6. v3.1: risk faktörlerinden 6 yıllık risk %1,3 (Düşük Risk), belirtilerle birlikte %2,1 (Orta Risk); iki açıklanamayan belirti olduğu için ayrıca ACİL.

**v3 bantlarının gerekçesi.** %1,5 alt sınırı PLCOm2012'nin tarama eşiğidir (6 yıllık risk ≥ %1,51 → düşük doz BT önerilir; USPSTF ölçütlerine denk). %5 sınırı, NLST ağır içici popülasyonunun ortalama ~6,5 yıllık tanı oranının (%3,85) belirgin üstüdür ve v2'nin "Orta" alt sınırıyla aynıdır. Sınırlar uzman validasyonu ve karar eğrisi analiziyle kesinleşecektir.

## Sonuçlar

| ID | Senaryo | v2 % | v2 bant | v3.0 % | v3.0 6y | v3 % | v3 belirti katmanı % | v3 6y-faktör % | PLCOm2012 6y % | alarm |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| D1 | **Düşük risk — genç, hiç içmemiş, semptomsuz**<br><sub>55 yaş altı kadın · hiç içmemiş · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti yok (7'si de hayır)</sub> | 0.01 | Düşük Risk | 0.01 | 0.02 | 0.03 | — | 0.04 | n/a | — |
| D2 | **Orta risk — yaşlı eski içici, hafif semptom**<br><sub>65–69 yaş erkek · eski içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: öksürük, halsizlik (diğerleri: 5 hayır)</sub> | 12.18 | Orta Risk | 5.63 | 3.99 | 2.09 | 1.23 | 1.31 | 1.31 | ACİL |
| D3 | **Yüksek risk — örnek rapor vakası (PRA-3C1DEB10)**<br><sub>55–59 yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava orta · belirti: öksürük, göğüs ağrısı, halsizlik (diğerleri: 4 hayır)</sub> | 56.12 | Yüksek Risk | 24.26 | 6.22 | 6.25 | 4.52 ⚠ | 2.90 | 1.90 | ACİL |
| D4 | **Alarm — hemoptizi (genç ama kan tükürme)**<br><sub>55–59 yaş erkek · eski içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: öksürük, kan tükürme (diğerleri: 5 hayır)</sub> | 19.23 | Yüksek Risk | 5.91 | 1.14 | 2.73 | 2.40 | 0.53 | 0.61 | ACİL |
| D5 | **Risk faktörleri var, semptom bilgisi YOK (gözlenmemiş)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava yüksek · belirtiler sorulmadı</sub> | 28.90 | Yüksek Risk | 24.07 | 24.07 | 9.79 | — | 9.79 | 5.86 | — |
| P1a | **Hava ORTA (İzmir) — diğer her şey sabit**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: öksürük, göğüs ağrısı (diğerleri: 5 hayır)</sub> | 28.00 | Yüksek Risk | 11.97 | 7.46 | 4.70 | 3.27 ⚠ | 2.36 | 2.29 | ACİL |
| P1b | **Hava YÜKSEK (Iğdır) — diğer her şey sabit**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava yüksek · belirti: öksürük, göğüs ağrısı (diğerleri: 5 hayır)</sub> | 30.53 | Yüksek Risk | 13.33 | 8.35 | 5.28 | 3.68 ⚠ | 2.66 | 2.29 | ACİL |
| P2a | **Ailede öykü YOK**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: öksürük (diğerleri: 6 hayır)</sub> | 3.66 | Düşük Risk | 5.64 | 7.46 | 1.87 | 0.33 | 2.36 | 2.29 | ACİL |
| P2b | **Ailede öykü VAR**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet yok, hava orta · belirti: öksürük (diğerleri: 6 hayır)</sub> | 6.07 | Orta Risk | 9.22 | 12.04 | 3.32 | 0.58 | 4.16 | 4.05 | ACİL |
| P3a | **ESKİ içici + nefes darlığı/göğüs/hırıltı**<br><sub>65–69 yaş erkek · eski içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: nefes darlığı, göğüs ağrısı, hırıltı (diğerleri: 4 hayır)</sub> | 61.83 | Yüksek Risk | 11.31 | 3.99 | 3.02 | 2.15 | 1.31 | 1.31 | ACİL |
| P3b | **AKTİF içici + nefes darlığı/göğüs/hırıltı**<br><sub>65–69 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirti: nefes darlığı, göğüs ağrısı, hırıltı (diğerleri: 4 hayır)</sub> | 69.33 | Yüksek Risk | 14.92 | 7.46 | 5.17 | 3.63 ⚠ | 2.36 | 2.29 | ACİL |
| P4a | **Hırıltı — DÜŞÜK taban (50y kadın, hiç içmemiş)**<br><sub>50 yaş kadın · hiç içmemiş · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: hırıltı (diğerleri: 6 hayır)</sub> | 0.01 | Düşük Risk | 0.02 | 0.02 | 0.03 | 0.00 | 0.04 | n/a | — |
| P4b | **Hırıltı — YÜKSEK taban (70+ erkek, aktif içici)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: hırıltı (diğerleri: 6 hayır)</sub> | 1.91 | Düşük Risk | 6.04 | 8.76 | 2.05 | 0.10 | 3.00 | 3.35 | — |
| P5a | **Semptomlar CEVAPSIZ (gözlenmemiş)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava yüksek · belirtiler sorulmadı</sub> | 28.90 | Yüksek Risk | 24.07 | 24.07 | 9.79 | — | 9.79 | 5.86 | — |
| P5b | **Aynı kişi, tüm semptomlar AÇIKÇA YOK (=0)**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü var, mesleki maruziyet var, hava yüksek · belirti yok (7'si de hayır)</sub> | 1.12 | Düşük Risk | 16.49 | 24.07 | 6.34 | — | 9.79 | 5.86 | — |
| S1 | **Hiç içmemiş (0 paket-yıl)**<br><sub>60–64 yaş erkek · hiç içmemiş · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 0.56 | Düşük Risk | 0.43 | 0.43 | 0.08 | — | 0.08 | n/a | — |
| S2 | **Hafif eski içici (10 paket-yıl)**<br><sub>60–64 yaş erkek · eski içici (10 paket-yıl) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.64 | Düşük Risk | 2.79 | 2.79 | 0.59 | — | 0.59 | 0.52 | — |
| S3 | **Ağır eski içici, yakın bırakmış (30 py, 3 yıl önce)**<br><sub>60–64 yaş erkek · eski içici (30 paket-yıl, 3 yıl önce bırakmış) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 6.30 | Orta Risk | 5.00 | 5.00 | 1.37 | — | 1.37 | 1.21 | — |
| S4 | **Ağır eski içici, çok önce bırakmış (30 py, 20 yıl önce)**<br><sub>60–64 yaş erkek · eski içici (30 paket-yıl, 20 yıl önce bırakmış) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.64 | Düşük Risk | 2.79 | 2.79 | 0.82 | — | 0.82 | 0.72 | — |
| S5 | **Aktif içici (30 paket-yıl)**<br><sub>60–64 yaş erkek · aktif içici (30 paket-yıl) · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 6.30 | Orta Risk | 5.00 | 5.00 | 2.00 | — | 2.00 | 1.72 | — |
| S6 | **Eski içici, paket-yıl bilinmiyor (eski davranış)**<br><sub>60–64 yaş erkek · eski içici · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.64 | Düşük Risk | 2.79 | 2.79 | 1.01 | — | 1.01 | 0.89 | — |
| B1a | **Bulgu 1 — 70+ erkek aktif içici, semptomlar sorulmamış**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirtiler sorulmadı</sub> | 10.92 | Orta Risk | 8.76 | 8.76 | 3.00 | — | 3.00 | 3.35 | — |
| B1b | **Bulgu 1 — aynı kişi, 7 semptoma da 'hayır'**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti yok (7'si de hayır)</sub> | 0.34 | Düşük Risk | 5.62 | 8.76 | 1.89 | — | 3.00 | 3.35 | — |
| B1c | **Bulgu 1 — aynı kişi, sadece hemoptizi 'evet', 6 'hayır'**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: kan tükürme (diğerleri: 6 hayır)</sub> | 7.81 | Orta Risk | 8.72 | 8.76 | 11.13 | 9.46 ⚠ | 3.00 | 3.35 | ACİL |
| B2a | **Bulgu 2 — öksürük+nefes darlığı+hırıltı, KOAH bilinmiyor**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: öksürük, nefes darlığı, hırıltı (diğerleri: 4 sorulmadı)</sub> | 93.64 | Yüksek Risk | 17.15 | 8.76 | 5.74 | 3.37 ⚠ | 3.00 | 3.35 | ACİL |
| B2b | **Bulgu 2 — aynı semptomlar, KOAH tanısı VAR**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük, KOAH var · belirti: öksürük, nefes darlığı, hırıltı (diğerleri: 4 sorulmadı)</sub> | 93.64 | Yüksek Risk | 14.14 | 11.24 | 4.99 | 2.47 | 3.92 | 4.71 | ACİL |
| B2c | **Bulgu 2 — aynı semptomlar, KOAH tanısı YOK**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük, KOAH yok · belirti: öksürük, nefes darlığı, hırıltı (diğerleri: 4 sorulmadı)</sub> | 93.64 | Yüksek Risk | 43.03 | 8.14 | 8.74 | 7.04 ⚠ | 2.78 | 3.35 | ACİL |
| B2d | **Bulgu 2 — 7 semptoma da 'evet'**<br><sub>70+ yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük · belirti: öksürük, nefes darlığı, göğüs ağrısı, hırıltı, halsizlik, kan tükürme, kilo kaybı</sub> | 99.99 | Yüksek Risk | 99.68 | 8.76 | 50.16 | 49.00 ⚠ | 3.00 | 3.35 | ACİL |
| B3a | **Bulgu 3 — 60-64 erkek aktif içici, yeni faktörler sorulmamış**<br><sub>60–64 yaş erkek · aktif içici · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 6.30 | Orta Risk | 5.00 | 5.00 | 1.83 | — | 1.83 | 1.56 | — |
| B3b | **Bulgu 3 — aynı kişi, yeni faktörlerin hepsi 'yok' (temiz)**<br><sub>60–64 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava düşük, KOAH yok · belirtiler sorulmadı</sub> | 4.94 | Düşük Risk | 3.62 | 3.62 | 1.29 | — | 1.29 | 1.56 | — |
| B3c | **Bulgu 3 — aynı kişi, ortalama maruziyet (orta hava, diğerleri yok)**<br><sub>60–64 yaş erkek · aktif içici · aile öyküsü yok, mesleki maruziyet yok, hava orta · belirtiler sorulmadı</sub> | 5.64 | Orta Risk | 4.48 | 4.48 | 1.61 | — | 1.61 | 1.56 | — |
| B4a | **Bulgu 4 — 55-59 kadın eski içici (15 py), semptomsuz: tarama adayı mı?**<br><sub>55–59 yaş kadın · eski içici (15 paket-yıl) · aile öyküsü var, sorulmadı: mesleki maruziyet, hava · belirtiler sorulmadı</sub> | 3.42 | Düşük Risk | 2.62 | 2.62 | 0.78 | — | 0.78 | 0.74 | — |
| B4b | **Bulgu 4 — 62 yaş erkek aktif içici, sadece hemoptizi (diğerleri sorulmamış)**<br><sub>62 yaş erkek · aktif içici · sorulmadı: aile öyküsü, mesleki maruziyet, hava · belirti: kan tükürme (diğerleri: 6 sorulmadı)</sub> | 57.33 | Yüksek Risk | 28.72 | 5.00 | 12.45 | 11.39 ⚠ | 1.83 | 1.56 | ACİL |

## Okuma notları

- **PLCOm2012 sütunu:** saf PLCOm2012 (bilinmeyen aile öyküsü/KOAH = 0, asbest/hava yok). v3.1'in 6 yıllık katmanı sigara içmişlerde bunun üzerine kurulur; farklar bilinmeyen aile öyküsü/KOAH'ın prior ortalaması ve asbest/il PM2.5 çarpanlarından gelir. v3.0'ın NLST tabanı (tüm NLST ≥30 paket-yıl, 55–74 yaş) genç ve hafif içicilerde 2–35 kat yüksekti (Kasım 2026 düzeltmesi).
- **B1b vs B1a:** v2'de 7 'hayır' tabanı 36 kat düşürüp 'Düşük'e çekiyordu; v3'te 6 yıllık taban korunur (latent semptomatik düğüm), yalnızca 'şu an semptomatik' olasılığı düşer.
- **B2a–c:** KOAH düğümü açıklama-giderme (explaining away) davranışını klinik yönde çalıştırır: KOAH 'yok' → semptomlar kansere daha çok yazılır (skor yükselir); KOAH 'var' → semptomlar kısmen KOAH'a yazılır ama KOAH'ın kendi OR'si tabanı yükseltir.
- **B3a–c:** OR normalizasyonu ile 'sorulmamış' ve 'ortalama maruziyet' NLST hücresine düşer; 'temiz' kişi NLST hücresinin altında kalır (v2'de üstündeydi).
- **B4:** v3 bantları PLCOm2012 tarama eşiğine (%1,51/6 yıl) bağlıdır; hemoptizi gibi alarm belirtileri skordan bağımsız 'ACİL' bayrağıyla yüzeye çıkar.
- **B2d (7 'evet'):** v3.0'da %99,7 idi. Bu daha önce "klinik karar zaten ACİL" diye kabul edilmişti; 40 yaş altında alarm çıkmadığında tek başına kalan abartılı skor (kullanıcı denemesi: %85) bunun yanlış olduğunu gösterdi. v3.1'de belirtiler ortak neden ("başka bir hastalık") üzerinden birbirini kısmen açıklar; her kombinasyonun belirti çarpanı Hamilton 2005 zarfı içinde kalır (`tests/model/test_plausibility.py`).
