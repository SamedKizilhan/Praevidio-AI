# Risk modeli v3.1 — düzeltme notu (Kasım 2026)

*Tablo bölümü otomatik üretilir: `make v31-diff`. Testler: `make model-test`.*

## 1. Tetikleyici

4 Kasım 2026'daki uygulama denemesinde (45 yaş altı erkek, günde 10 sigara × 10 yıl, asbest maruziyeti, İzmir,
KOAH yok; öksürük, nefes darlığı, göğüs ağrısı, halsizlik, kilo kaybı) v3.0 şunu verdi:
**6 yıllık risk %1,49 (Düşük), belirtilerle birlikte %85,3 (Yüksek)**, NICE alarmı yok (yaş < 40).
İki sayı da klinik olarak savunulamaz: PLCOm2012 aynı kişi için %0,03–0,10 verir; Hamilton 2005'te birinci
basamakta tek belirti PPV'leri %2'nin, öksürük içeren hiçbir ikili %2'nin altındadır.

## 2. Kök nedenler

| # | Sorun | Neden | Neden önceden yakalanmadı |
| --- | --- | --- | --- |
| 5a | Genç / hafif içicide 6 yıllık risk 2–35 kat yüksek | NLST yalnız 55–74 yaş ve ≥30 paket-yıl kişileri içerir; "55 yaş altı" ve hafif içici hücreleri kohort seviyesini verir | Karşılaştırma setinde genç hafif içici yoktu; NLST/PLCOm2012 farkı yalnız kohort içi profillerde ölçülmüştü (~2–3×) |
| 5b | Hiç içmemişte risk 4–7 kat yüksek | NLST eski-içici hücresi × sabit 0,15 | Hiç içmemiş için dış referans testi yoktu |
| 5c | Çoklu belirtide aşırı güven (5 belirti ×380, 7 belirti ×3236) | Göğüs ağrısı, halsizlik, kilo kaybı, hemoptizi kansersiz kişide birbirinden bağımsızdı; KOAH yalnız 3 solunum belirtisini açıklıyordu (KOAH = 0 iken hiçbirini) | Tabloda görünüyordu (B2d %99,7) ama "karar zaten ACİL" diye kabul edildi; çoklu belirti için klinik hedefe karşı test yoktu |
| 5d | Hemoptizi + 6 "hayır" riski artırmıyordu (×1,0) | Aynı bağımsızlık: 6 "hayır" kanser-semptomatik olasılığını hemoptizinin artırdığı kadar düşürüyordu | NICE alarmı bu vakayı yakaladığı için skor incelenmedi |
| 5e | Öneri metni ve PDF tam skora bağlı | "Yüksek" metni faktörleri "Düşük" kişiye "risk faktörleriniz riskinizi artırıyor" diyordu; PDF v2 metinlerini kullanıyordu | Arayüz metinleri test edilmiyordu |

## 3. Düzeltmeler (her biri ayrı bayrakla; v3.0 `load_engine("v3.0")` ile birebir yeniden üretilir)

**A — Sigara içmişlerde 6 yıllık taban PLCOm2012** (Tammemägi 2013, NEJM 368:728). Yaş, adet/gün, süre ve bırakma
süresini sürekli değişken olarak kullanır. Bilinmeyen aile öyküsü/KOAH prior üzerinden ortalanır. PLCOm2012'de olmayan
asbest ve il PM2.5 için normalize OR çarpanı (OR/E[OR]) uygulanır. Belirti kanıtı BBN'den olasılık oranı olarak taşınır.

**A2 — Hiç içmemişlerde taban Wakelee 2007** (J Clin Oncol 25:472; 6 kohort, 40–79 yaş). Yaşa göre standardize
insidans kadın 14,4–20,8, erkek 4,8–13,7/100.000 kişi-yıl. Orta değerler ~58 yaşa atanır, her 10 yılda ×2,2 artar;
aile öyküsü, asbest, hava ve KOAH için normalize OR'ler uygulanır.

**B — Ortak neden düğümü "başka bir hastalık"** (enfeksiyon, astım, reflü, kaygı, kas-iskelet…) yedi belirtinin hepsine
bağlanır (noisy-OR). Her belirtinin kansersiz taban sıklığı (NHANES/literatür kalibrasyonu) birebir korunur
(`test_marginal_symptom_prevalence_unchanged_without_cancer`); yalnız belirtiler arası korelasyon eklenir.
Kısıt: p_o ≤ p_cancer (ortak neden bir belirtiyi kanserden güçlü üretemez). Bu kısıt olmadan halsizlik ve hırıltı
eklemek riski düşürüyordu. Kalibrasyon: NHANES 2007–12'de kansersiz, 40+, hiç içmemiş ve KOAH/amfizem/kronik bronşit
tanısı olmayan 5.053 kişide OR(kronik öksürük, hırıltı) = **4,1**. v3.0 bu grupta **1,0** (bağımsızlık) varsayıyordu.
Kısıt altında en yakın değer π = 0,20, ρ = 1,0 → **3,4**. Model veriden biraz düşük korelasyon kullanır, yani açıklama
etkisini abartmaz.

**C — Arayüz:** öneri metni 6 yıllık katman + alarma bağlandı. Alarm yokken belirti bildirilmişse "birkaç haftadır
sürüyorsa aile hekiminize görünün" eklenir. PDF iki katmanlı oldu (ana gösterge 6 yıllık risk; belirtili skor ayrı
satır; NICE alarm kutusu). %10 altındaki değerler iki ondalıkla gösterilir ("%1,49 Düşük").

## 4. Testler (`tests/model`, 86 test)

* **Regresyon:** v3.0 ön ayarı 43 profilin dondurulmuş çıktısını birebir üretir (`test_baseline.py`).
* **Hamilton zarfı:** 127 belirti kombinasyonu × 3 taban profil × 3 KOAH durumu. Belirti çarpanı tek belirtide ≤ ×11,3
  (hemoptizi ≤ ×13,6), öksürük içeren ikilide ≤ ×11,3, hemoptizisiz her kombinasyonda ≤ ×61,6, her kombinasyonda
  ≤ ×113,6. v3.0'da 270 ihlal vardı (en kötü 780× sınır); v3.1'de 0.
* **Bilgi korunur:** her belirti riski artırır; hemoptizi en güçlü (≥ ×3), kilo kaybı/göğüs ağrısı ≥ ×2, 7 belirti ≥ ×10.
* **Tutarlılık:** belirti eklemek riski düşürmez (istisna: KOAH bilinmiyorken hırıltı, ≥ ×0,8; v3.0'dan beri var,
  KOAH üzerinden açıklama etkisi). Risk faktörü, paket-yıl ve yaş artışı 6 yıllık riski düşürmez. Hiç içmemiş ≤ hafif
  içici ≤ ağır içici.
* **Dış referans:** sigara içmişlerde 6 yıllık katman PLCOm2012'nin 0,5–2 katı aralığında. Hiç içmemişte Wakelee
  aralığında. NHANES belirti birlikteliği OR 2,5–5,5 aralığında.
* **Kullanıcı vakası:** 30 ve 45 yaşta 6 yıllık < %0,5 ve tam skor < %10; alarm yalnız 45 yaşta.

## 5. Profil bazında değişim (v3.0 → v3.1)

Kimlik önekleri: S = `scenarios.json`, P = karşılaştırma sınama vakaları (Bulgu 1–4), E = uzman vakaları.

| Profil | 6y v3.0 | 6y v3.1 | Tam v3.0 | Tam v3.1 | PLCOm2012 | alarm |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| S:D1 | 0.02 Düşük | **0.04 Düşük** | 0.01 Düşük | **0.03 Düşük** | n/a | — |
| S:D2 | 3.99 Orta | **1.31 Düşük** | 5.63 Yüksek | **2.09 Orta** | 1.31 | ACİL |
| S:D3 | 6.22 Yüksek | **2.90 Orta** | 24.26 Yüksek | **6.25 Yüksek** | 1.9 | ACİL |
| S:D4 | 1.14 Düşük | **0.53 Düşük** | 5.91 Yüksek | **2.73 Orta** | 0.61 | ACİL |
| S:D5 | 24.07 Yüksek | **9.79 Yüksek** | 24.07 Yüksek | **9.79 Yüksek** | 5.86 | — |
| S:P1a | 7.46 Yüksek | **2.36 Orta** | 11.97 Yüksek | **4.70 Orta** | 2.29 | ACİL |
| S:P1b | 8.35 Yüksek | **2.66 Orta** | 13.33 Yüksek | **5.28 Yüksek** | 2.29 | ACİL |
| S:P2a | 7.46 Yüksek | **2.36 Orta** | 5.64 Yüksek | **1.87 Orta** | 2.29 | ACİL |
| S:P2b | 12.04 Yüksek | **4.16 Orta** | 9.22 Yüksek | **3.32 Orta** | 4.05 | ACİL |
| S:P3a | 3.99 Orta | **1.31 Düşük** | 11.31 Yüksek | **3.02 Orta** | 1.31 | ACİL |
| S:P3b | 7.46 Yüksek | **2.36 Orta** | 14.92 Yüksek | **5.17 Yüksek** | 2.29 | ACİL |
| S:P4a | 0.02 Düşük | **0.04 Düşük** | 0.02 Düşük | **0.03 Düşük** | n/a | — |
| S:P4b | 8.76 Yüksek | **3.00 Orta** | 6.04 Yüksek | **2.05 Orta** | 3.35 | — |
| S:P5a | 24.07 Yüksek | **9.79 Yüksek** | 24.07 Yüksek | **9.79 Yüksek** | 5.86 | — |
| S:P5b | 24.07 Yüksek | **9.79 Yüksek** | 16.49 Yüksek | **6.34 Yüksek** | 5.86 | — |
| S:S1 | 0.43 Düşük | **0.08 Düşük** | 0.43 Düşük | **0.08 Düşük** | n/a | — |
| S:S2 | 2.79 Orta | **0.59 Düşük** | 2.79 Orta | **0.59 Düşük** | 0.52 | — |
| S:S3 | 5.00 Yüksek | **1.37 Düşük** | 5.00 Yüksek | **1.37 Düşük** | 1.21 | — |
| S:S4 | 2.79 Orta | **0.82 Düşük** | 2.79 Orta | **0.82 Düşük** | 0.72 | — |
| S:S5 | 5.00 Yüksek | **2.00 Orta** | 5.00 Yüksek | **2.00 Orta** | 1.72 | — |
| S:S6 | 2.79 Orta | **1.01 Düşük** | 2.79 Orta | **1.01 Düşük** | 0.89 | — |
| P:B1a | 8.76 Yüksek | **3.00 Orta** | 8.76 Yüksek | **3.00 Orta** | 3.35 | — |
| P:B1b | 8.76 Yüksek | **3.00 Orta** | 5.62 Yüksek | **1.89 Orta** | 3.35 | — |
| P:B1c | 8.76 Yüksek | **3.00 Orta** | 8.72 Yüksek | **11.13 Yüksek** | 3.35 | ACİL |
| P:B2a | 8.76 Yüksek | **3.00 Orta** | 17.15 Yüksek | **5.74 Yüksek** | 3.35 | ACİL |
| P:B2b | 11.24 Yüksek | **3.92 Orta** | 14.14 Yüksek | **4.99 Orta** | 4.71 | ACİL |
| P:B2c | 8.14 Yüksek | **2.78 Orta** | 43.03 Yüksek | **8.74 Yüksek** | 3.35 | ACİL |
| P:B2d | 8.76 Yüksek | **3.00 Orta** | 99.68 Yüksek | **50.16 Yüksek** | 3.35 | ACİL |
| P:B3a | 5.00 Yüksek | **1.83 Orta** | 5.00 Yüksek | **1.83 Orta** | 1.56 | — |
| P:B3b | 3.62 Orta | **1.29 Düşük** | 3.62 Orta | **1.29 Düşük** | 1.56 | — |
| P:B3c | 4.48 Orta | **1.61 Orta** | 4.48 Orta | **1.61 Orta** | 1.56 | — |
| P:B4a | 2.62 Orta | **0.78 Düşük** | 2.62 Orta | **0.78 Düşük** | 0.74 | — |
| P:B4b | 5.00 Yüksek | **1.83 Orta** | 28.72 Yüksek | **12.45 Yüksek** | 1.56 | ACİL |
| E:E1 | 0.02 Düşük | **0.03 Düşük** | 0.01 Düşük | **0.02 Düşük** | n/a | — |
| E:E2 | 2.54 Orta | **1.78 Orta** | 2.97 Orta | **2.13 Orta** | 1.73 | ACİL |
| E:E3 | 7.46 Yüksek | **4.77 Orta** | 57.17 Yüksek | **22.60 Yüksek** | 4.64 | ACİL |
| E:E4 | 0.17 Düşük | **0.22 Düşük** | 0.15 Düşük | **0.29 Düşük** | 0.22 | ACİL |
| E:E5 | 15.77 Yüksek | **8.84 Yüksek** | 10.43 Yüksek | **5.69 Yüksek** | 8.62 | — |
| E:E6 | 7.36 Yüksek | **2.27 Orta** | 9.03 Yüksek | **3.87 Orta** | 1.35 | ACİL |
| E:E7 | 1.83 Orta | **0.85 Düşük** | 1.36 Düşük | **0.67 Düşük** | 0.82 | ACİL |
| E:E8 | 0.65 Düşük | **0.27 Düşük** | 0.55 Düşük | **0.35 Düşük** | n/a | — |
| E:E9 | 2.54 Orta | **1.03 Düşük** | 1.71 Orta | **0.71 Düşük** | 1.0 | ACİL |
| E:E10 | 8.28 Yüksek | **2.10 Orta** | 7.49 Yüksek | **1.99 Orta** | 2.1 | ACİL |

**Bant geçişleri (6 yıllık katman):** Düşük→Düşük: 7, Orta→Düşük: 9, Orta→Orta: 2, Yüksek→Düşük: 1, Yüksek→Orta: 20, Yüksek→Yüksek: 4

**Bant geçişleri (tam skor):** Düşük→Düşük: 7, Orta→Düşük: 6, Orta→Orta: 2, Yüksek→Düşük: 1, Yüksek→Orta: 14, Yüksek→Yüksek: 13

## 6. Bilinen sınırlılıklar

* **Sigara içenlerde belirti birlikteliği eksik:** modelin OR'si 1,4, NHANES'te 3,7. Sigaraya bağlı öksürük/hırıltı
  katkısı ortak nedene bağlı değil. İleride ortak neden düğümü sigaraya bağlanabilir.
* **Wakelee yaş eğimi:** her 10 yılda ×2,2 varsayımı literatürdeki genel eğime dayanır, yaşa özgü tablodan alınmadı.
* **Hamilton ölçeği:** Hamilton PPV'leri 2 yıllık pencere ve birinci basamağa başvuran ≥40 yaş nüfusundan gelir.
  6 yıllık ufukta bu oranlar üst sınır olarak kullanılır; uzman görüşü ve gerçek veriyle sıkılaştırılmalıdır.
* **Hemoptizi:** bugün Hamilton'daki 70+ yaş hemoptizi değerine (%7,1, sigara içende ~2×) göre makul ama dışarıda
  doğrulanmadı.
* **Tarama ölçütleri ayrışabilir:** ör. S3 (60–64 yaş, 30 paket-yıl, 3 yıl önce bırakmış) USPSTF 2021'e göre tarama
  adayıdır, PLCOm2012 riski ise %1,37 ile %1,51 eşiğinin altındadır. Uygulama ikisini ayrı gösterir: tarama uygunluğu
  kutusu ve 6 yıllık risk. Bu ayrışma literatürde bilinen bir durumdur.
* **Alarmın önceliği:** NICE alarmı skordan bağımsızdır ve klinik karar için önceliklidir; skor farkındalık amaçlıdır.

## 7. Etkiler

* **Uzman formu (`uzman_tahmin_formu.md`) değişmedi;** yalnız model cevap anahtarı (`model_sonuclari.md`) v3.1 ile yeniden
  üretildi. v2 ve v3.0 değerleri bu belgede ve `docs/v2_vs_v3_karsilastirma.md`'de korunur.
* **Taban seçimi:** NLST yerine PLCOm2012 kararı Ekim'de uzman görüşüne bırakılmıştı. Bu kararı dış referans
  testleriyle şimdi verdik. Uzman görüşmesinde yine ele alınabilir (`load_engine("v3.0")`).
* Ara rapor için **5. bulgu**: tespit (kullanıcı denemesi) → kök neden → veriyle kalibre düzeltme → test.
