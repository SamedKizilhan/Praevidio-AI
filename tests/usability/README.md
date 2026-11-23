# Usability test protocol (SUS-TR)

*English first; the Turkish original, including the texts that are read to participants, follows below.*

**Purpose.** To measure how easy the Praevidio AI mobile web app (an installable PWA) is to use with a standard scale (SUS), to see whether users understand the result correctly, and to find problems to fix. Planned dates: **18 November – 4 December 2026**, after the phone trials.

**Participants.** Five to eight adult volunteers; at least one over 50 (the target group) and at least one with little experience of technology. Five participants are enough to reveal most usability problems; with a sample of this size the SUS score is indicative only.

**Ethics and privacy.** Participants **do not give their own health information**; they answer as the fictional person on a case card. A participant code (K1, K2, …) is used instead of a name.

## Procedure (about 20 minutes per participant)

1. **Information and consent (2 min).** The information text is read aloud and verbal consent is obtained.
2. **Case card (1 min).** The participant receives one of the cards.
3. **Tasks (10–12 min).** The participant performs the tasks while thinking aloud; the observer does not help and only takes notes.
4. **Questionnaire (3 min).** [`sus_tr_questionnaire.md`](sus_tr_questionnaire.md): Part 1 is SUS-TR, Part 2 has four app-specific questions.
5. **Short interview (2 min).** Open questions.

The information text tells participants that the app is being tested and not they themselves, that taking part is voluntary and can be stopped at any time, that they will answer as the person on the card and not with their own health information, that their speech is processed on OpenAI's servers for transcription and the recordings are deleted after the test, and that their name is not used anywhere. The Turkish wording is in the Turkish section.

## Fictional case cards

| Card | Profile |
| --- | --- |
| **K-A** | Man, 64, lives in Izmir. One pack a day for 35 years. A cough that has not gone away for two months. Worked in construction when young. No cancer in the family, no COPD diagnosis. |
| **K-B** | Woman, 57, lives in Ankara. Half a pack a day for 20 years; quit 10 years ago. No complaints. Her mother had lung cancer. |
| **K-C** | Man, 45, lives in Konya. Never smoked. Tired lately. Answers "I don't know" if asked about weight loss. |
| **K-D** | Woman, 70, lives in Iğdır. Two packs a day for 20 years. Coughed up blood once, short of breath. Her doctor has diagnosed COPD. |

## Tasks

| # | Task | Success criterion |
| --- | --- | --- |
| G1 | Open the app and complete the voice assessment from start to finish as the person on your card. | The result screen is reached without help |
| G2 | When the app repeats your age, assume it was misheard and correct it. | The corrected age appears in the summary |
| G3 | Answer "I don't know" to a question you cannot answer. | The interview moves on without repeating the question |
| G4 | On the result screen, find your risk level and the step recommended to you; explain in your own words what it means. | The advice is reported correctly (for example "I should go to a KETEM for screening") |
| G5 | Open your report and find the option to share it. | The report opens and the share menu is found |
| G6 | Find the KETEM (cancer screening centre) nearest to you. | The nearest centre is shown on the map |

*G5 and G6 are added once the report screen and the KETEM map are finished.*

For every participant the observer records, per task, the outcome (unaided ✓, with help ~, failed ✗), the time in minutes and any error or hesitation.

## Scoring and reporting

Answers are entered in `sus_answers.csv` and `make sus` is run. Scoring: odd-numbered items contribute (answer − 1), even-numbered items (5 − answer); the sum times 2.5 gives 0–100. The mean, standard deviation, 95 % confidence interval and the curved grading scale of Sauro and Lewis (68 is about average, grade C) are written to [`sus_results.md`](sus_results.md).

**References.** Brooke J. (1996). SUS: a "quick and dirty" usability scale. *Usability Evaluation in Industry*, 189–194. · Demirkol D., Şeneler Ç. (2018). A Turkish translation of the System Usability Scale: the SUS-TR. *Uşak Üniversitesi Sosyal Bilimler Dergisi*, 11(3), 237–253. · Sauro J., Lewis J.R. (2016). *Quantifying the User Experience*, 2nd ed. Morgan Kaufmann.

---

## Türkçe: Kullanılabilirlik testi protokolü (SUS-TR)

**Amaç.** Praevidio AI mobil web uygulamasının (telefona kurulabilen PWA) ne kadar kolay kullanıldığını standart bir ölçekle (SUS) ölçmek, kullanıcıların sonucu doğru anlayıp anlamadığını görmek ve düzeltilecek sorunları bulmak. Planlanan tarih: **18 Kasım – 4 Aralık 2026** (telefon denemeleri tamamlandıktan sonra).

**Katılımcılar.** 5–8 gönüllü yetişkin; en az biri 50 yaş üstü (hedef kitle), en az biri teknolojiyle az haşır neşir. 5 katılımcı, kullanılabilirlik sorunlarının çoğunu ortaya çıkarmaya yeterlidir; SUS puanı bu örneklemde gösterge niteliğindedir.

**Etik ve gizlilik.** Katılımcılar **kendi sağlık bilgilerini vermez**; kendilerine verilen kurgusal bir vaka kartına göre cevap verir. Ad yerine katılımcı kodu (K1, K2…) kullanılır.

### Akış (katılımcı başına ~20 dakika)

1. **Bilgilendirme ve onay (2 dk)** — aşağıdaki metin okunur, sözlü onay alınır.
2. **Vaka kartı (1 dk)** — katılımcıya kartlardan biri verilir.
3. **Görevler (10–12 dk)** — katılımcı görevleri yüksek sesle düşünerek yapar; gözlemci yardım etmez, yalnızca not alır.
4. **Anket (3 dk)** — `sus_tr_questionnaire.md` (Bölüm 1 SUS-TR + Bölüm 2 ek sorular).
5. **Kısa görüşme (2 dk)** — açık uçlu sorular.

#### Bilgilendirme metni

> Bu test, bir bitirme projesi olan Praevidio AI uygulamasının kullanım kolaylığını ölçmek içindir; sizi değil, uygulamayı test ediyoruz. Katılım gönüllüdür, istediğiniz an bırakabilirsiniz. Kendi sağlık bilgilerinizi vermeyeceksiniz; size vereceğimiz karttaki kişiymiş gibi cevap vereceksiniz. Konuşmalarınız yazıya çevrilmek üzere OpenAI'nin sunucularında işlenir; ses kayıtları test bitince silinir. Adınız hiçbir yerde kullanılmaz. Katılmayı kabul ediyor musunuz?

### Kurgusal vaka kartları

| Kart | Profil |
| --- | --- |
| **K-A** | 64 yaşında erkek, İzmir'de yaşıyor. Günde 1 paket, 35 yıldır sigara içiyor. 2 aydır geçmeyen öksürüğü var. Gençliğinde inşaatta çalışmış. Ailede kanser yok. KOAH tanısı yok. |
| **K-B** | 57 yaşında kadın, Ankara'da yaşıyor. Günde yarım paket, 20 yıl içmiş; 10 yıl önce bırakmış. Şikâyeti yok. Annesinde akciğer kanseri olmuş. |
| **K-C** | 45 yaşında erkek, Konya'da yaşıyor. Hiç sigara içmemiş. Son zamanlarda halsiz. Kilo kaybı sorulursa "bilmiyorum" der. |
| **K-D** | 70 yaşında kadın, Iğdır'da yaşıyor. Günde 2 paket, 20 yıldır içiyor. Bir kez kan tükürmüş, nefes darlığı var. Doktoru KOAH demiş. |

### Görevler

| # | Görev | Başarı ölçütü |
| --- | --- | --- |
| G1 | Uygulamayı açın ve sesli değerlendirmeyi kartınıza göre baştan sona tamamlayın. | Sonuç ekranına yardımsız ulaşıldı |
| G2 | Uygulama yaşınızı tekrar ettiğinde yanlış anlaşıldığını varsayın ve düzeltin. | Düzeltilen yaş özete yansıdı |
| G3 | Bilmediğiniz bir soruya "bilmiyorum" deyin. | Soru tekrarlanmadan geçildi |
| G4 | Sonuç ekranında risk düzeyinizi ve size önerilen adımı bulun; ne anlama geldiğini kendi cümlenizle anlatın. | Öneri doğru aktarıldı (ör. "tarama için KETEM'e gitmeliyim") |
| G5 | Raporunuzu açın ve paylaşma seçeneğini bulun. | Rapor açıldı, paylaş menüsü bulundu |
| G6 | Size en yakın KETEM'i bulun. | Haritada en yakın merkez gösterildi |

*G5 ve G6 rapor ekranı ve KETEM haritası tamamlandıktan sonra eklenir.*

### Gözlem formu (her katılımcı için)

| Görev | Sonuç (Yardımsız ✓ / Yardımla ~ / Başarısız ✗) | Süre (dk) | Hata / takılma notu |
| --- | --- | --- | --- |
| G1 | | | |
| G2 | | | |
| G3 | | | |
| G4 | | | |
| G5 | | | |
| G6 | | | |

### Puanlama ve raporlama

Cevaplar `sus_answers.csv`'ye girilir, ardından `make sus` çalıştırılır. Skor: tek numaralı maddelerde (puan − 1), çift numaralılarda (5 − puan); toplam × 2,5 → 0–100. Ortalama, standart sapma, %95 güven aralığı ve Sauro & Lewis eğri not ölçeği (68 ≈ ortalama, C) raporlanır: `sus_results.md`.

**Kaynaklar.** Brooke J. (1996). SUS: a "quick and dirty" usability scale. *Usability Evaluation in Industry*, 189–194. · Demirkol D., Şeneler Ç. (2018). SUS-TR. *Uşak Üniv. Sosyal Bilimler Dergisi*, 11(3), 237–253. · Sauro J., Lewis J.R. (2016). *Quantifying the User Experience*, 2nd ed. Morgan Kaufmann.
