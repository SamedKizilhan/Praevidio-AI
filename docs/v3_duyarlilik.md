# v3 duyarlılık analizi

*Hücreler: tam skor % (6 yıllık faktör katmanı %). Varsayılan q=0.35.*

| Vaka | q=0.25 | q=0.35 (varsayılan) | q=0.50 | q=0.35, normalizasyon kapalı | q=0.35, taban=PLCOm2012 |
| --- | ---: | ---: | ---: | ---: | ---: |
| K1 72y erkek aktif (50 py), semptom sorulmamış | 8.8 (8.8) | 8.8 (8.8) | 8.8 (8.8) | 11.7 (11.7) | 6.7 (6.7) |
| K2 aynı, 7 semptom 'hayır' | 6.4 (8.8) | 5.6 (8.8) | 4.5 (8.8) | 7.7 (11.7) | 4.3 (6.7) |
| K3 aynı, sadece hemoptizi 'evet' (6 hayır) | 8.5 (8.8) | 8.7 (8.8) | 8.8 (8.8) | 11.6 (11.7) | 6.6 (6.7) |
| K4 aynı, öksürük+nefes+hırıltı, KOAH ? | 17.0 (8.8) | 19.2 (8.8) | 22.2 (8.8) | 24.8 (11.7) | 15.1 (6.7) |
| K5 aynı, 7 semptom 'evet' | 99.6 (8.8) | 99.7 (8.8) | 99.8 (8.8) | 99.8 (11.7) | 99.7 (6.7) |
| K6 58y kadın eski içici (15 py, 20 yıl önce), semptomsuz | 1.7 (1.7) | 1.7 (1.7) | 1.7 (1.7) | 2.3 (2.3) | 0.3 (0.3) |
| K7 62y erkek aktif (30 py), sadece hemoptizi (diğerleri ?) | 23.2 (5.0) | 28.7 (5.0) | 35.6 (5.0) | 35.8 (6.8) | 11.8 (1.7) |

## Okuma

- q arttıkça negatif kanıt ('hayır') daha çok düşürür, pozitif kanıt daha çok yükseltir; q=0,25–0,50 aralığında sıralama (K2 < K1 < K3 < K4 < K5) değişmez, yalnız mesafeler değişir.
- Normalizasyon kapalıyken yalnız 'sorulmamış' faktörler skoru ~1,3× şişirir; K1–K5'te faktörler açıkça 0 olduğu için fark küçüktür.
- PLCOm2012 tabanı aynı profilde NLST hücresinin ~1/3'ünü verir: NLST taban oranı (%3,85/≈6,5 yıl) yalnız ≥30 paket-yıl ağır içicilerin gözlenen oranıdır ve tarama ile saptanan kanserleri içerir; PLCOm2012 ise doz/süre/bırakma ile düzeltir. Hangi tabanın kullanılacağı uzman görüşü ve tam NLST verisiyle kararlaştırılacak; iki taban da raporlanır (`nlst_6y_factors`, `benchmark_plcom2012`).
