"""
Praevidio AI — NHANES ile kansersiz semptom tabanları
=======================================================
Semptom CPT'lerinin "kanser YOK" sütunları (leak / sigara / KOAH katkıları) literatürden
gelir ve hiçbir kohortta doğrulanmamıştır. NHANES 2007–2012 (ABD genel nüfus anketi,
RDQ solunum modülü) ile kansersiz kişilerde:
    P(kronik öksürük | sigara durumu, yaş grubu),  P(hırıltı | ...),  P(balgam | ...)
hesaplanır ve v3 noisy-OR parametrelerinin ima ettiği değerlerle yan yana konur.

Girdi:  data/raw/nhanes/{RDQ,SMQ,MCQ,DEMO}_{E,F,G}.xpt   (bash tools/download_nhanes.sh)
Çıktı:  data/processed/nhanes_symptom_baselines.json + docs/nhanes_semptom_tabanlari.md

Değişkenler (NHANES kod kitapları):
  RDQ031  Coughing most days ≥3 months (kronik öksürük)         1=Evet 2=Hayır
  RDQ050  Bring up phlegm most days ≥3 months (balgam)           1/2
  RDQ070  Wheezing or whistling in chest, past 12 months          1/2
  SMQ020  Smoked ≥100 cigarettes in life                           1/2
  SMQ040  Do you now smoke: 1 every day, 2 some days, 3 not at all
  MCQ220  Ever told you had cancer                                  1/2
  MCQ230A-D  Cancer type codes (23 = lung)
  RIDAGEYR yaş, RIAGENDR cinsiyet (1 E, 2 K), WTINT2YR görüşme ağırlığı
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "nhanes"
OUT_JSON = ROOT / "data" / "processed" / "nhanes_symptom_baselines.json"
OUT_MD = ROOT / "docs" / "nhanes_semptom_tabanlari.md"
CYCLES = ["E", "F", "G"]

sys.path.insert(0, str(ROOT / "src"))


def load_cycle(letter: str) -> pd.DataFrame:
    frames = []
    for f in ("DEMO", "SMQ", "RDQ", "MCQ"):
        p = RAW / f"{f}_{letter}.xpt"
        if not p.exists():
            raise FileNotFoundError(f"{p} yok — önce: bash tools/download_nhanes.sh")
        frames.append(pd.read_sas(p, format="xport"))
    df = frames[0]
    for fr in frames[1:]:
        df = df.merge(fr, on="SEQN", how="left")
    df["cycle"] = letter
    return df


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Sigara durumu, yaş grubu, kanser bayrağı ve semptomları türetir (anketi yanıtlayanlar)."""
    d = df.copy()
    d = d[d["RIDAGEYR"] >= 40]                                   # RDQ kronik öksürük 40+ sorulur
    ever = d["SMQ020"] == 1
    now = d["SMQ040"].isin([1, 2])
    d["smoking"] = "never"
    d.loc[ever & ~now, "smoking"] = "former"
    d.loc[ever & now, "smoking"] = "current"
    d.loc[d["SMQ020"].isna() | ((d["SMQ020"] == 1) & d["SMQ040"].isna()), "smoking"] = None
    d["age_group"] = pd.cut(d["RIDAGEYR"], bins=[39, 54, 64, 120], labels=["40-54", "55-64", "65+"])
    cancer_cols = [c for c in ("MCQ230A", "MCQ230B", "MCQ230C", "MCQ230D") if c in d.columns]
    d["any_cancer"] = d["MCQ220"] == 1
    d["lung_cancer"] = False
    for c in cancer_cols:
        d["lung_cancer"] |= d[c] == 23
    for var, col in (("chronic_cough", "RDQ031"), ("phlegm", "RDQ050"), ("wheeze", "RDQ070")):
        d[var] = d[col].map({1: 1.0, 2: 0.0})                   # 7/9 (bilmiyor/ret) → NaN
    d["w"] = d["WTINT2YR"] / len(CYCLES)                         # 3 döngü birleşik ağırlık
    return d


def weighted_rate(sub: pd.DataFrame, var: str):
    s = sub.dropna(subset=[var, "w"])
    if len(s) < 30:
        return None, int(len(s))
    return float((s[var] * s["w"]).sum() / s["w"].sum()), int(len(s))


def implied_v3() -> dict:
    """v3 noisy-OR parametrelerinin kansersiz kişide ima ettiği P(semptom | sigara)."""
    from model.hybrid_bayesian_network_v3 import NOISY_OR, COPD_GIVEN_SMOKING
    out = {}
    for sym, p in NOISY_OR.items():
        row = {}
        for status, sm, pc in (("never", 0, 0.0), ("former", 0, COPD_GIVEN_SMOKING[0]),
                               ("current", 1, COPD_GIVEN_SMOKING[1])):
            no_copd = 1 - (1 - p["leak"]) * (1 - p["smoke"]) ** sm
            with_copd = 1 - (1 - p["leak"]) * (1 - p["smoke"]) ** sm * (1 - p["copd"])
            row[status] = round((1 - pc) * no_copd + pc * with_copd, 3)
        out[sym] = row
    return out


def main():
    df = pd.concat([load_cycle(c) for c in CYCLES], ignore_index=True)
    d = derive(df)
    base = d[~d["any_cancer"] & d["smoking"].notna()]          # kansersiz (her türlü) + sigara bilinen
    res = {"source": "NHANES 2007-2012 (E,F,G), age ≥40, no self-reported cancer, WTINT2YR/3 weighted",
           "n_total_40plus": int(len(d)), "n_no_cancer": int(len(base)),
           "n_self_reported_lung_cancer_40plus": int(d["lung_cancer"].sum()),
           "rates": {}, "implied_v3_no_cancer": implied_v3()}
    for var in ("chronic_cough", "phlegm", "wheeze"):
        res["rates"][var] = {}
        for status in ("never", "former", "current"):
            sub = base[base["smoking"] == status]
            rate, n = weighted_rate(sub, var)
            res["rates"][var][status] = {"all_40plus": rate, "n": n}
            for ag in ("40-54", "55-64", "65+"):
                r2, n2 = weighted_rate(sub[sub["age_group"] == ag], var)
                res["rates"][var][status][ag] = {"rate": r2, "n": n2}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    imp = res["implied_v3_no_cancer"]
    L = ["# NHANES ile kansersiz semptom tabanları (v3 doğrulaması)", "",
         f"*{res['source']}. n(40+)={res['n_total_40plus']}, kansersiz n={res['n_no_cancer']}, "
         f"öz-bildirim akciğer kanseri (40+) n={res['n_self_reported_lung_cancer_40plus']} — kanser sütunu için yetersiz; "
         "yalnız KANSERSİZ tabanlar kullanılır.*", "",
         "| Semptom (NHANES tanımı) | Sigara | NHANES % (n) | 40-54 | 55-64 | 65+ | v3'ün ima ettiği % (kanser yok) |",
         "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    label = {"chronic_cough": ("Kronik öksürük (çoğu gün ≥3 ay)", "COUGHING"),
             "phlegm": ("Balgam (çoğu gün ≥3 ay)", None),
             "wheeze": ("Hırıltı/ıslık (son 12 ay)", "WHEEZING")}
    def pct(x): return "—" if x is None else f"{x*100:.1f}"
    for var, (lbl, v3key) in label.items():
        for status in ("never", "former", "current"):
            r = res["rates"][var][status]
            v3v = pct(imp[v3key][status]) if v3key else "—"
            L.append(f"| {lbl} | {status} | {pct(r['all_40plus'])} ({r['n']}) | {pct(r['40-54']['rate'])} | "
                     f"{pct(r['55-64']['rate'])} | {pct(r['65+']['rate'])} | {v3v} |")
    L += ["", "## Yorum", "",
          "- NHANES 'kronik öksürük' (çoğu gün, ≥3 ay) tanımı ajanın 'geçmeyen öksürük' sorusundan daha dardır; "
          "bu yüzden NHANES oranlarının v3 değerlerinin biraz altında kalması beklenir. Belirgin sapma (>2×) "
          "varsa `NOISY_OR[...]['leak'|'smoke']` güncellenmelidir.",
          "- Hırıltı için NHANES 12 aylık pencere kullanır; v3 'solunumda hırıltı oluyor mu' sorusuyla yakın.",
          "- Nefes darlığı NHANES RDQ'da bu döngülerde yoktur; literatür değeri korunur.",
          "- Sigara etkisi (current/never oranı) v3'teki KOAH-aracılı mekanizmanın büyüklüğünü sınar: NHANES'te "
          "current/never oranı v3'ünkinden büyükse `smoke` ya da `copd` katkısı artırılmalıdır."]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps(res["rates"], indent=1)[:1500])
    print(f"\n📄 {OUT_MD}\n📄 {OUT_JSON}")


if __name__ == "__main__":
    main()
