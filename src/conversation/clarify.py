# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samed KIZILHAN — Praevidio AI (https://github.com/SamedKizilhan/Praevidio-AI)
"""
Praevidio AI — Ara soru (açıklama) yanıtlayıcı
==============================================
Kullanıcı bir soruyu cevaplamak yerine soru sorarsa ("5 paket-yıl ne demek?",
"neden soruyorsunuz?", "tekrar eder misiniz?") ajan önce bunu yanıtlar, sonra
kendi sorusunu tekrar sorar. Anket akışı (durum makinesi) DEĞİŞMEZ; yalnız
cevap bekleme noktasına bir açıklama döngüsü eklenir.

Yanıt kaynağı, öncelik sırasıyla:
  1. "Tekrar eder misiniz?" → açıklama yok, soru yeniden sorulur
  2. "Neden soruyorsunuz?" → o sorunun gerekçesi (WHY)
  3. Kullanıcının cümlesindeki terim → sözlük (GLOSSARY; paket-yıl kişiselleştirilir)
  4. "Ne demek / anlamadım" + terim yok → son sorudaki terim, yoksa sorunun açıklaması
  5. Eşleşme yok: llm modunda kısıtlı GPT yanıtı (tanı/yüzde/tedavi YOK), keyword modunda
     kibar bir yönlendirme
Sözlük ve gerekçeler sabit metin → keyword modunda da çalışır, ücretsiz ve tekrarlanabilir.
"""
import re

MAX_SIDE_QUESTIONS = 3   # aynı soru üzerinde art arda en fazla kaç ara soru yanıtlanır


def _norm(text: str) -> str:
    t = (text or "").replace("I", "ı").replace("İ", "i").lower().replace("̇", "")
    return re.sub(r"\s+", " ", t).strip()


_REPEAT = ["tekrar eder", "tekrar söyle", "tekrarlar mı", "tekrarlayabilir", "bir daha söyle",
           "bir daha sor", "ne sordu", "duyamadım", "duymadım", "kaçırdım"]
_WHY = ["neden sor", "niye sor", "neden soru", "niye soru", "ne için sor", "neden önemli",
        "ne işe yar", "neden gerekli", "niye gerekli", "neden lazım", "niye lazım"]
_WHAT = ["ne demek", "nedir", "ne anlama", "anlamı ne", "anlamadım", "anlayamadım",
         "açıklar mı", "açıklayabilir", "açar mısın", "açar mısınız", "nasıl yani",
         "örnek ver", "kastedi", "ne kastet", "ne oluyor o", "neymiş"]
_QWORDS = ["ne ", "neden", "niye", "nasıl", "nedir", "neymiş"]


def is_side_question(text: str) -> bool:
    """Kullanıcı cevap yerine soru mu sordu? (Açık işaretler; '?' yalnız soru kelimesiyle.)"""
    t = _norm(text)
    if not t:
        return False
    if any(m in t for m in _REPEAT + _WHY + _WHAT):
        return True
    return t.endswith("?") and not re.search(r"\d", t) and any(w in t for w in _QWORDS)


# ──────────────────────────────────────────────
# Sözlük: (anahtar kelimeler, açıklama)
# ──────────────────────────────────────────────
GLOSSARY = {
    "pack_years": (["paket yıl", "paket-yıl", "paketyıl", "paket/yıl", "paketi yıl"],
                   "Paket-yıl, ömür boyu içilen sigara miktarının ölçüsüdür: günde içilen paket "
                   "sayısı ile içilen yıl sayısı çarpılır, bir paket 20 sigaradır. Örneğin günde "
                   "1 paketi 20 yıl içmek 20 paket-yıl eder. Tarama önerilerinde kullanılır; 50–80 "
                   "yaş arasında 20 paket-yıl ve üzeri, düşük doz tomografi taraması ölçütlerinden biridir."),
    "copd": (["koah", "obstrüktif"],
             "KOAH, yani kronik obstrüktif akciğer hastalığı, hava yollarının kalıcı olarak daraldığı ve "
             "çoğunlukla sigaraya bağlı gelişen uzun süreli bir akciğer hastalığıdır. Amfizem ve kronik "
             "bronşit de bu gruba girer. Tanıyı genellikle solunum fonksiyon testiyle hekim koyar."),
    "emphysema": (["amfizem"],
                  "Amfizem, akciğerdeki küçük hava keseciklerinin hasar görüp genişlemesidir; KOAH'ın bir türüdür."),
    "bronchitis": (["bronşit"],
                   "Kronik bronşit, en az iki yıl üst üste, yılda en az üç ay süren balgamlı öksürüktür; "
                   "KOAH'ın bir türüdür."),
    "wheezing": (["hırıltı", "hırıl", "hışıltı"],
                 "Hırıltı, nefes alıp verirken göğsünüzden gelen ıslık ya da vızıltı benzeri sestir; "
                 "hava yolları daraldığında olur."),
    "hemoptysis": (["kan tükür", "hemoptizi", "kanlı balgam"],
                   "Kan tükürme, öksürükle birlikte balgamda kan ya da kan çizgileri gelmesidir. Böyle bir "
                   "durum varsa, bu değerlendirmenin sonucundan bağımsız olarak bir hekime başvurmanız önerilir."),
    "dyspnea": (["nefes darl"],
                "Nefes darlığı, normalde zorlanmadığınız işlerde, örneğin merdiven çıkarken ya da yürürken "
                "nefesinizin yetmediğini hissetmenizdir."),
    "cough": (["geçmeyen öksürük", "geçmeyen", "inatçı öksürük"],
              "Geçmeyen öksürükten kastımız, üç haftadan uzun süren ya da sık sık tekrarlayan öksürüktür."),
    "weight_loss": (["kilo kayb", "istemsiz", "kilo ver"],
                    "İstemsiz kilo kaybı, diyet ya da spor yapmadan son aylarda belirgin şekilde kilo vermenizdir."),
    "fatigue": (["halsizlik", "yorgunluk"],
                "Halsizlik ya da yorgunluktan kastımız, dinlenmekle geçmeyen ve günlük işlerinizi "
                "zorlaştıran bir bitkinlik hâlidir."),
    "first_degree": (["birinci derece", "akraba"],
                     "Birinci derece akrabalarınız anne, baba, kardeşleriniz ve çocuklarınızdır."),
    "asbestos": (["asbest", "eternit", "yalıtım", "meslek grub", "silika"],
                 "Bu meslek gruplarında asbest ve silika gibi akciğere zararlı tozlar solunabiliyor. "
                 "Asbest, eskiden yalıtımda ve eternit denen çatı ve boru malzemelerinde kullanılan, "
                 "solunduğunda akciğer kanseri riskini artıran bir mineral liftir."),
    "ketem": (["ketem"],
              "KETEM, Sağlık Bakanlığı'na bağlı Kanser Erken Teşhis, Tarama ve Eğitim Merkezleri'dir; "
              "illerde bulunur ve kanser taraması ile bilgilendirme hizmeti verir."),
    "ldct": (["tomografi", "ldct", "düşük doz"],
             "Düşük doz bilgisayarlı tomografi, akciğerin normal tomografiye göre çok daha az radyasyonla "
             "görüntülendiği bir tarama yöntemidir; akciğer kanserini belirti vermeden, erken evrede "
             "yakalamaya yarar."),
    "risk": (["6 yıllık", "altı yıllık", "risk skoru", "risk puan"],
             "Altı yıllık risk, sizinle benzer özelliklere sahip 100 kişiden yaklaşık kaçının önümüzdeki "
             "altı yıl içinde akciğer kanseri tanısı alabileceğinin tahminidir. Bir tanı değildir."),
    "pm25": (["pm2", "partikül", "hava kirlil"],
             "Yaşadığınız ilin yıllık ince partikül, yani PM2.5 hava kirliliği düzeyini kullanıyoruz. "
             "Uzun süre kirli havaya maruz kalmak akciğer kanseri riskini biraz artırır."),
}

# ──────────────────────────────────────────────
# Soru → gerekçe ("neden soruyorsunuz?") — sorunun metnindeki ifadeyle eşlenir
# ──────────────────────────────────────────────
WHY = [
    (["yaşınızı ve cinsiyet", "yaşınızı", "cinsiyetinizi"],
     "Akciğer kanseri riski yaşla birlikte belirgin şekilde artar ve kadın ile erkek arasında farklılık "
     "gösterir; bu yüzden ilk olarak bunu soruyorum."),
    (["not ettim", "doğru mu"],
     "Yanlış anlaşılmış bir yaş ya da sigara bilgisi sonucu çok etkiler; bu yüzden size teyit ettiriyorum."),
    (["bıraktınız", "bıraktığınızı"],
     "Sigarayı bıraktıktan sonra geçen süre uzadıkça risk azalır; ayrıca tarama önerisi bırakmanın "
     "üzerinden 15 yıldan az geçenler için geçerlidir."),
    (["sigara", "kaç adet", "kaç yıl"],
     "Sigara akciğer kanserinin en önemli risk etkenidir; ne kadar ve ne kadar süre içildiği hem riskinizi "
     "hem de taramaya uygun olup olmadığınızı belirler."),
    (["şikâyetleriniz", "şikayetleriniz"],
     "Bazı belirtiler, risk skorundan bağımsız olarak kısa sürede bir hekime görünmenizi gerektirebilir; "
     "bu yüzden önce sizin kendi şikâyetlerinizi dinlemek istiyorum."),
    (["koah", "amfizem", "bronşit"],
     "KOAH hem akciğer kanseri riskini artırır hem de öksürük ve nefes darlığı gibi belirtilerin sık bir "
     "nedenidir; model bu ikisini ayırt edebilmek için bunu bilmeli."),
    (["akrabalarınızda"],
     "Anne, baba ya da kardeşte akciğer kanseri olması riski artıran bir etkendir."),
    (["meslek grup"],
     "Bu işlerde akciğere zararlı tozlara, özellikle asbeste maruz kalınabiliyor; bu da riski artırır."),
    (["ilde yaşıyorsunuz", "ilinizi"],
     "Yaşadığınız ilin hava kirliliği düzeyini bulmak için soruyorum; uzun süreli kirli hava riski biraz artırır."),
    (["öksürük", "nefes darlığı", "göğüs ağrı", "hırıltı", "yorgunluk", "halsizlik", "kan tükür", "kilo kayb"],
     "Bu belirti tek başına bir şey ifade etmez, ama bazı belirtilerin birlikte olması hekime görünmenizi "
     "gerektirebilir; bu yüzden tek tek soruyorum."),
]


def _glossary_hits(t: str):
    hits = []
    for key, (pats, _) in GLOSSARY.items():
        pos = [t.find(p) for p in pats if p in t]
        if pos:
            hits.append((min(pos), key))
    return [k for _, k in sorted(hits)]


def _num(x) -> str:
    return f"{x:g}".replace(".", ",")          # Türkçe ondalık virgülü (TTS "sıfır virgül beş" okur)


def _explain(key: str, evidence: dict) -> str:
    text = GLOSSARY[key][1]
    if key == "pack_years" and evidence:
        c, y, py = evidence.get("_cigs_per_day"), evidence.get("_years_smoked"), evidence.get("_pack_years")
        if c and y and py:
            text += (f" Sizin için: günde {_num(c)} sigara yaklaşık {_num(c / 20)} paket eder; bunu {_num(y)} yıl "
                     f"içtiğiniz için yaklaşık {_num(py)} paket-yıl hesapladım.")
        elif py:
            text += f" Sizin için yaklaşık {_num(py)} paket-yıl hesapladım."
    return text


def _why(question: str):
    q = _norm(question)
    for pats, txt in WHY:
        if any(p in q for p in pats):
            return txt
    return None


# ──────────────────────────────────────────────
# Eşleşme yoksa (yalnız llm modu): kısıtlı GPT yanıtı
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """Sen Praevidio AI'ın Türkçe konuşan, sakin ve nazik akciğer sağlığı farkındalık asistanısın.
Kullanıcıyla yapılandırılmış bir risk değerlendirmesi yapıyorsun; kullanıcı bir soruyu cevaplamak yerine araya
bir soru sordu. Görevin yalnızca bu ara soruyu yanıtlamak.

Kurallar:
- Türkçe, sade, en fazla iki kısa cümle. Tıbbi terimleri günlük dille açıkla.
- Tanı koyma; kullanıcının risk yüzdesini, sonucunu ya da kanser olup olmadığını tahmin etme.
- İlaç, tedavi ya da doz önerme. Kan tükürme, şiddetli nefes darlığı veya göğüs ağrısı gibi acil durumlarda
  bir hekime, gerekirse 112'ye başvurmasını söyle.
- Soru değerlendirmeyle ilgisizse bunu kibarca belirt ve değerlendirmeye devam etmeyi öner.
- Kendi sorunu tekrar etme ve yeni soru sorma; sistem soruyu ardından kendisi tekrar soracak.
- Sözlükteki tanımlarla çelişme."""

_client = None


def _llm_answer(user_text: str, question: str) -> str:
    global _client
    from config import OPENAI_API_KEY, LLM_MODEL
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY, timeout=10)
    glossary = "\n".join(f"- {v[0][0]}: {v[1]}" for v in GLOSSARY.values())
    r = _client.chat.completions.create(
        model=LLM_MODEL, temperature=0.2, max_tokens=160,
        messages=[{"role": "system", "content": SYSTEM_PROMPT + "\n\nSözlük:\n" + glossary},
                  {"role": "user", "content": f"Asistanın sorduğu soru: {question}\nKullanıcının ara sorusu: {user_text}"}])
    return (r.choices[0].message.content or "").strip()


FALLBACK = ("Bu soruyu burada yanıtlayamıyorum; değerlendirme bittikten sonra hekiminize sorabilirsiniz.")


def answer_side_question(user_text: str, question: str = "", evidence: dict = None,
                         nlp_mode: str = "keyword") -> str:
    """Ara soruya kısa bir yanıt döndürür. Boş metin → yalnız soruyu tekrar et."""
    t = _norm(user_text)
    if any(m in t for m in _REPEAT) and not any(m in t for m in _WHY + _WHAT):
        return ""
    if any(m in t for m in _WHY):
        why = _why(question)
        if why:
            return why
    hits = _glossary_hits(t)
    if hits:
        return " ".join(_explain(k, evidence or {}) for k in hits[:2])
    if any(m in t for m in _WHAT):
        qhits = _glossary_hits(_norm(question))
        if qhits:
            return _explain(qhits[0], evidence or {})
    if nlp_mode == "llm":
        try:
            ans = _llm_answer(user_text, question)
            if ans:
                return ans
        except Exception as e:  # ağ/anahtar hatası → sabit yanıt
            print(f"   ⚠️  Ara soru LLM yanıtı alınamadı: {e}")
    return _why(question) if any(m in t for m in _WHAT) and _why(question) else FALLBACK
