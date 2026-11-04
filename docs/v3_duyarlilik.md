# v3 duyarlılık analizi

*Otomatik üretildi: `make sensitivity`. Hücreler: tam skor % (6 yıllık faktör katmanı %). v3.1 varsayılanı: q=0.35, π (başka hastalık önceliği)=0,20, ρ (ortak neden payı)=1,0, taban PLCOm2012 / Wakelee 2007.*

| Vaka | v3.0 | v3.1 (varsayılan) | q=0.25 | q=0.50 | π=0.15 | π=0.30 | ρ=0.70 | ρ=0.85 | normalizasyon kapalı |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K1 72y erkek aktif (50 py), semptom sorulmamış | 8.76 (8.76) | 6.03 (6.03) | 6.03 (6.03) | 6.03 (6.03) | 6.03 (6.03) | 6.03 (6.03) | 6.03 (6.03) | 6.03 (6.03) | 6.03 (6.03) |
| K2 aynı, 7 semptom 'hayır' | 5.62 (8.76) | 3.83 (6.03) | 4.36 (6.03) | 3.04 (6.03) | 3.83 (6.03) | 3.83 (6.03) | 3.83 (6.03) | 3.83 (6.03) | 3.84 (6.03) |
| K3 aynı, sadece hemoptizi 'evet' (6 hayır) | 8.72 (8.76) | 20.61 (6.03) | 16.84 (6.03) | 25.66 (6.03) | 27.79 (6.03) | 12.32 (6.03) | 8.60 (6.03) | 11.17 (6.03) | 20.62 (6.03) |
| K4 aynı, öksürük+nefes+hırıltı, KOAH ? | 17.15 (8.76) | 11.20 (6.03) | 10.15 (6.03) | 12.74 (6.03) | 11.21 (6.03) | 11.54 (6.03) | 11.63 (6.03) | 11.43 (6.03) | 11.22 (6.03) |
| K5 aynı, 7 semptom 'evet' | 99.68 (8.76) | 67.60 (6.03) | 60.18 (6.03) | 74.67 (6.03) | 54.02 (6.03) | 86.08 (6.03) | 84.20 (6.03) | 76.33 (6.03) | 67.63 (6.03) |
| K6 58y kadın eski içici (15 py, 20 yıl önce), semptomsuz | 1.66 (1.66) | 0.37 (0.37) | 0.37 (0.37) | 0.37 (0.37) | 0.37 (0.37) | 0.37 (0.37) | 0.37 (0.37) | 0.37 (0.37) | 0.37 (0.37) |
| K7 62y erkek aktif (30 py), sadece hemoptizi (diğerleri ?) | 28.72 (5.00) | 13.52 (2.00) | 10.52 (2.00) | 17.67 (2.00) | 13.52 (2.00) | 13.52 (2.00) | 13.52 (2.00) | 13.52 (2.00) | 13.52 (2.00) |
| K8 45y erkek aktif (5 py), asbest, 5 belirti, KOAH yok (kullanıcı denemesi) | 85.27 (1.49) | 0.84 (0.14) | 0.64 (0.14) | 1.14 (0.14) | 0.60 (0.14) | 2.08 (0.14) | 1.97 (0.14) | 1.24 (0.14) | 0.84 (0.14) |
| **Hamilton zarfı: en kötü çarpan / sınır** (≤1 = içinde) | **169.94** | **0.35** | **0.25** | **0.50** | **0.47** | **1.40** | **1.06** | **0.58** | **0.35** |

## Okuma

- **v3.0 → v3.1:** sigara içmişlerde taban PLCOm2012'ye geçtiği için 6 yıllık katman genel olarak 2–3 kat (genç/hafif içicilerde 10–35 kat) düşer; ortak neden düğümü sayesinde çoklu belirti kombinasyonları Hamilton 2005 zarfına girer (son satır).
- **q (bugün semptomatik pay):** 0,25–0,50 aralığında vaka sıralaması değişmez; q büyüdükçe belirtilerin (hem 'evet' hem 'hayır') etkisi artar.
- **π, ρ (ortak neden):** ρ küçüldükçe belirtiler yeniden bağımsızlaşır ve zarf aşılmaya başlar; π büyüdükçe belirti başına ortak neden katkısı azalır. Varsayılan (π=0,20, ρ=1,0), NHANES 2007–12'deki öksürük–hırıltı birlikteliğine (OR 4,1; kansersiz, hiç içmemiş, KOAH'sız) p_o ≤ p_cancer kısıtı altında en yakın değerdir (model OR 3,4).
- **Normalizasyon:** v3.1'de yalnız asbest ve il PM2.5 çarpanlarını etkiler (aile öyküsü ve KOAH PLCOm2012'nin içinde).
