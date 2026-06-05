# Praevidio AI — v2 Genişletme Tasarımı

**Tarih:** Haziran 2026
**Kapsam:** (1) 3 yeni risk faktörünün literatür temelli entegrasyonu, (2) veri toplama tasarımı, (3) konuşmalı ajan mimarisi, (4) performans metriği revizyonu
**İlgili modül:** `src/model/hybrid_bayesian_network.py`, `src/pipeline.py`

---

## 0. Mevcut Durumun Özeti (Analiz)

Sistem şu an **hibrit bir Bayesian Belief Network (BBN)** üzerinde çalışıyor:

- **Part A — Risk faktörü CPT'leri:** `P(LUNG_CANCER | AGE, GENDER, SMOKING)`, gerçek NLST klinik çalışma verisinden (n=53.452) öğreniliyor.
- **Part B — Semptom CPT'leri:** `LUNG_CANCER → 7 semptom` (öksürük, nefes darlığı, göğüs ağrısı, hırıltı, yorgunluk, hemoptizi, kilo kaybı), peer-review literatürden uzman-elicitation ile türetiliyor. SMOKING üç solunum semptomu için confounder.
- Akış: Ses → Whisper STT → semptom çıkarımı (keyword / GPT-4o-mini) → RAG ICD-10 → BBN çıkarımı → risk skoru (0–100%) → WeasyPrint PDF.
- Risk seviyeleri: Düşük (<%5), Orta (%5–15), Yüksek (>%15). ~%3.85 taban prevalansına göre kalibre edilmiş.
- Model "explaining-away" sorunu için zaten bir duyarlılık analizi + kalibrasyon adımından geçmiş (bkz. `sensitivity_analysis_calibration.md`).

Doktorun önerdiği yeni 3 faktör (ailede kanser geçmişi, asbest maruziyeti, hava kirliliği) tıpkı SMOKING gibi **`LUNG_CANCER`'ın ebeveyni olan risk faktörleridir** — semptom değil. Bu yüzden Part A'ya eklenmeleri gerekir.

**Önemli kısıt:** NLST verisinde bu 3 değişken yok. Dolayısıyla bunları veriden öğrenemeyiz; literatürdeki **odds ratio (OR) / relative risk (RR)** değerlerini NLST tabanına çarpan olarak uygulayarak türetmemiz gerekir. Bu, projenin mevcut "NLST tabanı + literatür düzeltmesi" felsefesiyle birebir uyumlu.

---

## 1. Literatür Araştırması: 3 Yeni Risk Faktörü

### 1.1 Ailede Kanser Geçmişi (Birinci Derece Akraba)

| Bulgu | Değer | Kaynak |
|---|---|---|
| Birinci derece akrabada akciğer kanseri (havuzlanmış, sigara-düzeltilmiş) | **RR ≈ 1.51** | ILCCO pooled analysis (Coté et al.) |
| Meta-analiz (28 çalışma) | **RR ≈ 1.88** | Cancer Treat Rev meta-analizi |
| Anne / baba / kardeş | OR 1.96 / 1.62 / 1.92 | Meta-analiz |
| 2+ etkilenmiş akraba | OR ≈ 3.60 | Meta-analiz |
| Hem vaka hem akraba <60 yaş tanı | OR ≈ 4.89 | BJC, age-at-diagnosis çalışması |

**Tasarım için seçilen değer:** Tek birinci derece akraba için **OR ≈ 1.7** (sigara-düzeltilmiş 1.51 ile meta 1.88 arası, savunulabilir orta nokta). İstersek ileride "2+ akraba" için ikinci bir kademe (OR ≈ 3.6) eklenebilir; demo için ikili (var/yok) yeterli.

### 1.2 Asbest Maruziyeti (Mesleki)

| Bulgu | Değer | Kaynak |
|---|---|---|
| Hiç maruz kalma (ever vs never, büyük havuz, erkek) | **OR ≈ 1.24** | 14 Avrupa/Kanada vaka-kontrol havuzu |
| Belirgin maruziyet (vaka-kontrol) | **OR ≈ 2.04** | Indonezya hastane-temelli çalışma |
| Orta/yüksek konsantrasyon | OR ≈ 2.16 | Aynı çalışma |
| Asbestoz olmadan, sigara içmeyen | 3.6 kat | North American Insulator Cohort |
| Sigara ile sinerji | additif–multiplikatif arası | Meta-analiz (synergism) |

**Tasarım için seçilen değer:** "Riskli meslek grubunda çalıştı/çalışıyor" (öz-bildirim) için **OR ≈ 1.5** (muhafazakâr; çünkü öz-bildirilen meslek = doğrulanmış maruziyet değil). Doğrulanmış yoğun maruziyet için literatür ~2.0'a çıkıyor. Sigara ile birlikteyse risk daha da artar — bu mevcut çarpımsal yapıda kendiliğinden yakalanıyor.

**Riskli meslek listesi (asbest proxy'si):** inşaat/yıkım işçiliği, gemi söküm/tersane, izolasyon/yalıtım, fren balatası–otomotiv tamiri, çimento/eternit fabrikası, maden, boru/kazan tesisatı, tekstil (asbest elyaf), eski bina tadilatı.

### 1.3 Hava Kirliliği (PM2.5)

| Bulgu | Değer | Kaynak |
|---|---|---|
| Akciğer kanseri, her 10 µg/m³ PM2.5 artışı | **RR ≈ 1.08–1.16** | Çok sayıda meta-analiz (15–17 çalışma) |
| En tutarlı havuz tahmini | **RR ≈ 1.16** (%95 GA 1.09–1.23) | Hamra/IARC meta-analizleri |
| Türkiye ulusal yıllık ortalama PM2.5 | ~15–26 µg/m³ | IQAir / istatistik kaynakları |
| WHO kılavuz değeri | 5 µg/m³ | WHO 2021 |

Türkiye'de hiçbir il WHO kılavuzunu karşılamıyor; maruziyet WHO sınırının ~5 katı. Risk **kronik (uzun yıllık) maruziyetten** kaynaklanır — anlık AQI değil.

**Tasarım için seçilen değerler (3 kademe, 1.16/10µg ankrajlı):**

| Kademe | Yıllık ortalama PM2.5 | OR (taban=düşük) |
|---|---|---|
| Düşük | < 10 µg/m³ | 1.0 |
| Orta | 10–20 µg/m³ | ≈ 1.15 |
| Yüksek | > 20 µg/m³ | ≈ 1.30 |

---

## 2. Kullanıcıdan Veri Toplama Tasarımı

### 2.1 Ailede Kanser Geçmişi → doğrudan sor (✅ senin önerin doğru)
Net, ikili bir soru:
> *"Birinci derece akrabalarınızda (anne, baba, kardeş) akciğer kanseri öyküsü var mı?"* → Evet / Hayır / Bilmiyorum
- "Bilmiyorum" → nötr (OR=1.0) olarak ele alınır (eksik kanıt).
- İleride opsiyonel: "Kaç akrabada?" → 2+ ise yüksek kademe.

### 2.2 Asbest → meslek üzerinden proxy (✅ senin önerin doğru)
Doğrudan "asbeste maruz kaldınız mı?" sorusu çoğu kullanıcı için anlamsız. Bunun yerine:
> *"Şu meslek gruplarından birinde 1 yıldan uzun çalıştınız mı: inşaat/yıkım, tersane, yalıtım, maden, otomotiv tamiri, çimento/eternit fabrikası?"* → Evet / Hayır
- Evet → ASBESTOS=1 (OR≈1.5). Bu bir **tahmini proxy**; raporda "öz-bildirilen mesleki risk" olarak etiketlenmeli, "doğrulanmış asbest maruziyeti" denmemeli.

### 2.3 Hava Kirliliği → konum (il) üzerinden lookup (🔵 birlikte değerlendirelim — önerim)

Üç seçenek var; **B önerim:**

**A) Sübjektif soru:** "Yoğun trafik / sanayi bölgesinde mi yaşıyorsunuz?" → Basit ama öznel, güvenilmez.

**B) İl bazlı statik PM2.5 tablosu (ÖNERİLEN):**
> *"Hangi ilde yaşıyorsunuz?"* → kullanıcı ili söyler (zaten konuşma içinde doğal) → 81 il için **yıllık ortalama PM2.5 lookup tablosu** → düşük/orta/yüksek kademesine eşlenir → CPT katkısı.
- **Artısı:** Düşük kullanıcı yükü, objektif, **kronik maruziyeti** temsil eder (kanser riski için doğru olan budur), API/izin gerektirmez, demo için tek bir küçük JSON tablosu yeterli.
- **Eksisi:** İl içi varyasyonu (şehir merkezi vs kırsal) yakalamaz; tablonun güncel tutulması gerekir. Demo için kabul edilebilir.
- Kaynak: Çevre Bakanlığı (sim.csb.gov.tr) il bazlı istasyon ortalamaları veya IQAir/WHO il verisi → `data/knowledge_base/tr_il_pm25.json`.

**C) Gerçek-zamanlı geolocation + AQI API (IQAir/aqicn):** Objektif ve otomatik ama **anlık** AQI kronik riski temsil etmez; konum izni + API bağımlılığı demo için gereksiz karmaşa.

> **Öneri:** Demo'da B. İl → PM2.5 kademe → OR. İleride mobil uygulamada ilçe/mahalle çözünürlüğüne veya C ile yıllık ortalamaya çıkılabilir.

> **✅ Uygulandı (gerçek veri):** `tr_il_pm25.json` artık **IQAir 2025 World Air Quality Report** (2023–2025) ölçülmüş değerleriyle dolduruldu. 48 il doğrudan ölçüm (kronik maruziyet için **3 yıllık ortalama**; il adı raporda yoksa il merkezi/büyük ilçe istasyonu kullanıldı), 33 il bölgesel tahmin (her kayıtta `source` alanıyla etiketli). Resmi sim.csb.gov.tr verisi gelirse aynı formata doğrudan işlenebilir.

---

## 3. BBN Entegrasyon Tasarımı

### 3.1 Yeni ağ yapısı
3 yeni düğüm, `LUNG_CANCER`'ın ebeveyni olarak eklenir (SMOKING gibi):

```
AGE ─────────┐
GENDER ──────┤
SMOKING ─────┤
FAMILY_HISTORY ──┤──→ LUNG_CANCER ──→ (7 semptom, mevcut)
ASBESTOS ────┤
AIR_POLLUTION ───┘
```

- FAMILY_HISTORY: 2 durum (0=yok/bilinmiyor, 1=var)
- ASBESTOS: 2 durum (0=hayır, 1=riskli meslek)
- AIR_POLLUTION: 3 durum (0=düşük, 1=orta, 2=yüksek)

### 3.2 CPT'yi odds-ratio çarpımıyla türetme (öğrenme yok, kalibrasyon var)

NLST tabanından başlanır, literatür OR'ları çarpılır:

```
odds_base  = p_NLST / (1 − p_NLST)          # P(cancer | AGE,GENDER,SMOKING)
odds_adj   = odds_base × OR_fam × OR_asb × OR_air
p_adj      = odds_adj / (1 + odds_adj)
```

Başlangıç OR'ları (sonra duyarlılık analiziyle kalibre edilecek — mevcut metodolojiyle birebir aynı):

| Faktör | Durum | OR |
|---|---|---|
| FAMILY_HISTORY | var | 1.7 |
| ASBESTOS | riskli meslek | 1.5 |
| AIR_POLLUTION | orta / yüksek | 1.15 / 1.30 |

Yeni `LUNG_CANCER` CPT boyutu: 5(AGE)×2(GENDER)×2(SMOKING)×2(FAM)×2(ASB)×3(AIR) = **240 sütun**, hepsi yukarıdaki formülle programatik üretilir (elle girilmez).

### 3.3 Neden bu yaklaşım?
- **Açıklanabilir:** Her faktörün katkısı tek bir OR; rapora "ailede öykü riski ×1.7 artırdı" diye yazılabilir.
- **Veri-uyumlu:** NLST tabanını bozmaz, üstüne biner.
- **Tutarlı:** Mevcut "explaining-away" kalibrasyon disiplini buraya da uygulanır (örn. yüksek hava kirliliği + sigara birlikteyken monotonluk korunmalı).

### 3.3b Explaining-away kararı (hava kirliliği)
Yeni 3 faktör (aile öyküsü, asbest, hava kirliliği) **yalnızca `LUNG_CANCER`'ın ebeveyni**;
hiçbir semptoma doğrudan ok yok. Ortak çocuk `LUNG_CANCER` da hiç gözlenmediği için
faktörler marjinal bağımsız kalır → **explaining-away yapısal olarak oluşmaz** (sigarada vardı,
çünkü sigaranın semptoma doğrudan oku var). Sayısal doğrulama: hava 0→1→2 riski monoton
artırır ve her seviyede sigara=1 > sigara=0. **Karar: hava kirliliği saf kanser risk faktörü
olarak modellenir; `AIR_POLLUTION → solunum semptomu` confounder okları EKLENMEDİ.** (Eklenseydi
sigaradaki kalibrasyon süreci tekrarlanırdı.)

### 3.4 Rapor & dil (doktorun uyarısı)
Doktor "dil kritik — korkutmadan taramaya yönlendir" dedi. Öneriler:
- Skor **olasılık** olarak değil, **"risk düzeyi + ne yapmalı"** olarak sunulmalı. "Kanserseniz" değil, "riskiniz yüksek görünüyor, bir göğüs hastalıkları uzmanına başvurmanız önerilir".
- Her raporda görünür feragatname: *"Bu bir tarama/farkındalık aracıdır, tanı koymaz."* (zaten var, korunmalı).
- Yeni faktörler için yumuşak dil: "doğrulanmış asbest maruziyeti" değil "mesleki risk olasılığı".
- Kapanış mesajı doktorun sözüyle uyumlu: *"Ne kadar erken tarama, o kadar erken teşhis."*

---

## 4. Konuşmalı Ajan Mimarisi

### 4.1 Cascade vs Realtime

| Kriter | Cascade (STT→LLM→TTS) | OpenAI Realtime (speech-to-speech) |
|---|---|---|
| Gecikme | Orta (turn-based için yeterli) | Çok düşük (barge-in, doğal kesme) |
| Kontrol / slot-filling | **Yüksek** — her turu sen yönetirsin | Düşük — yapılandırılmış akış zor |
| Loglama / kanıt çıkarımı | **Kolay** (her turda evidence dict) | Zor |
| Mevcut bileşenleri yeniden kullanım | **Whisper + GPT-4o-mini + bir TTS hazır** | Çoğu yeniden yazılır |
| Maliyet | Düşük | Yüksek |
| Determinizm / tekrarlanabilirlik (demo) | **Yüksek** | Düşük |

> **Öneri — Demo için CASCADE.** Bir sağlık anketi sıralı, yapılandırılmış slot-filling işidir; ultra-düşük gecikme/barge-in gerekmez. Mevcut Whisper STT + GPT-4o-mini'yi yeniden kullanır, her turda kanıt toplamak ve loglamak kolaydır, ucuzdur ve demo'da tekrarlanabilir. Realtime'ı mobil uygulama fazına (doğal sohbet istendiğinde) saklayalım.
>
> TTS için: OpenAI TTS (`tts-1`, Türkçe) veya yerel bir seçenek. Whisper zaten var.

### 4.2 Oturum akışı (state machine)

```
[0] KARŞILAMA (TTS)
    "Merhaba. Sağlıklı bir risk analizi için önce yaş, cinsiyet ve
     sigara kullanım durumunuzu söyler misiniz?"
        ↓ (ses kaydı → STT → GPT slot çıkarımı)
[1] DEMOGRAFİ TOPLAMA  → AGE, GENDER, SMOKING
    eksik slot varsa → sadece eksiği tekrar sor (örn. "Sigara durumunuzu alamadım…")
        ↓
[2] SEMPTOM DÖNGÜSÜ  (7 semptom, sırayla sorulur)
    "Son zamanlarda öksürük şikâyetiniz var mı?" → kaydet → sonraki
    (kullanıcı serbest konuşursa GPT birden fazla semptomu tek seferde yakalar)
        ↓
[3] YENİ RİSK FAKTÖRLERİ
    "Ailenizde akciğer kanseri öyküsü var mı?"      → FAMILY_HISTORY
    "Şu meslek gruplarında çalıştınız mı: …?"        → ASBESTOS
    "Hangi ilde yaşıyorsunuz?"                        → il → PM2.5 → AIR_POLLUTION
        ↓
[4] DEĞERLENDİRME  → tüm kanıtlar birlikte → engine.predict_risk()
        ↓
[5] SESLİ ÖZET (TTS)
    risk düzeyi + öneri (yumuşak dil) +
    "Detaylı raporu indirmek için rapor butonuna basabilirsiniz."
        ↓
[6] PDF  (zaten otomatik üretiliyor — butona bağlanır)
```

### 4.3 Uygulama notları
- Her state'in bir **"required slots"** listesi var; eksikse aynı state tekrarlanır (en fazla 2 deneme, sonra "bilinmiyor" geçilir).
- GPT-4o-mini'ye slot-çıkarım için JSON-schema'lı bir system prompt verilir; `symptom_extractor.py` zaten bu işin temelini yapıyor — demografi + yeni faktörler için genişletilir.
- Demo'da web yerine basit bir CLI/Streamlit ses döngüsü yeterli ("çalışan model göster" hedefi). Mobil sonraki dönem.

---

## 5. Performans Metriği Önerisi (F1'in Yerine)

### 5.1 F1 neden bu proje için uygun değil?
1. **Hedef tanı değil, risk stratifikasyonu.** "Bu kişi kanser/değil" demiyoruz; "şu olasılıkla risk altında" diyoruz. F1, sürekli olasılığı zorla eşikleyip ikili sınıfa indirger → bilgi kaybı.
2. **Eşiğe aşırı duyarlı + sınıf dengesizliği.** Taban ~%3.85. Mevcut sonuçlar (F1=0.67, recall=0.97, precision=0.51, accuracy=0.51) modelin neredeyse **her şeye "pozitif" dediğini** gösteriyor — confusion matrix [[42,1439],[42,1475]] bunu doğruluyor. F1 burada yanıltıcı şekilde "iyi" görünüyor.
3. **Deployment'ta ground-truth yok.** Semptom-temelli çıktılar için gerçek kanser etiketi yok; F1 hesaplanamaz bile.

### 5.2 Önerilen metrik seti

**A) Ayrım gücü (discrimination) — modeli sıralama yeteneği:**
- **AUC-ROC (AUROC):** Birincil metrik. Eşikten bağımsız; "model riskli olanı risksizden yüksek skorluyor mu?"
- **AUPRC (PR-AUC):** Sınıf dengesizliğinde AUROC'tan daha bilgilendirici — bunu da raporla.

**B) Kalibrasyon — "%15 dediğimizde gerçekten ~%15 mi?" (bir risk skoru için EN kritik):**
- **Brier skoru:** Olasılık doğruluğunun tek-sayı özeti (düşük = iyi).
- **Kalibrasyon eğrisi (reliability diagram) + ECE** (Expected Calibration Error).
- **Kalibrasyon eğimi/kesişimi** (Cox): sistematik over/under-confidence kontrolü.

**C) Klinik fayda — tarama aracı için modern standart:**
- **Decision Curve Analysis (net benefit):** "Bu skoru kullanmak, herkesi tara / kimseyi tarama'ya kıyasla net fayda sağlıyor mu?" Tarama araçları için altın standart.
- Seçilen eşiklerde (%5, %15) **duyarlılık (sensitivity) ve özgüllük (specificity)** — projenin amacı "daha çok kişiyi taramaya yönlendirmek" olduğu için yüksek duyarlılık önceliklendirilir.
- İsteğe bağlı: **Number Needed to Screen (NNS)**.

### 5.3 Özet öneri
> Birincil: **AUC-ROC + Kalibrasyon (Brier + reliability eğrisi)**.
> İkincil: **Decision Curve Analysis** (klinik fayda) ve seçilen eşiklerde **duyarlılık/özgüllük**.
> F1/accuracy README'den birincil metrik olmaktan çıkarılır; istenirse referans amaçlı, belirli bir eşikte dipnot olarak bırakılabilir.

Bu set, "tanı koymuyoruz, kalibre bir risk veriyoruz" mesajınla tam uyumlu ve göğüs hastalıkları uzmanının "farkındalık + taramaya yönlendirme" çerçevesini doğrudan ölçer.

---

## 6. Önerilen Uygulama Sırası

1. **Lookup tablosu:** `data/knowledge_base/tr_il_pm25.json` (81 il → yıllık PM2.5 → kademe).
2. **BBN genişletme:** `hybrid_bayesian_network.py`'ye 3 yeni ebeveyn düğüm + OR-çarpımı CPT üretimi + duyarlılık kalibrasyonu.
3. **Slot çıkarımı:** `symptom_extractor.py`'yi demografi + yeni faktörler için genişlet (GPT-4o-mini JSON schema).
4. **Konuşma döngüsü:** cascade state-machine (STT→LLM→TTS) — demo için CLI/Streamlit.
5. **Rapor:** yeni faktörleri ve yumuşak dili PDF şablonuna ekle; butonla indirme.
6. **Değerlendirme:** yeni metrik seti (AUC + kalibrasyon + DCA) + çeşitlendirilmiş demo senaryoları + açıklanabilirlik (her faktörün OR katkısı).
