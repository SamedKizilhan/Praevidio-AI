"""
Praevidio AI - Data Preprocessing Pipeline
==========================================
Cleans and normalizes the raw Lung Cancer dataset for BBN training.

Input:  data/raw/lung_cancer_kaggle.csv
Output: data/processed/lung_cancer_cleaned.csv

Steps:
  1. Load and inspect raw data
  2. Handle missing values
  3. Normalize binary encodings (1/2 → 0/1)
  4. Encode categorical variables
  5. Create age bins
  6. Map features to ICD-10 codes
  7. Generate EDA statistics and visualizations
  8. Save cleaned dataset
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
import sys
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Paths ---
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "lung_cancer_kaggle.csv"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "lung_cancer_cleaned.csv"
KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "knowledge_base" / "symptom_risk_factors.json"
EDA_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "eda_plots"


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load the raw CSV dataset."""
    print(f"📂 Loading raw data from: {path}")
    df = pd.read_csv(path)
    print(f"   ✅ Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def inspect_data(df: pd.DataFrame) -> dict:
    """Perform initial data inspection and return summary stats."""
    print("\n🔍 DATA INSPECTION")
    print("=" * 60)

    stats = {}

    # Shape
    print(f"\n📊 Shape: {df.shape}")
    stats["shape"] = df.shape

    # Data types
    print(f"\n📋 Data Types:")
    for col, dtype in df.dtypes.items():
        print(f"   {col}: {dtype}")

    # Missing values
    missing = df.isnull().sum()
    print(f"\n❌ Missing Values:")
    if missing.sum() == 0:
        print("   ✅ No missing values found!")
    else:
        for col in missing[missing > 0].index:
            print(f"   {col}: {missing[col]} ({missing[col]/len(df)*100:.1f}%)")
    stats["missing_values"] = missing.to_dict()

    # Duplicates
    dupes = df.duplicated().sum()
    print(f"\n🔄 Duplicate Rows: {dupes} ({dupes/len(df)*100:.1f}%)")
    stats["duplicates"] = dupes

    # Target distribution
    print(f"\n🎯 Target Variable (LUNG_CANCER) Distribution:")
    target_dist = df["LUNG_CANCER"].value_counts()
    for val, count in target_dist.items():
        print(f"   {val}: {count} ({count/len(df)*100:.1f}%)")
    stats["target_distribution"] = target_dist.to_dict()

    # Basic statistics for numeric columns
    print(f"\n📈 AGE Statistics:")
    age_stats = df["AGE"].describe()
    for stat_name, val in age_stats.items():
        print(f"   {stat_name}: {val:.1f}")
    stats["age_stats"] = age_stats.to_dict()

    # Unique values per column
    print(f"\n🔢 Unique Values per Column:")
    for col in df.columns:
        unique_vals = sorted(df[col].unique())
        if len(unique_vals) <= 10:
            print(f"   {col}: {unique_vals}")
        else:
            print(f"   {col}: {len(unique_vals)} unique values (range: {min(unique_vals)}-{max(unique_vals)})")

    return stats


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize the dataset."""
    print("\n🧹 DATA CLEANING")
    print("=" * 60)

    df_clean = df.copy()

    # Step 1: Remove duplicates
    initial_count = len(df_clean)
    df_clean = df_clean.drop_duplicates()
    removed = initial_count - len(df_clean)
    print(f"\n1️⃣  Removed {removed} duplicate rows ({len(df_clean)} remaining)")

    # Step 2: Normalize binary columns (1/2 → 0/1)
    # In this dataset: 1 = No/Absent, 2 = Yes/Present
    binary_columns = [
        "SMOKING", "YELLOW_FINGERS", "ANXIETY", "PEER_PRESSURE",
        "CHRONIC_DISEASE", "FATIGUE", "ALLERGY", "WHEEZING",
        "ALCOHOL_CONSUMING", "COUGHING", "SHORTNESS_OF_BREATH",
        "SWALLOWING_DIFFICULTY", "CHEST_PAIN"
    ]

    print(f"\n2️⃣  Normalizing binary columns (1/2 → 0/1):")
    for col in binary_columns:
        if col in df_clean.columns:
            # Check if the column uses 1/2 encoding
            unique_vals = sorted(df_clean[col].unique())
            if set(unique_vals).issubset({1, 2}):
                df_clean[col] = df_clean[col].map({1: 0, 2: 1})
                print(f"   ✅ {col}: {unique_vals} → [0, 1]")
            else:
                print(f"   ⚠️  {col}: unexpected values {unique_vals}, skipping")

    # Step 3: Encode GENDER (M/F → 1/0)
    print(f"\n3️⃣  Encoding GENDER:")
    gender_map = {"M": 1, "F": 0}
    df_clean["GENDER"] = df_clean["GENDER"].map(gender_map)
    print(f"   ✅ M → 1, F → 0")

    # Step 4: Encode target variable (YES/NO → 1/0)
    print(f"\n4️⃣  Encoding LUNG_CANCER target:")
    target_map = {"YES": 1, "NO": 0}
    df_clean["LUNG_CANCER"] = df_clean["LUNG_CANCER"].map(target_map)
    print(f"   ✅ YES → 1, NO → 0")

    # Step 5: Create AGE_GROUP bins
    print(f"\n5️⃣  Creating AGE_GROUP bins:")
    bins = [0, 39, 49, 59, 69, 79, 100]
    labels = ["<40", "40-49", "50-59", "60-69", "70-79", "80+"]
    df_clean["AGE_GROUP"] = pd.cut(df_clean["AGE"], bins=bins, labels=labels)
    age_group_dist = df_clean["AGE_GROUP"].value_counts().sort_index()
    for group, count in age_group_dist.items():
        print(f"   {group}: {count} ({count/len(df_clean)*100:.1f}%)")

    # Step 6: Add ICD-10 code mapping column names
    print(f"\n6️⃣  Adding ICD-10 metadata:")
    icd10_mapping = {
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
    # Store mapping as metadata (not a column, but saved alongside)
    print(f"   ✅ Mapped {len(icd10_mapping)} features to ICD-10 codes")

    # Step 7: Final validation
    print(f"\n7️⃣  Final validation:")
    print(f"   Shape: {df_clean.shape}")
    print(f"   Null values: {df_clean.isnull().sum().sum()}")
    print(f"   All numeric: {df_clean.select_dtypes(include=[np.number]).shape[1]} / {len(df_clean.columns)} columns")

    return df_clean, icd10_mapping


def generate_eda_plots(df_raw: pd.DataFrame, df_clean: pd.DataFrame, output_dir: Path):
    """Generate EDA visualizations."""
    print("\n📊 GENERATING EDA VISUALIZATIONS")
    print("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Set style
    sns.set_theme(style="whitegrid", palette="husl")
    plt.rcParams["figure.figsize"] = (12, 8)
    plt.rcParams["font.size"] = 11

    # --- Plot 1: Target Distribution ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Raw distribution
    raw_target = df_raw["LUNG_CANCER"].value_counts()
    axes[0].pie(raw_target, labels=raw_target.index, autopct="%1.1f%%",
                colors=["#2ecc71", "#e74c3c"], startangle=90,
                textprops={"fontsize": 13})
    axes[0].set_title("Target Distribution (Raw)", fontsize=14, fontweight="bold")
    
    # Clean distribution
    clean_target = df_clean["LUNG_CANCER"].value_counts()
    labels_clean = ["Cancer (1)" if x == 1 else "No Cancer (0)" for x in clean_target.index]
    axes[1].pie(clean_target, labels=labels_clean, autopct="%1.1f%%",
                colors=["#e74c3c", "#2ecc71"], startangle=90,
                textprops={"fontsize": 13})
    axes[1].set_title("Target Distribution (Cleaned)", fontsize=14, fontweight="bold")
    
    plt.tight_layout()
    plt.savefig(output_dir / "01_target_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("   ✅ 01_target_distribution.png")

    # --- Plot 2: Age Distribution ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].hist(df_clean["AGE"], bins=30, color="#3498db", edgecolor="white", alpha=0.8)
    axes[0].set_xlabel("Age")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Age Distribution", fontsize=14, fontweight="bold")
    axes[0].axvline(df_clean["AGE"].mean(), color="#e74c3c", linestyle="--",
                    label=f"Mean: {df_clean['AGE'].mean():.1f}")
    axes[0].legend()

    age_group_counts = df_clean["AGE_GROUP"].value_counts().sort_index()
    axes[1].bar(range(len(age_group_counts)), age_group_counts.values,
                color=sns.color_palette("viridis", len(age_group_counts)))
    axes[1].set_xticks(range(len(age_group_counts)))
    axes[1].set_xticklabels(age_group_counts.index, rotation=0)
    axes[1].set_xlabel("Age Group")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Age Group Distribution", fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_dir / "02_age_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("   ✅ 02_age_distribution.png")

    # --- Plot 3: Feature Correlation Heatmap ---
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    corr_matrix = df_clean[numeric_cols].corr()

    fig, ax = plt.subplots(figsize=(14, 11))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, square=True, ax=ax,
                linewidths=0.5, annot_kws={"size": 9})
    ax.set_title("Feature Correlation Matrix", fontsize=16, fontweight="bold", pad=20)
    plt.tight_layout()
    plt.savefig(output_dir / "03_correlation_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("   ✅ 03_correlation_heatmap.png")

    # --- Plot 4: Feature vs Target (Cancer Rate per Feature) ---
    binary_features = [
        "SMOKING", "YELLOW_FINGERS", "ANXIETY", "PEER_PRESSURE",
        "CHRONIC_DISEASE", "FATIGUE", "ALLERGY", "WHEEZING",
        "ALCOHOL_CONSUMING", "COUGHING", "SHORTNESS_OF_BREATH",
        "SWALLOWING_DIFFICULTY", "CHEST_PAIN"
    ]

    cancer_rates = []
    for feat in binary_features:
        rate_present = df_clean[df_clean[feat] == 1]["LUNG_CANCER"].mean()
        rate_absent = df_clean[df_clean[feat] == 0]["LUNG_CANCER"].mean()
        cancer_rates.append({
            "feature": feat,
            "present": rate_present,
            "absent": rate_absent,
            "lift": rate_present - rate_absent
        })

    rates_df = pd.DataFrame(cancer_rates).sort_values("lift", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    y_pos = range(len(rates_df))
    bars = ax.barh(y_pos, rates_df["lift"], color=[
        "#e74c3c" if x > 0 else "#2ecc71" for x in rates_df["lift"]
    ], edgecolor="white", height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(rates_df["feature"], fontsize=11)
    ax.set_xlabel("Cancer Rate Lift (Present - Absent)", fontsize=12)
    ax.set_title("Impact of Each Feature on Cancer Risk",
                 fontsize=14, fontweight="bold")
    ax.axvline(0, color="black", linewidth=0.8)

    # Add value labels
    for i, (val, feat) in enumerate(zip(rates_df["lift"], rates_df["feature"])):
        ax.text(val + 0.005 if val >= 0 else val - 0.005, i,
                f"{val:+.3f}", va="center",
                ha="left" if val >= 0 else "right", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "04_feature_impact.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("   ✅ 04_feature_impact.png")

    # --- Plot 5: Smoking × Cancer Crosstab ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ct = pd.crosstab(df_clean["SMOKING"], df_clean["LUNG_CANCER"], normalize="index")
    ct.plot(kind="bar", ax=axes[0], color=["#2ecc71", "#e74c3c"], edgecolor="white")
    axes[0].set_xlabel("Smoking (0=No, 1=Yes)")
    axes[0].set_ylabel("Proportion")
    axes[0].set_title("Smoking vs Lung Cancer", fontsize=14, fontweight="bold")
    axes[0].legend(["No Cancer", "Cancer"])
    axes[0].set_xticklabels(["Non-Smoker", "Smoker"], rotation=0)

    # Gender distribution
    ct2 = pd.crosstab(df_clean["GENDER"], df_clean["LUNG_CANCER"], normalize="index")
    ct2.plot(kind="bar", ax=axes[1], color=["#2ecc71", "#e74c3c"], edgecolor="white")
    axes[1].set_xlabel("Gender (0=Female, 1=Male)")
    axes[1].set_ylabel("Proportion")
    axes[1].set_title("Gender vs Lung Cancer", fontsize=14, fontweight="bold")
    axes[1].legend(["No Cancer", "Cancer"])
    axes[1].set_xticklabels(["Female", "Male"], rotation=0)

    plt.tight_layout()
    plt.savefig(output_dir / "05_smoking_gender_cancer.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("   ✅ 05_smoking_gender_cancer.png")

    # --- Plot 6: Correlation with Target ---
    target_corr = corr_matrix["LUNG_CANCER"].drop("LUNG_CANCER").sort_values()

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ["#e74c3c" if x > 0 else "#3498db" for x in target_corr.values]
    ax.barh(range(len(target_corr)), target_corr.values, color=colors, 
            edgecolor="white", height=0.6)
    ax.set_yticks(range(len(target_corr)))
    ax.set_yticklabels(target_corr.index, fontsize=11)
    ax.set_xlabel("Pearson Correlation with LUNG_CANCER", fontsize=12)
    ax.set_title("Feature Correlations with Target Variable",
                 fontsize=14, fontweight="bold")
    ax.axvline(0, color="black", linewidth=0.8)

    for i, val in enumerate(target_corr.values):
        ax.text(val + 0.005 if val >= 0 else val - 0.005, i,
                f"{val:.3f}", va="center",
                ha="left" if val >= 0 else "right", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "06_target_correlations.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("   ✅ 06_target_correlations.png")

    print(f"\n   📁 All plots saved to: {output_dir}")


def save_cleaned_data(df: pd.DataFrame, icd10_mapping: dict, output_path: Path):
    """Save the cleaned dataset and metadata."""
    print(f"\n💾 SAVING CLEANED DATA")
    print("=" * 60)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"   ✅ Saved cleaned dataset to: {output_path}")
    print(f"   📊 Shape: {df.shape}")

    # Save ICD-10 mapping metadata
    mapping_path = output_path.parent / "icd10_column_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(icd10_mapping, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved ICD-10 column mapping to: {mapping_path}")

    # Save summary statistics
    summary_path = output_path.parent / "dataset_summary.json"
    summary = {
        "total_samples": len(df),
        "features": len(df.columns),
        "target_distribution": df["LUNG_CANCER"].value_counts().to_dict(),
        "cancer_rate": float(df["LUNG_CANCER"].mean()),
        "age_range": {"min": int(df["AGE"].min()), "max": int(df["AGE"].max()), "mean": float(df["AGE"].mean())},
        "gender_distribution": df["GENDER"].value_counts().to_dict(),
        "smoking_rate": float(df["SMOKING"].mean()),
        "columns": list(df.columns),
        "icd10_mapping": icd10_mapping
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved dataset summary to: {summary_path}")


def print_final_report(df: pd.DataFrame, icd10_mapping: dict):
    """Print a final summary of the preprocessing."""
    print("\n" + "=" * 60)
    print("📋 PREPROCESSING COMPLETE — FINAL REPORT")
    print("=" * 60)

    cancer_positive = df["LUNG_CANCER"].sum()
    cancer_negative = len(df) - cancer_positive

    print(f"""
    📊 Dataset Summary:
       Total Samples:    {len(df)}
       Features:         {len(df.columns) - 1} (+ 1 target)
       Cancer Positive:  {cancer_positive} ({cancer_positive/len(df)*100:.1f}%)
       Cancer Negative:  {cancer_negative} ({cancer_negative/len(df)*100:.1f}%)

    🎯 Key Risk Factors (Cancer Rate):
       Smokers:          {df[df['SMOKING']==1]['LUNG_CANCER'].mean()*100:.1f}% cancer rate
       Non-Smokers:      {df[df['SMOKING']==0]['LUNG_CANCER'].mean()*100:.1f}% cancer rate
       Males:            {df[df['GENDER']==1]['LUNG_CANCER'].mean()*100:.1f}% cancer rate
       Females:          {df[df['GENDER']==0]['LUNG_CANCER'].mean()*100:.1f}% cancer rate

    🏥 ICD-10 Mapped Features:
""")
    for feature, code in icd10_mapping.items():
        present_rate = df[feature].mean() * 100 if feature in df.columns else 0
        print(f"       {code:8s} → {feature:25s} ({present_rate:.1f}% present)")

    print(f"""
    ✅ Data is ready for:
       • Bayesian Belief Network training (pgmpy)
       • RAG knowledge base enrichment
       • Risk scoring engine development
    """)


# ==============================================================
# MAIN EXECUTION
# ==============================================================
if __name__ == "__main__":
    print("🏥 PRAEVIDIO AI — Data Preprocessing Pipeline")
    print("=" * 60)
    print(f"   Project Root: {PROJECT_ROOT}")
    print(f"   Input:  {RAW_DATA_PATH}")
    print(f"   Output: {PROCESSED_DATA_PATH}")
    print()

    # Step 1: Load raw data
    df_raw = load_raw_data(RAW_DATA_PATH)

    # Step 2: Inspect
    stats = inspect_data(df_raw)

    # Step 3: Clean
    df_clean, icd10_map = clean_data(df_raw)

    # Step 4: Generate EDA plots
    generate_eda_plots(df_raw, df_clean, EDA_OUTPUT_DIR)

    # Step 5: Save
    save_cleaned_data(df_clean, icd10_map, PROCESSED_DATA_PATH)

    # Step 6: Final report
    print_final_report(df_clean, icd10_map)

    print("\n🎉 Pipeline completed successfully!")
