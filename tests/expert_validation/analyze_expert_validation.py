# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI - Uzman Doğrulama Analizi
======================================
uzman_cevaplari.csv (uzmanın 6 yıllık risk % ve A/B/C eylem tahminleri) ile
model_sonuclari.json (v2 / v3 cevap anahtarı) karşılaştırılır:

  • Eylem uyumu   : tam eşleşme %, ağırlıklı (doğrusal) Cohen kappa (A < B < C sıralı)
  • Risk uyumu    : Spearman sıra korelasyonu (uzman % ↔ model %), medyan oran (model / uzman)
  • Vaka tablosu  : uyuşmayan vakalar işaretli

Çıktı: tests/expert_validation/uzman_karsilastirma.md
Çalıştırma: python tests/expert_validation/analyze_expert_validation.py   (veya: make expert-analyze)
"""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
ANSWERS = HERE / "uzman_cevaplari.csv"
KEY = HERE / "model_sonuclari.json"
OUT = HERE / "uzman_karsilastirma.md"
ORD = {"A": 0, "B": 1, "C": 2}


def weighted_kappa(a, b, k=3):
    """Doğrusal ağırlıklı Cohen kappa (sıralı kategoriler 0..k-1)."""
    n = len(a)
    if n == 0:
        return float("nan")
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x][y] += 1
    ra = [sum(obs[i]) / n for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]
    w = [[abs(i - j) / (k - 1) for j in range(k)] for i in range(k)]
    po = sum(w[i][j] * obs[i][j] / n for i in range(k) for j in range(k))
    pe = sum(w[i][j] * ra[i] * rb[j] for i in range(k) for j in range(k))
    return float("nan") if pe == 0 else 1 - po / pe


def _ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for t in range(i, j + 1):
            r[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    if len(x) < 3:
        return float("nan")
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return float("nan") if den == 0 else num / den


def median(v):
    v = sorted(v)
    n = len(v)
    return float("nan") if n == 0 else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def main():
    if not KEY.exists():
        sys.exit("Önce cevap anahtarını üretin: make expert")
    key = {r["id"]: r for r in json.loads(KEY.read_text(encoding="utf-8"))}
    exp = {}
    with open(ANSWERS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            act = (row.get("uzman_eylem") or "").strip().upper()
            pct = (row.get("uzman_risk_6y_yuzde") or "").strip().replace(",", ".").replace("%", "")
            if act in ORD or pct:
                exp[row["id"].strip()] = {"act": act if act in ORD else None,
                                          "pct": float(pct) if pct else None,
                                          "note": (row.get("not") or "").strip()}
    if not exp:
        sys.exit(f"{ANSWERS.name} boş — uzmanın cevaplarını girin (id, uzman_risk_6y_yuzde, uzman_eylem A/B/C, not).")

    ids = [i for i in key if i in exp]
    L = ["# Uzman ile model karşılaştırması", "",
         f"*{len(ids)} vaka. Otomatik üretildi: `make expert-analyze`.*", "",
         "## Özet", "",
         "| Ölçüt | v2 | v3 (6y faktör / tam skor) |", "| --- | ---: | ---: |"]
    summary = {}
    for m in ("v2", "v3"):
        a_ids = [i for i in ids if exp[i]["act"]]
        ea = [ORD[exp[i]["act"]] for i in a_ids]
        ma = [ORD[key[i][f"{m}_action"]] for i in a_ids]
        exact = sum(x == y for x, y in zip(ea, ma)) / len(a_ids) if a_ids else float("nan")
        within1 = sum(abs(x - y) <= 1 for x, y in zip(ea, ma)) / len(a_ids) if a_ids else float("nan")
        p_ids = [i for i in ids if exp[i]["pct"] is not None]
        ep = [exp[i]["pct"] for i in p_ids]
        cols = [f"{m}_score"] if m == "v2" else ["v3_6y", "v3_score"]
        sp = [spearman(ep, [key[i][c] for i in p_ids]) for c in cols]
        ratio = [median([max(key[i][c], 0.01) / max(exp[i]["pct"], 0.01) for i in p_ids]) for c in cols]
        summary[m] = (exact, within1, weighted_kappa(ea, ma), sp, ratio)
    f2 = lambda x: "—" if x != x else f"{x:.2f}"
    pc = lambda x: "—" if x != x else f"%{x*100:.0f}"
    v2, v3 = summary["v2"], summary["v3"]
    L += [f"| Eylem tam uyum | {pc(v2[0])} | {pc(v3[0])} |",
          f"| Eylem en fazla 1 kademe fark | {pc(v2[1])} | {pc(v3[1])} |",
          f"| Ağırlıklı kappa (eylem) | {f2(v2[2])} | {f2(v3[2])} |",
          f"| Spearman ρ (risk %) | {f2(v2[3][0])} | {f2(v3[3][0])} / {f2(v3[3][1])} |",
          f"| Medyan oran model/uzman (risk %) | {f2(v2[4][0])} | {f2(v3[4][0])} / {f2(v3[4][1])} |",
          "",
          "*Kappa yorumu (Landis & Koch): <0,20 zayıf · 0,21–0,40 orta-altı · 0,41–0,60 orta · 0,61–0,80 iyi · >0,80 çok iyi. "
          "10 vakada güven aralığı geniştir; sonuçlar gösterge niteliğindedir.*",
          "", "## Vaka bazında", "",
          "| # | Uzman % | Uzman eylem | v2 % / eylem | v3 6y % / tam % / eylem | Not |",
          "| --- | ---: | :---: | --- | --- | --- |"]
    for i in ids:
        e, k = exp[i], key[i]
        flag2 = "" if e["act"] in (None, k["v2_action"]) else " ✗"
        flag3 = "" if e["act"] in (None, k["v3_action"]) else " ✗"
        ep = "—" if e["pct"] is None else f"{e['pct']:g}"
        L.append(f"| {i} | {ep} | {e['act'] or '—'} | {k['v2_score']:.1f} / {k['v2_action']}{flag2} | "
                 f"{k['v3_6y']:.1f} / {k['v3_score']:.1f} / {k['v3_action']}{flag3} | {e['note']} |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:14]))
    print(f"\n📄 {OUT}")


if __name__ == "__main__":
    main()
