#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
# NHANES 2007–2012 (RDQ solunum anketi + SMQ sigara + MCQ tıbbi durum + DEMO) indirir.
# Kullanım: bash tools/download_nhanes.sh      → data/raw/nhanes/*.xpt   (toplam ~15 MB)
# macOS'un bash 3.2'siyle uyumludur (ilişkisel dizi kullanılmaz).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/raw/nhanes"; mkdir -p "$OUT"
for PAIR in E:2007 F:2009 G:2011; do
  L="${PAIR%%:*}"; Y="${PAIR##*:}"
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
echo "Tamam → make nhanes"
