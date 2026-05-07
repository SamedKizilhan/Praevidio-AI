"""
Praevidio AI - NLST Data Preprocessing Pipeline
=================================================
Cleans and merges the real NLST (National Lung Screening Trial) clinical data
for use with the Hybrid BBN model.

Input:
  data/raw/nlst_780_prsn_idc_20210527.csv  (53,452 participants)
  data/raw/nlst_780_canc_idc_20210527.csv  (2,150 cancer records)

Output:
  data/processed/nlst_cleaned.csv
  data/processed/nlst_summary.json

Steps:
  1. Load prsn (participant) and canc (cancer) CSVs
  2. Filter canc to first primary lung cancers only
  3. Left-join on pid to preserve all participants
  4. Create binary target: has_cancer
  5. Normalize demographics (gender, age bins, race)
  6. Generate summary statistics
  7. Save cleaned dataset
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Paths ---
PRSN_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "nlst_780_prsn_idc_20210527.csv"
CANC_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "nlst_780_canc_idc_20210527.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "nlst_cleaned.csv"
OUTPUT_SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "nlst_summary.json"


def load_nlst_data():
    """Load the raw NLST CSV files."""
    print("📂 Loading NLST raw data...")

    prsn = pd.read_csv(PRSN_CSV_PATH)
    print(f"   ✅ prsn (participants): {len(prsn)} rows, {len(prsn.columns)} columns")

    canc = pd.read_csv(CANC_CSV_PATH)
    print(f"   ✅ canc (cancer cases):  {len(canc)} rows, {len(canc.columns)} columns")

    return prsn, canc


def merge_tables(prsn: pd.DataFrame, canc: pd.DataFrame) -> pd.DataFrame:
    """
    Merge participant and cancer tables on pid.
    Uses only the first primary lung cancer per participant.
    """
    print("\n🔗 Merging prsn + canc tables...")

    # Filter to first primary lung cancers only
    canc_first = canc[canc["first_lc"] == 1].copy()
    print(f"   First primary cancers: {len(canc_first)} records")
    print(f"   Unique patients with cancer: {canc_first['pid'].nunique()}")

    # Select useful columns from canc
    canc_cols = ["pid", "de_stag", "de_type", "lesionsize", "lc_topog",
                 "de_stag_7thed", "de_grade"]
    canc_selected = canc_first[canc_cols].copy()

    # Left join — keep all participants
    merged = prsn.merge(canc_selected, on="pid", how="left",
                        suffixes=("_prsn", "_canc"))

    print(f"   ✅ Merged dataset: {len(merged)} rows")

    # Verify: cancer count should match
    cancer_count = (merged["can_scr"] > 0).sum()
    print(f"   Cancer cases in merged: {cancer_count}")
    print(f"   Non-cancer cases: {len(merged) - cancer_count}")

    return merged


def create_target_variable(df: pd.DataFrame) -> pd.DataFrame:
    """Create binary cancer target variable from can_scr."""
    print("\n🎯 Creating target variable (has_cancer)...")

    # can_scr: 0 = No Cancer, 1-4 = Various cancer detection modes
    df["has_cancer"] = (df["can_scr"] > 0).astype(int)

    cancer_pos = df["has_cancer"].sum()
    cancer_neg = len(df) - cancer_pos
    prevalence = cancer_pos / len(df) * 100

    print(f"   Cancer positive: {cancer_pos} ({prevalence:.2f}%)")
    print(f"   Cancer negative: {cancer_neg} ({100 - prevalence:.2f}%)")
    print(f"   ✅ Real-world cancer prevalence: {prevalence:.2f}%")

    return df


def normalize_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize demographic variables for BBN compatibility."""
    print("\n🔧 Normalizing demographics...")

    # --- Gender: NLST (1=Male, 2=Female) → BBN (1=Male, 0=Female) ---
    df["gender_norm"] = df["gender"].map({1: 1, 2: 0})
    male_count = (df["gender_norm"] == 1).sum()
    female_count = (df["gender_norm"] == 0).sum()
    print(f"   Gender: Male={male_count}, Female={female_count}")

    # --- Age: Create bins for BBN ---
    # Bin edges chosen for clinical relevance in lung cancer screening
    df["age_group"] = pd.cut(
        df["age"],
        bins=[0, 54, 59, 64, 69, 100],
        labels=[0, 1, 2, 3, 4]
        # 0: <55 (low risk age)
        # 1: 55-59 (USPSTF screening starts)
        # 2: 60-64 (increasing risk)
        # 3: 65-69 (high risk)
        # 4: 70+   (highest risk)
    ).astype(int)

    print(f"   Age groups:")
    for group in sorted(df["age_group"].unique()):
        count = (df["age_group"] == group).sum()
        cancer_rate = df[df["age_group"] == group]["has_cancer"].mean() * 100
        labels = {0: "<55", 1: "55-59", 2: "60-64", 3: "65-69", 4: "70+"}
        print(f"     {labels[group]:>5s}: {count:>6d} patients, {cancer_rate:.2f}% cancer rate")

    # --- Race: Simplify to binary (for BBN simplicity) ---
    # 1=White → 0, All others → 1
    df["race_binary"] = (df["race"] != 1).astype(int)
    white = (df["race_binary"] == 0).sum()
    nonwhite = (df["race_binary"] == 1).sum()
    print(f"   Race: White={white}, Non-White={nonwhite}")

    # --- Smoking: NLST already uses 0=Former, 1=Current ---
    current = (df["cigsmok"] == 1).sum()
    former = (df["cigsmok"] == 0).sum()
    current_cancer = df[df["cigsmok"] == 1]["has_cancer"].mean() * 100
    former_cancer = df[df["cigsmok"] == 0]["has_cancer"].mean() * 100
    print(f"   Smoking: Current={current} ({current_cancer:.2f}% cancer), "
          f"Former={former} ({former_cancer:.2f}% cancer)")

    return df


def compute_conditional_probabilities(df: pd.DataFrame) -> dict:
    """
    Compute conditional probability tables from NLST data.
    These will be used by the Hybrid BBN model.
    """
    print("\n📊 Computing conditional probabilities from NLST data...")

    cpts = {}

    # --- P(CANCER | SMOKING) ---
    smoking_cpt = {}
    for smoking_val in [0, 1]:
        subset = df[df["cigsmok"] == smoking_val]
        p_cancer = subset["has_cancer"].mean()
        smoking_cpt[smoking_val] = round(p_cancer, 6)
    cpts["smoking"] = smoking_cpt
    print(f"   P(Cancer | Former smoker) = {smoking_cpt[0]:.4f}")
    print(f"   P(Cancer | Current smoker) = {smoking_cpt[1]:.4f}")

    # --- P(CANCER | AGE_GROUP) ---
    age_cpt = {}
    for age_val in sorted(df["age_group"].unique()):
        subset = df[df["age_group"] == age_val]
        p_cancer = subset["has_cancer"].mean()
        age_cpt[int(age_val)] = round(p_cancer, 6)
    cpts["age"] = age_cpt
    print(f"   P(Cancer | Age groups): {age_cpt}")

    # --- P(CANCER | GENDER) ---
    gender_cpt = {}
    for gender_val in [0, 1]:
        subset = df[df["gender_norm"] == gender_val]
        p_cancer = subset["has_cancer"].mean()
        gender_cpt[gender_val] = round(p_cancer, 6)
    cpts["gender"] = gender_cpt
    print(f"   P(Cancer | Female) = {gender_cpt[0]:.4f}")
    print(f"   P(Cancer | Male) = {gender_cpt[1]:.4f}")

    # --- P(CANCER | SMOKING, AGE_GROUP) joint ---
    joint_cpt = {}
    for smoking_val in [0, 1]:
        for age_val in sorted(df["age_group"].unique()):
            subset = df[(df["cigsmok"] == smoking_val) &
                        (df["age_group"] == age_val)]
            if len(subset) > 0:
                p_cancer = subset["has_cancer"].mean()
                joint_cpt[f"smoke{smoking_val}_age{int(age_val)}"] = round(p_cancer, 6)
    cpts["smoking_age_joint"] = joint_cpt
    print(f"   Joint P(Cancer | Smoking, Age): computed for {len(joint_cpt)} combinations")

    # --- Overall base rate ---
    base_rate = df["has_cancer"].mean()
    cpts["base_rate"] = round(base_rate, 6)
    print(f"   Base cancer rate: {base_rate:.4f} ({base_rate * 100:.2f}%)")

    return cpts


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select final columns for the cleaned dataset."""
    print("\n✂️ Selecting output columns...")

    output_cols = [
        "pid",
        "age", "age_group",
        "gender", "gender_norm",
        "race", "race_binary",
        "cigsmok",
        "has_cancer",
        "can_scr",
        "candx_days",
        "canc_free_days",
        # Cancer details (will be NaN for non-cancer cases)
        "de_stag_canc",      # from canc table (or de_stag if no suffix)
        "de_type_canc",
        "lesionsize",
    ]

    # Handle column naming from merge
    available_cols = []
    for col in output_cols:
        if col in df.columns:
            available_cols.append(col)
        elif col == "de_stag_canc" and "de_stag" in df.columns:
            # If no suffix collision, de_stag from canc is just de_stag
            pass  # Will handle below
        elif col == "de_type_canc" and "de_type" in df.columns:
            pass

    # Build clean output
    df_out = pd.DataFrame()
    df_out["pid"] = df["pid"]
    df_out["age"] = df["age"]
    df_out["age_group"] = df["age_group"]
    df_out["gender"] = df["gender"]
    df_out["gender_norm"] = df["gender_norm"]
    df_out["race"] = df["race"]
    df_out["race_binary"] = df["race_binary"]
    df_out["cigsmok"] = df["cigsmok"]
    df_out["has_cancer"] = df["has_cancer"]
    df_out["can_scr"] = df["can_scr"]
    df_out["candx_days"] = df["candx_days"]
    df_out["canc_free_days"] = df["canc_free_days"]

    # Cancer details — handle suffix or plain column names
    for canc_col, orig_options in [
        ("de_stag", ["de_stag_canc", "de_stag"]),
        ("de_type", ["de_type_canc", "de_type"]),
    ]:
        for opt in orig_options:
            if opt in df.columns:
                df_out[canc_col] = df[opt]
                break

    if "lesionsize" in df.columns:
        df_out["lesionsize"] = df["lesionsize"]

    print(f"   ✅ Output columns: {list(df_out.columns)}")
    print(f"   ✅ Shape: {df_out.shape}")

    return df_out


def save_outputs(df: pd.DataFrame, cpts: dict):
    """Save the cleaned dataset and summary statistics."""
    print("\n💾 Saving outputs...")

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save cleaned CSV
    df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"   ✅ Cleaned dataset: {OUTPUT_CSV_PATH}")

    # Build summary
    summary = {
        "source": "NLST (National Lung Screening Trial)",
        "dataset_description": "Real clinical trial data from 53,452 participants",
        "total_participants": len(df),
        "cancer_cases": int(df["has_cancer"].sum()),
        "cancer_prevalence_pct": round(df["has_cancer"].mean() * 100, 2),
        "age_range": {
            "min": int(df["age"].min()),
            "max": int(df["age"].max()),
            "mean": round(float(df["age"].mean()), 1)
        },
        "gender_distribution": {
            "male": int((df["gender_norm"] == 1).sum()),
            "female": int((df["gender_norm"] == 0).sum()),
            "male_cancer_rate_pct": round(
                df[df["gender_norm"] == 1]["has_cancer"].mean() * 100, 2),
            "female_cancer_rate_pct": round(
                df[df["gender_norm"] == 0]["has_cancer"].mean() * 100, 2)
        },
        "smoking_distribution": {
            "current": int((df["cigsmok"] == 1).sum()),
            "former": int((df["cigsmok"] == 0).sum()),
            "current_cancer_rate_pct": round(
                df[df["cigsmok"] == 1]["has_cancer"].mean() * 100, 2),
            "former_cancer_rate_pct": round(
                df[df["cigsmok"] == 0]["has_cancer"].mean() * 100, 2)
        },
        "conditional_probabilities": cpts,
        "columns": list(df.columns),
        "notes": [
            "has_cancer: binary target derived from can_scr > 0",
            "age_group: 0=<55, 1=55-59, 2=60-64, 3=65-69, 4=70+",
            "gender_norm: 0=Female, 1=Male",
            "race_binary: 0=White, 1=Non-White",
            "cigsmok: 0=Former smoker, 1=Current smoker",
            "All NLST participants were heavy smokers (current or former with ≥30 pack-years)"
        ]
    }

    with open(OUTPUT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Summary: {OUTPUT_SUMMARY_PATH}")


def print_final_report(df: pd.DataFrame, cpts: dict):
    """Print final preprocessing report."""
    print("\n" + "=" * 60)
    print("📋 NLST PREPROCESSING COMPLETE — FINAL REPORT")
    print("=" * 60)

    cancer_pos = df["has_cancer"].sum()
    cancer_neg = len(df) - cancer_pos

    print(f"""
    📊 Dataset Summary:
       Source:            NLST (National Lung Screening Trial)
       Total Participants: {len(df):,}
       Cancer Positive:   {cancer_pos:,} ({cancer_pos / len(df) * 100:.2f}%)
       Cancer Negative:   {cancer_neg:,} ({cancer_neg / len(df) * 100:.2f}%)

    🔬 Key Statistics from Real Clinical Data:
       P(Cancer | Current Smoker) = {cpts['smoking'][1]:.4f}
       P(Cancer | Former Smoker)  = {cpts['smoking'][0]:.4f}
       P(Cancer | Male)           = {cpts['gender'][1]:.4f}
       P(Cancer | Female)         = {cpts['gender'][0]:.4f}
       Base Cancer Rate           = {cpts['base_rate']:.4f}

    ⚠️  Important Note:
       All NLST participants were heavy smokers (current or former
       with ≥30 pack-years who quit within 15 years). This means
       the base rate of 3.85% is among high-risk individuals, not
       the general population.

    ✅ Data is ready for:
       • Hybrid BBN model training
       • Risk factor CPT computation
       • Integration with literature-based symptom CPTs
    """)


# ==============================================================
# MAIN EXECUTION
# ==============================================================
if __name__ == "__main__":
    print("🏥 PRAEVIDIO AI — NLST Data Preprocessing Pipeline")
    print("=" * 60)
    print(f"   Project Root: {PROJECT_ROOT}")
    print(f"   Input (prsn): {PRSN_CSV_PATH}")
    print(f"   Input (canc): {CANC_CSV_PATH}")
    print(f"   Output:       {OUTPUT_CSV_PATH}")
    print()

    # Step 1: Load raw data
    prsn, canc = load_nlst_data()

    # Step 2: Merge tables
    merged = merge_tables(prsn, canc)

    # Step 3: Create target variable
    merged = create_target_variable(merged)

    # Step 4: Normalize demographics
    merged = normalize_demographics(merged)

    # Step 5: Compute conditional probabilities
    cpts = compute_conditional_probabilities(merged)

    # Step 6: Select output columns
    df_clean = select_output_columns(merged)

    # Step 7: Save outputs
    save_outputs(df_clean, cpts)

    # Step 8: Final report
    print_final_report(df_clean, cpts)

    print("🎉 NLST Preprocessing Pipeline completed successfully!")
