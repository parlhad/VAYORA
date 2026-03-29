// ── VAYORA app.js — FINAL ────────────────────────────────────────────────────
const API = "";  // same origin — FastAPI serves this file

// ── State ─────────────────────────────────────────────────────────────────────
let isListening   = false;
let recognition   = null;
let ttsEnabled    = true;
let currentSpeech = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const chat      = document.getElementById("chat");
const input     = document.getElementById("msgInput");
const sendBtn   = document.getElementById("sendBtn");
const micBtn    = document.getElementById("micBtn");
const aqiStrip  = document.getElementById("aqiStrip");
const modeSelect = document.getElementById("modeSelect");
const langSelect  = document.getElementById("langSelect");

// ── Welcome ───────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  addMessage(
    "agent",
    `**Hello! I'm VAYORA** — your Environmental Intelligence AI.\n\n` +
    `I can help you with:\n` +
    `• 🌫 Live AQI for any city — *"AQI in Delhi"*\n` +
    `• 🌤 Weather & forecast — *"Tomorrow forecast for Mumbai"*\n` +
    `• 💊 Health tips & home remedies\n` +
    `• 🌿 Environment & pollution science\n\n` +
    `Ask me anything — or tap 🎤 to speak.`
  );
});

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMessage(overrideText = null) {
  const text = (overrideText || input.value).trim();
  if (!text) return;

  input.value = "";
  autoResize(input);
  addMessage("user", text);
  setLoading(true);

  const mode     = modeSelect.value;
  const language = langSelect.value;

  try {
    const res = await fetch(`${API}/vayora/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, mode, language })
    });

    const data = await res.json();
    const reply = data.reply || "Sorry, I couldn't process that.";

    // Update AQI strip if city data returned
    if (data.aqi !== undefined && data.city) {
      showAqiStrip(data.city, data.aqi, data.category, data.color);
    }

    addMessage("agent", reply);

    // TTS — speak response
    if (ttsEnabled) speakText(reply);

  } catch (err) {
    addMessage("agent", "⚠️ Network error. Make sure the VAYORA server is running.");
  }

  setLoading(false);
}

// ── Quick chip ────────────────────────────────────────────────────────────────
function sendChip(text) {
  closeDrawer();
  sendMessage(text);
}

// ── Handle Enter key ──────────────────────────────────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ── Auto-resize textarea ──────────────────────────────────────────────────────
function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 130) + "px";
}

// ── Add message bubble ────────────────────────────────────────────────────────
function addMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (role === "agent") {
    const title = document.createElement("div");
    title.className = "msg-title";
    title.textContent = "VAYORA";
    bubble.appendChild(title);
  }

  const body = document.createElement("div");
  body.className = "msg-text";
  body.innerHTML = formatText(text);
  bubble.appendChild(body);

  const meta = document.createElement("div");
  meta.className = "msg-meta";
  meta.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  bubble.appendChild(meta);

  wrapper.appendChild(bubble);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
}

// ── Format text (markdown-lite) ───────────────────────────────────────────────
function formatText(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<b>$1</b>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/^#{1,3}\s(.+)/gm, "<b>$1</b>")
    .replace(/^•\s(.+)/gm, "<span class='bullet'>• $1</span>")
    .replace(/^-\s(.+)/gm, "<span class='bullet'>• $1</span>")
    .replace(/\n/g, "<br/>");
}

// ── Loading state ─────────────────────────────────────────────────────────────
function setLoading(on) {
  sendBtn.disabled = on;
  if (on) {
    const typing = document.createElement("div");
    typing.className = "msg agent";
    typing.id = "typing";
    typing.innerHTML = `
      <div class="bubble">
        <div class="msg-title">VAYORA</div>
        <div class="typing">
          <div class="dot-pulse"></div>
          <div class="dot-pulse"></div>
          <div class="dot-pulse"></div>
        </div>
      </div>`;
    chat.appendChild(typing);
    chat.scrollTop = chat.scrollHeight;
  } else {
    const t = document.getElementById("typing");
    if (t) t.remove();
  }
}

// ── AQI strip ─────────────────────────────────────────────────────────────────
const AQI_COLORS = {
  green: "#22c55e", yellow: "#eab308", orange: "#f97316",
  red: "#ef4444", purple: "#a855f7", maroon: "#7f1d1d", gray: "#6b7280"
};

function showAqiStrip(city, aqi, category, color) {
  aqiStrip.style.display = "flex";
  document.getElementById("aqiCity").textContent = city;
  document.getElementById("aqiCat").textContent = category || "";
  const pill = document.getElementById("aqiPill");
  pill.textContent = `AQI ${aqi}`;
  pill.style.background = AQI_COLORS[color] || "#6b7280";
  pill.style.color = (color === "yellow") ? "#1a1a00" : "#fff";
}

// ── Voice Input (Web Speech API) ──────────────────────────────────────────────
function toggleVoice() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    alert("Voice input not supported in this browser. Use Chrome or Edge.");
    return;
  }

  if (isListening) {
    stopListening();
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();

  // ── Set language based on selector ──────────────────────────────────────────
  const lang = langSelect.value;
  recognition.lang = lang === "hi" ? "hi-IN" : lang === "hinglish" ? "hi-IN" : "en-IN";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    micBtn.textContent = "🔴";
    micBtn.classList.add("listening");
    input.placeholder = "Listening...";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
    autoResize(input);
    stopListening();
    sendMessage();
  };

  recognition.onerror = (e) => {
    console.error("Speech error:", e.error);
    stopListening();
    if (e.error === "not-allowed") {
      alert("Microphone access denied. Allow microphone in browser settings.");
    }
  };

  recognition.onend = () => stopListening();

  recognition.start();
}

function stopListening() {
  isListening = false;
  micBtn.textContent = "🎤";
  micBtn.classList.remove("listening");
  input.placeholder = "Ask about AQI, health, environment, remedies...";
  if (recognition) {
    try { recognition.stop(); } catch (_) {}
  }
}

// ── Voice Output (Web Speech Synthesis) ──────────────────────────────────────
function speakText(text) {
  if (!("speechSynthesis" in window)) return;

  // Strip markdown symbols for cleaner speech
  const clean = text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/^#{1,3}\s/gm, "")
    .replace(/^[•\-]\s/gm, "")
    .substring(0, 500);  // limit length

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(clean);
  const lang = langSelect.value;
  utterance.lang = lang === "hi" ? "hi-IN" : "en-IN";
  utterance.rate = 0.92;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

// ── Drawer ────────────────────────────────────────────────────────────────────
document.getElementById("drawerBtn").addEventListener("click", () => {
  document.getElementById("drawer").classList.add("open");
  document.getElementById("overlay").classList.add("show");
});

function closeDrawer() {
  document.getElementById("drawer").classList.remove("open");
  document.getElementById("overlay").classList.remove("show");
}

// ── Clear chat ────────────────────────────────────────────────────────────────
function clearChat() {
  chat.innerHTML = "";
  aqiStrip.style.display = "none";
  closeDrawer();
  addMessage("agent", "Chat cleared. Ask me anything about air quality or environment.");
}
