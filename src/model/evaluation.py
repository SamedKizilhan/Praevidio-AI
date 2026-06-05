"""
Praevidio AI - Risk Modeli Değerlendirme (v2)
==============================================
F1/accuracy YERİNE, bir olasılıksal risk/tarama aracı için uygun metrikler.

Neden F1 değil?
  - Amaç tanı değil, risk STRATİFİKASYONU. Model sürekli bir olasılık üretir;
    F1 bunu zorla eşikler → bilgi kaybı.
  - Taban prevalans ~%3.85 (çok dengesiz). Eşiğe aşırı duyarlı F1 yanıltıcıdır
    (model her şeye "pozitif" derse bile yüksek görünebilir).

Bunun yerine ölçülenler:
  AYRIM (discrimination):  AUC-ROC, AUPRC
  KALİBRASYON:             Brier skoru, reliability eğrisi, ECE, kalibrasyon eğimi/kesişimi
  KLİNİK FAYDA:            Decision Curve Analysis (net benefit)
  EŞİK BAZLI:             seçilen risk eşiklerinde duyarlılık (sensitivity)/özgüllük

KAPSAM NOTU
-----------
NLST verisinde yaş/cinsiyet/sigara + kanser sonucu vardır; 7 semptom ve 3 yeni
risk faktörü (aile öyküsü, asbest, hava kirliliği) YOKTUR. Bu yüzden burada
NLST tabanlı risk-faktörü modeli P(kanser | yaş, cinsiyet, sigara) gerçek
etiketlerle hold-out üzerinde değerlendirilir. Semptom CPT'leri ve yeni faktör
OR'ları literatür temellidir (yüz geçerliliği), NLST ile doğrulanamaz —
bu, projenin "tanı değil, kalibre risk" çerçevesiyle tutarlıdır.

Çalıştırma:
  python src/model/evaluation.py
"""

import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    roc_curve, precision_recall_curve, confusion_matrix
)
from sklearn.calibration import calibration_curve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import NLST_CLEANED_PATH, PROCESSED_DATA_DIR
from model.hybrid_bayesian_network import compute_nlst_cancer_cpt

RESULTS_DIR = PROCESSED_DATA_DIR / "hybrid_model_results"
RISK_THRESHOLDS = [0.05, 0.15]   # Orta ve Yüksek eşikleri (config ile uyumlu)


# ──────────────────────────────────────────────
# Metrik yardımcıları
# ──────────────────────────────────────────────

def expected_calibration_error(y_true, y_prob, n_bins=10):
    """ECE: tahmin edilen ile gözlenen frekans arasındaki ağırlıklı fark."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.digitize(y_prob, bins) - 1
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        m = idx == b
        if m.sum() == 0:
            continue
        conf = y_prob[m].mean()
        acc = y_true[m].mean()
        ece += (m.sum() / n) * abs(acc - conf)
    return float(ece)


def calibration_slope_intercept(y_true, y_prob):
    """Logistic recalibration: ideal eğim=1, kesişim=0."""
    from sklearn.linear_model import LogisticRegression
    eps = 1e-9
    logit = np.log(np.clip(y_prob, eps, 1 - eps) / np.clip(1 - y_prob, eps, 1 - eps))
    lr = LogisticRegression(fit_intercept=True, C=1e6, solver="lbfgs")
    lr.fit(logit.reshape(-1, 1), y_true)
    return float(lr.coef_[0][0]), float(lr.intercept_[0])


def sensitivity_specificity(y_true, y_prob, threshold):
    pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    return float(sens), float(spec)


def decision_curve_analysis(y_true, y_prob, thresholds=None):
    """
    Net benefit = (TP/n) - (FP/n) * (pt/(1-pt)).
    Modeli 'herkesi tara' ve 'kimseyi tarama' ile karşılaştırır.
    Tarama araçları için modern klinik fayda standardı.
    """
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.30, 30)
    n = len(y_true)
    prev = y_true.mean()
    nb_model, nb_all = [], []
    for pt in thresholds:
        pred = (y_prob >= pt).astype(int)
        tp = ((pred == 1) & (y_true == 1)).sum()
        fp = ((pred == 1) & (y_true == 0)).sum()
        w = pt / (1 - pt)
        nb_model.append(tp / n - (fp / n) * w)
        nb_all.append(prev - (1 - prev) * w)   # herkesi tara
    return list(thresholds), nb_model, nb_all


# ──────────────────────────────────────────────
# Değerlendirme
# ──────────────────────────────────────────────

def evaluate():
    print("📊 PRAEVIDIO AI — Risk Modeli Değerlendirme (v2)")
    print("=" * 60)

    df = pd.read_csv(NLST_CLEANED_PATH)
    print(f"   NLST: {len(df)} katılımcı, {int(df['has_cancer'].sum())} kanser vakası "
          f"(taban %{100*df['has_cancer'].mean():.2f})")

    # Hold-out: CPT train'den hesaplanır, test'te değerlendirilir (iyimser sapmayı önler)
    train, test = train_test_split(
        df, test_size=0.30, stratify=df["has_cancer"], random_state=42
    )
    cpts = compute_nlst_cancer_cpt(train)

    def risk_of(row):
        key = (int(row["age_group"]), int(row["gender_norm"]), int(row["cigsmok"]))
        return cpts.get(key, train["has_cancer"].mean())

    y_true = test["has_cancer"].values.astype(int)
    y_prob = test.apply(risk_of, axis=1).values.astype(float)

    # --- Metrikler ---
    auc = roc_auc_score(y_true, y_prob)
    auprc = average_precision_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    ece = expected_calibration_error(y_true, y_prob)
    slope, intercept = calibration_slope_intercept(y_true, y_prob)

    thr_metrics = {}
    for t in RISK_THRESHOLDS:
        sens, spec = sensitivity_specificity(y_true, y_prob, t)
        thr_metrics[f"@{int(t*100)}%"] = {"sensitivity": sens, "specificity": spec}

    print("\n--- AYRIM (Discrimination) ---")
    print(f"   AUC-ROC : {auc:.3f}   (0.5=şans, 1.0=mükemmel)")
    print(f"   AUPRC   : {auprc:.3f}   (taban={df['has_cancer'].mean():.3f})")
    print("\n--- KALİBRASYON ---")
    print(f"   Brier   : {brier:.4f}  (düşük=iyi)")
    print(f"   ECE     : {ece:.4f}")
    print(f"   Eğim    : {slope:.3f} (ideal 1.0) | Kesişim: {intercept:.3f} (ideal 0.0)")
    print("\n--- EŞİK BAZLI (klinik operasyon noktaları) ---")
    for k, v in thr_metrics.items():
        print(f"   {k}: duyarlılık={v['sensitivity']:.3f}, özgüllük={v['specificity']:.3f}")

    # --- Grafikler ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _plot_roc(y_true, y_prob, auc)
    _plot_calibration(y_true, y_prob)
    _plot_dca(y_true, y_prob)

    metrics = {
        "scope": "NLST hold-out (P(cancer|age,gender,smoking)). Semptom/yeni faktör "
                 "CPT'leri literatür temelli, NLST ile doğrulanamaz.",
        "n_test": int(len(test)),
        "base_rate": float(df["has_cancer"].mean()),
        "discrimination": {"auc_roc": float(auc), "auprc": float(auprc)},
        "calibration": {"brier": float(brier), "ece": float(ece),
                        "slope": slope, "intercept": intercept},
        "threshold_metrics": thr_metrics,
        "note": "F1/accuracy birincil metrik DEĞİL — bkz. modül başlığı.",
    }
    out = RESULTS_DIR / "evaluation_metrics_v2.json"
    out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Metrikler: {out}")
    print("📊 Grafikler: roc_curve_v2.png, calibration_curve_v2.png, decision_curve_v2.png")
    return metrics


def _plot_roc(y_true, y_prob, auc):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    plt.figure(figsize=(6, 6))
    plt.plot(fpr, tpr, color="#e74c3c", lw=2, label=f"Hibrit BBN (AUC={auc:.3f})")
    plt.plot([0, 1], [0, 1], "--", color="#999", label="Şans (0.5)")
    plt.xlabel("1 - Özgüllük (FPR)"); plt.ylabel("Duyarlılık (TPR)")
    plt.title("ROC Eğrisi — Risk Faktörü Modeli (NLST hold-out)")
    plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(RESULTS_DIR / "roc_curve_v2.png", dpi=150); plt.close()


def _plot_calibration(y_true, y_prob):
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy="quantile")
    plt.figure(figsize=(6, 6))
    plt.plot(mean_pred, frac_pos, "o-", color="#2980b9", label="Hibrit BBN")
    plt.plot([0, 1], [0, 1], "--", color="#999", label="Mükemmel kalibrasyon")
    plt.xlabel("Tahmin edilen risk"); plt.ylabel("Gözlenen frekans")
    plt.title("Kalibrasyon (Reliability) Eğrisi")
    plt.legend(loc="upper left"); plt.tight_layout()
    plt.savefig(RESULTS_DIR / "calibration_curve_v2.png", dpi=150); plt.close()


def _plot_dca(y_true, y_prob):
    thr, nb_model, nb_all = decision_curve_analysis(y_true, y_prob)
    plt.figure(figsize=(7, 5))
    plt.plot(thr, nb_model, color="#e74c3c", lw=2, label="Model")
    plt.plot(thr, nb_all, "--", color="#888", label="Herkesi tara")
    plt.axhline(0, color="#333", lw=1, label="Kimseyi tarama")
    plt.xlabel("Eşik olasılığı (pt)"); plt.ylabel("Net fayda")
    plt.title("Decision Curve Analysis — Klinik Fayda")
    plt.legend(loc="upper right"); plt.ylim(bottom=min(0, min(nb_model)) - 0.005)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "decision_curve_v2.png", dpi=150); plt.close()


if __name__ == "__main__":
    evaluate()
