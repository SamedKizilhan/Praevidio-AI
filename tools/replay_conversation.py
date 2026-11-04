# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Konuşma kaydını yeniden oynatır (make replay F=data/conversations/<kayıt>.txt).

  python tools/replay_conversation.py KAYIT.txt [--model v3|v3.0|v2] [--nlp keyword|llm] [--full]

Çıktı: ">>" hata notları (kayıttaki yerleriyle), kayıt ↔ şimdiki ajan farkı, son kanıt ve sonuç,
"# beklenen:" kontrolleri. Beklenti başarısızsa çıkış kodu 1.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from conversation.replay import replay  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--model")
    p.add_argument("--nlp", choices=["keyword", "llm"])
    p.add_argument("--full", action="store_true", help="şimdiki konuşmanın tamamını da yazdır")
    a = p.parse_args()
    r = replay(Path(a.file), model=a.model, nlp_mode=a.nlp)
    turns = r["record"]["turns"]
    print(f"▶ {a.file}  ·  model {r['model']}  ·  nlp {r['nlp_mode']}")
    if r["record"]["notes"]:
        print("\n── Kayıttaki hata notları ──")
        for i, note in r["record"]["notes"]:
            ctx = turns[i] if 0 <= i < len(turns) else None
            if ctx:
                print(f"  {ctx['role']}: {ctx['text'][:110]}")
            print(f"    >> {note}")
    print("\n── Kayıt ↔ şimdi (yalnız farklar) ──")
    print("\n".join(r["diff"][2:]) if r["diff"] else "  (fark yok — ajan aynı cevapları verdi)")
    if a.full:
        print("\n── Şimdiki konuşma ──")
        print("\n".join(r["new_turns"]))
    print("\n── Durum ──")
    print(f"  bitti: {r['finished']}" + (f" · kullanılmayan cevap: {r['unused_answers']}" if r["unused_answers"] else ""))
    if r["result"]:
        res = r["result"]
        print(f"  6y %{res.get('risk_6y_factors')} ({res.get('risk_level_factors')}) · tam %{res['risk_score']} "
              f"({res['risk_level']}) · alarm {(res.get('alarm') or {}).get('level')}")
    print("  kanıt:", json.dumps(r["evidence"], ensure_ascii=False, sort_keys=True))
    if r["record"]["expect"]:
        print("\n── Beklentiler ──")
        print("  ✅ hepsi tuttu" if not r["fails"] else "\n".join("  ❌ " + f for f in r["fails"]))
    sys.exit(1 if r["fails"] else 0)


if __name__ == "__main__":
    main()
