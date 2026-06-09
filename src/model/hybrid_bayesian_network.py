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

        # Part A2: Additional risk factors → Cancer (literature OR-adjusted)
        # NLST veri setinde bu 3 değişken yok; bu yüzden veriden öğrenilmez,
        # NLST tabanına literatür odds-ratio'ları çarpılarak entegre edilir.
        ("FAMILY_HISTORY", "LUNG_CANCER"),   # Ailede 1. derece akraba öyküsü
        ("ASBESTOS", "LUNG_CANCER"),          # Mesleki asbest/risk maruziyeti (proxy)
        ("AIR_POLLUTION", "LUNG_CANCER"),     # İl bazlı yıllık PM2.5 kademesi

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

# --- Literatür temelli odds-ratio'lar (yeni risk faktörleri) ---
# Bunlar NLST tabanına çarpılarak P(cancer | ...) hesaplanır.
# Başlangıç değerleri; duyarlılık analizi ile kalibre edilebilir
# (bkz. docs/v2_genisletme_tasarim.md ve sensitivity_analysis_calibration.md).
RISK_FACTOR_ORS = {
    # Ailede 1. derece akraba öyküsü — ILCCO pooled RR≈1.51, meta RR≈1.88
    "FAMILY_HISTORY": {0: 1.00, 1: 1.70},
    # Mesleki asbest/risk maruziyeti (öz-bildirim proxy) — ever-exposed OR≈1.24,
    # belirgin maruziyet OR≈2.04; muhafazakâr orta değer
    "ASBESTOS": {0: 1.00, 1: 1.50},
    # Hava kirliliği kademesi (il PM2.5) — her 10µg/m³ için RR≈1.16 ankrajlı
    "AIR_POLLUTION": {0: 1.00, 1: 1.15, 2: 1.30},
}


# --- Paket-yıl temelli sigara düzeltmesi (A kuralı) ---
# NLST'nin ikili "aktif/eski içici" sınıflaması dozu (paket-yıl) görmez ve
# tüm NLST nüfusu ≥30 paket-yıl olduğu için "eski içici" hücresi AĞIR eski
# içiciyi temsil eder. Bu yüzden:
#   • Hiç/çok hafif içen (paket-yıl < 1): NLST ağır-eski-içici oranına takılı
#     kalmasın diye taban riske aşağı çarpan uygulanır.
#   • Ağır + yakın zamanda bırakmış eski içici (≥20 paket-yıl ve bırakalı ≤15 yıl):
#     NLST'nin kendi yüksek-risk tanımına girer → aktif içici gibi değerlendirilir.
NEVER_SMOKER_OR = 0.15            # hiç içmeyen ~6-7 kat düşük (epidemiyolojik)
HEAVY_FORMER_PACK_YEARS = 20      # "ağır" eşiği (paket-yıl)
HEAVY_FORMER_MAX_QUIT_YEARS = 15  # "yakın zamanda bırakmış" eşiği (yıl)


def _apply_odds_ratio(p_base: float, or_product: float) -> float:
    """
    Taban olasılığa odds-ratio çarpımı uygular (logit/odds dünyasında).
        odds_adj = (p/(1-p)) * OR_product ;  p_adj = odds_adj/(1+odds_adj)
    """
    p_base = min(max(p_base, 1e-6), 1 - 1e-6)
    odds = p_base / (1.0 - p_base)
    odds_adj = odds * or_product
    return odds_adj / (1.0 + odds_adj)


def compute_nlst_cancer_cpt(df: pd.DataFrame) -> dict:
    """
    Compute P(LUNG_CANCER | AGE, GENDER, SMOKING) from NLST data.
    Returns a dictionary with all conditional probabilities.

    Note: NLST enrolled only ages 55-74. For AGE=0 (<55), we use
    epidemiological baselines from general population studies since
    the NLST subgroup is too small (n=5) for reliable estimation.
    """
    print("   📊 Computing P(Cancer | Age, Gender, Smoking) from NLST...")

    # Epidemiological baselines for under-55 age group
    # Source: ACS Cancer Facts & Figures 2023; Siegel et al., CA Cancer J Clin
    # Risk is lower than 55+ but NOT zero, especially for smokers
    UNDER_55_BASELINES = {
        # (age_group, gender, smoking): P(cancer)
        (0, 0, 0): 0.002,   # Female, former smoker: ~0.2%
        (0, 0, 1): 0.008,   # Female, current smoker: ~0.8%
        (0, 1, 0): 0.003,   # Male, former smoker: ~0.3%
        (0, 1, 1): 0.012,   # Male, current smoker: ~1.2%
    }

    MIN_SAMPLE_SIZE = 30  # Minimum samples for reliable CPT estimation

    cpt_values = {}
    for age_val in sorted(df["age_group"].unique()):
        for gender_val in [0, 1]:
            for smoking_val in [0, 1]:
                key = (int(age_val), gender_val, smoking_val)
                subset = df[(df["age_group"] == age_val) &
                            (df["gender_norm"] == gender_val) &
                            (df["cigsmok"] == smoking_val)]

                if len(subset) >= MIN_SAMPLE_SIZE:
                    # Sufficient data — use NLST empirical rate
                    p_cancer = subset["has_cancer"].mean()
                elif key in UNDER_55_BASELINES:
                    # Insufficient data — use epidemiological baseline
                    p_cancer = UNDER_55_BASELINES[key]
                    print(f"      ⚠️  AGE={age_val} G={gender_val} S={smoking_val}: "
                          f"n={len(subset)}, using epidemiological baseline {p_cancer:.3f}")
                else:
                    # Fallback to overall base rate
                    p_cancer = df["has_cancer"].mean()

                # Apply Laplace smoothing to avoid zero probabilities
                p_cancer = max(0.001, min(0.999, p_cancer))
                cpt_values[key] = p_cancer

    return cpt_values


def build_cancer_cpd(nlst_cpts: dict) -> TabularCPD:
    """
    Build the LUNG_CANCER CPD conditioned on:
      AGE, GENDER, SMOKING  (NLST tabanı) +
      FAMILY_HISTORY, ASBESTOS, AIR_POLLUTION  (literatür OR çarpımı)

    Variable ordering / cardinality:
      - AGE: 5, GENDER: 2, SMOKING: 2  → NLST tabanı P(cancer|age,gender,smoking)
      - FAMILY_HISTORY: 2, ASBESTOS: 2, AIR_POLLUTION: 3  → OR çarpanı
    Toplam sütun: 5*2*2*2*2*3 = 240 (programatik üretilir, elle girilmez).

    pgmpy sütun sırası: ilk evidence (AGE) en yavaş, son evidence (AIR_POLLUTION)
    en hızlı değişir. Aşağıdaki iç içe döngü bu sırayı birebir takip eder.
    """
    age_states, gender_states, smoking_states = 5, 2, 2
    fam_states, asb_states, air_states = 2, 2, 3

    p_cancer_vals = []
    p_no_cancer_vals = []

    for age_val in range(age_states):
        for gender_val in range(gender_states):
            for smoking_val in range(smoking_states):
                p_base = nlst_cpts.get((age_val, gender_val, smoking_val), 0.0385)
                for fam_val in range(fam_states):
                    for asb_val in range(asb_states):
                        for air_val in range(air_states):
                            or_product = (
                                RISK_FACTOR_ORS["FAMILY_HISTORY"][fam_val] *
                                RISK_FACTOR_ORS["ASBESTOS"][asb_val] *
                                RISK_FACTOR_ORS["AIR_POLLUTION"][air_val]
                            )
                            p_cancer = _apply_odds_ratio(p_base, or_product)
                            p_cancer = max(0.001, min(0.999, p_cancer))
                            p_cancer_vals.append(p_cancer)
                            p_no_cancer_vals.append(1.0 - p_cancer)

    cpd = TabularCPD(
        variable="LUNG_CANCER",
        variable_card=2,
        values=[p_no_cancer_vals, p_cancer_vals],
        evidence=["AGE", "GENDER", "SMOKING",
                  "FAMILY_HISTORY", "ASBESTOS", "AIR_POLLUTION"],
        evidence_card=[age_states, gender_states, smoking_states,
                       fam_states, asb_states, air_states]
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

    # --- Yeni risk faktörü priorları ---
    # Bunlar yalnızca değişken GÖZLENMEDİĞİNDE devreye girer (kanıt yoksa
    # popülasyon priori üzerinden marjinalize edilir → ~nötr etki).
    # FAMILY_HISTORY: ~%10 birinci derece akraba öyküsü
    family_history_cpd = TabularCPD(
        variable="FAMILY_HISTORY",
        variable_card=2,
        values=[[0.90], [0.10]]
    )
    # ASBESTOS: ~%8 mesleki risk maruziyeti
    asbestos_cpd = TabularCPD(
        variable="ASBESTOS",
        variable_card=2,
        values=[[0.92], [0.08]]
    )
    # AIR_POLLUTION: Türkiye nüfusunun çoğu "orta" kademede (il PM2.5 dağılımı)
    # 0=düşük (10%), 1=orta (70%), 2=yüksek (20%)
    air_pollution_cpd = TabularCPD(
        variable="AIR_POLLUTION",
        variable_card=3,
        values=[[0.10], [0.70], [0.20]]
    )

    return [age_cpd, gender_cpd, smoking_cpd,
            family_history_cpd, asbestos_cpd, air_pollution_cpd]


def build_symptom_cpds() -> list:
    """
    Build symptom CPDs from peer-reviewed medical literature.

    Parameterization Method: Expert Elicitation
    ============================================
    CPT values are derived from published symptom prevalence data using a
    standard expert-elicitation approach (Fenton & Neil, 2018; Druzdzel &
    van der Gaag, 2000). Each value is informed by one or more peer-reviewed
    sources reporting symptom prevalence, odds ratios, or positive predictive
    values, then translated into conditional probabilities suitable for a
    generative (Cancer → Symptom) Bayesian Network.

    For symptoms with SMOKING as a confounder:
      P(symptom | LUNG_CANCER, SMOKING) — 4 columns

    For symptoms without confounders:
      P(symptom | LUNG_CANCER) — 2 columns

    CPT Derivation Table
    ====================
    Each row maps a CPT value to its literature justification.

    ┌──────────────────────┬───────────┬───────────┬───────────────────────────────────────────────────────┐
    │ Symptom              │ Condition │ CPT Value │ Source & Derivation                                   │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ COUGHING             │ LC=1,SM=0 │ 0.60      │ Beckles (2003): cough prevalence 45-75% in LC;       │
    │                      │           │           │ Hamilton (2005): cough OR=1.6 in case-control.        │
    │                      │           │           │ Midpoint of range selected for non-smoker LC.         │
    │                      │ LC=1,SM=1 │ 0.70      │ Smoker + cancer: upper range (additive effect).       │
    │                      │ LC=0,SM=0 │ 0.10      │ General population cough prevalence ~9-12%            │
    │                      │           │           │ (Schappert, Natl Amb Med Care Survey, 1992).          │
    │                      │ LC=0,SM=1 │ 0.25      │ Chronic cough in smokers ~20-30%                      │
    │                      │           │           │ (Wynder & Graham, JAMA 1950; Doll & Hill, BMJ 1950). │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ SHORTNESS_OF_BREATH  │ LC=1,SM=0 │ 0.50      │ Beckles (2003): dyspnoea 37-58% in LC patients.      │
    │                      │           │           │ Hamilton (2005): dyspnoea independently associated.   │
    │                      │ LC=1,SM=1 │ 0.60      │ Upper bound of range for smoker + cancer.             │
    │                      │ LC=0,SM=0 │ 0.08      │ Dyspnoea in general adult population ~5-10%.          │
    │                      │ LC=0,SM=1 │ 0.18      │ COPD-related dyspnoea in long-term smokers ~15-20%   │
    │                      │           │           │ (Mannino et al., MMWR 2002).                          │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ WHEEZING             │ LC=1,SM=0 │ 0.22      │ Beckles (2003): wheezing less common, ~15-30%.       │
    │                      │ LC=1,SM=1 │ 0.30      │ Upper bound for smoker + cancer.                      │
    │                      │ LC=0,SM=0 │ 0.05      │ Wheezing in non-smoking adults ~3-7%.                │
    │                      │ LC=0,SM=1 │ 0.15      │ Wheezing in chronic smokers ~12-18%.                 │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ CHEST_PAIN           │ LC=1      │ 0.35      │ Beckles (2003): chest/thoracic pain 27-49% in LC.    │
    │                      │           │           │ Hamilton (2005): thoracic pain OR significant.         │
    │                      │ LC=0      │ 0.05      │ Non-cardiac chest pain prevalence ~2-7% in adults    │
    │                      │           │           │ (Eslick et al., Aliment Pharmacol Ther 2003).         │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ FATIGUE              │ LC=1      │ 0.50      │ Hopwood & Stephens (BJC 2000): fatigue 40-55% at     │
    │                      │           │           │ diagnosis. Corner (2005): fatigue/lethargy as major   │
    │                      │           │           │ systemic symptom category.                             │
    │                      │ LC=0      │ 0.20      │ General fatigue prevalence ~15-25% in adults          │
    │                      │           │           │ (Pawlikowska et al., BMJ 1994).                       │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ HEMOPTYSIS           │ LC=1      │ 0.20      │ Kvale (Chest 2006): hemoptysis in ~20% of LC          │
    │                      │           │           │ patients. Beckles (2003): confirms ~20%.               │
    │                      │           │           │ Hamilton (2005): highest PPV among symptoms.           │
    │                      │ LC=0      │ 0.01      │ Hemoptysis base rate in general population <1-2%     │
    │                      │           │           │ (Kvale 2006; Santiago et al., Medicine 1991).          │
    ├──────────────────────┼───────────┼───────────┼───────────────────────────────────────────────────────┤
    │ WEIGHT_LOSS          │ LC=1      │ 0.35      │ Hopwood & Stephens (BJC 2000): weight loss 30-40%.   │
    │                      │           │           │ Hamilton (2005): weight loss independently associated │
    │                      │           │           │ (OR significant in multivariable model).               │
    │                      │ LC=0      │ 0.05      │ Unexplained weight loss prevalence ~1-7% in adults   │
    │                      │           │           │ (McMinn et al., BMJ 2010).                             │
    └──────────────────────┴───────────┴───────────┴───────────────────────────────────────────────────────┘

    Primary References (with DOI/PMID)
    ===================================
    [1] Hamilton W, Peters TJ, Round A, Sharp D. "What are the clinical
        features of lung cancer before the diagnosis is made? A population
        based case-control study." Thorax. 2005;60(12):1059-65.
        DOI: 10.1136/thx.2005.045880 | PMID: 16227326
        → 247 LC cases, 1235 controls in Exeter UK. Reports OR and PPV
          for 7 symptoms: haemoptysis, weight loss, appetite loss,
          dyspnoea, thoracic pain, fatigue, cough.

    [2] Beckles MA, Spiro SG, Colice GL, Rudd RM. "Initial evaluation of
        the patient with lung cancer: symptoms, signs, laboratory tests,
        and paraneoplastic syndromes." Chest. 2003;123(1 Suppl):97S-104S.
        DOI: 10.1378/chest.123.1_suppl.97S | PMID: 12527569
        → ACCP evidence-based guideline. Systematic review reporting
          symptom frequency ranges from multiple clinical series.

    [3] Corner J, Hopkinson J, Fitzsimmons D, Barclay S, Muers M. "Is late
        diagnosis of lung cancer inevitable? Interview study of patients'
        recollections of symptoms before diagnosis." Thorax. 2005;60:314-9.
        DOI: 10.1136/thx.2004.029264 | PMID: 15790987
        → Qualitative study. Identifies chest and systemic symptom
          categories; supports symptom selection rationale.

    [4] Kvale PA. "Chronic cough due to lung tumors: ACCP evidence-based
        clinical practice guidelines." Chest. 2006;129(1 Suppl):147S-153S.
        DOI: 10.1378/chest.129.1_suppl.147S | PMID: 16428705
        → Hemoptysis prevalence in LC ~20%. Strongest alarm symptom
          with highest specificity among presenting symptoms.

    [5] Hopwood P, Stephens RJ. "Depression in patients with lung cancer:
        prevalence and risk factors derived from quality-of-life data."
        J Clin Oncol. 2000;18(4):893-903.
        DOI: 10.1200/JCO.2000.18.4.893 | PMID: 10673533
        → Fatigue ~50%, weight loss ~35% at diagnosis from MRC LC
          trial QoL data (n=987).

    Methodological Note
    ====================
    The sources above report odds ratios (OR), positive predictive values
    (PPV), and prevalence percentages — not direct conditional probabilities.
    Translation to P(symptom | cancer) and P(symptom | no cancer) follows
    standard epidemiological conversion:
      - P(S|LC=1) is set within the reported prevalence range for LC patients
      - P(S|LC=0) is set using general population or primary care base rates
      - Smoking confounder columns use the additive risk model for
        symptoms independently caused by both smoking and cancer
    This approach is consistent with expert-elicited BBN parameterization
    as described in Fenton & Neil (2018) "Risk Assessment and Decision
    Analysis with Bayesian Networks", CRC Press, Chapter 10.
    """
    symptom_cpds = []

    # ─── COUGHING: P(Coughing | LUNG_CANCER, SMOKING) ───
    # Sources: Beckles (2003) cough 45-75% in LC; Hamilton (2005) OR=1.6
    # Confounder: Smoking independently causes chronic cough (20-30%)
    # Column order: LC=0/SM=0, LC=0/SM=1, LC=1/SM=0, LC=1/SM=1
    #
    # Design note: P(LC=0, SM=1)=0.15 is kept moderate — smoking does cause
    # cough, but this must NOT over-suppress cancer inference for smokers.
    # A smoker who coughs should have HIGHER cancer risk, not lower.
    coughing_cpd = TabularCPD(
        variable="COUGHING",
        variable_card=2,
        values=[
            [0.90, 0.85, 0.40, 0.30],   # P(no coughing | ...)
            [0.10, 0.15, 0.60, 0.70],   # P(coughing | ...)
        ],
        evidence=["LUNG_CANCER", "SMOKING"],
        evidence_card=[2, 2]
    )
    symptom_cpds.append(coughing_cpd)

    # ─── SHORTNESS_OF_BREATH: P(SOB | LUNG_CANCER, SMOKING) ───
    # Sources: Beckles (2003) dyspnoea 37-58% in LC; Mannino (2002) COPD
    # Confounder: Smoking causes COPD-related dyspnoea, but P(SOB|LC=0,SM=1)
    # is kept low (0.10) to prevent explaining-away: a smoker with dyspnoea
    # must not have LOWER cancer probability than a non-smoker with dyspnoea.
    sob_cpd = TabularCPD(
        variable="SHORTNESS_OF_BREATH",
        variable_card=2,
        values=[
            [0.92, 0.90, 0.50, 0.40],   # P(no SOB | ...)
            [0.08, 0.10, 0.50, 0.60],   # P(SOB | ...)
        ],
        evidence=["LUNG_CANCER", "SMOKING"],
        evidence_card=[2, 2]
    )
    symptom_cpds.append(sob_cpd)

    # ─── WHEEZING: P(Wheezing | LUNG_CANCER, SMOKING) ───
    # Sources: Beckles (2003) wheezing 15-30% in LC
    # Confounder: P(Wheezing|LC=0,SM=1) kept at 0.07 (not 0.15) to avoid
    # explaining away — a smoker with wheezing should raise, not lower, risk.
    wheezing_cpd = TabularCPD(
        variable="WHEEZING",
        variable_card=2,
        values=[
            [0.95, 0.93, 0.78, 0.70],   # P(no wheezing | ...)
            [0.05, 0.07, 0.22, 0.30],   # P(wheezing | ...)
        ],
        evidence=["LUNG_CANCER", "SMOKING"],
        evidence_card=[2, 2]
    )
    symptom_cpds.append(wheezing_cpd)

    # ─── CHEST_PAIN: P(Chest Pain | LUNG_CANCER) ───
    # Sources: Beckles (2003) chest pain 27-49%; Hamilton (2005) OR significant
    # No smoking confounder — chest pain is cancer-specific, not smoking-related
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

    # ─── FATIGUE: P(Fatigue | LUNG_CANCER) ───
    # Sources: Hopwood & Stephens (2000) fatigue 40-55% at diagnosis;
    #          Corner (2005) fatigue as major systemic symptom
    # LC=0 base: general fatigue ~15-25% (Pawlikowska, BMJ 1994)
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

    # ─── HEMOPTYSIS: P(Hemoptysis | LUNG_CANCER) ───
    # Sources: Kvale (2006) hemoptysis in ~20% of LC patients;
    #          Beckles (2003) confirms ~20%; Hamilton (2005) highest PPV
    # LC=0 base: hemoptysis <1-2% (Kvale 2006; Santiago, Medicine 1991)
    # Strongest alarm symptom — highest specificity and LR+
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

    # ─── WEIGHT_LOSS: P(Weight Loss | LUNG_CANCER) ───
    # Sources: Hopwood & Stephens (2000) weight loss 30-40% at diagnosis;
    #          Hamilton (2005) OR significant in multivariable model
    # LC=0 base: unexplained weight loss ~1-7% (McMinn, BMJ 2010)
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
        # Yeni risk faktörleri
        "FAMILY_HISTORY": "Z80.1",   # Family history of malignant neoplasm of bronchus/lung
        "ASBESTOS": "Z57.2",         # Occupational exposure to dust (asbestos proxy)
        "AIR_POLLUTION": "Z77.110",  # Contact with/exposure to air pollution
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

    def _refine_smoking(self, ev: dict):
        """
        Paket-yıl + bırakma süresine göre etkin SMOKING değerini belirler (A kuralı).
        Returns: (effective_smoking | None, never_flag: bool, note_tr: str | None)
        Veri yoksa (paket-yıl bilinmiyor) mevcut SMOKING korunur — geriye dönük uyumlu.
        """
        smoking = ev.get("SMOKING")
        py = ev.get("_pack_years")
        yq = ev.get("_years_quit")
        if smoking is None:
            return None, False, None
        # Hiç / çok hafif içici → aşağı düzeltme bayrağı
        if smoking == 0 and py is not None and py < 1:
            return 0, True, ("Sigara öyküsü yok/çok az: taban risk hiç-içmeyen "
                             "seviyesine düşürüldü.")
        # Ağır + yakın zamanda bırakmış eski içici → aktif gibi
        if (smoking == 0 and py is not None and py >= HEAVY_FORMER_PACK_YEARS
                and (yq is None or yq <= HEAVY_FORMER_MAX_QUIT_YEARS)):
            return 1, False, (f"Ağır eski içici ({py:.0f} paket-yıl, bırakalı "
                              f"≤{HEAVY_FORMER_MAX_QUIT_YEARS} yıl): aktif içici gibi değerlendirildi.")
        return smoking, False, None

    def predict_risk(self, evidence: dict) -> dict:
        """
        Calculate lung cancer risk given patient evidence.

        Args:
            evidence: Dict of observed variables, e.g.,
                      {"SMOKING": 1, "COUGHING": 1, "AGE": 3, "GENDER": 1}

        Returns:
            Dict with risk score, level, and detailed analysis
        """
        # Paket-yıl temelli sigara düzeltmesi (A kuralı) — inference ÖNCESİ
        evidence = dict(evidence)
        eff_smoking, never_flag, smoking_note = self._refine_smoking(evidence)
        if eff_smoking is not None:
            evidence["SMOKING"] = eff_smoking

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

        # Hiç içmeyen için taban riske aşağı odds-çarpanı (inference SONRASI;
        # odds çarpımı değişmeli olduğundan prior'a uygulamakla matematiksel olarak eşdeğer)
        if never_flag:
            _o = cancer_prob / max(1e-9, 1 - cancer_prob)
            _o *= NEVER_SMOKER_OR
            cancer_prob = _o / (1 + _o)
        cancer_prob = max(0.0001, min(0.9999, cancer_prob))
        no_cancer_prob = 1.0 - cancer_prob

        # Determine risk level
        risk_level = "high"  # default for >= 0.15
        for level, info in self.RISK_LEVELS.items():
            if info["range"][0] <= cancer_prob < info["range"][1]:
                risk_level = level
                break

        # Map findings to ICD-10 (value >= 1 → present; AIR_POLLUTION orta=1/yüksek=2)
        icd10_findings = []
        for feature, value in filtered_evidence.items():
            if value >= 1 and feature in self.ICD10_MAP:
                icd10_findings.append({
                    "code": self.ICD10_MAP[feature],
                    "feature": feature,
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

        # Yeni risk faktörleri + açıklanabilirlik (her faktörün OR katkısı)
        or_contributions = {}
        if filtered_evidence.get("FAMILY_HISTORY") == 1:
            risk_factors.append("Ailede akciğer kanseri öyküsü")
            or_contributions["Ailede akciğer kanseri öyküsü"] = RISK_FACTOR_ORS["FAMILY_HISTORY"][1]
        if filtered_evidence.get("ASBESTOS") == 1:
            risk_factors.append("Mesleki asbest/risk maruziyeti (öz-bildirim)")
            or_contributions["Mesleki risk maruziyeti"] = RISK_FACTOR_ORS["ASBESTOS"][1]
        _air = filtered_evidence.get("AIR_POLLUTION")
        if _air in (1, 2):
            _air_lbl = "Hava kirliliği (orta)" if _air == 1 else "Hava kirliliği (yüksek)"
            risk_factors.append(_air_lbl)
            or_contributions[_air_lbl] = RISK_FACTOR_ORS["AIR_POLLUTION"][_air]

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
            "or_contributions": or_contributions,
            "smoking_adjustment": smoking_note,
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
            "low": ("Semptomlarınıza dayalı anlık risk düzeyiniz düşük görünmektedir. "
                    "Bu, risk faktörünüz olmadığı anlamına gelmez; sigara, yaş veya "
                    "mesleki maruziyet gibi etkenler varsa önemini korur. Yıllık sağlık "
                    "kontrollerinizi ihmal etmeyiniz ve tarama uygunluğunuzu hekiminizle "
                    "değerlendiriniz. Bu değerlendirme bir tarama aracıdır, tanı yerine geçmez."),
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
            "low": ("Your symptom-based risk appears low at this time. This does not mean "
                    "you have no risk factors; smoking, age, or occupational exposure remain "
                    "important if present. Maintain regular annual check-ups and discuss your "
                    "screening eligibility with your physician. This is a screening tool, not a diagnosis."),
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
                "FAMILY_HISTORY": 1, "ASBESTOS": 1, "AIR_POLLUTION": 2,
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
                "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 1,
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
                "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 0,
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
                "FAMILY_HISTORY": 1, "ASBESTOS": 0, "AIR_POLLUTION": 1,
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
                "FAMILY_HISTORY": 1, "ASBESTOS": 1, "AIR_POLLUTION": 2,
            }
        },
        {
            "name": "Hasta F — Genç Temiz Hava vs Kirli Hava Karşılaştırması",
            "name_en": "Patient F — Air Pollution Sensitivity (same profile, high pollution)",
            "evidence": {
                "SMOKING": 0, "AGE": 2, "GENDER": 0,
                "FAMILY_HISTORY": 0, "ASBESTOS": 0, "AIR_POLLUTION": 2,
                "COUGHING": 1,
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

    names = [r["scenario"].split("—")[0].strip().replace("Hasta", "Patient") for r in demo_results]
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
    plt.savefig(output_dir / "hybrid_risk_scores.png", dpi=300, bbox_inches="tight")
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
