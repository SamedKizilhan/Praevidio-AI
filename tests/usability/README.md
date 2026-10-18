# Kullanılabilirlik testi protokolü (SUS-TR)

**Amaç.** Praevidio AI mobil uygulamasının (Flutter MVP) ne kadar kolay kullanıldığını standart bir ölçekle (SUS) ölçmek, kullanıcıların sonucu doğru anlayıp anlamadığını görmek ve düzeltilecek sorunları bulmak. Planlanan tarih: **18 Kasım – 4 Aralık 2026** (mobil uygulama tamamlandıktan sonra).

**Katılımcılar.** 5–8 gönüllü yetişkin; en az biri 50 yaş üstü (hedef kitle), en az biri teknolojiyle az haşır neşir. 5 katılımcı, kullanılabilirlik sorunlarının çoğunu ortaya çıkarmaya yeterlidir; SUS puanı bu örneklemde gösterge niteliğindedir.

**Etik ve gizlilik.** Katılımcılar **kendi sağlık bilgilerini vermez**; kendilerine verilen kurgusal bir vaka kartına göre cevap verir. Ad yerine katılımcı kodu (K1, K2…) kullanılır. Kurumun insan katılımcılı çalışmalar için onay gerektirip gerektirmediği danışmana sorulmalıdır.

## Akış (katılımcı başına ~20 dakika)

1. **Bilgilendirme ve onay (2 dk)** — aşağıdaki metin okunur, sözlü onay alınır.
2. **Vaka kartı (1 dk)** — katılımcıya kartlardan biri verilir.
3. **Görevler (10–12 dk)** — katılımcı görevleri yüksek sesle düşünerek yapar; gözlemci yardım etmez, yalnızca not alır.
4. **Anket (3 dk)** — `sus_tr_anket.md` (Bölüm 1 SUS-TR + Bölüm 2 ek sorular).
5. **Kısa görüşme (2 dk)** — açık uçlu sorular.

### Bilgilendirme metni

> Bu test, bir bitirme projesi olan Praevidio AI uygulamasının kullanım kolaylığını ölçmek içindir; sizi değil, uygulamayı test ediyoruz. Katılım gönüllüdür, istediğiniz an bırakabilirsiniz. Kendi sağlık bilgilerinizi vermeyeceksiniz; size vereceğimiz karttaki kişiymiş gibi cevap vereceksiniz. Konuşmalarınız yazıya çevrilmek üzere OpenAI'nin sunucularında işlenir; ses kayıtları test bitince silinir. Adınız hiçbir yerde kullanılmaz. Katılmayı kabul ediyor musunuz?

## Kurgusal vaka kartları

| Kart | Profil |
| --- | --- |
| **K-A** | 64 yaşında erkek, İzmir'de yaşıyor. Günde 1 paket, 35 yıldır sigara içiyor. 2 aydır geçmeyen öksürüğü var. Gençliğinde inşaatta çalışmış. Ailede kanser yok. KOAH tanısı yok. |
| **K-B** | 57 yaşında kadın, Ankara'da yaşıyor. Günde yarım paket, 20 yıl içmiş; 10 yıl önce bırakmış. Şikâyeti yok. Annesinde akciğer kanseri olmuş. |
| **K-C** | 45 yaşında erkek, Konya'da yaşıyor. Hiç sigara içmemiş. Son zamanlarda halsiz. Kilo kaybı sorulursa "bilmiyorum" der. |
| **K-D** | 70 yaşında kadın, Iğdır'da yaşıyor. Günde 2 paket, 20 yıldır içiyor. Bir kez kan tükürmüş, nefes darlığı var. Doktoru KOAH demiş. |

## Görevler

| # | Görev | Başarı ölçütü |
| --- | --- | --- |
| G1 | Uygulamayı açın ve sesli değerlendirmeyi kartınıza göre baştan sona tamamlayın. | Sonuç ekranına yardımsız ulaşıldı |
| G2 | Uygulama yaşınızı tekrar ettiğinde yanlış anlaşıldığını varsayın ve düzeltin. | Düzeltilen yaş özete yansıdı |
| G3 | Bilmediğiniz bir soruya "bilmiyorum" deyin. | Soru tekrarlanmadan geçildi |
| G4 | Sonuç ekranında risk düzeyinizi ve size önerilen adımı bulun; ne anlama geldiğini kendi cümlenizle anlatın. | Öneri doğru aktarıldı (ör. "tarama için KETEM'e gitmeliyim") |
| G5 | Raporunuzu açın ve paylaşma seçeneğini bulun. | Rapor açıldı, paylaş menüsü bulundu |
| G6 | Size en yakın KETEM'i bulun. | Haritada en yakın merkez gösterildi |

*G5 ve G6 rapor ekranı ve KETEM haritası tamamlandıktan sonra eklenir.*

## Gözlem formu (her katılımcı için)

| Görev | Sonuç (Yardımsız ✓ / Yardımla ~ / Başarısız ✗) | Süre (dk) | Hata / takılma notu |
| --- | --- | --- | --- |
| G1 | | | |
| G2 | | | |
| G3 | | | |
| G4 | | | |
| G5 | | | |
| G6 | | | |

## Puanlama ve raporlama

Cevaplar `sus_cevaplari.csv`'ye girilir, ardından `make sus` çalıştırılır. Skor: tek numaralı maddelerde (puan − 1), çift numaralılarda (5 − puan); toplam × 2,5 → 0–100. Ortalama, standart sapma, %95 güven aralığı ve Sauro & Lewis eğri not ölçeği (68 ≈ ortalama, C) raporlanır: `sus_sonuclari.md`.

**Kaynaklar.** Brooke J. (1996). SUS: a "quick and dirty" usability scale. *Usability Evaluation in Industry*, 189–194. · Demirkol D., Şeneler Ç. (2018). SUS-TR. *Uşak Üniv. Sosyal Bilimler Dergisi*, 11(3), 237–253. · Sauro J., Lewis J.R. (2016). *Quantifying the User Experience*, 2nd ed. Morgan Kaufmann.
