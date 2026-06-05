# Praevidio AI — Olası Sunum / Savunma Soruları ve Cevapları

Projeye her yönüyle hakim olmak için hazırlanmış soru-cevap seti. Sayılar
modelden doğrulanmıştır (`make scenarios`, `make eval`, `make explain`).

---

## A. Amaç ve Kapsam

**S: Bu proje tam olarak ne yapıyor? Tanı mı koyuyor?**
Hayır, tanı koymuyor. Sesli/etkileşimli olarak kullanıcıdan yaş, cinsiyet, sigara
ve semptom bilgisi toplayıp **kalibre bir akciğer kanseri risk skoru** (olasılık)
üretiyor; amaç farkındalık yaratmak ve uygun kişileri taramaya (LDCT) yönlendirmek.
"Şu kişi kanser/değil" demiyoruz; "şu olasılıkla risk altında" diyoruz.

**S: Neden akciğer kanseri?**
Türkiye'de erkeklerde en sık ve en ölümcül kanser (ASR ~68/100.000), vakaların
yarısından fazlası geç evrede (Evre 4) yakalanıyor. Erken teşhiste sağkalım %90'ı
aşıyor. Çekirdek semptomlar (öksürük, nefes darlığı) sesle ifadeye çok uygun ve
düşük sağlık okuryazarlığı olan kesime sesli arayüz erişim sağlıyor.

---

## B. Veri

**S: Hangi verileri kullandınız?**
İki kaynak: (1) **NLST** (53.452 gerçek katılımcı) — risk faktörü temelini
(yaş/cinsiyet/sigara → kanser) buradan öğrendik. (2) Semptom ilişkileri için
**peer-review literatür** (Hamilton 2005, Beckles 2003, Kvale 2006, Hopwood 2000).
Başlangıçtaki Kaggle veri seti sentetikti; onu yapay olduğu için birincil modelden
çıkardık.

**S: NLST verisinin sınırı ne?**
NLST yalnızca **yüksek-riskli, 55-74 yaş, ≥30 paket-yıl** kişileri içeriyor.
Yani: (a) hiç-içmeyen yok, (b) <55 yaş yok, (c) hafif içici yok. Bu yüzden bu
gruplar için epidemiyolojik tahminler (ACS) ve paket-yıl temelli düzeltmeler
ekledik. Bunu açıkça raporluyoruz — modelin nerede veri-temelli, nerede
literatür-temelli olduğunu gizlemiyoruz.

---

## C. Model (BBN)

**S: Neden Bayesçi ağ, neden derin öğrenme değil?**
Üç sebep: (1) **Açıklanabilirlik** — her ok ve olasılık klinik olarak gerekçeli;
kara kutu değil. (2) **Belirsizlik** — Bayes eksik/kısmi kanıtla doğal çalışır
(kullanıcı her soruyu yanıtlamayabilir). (3) **Veri verimliliği** — küçük/
literatür-temelli bilgiyle çalışabilir; derin öğrenme için büyük etiketli hasta
verisi yok. Tarama-farkındalık bağlamında güvenilirlik ve şeffaflık önceliğimiz.

**S: Ağ yapısı neden "kanser → semptom" yönünde?**
Gerçekte hastalık semptomu üretir, semptom hastalığı değil. Bu "üretici
(generative)" yön tıbbi BBN standardıdır ve CPT'leri "kanser varsa öksürük
olasılığı" gibi klinik olarak okunabilir kılar. Tanıda Bayes ile tersine yürürüz.

**S: %56.1 gibi bir skor nasıl üretiliyor?**
Odds zinciri: NLST tabanı (örn. 55-59E içici %3.60) → yeni faktör OR çarpanları
(aile ×1.7, asbest ×1.5, hava ×1.15 → %7.81) → her semptomun olasılık oranı
(öksürük ×4.67, göğüs ağrısı ×7.0... yok semptomlar <1 ile düşürür) → %56.1.
Detay: `docs/risk_skoru_nasil_hesaplanir.md`.

**S: Soru sırası sonucu değiştirir mi?**
Hayır. Çarpma sıradan bağımsız (a×b×c = c×b×a); nihai skor ve Shapley katkıları
sıra-bağımsız. Yalnızca waterfall grafiğinin ara adımları sıraya bağlıdır
(bu sadece görsel bir gösterimdir).

---

## D. Yeni Risk Faktörleri ve Kalibrasyon

**S: Aile öyküsü, asbest, hava kirliliğini nasıl eklediniz?**
Hepsi `LUNG_CANCER`'ın ebeveyni (sigara gibi). NLST'de bu veriler olmadığından
veriden öğrenemedik; literatür OR'larını (aile RR≈1.5-1.9→1.70; asbest 1.24-2.04
→1.50; hava 1.16/10µg → kademe 1.15/1.30) **odds çarpımıyla** NLST tabanına
uyguladık. Bu, projenin "NLST tabanı + literatür düzeltmesi" felsefesiyle tutarlı.

**S: OR değerlerini nasıl doğruladınız?**
İki yönlü: (1) **Construct validity** — modelin gerçekleştirdiği OR, hedef OR'a
çok yakın (hata <0.002), yani odds-uzayında sadık uygulanıyor. (2) **Duyarlılık
analizi (OAT)** — her OR'ı literatür güven aralığında tarayıp monoton ve sınırlı
davrandığını gösterdik. Detay: `docs/calibration_new_factors.md`.

**S: Hava kirliliği explaining-away yaratır mı?**
Hayır. Yapısal olarak imkânsız — hava kirliliği yalnızca kanserin ebeveyni,
hiçbir semptoma doğrudan oku yok. Sayısal olarak da doğruladık: hava 0→1→2 riski
monoton artırır ve her seviyede sigara=1 > sigara=0.

**S: Hava kirliliği verisini nasıl topluyorsunuz?**
Kullanıcıdan il bilgisi alıp 81 il için **IQAir 2023-2025** yıllık ortalama PM2.5
tablosundan (kronik maruziyet için 3 yıl ortalaması) kademe çıkarıyoruz. 48 il
ölçülmüş, 33 il bölgesel tahmin (her kayıtta etiketli). Anlık AQI yerine yıllık
ortalama kullanıyoruz çünkü kanser riski kronik maruziyetten gelir.

---

## E. Sigara ve Paket-yıl

**S: SMOKING neden ikiliyken paket-yıl ekleme ihtiyacı doğdu?**
NLST'nin ikili "aktif/eski içici" sınıflaması **dozu görmüyor** ve NLST nüfusu
tamamen ağır içici (≥30 py) olduğundan "eski içici" hücresi ağır eski içiciyi
temsil ediyor. Bizim uygulamada hiç-içmeyen ve hafif içici de aynı hücreye
düşüyordu → hiç-içmeyen abartılıyordu. Düzeltme: paket-yıl ile (a) hiç-içmeyeni
düşür (OR≈0.15), (b) ağır + yakın bırakmış eski içiciyi (≥20py, ≤15y) aktif gibi
değerlendir (NLST'nin kendi yüksek-risk tanımı). Doğrulanmış örnek (60-64E,
semptomsuz): hiç içmemiş %0.6, hafif eski %3.6, ağır+yakın eski %6.3, aktif %6.3.

---

## F. Negatif Kanıt ve "Belirtisiz Ağır İçici" Gerilimi

**S: Ağır içici bir hastaya neden bazen düşük skor çıkıyor (örn. uzman setinde E5/E9)?**
Çünkü ajan tüm semptomları soruyor ve hepsi "yok" ise bu **güçlü negatif kanıt**.
Modelin semptom CPT'leri "kanser varsa öksürük çok olası" der; öksürüğün yokluğu
kansere karşı kanıttır. Bu **Bayesçi olarak doğrudur** ama bir gerilim yaratır:
erken kanser çoğu zaman **belirtisizdir**; bu yüzden belirtisiz ağır içici düşük
semptom-skoru alsa bile bir **tarama adayıdır**.

**S: Bu bir hata değil mi?**
Hayır, bilinçli bir ayrım. İki ayrı soruyu ayrı yanıtlıyoruz: "şu anki semptom-
temelli olasılık" (Bayes, düşük olabilir) ve "tarama adayı mı?" (yaş+paket-yıl,
semptomdan bağımsız). Bu yüzden semptom-skorundan bağımsız bir **tarama uygunluğu
bayrağı** ekledik (`screening.py`): E5 düşük skor alsa bile "Tarama Adayı" işareti
hekime yönlendiriyor. Bu, "ne kadar çok tarama, o kadar erken teşhis" amacıyla
birebir uyumlu.

**S: Negatif kanıtın etkisi fazla agresif olabilir mi?**
Olabilir — bu bilinen bir sınırlama. Semptom CPT'leri erken/belirtisiz kanseri
tam yansıtmıyor. Bunu tarama bayrağıyla telafi ediyoruz; gelecek işte semptom
yokluğunun etkisine bir "taban" konabilir veya paket-yıl ağırlığı artırılabilir.

---

## G. Performans Metriği

**S: Neden F1/accuracy kullanmıyorsunuz?**
Çünkü amaç tanı (ikili sınıf) değil, kalibre risk. F1 sürekli olasılığı zorla
eşikler (bilgi kaybı) ve %3.85 taban dengesizliğinde yanıltıcıdır — nitekim eski
F1=0.67, modelin neredeyse her şeye "pozitif" dediği bir durumda yüksek
görünüyordu (precision 0.51, recall 0.97). Yerine: **AUC-ROC, AUPRC** (ayrım),
**Brier, ECE, reliability eğrisi** (kalibrasyon), **Decision Curve Analysis**
(klinik fayda). NLST hold-out: kalibrasyon mükemmel (Brier 0.037, ECE 0.002,
eğim 0.999), AUC 0.65 (sadece demografiden makul; yüksek riske semptomlar taşır).

---

## H. Risk Eşikleri (%5 / %15) — Ne kadar mantıklı?

**S: Eşikleri neye göre belirlediniz?**
NLST taban prevalansı ~%3.85. Eşikler: Düşük <%5 (≈taban, ~1.3× taban), Orta
%5-15, Yüksek >%15 (≈3.9× taban). Mantık: "düşük ≈ popülasyon tabanı, yüksek ≈
tabanın ~4 katı, klinik olarak anlamlı yükselme".

**S: %15 yüksek eşiği ne kadar savunulabilir? (Eleştirel bakış)**
*Güçlü yanları:* (1) Tabana göre relatif bir çapa olarak tutarlı — "~4× taban"
anlamlı bir yükselmedir. (2) Model kalibre olduğundan %15 gerçekten ~%15 olasılığa
karşılık gelir ki bu akciğer kanseri için yüksektir (genel popülasyon yıllık
insidansı <%0.1). (3) Aşırı düşük bir eşik çok fazla "yüksek" üretir → alarm
yorgunluğu ve doktorun "gereksiz korkutma" uyarısıyla çelişir.
*Zayıf yanları / dürüst eleştiri:* (1) Skorumuz **1-yıllık mutlak risk değil**,
semptoma koşullu bir BBN posterior'u; o yüzden epidemiyolojik mutlak risk
eşikleriyle (örn. PLCOm2012'nin 6-yıllık %1.5'i) doğrudan kıyaslanamaz. Yani
%5/%15 **kalibre karar eşikleri değil, iletişim/farkındalık bantları**. (2) Model
belirtisiz ağır içiciyi %5'in altına düşürebildiğinden, tek başına bu bantlar
**az-yönlendirme** yapar — bu yüzden tarama bayrağına ihtiyaç var.
*Önerim/savunmam:* %5/%15'i **relatif iletişim bantları** olarak konumlandırıyoruz;
gerçek "taranmalı mı?" kararını semptomdan bağımsız tarama bayrağı + Decision
Curve Analysis veriyor. Eşikleri **uzman doğrulama setiyle** (10 vaka) ampirik
olarak da sınıyoruz — uzmanın seviye atamalarıyla uyum, eşiklerin gerçekçiliğini
gösterecek. Gelecekte DCA'nın net-fayda optimumu veya uzman uzlaşısıyla
ince-ayar yapılabilir.

---

## I. Açıklanabilirlik

**S: Bir hastaya "skorun neden bu?" diye nasıl açıklıyorsunuz?**
Üç araçla: (1) **Shapley katkıları** — her bulgunun sıra-bağımsız adil katkısı
(toplamları skora eşit). (2) **Waterfall** — taban riskten başlayıp bulgu ekleyerek
skorun oluşumu. (3) **OR çarpanları** — raporda her risk faktörünün kaç kat
artırdığı. Detay: `docs/explainability_demo.md`.

**S: Aynı semptom her hastada aynı katkıyı yapar mı?**
Hayır. İki nedenle: (a) **doygunluk** — aynı odds çarpanı düşük/orta/yüksek
tabanda farklı yüzde-puan üretir; (b) **confounder** — solunum semptomlarının
(öksürük/hırıltı/nefes darlığı) olasılık oranı sigara durumuna bağlıdır.
Confounder'sız semptomlarda (hemoptizi) odds çarpanı sabit ama yüzde-puan yine
bağlama göre değişir.

---

## J. Mimari ve Mühendislik

**S: Sesli etkileşimi nasıl kurdunuz? Neden OpenAI Realtime değil?**
**Cascade** mimari: STT (Whisper) → LLM/keyword slot çıkarımı → TTS (OpenAI tts-1).
Yapılandırılmış bir sağlık anketi için cascade daha kontrollü, loglanabilir, ucuz
ve tekrarlanabilir; Realtime'ı doğal sohbet gereken mobil faza sakladık. Akış bir
durum makinesi: karşılama → demografi (yaş/cinsiyet, sonra sigara+paket-yıl) →
semptomlar (sırayla) → yeni risk faktörleri → değerlendirme → sesli özet → PDF.

**S: Testlerinizi nasıl yapıyorsunuz?**
`tests/test_scenarios/` — golden doğrulamalı demo vakaları + kontrollü A/B
çiftleri (her biri tek faktörü izole eder). `make scenarios` çalıştırır ve sunum
için açıklamalı bir rapor (`SENARYO_RAPORU.md`) üretir. Ayrı olarak
`tests/expert_validation/` — bir göğüs hastalıkları uzmanına model sonucunu
göstermeden tahmin yaptırıp uyumu ölçtüğümüz 10 vaka.

---

## K. Sınırlamalar ve Gelecek İş

**S: Projenin başlıca sınırlamaları neler?**
(1) NLST kapsam dışı (hiç-içmeyen, <55) için tahminler. (2) Semptom CPT'leri
literatür-temelli, hasta verisiyle doğrulanmadı (uygun etiketli veri yok).
(3) Negatif kanıt belirtisiz erken kanseri eksik temsil edebilir. (4) İl PM2.5'in
33'ü tahmini; il-içi varyasyon yok. (5) Risk eşikleri kalibre karar eşiği değil,
iletişim bandı. (6) Paket-yıl/yaş gibi bilgiler öz-bildirim.

**S: Gelecekte ne eklenir?**
Mobil uygulama (Flutter) + KETEM harita entegrasyonu + OpenAI Realtime; resmi
sim.csb.gov.tr PM2.5 verisi; uzman doğrulamasıyla eşik ince-ayarı; semptom
CPT'lerinin gerçek hasta kohortuyla doğrulanması; belirtisiz kanser için
risk-faktörü ağırlığının artırılması.

---

## L. Katkı Katsayıları Özet Tablosu (her değişkenin riske etkisi)

> Tüm katsayılar kanser **odds**'una uygulanan çarpanlardır. >1 riski artırır,
> <1 azaltır. Risk faktörleri **prior odds**'a (kanser nedeni), semptomlar ise
> **gözlem sonrası** odds'a (Bayes güncellemesi) etki eder. Farkları aşağıda.

### L.1 Risk faktörleri — *kanserin EBEVEYNİ* (OR; prior odds çarpanı)

| Değişken | Tip | Durum | Katsayı | Kaynak |
|---|---|---|---|---|
| AGE | risk faktörü | (tek çarpan değil) | NLST CPT'sinden öğrenilmiş tam tablo | NLST verisi |
| GENDER | risk faktörü | (tek çarpan değil) | NLST CPT | NLST verisi |
| SMOKING | risk faktörü | aktif vs eski | NLST CPT (+ paket-yıl düzeltmesi) | NLST verisi |
| FAMILY_HISTORY | risk faktörü | var / yok | **×1.70** / ×1.00 | Literatür OR (ILCCO, meta) |
| ASBESTOS | risk faktörü | var / yok | **×1.50** / ×1.00 | Literatür OR |
| AIR_POLLUTION | risk faktörü | düşük/orta/yüksek | ×1.00 / **×1.15** / **×1.30** | Literatür OR (PM2.5) |
| (sigara düzeltmesi) | risk faktörü | hiç içmemiş | **×0.15** (aşağı) | epidemiyolojik |

**AGE/GENDER/SMOKING'in etkisi** tek bir OR değil, NLST'den öğrenilmiş tam CPT'dir.
Örnek (erkek, aktif içici) taban P(kanser): <55 %1.20 · 55-59 %2.81 · 60-64 %4.94
· 65-69 %8.22 · 70+ %10.92. Yani yaş etkisi katlanarak artar.

### L.2 Semptomlar — *kanserin ÇOCUĞU* (LR; gözlem güncellemesi, CPT'den hesaplanır)

LR = P(semptom durumu | kanser=1) / P(semptom durumu | kanser=0). **Doğrudan CPT
hücrelerinden hesaplanır.** VAR (=1) odds'u artırır, YOK (=0) azaltır.

| Semptom | Confounder | VAR (=1) | YOK (=0) |
|---|---|---|---|
| COUGHING (öksürük) | sigara | ×6.00 (eski) / ×4.67 (aktif) | ×0.44 / ×0.35 |
| SHORTNESS_OF_BREATH (nefes darlığı) | sigara | ×6.25 / ×6.00 | ×0.54 / ×0.44 |
| WHEEZING (hırıltı) | sigara | ×4.40 / ×4.29 | ×0.82 / ×0.75 |
| CHEST_PAIN (göğüs ağrısı) | yok | ×7.00 | ×0.68 |
| FATIGUE (yorgunluk) | yok | ×2.50 | ×0.62 |
| HEMOPTYSIS (hemoptizi) | yok | **×20.00** | ×0.81 |
| WEIGHT_LOSS (kilo kaybı) | yok | ×7.00 | ×0.68 |

> Solunum semptomlarının (öksürük/nefes darlığı/hırıltı) LR'ı **sigara durumuna
> bağlıdır** (confounder); diğerlerinde sabittir. Hemoptizi en güçlü pozitif kanıt
> (×20), yokluğunun etkisi ise zayıftır (×0.81) — çünkü zaten nadirdir.

### L.3 OR ve LR aynı şey mi? (Sık karışan nokta)

**İkisi de odds çarpanıdır ama kökenleri ve rolleri farklıdır:**

| | OR (risk faktörü, örn. asbest ×1.5) | LR (semptom, örn. öksürük ×4.67) |
|---|---|---|
| Düğüm yönü | Faktör → KANSER (neden) | KANSER → Semptom (sonuç) |
| Neye etki eder | Kanserin **prior** odds'una | Gözlem sonrası (**Bayes güncellemesi**) |
| Nereden geldi | **Literatürden GİRDİ**; kanser CPT'sini kurarken kullanılır | Semptom **CPT'sinden HESAPLANIR** (iki hücrenin oranı) |
| Yorumu | "Asbest kanser olasılığını 1.5 kat artırır" | "Öksürük görmek kanser odds'unu 4.67 kat günceller" |

Yani **OR bir parametre (girdi)**, kanser düğümünün olasılığını biz literatürle
ayarlarız; **LR bir sonuç (çıktı)**, semptom CPT'sinden Bayes'le türetilir. Asbest
kanserin *nedeni* olduğu için odds'u doğrudan çarpar; öksürük kanserin *kanıtı*
olduğu için Bayes onu tersine çevirip odds'u günceller. Matematikte ikisi de
çarpan olarak davranır (bu yüzden benzerler), ama biri "sebep etkisi", diğeri
"kanıt gücü"dür.

### L.4 Risk faktörü / semptom ayrımı nasıl yapılıyor?

Yapısal olarak **okun yönüyle**: kanser düğümüne **giren** oklar risk faktörü
(neden), kanserden **çıkan** oklar semptom (sonuç). Risk faktörleri prior'ı
belirler; semptomlar kanıt olarak prior'ı günceller. Kod tarafında bu ayrım
`get_hybrid_structure()`'daki kenar yönleriyle ve `RISK_FACTOR_ORS` (OR) ile
`build_symptom_cpds` (LR'ı doğuran CPT) arasında nettir.
