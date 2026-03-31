"""
Praevidio AI - Bayesian Belief Network for Lung Cancer Risk Assessment
=====================================================================
Implements a Bayesian Network using pgmpy to model causal relationships
between risk factors, symptoms, and lung cancer diagnosis.

The network structure is based on medical domain knowledge:
- Risk factors (Smoking, Age, Gender) → influence symptoms
- Symptoms (Coughing, Shortness of Breath, etc.) → indicate cancer
- Conditional Probability Tables (CPTs) are learned from the dataset
"""

import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.estimators import MaximumLikelihoodEstimator, BayesianEstimator
from pgmpy.estimators import HillClimbSearch, K2, BDeu
from pgmpy.inference import VariableElimination
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, classification_report, confusion_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
CLEANED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "lung_cancer_cleaned.csv"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "data" / "models"
RESULTS_DIR = PROJECT_ROOT / "data" / "processed" / "model_results"


# ==============================================================
# 1. NETWORK STRUCTURE DEFINITION
# ==============================================================

def get_expert_structure():
    """
    Define the BBN structure based on medical domain knowledge.
    
    Structure rationale:
    - Smoking is the primary risk factor → causes multiple symptoms
    - Age and Gender influence cancer risk directly
    - Chronic Disease influences respiratory symptoms
    - Allergy influences respiratory symptoms (differential diagnosis)
    - All symptoms + risk factors → LUNG_CANCER
    """
    edges = [
        # Risk factors → Cancer
        ("SMOKING", "LUNG_CANCER"),
        ("AGE", "LUNG_CANCER"),
        ("GENDER", "LUNG_CANCER"),
        ("CHRONIC_DISEASE", "LUNG_CANCER"),
        ("ALCOHOL_CONSUMING", "LUNG_CANCER"),

        # Symptoms → Cancer
        ("COUGHING", "LUNG_CANCER"),
        ("SHORTNESS_OF_BREATH", "LUNG_CANCER"),
        ("WHEEZING", "LUNG_CANCER"),
        ("CHEST_PAIN", "LUNG_CANCER"),
        ("FATIGUE", "LUNG_CANCER"),
        ("SWALLOWING_DIFFICULTY", "LUNG_CANCER"),
        ("YELLOW_FINGERS", "LUNG_CANCER"),
        ("ALLERGY", "LUNG_CANCER"),
        ("ANXIETY", "LUNG_CANCER"),

        # Causal relationships between features (domain knowledge)
        ("SMOKING", "COUGHING"),        # Smoking causes coughing
        ("SMOKING", "WHEEZING"),        # Smoking causes wheezing
        ("SMOKING", "YELLOW_FINGERS"),  # Smoking causes yellow fingers
        ("SMOKING", "SHORTNESS_OF_BREATH"),  # Smoking causes dyspnea
        ("CHRONIC_DISEASE", "FATIGUE"),      # Chronic disease causes fatigue
        ("CHRONIC_DISEASE", "COUGHING"),     # Chronic disease causes coughing
        ("CHRONIC_DISEASE", "SHORTNESS_OF_BREATH"),  # Chronic disease causes dyspnea
        ("ALLERGY", "COUGHING"),        # Allergy causes coughing
        ("ALLERGY", "WHEEZING"),        # Allergy causes wheezing
    ]
    return edges


def get_data_driven_structure(df):
    """
    Learn the network structure directly from data using Hill Climb Search.
    This is an alternative to the expert-defined structure.
    """
    print("🔍 Learning structure from data (Hill Climb Search)...")
    hc = HillClimbSearch(df)
    best_model = hc.estimate(scoring_method=K2(df))
    print(f"   Found {len(best_model.edges())} edges")
    return list(best_model.edges())


# ==============================================================
# 2. MODEL TRAINING
# ==============================================================

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for BBN training by discretizing continuous variables."""
    df_bbn = df.copy()

    # Discretize AGE into bins
    df_bbn["AGE"] = pd.cut(
        df_bbn["AGE"],
        bins=[0, 44, 59, 74, 100],
        labels=[0, 1, 2, 3]  # 0: Young, 1: Middle, 2: Senior, 3: Elderly
    ).astype(int)

    # Drop AGE_GROUP (we have discretized AGE now)
    if "AGE_GROUP" in df_bbn.columns:
        df_bbn = df_bbn.drop(columns=["AGE_GROUP"])

    # Drop PEER_PRESSURE (not clinically relevant for BBN)
    if "PEER_PRESSURE" in df_bbn.columns:
        df_bbn = df_bbn.drop(columns=["PEER_PRESSURE"])

    # Ensure all columns are integer type
    for col in df_bbn.columns:
        df_bbn[col] = df_bbn[col].astype(int)

    return df_bbn


def train_model(df: pd.DataFrame, structure: str = "expert") -> DiscreteBayesianNetwork:
    """
    Train the Bayesian Network model.
    
    Args:
        df: Prepared DataFrame (all columns discretized)
        structure: "expert" for domain-knowledge structure, "data" for learned structure
    
    Returns:
        Trained BayesianNetwork model
    """
    print(f"\n🧠 TRAINING BAYESIAN NETWORK ({structure} structure)")
    print("=" * 60)

    # Get structure
    if structure == "expert":
        edges = get_expert_structure()
        print(f"   Using expert-defined structure: {len(edges)} edges")
    else:
        edges = get_data_driven_structure(df)
        print(f"   Using data-driven structure: {len(edges)} edges")

    # Create model
    model = DiscreteBayesianNetwork(edges)

    # Fit CPTs using Maximum Likelihood Estimation
    print("   Fitting Conditional Probability Tables (MLE)...")
    model.fit(df, estimator=MaximumLikelihoodEstimator)

    # Validate
    print(f"   ✅ Model fitted successfully!")
    print(f"   Nodes: {len(model.nodes())}")
    print(f"   Edges: {len(model.edges())}")

    # Print some CPT info
    print(f"\n   📊 CPT Summary:")
    for node in ["LUNG_CANCER", "COUGHING", "SHORTNESS_OF_BREATH"]:
        if node in model.nodes():
            cpd = model.get_cpds(node)
            print(f"   {node}: {cpd.variable} | parents: {cpd.get_evidence()}")

    return model


# ==============================================================
# 3. INFERENCE ENGINE
# ==============================================================

class LungCancerRiskEngine:
    """
    Risk scoring engine that wraps the BBN for easy inference.
    Takes patient evidence and returns risk probability.
    """

    # ICD-10 mapping for output
    ICD10_MAP = {
        "SMOKING": "F17",
        "COUGHING": "R05",
        "SHORTNESS_OF_BREATH": "R06.0",
        "WHEEZING": "R06.2",
        "CHEST_PAIN": "R07.9",
        "SWALLOWING_DIFFICULTY": "R13",
        "FATIGUE": "R53",
        "YELLOW_FINGERS": "R23.8",
        "ALCOHOL_CONSUMING": "F10",
        "ANXIETY": "F41",
        "ALLERGY": "T78.4",
        "CHRONIC_DISEASE": "Z87.39",
        "LUNG_CANCER": "C34"
    }

    RISK_LEVELS = {
        "low": {"range": (0, 0.30), "label_tr": "Düşük Risk", "label_en": "Low Risk", "color": "#2ecc71"},
        "moderate": {"range": (0.30, 0.60), "label_tr": "Orta Risk", "label_en": "Moderate Risk", "color": "#f39c12"},
        "high": {"range": (0.60, 1.0), "label_tr": "Yüksek Risk", "label_en": "High Risk", "color": "#e74c3c"},
    }

    def __init__(self, model: DiscreteBayesianNetwork):
        self.model = model
        self.inference = VariableElimination(model)
        print("✅ Risk Engine initialized")

    def predict_risk(self, evidence: dict) -> dict:
        """
        Calculate lung cancer risk given patient evidence.
        
        Args:
            evidence: Dict of observed variables, e.g.,
                      {"SMOKING": 1, "COUGHING": 1, "AGE": 2}
        
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
        risk_level = "low"
        for level, info in self.RISK_LEVELS.items():
            if info["range"][0] <= cancer_prob < info["range"][1]:
                risk_level = level
                break
        if cancer_prob >= 0.60:
            risk_level = "high"

        # Map symptoms to ICD-10
        icd10_findings = []
        for symptom, value in filtered_evidence.items():
            if value == 1 and symptom in self.ICD10_MAP:
                icd10_findings.append({
                    "code": self.ICD10_MAP[symptom],
                    "feature": symptom,
                    "status": "Present"
                })

        return {
            "risk_score": round(cancer_prob * 100, 2),
            "risk_probability": round(cancer_prob, 4),
            "no_cancer_probability": round(no_cancer_prob, 4),
            "risk_level": risk_level,
            "risk_level_tr": self.RISK_LEVELS[risk_level]["label_tr"],
            "risk_level_en": self.RISK_LEVELS[risk_level]["label_en"],
            "evidence_provided": filtered_evidence,
            "icd10_findings": icd10_findings,
            "recommendation_tr": self._get_recommendation_tr(risk_level),
            "recommendation_en": self._get_recommendation_en(risk_level)
        }

    def _get_recommendation_tr(self, level: str) -> str:
        recommendations = {
            "low": "Şu an için belirgin bir risk faktörü tespit edilmemiştir. Yıllık sağlık kontrollerinizi ihmal etmeyiniz.",
            "moderate": "Bazı risk faktörleri tespit edilmiştir. En yakın sağlık kuruluşuna veya KETEM merkezine başvurmanızı öneririz.",
            "high": "Önemli risk faktörleri tespit edilmiştir. Acil olarak bir göğüs hastalıkları uzmanına veya onkoloji polikliniğine başvurmanızı şiddetle öneriyoruz."
        }
        return recommendations.get(level, "")

    def _get_recommendation_en(self, level: str) -> str:
        recommendations = {
            "low": "No significant risk factors detected at this time. Please maintain regular annual health check-ups.",
            "moderate": "Some risk factors have been identified. We recommend visiting your nearest healthcare facility or KETEM center.",
            "high": "Significant risk factors have been identified. We strongly recommend an urgent consultation with a pulmonologist or oncology department."
        }
        return recommendations.get(level, "")

    def batch_predict(self, df: pd.DataFrame) -> list:
        """Run prediction on a batch of patients."""
        predictions = []
        for _, row in df.iterrows():
            evidence = row.to_dict()
            # Remove target variable
            evidence.pop("LUNG_CANCER", None)
            try:
                result = self.predict_risk(evidence)
                predictions.append(1 if result["risk_probability"] >= 0.5 else 0)
            except Exception:
                predictions.append(0)
        return predictions


# ==============================================================
# 4. MODEL EVALUATION
# ==============================================================

def evaluate_model(model: DiscreteBayesianNetwork, df: pd.DataFrame, n_folds: int = 5) -> dict:
    """
    Evaluate the BBN model using K-Fold cross-validation.
    """
    print(f"\n📊 MODEL EVALUATION ({n_folds}-Fold Cross-Validation)")
    print("=" * 60)

    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    
    all_y_true = []
    all_y_pred = []
    fold_metrics = []

    for fold, (train_idx, test_idx) in enumerate(kf.split(df), 1):
        print(f"\n   Fold {fold}/{n_folds}...")
        
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]

        # Train model on this fold
        fold_model = DiscreteBayesianNetwork(get_expert_structure())
        fold_model.fit(train_df, estimator=MaximumLikelihoodEstimator)
        
        # Create inference engine
        engine = LungCancerRiskEngine(fold_model)
        
        # Predict
        y_true = test_df["LUNG_CANCER"].values
        y_pred = engine.batch_predict(test_df)

        all_y_true.extend(y_true)
        all_y_pred.extend(y_pred)

        # Fold metrics
        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred)
        
        fold_metrics.append({"fold": fold, "accuracy": acc, "f1": f1, "precision": prec, "recall": rec})
        print(f"   Acc: {acc:.4f} | F1: {f1:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f}")

    # Overall metrics
    overall = {
        "accuracy": accuracy_score(all_y_true, all_y_pred),
        "f1_score": f1_score(all_y_true, all_y_pred),
        "precision": precision_score(all_y_true, all_y_pred, zero_division=0),
        "recall": recall_score(all_y_true, all_y_pred),
        "fold_metrics": fold_metrics
    }

    print(f"\n   {'='*40}")
    print(f"   📋 OVERALL RESULTS:")
    print(f"   Accuracy:  {overall['accuracy']:.4f}")
    print(f"   F1 Score:  {overall['f1_score']:.4f}")
    print(f"   Precision: {overall['precision']:.4f}")
    print(f"   Recall:    {overall['recall']:.4f}")

    # Classification report
    print(f"\n   📊 Classification Report:")
    report = classification_report(all_y_true, all_y_pred, 
                                    target_names=["No Cancer", "Cancer"])
    print(report)

    # Confusion matrix
    cm = confusion_matrix(all_y_true, all_y_pred)
    overall["confusion_matrix"] = cm.tolist()

    return overall


def generate_evaluation_plots(metrics: dict, output_dir: Path):
    """Generate evaluation visualizations."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Plot 1: Confusion Matrix ---
    cm = np.array(metrics["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=["No Cancer", "Cancer"],
                yticklabels=["No Cancer", "Cancer"],
                annot_kws={"size": 16})
    ax.set_xlabel("Predicted", fontsize=13)
    ax.set_ylabel("Actual", fontsize=13)
    ax.set_title("Confusion Matrix (5-Fold CV)", fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ confusion_matrix.png")

    # --- Plot 2: Fold Metrics ---
    fold_df = pd.DataFrame(metrics["fold_metrics"])
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = range(len(fold_df))
    width = 0.2
    ax.bar([i - 1.5*width for i in x], fold_df["accuracy"], width, label="Accuracy", color="#3498db")
    ax.bar([i - 0.5*width for i in x], fold_df["f1"], width, label="F1 Score", color="#e74c3c")
    ax.bar([i + 0.5*width for i in x], fold_df["precision"], width, label="Precision", color="#2ecc71")
    ax.bar([i + 1.5*width for i in x], fold_df["recall"], width, label="Recall", color="#f39c12")
    
    ax.set_xlabel("Fold", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Model Performance per Fold", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Fold {i+1}" for i in x])
    ax.legend()
    ax.set_ylim(0, 1.1)
    
    plt.tight_layout()
    plt.savefig(output_dir / "fold_metrics.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ fold_metrics.png")


# ==============================================================
# 5. DEMO SCENARIOS
# ==============================================================

def run_demo_scenarios(engine: LungCancerRiskEngine):
    """Run sample patient scenarios to demonstrate the model."""
    print(f"\n🏥 DEMO PATIENT SCENARIOS")
    print("=" * 60)

    scenarios = [
        {
            "name": "Patient A — High Risk (Heavy Smoker, Multiple Symptoms)",
            "evidence": {
                "SMOKING": 1, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1,
                "WHEEZING": 1, "CHEST_PAIN": 1, "FATIGUE": 1,
                "YELLOW_FINGERS": 1, "AGE": 3, "GENDER": 1,
                "CHRONIC_DISEASE": 1
            }
        },
        {
            "name": "Patient B — Moderate Risk (Smoker, Some Symptoms)",
            "evidence": {
                "SMOKING": 1, "COUGHING": 1, "FATIGUE": 1,
                "AGE": 2, "GENDER": 1,
                "SHORTNESS_OF_BREATH": 0, "CHEST_PAIN": 0,
                "WHEEZING": 0, "YELLOW_FINGERS": 0
            }
        },
        {
            "name": "Patient C — Low Risk (Non-smoker, Young, No Major Symptoms)",
            "evidence": {
                "SMOKING": 0, "COUGHING": 0, "SHORTNESS_OF_BREATH": 0,
                "WHEEZING": 0, "CHEST_PAIN": 0, "FATIGUE": 0,
                "YELLOW_FINGERS": 0, "AGE": 0, "GENDER": 0,
                "ALLERGY": 1
            }
        },
        {
            "name": "Patient D — Elderly Non-Smoker with Respiratory Symptoms",
            "evidence": {
                "SMOKING": 0, "COUGHING": 1, "SHORTNESS_OF_BREATH": 1,
                "WHEEZING": 1, "CHEST_PAIN": 0, "FATIGUE": 1,
                "AGE": 3, "GENDER": 0,
                "CHRONIC_DISEASE": 1, "ALLERGY": 0
            }
        }
    ]

    results = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n   {'─'*50}")
        print(f"   🧑‍⚕️ {scenario['name']}")
        
        result = engine.predict_risk(scenario["evidence"])
        results.append({**result, "scenario": scenario["name"]})

        print(f"   Risk Score: {result['risk_score']}%")
        print(f"   Risk Level: {result['risk_level_tr']} ({result['risk_level_en']})")
        print(f"   ICD-10 Findings: {len(result['icd10_findings'])} codes")
        for finding in result["icd10_findings"]:
            print(f"     • {finding['code']}: {finding['feature']}")
        print(f"   💡 {result['recommendation_tr']}")

    return results


# ==============================================================
# MAIN EXECUTION
# ==============================================================

if __name__ == "__main__":
    print("🧠 PRAEVIDIO AI — Bayesian Belief Network Training")
    print("=" * 60)

    # Step 1: Load cleaned data
    print(f"\n📂 Loading cleaned data...")
    df = pd.read_csv(CLEANED_DATA_PATH)
    print(f"   ✅ Loaded {len(df)} samples")

    # Step 2: Prepare data for BBN
    print(f"\n🔧 Preparing data for BBN...")
    df_bbn = prepare_data(df)
    print(f"   ✅ Prepared data shape: {df_bbn.shape}")
    print(f"   Columns: {list(df_bbn.columns)}")

    # Step 3: Train model with expert structure
    model = train_model(df_bbn, structure="expert")

    # Step 4: Evaluate with K-Fold CV
    metrics = evaluate_model(model, df_bbn, n_folds=5)

    # Step 5: Generate evaluation plots
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    generate_evaluation_plots(metrics, RESULTS_DIR)

    # Step 6: Save model
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_OUTPUT_DIR / "bbn_lung_cancer_v1.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\n💾 Model saved to: {model_path}")

    # Step 7: Save metrics
    metrics_path = RESULTS_DIR / "evaluation_metrics.json"
    metrics_serializable = {k: v for k, v in metrics.items() if k != "confusion_matrix"}
    metrics_serializable["confusion_matrix"] = metrics["confusion_matrix"]
    with open(metrics_path, "w") as f:
        json.dump(metrics_serializable, f, indent=2)
    print(f"   ✅ Metrics saved to: {metrics_path}")

    # Step 8: Run demo scenarios
    engine = LungCancerRiskEngine(model)
    demo_results = run_demo_scenarios(engine)

    # Save demo results
    demo_path = RESULTS_DIR / "demo_scenarios.json"
    with open(demo_path, "w", encoding="utf-8") as f:
        json.dump(demo_results, f, indent=2, ensure_ascii=False)
    print(f"\n   ✅ Demo results saved to: {demo_path}")

    print("\n🎉 BBN Training Pipeline completed successfully!")
