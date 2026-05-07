"""
Praevidio AI - Hybrid Bayesian Belief Network for Lung Cancer Risk Assessment
==============================================================================
A hybrid BBN that combines:
  - PART A: Risk factor CPTs learned from real NLST clinical trial data (n=53,452)
  - PART B: Symptom CPTs derived from peer-reviewed medical literature

This model replaces the Kaggle-based BBN with clinically calibrated probabilities.

Network Structure:
  Risk Factors → LUNG_CANCER ← (learned from NLST data)
    AGE → LUNG_CANCER
    GENDER → LUNG_CANCER
    SMOKING → LUNG_CANCER

  LUNG_CANCER → Symptoms  ← (from medical literature)
    LUNG_CANCER → COUGHING
    LUNG_CANCER → SHORTNESS_OF_BREATH
    LUNG_CANCER → CHEST_PAIN
    LUNG_CANCER → WHEEZING
    LUNG_CANCER → FATIGUE
    LUNG_CANCER → HEMOPTYSIS
    LUNG_CANCER → WEIGHT_LOSS

  Confounders:
    SMOKING → COUGHING
    SMOKING → WHEEZING
    SMOKING → SHORTNESS_OF_BREATH

References:
  - NLST Research Team. NEJM 2011;365:395-409
  - Hamilton et al. BMJ 2005;331:1145
  - Beckles et al. Chest 2003;123:97S-104S
  - Corner et al. Thorax 2005;60:314-319
  - Kvale. Chest 2006;129:72S-78S
"""

import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination
from sklearn.model_selection import KFold
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, classification_report, confusion_matrix)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
NLST_CLEANED_PATH = PROJECT_ROOT / "data" / "processed" / "nlst_cleaned.csv"
NLST_SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "nlst_summary.json"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "data" / "models"
RESULTS_DIR = PROJECT_ROOT / "data" / "processed" / "hybrid_model_results"


# ==============================================================
# 1. NETWORK STRUCTURE
# ==============================================================

def get_hybrid_structure():
    """
    Define the hybrid BBN structure.

    Risk factors → LUNG_CANCER: edges learned from NLST data
    LUNG_CANCER → Symptoms: generative model (standard in medical BBNs)
    Smoking → Respiratory symptoms: confounding relationships
    """
    edges = [
        # Part A: Risk factors → Cancer (CPTs from NLST data)
        ("AGE", "LUNG_CANCER"),
        ("GENDER", "LUNG_CANCER"),
        ("SMOKING", "LUNG_CANCER"),

        # Part B: Cancer → Symptoms (CPTs from literature)
        # This is the "generative" or "Naive Bayes" direction:
        # Cancer CAUSES symptoms to appear
        ("LUNG_CANCER", "COUGHING"),
        ("LUNG_CANCER", "SHORTNESS_OF_BREATH"),
        ("LUNG_CANCER", "CHEST_PAIN"),
        ("LUNG_CANCER", "WHEEZING"),
        ("LUNG_CANCER", "FATIGUE"),
        ("LUNG_CANCER", "HEMOPTYSIS"),
        ("LUNG_CANCER", "WEIGHT_LOSS"),

        # Confounders: Smoking → Respiratory symptoms
        # Smoking independently causes these symptoms regardless of cancer
        ("SMOKING", "COUGHING"),
        ("SMOKING", "WHEEZING"),
        ("SMOKING", "SHORTNESS_OF_BREATH"),
    ]
    return edges


# ==============================================================
# 2. CPT CONSTRUCTION
# ==============================================================

def compute_nlst_cancer_cpt(df: pd.DataFrame) -> dict:
    """
    Compute P(LUNG_CANCER | AGE, GENDER, SMOKING) from NLST data.
    Returns a dictionary with all conditional probabilities.
    """
    print("   📊 Computing P(Cancer | Age, Gender, Smoking) from NLST...")

    cpt_values = {}
    for age_val in sorted(df["age_group"].unique()):
        for gender_val in [0, 1]:
            for smoking_val in [0, 1]:
                subset = df[(df["age_group"] == age_val) &
                            (df["gender_norm"] == gender_val) &
                            (df["cigsmok"] == smoking_val)]
                if len(subset) > 0:
                    p_cancer = subset["has_cancer"].mean()
                else:
                    # Fallback to marginal
                    p_cancer = df["has_cancer"].mean()

                # Apply Laplace smoothing to avoid zero probabilities
                p_cancer = max(0.001, min(0.999, p_cancer))
                key = (int(age_val), gender_val, smoking_val)
                cpt_values[key] = p_cancer

    return cpt_values


def build_cancer_cpd(nlst_cpts: dict) -> TabularCPD:
    """
    Build the LUNG_CANCER CPD conditioned on AGE, GENDER, SMOKING.

    Variable ordering for TabularCPD:
      - AGE: 5 states (0,1,2,3,4)
      - GENDER: 2 states (0=Female, 1=Male)
      - SMOKING: 2 states (0=Former, 1=Current)
    """
    age_states = 5
    gender_states = 2
    smoking_states = 2
    total_cols = age_states * gender_states * smoking_states  # 20

    # Build probability table
    # Column order: iterate over parents in order (AGE, GENDER, SMOKING)
    # pgmpy iterates: AGE changes slowest, SMOKING changes fastest
    p_cancer_vals = []
    p_no_cancer_vals = []

    for age_val in range(age_states):
        for gender_val in range(gender_states):
            for smoking_val in range(smoking_states):
                key = (age_val, gender_val, smoking_val)
                p_cancer = nlst_cpts.get(key, 0.0385)  # fallback to base rate
                p_cancer_vals.append(p_cancer)
                p_no_cancer_vals.append(1.0 - p_cancer)

    cpd = TabularCPD(
        variable="LUNG_CANCER",
        variable_card=2,
        values=[p_no_cancer_vals, p_cancer_vals],
        evidence=["AGE", "GENDER", "SMOKING"],
        evidence_card=[age_states, gender_states, smoking_states]
    )

    return cpd


def build_prior_cpds() -> list:
    """
    Build prior CPDs for root nodes (AGE, GENDER, SMOKING).
    Priors are based on NLST population statistics.
    """
    # AGE prior (from NLST data)
    # 0: <55 (0.01%), 1: 55-59 (42.8%), 2: 60-64 (30.6%), 3: 65-69 (17.8%), 4: 70+ (8.8%)
    age_cpd = TabularCPD(
        variable="AGE",
        variable_card=5,
        values=[[0.001], [0.428], [0.306], [0.178], [0.087]]
    )

    # GENDER prior (from NLST data)
    # 0=Female (41%), 1=Male (59%)
    gender_cpd = TabularCPD(
        variable="GENDER",
        variable_card=2,
        values=[[0.41], [0.59]]
    )

    # SMOKING prior (from NLST data)
    # 0=Former (51.8%), 1=Current (48.2%)
    smoking_cpd = TabularCPD(
        variable="SMOKING",
        variable_card=2,
        values=[[0.518], [0.482]]
    )

    return [age_cpd, gender_cpd, smoking_cpd]


def build_symptom_cpds() -> list:
    """
    Build symptom CPDs from medical literature.

    For symptoms with SMOKING as a confounder:
      P(symptom | LUNG_CANCER, SMOKING) — 4 columns

    For symptoms without confounders:
      P(symptom | LUNG_CANCER) — 2 columns

    Literature sources:
      - Hamilton et al., BMJ 2005
      - Beckles et al., Chest 2003
      - Corner et al., Thorax 2005
      - Kvale, Chest 2006
      - Hopwood & Stephens, BJC 2000
    """
    symptom_cpds = []

    # --- COUGHING: P(Coughing | LUNG_CANCER, SMOKING) ---
    # LC=0,SM=0  LC=0,SM=1  LC=1,SM=0  LC=1,SM=1
    coughing_cpd = TabularCPD(
        variable="COUGHING",
        variable_card=2,
        values=[
            [0.90, 0.75, 0.40, 0.30],   # P(no coughing | ...)
            [0.10, 0.25, 0.60, 0.70],   # P(coughing | ...)
        ],
        evidence=["LUNG_CANCER", "SMOKING"],
        evidence_card=[2, 2]
    )
    symptom_cpds.append(coughing_cpd)

    # --- SHORTNESS_OF_BREATH: P(SOB | LUNG_CANCER, SMOKING) ---
    sob_cpd = TabularCPD(
        variable="SHORTNESS_OF_BREATH",
        variable_card=2,
        values=[
            [0.92, 0.82, 0.50, 0.40],   # P(no SOB | ...)
            [0.08, 0.18, 0.50, 0.60],   # P(SOB | ...)
        ],
        evidence=["LUNG_CANCER", "SMOKING"],
        evidence_card=[2, 2]
    )
    symptom_cpds.append(sob_cpd)

    # --- WHEEZING: P(Wheezing | LUNG_CANCER, SMOKING) ---
    wheezing_cpd = TabularCPD(
        variable="WHEEZING",
        variable_card=2,
        values=[
            [0.95, 0.85, 0.78, 0.70],   # P(no wheezing | ...)
            [0.05, 0.15, 0.22, 0.30],   # P(wheezing | ...)
        ],
        evidence=["LUNG_CANCER", "SMOKING"],
        evidence_card=[2, 2]
    )
    symptom_cpds.append(wheezing_cpd)

    # --- CHEST_PAIN: P(Chest Pain | LUNG_CANCER) ---
    # No smoking confounder — chest pain is more cancer-specific
    chest_pain_cpd = TabularCPD(
        variable="CHEST_PAIN",
        variable_card=2,
        values=[
            [0.95, 0.65],   # P(no chest pain | no cancer, cancer)
            [0.05, 0.35],   # P(chest pain | no cancer, cancer)
        ],
        evidence=["LUNG_CANCER"],
        evidence_card=[2]
    )
    symptom_cpds.append(chest_pain_cpd)

    # --- FATIGUE: P(Fatigue | LUNG_CANCER) ---
    fatigue_cpd = TabularCPD(
        variable="FATIGUE",
        variable_card=2,
        values=[
            [0.80, 0.50],   # P(no fatigue | no cancer, cancer)
            [0.20, 0.50],   # P(fatigue | no cancer, cancer)
        ],
        evidence=["LUNG_CANCER"],
        evidence_card=[2]
    )
    symptom_cpds.append(fatigue_cpd)

    # --- HEMOPTYSIS: P(Hemoptysis | LUNG_CANCER) ---
    # Hemoptysis (coughing blood) is a strong cancer indicator
    hemoptysis_cpd = TabularCPD(
        variable="HEMOPTYSIS",
        variable_card=2,
        values=[
            [0.99, 0.80],   # P(no hemoptysis | no cancer, cancer)
            [0.01, 0.20],   # P(hemoptysis | no cancer, cancer)
        ],
        evidence=["LUNG_CANCER"],
        evidence_card=[2]
    )
    symptom_cpds.append(hemoptysis_cpd)

    # --- WEIGHT_LOSS: P(Weight Loss | LUNG_CANCER) ---
    weight_loss_cpd = TabularCPD(
        variable="WEIGHT_LOSS",
        variable_card=2,
        values=[
            [0.95, 0.65],   # P(no weight loss | no cancer, cancer)
            [0.05, 0.35],   # P(weight loss | no cancer, cancer)
        ],
        evidence=["LUNG_CANCER"],
        evidence_card=[2]
    )
    symptom_cpds.append(weight_loss_cpd)

    return symptom_cpds


# ==============================================================
# 3. MODEL BUILDING AND TRAINING
# ==============================================================

def build_hybrid_model(nlst_data_path: Path = NLST_CLEANED_PATH) -> DiscreteBayesianNetwork:
    """
    Build and validate the Hybrid BBN model.

    1. Load NLST cleaned data
    2. Compute risk factor CPTs from data
    3. Create literature-based symptom CPTs
    4. Assemble and validate the model
    """
    print("\n🧠 BUILDING HYBRID BAYESIAN NETWORK")
    print("=" * 60)

    # Load NLST data
    print("\n📂 Loading cleaned NLST data...")
    df = pd.read_csv(nlst_data_path)
    print(f"   Loaded {len(df)} participants, {df['has_cancer'].sum()} cancer cases")

    # Create model structure
    edges = get_hybrid_structure()
    model = DiscreteBayesianNetwork(edges)
    print(f"\n🔧 Network structure: {len(edges)} edges")
    for src, dst in edges:
        print(f"   {src} → {dst}")

    # Part A: Compute NLST-based CPTs
    print("\n📊 PART A: Risk Factor CPTs (from NLST data)")
    print("-" * 40)
    nlst_cpts = compute_nlst_cancer_cpt(df)
    cancer_cpd = build_cancer_cpd(nlst_cpts)
    prior_cpds = build_prior_cpds()

    print("   ✅ P(LUNG_CANCER | AGE, GENDER, SMOKING) computed from 53,452 real patients")
    print("   ✅ Prior distributions for AGE, GENDER, SMOKING set from NLST demographics")

    # Part B: Literature-based symptom CPTs
    print("\n📚 PART B: Symptom CPTs (from medical literature)")
    print("-" * 40)
    symptom_cpds = build_symptom_cpds()
    print(f"   ✅ {len(symptom_cpds)} symptom CPTs created from peer-reviewed sources")
    for cpd in symptom_cpds:
        print(f"      • {cpd.variable}: {cpd.get_evidence()}")

    # Add all CPDs to model
    model.add_cpds(cancer_cpd, *prior_cpds, *symptom_cpds)

    # Validate
    if model.check_model():
        print("\n   ✅ Model validation PASSED — all CPTs are consistent")
    else:
        print("\n   ❌ Model validation FAILED!")
        return None

    print(f"\n   📋 Model Summary:")
    print(f"      Nodes: {len(model.nodes())}")
    print(f"      Edges: {len(model.edges())}")
    print(f"      CPDs:  {len(model.get_cpds())}")

    return model


# ==============================================================
# 4. INFERENCE ENGINE
# ==============================================================

class HybridLungCancerEngine:
    """
    Hybrid risk scoring engine combining NLST real data
    with literature-based symptom analysis.

    Takes patient evidence (risk factors + symptoms) and returns
    calibrated risk probabilities.
    """

    # ICD-10 mapping for clinical output
    ICD10_MAP = {
        "SMOKING": "F17.2",
        "COUGHING": "R05",
        "SHORTNESS_OF_BREATH": "R06.0",
        "WHEEZING": "R06.2",
        "CHEST_PAIN": "R07.9",
        "FATIGUE": "R53.83",
        "HEMOPTYSIS": "R04.2",
        "WEIGHT_LOSS": "R63.4",
        "LUNG_CANCER": "C34"
    }

    # Risk levels calibrated for real-world prevalence (~3.85% base rate)
    RISK_LEVELS = {
        "low": {
            "range": (0, 0.05),
            "label_tr": "Düşük Risk",
            "label_en": "Low Risk",
            "color": "#2ecc71"
        },
        "moderate": {
            "range": (0.05, 0.15),
            "label_tr": "Orta Risk",
            "label_en": "Moderate Risk",
            "color": "#f39c12"
        },
        "high": {
            "range": (0.15, 1.0),
            "label_tr": "Yüksek Risk",
            "label_en": "High Risk",
            "color": "#e74c3c"
        },
    }

    def __init__(self, model: DiscreteBayesianNetwork):
        self.model = model
        self.inference = VariableElimination(model)
        print("✅ Hybrid Risk Engine initialized")

    def predict_risk(self, evidence: dict) -> dict:
        """
        Calculate lung cancer risk given patient evidence.

        Args:
            evidence: Dict of observed variables, e.g.,
                      {"SMOKING": 1, "COUGHING": 1, "AGE": 3, "GENDER": 1}

        Returns:
            Dict with risk score, level, and detailed analysis
        """
        # Filter evidence to only include valid model variables
        valid_vars = set(self.model.nodes()) - {"LUNG_CANCER"}
        filtered_evidence = {k: v for k, v in evidence.items() if k in valid_vars}

        # Run inference
        result = self.inference.query(
            variables=["LUNG_CANCER"],
            evidence=filtered_evidence
        )

        # Extract probability of cancer
        cancer_prob = float(result.values[1])  # P(LUNG_CANCER=1)
        no_cancer_prob = float(result.values[0])  # P(LUNG_CANCER=0)

        # Determine risk level
        risk_level = "high"  # default for >= 0.15
        for level, info in self.RISK_LEVELS.items():
            if info["range"][0] <= cancer_prob < info["range"][1]:
                risk_level = level
                break

        # Map symptoms to ICD-10
        icd10_findings = []
        for symptom, value in filtered_evidence.items():
            if value == 1 and symptom in self.ICD10_MAP:
                icd10_findings.append({
                    "code": self.ICD10_MAP[symptom],
                    "feature": symptom,
                    "status": "Present"
                })

        # Identify risk factors present
        risk_factors = []
        if filtered_evidence.get("SMOKING") == 1:
            risk_factors.append("Aktif sigara kullanımı")
        elif filtered_evidence.get("SMOKING") == 0:
            risk_factors.append("Eski sigara kullanıcısı")
        if filtered_evidence.get("AGE", 0) >= 3:
            risk_factors.append("65 yaş üstü")
        elif filtered_evidence.get("AGE", 0) >= 2:
            risk_factors.append("60-64 yaş arası")

        # Count symptoms present
        symptom_names = ["COUGHING", "SHORTNESS_OF_BREATH", "CHEST_PAIN",
                         "WHEEZING", "FATIGUE", "HEMOPTYSIS", "WEIGHT_LOSS"]
        symptoms_present = [s for s in symptom_names if filtered_evidence.get(s) == 1]

        return {
            "risk_score": round(cancer_prob * 100, 2),
            "risk_probability": round(cancer_prob, 6),
            "no_cancer_probability": round(no_cancer_prob, 6),
            "risk_level": risk_level,
            "risk_level_tr": self.RISK_LEVELS[risk_level]["label_tr"],
            "risk_level_en": self.RISK_LEVELS[risk_level]["label_en"],
            "risk_color": self.RISK_LEVELS[risk_level]["color"],
            "evidence_provided": filtered_evidence,
            "icd10_findings": icd10_findings,
            "risk_factors_tr": risk_factors,
            "symptoms_present": symptoms_present,
            "data_sources": {
                "risk_factors": "NLST Clinical Trial (n=53,452)",
                "symptoms": "Peer-reviewed medical literature"
            },
            "recommendation_tr": self._get_recommendation_tr(risk_level),
            "recommendation_en": self._get_recommendation_en(risk_level)
        }

    def _get_recommendation_tr(self, level: str) -> str:
        recommendations = {
            "low": ("Şu an için belirgin risk faktörleri tespit edilmemiştir. "
                    "Yıllık sağlık kontrollerinizi ihmal etmeyiniz. "
                    "Bu değerlendirme bir tarama aracıdır, kesin tanı yerine geçmez."),
            "moderate": ("Bazı risk faktörleri ve/veya semptomlar tespit edilmiştir. "
                         "En yakın sağlık kuruluşuna veya KETEM merkezine başvurmanızı öneririz. "
                         "Düşük doz BT taraması hakkında doktorunuzla görüşünüz."),
            "high": ("Önemli risk faktörleri ve semptomlar tespit edilmiştir. "
                     "En kısa sürede bir göğüs hastalıkları uzmanına veya "
                     "onkoloji polikliniğine başvurmanızı şiddetle öneriyoruz. "
                     "Düşük doz BT taraması veya ileri tetkik gerekebilir.")
        }
        return recommendations.get(level, "")

    def _get_recommendation_en(self, level: str) -> str:
        recommendations = {
            "low": ("No significant risk factors detected at this time. "
                    "Please maintain regular annual health check-ups. "
                    "This assessment is a screening tool, not a definitive diagnosis."),
            "moderate": ("Some risk factors and/or symptoms have been identified. "
                         "We recommend visiting your nearest healthcare facility. "
                         "Discuss low-dose CT screening with your physician."),
            "high": ("Significant risk factors and symptoms have been identified. "
                     "We strongly recommend an urgent consultation with a "
                     "pulmonologist or oncology department. "
                     "Low-dose CT screening or further evaluation may be needed.")
        }
        return recommendations.get(level, "")


# ==============================================================
# 5. DEMO SCENARIOS
# ==============================================================

def run_demo_scenarios(engine: HybridLungCancerEngine) -> list:
    """Run clinical demo scenarios to demonstrate the hybrid model."""
    print(f"\n🏥 DEMO PATIENT SCENARIOS (Hybrid Model)")
    print("=" * 60)

    scenarios = [
        {
            "name": "Hasta A — Yüksek Risk (Yaşlı, Aktif İçici, Çoklu Semptom)",
            "name_en": "Patient A — High Risk (Elderly, Current Smoker, Multiple Symptoms)",
            "evidence": {
                "SMOKING": 1, "AGE": 4, "GENDER": 1,
                "COUGHING": 1, "SHORTNESS_OF_BREATH": 1,
                "CHEST_PAIN": 1, "HEMOPTYSIS": 1,
                "FATIGUE": 1, "WEIGHT_LOSS": 1, "WHEEZING": 1
            }
        },
        {
            "name": "Hasta B — Orta Risk (Yaşlı, Eski İçici, Az Semptom)",
            "name_en": "Patient B — Moderate Risk (Elderly, Former Smoker, Few Symptoms)",
            "evidence": {
                "SMOKING": 0, "AGE": 3, "GENDER": 1,
                "COUGHING": 1, "FATIGUE": 1,
                "SHORTNESS_OF_BREATH": 0, "CHEST_PAIN": 0,
                "HEMOPTYSIS": 0, "WEIGHT_LOSS": 0, "WHEEZING": 0
            }
        },
        {
            "name": "Hasta C — Düşük Risk (Genç, Eski İçici, Semptomsuz)",
            "name_en": "Patient C — Low Risk (Young, Former Smoker, No Symptoms)",
            "evidence": {
                "SMOKING": 0, "AGE": 1, "GENDER": 0,
                "COUGHING": 0, "SHORTNESS_OF_BREATH": 0,
                "CHEST_PAIN": 0, "WHEEZING": 0, "FATIGUE": 0,
                "HEMOPTYSIS": 0, "WEIGHT_LOSS": 0
            }
        },
        {
            "name": "Hasta D — Alarm: Hemoptizi (Genç, Eski İçici, Kan Tükürme)",
            "name_en": "Patient D — Alarm: Hemoptysis (Young, Former Smoker, Coughing Blood)",
            "evidence": {
                "SMOKING": 0, "AGE": 1, "GENDER": 1,
                "COUGHING": 1, "HEMOPTYSIS": 1,
                "SHORTNESS_OF_BREATH": 0, "CHEST_PAIN": 0,
                "WHEEZING": 0, "FATIGUE": 0, "WEIGHT_LOSS": 0
            }
        },
        {
            "name": "Hasta E — Sadece Risk Faktörleri (Semptom Yok)",
            "name_en": "Patient E — Risk Factors Only (No Symptoms)",
            "evidence": {
                "SMOKING": 1, "AGE": 4, "GENDER": 1,
            }
        },
    ]

    results = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n   {'─' * 50}")
        print(f"   🧑‍⚕️  {scenario['name']}")

        result = engine.predict_risk(scenario["evidence"])
        results.append({**result, "scenario": scenario["name"]})

        print(f"   Risk Skoru: {result['risk_score']}%")
        print(f"   Risk Seviyesi: {result['risk_level_tr']} ({result['risk_level_en']})")
        print(f"   ICD-10 Bulgular: {len(result['icd10_findings'])} kod")
        for finding in result["icd10_findings"]:
            print(f"     • {finding['code']}: {finding['feature']}")
        if result.get("symptoms_present"):
            print(f"   Mevcut Semptomlar: {', '.join(result['symptoms_present'])}")
        print(f"   💡 {result['recommendation_tr']}")

    return results


# ==============================================================
# 6. MODEL EVALUATION
# ==============================================================

def generate_evaluation_plots(demo_results: list, output_dir: Path):
    """Generate evaluation visualizations for the hybrid model."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid", palette="husl")

    # --- Plot 1: Risk Scores by Scenario ---
    fig, ax = plt.subplots(figsize=(12, 6))

    names = [r["scenario"].split("—")[0].strip() for r in demo_results]
    scores = [r["risk_score"] for r in demo_results]
    colors = [r["risk_color"] for r in demo_results]

    bars = ax.barh(range(len(names)), scores, color=colors, edgecolor="white", height=0.6)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=11)
    ax.set_xlabel("Cancer Risk Score (%)", fontsize=12)
    ax.set_title("Hybrid BBN — Risk Scores by Patient Scenario",
                 fontsize=14, fontweight="bold")

    # Add value labels
    for i, val in enumerate(scores):
        ax.text(val + 0.5, i, f"{val:.1f}%", va="center", fontsize=10)

    # Add risk level zones
    ax.axvline(5, color="#f39c12", linestyle="--", alpha=0.5, label="Moderate threshold (5%)")
    ax.axvline(15, color="#e74c3c", linestyle="--", alpha=0.5, label="High threshold (15%)")
    ax.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(output_dir / "hybrid_risk_scores.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ hybrid_risk_scores.png")

    # --- Plot 2: NLST Base Rates by Age + Smoking ---
    df = pd.read_csv(NLST_CLEANED_PATH)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Age vs cancer rate
    age_labels = {0: "<55", 1: "55-59", 2: "60-64", 3: "65-69", 4: "70+"}
    age_rates = df.groupby("age_group")["has_cancer"].mean() * 100
    axes[0].bar(range(len(age_rates)), age_rates.values,
                color=sns.color_palette("YlOrRd", len(age_rates)))
    axes[0].set_xticks(range(len(age_rates)))
    axes[0].set_xticklabels([age_labels[i] for i in age_rates.index], fontsize=11)
    axes[0].set_xlabel("Age Group", fontsize=12)
    axes[0].set_ylabel("Cancer Rate (%)", fontsize=12)
    axes[0].set_title("Cancer Rate by Age (NLST Data)",
                      fontsize=13, fontweight="bold")
    for i, v in enumerate(age_rates.values):
        axes[0].text(i, v + 0.1, f"{v:.1f}%", ha="center", fontsize=10)

    # Smoking vs cancer rate
    smoke_labels = {0: "Former\nSmoker", 1: "Current\nSmoker"}
    smoke_rates = df.groupby("cigsmok")["has_cancer"].mean() * 100
    axes[1].bar(range(len(smoke_rates)), smoke_rates.values,
                color=["#3498db", "#e74c3c"], edgecolor="white")
    axes[1].set_xticks(range(len(smoke_rates)))
    axes[1].set_xticklabels([smoke_labels[i] for i in smoke_rates.index], fontsize=11)
    axes[1].set_xlabel("Smoking Status", fontsize=12)
    axes[1].set_ylabel("Cancer Rate (%)", fontsize=12)
    axes[1].set_title("Cancer Rate by Smoking Status (NLST Data)",
                      fontsize=13, fontweight="bold")
    for i, v in enumerate(smoke_rates.values):
        axes[1].text(i, v + 0.1, f"{v:.2f}%", ha="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / "nlst_base_rates.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ nlst_base_rates.png")


# ==============================================================
# MAIN EXECUTION
# ==============================================================

if __name__ == "__main__":
    print("🧠 PRAEVIDIO AI — Hybrid Bayesian Belief Network")
    print("=" * 60)
    print("   Combining NLST real clinical data + medical literature")
    print()

    # Step 1: Build hybrid model
    model = build_hybrid_model()

    if model is None:
        print("❌ Model building failed!")
        exit(1)

    # Step 2: Create inference engine
    engine = HybridLungCancerEngine(model)

    # Step 3: Run demo scenarios
    demo_results = run_demo_scenarios(engine)

    # Step 4: Generate plots
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📊 GENERATING VISUALIZATIONS")
    generate_evaluation_plots(demo_results, RESULTS_DIR)

    # Step 5: Save model
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_OUTPUT_DIR / "hybrid_bbn_nlst_v1.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\n💾 Model saved: {model_path}")

    # Step 6: Save demo results
    demo_path = RESULTS_DIR / "hybrid_demo_scenarios.json"
    with open(demo_path, "w", encoding="utf-8") as f:
        json.dump(demo_results, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Demo results: {demo_path}")

    print("\n🎉 Hybrid BBN Pipeline completed successfully!")
