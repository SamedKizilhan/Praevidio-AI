# Belirti katmanı — tasarım notu (4 Kasım 2026)

## Sorun
v3.1'de tam skor (risk etkenleri + belirtiler) 6 yıllık katmanla **aynı bantlarla** (Düşük < %1,5 · Orta %1,5–5 ·
Yüksek ≥ %5) etiketleniyordu. Bu bantların alt sınırı PLCOm2012'nin **tarama** eşiğidir (belirtisiz kişide düşük doz
BT). Tam skor ise iki farklı sorunun toplamıdır: önümüzdeki 6 yılda ortaya çıkacak belirtisiz kanser (tarama) ve
bugünkü belirtilere yol açan kanser (tanı/sevk). Sonuç: belirtisiz 62 yaş içici "Orta" (%1,5) görünürken, 35 yaşında
7 belirtili kadının %14,4'ünün %14,2'si bugünkü belirtilerden geliyordu ve iki durum aynı etiket dilini kullanıyordu.

## Çözüm
* **6 yıllık katman** (tarama sorusu) değişmedi: sayı, bantlar, %1,5 eşiği.
* **Belirti katmanı** (sevk sorusu): `P(şu an belirti veren akciğer kanseri | kanıt) = P(LC | kanıt) · P(SEMPTOMATİK | LC, kanıt)`.
  İkinci çarpan taban riskten bağımsızdır (NLST / PLCOm2012 / Wakelee ile aynı pay — test edildi).
  * `none`: belirti bildirilmedi · `low`: < eşik → "birkaç haftadır sürüyorsa aile hekiminize" · `elevated`: ≥ eşik → kısa sürede hekim.
  * **Eşik %3** = NICE NG12'nin birinci basamak sevk ölçütü (PPV %3; NICE'ın açıkça belirttiği bir değer yargısı).
    `PRAEVIDIO_SYMPTOM_REFERRAL_PPV` ile değiştirilebilir. Model değeri ölçülmüş bir PPV değildir.
* **Kısa sürede hekim** = NICE NG12 kuralı (≥40 yaş) **ya da** belirti katmanı `elevated` **ya da** hemoptizi (her yaşta;
  enfeksiyon, tüberküloz gibi kanser dışı nedenleri için de beklenmemeli — kanser şüphesi diliyle sunulmaz).
* **Tam skor** bantlanmaz; raporda "karma ufuk, ek bilgi" olarak sayıyla kalır.

## Doğrulama (`tests/model/test_symptom_layer.py`)
62 yaş, 40 paket-yıl, tek belirti + diğer 6 "hayır": hemoptizi %7,7 (Hamilton 2005: genel %2,4, 70+ yaş %7,1, sigara
içende ~2 kat); göğüs ağrısı/kilo kaybı %2,5; öksürük %0,3 — hemoptizi dışındaki tek belirtiler < %4 (Hamilton < %2 ×
sigara ~2). Hiç içmemişte tek belirtilerin hiçbiri eşiği aşmaz. 35 yaş kadın, tüm etkenler, 7 belirti: %14,2 → kısa
sürede hekim (NICE kuralı yaş nedeniyle tetiklenmez). 30 yaş hiç içmemiş, yalnız hemoptizi: kanser olasılığı %0,04
(dürüst sayı) ama hemoptizi kuralıyla kısa sürede hekim.

## Açık konular (uzman görüşmesinde sorulacak)
* Türkiye için eşik: %3 mü, daha düşük mü (göğüs röntgeni/uzman erişimi kolay)?
* PLCOm2012'nin 50 yaş altına uzatılması genç kişilerde belirti katmanını da yükseltebilir.
* Kullanıcı ekranında belirti katmanının **sayısı gösterilmiyor** (yalnız mesaj); sayı hekim raporunda yer alıyor.
