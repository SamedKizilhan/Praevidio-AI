# Praevidio AI — Terimler Sözlüğü

Projede geçen teknik ve klinik terimlerin kısa açıklaması ve **bizim nasıl kullandığımız**.

---

## Klinik / Epidemiyolojik

**LDCT (Low-Dose Computed Tomography / Düşük Doz Bilgisayarlı Tomografi)**
Akciğer kanseri taramasının altın standardı olan düşük radyasyon dozlu BT. NLST,
LDCT taramasının yüksek-riskli kişilerde ölümü azalttığını göstermiştir.
*Bizde:* Hedef çıktı — yüksek risk veya tarama-uygunluğu durumunda kullanıcıyı
LDCT için hekime/ KETEM'e yönlendiriyoruz.

**NLST (National Lung Screening Trial)**
ABD'de yürütülen, 53.452 katılımcılı büyük klinik tarama denemesi. Katılımcıların
tamamı yüksek riskli (yaş 55-74, ≥30 paket-yıl, halen/yakın zamanda içici).
*Bizde:* Risk faktörü temelini (yaş, cinsiyet, sigara → kanser olasılığı)
gerçek NLST verisinden öğreniyoruz. **Önemli kısıt:** NLST'de hiç-içmeyen ve
<55 yaş yok; bu yüzden o gruplar için epidemiyolojik tahminler kullanıyoruz.

**ASR (Age-Standardized Rate / Yaşa Standardize Hız)**
Farklı yaş dağılımlı toplulukları adil kıyaslamak için yaşa göre düzeltilmiş
insidans/mortalite hızı (genelde /100.000). *Bizde:* Motivasyonda Türkiye'de
akciğer kanseri yükünü belirtmek için kullanıyoruz (erkeklerde ASR ~68/100.000).

**Paket-yıl (pack-year)**
Kümülatif sigara dozu = (günde içilen sigara / 20) × içilen yıl. Örn. günde 1
paket × 30 yıl = 30 paket-yıl. *Bizde:* (1) tarama uygunluğu kriteri (≥20 py),
(2) risk skorunda sigara düzeltmesi (hiç-içmeyeni düşür, ağır+yakın eski içiciyi
aktif gibi değerlendir).

**Hemoptizi**
Öksürükle kan/kanlı balgam çıkarma. Akciğer kanserinin en özgül (alarm)
semptomlarından. *Bizde:* En güçlü pozitif semptom (olasılık oranı ≈ ×20).

**KETEM**
Kanser Erken Teşhis, Tarama ve Eğitim Merkezi (T.C. Sağlık Bakanlığı).
*Bizde:* Yüksek risk/ tarama adaylarını yönlendirdiğimiz adres.

---

## Kodlama Standartları

**ICD-10 (International Classification of Diseases, 10. revizyon)**
Hastalık ve semptomların uluslararası standart kodları (örn. R05 = öksürük,
C34 = bronş/akciğer malign neoplazmı). *Bizde:* Her semptom ve bulguyu ICD-10'a
eşleyip "doktora hazır" rapor üretiyoruz; RAG ile metinden koda eşleme yapıyoruz.

**ICD-O-3 (ICD for Oncology, 3. revizyon)**
Onkolojiye özgü, tümörün topografisi (yeri) ve morfolojisi (hücre tipi) için
kodlama. *Bizde:* Onkolojik standart uyumu için referans alıyoruz (raporun
klinik geçerliliği). Risk skorunda doğrudan kullanılmaz.

---

## Modelleme

**BBN (Bayesian Belief Network / Bayesçi İnanç Ağı)**
Değişkenler arası nedensel ilişkileri yönlü oklarla ve koşullu olasılıklarla
gösteren olasılıksal grafik model. Kanıt verildiğinde Bayes kuralıyla
"sonuç olasılığı" hesaplar. *Bizde:* Çekirdek motor. Yapı: risk faktörleri →
KANSER → semptomlar. Kanser düğümü gizli; biz P(kanser | kanıtlar)'ı hesaplıyoruz.
Avantajı: kara kutu değil — her ilişki açıklanabilir.

**CPT (Conditional Probability Table / Koşullu Olasılık Tablosu)**
Bir düğümün, ebeveynlerinin her durumu için olasılık değerlerini tutan tablo
(örn. P(öksürük | kanser, sigara)). *Bizde:* Risk faktörü CPT'leri NLST verisinden
öğrenildi; semptom CPT'leri peer-review literatürden uzman-elicitation ile türetildi.

**Odds (bahis oranı)**
"Olma / olmama" oranı: odds = p / (1 − p). 0 ile sonsuz arası değer alır,
serbestçe çarpılabilir. *Bizde:* Kanıtları birleştirmenin matematiksel temeli;
olasılık doğrudan çarpılamadığı için odds üzerinden çarpıyoruz.

**Odds Ratio (OR) / Olasılık Oranı (Likelihood Ratio, LR)**
Bir faktörün/bulgunun odds'u kaç katına çıkardığı. OR genelde risk faktörleri
(örn. aile öyküsü OR≈1.70), LR genelde tanısal bulgular için kullanılır.
*Bizde:* Yeni risk faktörlerini (aile, asbest, hava) literatür OR'larıyla NLST
tabanına çarparak entegre ettik; her semptomun LR'ı odds'u günceller.

**Generative (üretici) yapı / Naive Bayes yönü**
Hastalık → semptom yönünde modelleme ("kanser varsa öksürük olasılığı şudur").
*Bizde:* Tıbbi BBN standardı; tanıda Bayes ile tersine yürüyoruz.

**Explaining-away (açıklayıp-götürme)**
Bir semptomun iki nedeni varken, birini gözlemenin diğerinin olasılığını
düşürmesi. *Bizde:* Sigara hem kansere hem öksürüğe sebep olduğundan, içicide
öksürük "sigarayla açıklanıp" kanseri yanlışlıkla düşürebiliyordu; duyarlılık
analiziyle CPT'leri kalibre edip bunu düzelttik. (Yeni 3 faktörde bu sorun
yok — onlar semptoma değil yalnızca kansere bağlı.)

**Shapley değeri**
Oyun teorisinden gelen, her faktöre **sıra-bağımsız adil katkı** atayan yöntem;
tüm faktör sıralarının ortalaması alınır. *Bizde:* "Bu hastanın skoruna hangi
faktör ne kadar katkı yaptı?" sorusunu adilce yanıtlamak için (açıklanabilirlik).

**Kalibrasyon (calibration)**
Tahmin edilen olasılığın gerçek frekansla uyumu ("%15 dediğimizde gerçekten
~%15 mi?"). *Bizde:* Tanı değil kalibre risk ürettiğimiz için birincil hedef.

---

## Performans Metrikleri (F1 yerine)

> Neden F1 değil? Amaç tanı (ikili sınıf) değil, **kalibre risk**. F1 sürekli
> olasılığı zorla eşikler ve %3.85 taban dengesizliğinde yanıltıcıdır.

**AUC-ROC (Area Under the ROC Curve)**
Ayrım gücü: modelin riskli olanı risksizden **yüksek sıralama** yeteneği.
0.5=şans, 1.0=mükemmel. Eşikten bağımsız. *Bizde:* Birincil ayrım metriği.

**AUPRC / PR-AUC (Area Under Precision-Recall Curve)**
Dengesiz veride AUC-ROC'tan daha bilgilendirici ayrım metriği (pozitif sınıfa
odaklı). *Bizde:* Taban prevalans %3.85 olduğu için AUC-ROC'un yanında raporlanır.

**Brier skoru**
Olasılık tahmininin ortalama karesel hatası (0=mükemmel, düşük=iyi). Hem ayrım
hem kalibrasyonu özetler. *Bizde:* Kalibrasyonun tek-sayı özeti.

**ECE (Expected Calibration Error)**
Tahmin edilen olasılık ile gözlenen frekans arasındaki ağırlıklı ortalama fark.
*Bizde:* Kalibrasyon eğrisini tek sayıya indirger.

**Reliability curve (kalibrasyon/güvenilirlik eğrisi)**
x: tahmin edilen risk, y: gözlenen frekans. İdeal = 45° çizgi. *Bizde:* Modelin
sistematik olarak fazla/eksik güvenli olup olmadığını görselleştirir.

**DCA (Decision Curve Analysis) / Net Fayda**
"Bu skoru kullanmak, herkesi tara / kimseyi tarama'ya kıyasla net fayda sağlıyor
mu?" Tarama araçları için modern klinik fayda standardı. *Bizde:* Eşik seçimini
ve klinik değeri gerekçelendirmek için.

**Duyarlılık / Özgüllük (sensitivity / specificity)**
Duyarlılık = gerçek pozitifleri yakalama; özgüllük = gerçek negatifleri dışlama.
*Bizde:* Seçilen eşiklerde (%5, %15) operasyon noktası olarak raporlanır;
tarama amacı gereği duyarlılık önceliklendirilir.
