# Risk Skoru Nasıl Hesaplanır? — Sunum Notları

Bu belge, Praevidio AI'nın bir risk skorunu nasıl ürettiğini **basit ve sezgisel**
biçimde anlatır. Hedef: sunumda skoru güvenle açıklayabilmek.

---

## 1. BBN (Bayesian Belief Network) nedir? — sezgi

Bir **Bayesçi İnanç Ağı**, "neyin neye sebep olduğunu" oklarla gösteren bir
diyagramdır. Her düğüm bir değişkendir (kanser, sigara, öksürük…), her ok bir
**nedensel ilişki**dir. Ağ, eldeki kanıtlara bakarak "kanser olma olasılığı
ne?" sorusunu olasılık kurallarıyla (Bayes) cevaplar.

Bizim ağımızın iskeleti şöyle:

```
        (RİSK FAKTÖRLERİ)                         (SEMPTOMLAR)
   Yaş ─┐                              ┌──► Öksürük
 Cinsiyet ┤                            ├──► Nefes darlığı
  Sigara ─┤                            ├──► Göğüs ağrısı
 Aile öyküsü ┼──►  AKCİĞER KANSERİ  ───┼──► Hırıltı
  Asbest ──┤        (gizli düğüm)      ├──► Yorgunluk
 Hava kirliliği ┘                      ├──► Hemoptizi
                                       └──► Kilo kaybı
```

İki yön var ve bu **bilinçli** bir tasarım:

- **Risk faktörleri → kanser:** Yaş, cinsiyet, sigara, aile öyküsü, asbest ve
  hava kirliliği kanser olasılığını *artıran* nedenlerdir (kanserin "ebeveynleri").
- **Kanser → semptomlar:** Kanser, semptomlara *sebep olur* (semptomların
  "ebeveyni"). Yani modelde "kanser varsa öksürük görme olasılığı şudur" yazar.
  Tanı anında biz tersine yürürüz: "öksürük gördüm, kanser olasılığı ne kadar
  yükseldi?" (Bayes bunu yapar.)

> **Neden bu yapı?** Çünkü gerçekte hastalık semptomu yaratır, semptom hastalığı
> değil. Bu "üretici (generative)" yön, tıbbi BBN'lerde standarttır ve modeli
> **açıklanabilir** kılar — her okun arkasında bir olasılık tablosu (CPT) vardır.

`LUNG_CANCER` düğümü **hiç gözlenmez** (zaten bilmediğimiz, tahmin etmeye
çalıştığımız şey odur); biz onun olasılığını hesaplarız. Risk skoru = bu olasılık.

### 1.1 Okların yönü ve hangi olasılık nerede saklı (sık karışır!)

Modelde iki tür ok var ve **sakladıkları olasılık farklı yöndedir**:

- **Risk faktörü → KANSER** (yaş, cinsiyet, sigara, aile öyküsü, asbest, hava):
  Burada saklanan olasılık **P(KANSER | risk faktörleri)**'dir — yani "bu risk
  faktörleri varsa kanser olasılığı nedir". *(P(risk faktörü | kanser) DEĞİL!)*
  Çünkü ok faktörden kansere gider; faktör kanserin **nedeni**dir.
- **KANSER → semptom** (7 semptom): Burada saklanan olasılık
  **P(semptom | KANSER)**'dir — "kanser varsa bu semptomu görme olasılığı".
  Çünkü ok kanserden semptoma gider; semptom kanserin **sonucu**dur.

Sonra çıkarım (inference) bu ikisini Bayes kuralıyla birleştirip aradığımız
**P(KANSER | risk faktörleri + semptomlar)**'ı hesaplar. Yani:

```
GİRDİ (CPT'lerde saklı):  P(kanser | risk faktörleri)   ve   P(semptom | kanser)
ÇIKTI (hesaplanan):        P(kanser | risk faktörleri VE semptomlar)  = risk skoru
```

Özet: risk faktörü tarafında olasılık **zaten kanser yönünde** (doğrudan), semptom
tarafında **kanserden semptoma** (ters); Bayes semptom tarafını çevirip birleştirir.

### 1.2 OR (asbest ×1.5) ile LR (öksürük ×4.67) aynı mı?

İkisi de kanser **odds**'una uygulanan çarpandır, **ama kökenleri ve rolleri farklı:**

| | OR — risk faktörü (örn. asbest ×1.5) | LR — semptom (örn. öksürük ×4.67) |
|---|---|---|
| Ok yönü | Faktör → Kanser (**neden**) | Kanser → Semptom (**sonuç**) |
| Etkilediği | Kanserin **önceki (prior)** odds'u | Gözlem sonrası **Bayes güncellemesi** |
| Nereden gelir | **Literatürden girdi** — kanser CPT'sini kurarken çarpanız | Semptom **CPT'sinden hesaplanır** (iki hücrenin oranı) |
| Anlamı | "Asbest kanser olasılığını ×1.5 yapar" | "Öksürük görmek kanser odds'unu ×4.67 günceller" |

Yani **asbestin 1.5'i bir parametredir** (biz koyarız, kanserin tabanını yükseltir);
**öksürüğün 4.67'si bir sonuçtur** (CPT'den türetilir, kanıt gücüdür). Matematikte
ikisi de odds'u çarptığı için benzer görünür; kavramsal olarak biri "sebebin
etkisi", diğeri "kanıtın gücü"dür. (Ayrıntılı tablo: `proje_sorulari_cevaplari.md` §L.)

---

## 2. Neden "odds" (bahis oranı) kullanıyoruz?

Kanıtları birleştirirken olasılıkları **doğrudan çarpamayız**. Çünkü olasılık
%0–%100 arasına sıkışıktır; %10'u 20 ile çarparsak %200 çıkar — anlamsız.

Çözüm **odds**'tur. Odds, "olma / olmama" oranıdır:

```
odds = p / (1 − p)
```

- p = %20  → odds = 0.20/0.80 = 0.25  ("1'e 4")
- p = %50  → odds = 1       ("1'e 1")
- p = %80  → odds = 4       ("4'e 1")

Odds **0 ile sonsuz** arasında değer alır; serbestçe çarpabiliriz ve sonuç hep
geçerli bir olasılığa geri döner. Her kanıt parçası odds'u bir **çarpanla**
çarpar. Bu çarpana **olasılık oranı** (likelihood ratio, LR) denir.

Bu, Bayes kuralının en sade hâlidir:

```
sonraki_odds = önceki_odds × LR
```

### Odds ↔ olasılık dönüşüm tablosu (referans)

| Olasılık p | odds = p/(1−p) | yorum |
|---|---|---|
| %0.3 | 0.003 | çok düşük (odds ≈ p) |
| %1 | 0.0101 | |
| %5 | 0.0526 | "düşük" eşiği |
| %10 | 0.111 | |
| %15 | 0.176 | "yüksek" eşiği |
| %20 | 0.25 | |
| %50 | 1.00 | eşit ihtimal |
| %76 | 3.17 | |
| %90 | 9.00 | |

### Çarpan olasılığa değil, odds'a uygulanır — örnek (hemoptizi, LR = ×20)

3 adım: (1) p→odds, (2) odds×LR, (3) odds→p geri.

| Taban p | odds | ×20 | geri: p_yeni = odds/(1+odds) | Artış |
|---|---|---|---|---|
| %0.26 | 0.0026 | 0.052 | **%5.0** | +4.7 puan |
| %3.6 | 0.0373 | 0.747 | **%42.8** | +39 puan |
| %13.6 | 0.1574 | 3.148 | **%75.9** | +62 puan |

**Aynı ×20 çarpanı**, farklı tabanlarda farklı yüzde-puan üretir. Düşük p'de
odds ≈ p olduğu için ×20 "≈5 kat" gibi görünür; p büyüdükçe sonuç %100'e doğru
**bükülerek** yaklaşır ama asla geçmez. Bu bükülmeye **doygunluk (saturation)**
denir. (Olasılık eğrisi ortada dik, uçlarda düzdür.)

---

## 3. %56.1'lik örnek skor adım adım

Örnek hasta (rapor PRA-3C1DEB10): 55-59 erkek, aktif içici, ailede öykü +
mesleki risk + İzmir (orta hava); öksürük + göğüs ağrısı + yorgunluk **var**,
diğer 4 semptom **yok**.

1. **NLST tabanı** — P(kanser | 55-59, erkek, içici) = **%3.60** (odds 0.0373).
   *(Gerçek hayattan öğrenilmiş: 53.452 NLST katılımcısı.)*
2. **Yeni risk faktörleri** — odds'u çarp: ×1.70 (aile) ×1.50 (asbest) ×1.15
   (hava) → **%7.81** (odds 0.0847). Bu, "semptomlardan önceki" risk.
3. **Semptomlar** — her biri bir LR ile odds'u çarpar (sigara=1 verili):
   | Semptom | Durum | LR (odds çarpanı) | Etki |
   |---|---|---|---|
   | Öksürük | var | ×4.67 | ↑ |
   | Göğüs ağrısı | var | ×7.00 | ↑ |
   | Yorgunluk | var | ×2.50 | ↑ |
   | Nefes darlığı | yok | ×0.44 | ↓ |
   | Hırıltı | yok | ×0.75 | ↓ |
   | Hemoptizi | yok | ×0.81 | ↓ |
   | Kilo kaybı | yok | ×0.68 | ↓ |

   Net semptom çarpanı = 4.67×7.00×2.50×0.44×0.75×0.81×0.68 ≈ **×15.1**
4. **Sonuç:** 0.0847 × 15.1 = **1.279 odds** → 1.279/(1+1.279) = **%56.1**.

Yani: *taban (NLST) → risk faktörü çarpanları → semptom çarpanları → olasılığa
çevir.* Modelin "Variable Elimination" algoritması tam olarak bunu yapar.

---

## 4. Soru sırası sonucu değiştirir mi? — Hayır

Çarpma sıradan bağımsızdır (`a×b×c = c×b×a`), bu yüzden **nihai skor, soruların
sorulma sırasından bağımsızdır.** Aynı %56.1 örneğini 3 farklı sırada kurduk:

| Sıra | Ara adımlar | Sonuç |
|---|---|---|
| öksürük → göğüs → yorgunluk | 1.54 → 6.81 → 33.84 → **56.12** | %56.12 |
| yorgunluk → göğüs → öksürük | 1.54 → 3.77 → 21.51 → **56.12** | %56.12 |
| göğüs → öksürük → yorgunluk | 1.54 → 9.88 → 33.84 → **56.12** | %56.12 |

Üçü de **aynı yerde bitiyor**; yalnızca *ara adımlar* farklı. Ajanın soru sırası
da, semptomların "önceliği" de skoru etkilemez — o sıra yalnızca konuşma akışı
ve waterfall grafiği için bir tercihtir.

> Bu yüzden "şu semptom her zaman X puan ekler" demek yanlıştır. Bir bulgunun
> adil, sıra-bağımsız katkısı için **Shapley değeri** kullanılır (tüm sıraların
> ortalaması). Bkz. `docs/explainability_demo.md`.

---

## 5. Negatif kanıt: "yok" demek riski düşürür

- **Cevapsız (sorulmadı):** semptom marjinalize edilir, kanser olasılığını
  **hiç değiştirmez** (bilgi yok).
- **Açıkça "yok" (=0):** gerçek negatif bilgidir; LR < 1 ile odds'u **düşürür**
  (örn. hemoptizi yok → ×0.81).

Bu yüzden "her şey soruldu, hepsi temiz" diyen bir hasta, durumu bilinmeyen bir
hastadan daha düşük risk alır — bu **doğru** klinik davranıştır. Tarama aracında
güvenli ilke: net "hayır" → 0; emin olunmayan / "bilmiyorum" → nötr (gözlenmemiş)
bırak ki olmayan bir negatifi varmış gibi sayıp riski yapay düşürmeyelim.

---

## 6. Sunumda kullanılacak tek cümlelik özetler

- *"Skor basit bir toplama değil; Bayes kuralıyla odds çarpımıdır."*
- *"Her bulgu kanıt gücü kadar (odds çarpanı) etki eder; yüzde-puan etkisi ise
  hastanın tabanına göre değişir (doygunluk)."*
- *"Sıra önemli değil; nihai skor ve Shapley katkıları sıra-bağımsızdır."*
- *"Negatif yanıtlar da bilgidir ve riski düşürür — sistem tek yönlü değildir."*
- *"Taban gerçek klinik veriden (NLST, n=53.452) gelir; üstüne literatür temelli
  faktörler biner."*
