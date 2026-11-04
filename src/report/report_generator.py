"""
Praevidio AI - PDF Report Generator
=====================================
Generates bilingual (TR/EN) "Doctor-Ready" PDF reports from
HybridLungCancerEngine risk assessment results.

Pipeline: Risk Result dict → Jinja2 HTML → WeasyPrint PDF
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure Homebrew system libraries (Pango, GLib) are discoverable by WeasyPrint
# on macOS. Without this, cffi cannot dlopen libgobject / libpango from the venv.
_homebrew_lib = Path("/opt/homebrew/lib")
if _homebrew_lib.exists():
    _current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if str(_homebrew_lib) not in _current:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            f"{_homebrew_lib}:{_current}" if _current else str(_homebrew_lib)
        )

from jinja2 import Environment, FileSystemLoader

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    REPORT_TEMPLATE_DIR, REPORTS_OUTPUT_DIR
)


# ──────────────────────────────────────────────
# ICD-10 Code Mapping for Report
# ──────────────────────────────────────────────

SYMPTOM_ICD10 = {
    "COUGHING": {"code": "R05", "name_tr": "Öksürük", "name_en": "Cough"},
    "SHORTNESS_OF_BREATH": {"code": "R06.0", "name_tr": "Nefes Darlığı", "name_en": "Dyspnea"},
    "CHEST_PAIN": {"code": "R07.9", "name_tr": "Göğüs Ağrısı", "name_en": "Chest Pain"},
    "WHEEZING": {"code": "R06.2", "name_tr": "Hırıltılı Solunum", "name_en": "Wheezing"},
    "FATIGUE": {"code": "R53", "name_tr": "Yorgunluk / Halsizlik", "name_en": "Fatigue"},
    "HEMOPTYSIS": {"code": "R04.2", "name_tr": "Hemoptizi (Kan Tükürme)", "name_en": "Hemoptysis"},
    "WEIGHT_LOSS": {"code": "R63.4", "name_tr": "Kilo Kaybı", "name_en": "Weight Loss"},
}

AGE_GROUP_LABELS = {
    0: {"tr": "55 yaş altı", "en": "Under 55"},
    1: {"tr": "55-59 yaş", "en": "55-59 years"},
    2: {"tr": "60-64 yaş", "en": "60-64 years"},
    3: {"tr": "65-69 yaş", "en": "65-69 years"},
    4: {"tr": "70 yaş ve üzeri", "en": "70+ years"},
}

GENDER_LABELS = {
    0: {"tr": "Kadın", "en": "Female"},
    1: {"tr": "Erkek", "en": "Male"},
}

SMOKING_LABELS = {
    0: {"tr": "İçmiyor / Bırakmış", "en": "Non-smoker / Former"},
    1: {"tr": "Aktif Sigara Kullanıcısı", "en": "Current Smoker"},
}

# Yeni risk faktörü etiketleri (v2). Dil bilinçli olarak yumuşak tutulmuştur:
# "doğrulanmış asbest maruziyeti" değil "mesleki risk"; korkutmadan yönlendirme.
FAMILY_HISTORY_LABELS = {
    0: {"tr": "Yok / Bilinmiyor", "en": "None / Unknown"},
    1: {"tr": "Var (1. derece akraba)", "en": "Yes (first-degree relative)"},
}
ASBESTOS_LABELS = {
    0: {"tr": "Bildirilmedi", "en": "Not reported"},
    1: {"tr": "Mesleki risk (öz-bildirim)", "en": "Occupational risk (self-reported)"},
}
AIR_POLLUTION_LABELS = {
    0: {"tr": "Düşük (il PM2.5)", "en": "Low (provincial PM2.5)"},
    1: {"tr": "Orta (il PM2.5)", "en": "Moderate (provincial PM2.5)"},
    2: {"tr": "Yüksek (il PM2.5)", "en": "High (provincial PM2.5)"},
}

RISK_LEVEL_LABELS = {
    "low": {"tr": "DÜŞÜK RİSK", "en": "LOW RISK"},
    "moderate": {"tr": "ORTA RİSK", "en": "MODERATE RISK"},
    "high": {"tr": "YÜKSEK RİSK", "en": "HIGH RISK"},
}

RECOMMENDATIONS = {
    "low": {
        "tr": (
            "Semptomlarınıza dayalı anlık risk düzeyiniz düşüktür. Bu, risk faktörünüz "
            "olmadığı anlamına gelmez; sigara, yaş veya mesleki maruziyet gibi etkenler "
            "varsa önemini korur (aşağıdaki tarama değerlendirmesine bakınız). Sigara "
            "kullanıyorsanız bırakmanız ve yıllık kontrollerinizi düzenli yaptırmanız "
            "önerilir. Semptomlarınızda değişiklik olursa aile hekiminize başvurunuz."
        ),
        "en": (
            "Your symptom-based risk is low. This does not mean you have no risk factors; "
            "smoking, age, or occupational exposure remain important if present (see the "
            "screening assessment below). If you smoke, quitting is strongly recommended, "
            "and annual check-ups should be maintained. Consult your physician if symptoms change."
        ),
    },
    "moderate": {
        "tr": (
            "Risk skorunuz orta seviyededir. Bir göğüs hastalıkları uzmanına "
            "başvurmanız önerilir. Gerekli görüldüğü takdirde düşük doz bilgisayarlı "
            "tomografi (LDCT) taraması planlanabilir. Sigara kullanıyorsanız derhal "
            "bırakmanız kritik önem taşımaktadır. En yakın KETEM'e (Kanser Erken "
            "Teşhis ve Tarama Merkezi) başvurabilirsiniz."
        ),
        "en": (
            "Your risk score is at a moderate level. Consultation with a pulmonologist "
            "is recommended. A low-dose computed tomography (LDCT) screening may be "
            "planned if deemed necessary. If you smoke, immediate cessation is critically "
            "important. You may visit your nearest KETEM (Cancer Early Diagnosis Center)."
        ),
    },
    "high": {
        "tr": (
            "Risk skorunuz yüksek seviyededir. En kısa sürede bir göğüs hastalıkları "
            "veya onkoloji uzmanına başvurmanız şiddetle önerilir. Düşük doz bilgisayarlı "
            "tomografi (LDCT) ve gerekli ek tetkiklerin acil olarak yapılması gerekmektedir. "
            "Bu raporu doktorunuzla paylaşınız. En yakın KETEM'e derhal başvurunuz."
        ),
        "en": (
            "Your risk score is at a high level. Immediate consultation with a pulmonologist "
            "or oncologist is strongly recommended. Low-dose computed tomography (LDCT) and "
            "necessary additional tests should be performed urgently. Share this report with "
            "your physician. Visit your nearest KETEM immediately."
        ),
    },
}


def _determine_risk_level(score: float) -> str:
    """Determine risk level from score percentage."""
    if score < 5.0:
        return "low"
    elif score < 15.0:
        return "moderate"
    else:
        return "high"


def prepare_template_data(risk_result: dict, evidence: dict = None) -> dict:
    """
    Transform risk engine output into template-ready data.

    Args:
        risk_result: Output from HybridLungCancerEngine.predict_risk()
        evidence: Original evidence dict (optional, for extracting patient profile)

    Returns:
        dict ready for Jinja2 template rendering
    """
    score = risk_result.get("risk_score", 0)
    risk_level = risk_result.get("risk_level", _determine_risk_level(score)).lower()

    # Build risk factors list
    risk_factors = []
    if evidence:
        if "AGE" in evidence:
            age_labels = AGE_GROUP_LABELS.get(evidence["AGE"], {"tr": "Bilinmiyor", "en": "Unknown"})
            risk_factors.append({
                "name_tr": "Yaş Grubu", "name_en": "Age Group",
                "value_tr": age_labels["tr"], "value_en": age_labels["en"]
            })
        if "GENDER" in evidence:
            g_labels = GENDER_LABELS.get(evidence["GENDER"], {"tr": "Bilinmiyor", "en": "Unknown"})
            risk_factors.append({
                "name_tr": "Cinsiyet", "name_en": "Gender",
                "value_tr": g_labels["tr"], "value_en": g_labels["en"]
            })
        if "SMOKING" in evidence:
            s_labels = SMOKING_LABELS.get(evidence["SMOKING"], {"tr": "Bilinmiyor", "en": "Unknown"})
            risk_factors.append({
                "name_tr": "Sigara Durumu", "name_en": "Smoking Status",
                "value_tr": s_labels["tr"], "value_en": s_labels["en"]
            })
        # Yeni risk faktörleri
        if "FAMILY_HISTORY" in evidence:
            fh = FAMILY_HISTORY_LABELS.get(evidence["FAMILY_HISTORY"], {"tr": "Bilinmiyor", "en": "Unknown"})
            risk_factors.append({
                "name_tr": "Ailede Kanser Öyküsü", "name_en": "Family History",
                "value_tr": fh["tr"], "value_en": fh["en"]
            })
        if "ASBESTOS" in evidence:
            ab = ASBESTOS_LABELS.get(evidence["ASBESTOS"], {"tr": "Bilinmiyor", "en": "Unknown"})
            risk_factors.append({
                "name_tr": "Mesleki Maruziyet", "name_en": "Occupational Exposure",
                "value_tr": ab["tr"], "value_en": ab["en"]
            })
        if "AIR_POLLUTION" in evidence:
            ap = AIR_POLLUTION_LABELS.get(evidence["AIR_POLLUTION"], {"tr": "Bilinmiyor", "en": "Unknown"})
            prov = evidence.get("_province")
            val_tr = ap["tr"] + (f" — {prov}" if prov else "")
            risk_factors.append({
                "name_tr": "Hava Kirliliği", "name_en": "Air Pollution",
                "value_tr": val_tr, "value_en": ap["en"]
            })

    # Build ICD-10 findings (present symptoms only)
    icd10_findings = []
    for finding in risk_result.get("icd10_findings", []):
        icd10_findings.append({
            "code": finding.get("code", ""),
            "feature": finding.get("feature", ""),
        })

    # Build symptom summary
    symptom_summary = []
    symptom_evidence = evidence or {}
    for var, info in SYMPTOM_ICD10.items():
        symptom_summary.append({
            "name": f"{info['code']} — {info['name_tr']} / {info['name_en']}",
            "present": symptom_evidence.get(var, 0) == 1,
        })

    # Açıklanabilirlik: her risk faktörünün odds-ratio katkısı
    risk_drivers = [
        {"name": name, "multiplier": f"×{mult:.2f}"}
        for name, mult in risk_result.get("or_contributions", {}).items()
    ]

    # Tarama uygunluğu (semptom skorundan bağımsız)
    from model.screening import assess_screening_eligibility
    screening = risk_result.get("screening") or assess_screening_eligibility(evidence or {})

    # v3: iki katman — ana gösterge 6 yıllık TARAMA riski (risk etkenleri), belirtiler ayrı satır +
    # NICE alarmı; öneri metni motorun ürettiği (katman + alarm). v2 raporu eskisi gibi tek skor.
    def _fmt(x):
        return f"{x:.2f}" if x < 10 else f"{x:.1f}"
    is_v3 = risk_result.get("risk_6y_factors") is not None
    alarm = risk_result.get("alarm") or {}
    if is_v3:
        p6 = risk_result["risk_6y_factors"]
        lvl6 = risk_result.get("risk_level_factors") or _determine_risk_level(p6)
        banner = {"label": "6 Yıllık Tahmini Risk (risk etkenleri) / 6-Year Risk (risk factors)",
                  "value": _fmt(p6), "level": "below" if lvl6 == "low" else lvl6,
                  "level_tr": (risk_result.get("risk_level_factors_display_tr") or RISK_LEVEL_LABELS[lvl6]["tr"])
                  .replace("i", "İ").replace("ı", "I").upper(),                     # Türkçe büyük harf (EŞİĞİNİN)
                  "level_en": (risk_result.get("risk_level_factors_display_en") or RISK_LEVEL_LABELS[lvl6]["en"]).upper()}
        context_lines = [x for x in (
            (risk_result.get("relative_message_tr"), risk_result.get("relative_message_en")),
            ((risk_result.get("projection") or {}).get("message_tr"), (risk_result.get("projection") or {}).get("message_en")),
        ) if x[0]]
        full_line = None
        if risk_result.get("risk_level") != lvl6 or abs(score - p6) >= 0.5:
            full_line = (f"Belirtilerle birlikte değerlendirme / Including symptoms: %{_fmt(score)} "
                         f"({RISK_LEVEL_LABELS[risk_level]['tr']} / {RISK_LEVEL_LABELS[risk_level]['en']})")
        rec_level = "high" if alarm.get("level") == "urgent" else lvl6
        rec_tr, rec_en = risk_result.get("recommendation_tr"), risk_result.get("recommendation_en")
        src = risk_result.get("base_risk_source", "nlst")
        rf_source = {"plco": "PLCOm2012 (Tammemägi 2013, NEJM) + NLST (n=53,452) faktör çarpanları",
                     "wakelee2007": "Hiç içmemiş insidansı: Wakelee 2007 (J Clin Oncol) + literatür OR'leri",
                     }.get(src, "NLST Clinical Trial (n=53,452), NCI/NIH")
        sym_source = ("Hamilton (2005) ve diğer literatür; NHANES 2007–12 taban sıklıkları; "
                      "ortak nedenler: KOAH, başka bir hastalık")
    else:
        banner = {"label": "Risk Skoru / Risk Score", "value": f"{score:.1f}", "level": risk_level,
                  "level_tr": RISK_LEVEL_LABELS[risk_level]["tr"], "level_en": RISK_LEVEL_LABELS[risk_level]["en"]}
        full_line, rec_level, context_lines = None, risk_level, []
        rec_tr, rec_en = RECOMMENDATIONS[risk_level]["tr"], RECOMMENDATIONS[risk_level]["en"]
        rf_source = "NLST Clinical Trial (n=53,452), NCI/NIH"
        sym_source = "Hamilton (2005), Beckles (2003), Kvale (2006), Hopwood (2000)"

    return {
        "banner": banner,
        "full_line": full_line,
        "context_lines": context_lines,
        "alarm": alarm if alarm.get("level") == "urgent" else None,
        "screening": screening,
        "smoking_note": risk_result.get("smoking_adjustment"),
        "report_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "report_id": f"PRA-{uuid.uuid4().hex[:8].upper()}",
        "risk_score": f"{score:.1f}",
        "risk_level": risk_level,
        "risk_level_tr": RISK_LEVEL_LABELS[risk_level]["tr"],
        "risk_level_en": RISK_LEVEL_LABELS[risk_level]["en"],
        "risk_factors": risk_factors,
        "risk_drivers": risk_drivers,
        "icd10_findings": icd10_findings,
        "symptom_summary": symptom_summary,
        "recommendation_tr": rec_tr or RECOMMENDATIONS[risk_level]["tr"],
        "recommendation_en": rec_en or RECOMMENDATIONS[risk_level]["en"],
        "rec_level": rec_level,
        "data_sources": {"risk_factors": rf_source, "symptoms": sym_source},
    }


def render_html(template_data: dict) -> str:
    """Render Jinja2 HTML from template data."""
    env = Environment(
        loader=FileSystemLoader(str(REPORT_TEMPLATE_DIR)),
        autoescape=True
    )
    template = env.get_template("report_template.html")
    return template.render(**template_data)


def generate_report(
    risk_result: dict,
    evidence: dict = None,
    output_path: str = None,
    format: str = "pdf",
    engine=None
) -> str:
    """
    Generate a Doctor-Ready PDF report.

    Args:
        risk_result: Output from HybridLungCancerEngine.predict_risk()
        evidence: Original evidence dict for patient profile
        output_path: Custom output path (auto-generated if None)
        format: "pdf" or "html"

    Returns:
        Path to the generated report file
    """
    print("📄 Generating Doctor-Ready Report...")

    # Prepare data
    template_data = prepare_template_data(risk_result, evidence)

    # Render HTML
    html_content = render_html(template_data)

    # Determine output path
    REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]
        filename = f"praevidio_report_{timestamp}_{uid}"
        output_path = str(REPORTS_OUTPUT_DIR / f"{filename}.{format}")

    if format == "html":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"   ✅ HTML report saved: {output_path}")
    else:
        # PDF generation with WeasyPrint
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(output_path)
            print(f"   ✅ PDF report saved: {output_path}")
        except ImportError:
            # Fallback to HTML if WeasyPrint not installed
            html_path = output_path.replace(".pdf", ".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"   ⚠️  WeasyPrint not installed — saved as HTML: {html_path}")
            output_path = html_path
        except Exception as e:
            # WeasyPrint can have system dependency issues
            html_path = output_path.replace(".pdf", ".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"   ⚠️  PDF generation failed ({e}) — saved as HTML: {html_path}")
            output_path = html_path

    # Skor analizi (.md) — aynı dosya adıyla, skorun nasıl üretildiğini gösterir
    if engine is not None and evidence is not None:
        try:
            from model.explainability import score_analysis_markdown
            md = score_analysis_markdown(engine, evidence, risk_result)
            md_path = os.path.splitext(output_path)[0] + ".md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"   🧾 Score analysis saved: {md_path}")
        except Exception as e:
            print(f"   ⚠️  Score analysis not written: {e}")

    return output_path


# ==============================================================
# MAIN — Test with demo data
# ==============================================================

if __name__ == "__main__":
    print("📄 PRAEVIDIO AI — Report Generator Test")
    print("=" * 50)

    # Simulate risk engine output (Patient C — High Risk)
    demo_risk_result = {
        "cancer_probability": 0.247,
        "risk_level": "HIGH",
        "risk_score": 24.7,
        "icd10_findings": [
            {"code": "F17.21", "feature": "Nicotine dependence, cigarettes"},
            {"code": "R05", "feature": "Cough"},
            {"code": "R04.2", "feature": "Hemoptysis"},
            {"code": "R53", "feature": "Malaise and fatigue"},
            {"code": "R63.4", "feature": "Abnormal weight loss"},
        ],
        "recommendations": {
            "tr": "Yüksek risk — acil değerlendirme gerekli",
            "en": "High risk — urgent evaluation required",
        }
    }

    demo_evidence = {
        "AGE": 3,       # 65-69
        "GENDER": 1,    # Male
        "SMOKING": 1,   # Current smoker
        "COUGHING": 1,
        "HEMOPTYSIS": 1,
        "FATIGUE": 1,
        "WEIGHT_LOSS": 1,
        "SHORTNESS_OF_BREATH": 0,
        "CHEST_PAIN": 0,
        "WHEEZING": 0,
    }

    # Generate PDF report
    pdf_path = generate_report(
        demo_risk_result, demo_evidence, format="pdf"
    )
    print(f"\n   📂 Report: {pdf_path}")

    # Generate HTML report as well (fallback / debug)
    html_path = generate_report(
        demo_risk_result, demo_evidence, format="html"
    )
    print(f"   📂 Report: {html_path}")
