// SPDX-License-Identifier: AGPL-3.0-or-later · Copyright (C) 2026 Samed KIZILHAN — Praevidio AI
// Praevidio AI — PWA istemcisi. Backend: src/api/server.py (aynı origin, /sessions…).
"use strict";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const CFG = {
  model: params.get("model") || "v3",          // ?model=v2 ile bahar modeli
  nlp: params.get("nlp") || null,              // ?nlp=llm | keyword (boşsa sunucu varsayılanı)
  token: params.get("token") || "",            // sunucu PRAEVIDIO_API_TOKEN kullanıyorsa
};
const VAD = { maxMs: 30000, noSpeechMs: 8000, silenceMs: 1600, minLevel: 0.012 };

const S = {                                    // istemci durumu
  sid: null, status: null, hint: "", busy: false,
  mode: loadMode(),                            // "voice" | "text" — kullanıcı başta seçer
  stream: null, recorder: null, recording: false, audioQueue: [], playing: false, result: null,
};

// ───────── yardımcılar ─────────
function loadPref(k, d) { try { const v = localStorage.getItem("pv-" + k); return v === null ? d : v === "1"; } catch { return d; } }
function savePref(k, v) { try { localStorage.setItem("pv-" + k, v ? "1" : "0"); } catch { /* özel mod */ } }
function loadMode() { try { return localStorage.getItem("pv-mode") === "text" ? "text" : "voice"; } catch { return "voice"; } }
function setMode(m) {
  S.mode = m; try { localStorage.setItem("pv-mode", m); } catch { /* özel mod */ }
  document.body.classList.toggle("mode-voice", m === "voice");
  document.body.classList.toggle("mode-text", m === "text");
  const b = $("btn-mode");
  b.textContent = m === "voice" ? "⌨️ Yazılıya geç" : "🎤 Sesliye geç";
  b.setAttribute("aria-label", m === "voice" ? "Yazılı görüşmeye geç" : "Sesli görüşmeye geç");
  $("mic-status").textContent = m === "voice" ? "Anlamadığınız bir şey olursa sorabilirsiniz." : "";
}
const micSupported = () => window.isSecureContext && navigator.mediaDevices && window.MediaRecorder;
function pct(n) {                              // %10 altında iki ondalık: bant sınırında "%1,49 Düşük" net okunur
  const d = Number(n) < 10 ? 2 : 1;
  return "%" + Number(n).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
}
function show(view) {
  for (const v of ["welcome", "chat", "result"]) $("view-" + v).hidden = v !== view;
  $("composer").hidden = view !== "chat"; $("btn-mode").hidden = view !== "chat";
}
function toast(msg, ms = 4000) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => (t.hidden = true), ms); }
function setBusy(b) { S.busy = b; $("composer").classList.toggle("busy", b); $("typing").hidden = !b; if (b) scrollDown(); }
function scrollDown() { requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" })); }

async function api(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  if (CFG.token) headers["Authorization"] = "Bearer " + CFG.token;
  if (opts.json !== undefined) { headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(opts.json); }
  const r = await fetch(path, { method: opts.method || "GET", headers, body: opts.body });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(data.detail || ("HTTP " + r.status)); e.status = r.status; throw e; }
  return data;
}

// ───────── mesajlar ve ses ─────────
function addMessage(role, text, audioUrl) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  el.textContent = text;
  if (audioUrl) {
    const b = document.createElement("button");
    b.className = "replay"; b.textContent = "🔈"; b.setAttribute("aria-label", "Tekrar dinle");
    b.onclick = () => { stopAudio(); enqueueAudio([audioUrl], true); };
    el.appendChild(b);
  }
  $("messages").appendChild(el);
  scrollDown();
}

function enqueueAudio(urls, force = false) {
  if (S.mode !== "voice" && !force) return Promise.resolve();   // yazılı modda otomatik okuma yok
  S.audioQueue.push(...urls.filter(Boolean));
  return playNext();
}
function playNext() {
  return new Promise((resolve) => {
    const step = () => {
      const url = S.audioQueue.shift();
      if (!url) { S.playing = false; return resolve(); }
      S.playing = true;
      const p = $("player");
      p.onended = step; p.onerror = step;
      p.src = url;
      p.play().catch(step);                   // otomatik oynatma engellenirse sıradakine geç
    };
    if (S.playing) { const wait = setInterval(() => { if (!S.playing) { clearInterval(wait); resolve(); } }, 200); return; }
    step();
  });
}
function stopAudio() { S.audioQueue = []; const p = $("player"); p.pause(); p.onended = null; S.playing = false; }

function renderChips(hint) {
  const box = $("chips"); box.innerHTML = "";
  const opts = [];
  if (/evet/i.test(hint)) opts.push("Evet", "Hayır", "Bilmiyorum");
  if (/şikâyeti yok|şikayeti yok/i.test(hint)) opts.push("Şikâyetim yok");
  opts.push("Bu ne demek?");                     // ara soru: ajan açıklar, sonra soruyu tekrar sorar
  for (const o of opts) {
    const b = document.createElement("button");
    b.className = "chip" + (o === "Bu ne demek?" ? " ask" : ""); b.type = "button"; b.textContent = o;
    b.onclick = () => { cancelRecording(); sendText(o); };
    box.appendChild(b);
  }
}

// ───────── tur akışı ─────────
async function handleTurn(data) {
  S.status = data.status; S.hint = data.hint || "";
  if (data.heard !== undefined && data.heard !== null) addMessage("user", data.heard || "(anlaşılamadı)");
  const urls = [];
  for (const m of data.messages || []) { addMessage("agent", m.text, m.audio_url); urls.push(m.audio_url); }
  renderChips(S.hint);
  setBusy(false);

  if (data.status === "finished") {
    S.result = data.result;
    renderResult(data.result);
    enqueueAudio(urls.slice(-1)).then(() => {});     // sonuç özetini oku (yalnız sesli modda)
    setTimeout(() => { show("result"); window.scrollTo({ top: 0 }); }, 600);
    return;
  }
  if (data.status === "error" || data.status === "expired") {
    toast(data.status === "expired" ? "Oturumun süresi doldu. Yeniden başlayalım." : "Bir hata oluştu: " + (data.error || ""));
    return;
  }
  await enqueueAudio(urls);
  if (S.mode === "voice" && S.status === "awaiting_input" && !S.busy) startRecording(true);
}

async function startSession(mode) {
  if (mode === "voice") {                         // mikrofon iznini başta, kullanıcı dokunuşuyla iste
    if (!micSupported()) {
      toast("Bu bağlantıda mikrofon kullanılamıyor (https gerekir). Yazılı görüşmeyle devam ediyoruz.", 6000);
      mode = "text";
    } else {
      try { await ensureStream(); }
      catch { toast("Mikrofon izni verilmedi. Yazılı görüşmeyle devam ediyoruz.", 5000); mode = "text"; }
    }
  }
  setMode(mode);
  for (const id of ["btn-start-voice", "btn-start-text"]) $(id).disabled = true;
  $("player").play().catch(() => {});             // iOS: oynatıcıyı kullanıcı dokunuşuyla "aç"
  try {
    const body = { model: CFG.model, tts: true, client: "pwa-" + mode };
    if (CFG.nlp) body.nlp_mode = CFG.nlp;
    $("messages").innerHTML = "";
    show("chat"); setBusy(true);
    const data = await api("/sessions", { method: "POST", json: body });
    S.sid = data.session_id;
    await handleTurn(data);
  } catch (e) {
    setBusy(false); show("welcome"); toast("Sunucuya bağlanılamadı: " + e.message);
  } finally { for (const id of ["btn-start-voice", "btn-start-text"]) $(id).disabled = false; }
}

async function sendText(text) {
  text = (text || "").trim();
  if (!text || S.busy || S.status !== "awaiting_input") return;
  stopAudio();
  addMessage("user", text);
  setBusy(true);
  try { await handleTurn(await api(`/sessions/${S.sid}/turn`, { method: "POST", json: { text } })); }
  catch (e) { setBusy(false); toast("Gönderilemedi: " + e.message); }
}

async function sendAudio(blob, ext) {
  setBusy(true);
  const fd = new FormData();
  fd.append("file", blob, "cevap." + ext);
  try { await handleTurn(await api(`/sessions/${S.sid}/turn-audio`, { method: "POST", body: fd })); }
  catch (e) { setBusy(false); toast("Ses gönderilemedi: " + e.message + " — seçeneklere dokunabilir ya da yazılıya geçebilirsiniz.", 6000); }
}

// ───────── ses kaydı (susunca otomatik durur) ─────────
function pickMime() {
  const c = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  for (const m of c) if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(m)) return m;
  return "";
}
function extFor(mime) { return /mp4/.test(mime) ? "m4a" : /ogg/.test(mime) ? "ogg" : "webm"; }

async function ensureStream() {
  if (S.stream && S.stream.active) return S.stream;
  S.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  return S.stream;
}

async function startRecording(auto = false) {
  if (S.recording || S.busy || S.status !== "awaiting_input") return;
  if (!micSupported()) {
    toast("Ses kaydı için güvenli bağlantı (https veya localhost) gerekir. Yazılı görüşmeye geçtik.", 6000);
    setMode("text"); return;
  }
  stopAudio();
  let stream;
  try { stream = await ensureStream(); }
  catch { toast("Mikrofon izni verilmedi. Yazılı görüşmeye geçtik."); setMode("text"); return; }

  const mime = pickMime();
  const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  let spoke = false, stopped = false;
  rec.ondataavailable = (e) => e.data && e.data.size && chunks.push(e.data);

  // Basit VAD: ortam gürültüsünü ölç, konuşma başladıktan sonra sessizlikte dur
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = ctx.createMediaStreamSource(stream);
  const an = ctx.createAnalyser(); an.fftSize = 1024; src.connect(an);
  const buf = new Float32Array(an.fftSize);
  const t0 = performance.now(); let noise = 0, nSamples = 0, lastVoice = t0;

  const finish = (discard, silent = false) => {
    if (stopped) return; stopped = true;
    clearInterval(timer); ctx.close().catch(() => {});
    S.recording = false; $("btn-mic").classList.remove("recording");
    $("mic-status").textContent = S.mode === "voice" ? "Konuşmak için mikrofona dokunun." : "";
    rec.onstop = () => {
      if (silent) return;
      if (discard || !spoke) { toast("Sizi duyamadım. Mikrofona dokunup tekrar deneyin ya da bir seçeneğe dokunun."); return; }
      sendAudio(new Blob(chunks, { type: rec.mimeType || mime || "audio/webm" }), extFor(rec.mimeType || mime));
    };
    rec.stop();
  };
  const timer = setInterval(() => {
    an.getFloatTimeDomainData(buf);
    let sum = 0; for (const v of buf) sum += v * v;
    const rms = Math.sqrt(sum / buf.length), now = performance.now();
    if (now - t0 < 300) { noise += rms; nSamples++; return; }
    const thr = Math.max(VAD.minLevel, (nSamples ? noise / nSamples : 0) * 2.5);
    if (rms > thr) { spoke = true; lastVoice = now; }
    if (spoke && now - lastVoice > VAD.silenceMs) finish(false);
    else if (!spoke && now - t0 > VAD.noSpeechMs) finish(true);
    else if (now - t0 > VAD.maxMs) finish(false);
  }, 100);

  S.recording = true;
  S.stopRecording = () => finish(false);
  S.cancelRecording = () => finish(true, true);
  $("btn-mic").classList.add("recording");
  $("mic-status").textContent = "Dinliyorum… Bitirince susmanız yeterli (ya da mikrofona dokunun).";
  rec.start(250);
}

function cancelRecording() { if (S.recording && S.cancelRecording) S.cancelRecording(); }
function releaseMic() { if (S.stream) { S.stream.getTracks().forEach((t) => t.stop()); S.stream = null; } }

// ───────── sonuç ─────────
function bandOf(r) {
  if (r.risk_6y_factors === null || r.risk_6y_factors === undefined) return { cls: r.risk_level, label: r.risk_level_tr };
  const lvl = r.risk_level_factors || "moderate";
  return { cls: lvl === "low" ? "below" : lvl, label: r.risk_level_factors_display_tr || r.risk_level_factors_tr || "" };
}
function renderResult(r) {
  if (!r) return;
  const main = r.risk_6y_factors ?? r.risk_score;
  $("risk6y").textContent = pct(main);
  const b = bandOf(r); const band = $("band");
  band.textContent = b.label; band.className = "band " + b.cls;
  for (const [id, txt] of [["relative", r.relative_message_tr], ["projection", r.projection_message_tr]]) {
    $(id).textContent = txt || ""; $(id).hidden = !txt;
  }
  // Belirti katmanı: tam skor artık bantlanmaz. Acilse gerekçeler alarm kutusunda, değilse belirti notu ayrı satırda.
  const fs = $("full-score");
  const urgent = r.urgent_assessment ?? (r.alarm && r.alarm.level === "urgent");
  const reasons = (r.urgent_reasons_tr && r.urgent_reasons_tr.length) ? r.urgent_reasons_tr : ((r.alarm && r.alarm.reasons_tr) || []);
  fs.textContent = (!urgent && r.symptom_level === "low" && r.symptom_message_tr) ? r.symptom_message_tr : "";
  $("alarm").hidden = !urgent;
  $("alarm-reasons").innerHTML = "";
  if (urgent) for (const x of reasons) { const li = document.createElement("li"); li.textContent = x; $("alarm-reasons").appendChild(li); }
  const sc = $("screening");
  if (r.screening && r.screening.eligible === true) { sc.hidden = false; sc.textContent = "✓ " + (r.screening.message_tr || "Düşük doz BT taraması için uygun görünüyorsunuz."); }
  else sc.hidden = true;
  $("recommendation").textContent = r.recommendation_tr || "";
  $("btn-report").disabled = !r.report_url;
}

async function openReport() {
  const url = S.result && S.result.report_url;
  if (!url) return;
  if (!CFG.token) { window.open(url, "_blank"); return; }
  const w = window.open("", "_blank");                       // açılır pencere engeline karşı önce aç
  try {
    const r = await fetch(url, { headers: { Authorization: "Bearer " + CFG.token } });
    const blobUrl = URL.createObjectURL(await r.blob());
    if (w) w.location = blobUrl; else window.location = blobUrl;
  } catch (e) { if (w) w.close(); toast("Rapor açılamadı: " + e.message); }
}

async function downloadTranscript() {         // agent:/user: satırları — hata notu ekleyip geri gönderilebilir
  if (!S.sid) return;
  try {
    const headers = CFG.token ? { Authorization: "Bearer " + CFG.token } : {};
    const r = await fetch(`/sessions/${S.sid}/transcript.txt`, { headers });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await r.blob()); a.download = `praevidio_${S.sid}.txt`;
    document.body.appendChild(a); a.click(); a.remove();
  } catch (e) { toast("Kayıt indirilemedi: " + e.message); }
}

function restart() {
  cancelRecording(); stopAudio(); releaseMic();
  Object.assign(S, { sid: null, status: null, hint: "", result: null, recording: false });
  $("messages").innerHTML = ""; $("chips").innerHTML = "";
  show("welcome");
}

// ───────── olaylar ─────────
$("btn-start-voice").onclick = () => startSession("voice");
$("btn-start-text").onclick = () => startSession("text");
$("btn-mode").onclick = async () => {
  if (S.mode === "voice") { cancelRecording(); stopAudio(); setMode("text"); $("input-text").focus(); return; }
  if (!micSupported()) { toast("Bu bağlantıda mikrofon kullanılamıyor (https gerekir).", 5000); return; }
  try { await ensureStream(); } catch { toast("Mikrofon izni verilmedi."); return; }
  setMode("voice");
  if (S.status === "awaiting_input" && !S.busy) startRecording(true);
};
$("btn-restart").onclick = restart;
$("btn-report").onclick = openReport;
$("btn-transcript").onclick = downloadTranscript;
$("btn-mic").onclick = () => (S.recording ? S.stopRecording() : startRecording(false));
$("form-text").onsubmit = (e) => { e.preventDefault(); const i = $("input-text"); sendText(i.value); i.value = ""; };
setMode(S.mode);

api("/health").then((h) => {
  $("server-status").textContent = `Sunucu hazır · model ${CFG.model} · ${CFG.nlp || h.default_nlp_mode} modu`;
}).catch(() => {
  $("server-status").textContent = "Sunucuya ulaşılamıyor.";
  for (const id of ["btn-start-voice", "btn-start-text"]) $(id).disabled = true;
});

if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("sw.js").catch(() => {});
