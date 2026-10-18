# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI - SUS-TR puanlama
==============================
sus_cevaplari.csv → katılımcı başına SUS (0-100), ortalama, SS, %95 GA,
Sauro & Lewis (2016) eğri not ölçeği, ek soruların (E1-E4) ortalaması ve
görev başarı oranları. Çıktı: tests/usability/sus_sonuclari.md

CSV sütunları: katilimci, yas_grubu, kart, s1..s10 (1-5), e1..e4 (1-5),
               g1..g6 (✓ / ~ / ✗ ya da 1 / 0.5 / 0; boş = uygulanmadı)
Çalıştırma: python tests/usability/score_sus.py   (veya: make sus)
"""
import csv
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "sus_cevaplari.csv"
OUT = HERE / "sus_sonuclari.md"

# Sauro & Lewis (2016) eğri not ölçeği (alt sınırlar)
GRADES = [(84.1, "A+"), (80.8, "A"), (78.9, "A−"), (77.2, "B+"), (74.1, "B"), (72.6, "B−"),
          (71.1, "C+"), (65.0, "C"), (62.7, "C−"), (51.7, "D"), (0.0, "F")]
# İki yönlü t kritik değerleri (%95), sd = n-1
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
       9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131}
TASK = {"✓": 1.0, "1": 1.0, "~": 0.5, "0.5": 0.5, "✗": 0.0, "x": 0.0, "0": 0.0}


def sus_score(items):
    """items: 10 adet 1-5 puan → 0-100."""
    if len(items) != 10 or any(not 1 <= v <= 5 for v in items):
        raise ValueError("SUS için 1-5 arası 10 cevap gerekir")
    odd = sum(items[i] - 1 for i in range(0, 10, 2))
    even = sum(5 - items[i] for i in range(1, 10, 2))
    return (odd + even) * 2.5


def grade(score):
    return next(g for lim, g in GRADES if score >= lim)


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    rows = [r for r in rows if (r.get("s1") or "").strip()]
    if not rows:
        sys.exit(f"{CSV.name} boş — katılımcı cevaplarını girin.")
    scores, per = [], []
    for r in rows:
        s = sus_score([int(r[f"s{i}"]) for i in range(1, 11)])
        scores.append(s)
        per.append((r["katilimci"], r.get("yas_grubu", ""), r.get("kart", ""), s))
    n = len(scores)
    mean = sum(scores) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in scores) / (n - 1)) if n > 1 else 0.0
    half = T95.get(n - 1, 1.96) * sd / math.sqrt(n) if n > 1 else float("nan")

    def avg(col):
        v = [float(r[col]) for r in rows if (r.get(col) or "").strip()]
        return (sum(v) / len(v), len(v)) if v else (None, 0)

    L = ["# SUS-TR sonuçları", "", f"*n = {n}. Otomatik üretildi: `make sus`.*", "",
         "| Ölçüt | Değer |", "| --- | --- |",
         f"| Ortalama SUS | **{mean:.1f}** (not: {grade(mean)}) |",
         f"| Standart sapma | {sd:.1f} |",
         f"| %95 güven aralığı | {max(0.0, mean - half):.1f} – {min(100.0, mean + half):.1f} |" if n > 1 else "| %95 güven aralığı | — |",
         f"| En düşük / en yüksek | {min(scores):.1f} / {max(scores):.1f} |", "",
         "*Yorum: 68 ≈ ortalama (C); ≥ 80,8 'A'. Küçük örneklemde güven aralığı geniştir, sonuç gösterge niteliğindedir.*",
         "", "## Katılımcılar", "", "| Kod | Yaş grubu | Kart | SUS | Not |", "| --- | --- | --- | ---: | :---: |"]
    L += [f"| {k} | {a} | {c} | {s:.1f} | {grade(s)} |" for k, a, c, s in per]
    L += ["", "## Ek sorular (1–5, SUS'a dahil değil)", "", "| Soru | Ortalama | n |", "| --- | ---: | ---: |"]
    labels = {"e1": "Sonucu ve öneriyi anladım", "e2": "Sonuç gereksiz endişelendirmedi",
              "e3": "Sesli konuşma doğal geldi", "e4": "Uygulama beni doğru anladı"}
    for c, lbl in labels.items():
        m, k = avg(c)
        L.append(f"| {lbl} | {'—' if m is None else f'{m:.1f}'} | {k} |")
    L += ["", "## Görev başarısı", "", "| Görev | Başarı (yardımsız = 1, yardımla = 0,5) | n |", "| --- | ---: | ---: |"]
    for g in ("g1", "g2", "g3", "g4", "g5", "g6"):
        v = [TASK[r[g].strip()] for r in rows if (r.get(g) or "").strip() in TASK]
        L.append(f"| {g.upper()} | {'—' if not v else f'%{100*sum(v)/len(v):.0f}'} | {len(v)} |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))
    print(f"\n📄 {OUT}")


if __name__ == "__main__":
    main()
