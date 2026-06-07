"""
Praevidio AI - Risk Skoru Açıklanabilirliği
============================================
"Bu hasta neden %X risk aldı ve hangi faktör ne kadar katkı yaptı?" sorusuna
sunum-hazır, sayısal ve savunulabilir cevaplar üretir.

ÜÇ ANALİZ
---------
1) SHAPLEY KATKILARI (sıra-bağımsız, ADİL):
   Her bulgunun risk skoruna katkısı, oyun teorisindeki Shapley değeriyle
   hesaplanır. Tüm bulgu altkümeleri üzerinden ortalama marjinal katkı alınır;
   katkılar TAM olarak toplanır: taban + Σ(katkılar) = nihai skor.
   Bu, "leave-one-out" veya "tek tek ekleme"nin sıraya bağlı olma sorununu çözer.

2) BAĞLAM-BAĞIMLILIĞI (senin kilit sorun):
   Aynı semptom (örn. HIRILTI) farklı hastalarda AYNI yüzdeyi mi katar?
   HAYIR. Bayesçi modelde katkı, taban riske (yaş/cinsiyet/sigara) ve diğer
   semptomlara bağlıdır. İki sebep:
     (a) Olasılık doygunluğu: aynı "olasılık oranı" (odds çarpanı) düşük tabanda
         küçük, orta tabanda büyük, ~%100'e yakın tabanda yine küçük yüzde-puan
         değişimi yaratır (lojistik eğrinin doğrusal-olmayışı).
     (b) Confounder: HIRILTI/ÖKSÜRÜK/NEFES DARLIĞI'nın olasılık oranı SİGARA
         durumuna bağlıdır (model yapısı gereği). Confounder'sız semptomlarda
         (hemoptizi, göğüs ağrısı...) odds çarpanı ~sabittir, ama yüzde-puan
         katkı yine bağlama göre değişir.

3) WATERFALL (build-up): taban riskten başlayıp bulguları ekleyerek skorun
   nasıl oluştuğunu adım adım gösterir (sunum görseli).

Çıktılar:
  - data/processed/hybrid_model_results/explainability_report_patient.json
  - .../explain_waterfall.png , .../explain_context_dependence.png
  - docs/explainability_demo.md  (sunum için)

Çalıştırma:  python src/model/explainability.py
"""

import json
import sys
from math import factorial
from itertools import combinations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PROCESSED_DATA_DIR, PROJECT_ROOT
from model.hybrid_bayesian_network import build_hybrid_model, HybridLungCancerEngine

RESULTS_DIR = PROCESSED_DATA_DIR / "hybrid_model_results"
DOCS_DIR = PROJECT_ROOT / "docs"

# İnsan-okur etiketler
LABELS = {
    "FAMILY_HISTORY": "Ailede kanser öyküsü",
    "ASBESTOS": "Mesleki maruziyet",
    "AIR_POLLUTION": "Hava kirliliği",
    "COUGHING": "Öksürük", "SHORTNESS_OF_BREATH": "Nefes darlığı",
    "CHEST_PAIN": "Göğüs ağrısı", "WHEEZING": "Hırıltı",
    "FATIGUE": "Yorgunluk", "HEMOPTYSIS": "Hemoptizi (kan tükürme)",
    "WEIGHT_LOSS": "Kilo kaybı",
}
DEMO_KEYS = {"AGE", "GENDER", "SMOKING"}   # taban (NLST risk-faktörü) — oyuncu değil

# Senin raporundaki gerçek vaka (PRA-3C1DEB10, %56.1).
# ÖNEMLİ: ajan akışında yok olan semptomlar AÇIKÇA 0 (yok) olarak gözlenir —
# bu negatif kanıt riski düşürür. Raporun %56.1'ini birebir yeniden üretmek için
# yok semptomları da 0 olarak veriyoruz (atlamak ≈ marjinalize → daha yüksek skor verir).
REPORT_PATIENT = {
    "AGE": 1, "GENDER": 1, "SMOKING": 1,
    "FAMILY_HISTORY": 1, "ASBESTOS": 1, "AIR_POLLUTION": 1,
    "COUGHING": 1, "CHEST_PAIN": 1, "FATIGUE": 1,
    "SHORTNESS_OF_BREATH": 0, "WHEEZING": 0, "HEMOPTYSIS": 0, "WEIGHT_LOSS": 0,
}


def risk_prob(eng, ev):
    clean = {k: v for k, v in ev.items() if not k.startswith("_")}
    return eng.predict_risk(clean)["risk_probability"]


def _odds(p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return p / (1 - p)


# ─────────────────────────────────────────────────────────
# 1) SHAPLEY KATKILARI
# ─────────────────────────────────────────────────────────

def shapley_contributions(eng, evidence):
    """
    Referans hasta = aynı demografi + TÜM bulgular null (semptom=0, risk faktörü=0).
    Oyuncular = AKTİF (=1/2) bulgular. Diğer (yok) bulgular referansta 0 sabit kalır.
    v(S) = risk(demografi + oyuncular[S] açık + kalan bulgular 0).
    Shapley_i = ortalama marjinal katkı.  Σ Shapley_i = v(tam) - v(referans).
    (TAM toplam, sıra bağımsız — nihai skor = rapor %56.1'e eşittir.)
    """
    base = {k: v for k, v in evidence.items() if k in DEMO_KEYS}
    nondemo = {k: v for k, v in evidence.items()
               if k not in DEMO_KEYS and not k.startswith("_")}
    background = {k: 0 for k in nondemo}            # null referans (yok semptomlar dahil)
    players = [k for k, v in nondemo.items() if v >= 1]
    n = len(players)

    # v(S) önbellekli
    cache = {}
    def v(subset):
        key = frozenset(subset)
        if key not in cache:
            ev = {**base, **background}
            for p in subset:
                ev[p] = evidence[p]
            cache[key] = risk_prob(eng, ev)
        return cache[key]

    base_p = v([])
    full_p = v(players)
    shap = {p: 0.0 for p in players}
    for i in players:
        others = [p for p in players if p != i]
        for r in range(len(others) + 1):
            w = factorial(r) * factorial(n - r - 1) / factorial(n)
            for S in combinations(others, r):
                shap[i] += w * (v(list(S) + [i]) - v(list(S)))

    # yüzde-puan cinsinden
    out = {p: round(shap[p] * 100, 2) for p in players}
    return {
        "base_risk_pct": round(base_p * 100, 2),
        "full_risk_pct": round(full_p * 100, 2),
        "shapley_pct": dict(sorted(out.items(), key=lambda kv: -kv[1])),
        "sum_check_pct": round(sum(out.values()) + base_p * 100, 2),  # ≈ full
    }


# ─────────────────────────────────────────────────────────
# 2) BAĞLAM-BAĞIMLILIĞI
# ─────────────────────────────────────────────────────────

CONTEXTS = {
    "C1: 50y kadın, hiç içmemiş (düşük taban)": {"AGE": 0, "GENDER": 0, "SMOKING": 0},
    "C2: 55-59 erkek, aktif içici (orta taban)": {"AGE": 1, "GENDER": 1, "SMOKING": 1},
    "C3: 70+ erkek, aktif içici (yüksek taban)": {"AGE": 4, "GENDER": 1, "SMOKING": 1},
    "C4: 70+ erkek içici + hemoptizi + kilo kaybı (doyma yakın)":
        {"AGE": 4, "GENDER": 1, "SMOKING": 1, "HEMOPTYSIS": 1, "WEIGHT_LOSS": 1},
}


def context_dependence(eng, factor, state=1):
    """Bir faktörü farklı tabanlara ekleyip Δ% ve odds-çarpanını ölç."""
    rows = []
    for name, base in CONTEXTS.items():
        if factor in base:
            continue
        p_off = risk_prob(eng, base)
        p_on = risk_prob(eng, {**base, factor: state})
        delta_pp = (p_on - p_off) * 100
        odds_mult = _odds(p_on) / _odds(p_off)
        rows.append({
            "context": name,
            "risk_off_pct": round(p_off * 100, 2),
            "risk_on_pct": round(p_on * 100, 2),
            "delta_pp": round(delta_pp, 2),
            "odds_multiplier": round(odds_mult, 2),
        })
    return rows


# ─────────────────────────────────────────────────────────
# 3) WATERFALL (build-up)
# ─────────────────────────────────────────────────────────

def build_up(eng, evidence, order=None):
    base = {k: v for k, v in evidence.items() if k in DEMO_KEYS}
    nondemo = {k: v for k, v in evidence.items()
               if k not in DEMO_KEYS and not k.startswith("_")}
    background = {k: 0 for k in nondemo}            # yok bulgular referansta 0
    players = order or [k for k, v in nondemo.items() if v >= 1]
    cur = {**base, **background}
    steps = [{"label": "Referans (demografi, semptomsuz)",
              "risk_pct": round(risk_prob(eng, cur) * 100, 2), "delta": None}]
    for p in players:
        prev = risk_prob(eng, cur)
        cur[p] = evidence[p]
        now = risk_prob(eng, cur)
        steps.append({"label": f"+ {LABELS.get(p, p)}",
                      "risk_pct": round(now * 100, 2),
                      "delta": round((now - prev) * 100, 2)})
    return steps


# ─────────────────────────────────────────────────────────
# Grafikler
# ─────────────────────────────────────────────────────────

def _plot_waterfall(steps):
    labels = [s["label"] for s in steps]
    vals = [s["risk_pct"] for s in steps]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(range(len(vals)), vals, "o-", color="#2c3e50", lw=2, zorder=3)
    for i, s in enumerate(steps):
        ax.annotate(f"{s['risk_pct']:.1f}%", (i, vals[i]),
                    textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9)
        if s["delta"] is not None:
            c = "#27ae60" if s["delta"] >= 0 else "#c0392b"
            ax.annotate(f"+{s['delta']:.1f}", (i, vals[i]),
                        textcoords="offset points", xytext=(0, -16), ha="center",
                        fontsize=8, color=c)
    ax.axhspan(0, 5, color="#2ecc71", alpha=0.08)
    ax.axhspan(5, 15, color="#f39c12", alpha=0.08)
    ax.axhspan(15, 100, color="#e74c3c", alpha=0.07)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Risk skoru (%)")
    ax.set_title("Risk Skorunun Oluşumu — Örnek Vaka (Rapor PRA-3C1DEB10)")
    ax.set_ylim(0, max(vals) * 1.25)
    plt.tight_layout()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(RESULTS_DIR / "explain_waterfall.png", dpi=150)
    plt.close()


def _plot_context(conf_rows, nonconf_rows, conf_name, nonconf_name):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=False)
    for ax, rows, title in [
        (axes[0], conf_rows, f"{conf_name} (confounder'lı — sigaraya bağlı)"),
        (axes[1], nonconf_rows, f"{nonconf_name} (confounder'sız)"),
    ]:
        ctx = [r["context"].split(":")[0] for r in rows]
        dpp = [r["delta_pp"] for r in rows]
        om = [r["odds_multiplier"] for r in rows]
        x = np.arange(len(ctx))
        b = ax.bar(x, dpp, color="#5dade2")
        ax.set_xticks(x); ax.set_xticklabels(ctx, fontsize=9)
        ax.set_ylabel("Katkı (yüzde-puan, Δpp)")
        ax.set_title(title, fontsize=10)
        for i, (d, o) in enumerate(zip(dpp, om)):
            ax.annotate(f"{d:+.1f}pp\n×{o:.2f}", (i, d),
                        textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8)
    fig.suptitle("Aynı Semptom, Farklı Bağlam → Farklı Katkı (Δpp) | odds çarpanı (×)", fontsize=12)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "explain_context_dependence.png", dpi=150)
    plt.close()


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

def main():
    print("🔎 PRAEVIDIO AI — Risk Skoru Açıklanabilirliği")
    print("=" * 60)
    eng = HybridLungCancerEngine(build_hybrid_model())

    # 1) Shapley
    shap = shapley_contributions(eng, REPORT_PATIENT)
    print(f"\n--- 1) SHAPLEY KATKILARI (Örnek vaka — rapor %56.1) ---")
    print(f"  Taban (demografi): {shap['base_risk_pct']:.2f}%  →  Nihai: {shap['full_risk_pct']:.2f}%")
    print(f"  Toplam kontrol (taban+Σkatkı): {shap['sum_check_pct']:.2f}%  (≈ nihai)")
    for f, c in shap["shapley_pct"].items():
        print(f"     {LABELS.get(f, f):24s}: {c:+.2f} yüzde-puan")

    # 2) Build-up
    steps = build_up(eng, REPORT_PATIENT)
    print(f"\n--- 2) WATERFALL (adım adım oluşum) ---")
    for s in steps:
        d = "" if s["delta"] is None else f"  (Δ {s['delta']:+.2f}pp)"
        print(f"     {s['label']:34s}: {s['risk_pct']:6.2f}%{d}")

    # 3) Bağlam-bağımlılığı: confounder'lı (HIRILTI) vs confounder'sız (HEMOPTİZİ)
    conf = context_dependence(eng, "WHEEZING")
    nonconf = context_dependence(eng, "HEMOPTYSIS")
    print(f"\n--- 3) BAĞLAM-BAĞIMLILIĞI ---")
    print(f"  HIRILTI (confounder'lı): aynı semptom, farklı bağlam → farklı katkı")
    for r in conf:
        print(f"     {r['context'][:40]:40s}: {r['risk_off_pct']:5.1f}% → {r['risk_on_pct']:5.1f}%  "
              f"(Δ {r['delta_pp']:+5.2f}pp, odds ×{r['odds_multiplier']:.2f})")
    print(f"  HEMOPTİZİ (confounder'sız): odds çarpanı ~sabit, Δpp yine değişir")
    for r in nonconf:
        print(f"     {r['context'][:40]:40s}: {r['risk_off_pct']:5.1f}% → {r['risk_on_pct']:5.1f}%  "
              f"(Δ {r['delta_pp']:+5.2f}pp, odds ×{r['odds_multiplier']:.2f})")

    # Grafikler + çıktılar
    _plot_waterfall(steps)
    _plot_context(conf, nonconf, "HIRILTI", "HEMOPTİZİ")

    report = {
        "report_patient_evidence": REPORT_PATIENT,
        "shapley": shap,
        "build_up": steps,
        "context_dependence": {"WHEEZING_confounded": conf, "HEMOPTYSIS_unconfounded": nonconf},
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "explainability_report_patient.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 {out}")
    print(f"📊 explain_waterfall.png , explain_context_dependence.png")

    _write_markdown(report)
    print(f"📄 {DOCS_DIR / 'explainability_demo.md'}")
    print("\n🎉 Açıklanabilirlik analizi tamamlandı.")
    return report


def score_analysis_markdown(engine, evidence: dict, risk_result: dict) -> str:
    """
    Tek bir hasta için skorun nasıl üretildiğini gösteren markdown üretir.
    Gerçek kanıt üzerinden (paket-yıl sigara düzeltmesi dahil) hesaplanır; bu yüzden
    nihai değer rapordaki skorla birebir tutuyor. Her rapora eşlik etmek üzere.
    """
    def risk(ev):
        return engine.predict_risk(ev)["risk_score"]

    meta = {k: v for k, v in evidence.items() if k.startswith("_")}       # paket-yıl vb.
    demo = {k: v for k, v in evidence.items() if k in DEMO_KEYS}
    # Gözlenen (demografi-dışı) bulgular: önce risk faktörleri, sonra semptomlar
    rf_order = ["FAMILY_HISTORY", "ASBESTOS", "AIR_POLLUTION"]
    findings = [k for k in rf_order if k in evidence] + \
               [k for k in SYMPTOMS_7 if k in evidence]

    base_ev = {**demo, **meta}     # semptom/faktör gözlenmemiş; sigara düzeltmesi geçerli
    base = risk(base_ev)
    final = risk({**evidence})

    # Build-up (sıralı) — her bulgunun eklenince getirdiği değişim
    cur = dict(base_ev)
    steps = [("Taban (yaş/cinsiyet/sigara)", base, None)]
    for k in findings:
        prev = risk(cur)
        cur[k] = evidence[k]
        now = risk(cur)
        steps.append((_label_val(k, evidence[k]), now, now - prev))

    # Leave-one-out — her bulgunun NİHAİ skora katkısı (sıra-bağımsız okuma)
    loo = []
    for k in findings:
        ev2 = dict(evidence)
        ev2.pop(k, None)
        loo.append((_label_val(k, evidence[k]), final - risk(ev2)))

    L = [
        f"# Risk Skoru Analizi — {risk_result.get('risk_score')}% "
        f"({risk_result.get('risk_level_tr','')})",
        "",
        "Bu dosya, eşlik ettiği PDF raporundaki skorun **nasıl üretildiğini** gösterir. "
        "Tüm değerler hastanın gerçek yanıtları üzerinden hesaplanmıştır.",
        "",
        f"**Risk eşikleri:** Düşük < %5 · Orta %5–15 · Yüksek > %15",
        "",
        "## 1. Skorun adım adım oluşumu (build-up)",
        "",
        "| Adım | Risk (%) | Değişim (puan) |",
        "|---|---|---|",
    ]
    for lbl, val, d in steps:
        L.append(f"| {lbl} | {val:.1f} | {'' if d is None else format(d, '+.1f')} |")
    L += [
        "",
        f"Taban **%{base:.1f}** → nihai **%{final:.1f}**. *(Ara adımlar ekleme sırasına "
        "bağlıdır; sıra-bağımsız adil katkı için aşağıdaki leave-one-out'a bakınız.)*",
        "",
        "## 2. Her bulgunun nihai skora katkısı (leave-one-out)",
        "",
        "| Bulgu | Katkı (puan) |",
        "|---|---|",
    ]
    for lbl, c in sorted(loo, key=lambda x: -x[1]):
        L.append(f"| {lbl} | {c:+.1f} |")

    if risk_result.get("or_contributions"):
        L += ["", "## 3. Risk faktörü çarpanları (literatür OR)", "",
              "| Faktör | Çarpan |", "|---|---|"]
        for n, m in risk_result["or_contributions"].items():
            L.append(f"| {n} | ×{m:.2f} |")

    if risk_result.get("smoking_adjustment"):
        L += ["", f"**Sigara değerlendirme notu:** {risk_result['smoking_adjustment']}"]
    sc = risk_result.get("screening")
    if sc:
        L += ["", f"**Tarama değerlendirmesi:** {sc.get('label_tr','')} — {sc.get('message_tr','')}"]

    L += ["", "---",
          "*Not: Skor bir olasılıktır, tanı değildir. Semptomlar kanserin sonucu olduğu "
          "için 'kanıt gücü' (olasılık oranı, LR) ile; risk faktörleri kanserin nedeni "
          "olduğu için odds-ratio (OR) ile etki eder. Ayrıntı: docs/contribution_coefficients.md*",
          ""]
    return "\n".join(L)


def _label_val(k, v):
    base = LABELS.get(k, k)
    if k in SYMPTOMS_7:
        return f"{base} ({'var' if v == 1 else 'yok'})"
    if k == "AIR_POLLUTION":
        return f"{base} ({'yüksek' if v == 2 else 'orta' if v == 1 else 'düşük'})"
    return f"{base} ({'var' if v == 1 else 'yok'})"


SYMPTOMS_7 = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN", "WHEEZING",
              "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]


def _write_markdown(r):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    s = r["shapley"]
    L = LABELS
    out = [
        "# Risk Skoru Açıklanabilirliği — Sunum Notları",
        "",
        "**Modül:** `src/model/explainability.py` (`make explain`)  ",
        "**Örnek vaka:** Rapor PRA-3C1DEB10 — 55-59 erkek, aktif içici, ailede öykü + "
        "mesleki risk + İzmir (orta hava), öksürük + göğüs ağrısı + yorgunluk → **%56.1 (Yüksek)**",
        "",
        "## 1. Shapley katkıları (sıra-bağımsız, adil)",
        "",
        "Her bulgunun skora katkısı oyun-teorisi Shapley değeriyle hesaplanır: tüm bulgu "
        "altkümeleri üzerinden ortalama marjinal katkı. Katkılar **tam toplanır**:",
        "",
        f"> Taban (yaş/cinsiyet/sigara) **{s['base_risk_pct']:.2f}%** + Σ(katkılar) = "
        f"**{s['full_risk_pct']:.2f}%** (kontrol: {s['sum_check_pct']:.2f}%)",
        "",
        "| Bulgu | Katkı (yüzde-puan) |",
        "|---|---|",
    ]
    for f, c in s["shapley_pct"].items():
        out.append(f"| {L.get(f, f)} | {c:+.2f} |")
    out += [
        "",
        "> Bu, “şu semptom her zaman X puan ekler” demenin doğru yolu **değildir** — Shapley "
        "katkısı bu hastanın bağlamına özeldir. Aşağıda neden değiştiği gösteriliyor.",
        "",
        "## 2. Build-up (skorun adım adım oluşumu)",
        "",
        "| Adım | Risk (%) | Δ (yüzde-puan) |",
        "|---|---|---|",
    ]
    for st in r["build_up"]:
        d = "" if st["delta"] is None else f"{st['delta']:+.2f}"
        out.append(f"| {st['label']} | {st['risk_pct']:.2f} | {d} |")
    out += [
        "",
        "*Not:* tek-tek ekleme sıraya bağlıdır; sıra-bağımsız adil pay için Shapley (§1) kullanılır.",
        "",
        "## 3. Bağlam-bağımlılığı — “Hırıltı her seferinde aynı mı katkı yapar?”",
        "",
        "**Hayır.** İki neden: (a) olasılık doygunluğu (lojistik eğri doğrusal değil), "
        "(b) confounder — hırıltı/öksürük/nefes darlığının olasılık oranı **sigara durumuna** bağlıdır.",
        "",
        "### HIRILTI (confounder'lı — sigaraya bağlı)",
        "",
        "| Bağlam | Risk (önce→sonra) | Katkı Δpp | Odds çarpanı |",
        "|---|---|---|---|",
    ]
    for row in r["context_dependence"]["WHEEZING_confounded"]:
        out.append(f"| {row['context']} | {row['risk_off_pct']:.1f}% → {row['risk_on_pct']:.1f}% | "
                   f"{row['delta_pp']:+.2f} | ×{row['odds_multiplier']:.2f} |")
    out += [
        "",
        "### HEMOPTİZİ (confounder'sız — kıyas için)",
        "",
        "| Bağlam | Risk (önce→sonra) | Katkı Δpp | Odds çarpanı |",
        "|---|---|---|---|",
    ]
    for row in r["context_dependence"]["HEMOPTYSIS_unconfounded"]:
        out.append(f"| {row['context']} | {row['risk_off_pct']:.1f}% → {row['risk_on_pct']:.1f}% | "
                   f"{row['delta_pp']:+.2f} | ×{row['odds_multiplier']:.2f} |")
    out += [
        "",
        "**Sunumda söylenecek cümle:** *Confounder'sız semptomlarda (hemoptizi, göğüs ağrısı...) "
        "odds çarpanı bağlamdan bağımsız ~sabittir; bu modelin tutarlılığını gösterir. Ancak "
        "yüzde-puan katkı, taban riske göre değişir (doygunluk). Confounder'lı solunum "
        "semptomlarında (hırıltı, öksürük, nefes darlığı) odds çarpanı bile sigara durumuna göre "
        "değişir — çünkü model, bu semptomların sigaradan da kaynaklanabileceğini biliyor. "
        "Bu, basit additif puanlamanın yakalayamadığı klinik etkileşimi yansıtır.*",
        "",
    ]
    (DOCS_DIR / "explainability_demo.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
