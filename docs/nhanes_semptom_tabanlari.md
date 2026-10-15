# NHANES ile kansersiz semptom tabanları (v3 doğrulaması)

*NHANES 2007-2012 (E,F,G), age ≥40, no self-reported cancer, WTINT2YR/3 weighted. n(40+)=11763, kansersiz n=10203, öz-bildirim akciğer kanseri (40+) n=37 — kanser sütunu için yetersiz; yalnız KANSERSİZ tabanlar kullanılır.*

| Semptom (NHANES tanımı) | Sigara | NHANES % (n) | 40-54 | 55-64 | 65+ | v3'ün ima ettiği % (kanser yok) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Kronik öksürük (çoğu gün ≥3 ay) | never | 5.7 (5294) | 3.9 | 7.8 | 7.6 | 10.0 |
| Kronik öksürük (çoğu gün ≥3 ay) | former | 9.2 (2915) | 7.3 | 7.3 | 13.1 | 16.5 |
| Kronik öksürük (çoğu gün ≥3 ay) | current | 25.1 (1984) | 24.2 | 23.2 | 34.6 | 30.3 |
| Balgam (çoğu gün ≥3 ay) | never | 4.4 (5295) | 2.9 | 5.1 | 6.9 | — |
| Balgam (çoğu gün ≥3 ay) | former | 8.1 (2916) | 7.0 | 6.0 | 11.0 | — |
| Balgam (çoğu gün ≥3 ay) | current | 18.8 (1986) | 15.9 | 23.6 | 24.5 | — |
| Hırıltı/ıslık (son 12 ay) | never | 8.4 (5299) | 8.4 | 9.0 | 7.6 | 8.0 |
| Hırıltı/ıslık (son 12 ay) | former | 14.4 (2911) | 16.1 | 11.7 | 14.6 | 14.1 |
| Hırıltı/ıslık (son 12 ay) | current | 27.2 (1986) | 27.3 | 28.5 | 23.8 | 26.3 |

## Yorum

- NHANES 'kronik öksürük' (çoğu gün, ≥3 ay) tanımı ajanın 'geçmeyen öksürük' sorusundan daha dardır; bu yüzden NHANES oranlarının model değerlerinin biraz altında kalması beklenir. **Kalibrasyon (16 Ekim 2026):** hırıltı tabanları ilk v3'te ~1,8× düşüktü, `leak/smoke/copd` NHANES'e göre güncellendi (hiç %8, eski %14, aktif %26); öksürükte hiç/eski tabanlar korundu, aktif içici katkısı NHANES oranı doğrultusunda artırıldı (→ ~%30).
- Yaş etkisi: 65+ grubunda kronik öksürük/balgam belirgin yüksek (aktif içicide %35); modelde semptomlar yaşa bağlı değil — ileride AGE → solunum semptomu kenarı değerlendirilebilir.
- Öz-bildirim akciğer kanseri (40+) yalnız 37 kişi (sağ kalanlar); kanser sütunu için kullanılamaz.
- Hırıltı için NHANES 12 aylık pencere kullanır; v3 'solunumda hırıltı oluyor mu' sorusuyla yakın.
- Nefes darlığı NHANES RDQ'da bu döngülerde yoktur; literatür değeri korunur.
- Sigara etkisi (current/never oranı) v3'teki KOAH-aracılı mekanizmanın büyüklüğünü sınar: NHANES'te current/never oranı v3'ünkinden büyükse `smoke` ya da `copd` katkısı artırılmalıdır.
