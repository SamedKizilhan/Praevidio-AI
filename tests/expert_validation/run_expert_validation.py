# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI - Uzman Doğrulama Çalıştırıcı (Güz 2026)
=====================================================
10 klinik vakayı v2 ve v3 modellerine uygular ve ÜÇ dosya üretir:

  1) uzman_tahmin_formu.md  → uzmana verilecek form: vaka metinleri + boş alanlar
                              (model sonucu ve risk bantları GÖSTERİLMEZ)
  2) model_sonuclari.md     → cevap anahtarı: v2/v3 skorları, katmanlar ve
                              modellerin önereceği eylem (A/B/C)
  3) uzman_cevaplari.csv    → uzmanın cevaplarının girileceği şablon (yoksa oluşturulur)

Uzman her vaka için iki şey verir — hekimler bantlarla değil bu ikisiyle düşünür:
  (a) tahmini 6 yıllık akciğer kanseri tanı riski (%)
  (b) önereceği eylem:  A = rutin takip / ek işlem gerekmez
                        B = düşük doz BT (LDCT) taraması önerilir
                        C = kısa sürede hekim değerlendirmesi (göğüs röntgeni / sevk)

Modellerin eylemi:
  v3: NICE NG12 alarmı → C;  değilse 6 yıllık faktör riski ≥ %1,51 (PLCOm2012 eşiği)
      veya USPSTF tarama adayı → B;  değilse A
  v2: Yüksek bant → C;  Orta bant veya USPSTF tarama adayı → B;  değilse A

Çalıştırma:
  python tests/expert_validation/run_expert_validation.py   (veya: make expert)
Uzman cevapları girildikten sonra:
  python tests/expert_validation/analyze_expert_validation.py   (veya: make expert-analyze)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from model.hybrid_bayesian_network_v3 import load_engine
from model.plcom2012 import SCREEN_THRESHOLD
from model.screening import assess_screening_eligibility

HERE = Path(__file__).parent
FORM_PATH = HERE / "uzman_tahmin_formu.md"
RESULTS_PATH = HERE / "model_sonuclari.md"
ANSWERS_PATH = HERE / "uzman_cevaplari.csv"
KEY_PATH = HERE / "model_sonuclari.json"

ACTIONS = {"A": "Rutin takip / ek işlem gerekmez",
           "B": "Düşük doz BT taraması önerilir",
           "C": "Kısa sürede hekim değerlendirmesi (göğüs röntgeni / sevk)"}


def action_v3(r3: dict, elig: dict) -> str:
    if r3["alarm"]["level"] == "urgent":
        return "C"
    if r3["risk_6y_factors"] / 100.0 >= SCREEN_THRESHOLD or elig["eligible"] is True:
        return "B"
    return "A"


def action_v2(r2: dict, elig: dict) -> str:
    if r2["risk_level"] == "high":
        return "C"
    if r2["risk_level"] == "moderate" or elig["eligible"] is True:
        return "B"
    return "A"


def run():
    eng2, eng3 = load_engine("v2"), load_engine("v3")
    data = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    rows = []
    for s in data["scenarios"]:
        ev = s["evidence"]
        r2, r3 = eng2.predict_risk(ev), eng3.predict_risk(ev)
        elig = assess_screening_eligibility(ev)
        bm = r3["benchmark_plcom2012"]
        rows.append({
            "id": s["id"], "vignette": s["vignette"],
            "v2_score": r2["risk_score"], "v2_level_tr": r2["risk_level_tr"], "v2_action": action_v2(r2, elig),
            "v3_score": r3["risk_score"], "v3_level_tr": r3["risk_level_tr"],
            "v3_6y": r3["risk_6y_factors"], "v3_action": action_v3(r3, elig),
            "alarm": "ACİL" if r3["alarm"]["level"] == "urgent" else "—",
            "plco": bm["risk_6y"] if bm["applicable"] else None,
            "screen": elig["label_tr"],
        })

    # ── 1) Uzman formu (model sonucu ve bant YOK) ──
    F = ["# Praevidio AI — Uzman Değerlendirme Formu",
         "",
         "Değerli Hocam,",
         "",
         "Praevidio AI, sesli bir anketle toplanan yaş, sigara öyküsü, risk faktörleri ve belirtilerden "
         "akciğer kanseri **risk farkındalığı** sağlamayı amaçlayan bir bitirme projesidir (tanı aracı değildir). "
         "Modelin klinik yargıyla ne kadar uyumlu olduğunu ölçmek için sizden aşağıdaki 10 kurgusal vakayı "
         "değerlendirmenizi rica ediyoruz. Formu doldururken modelin sonuçlarını görmeyeceksiniz; "
         "karşılaştırmayı sonradan biz yapacağız. Yaklaşık süre: 15–20 dakika.",
         "",
         "## Bölüm 1 — Vakalar",
         "",
         "Her vaka için lütfen iki şey belirtin:",
         "",
         "- **(a) Tahmini 6 yıllık risk (%):** Bu kişinin önümüzdeki **6 yıl içinde akciğer kanseri tanısı alma** "
         "olasılığı sizce yüzde kaç? Kesin bir sayı beklenmiyor; klinik sezginize göre bir tahmin yeterli. "
         "*(Fikir vermesi için: NLST çalışmasında 55–74 yaş, ≥30 paket-yıl içicilerde yaklaşık 6 yıllık tanı oranı ~%4'tü.)*",
         "- **(b) Önereceğiniz eylem:**",
         f"    - **A** — {ACTIONS['A']}",
         f"    - **B** — {ACTIONS['B']}",
         f"    - **C** — {ACTIONS['C']}",
         "",
         "Vaka metninde belirtilmeyen bilgileri (ör. KOAH tanısı, meslek) **yok/bilinmiyor** kabul edebilirsiniz.",
         "",
         "| # | Vaka | (a) 6 yıllık risk % | (b) Eylem (A/B/C) | Not (opsiyonel) |",
         "|---|---|---|---|---|"]
    for r in rows:
        F.append(f"| {r['id']} | {r['vignette']} |  |  |  |")
    F += ["",
          "## Bölüm 2 — Model varsayımları hakkında görüşünüz",
          "",
          "*Lütfen bu bölümü Bölüm 1'i tamamladıktan sonra doldurun.*",
          "",
          "1. **Belirti verme oranı.** Önümüzdeki 6 yıl içinde akciğer kanseri tanısı alacak 100 kişiden kaçının "
          "*bugün* (tanıdan aylar–yıllar önce) en az bir belirti (öksürük, nefes darlığı, kilo kaybı vb.) "
          "göstermesini beklersiniz?  ______ / 100",
          "2. **KOAH sıklığı.** Sizin hasta profilinizde aktif içicilerin yaklaşık yüzde kaçında KOAH / kronik "
          "bronşit tanısı vardır?  Aktif içici: ____ %   Bırakmış içici: ____ %",
          "3. **Taban risk.** *62 yaşında, günde 1 paket ve 30 yıldır içen, belirtisiz bir erkek* için 6 yıllık "
          "risk tahmininiz hangisine yakın?  ☐ ~%1,5–2   ☐ ~%3   ☐ ~%5   ☐ Diğer: ____",
          "4. **Acil değerlendirme kuralı.** İngiltere NICE NG12 kılavuzu; 40 yaş üstü, sigara öyküsü olan ve "
          "açıklanamayan **tek bir** belirtisi (ör. hafif öksürük) bulunan kişiye kısa sürede göğüs röntgeni "
          "önermektedir. Türkiye pratiği için bu kural sizce:  ☐ Uygun   ☐ Aşırı temkinli   ☐ Yetersiz",
          "5. **Eksik sorular.** Uygulamanın sorduğu belirti ve risk faktörlerine (öksürük, nefes darlığı, "
          "göğüs ağrısı, hırıltı, halsizlik, kan tükürme, kilo kaybı; sigara, aile öyküsü, mesleki maruziyet, "
          "KOAH, yaşanan il) eklenmesini önerdiğiniz bir şey var mı? (ör. ses kısıklığı, iştahsızlık, "
          "geçirilmiş tüberküloz, biyomas/tandır dumanı)",
          "",
          "   ______________________________________________________________",
          "",
          "6. **Genel yorumunuz** (opsiyonel):",
          "",
          "   ______________________________________________________________",
          "",
          "*Değerli katkınız için teşekkür ederiz. Adınız raporda yalnızca izniniz olursa teşekkür bölümünde yer alır.*",
          ""]
    FORM_PATH.write_text("\n".join(F), encoding="utf-8")

    # ── 2) Cevap anahtarı ──
    def pct(x):
        return "n/a" if x is None else f"%{x:.1f}"
    R = ["# Praevidio AI — Model Sonuçları (Cevap Anahtarı)",
         "",
         "*Uzmana gösterilmez. Otomatik üretilir: `make expert`.*",
         "",
         "Eylem: **A** rutin takip · **B** düşük doz BT taraması · **C** kısa sürede hekim değerlendirmesi. "
         "v3 eylemi = NICE NG12 alarmı → C; 6 yıllık faktör riski ≥ %1,51 veya USPSTF adayı → B; değilse A. "
         "v2 eylemi = Yüksek → C; Orta veya USPSTF adayı → B; değilse A.",
         "",
         "| # | Vaka (özet) | v2 % | v2 bant | v2 eylem | v3 % | v3 6y % | v3 bant | v3 eylem | PLCOm2012 6y | Alarm | USPSTF |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        short = r["vignette"][:60] + ("…" if len(r["vignette"]) > 60 else "")
        R.append(f"| {r['id']} | {short} | %{r['v2_score']:.1f} | {r['v2_level_tr']} | **{r['v2_action']}** | "
                 f"%{r['v3_score']:.1f} | %{r['v3_6y']:.1f} | {r['v3_level_tr']} | **{r['v3_action']}** | "
                 f"{pct(r['plco'])} | {r['alarm']} | {r['screen']} |")
    R += ["", "Uzman cevapları `uzman_cevaplari.csv`'ye girildikten sonra karşılaştırma için: `make expert-analyze`.", ""]
    RESULTS_PATH.write_text("\n".join(R), encoding="utf-8")
    KEY_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 3) Cevap şablonu (varsa ezilmez) ──
    if not ANSWERS_PATH.exists():
        lines = ["id,uzman_risk_6y_yuzde,uzman_eylem,not"] + [f"{r['id']},,," for r in rows]
        ANSWERS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("🩺 UZMAN DOĞRULAMA — Cevap anahtarı")
    print("=" * 78)
    for r in rows:
        print(f"  {r['id']:4} v2 %{r['v2_score']:5.1f} {r['v2_action']} | v3 %{r['v3_score']:5.1f} "
              f"6y %{r['v3_6y']:4.1f} {r['v3_action']} | PLCO {pct(r['plco']):6} {r['alarm']:4} | {r['screen']}")
    print(f"\n📄 {FORM_PATH.name} (uzmana)  ·  {RESULTS_PATH.name} (cevap anahtarı)  ·  {ANSWERS_PATH.name} (şablon)")


if __name__ == "__main__":
    run()
