"""
Praevidio AI - Demo & Test Senaryoları Çalıştırıcı
===================================================
scenarios.json içindeki senaryoları hibrit BBN üzerinde çalıştırır:
  - terminalde özet tablo + 'demo' senaryolarında beklenen seviye doğrulaması (golden test),
  - 'pair' (kontrollü çift/grup) senaryolarında değişen faktörün etkisini gösterir,
  - SUNUM İÇİN: tests/test_scenarios/SENARYO_RAPORU.md dosyasını açıklamalı üretir.

Çalıştırma:
  python tests/test_scenarios/run_scenarios.py     (veya: make scenarios)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from model.hybrid_bayesian_network import build_hybrid_model, HybridLungCancerEngine

HERE = Path(__file__).parent
SCENARIOS_PATH = HERE / "scenarios.json"
REPORT_PATH = HERE / "SENARYO_RAPORU.md"


def run():
    print("🧪 PRAEVIDIO AI — Demo & Test Senaryoları")
    print("=" * 70)
    eng = HybridLungCancerEngine(build_hybrid_model())
    data = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    scenarios = data["scenarios"]
    explanations = data["_meta"].get("pair_explanations", {})

    res = {}
    for s in scenarios:
        r = eng.predict_risk(s["evidence"])
        res[s["id"]] = {"score": r["risk_score"], "level": r["risk_level"],
                        "level_tr": r["risk_level_tr"], "note": r.get("smoking_adjustment")}

    demos = [s for s in scenarios if s["group"] == "demo"]
    pairs = {}
    for s in [x for x in scenarios if x["group"] == "pair"]:
        pairs.setdefault(s["pair"], []).append(s)

    # --- Terminal: demolar ---
    print("\n📋 DEMO SENARYOLARI (beklenen seviye doğrulaması)")
    failures = 0
    for s in demos:
        r = res[s["id"]]
        exp = s.get("expected_level")
        ok = (exp is None) or (r["level"] == exp)
        failures += 0 if ok else 1
        mark = "—" if exp is None else ("✓" if ok else "✗ HATA")
        print(f"   {s['id']:4} {s['name'][:50]:50} {r['score']:6.1f}% {r['level']:9} {mark}")

    # --- Terminal: çiftler ---
    print("\n🔬 KONTROLLÜ ÇİFTLER / GRUPLAR")
    for pair_name, items in pairs.items():
        print(f"\n   • {pair_name}")
        for s in items:
            r = res[s["id"]]
            note = f"  [{r['note']}]" if r["note"] else ""
            print(f"      {s['id']:4} {s['name'][:46]:46} → {r['score']:6.1f}% ({r['level_tr']}){note}")
        if len(items) == 2:
            d = res[items[1]["id"]]["score"] - res[items[0]["id"]]["score"]
            print(f"      Δ = {d:+.1f} yüzde-puan")

    # --- Markdown rapor ---
    _write_report(demos, pairs, res, explanations)
    print(f"\n📄 Sunum raporu: {REPORT_PATH}")

    print("\n" + "=" * 70)
    if failures == 0:
        print("✅ Tüm demo senaryoları beklenen risk seviyesiyle eşleşti.")
    else:
        print(f"❌ {failures} demo senaryosu beklenenle eşleşmedi.")
    return failures


def _write_report(demos, pairs, res, explanations):
    L = ["# Praevidio AI — Test Senaryoları Raporu",
         "",
         "Bu rapor `make scenarios` ile otomatik üretilir. Risk eşikleri: "
         "**Düşük < %5 · Orta %5–15 · Yüksek > %15**.",
         "",
         "## 1. Demo Senaryoları",
         "",
         "Gerçekçi bağımsız vakalar; beklenen risk seviyesi doğrulanır (golden test).",
         "",
         "| ID | Senaryo | Amaç | Risk | Seviye | Beklenen |",
         "|---|---|---|---|---|---|"]
    for s in demos:
        r = res[s["id"]]
        L.append(f"| {s['id']} | {s['name']} | {s.get('purpose','')} | "
                 f"%{r['score']:.1f} | {r['level_tr']} | {s.get('expected_level','-')} |")

    L += ["", "## 2. Kontrollü Çiftler / Gruplar (Açıklanabilirlik)", "",
          "Her grupta **yalnızca belirtilen faktör** değişir; gerisi sabittir. "
          "Böylece o faktörün riske katkısı izole edilir."]
    for pair_name, items in pairs.items():
        L += ["", f"### {pair_name}", ""]
        if pair_name in explanations:
            L += [f"> {explanations[pair_name]}", ""]
        L += ["| ID | Senaryo | Risk | Seviye | Not |", "|---|---|---|---|---|"]
        for s in items:
            r = res[s["id"]]
            L.append(f"| {s['id']} | {s['name']} | %{r['score']:.1f} | {r['level_tr']} | {r['note'] or '—'} |")
        if len(items) == 2:
            d = res[items[1]["id"]]["score"] - res[items[0]["id"]]["score"]
            L += ["", f"**Δ ({items[1]['id']} − {items[0]['id']}) = {d:+.1f} yüzde-puan**"]

    L += ["", "---",
          "*Not: Risk skorları olasılıktır, tanı değildir. Düşük semptom-skoru, tarama "
          "uygunluğunu ortadan kaldırmaz (bkz. `screening.py`).*", ""]
    REPORT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
