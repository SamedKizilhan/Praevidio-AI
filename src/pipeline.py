"""
Praevidio AI - End-to-End Pipeline
====================================
Chains all components into a unified workflow:

  Audio/Text → STT → NLP Extraction → RAG ICD-10 → BBN Inference → PDF Report

Usage:
  # Interactive text mode (demo, no audio needed)
  python src/pipeline.py --interactive

  # Audio mode (requires audio file + API key)
  python src/pipeline.py --audio patient_recording.m4a

  # Interactive mode with LLM extraction
  python src/pipeline.py --interactive --nlp-mode llm

  # Quick test with a predefined scenario
  python src/pipeline.py --demo
"""

import argparse
import json
import sys
import pickle
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    HYBRID_MODEL_PATH, OPENAI_API_KEY, NLP_MODE,
    REPORTS_OUTPUT_DIR
)


def load_hybrid_engine():
    """Load the trained hybrid BBN model and create inference engine."""
    from model.hybrid_bayesian_network import (
        build_hybrid_model, HybridLungCancerEngine
    )

    print(f"   🧠 Building Hybrid BBN from NLST data...")
    model = build_hybrid_model()
    engine = HybridLungCancerEngine(model)
    return engine


def run_interactive_pipeline(nlp_mode: str = "keyword"):
    """
    Run the full pipeline in interactive text mode.
    User types symptom descriptions, system returns risk assessment + PDF.
    """
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         🩺 PRAEVIDIO AI — Risk Assessment           ║")
    print("║         Akciğer Kanseri Risk Değerlendirme           ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Load components
    print("📦 Loading components...")
    engine = load_hybrid_engine()

    from stt.whisper_stt import post_process_medical_terms
    from nlp.symptom_extractor import extract_symptoms
    from rag.rag_pipeline import keyword_search
    from report.report_generator import generate_report

    print("   ✅ All components loaded\n")

    while True:
        print("─" * 55)
        print("📝 Semptomlarınızı Türkçe olarak yazınız:")
        print("   (veya 'çıkış' / 'quit' yazarak çıkın)")
        print("─" * 55)
        user_input = input("\n   🎤 > ").strip()

        if user_input.lower() in ("quit", "exit", "q", "çıkış", "çık"):
            print("\n   👋 Praevidio AI'dan çıkılıyor. Sağlıcakla kalın!")
            break

        if not user_input:
            print("   ⚠️  Boş giriş — lütfen semptomlarınızı yazın.")
            continue

        # Step 1: Post-process medical terms
        print(f"\n   ────── Adım 1: Metin İşleme ──────")
        processed_text = post_process_medical_terms(user_input)
        if processed_text != user_input:
            print(f"   🔧 Tıbbi terim düzeltmeleri: \"{processed_text}\"")
        else:
            print(f"   📝 Metin: \"{processed_text}\"")

        # Step 2: NLP Symptom Extraction
        print(f"\n   ────── Adım 2: Semptom Çıkarma ({nlp_mode}) ──────")
        evidence = extract_symptoms(processed_text, mode=nlp_mode)
        print(f"   📋 Tespit edilen kanıtlar:")
        for key, val in evidence.items():
            print(f"      • {key}: {val}")

        if not evidence:
            print("   ⚠️  Hiçbir semptom veya risk faktörü tespit edilemedi.")
            print("   💡 Daha fazla detay veriniz (örn: yaş, sigara, semptomlar)")
            continue

        # Step 3: RAG ICD-10 Matching
        print(f"\n   ────── Adım 3: ICD-10 Eşleştirme ──────")
        rag_results = keyword_search(processed_text)
        if rag_results:
            for r in rag_results[:5]:
                print(f"      • {r['code']}: {r['description_tr']} "
                      f"(matched: {r.get('matched_terms', [])})")
        else:
            print("      • Eşleşen ICD-10 kodu bulunamadı")

        # Step 4: BBN Inference
        print(f"\n   ────── Adım 4: Bayesian Risk Analizi ──────")
        try:
            risk_result = engine.predict_risk(evidence)
        except Exception as e:
            print(f"   ❌ Inference error: {e}")
            print("   ⚠️  Devam ediliyor...")
            continue

        prob = risk_result.get("risk_score", 0)
        level = risk_result.get("risk_level", "UNKNOWN")
        print(f"   🎯 Risk Skoru: %{prob:.1f}")
        print(f"   📊 Risk Seviyesi: {level}")

        # Display ICD-10 findings
        findings = risk_result.get("icd10_findings", [])
        if findings:
            print(f"   🔬 ICD-10 Bulgular:")
            for f in findings:
                print(f"      • {f['code']}: {f['feature']}")

        # Display recommendations
        recs = risk_result.get("recommendations", {})
        if recs:
            print(f"\n   💡 Öneri (TR): {recs.get('tr', 'N/A')}")
            print(f"   💡 Öneri (EN): {recs.get('en', 'N/A')}")

        # Step 5: Generate Report
        print(f"\n   ────── Adım 5: Rapor Oluşturma ──────")
        try:
            report_path = generate_report(
                risk_result, evidence, format="pdf", engine=engine
            )
            print(f"   📄 Rapor oluşturuldu: {report_path}")
        except Exception as e:
            print(f"   ⚠️  Rapor oluşturulamadı: {e}")

        print()


def run_audio_pipeline(audio_path: str, nlp_mode: str = "keyword"):
    """
    Run the full pipeline from an audio file.
    """
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         🩺 PRAEVIDIO AI — Audio Pipeline             ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Load components
    print("📦 Loading components...")
    engine = load_hybrid_engine()

    from stt.whisper_stt import transcribe_audio
    from nlp.symptom_extractor import extract_symptoms
    from rag.rag_pipeline import keyword_search
    from report.report_generator import generate_report

    print("   ✅ All components loaded\n")

    # Step 1: Transcribe audio
    print("────── Adım 1: Ses → Metin (Whisper) ──────")
    try:
        stt_result = transcribe_audio(audio_path)
        text = stt_result["text"]
        print(f"   📝 Transkripsiyon: \"{text}\"")
    except Exception as e:
        print(f"   ❌ Transcription failed: {e}")
        return

    # Step 2: NLP extraction
    print(f"\n────── Adım 2: Semptom Çıkarma ({nlp_mode}) ──────")
    evidence = extract_symptoms(text, mode=nlp_mode)
    print(f"   📋 Evidence: {evidence}")

    # Step 3: RAG
    print(f"\n────── Adım 3: ICD-10 Eşleştirme ──────")
    rag_results = keyword_search(text)
    for r in rag_results[:5]:
        print(f"   • {r['code']}: {r['description_tr']}")

    # Step 4: BBN Inference
    print(f"\n────── Adım 4: Bayesian Risk Analizi ──────")
    risk_result = engine.predict_risk(evidence)
    prob = risk_result.get("risk_score", 0)
    print(f"   🎯 Risk: %{prob:.1f} — {risk_result.get('risk_level', 'N/A')}")

    # Step 5: Generate Report
    print(f"\n────── Adım 5: Rapor Oluşturma ──────")
    report_path = generate_report(risk_result, evidence, format="pdf", engine=engine)
    print(f"   📄 {report_path}")


def run_demo():
    """Run a quick demo with predefined scenarios."""
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         🩺 PRAEVIDIO AI — Demo Senaryolar            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Load components
    print("📦 Loading components...")
    engine = load_hybrid_engine()

    from stt.whisper_stt import post_process_medical_terms
    from nlp.symptom_extractor import extract_symptoms
    from report.report_generator import generate_report

    print("   ✅ Ready\n")

    scenarios = [
        {
            "name": "Hasta A — Düşük Risk",
            "text": "38 yaşında kadınım, sigara içmiyorum. Bazen hafif öksürüğüm oluyor."
        },
        {
            "name": "Hasta B — Orta Risk",
            "text": "58 yaşındayım, erkeyim, sigarayı bıraktım. Nefes darlığı ve göğüs ağrısı var."
        },
        {
            "name": "Hasta C — Yüksek Risk",
            "text": "67 yaşında erkeyim, günde bir paket sigara içiyorum. Sürekli öksürüyorum, kan tükürdüm, kilo verdim ve çok yorgunum."
        },
    ]

    for scenario in scenarios:
        print(f"\n{'═'*55}")
        print(f"  🏥 {scenario['name']}")
        print(f"  📝 \"{scenario['text']}\"")
        print(f"{'═'*55}")

        # Process
        processed = post_process_medical_terms(scenario["text"])
        evidence = extract_symptoms(processed, mode="keyword")
        print(f"\n  📋 Evidence: {json.dumps(evidence, indent=2)}")

        # Inference
        try:
            risk_result = engine.predict_risk(evidence)
            prob = risk_result.get("risk_score", 0)
            level = risk_result.get("risk_level", "N/A")
            print(f"\n  🎯 Risk: %{prob:.1f} — {level}")

            # Generate report
            report_path = generate_report(
                risk_result, evidence, format="pdf", engine=engine
            )
            print(f"  📄 Report: {report_path}")
        except Exception as e:
            print(f"  ❌ Error: {e}")


# ==============================================================
# CLI Entry Point
# ==============================================================

def record_audio(output_path: str = None, max_seconds: int = 30) -> str:
    """
    Record audio from the Mac microphone.

    Uses macOS built-in `say` for prompting and `sox` (rec) for recording.
    Falls back to Python `sounddevice` if sox is not available.

    Args:
        output_path: Where to save the recording
        max_seconds: Maximum recording duration

    Returns:
        Path to the saved audio file
    """
    import subprocess
    import os
    from config import PROCESSED_DATA_DIR

    recordings_dir = PROCESSED_DATA_DIR / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(recordings_dir / f"recording_{timestamp}.wav")

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         🎤 PRAEVIDIO AI — Ses Kaydı                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    print(f"   📍 Kayıt dosyası: {output_path}")
    print(f"   ⏱️  Maksimum süre: {max_seconds} saniye")
    print()

    # Check if sox/rec is available
    sox_available = subprocess.run(
        ["which", "rec"], capture_output=True
    ).returncode == 0

    if sox_available:
        print("   🎙️  'rec' (sox) bulundu — terminalden kayıt yapılacak")
        print()
        print("   ─────────────────────────────────────────────")
        print("   Semptomlarınızı Türkçe anlatın.")
        print("   Bitirmek için Ctrl+C'ye basın.")
        print("   ─────────────────────────────────────────────")
        print()
        input("   ▶ Kayda başlamak için ENTER'a basın...")
        print("   🔴 KAYDEDİLİYOR... (Ctrl+C ile durdurun)")
        print()

        try:
            subprocess.run(
                ["rec", output_path, "rate", "16000", "channels", "1",
                 "trim", "0", str(max_seconds)],
                check=True
            )
        except KeyboardInterrupt:
            print("\n   ⏹️  Kayıt durduruldu.")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Kayıt hatası: {e}")
            return None
    else:
        # Fallback: use macOS afrecord (built-in, no extra deps)
        afrecord_available = subprocess.run(
            ["which", "afrecord"], capture_output=True
        ).returncode == 0

        if not afrecord_available:
            # Last resort: give instructions for manual recording
            print("   ⚠️  'sox' yüklü değil. Ses kaydı için:")
            print()
            print("   Seçenek 1 — sox yükle:")
            print("     brew install sox")
            print()
            print("   Seçenek 2 — Telefonundan kaydet:")
            print("     iPhone Sesli Notlar uygulamasından .m4a olarak kaydet,")
            print("     AirDrop ile Mac'e at, sonra:")
            print(f"     python src/pipeline.py --audio kayit.m4a --nlp-mode llm")
            print()
            print("   Seçenek 3 — QuickTime Player:")
            print("     Dosya → Yeni Ses Kaydı → Kaydet → .m4a olarak kaydet")
            print(f"     python src/pipeline.py --audio kayit.m4a --nlp-mode llm")
            print()
            return None

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        size_kb = os.path.getsize(output_path) / 1024
        print(f"\n   ✅ Kayıt tamamlandı: {output_path} ({size_kb:.1f} KB)")
        return output_path
    else:
        print("   ❌ Kayıt dosyası oluşturulamadı")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="🩺 Praevidio AI — Lung Cancer Risk Assessment Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/pipeline.py --interactive              # Text input mode
  python src/pipeline.py --interactive --nlp-mode llm  # With GPT-4o-mini
  python src/pipeline.py --audio recording.m4a      # Audio file mode
  python src/pipeline.py --record                   # Record + full pipeline
  python src/pipeline.py --record --nlp-mode llm    # Record + LLM extraction
  python src/pipeline.py --demo                     # Quick demo scenarios
        """
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--interactive", action="store_true",
                           help="Interactive text input mode")
    mode_group.add_argument("--audio", type=str,
                           help="Path to audio file for Whisper transcription")
    mode_group.add_argument("--record", action="store_true",
                           help="Record from microphone, then run full pipeline")
    mode_group.add_argument("--demo", action="store_true",
                           help="Run predefined demo scenarios")

    parser.add_argument("--nlp-mode", type=str, default=NLP_MODE,
                       choices=["keyword", "llm"],
                       help="NLP extraction mode (default: keyword)")

    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.interactive:
        run_interactive_pipeline(nlp_mode=args.nlp_mode)
    elif args.record:
        audio_path = record_audio()
        if audio_path:
            run_audio_pipeline(audio_path, nlp_mode=args.nlp_mode)
    elif args.audio:
        run_audio_pipeline(args.audio, nlp_mode=args.nlp_mode)


if __name__ == "__main__":
    main()

