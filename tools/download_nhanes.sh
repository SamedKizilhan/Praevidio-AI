#!/usr/bin/env bash
# NHANES 2007–2012 (RDQ solunum anketi + SMQ sigara + MCQ tıbbi durum + DEMO) indirir.
# Kullanım: bash tools/download_nhanes.sh      → data/raw/nhanes/*.xpt   (toplam ~15 MB)
# Not: bu makineden (Mac) çalıştırılmalı; sandbox ortamı cdc.gov'a erişemiyor.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/raw/nhanes"; mkdir -p "$OUT"
declare -A CYCLE=( [E]=2007 [F]=2009 [G]=2011 )
for L in E F G; do
  Y=${CYCLE[$L]}
  for F in RDQ SMQ MCQ DEMO; do
    N="${F}_${L}"
    if [ -s "$OUT/$N.xpt" ]; then echo "✓ $N.xpt var"; continue; fi
    URL1="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/$Y/DataFiles/$N.xpt"
    URL2="https://wwwn.cdc.gov/Nchs/Nhanes/$Y-$((Y+1))/$N.XPT"
    echo "↓ $N"
    curl -fsSL -o "$OUT/$N.xpt" "$URL1" || curl -fsSL -o "$OUT/$N.xpt" "$URL2"
  done
done
ls -la "$OUT"
echo "Tamam → python src/model/nhanes_symptom_baselines.py  (veya: make nhanes)"
