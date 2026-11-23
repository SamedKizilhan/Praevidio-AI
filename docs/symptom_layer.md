# The symptom layer: design note (4 November 2026)

*English first; the Turkish original follows below.*

## The problem

In v3.1 the full score (risk factors and symptoms) carried the **same bands** as the 6-year layer (low below
1.5 %, moderate 1.5 to 5 %, high 5 % or more). The lower bound of those bands is the **screening** threshold of
PLCOm2012, meant for low-dose CT in a person without symptoms. The full score, however, adds up two different
questions: a cancer without symptoms that will appear in the next six years (screening) and a cancer that is
causing today's symptoms (diagnosis and referral). As a result a 62-year-old smoker without symptoms appeared as
"moderate" (1.5 %), while for a 35-year-old woman with seven symptoms 14.2 of her 14.4 % came from the present
symptoms, and both cases were described in the same vocabulary.

## The solution

* **The 6-year layer** (the screening question) did not change: the number, the bands, the 1.5 % threshold.
* **The symptom layer** (the referral question):
  `P(lung cancer causing symptoms now | evidence) = P(LC | evidence) · P(SYMPTOMATIC | LC, evidence)`.
  The second factor does not depend on the base risk (the same share with NLST, PLCOm2012 or Wakelee; tested).
  * `none`: no symptom reported. `low`: below the threshold, "see your family physician if it has lasted a few
    weeks". `elevated`: at or above the threshold, prompt physician assessment.
  * **Threshold 3 %**: the referral criterion of NICE NG12 for primary care (a positive predictive value of 3 %,
    which NICE states openly to be a value judgement). It can be changed with `PRAEVIDIO_SYMPTOM_REFERRAL_PPV`.
    The model value is not a measured predictive value.
* **Prompt physician assessment** = the NICE NG12 rule (age 40 or more) **or** an `elevated` symptom layer **or**
  haemoptysis at any age (it should not be left waiting for its non-cancer causes either, such as infection or
  tuberculosis, and it is not presented in the language of suspected cancer).
* **The full score** has no band; it stays in the report as a number, labelled "mixed horizon, additional
  information".

## Validation (`tests/model/test_symptom_layer.py`)

Age 62, 40 pack-years, one symptom present and the other six denied: haemoptysis 7.7 % (Hamilton 2005: 2.4 %
overall, 7.1 % at age 70 or more, about double in smokers); chest pain or weight loss 2.5 %; cough 0.3 %. Single
symptoms other than haemoptysis stay below 4 % (Hamilton below 2 %, times about two for smoking). In a never-smoker
no single symptom crosses the threshold. A woman of 35 with every risk factor and seven symptoms: 14.2 %, prompt
assessment (the NICE rule does not fire because of her age). A never-smoker of 30 with haemoptysis only: the
probability of cancer is 0.04 % (the honest number), yet prompt assessment is advised by the haemoptysis rule.

## Open questions for the expert session

* The threshold for Türkiye: 3 %, or lower, given easy access to chest X-rays and specialists?
* Extending PLCOm2012 below the age of 50 may also raise the symptom layer in young people.
* The **number** of the symptom layer is not shown on the user's screen (only the message); it appears in the
  physician report. Reason: it is a model estimate and not a measured predictive value, it has not been validated
  below the age of 50, and the information needed for the decision is whether it is below or above the threshold.

## Addendum (15 November 2026): explaining a small 6-year percentage

With the symptom number hidden, the only number the user sees is the 6-year risk, and "0.42 %" can look
negligible to someone who does not know the subject. The 6-year layer is therefore also shown as a **natural
frequency**: "About 42 in 10,000 people like you; about 1.2 among peers of the same age without risk factors;
about 34 times" (two bars on the screen, a sentence in the spoken summary and in the physician report). The
denominator is the smallest power of ten for which the peer count is at least 1; the numbers are consistent with
the relative risk (`tests/model/test_context.py`). Absolute and relative risk are given together: relative risk
alone ("34 times") reads as alarming, a percentage alone ("0.42 %") as negligible.

---

## Türkçe: Belirti katmanı — tasarım notu (4 Kasım 2026)

### Sorun
v3.1'de tam skor (risk etkenleri + belirtiler) 6 yıllık katmanla **aynı bantlarla** (Düşük < %1,5 · Orta %1,5–5 ·
Yüksek ≥ %5) etiketleniyordu. Bu bantların alt sınırı PLCOm2012'nin **tarama** eşiğidir (belirtisiz kişide düşük doz
BT). Tam skor ise iki farklı sorunun toplamıdır: önümüzdeki 6 yılda ortaya çıkacak belirtisiz kanser (tarama) ve
bugünkü belirtilere yol açan kanser (tanı/sevk). Sonuç: belirtisiz 62 yaş içici "Orta" (%1,5) görünürken, 35 yaşında
7 belirtili kadının %14,4'ünün %14,2'si bugünkü belirtilerden geliyordu ve iki durum aynı etiket dilini kullanıyordu.

### Çözüm
* **6 yıllık katman** (tarama sorusu) değişmedi: sayı, bantlar, %1,5 eşiği.
* **Belirti katmanı** (sevk sorusu): `P(şu an belirti veren akciğer kanseri | kanıt) = P(LC | kanıt) · P(SEMPTOMATİK | LC, kanıt)`.
  İkinci çarpan taban riskten bağımsızdır (NLST / PLCOm2012 / Wakelee ile aynı pay — test edildi).
  * `none`: belirti bildirilmedi · `low`: < eşik → "birkaç haftadır sürüyorsa aile hekiminize" · `elevated`: ≥ eşik → kısa sürede hekim.
  * **Eşik %3** = NICE NG12'nin birinci basamak sevk ölçütü (PPV %3; NICE'ın açıkça belirttiği bir değer yargısı).
    `PRAEVIDIO_SYMPTOM_REFERRAL_PPV` ile değiştirilebilir. Model değeri ölçülmüş bir PPV değildir.
* **Kısa sürede hekim** = NICE NG12 kuralı (≥40 yaş) **ya da** belirti katmanı `elevated` **ya da** hemoptizi (her yaşta;
  enfeksiyon, tüberküloz gibi kanser dışı nedenleri için de beklenmemeli — kanser şüphesi diliyle sunulmaz).
* **Tam skor** bantlanmaz; raporda "karma ufuk, ek bilgi" olarak sayıyla kalır.

### Doğrulama (`tests/model/test_symptom_layer.py`)
62 yaş, 40 paket-yıl, tek belirti + diğer 6 "hayır": hemoptizi %7,7 (Hamilton 2005: genel %2,4, 70+ yaş %7,1, sigara
içende ~2 kat); göğüs ağrısı/kilo kaybı %2,5; öksürük %0,3 — hemoptizi dışındaki tek belirtiler < %4 (Hamilton < %2 ×
sigara ~2). Hiç içmemişte tek belirtilerin hiçbiri eşiği aşmaz. 35 yaş kadın, tüm etkenler, 7 belirti: %14,2 → kısa
sürede hekim (NICE kuralı yaş nedeniyle tetiklenmez). 30 yaş hiç içmemiş, yalnız hemoptizi: kanser olasılığı %0,04
(dürüst sayı) ama hemoptizi kuralıyla kısa sürede hekim.

### Açık konular (uzman görüşmesinde sorulacak)
* Türkiye için eşik: %3 mü, daha düşük mü (göğüs röntgeni/uzman erişimi kolay)?
* PLCOm2012'nin 50 yaş altına uzatılması genç kişilerde belirti katmanını da yükseltebilir.
* Kullanıcı ekranında belirti katmanının **sayısı gösterilmiyor** (yalnız mesaj); sayı hekim raporunda yer alıyor.
  Gerekçe: model tahmini, ölçülmüş PPV değil ve 50 yaş altında doğrulanmadı; karar için gereken bilgi eşiğin
  altında/üstünde olmasıdır.

### Ek (15 Kasım 2026): 6 yıllık küçük yüzdenin anlatımı
Belirti sayısı gizlenince kullanıcının gördüğü tek sayı 6 yıllık risk kalıyor ve "%0,42" konuyu bilmeyene önemsiz
görünebiliyor. Bu yüzden 6 yıllık katman **doğal sıklık** olarak da gösterilir: "Sizinle aynı özelliklere sahip
10.000 kişiden yaklaşık 42 kişi; risk etkeni olmayan yaşıtlarınızda yaklaşık 1,2 — yaklaşık 34 kat" (ekranda iki
çubuk, sesli özette ve hekim raporunda cümle). Payda, yaşıt sayısı ≥ 1 olan en küçük 10'un kuvvetidir; sayılar göreli
riskle tutarlıdır (`tests/model/test_context.py`). Mutlak ve göreli risk birlikte verilir; yalnız göreli risk
("34 kat") abartılı, yalnız yüzde ("%0,42") önemsiz algılanır.
