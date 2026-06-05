"""
Praevidio AI - Uzman Doğrulama Çalıştırıcı
==========================================
10 klinik vakayı modele uygular ve İKİ dosya üretir:
  1) uzman_tahmin_formu.md  → SADECE vaka açıklamaları + boş tahmin alanı
                              (uzmana bunu verirsiniz; model sonucunu görmez)
  2) model_sonuclari.md     → modelin risk skoru/seviyesi (cevap anahtarı);
                              uzmanın tahminleriyle karşılaştırmak için.

Eşikler: Düşük <%5 · Orta %5–15 · Yüksek >%15

Çalıştırma:
  python tests/expert_validation/run_expert_validation.py   (veya: make expert)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from model.hybrid_bayesian_network import build_hybrid_model, HybridLungCancerEngine
from model.screening import assess_screening_eligibility

HERE = Path(__file__).parent
FORM_PATH = HERE / "uzman_tahmin_formu.md"
RESULTS_PATH = HERE / "model_sonuclari.md"


def run():
    eng = HybridLungCancerEngine(build_hybrid_model())
    data = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    scenarios = data["scenarios"]

    rows = []
    for s in scenarios:
        r = eng.predict_risk(s["evidence"])
        elig = assess_screening_eligibility(s["evidence"])
        rows.append({"id": s["id"], "vignette": s["vignette"],
                     "score": r["risk_score"], "level_tr": r["risk_level_tr"],
                     "note": r.get("smoking_adjustment"),
                     "screen": elig["label_tr"]})

    # --- 1) Uzman tahmin formu (sonuç YOK) ---
    F = ["# Praevidio AI — Uzman Risk Tahmini Formu",
         "",
         "Aşağıdaki her vaka için, lütfen yalnızca klinik değerlendirmenize dayanarak "
         "bir **risk seviyesi** (Düşük / Orta / Yüksek) ve dilerseniz bir **yüzde tahmini** veriniz. "
         "Bu bir akciğer kanseri tarama/farkındalık risk skorudur, kesin tanı değildir.",
         "",
         "**Risk eşikleri:** Düşük < %5 · Orta %5–15 · Yüksek > %15",
         "",
         "| # | Vaka | Tahmini Seviye | Tahmini % |",
         "|---|---|---|---|"]
    for r in rows:
        F.append(f"| {r['id']} | {r['vignette']} | | |")
    F += ["", "*Teşekkürler. Tahminlerinizi tamamladıktan sonra model sonuçlarıyla "
          "karşılaştıracağız.*", ""]
    FORM_PATH.write_text("\n".join(F), encoding="utf-8")

    # --- 2) Model sonuçları (cevap anahtarı) ---
    R = ["# Praevidio AI — Model Sonuçları (Cevap Anahtarı)",
         "",
         "Uzman tahminleriyle karşılaştırmak içindir. Eşikler: Düşük <%5 · Orta %5–15 · Yüksek >%15.",
         "",
         "| # | Vaka (özet) | Model % | Model Seviye | Tarama | Not |",
         "|---|---|---|---|---|---|"]
    for r in rows:
        short = r["vignette"][:70] + ("…" if len(r["vignette"]) > 70 else "")
        R.append(f"| {r['id']} | {short} | %{r['score']:.1f} | {r['level_tr']} | "
                 f"{r['screen']} | {r['note'] or '—'} |")
    R += ["",
          "### Uzman vs Model karşılaştırma tablosu (doldurmak için)",
          "",
          "| # | Uzman seviye | Model seviye | Uyum? |",
          "|---|---|---|---|"]
    for r in rows:
        R.append(f"| {r['id']} |  | {r['level_tr']} |  |")
    R += ["",
          "> Uyum ölçütü olarak ağırlıklı kappa (weighted Cohen's kappa) veya basit "
          "seviye-eşleşme yüzdesi kullanılabilir. Tam eşleşme yerine 'bir seviye fark' "
          "tolere edilebilir (örn. Orta↔Yüksek).",
          ""]
    RESULTS_PATH.write_text("\n".join(R), encoding="utf-8")

    # Terminal özeti
    print("🩺 UZMAN DOĞRULAMA — Model Sonuçları")
    print("=" * 60)
    for r in rows:
        print(f"  {r['id']:4} %{r['score']:5.1f}  {r['level_tr']:11} | {r['screen']}")
    print(f"\n📄 Form (uzmana verin): {FORM_PATH.name}")
    print(f"📄 Cevap anahtarı: {RESULTS_PATH.name}")


if __name__ == "__main__":
    run()
