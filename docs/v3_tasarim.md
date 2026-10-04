# Risk Modeli v3 — Tasarım Notu (Güz 2026)

**Amaç.** Bahar dönemi modelini (v2, `src/model/hybrid_bayesian_network.py`) *değiştirmeden*
dört metodolojik düzeltmeyi ayrı bir modülde (`hybrid_bayesian_network_v3.py`) uygulamak ve iki
sürümü yan yana karşılaştırabilmek (`make compare` → `docs/v2_vs_v3_karsilastirma.md`).

## 1. Sorun tespiti (v2 üzerinde ölçüldü)

| Profil (70+ erkek, aktif içici, ek faktör yok) | v2 skoru | Yorum |
| --- | ---: | --- |
| Semptomlar sorulmamış (NLST hücresi) | %10,9 | taban |
| 7 semptoma da "hayır" | %0,34 | odds 36 kat düşüyor → "Düşük", oysa 6 yıllık risk ~%11 |
| 7 semptoma da "evet" | %99,99 | LR+ çarpımı ≈ 294.000 (naive-Bayes aşırı güveni) |

- **Anlam uyuşmazlığı:** NLST etiketi "≈6 yıl içinde tanı" (katılımcılar başlangıçta asemptomatik,
  NLST dışlama ölçütü), semptom CPT'leri "klinik tanı anındaki hasta". Aynı düğümde çarpılınca
  negatif kanıt 6 yıllık riski siliyor.
- **Koşullu bağımsızlık:** öksürük–nefes darlığı–hırıltı KOAH üzerinden birlikte gelir; ayrı ayrı
  çarpmak kanıtı 2–3 kez sayar.
- **Referans kategorisi:** NLST hücresi "ortalama maruziyetli" kişidir; literatür OR'leri üstüne
  çarpılınca sorulmayan herkes ortalamada 1,30× şişer (prior: 1,07 × 1,04 × 1,165).
- **Zaman ufku/eşikler:** %5/%15 bantları hangi ufka ait belirsiz; tarama eşiği PLCOm2012 %1,51/6 yıl.

## 2. Düzeltmeler

### 2.1 Latent "semptomatik" düğümü
`LUNG_CANCER → SYMPTOMATIC → {7 semptom}`; `P(SYMPTOMATIC=1 | LC=1) = q`, `P(SYMPTOMATIC=1 | LC=0) = 0`.
q = "6 yıl içinde tanı alacakların bugün semptomatik payı"; başlangıç **0,35**
(`PRAEVIDIO_Q_SYMPTOMATIC`). Etki (70+ aktif içici): 7 "hayır" → %5,6 (v2: %0,34), sorulmamış → %8,8.
q'nun kalibrasyonu: Hamilton 2005 PPV'leriyle tutarlılık (hemoptizi %2,4; ≥40 yaş birinci basamak)
ve göğüs hastalıkları uzmanı görüşü; duyarlılık analizi q ∈ {0,25; 0,35; 0,5}.

### 2.2 KOAH düğümü (ortak neden, noisy-OR)
`SMOKING → COPD → {COUGHING, SHORTNESS_OF_BREATH, WHEEZING}`, `COPD → LUNG_CANCER` (OR 1,43;
PLCOm2012 exp(0,3553)). P(KOAH | eski içici)=0,12, P(KOAH | aktif)=0,20.
Solunum semptomu CPT'leri noisy-OR ile üretilir:
`P(s=1 | S, sm, copd) = 1 − (1−leak)(1−p_smoke)^sm (1−p_copd)^copd (1−p_cancer)^S`
(parametreler v2'nin belgelenmiş değerlerini aynen üretir; `NOISY_OR` tablosu).
Davranış: KOAH "yok" → semptomlar kansere daha çok yazılır (skor ↑); KOAH "var" → semptomların bir
kısmı KOAH'a yazılır ama KOAH'ın kendi OR'si tabanı yükseltir; bilinmiyorsa prior üzerinden ortalanır.

### 2.3 OR normalizasyonu
Kullanılan çarpan `OR / E[OR]`, `E[OR] = Σ prior_i · OR_i` (aile öyküsü 1,07; asbest 1,04;
hava 1,165; KOAH 1,068). Ortalama/sorulmamış kişi NLST hücresine düşer, "temiz" kişi altına iner.
Tam NLST (CDAS) gelince aile öyküsü/asbest/KOAH doğrudan veriden öğrenilecek ve bu düzeltme o
faktörler için gereksizleşecek. Kapatmak için `PRAEVIDIO_NORMALIZE_ORS=0`.

### 2.4 İki katmanlı çıktı ve klinik uyarı kuralı
- `risk_6y_factors`: yalnız risk faktörlerinden (semptomlar marjinalize) 6 yıllık risk — **tarama katmanı**.
- `risk_score`: semptomlar dahil tam sonsal (v2 ile aynı anlam, raporda korunur).
- `alarm`: **NICE NG12 §1.1** kuralı (≥40 yaş + hemoptizi; ≥40 + ≥2 açıklanamayan semptom;
  ≥40 + sigara öyküsü + ≥1 semptom → acil göğüs röntgeni). Skordan bağımsız; sesli özet ve rapora
  "ACİL" olarak yansır. Öneri metni alarm varsa sevk dilinde, yoksa tarama dilinde konuşur.
- **Bantlar (6 yıllık ufuk):** Düşük <%1,5 · Orta %1,5–5 ("tarama adayı", PLCOm2012 eşiği %1,51) ·
  Yüksek ≥%5 (NLST taban oranının ~1,3 katı; Kovalchik 2013'te en yüksek risk beşte-birliğine denk).
  Eski bantlar: `PRAEVIDIO_BANDS=v2`. Nihai bantlar uzman validasyonu + DCA ile kesinleşecek.

## 3. Bilinen sınırlar / sonraki adımlar
- Çoklu pozitif kanıt hâlâ ~%99 verir (7 "evet"); klinik karar zaten "Yüksek + ACİL". İleride
  semptom LR'lerini meta-analiz DOR'larına (hemoptizi 6,4; nefes darlığı 2,7; öksürük 2,6; göğüs
  ağrısı 2,0 — PLOS One 2018) çeken alternatif CPT seti `SYMPTOM_LR_SOURCE` ile eklenebilir.
- q, KOAH priorları ve bantlar uzman görüşü gerektirir (tests/expert_validation setine v3 sütunu eklenecek).
- Tam NLST/PLCO verisi gelince: paket-yıl dozu, aile öyküsü, asbest, KOAH için CPT'ler veriden;
  PLCOm2012 benchmark (`src/model/plcom2012.py`, planlı).

## 4. Konuşma akışı v3 (`voice_agent.py`)
Açık uçlu şikâyet sorusu → söylenenler not edilir → yalnız eksik belirtiler tek tek;
"bilmiyorum/emin değilim/geç" → alan gözlenmemiş kalır (tekrar sorulmaz); demografi onayı ve
düzeltme ("aslında 61 yaşındayım"); yalın "hayır" → "daha önce içtiniz mi?"; günlük adet sorusu;
KOAH sorusu (v3); iki katmanlı sesli özet. Model seçimi: `--model v2|v3` (varsayılan v3).

## 5. STT / TTS
- STT: `gpt-4o-mini-transcribe` (varsayılan, $0,003/dk) + sabit tıbbi terim ipucu
  (`STT_CONTEXT_TERMS`); `PRAEVIDIO_STT_MODEL=whisper-1` ile eski davranış.
- TTS: `PRAEVIDIO_TTS_PROVIDER=edge` → Microsoft Edge nöral Türkçe sesleri (ücretsiz,
  `tr-TR-EmelNeural` / `AhmetNeural`); kör dinleme testi `make tts-test`
  (`data/processed/tts_test/`, cevap anahtarı `KEY.json`). Üretimde Azure Speech / Google Chirp 3 HD.

**Kaynaklar.** Tammemägi MC et al. NEJM 2013;368:728-36 (PLCOm2012). Kovalchik SA et al. NEJM
2013;369:245-54. NICE NG12 (2015, güncelleme 2023). Hamilton W et al. Thorax 2005;60:1059-65.
Pre-diagnostic symptoms meta-analysis, PLOS One 2018;13(11):e0207686. Fenton & Neil, Risk
Assessment and Decision Analysis with Bayesian Networks, 2nd ed., CRC 2018 (noisy-OR, böl. 9).
