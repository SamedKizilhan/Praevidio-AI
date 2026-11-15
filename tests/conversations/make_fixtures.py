# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""Örnek kayıtları yeniden üretir (ajan metni bilinçli değiştiğinde): python tests/conversations/make_fixtures.py"""
import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from conversation.replay import ScriptedChannel, _engine  # noqa: E402
from conversation.voice_agent import ConversationAgent  # noqa: E402

PHONE_NOTE = ("15 Kasım 2026 telefon denemesi (pwa-voice, yazılıya geçildi). Özgün kayıtta '45 yaş erkek' ve '45' "
              "anlaşılmamış, yaş üç kez sorulmuştu; düzeltmeden sonra ilk cevap yettiği için fazlalık iki cevap "
              "('45', 'Bu ne demek?', '45 yaşındayım') bu kayıttan çıkarıldı.")

FIXTURES = [
    ("01_paket_yil_ara_soru",
     ["45 yaşındayım erkeğim", "günde 10 tane, yaklaşık 10 yıldır içiyorum", "5 paket-yıl ne demek ki?", "evet",
      "şikâyetim yok", "Bu ne demek?", "hayır", "hayır", "hayır", "hayır", "hayır", "hayır", "hayır",
      "hayır", "neden soruyorsunuz?", "hayır", "hayır", "İstanbul"],
     "3 Kasım 2026 kullanıcı bildirimi: '5 paket-yıl ne demek?' sorusu cevapsız kalıyordu (düzeltildi).",
     ['_pack_years=5', 'ajan_der="günde 10 sigara yaklaşık 0,5 paket"', 'ajan_der="üç haftadan uzun"',
      'ajan_der="asbeste"', 'COUGHING=0', 'COPD=0', '_province="İstanbul"', 'ajan_der="tarama eşiğinin altında"',
      'ajan_der="bugün bırakırsanız"', 'belirti="none"', 'acil=false', 'bitti=true'],
     {"5 paket-yıl ne demek ki?": "önceden açıklamadan sonraki soruya geçiyordu — artık açıklayıp aynı soruyu tekrar sormalı"}),
    ("02_35y_kadin_tum_belirtiler",
     ["35 yaşında kadınım", "günde bir paket, 18 yıldır içiyorum", "evet",
      "öksürüyorum, nefes darlığım var, göğsüm ağrıyor, hırıltı oluyor, çok halsizim, kan tükürdüm ve kilo verdim",
      "evet", "evet", "hayır", "Iğdır"],
     "4 Kasım 2026 simülasyonu: 35 yaş, aktif içici 18 paket-yıl, aile öyküsü + meslek + yüksek hava, KOAH yok, 7 belirti.",
     ['_pack_years=18', 'FAMILY_HISTORY=1', 'ASBESTOS=1', 'COPD=0', 'AIR_POLLUTION=2', 'HEMOPTYSIS=1', 'WEIGHT_LOSS=1',
      'risk_level_factors="low"', 'ajan_der="tarama eşiğinin altında"', 'ajan_der="yaklaşık 34 katı"',
      'ajan_der="10.000 kişiden yaklaşık 42 kişinin"', 'ajan_der="bu sayı yaklaşık 1,2"',
      'ajan_der="tarama aralığına girersiniz"', 'ajan_demez="düşük risk grubuna"', 'ajan_demez="yüksek risk"',
      'ajan_demez="birkaç haftadır"', 'ajan_der="kısa sürede"', 'alarm="none"', 'belirti="elevated"', 'acil=true',
      'bitti=true'],
     {"Iğdır": "ÇÖZÜLDÜ (4 Kas 2026): 40 yaş altında NICE alarmı yoktu ve 'birkaç haftadır sürüyorsa' deniyordu; belirti katmanı (bugünkü belirtilerin kansere bağlı olma olasılığı, eşik %3) ve her yaşta hemoptizi kuralı ile artık 'kısa sürede hekim' öneriliyor; tam skor ('%14,4 yüksek risk') bantlanmıyor"}),
    ("03_telefon_45_yas_erkek",
     ["45 yaş erkek", "Günde 1 paket 10 yıl", "Evet", "Öksürük göğüs ağrısı halsizlik", "Hayır", "Evet", "Hayır", "Evet",
      "Bilmiyorum", "Hayır", "Hayır", "İstanbul"],
     PHONE_NOTE,
     ['_age_exact=45', 'GENDER=1', '_pack_years=10', 'ajan_der="10 yıldır günde 1 paket sigara içiyorsunuz"',
      'ajan_demez="paket-yıl. Doğru mu"', 'ajan_demez="tam alamadım"', 'FAMILY_HISTORY=yok', 'WHEEZING=1',
      'ajan_der="40 yaşın üzerindesiniz ve açıklanamayan 4 belirtiniz var"', 'ajan_demez="40 yaş ve üstü ve"',
      'alarm="urgent"', 'belirti="low"', 'acil=true', 'bitti=true'],
     {"45 yaş erkek": "özgün kayıtta: 'Şunu tam alamadım: yaşınızı' — artık ilk cevapta anlaşılmalı",
      "Günde 1 paket 10 yıl": "özgün kayıtta onay 'yaklaşık 10 paket-yıl' diyordu — kullanıcının söylediği biçimde olmalı"}),
]


def make(name, answers, header_note, expects, notes_after):
    ch = ScriptedChannel(answers)
    ag = ConversationAgent(ch, nlp_mode="keyword", model_version="v3", engine=_engine("v3"), save_transcript=False,
                           session_id=name, transcript_meta={"kanal": "test-fixture"})
    with contextlib.redirect_stdout(io.StringIO()):
        ag.run()
    lines = ag.transcript.lines[:]
    out = [lines[0], f"# oturum: {name}  ·  model: v3  ·  nlp: keyword  ·  kanal: test-fixture", "# " + header_note]
    for line in lines[3:]:
        if line.startswith("# rapor:"):
            continue
        out.append(line)
        for trig, note in notes_after.items():
            if line == "user: " + trig:
                out.append(">> " + note)
    out += ["# beklenen: " + e for e in expects]
    (HERE / f"{name}.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(name, "→", ag.result["risk_6y_factors"], ag.result["risk_score"], ag.result["alarm"]["level"])


if __name__ == "__main__":
    for f in FIXTURES:
        make(*f)
