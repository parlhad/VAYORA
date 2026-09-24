// ── VAYORA app.js — FINAL + SESSION MEMORY ───────────────────────────────────
const API = "";  // same origin — FastAPI serves this file

// ── AUTHENTICATION ──────────────────────────────────────────────────────────
// JWT is kept in sessionStorage for this browser tab/session.
// Existing VAYORA session memory remains separate.

const AUTH_TOKEN_KEY = "vayora_access_token";
const AUTH_USER_KEY = "vayora_user";

function getAuthToken() {
  return sessionStorage.getItem(AUTH_TOKEN_KEY);
}

function getAuthUser() {
  const storedUser = sessionStorage.getItem(AUTH_USER_KEY);

  if (!storedUser) {
    return null;
  }

  try {
    return JSON.parse(storedUser);
  } catch (_) {
    return null;
  }
}

function setAuthSession(accessToken, user) {
  sessionStorage.setItem(
    AUTH_TOKEN_KEY,
    accessToken
  );

  sessionStorage.setItem(
    AUTH_USER_KEY,
    JSON.stringify(user)
  );

  updateAuthUI();
  loadConversations();
}

function clearAuthSession() {
  sessionStorage.removeItem(
    AUTH_TOKEN_KEY
  );

  sessionStorage.removeItem(
    AUTH_USER_KEY
  );

  updateAuthUI();
}

function updateAuthUI() {
  const token = getAuthToken();
  const user = getAuthUser();

  const status =
    document.getElementById("authStatus");

  const loginBtn =
    document.getElementById("loginBtn");

  const logoutBtn =
    document.getElementById("logoutBtn");

  if (!status || !loginBtn || !logoutBtn) {
    return;
  }

  if (token && user) {

    status.textContent =
      `Logged in as ${user.name || user.email}`;

    loginBtn.style.display =
      "none";

    logoutBtn.style.display =
      "block";

  } else {

    status.textContent =
      "Not logged in";

    loginBtn.style.display =
      "block";

    logoutBtn.style.display =
      "none";
  }
}

// ── CONVERSATION HISTORY ───────────────────────────────────────────────────

async function loadConversations() {
  const list =
    document.getElementById("conversationList");

  if (!list) {
    return;
  }

  const token = getAuthToken();

  if (!token) {
    list.innerHTML = `
      <div class="conversation-empty">
        Login to see your conversations
      </div>
    `;
    return;
  }

  list.innerHTML = `
    <div class="conversation-empty">
      Loading conversations...
    </div>
  `;

  try {

    const res = await fetch(
      `${API}/conversations`,
      {
        method: "GET",

        headers: {
          "Authorization":
            `Bearer ${token}`
        }
      }
    );
        // AUTH CHECK — TOKEN EXPIRED / INVALID
    if (res.status === 401) {
      clearAuthSession();
      return;
    }

    const data =
      await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Could not load conversations."
      );
    }

    const conversations =
      data.conversations || [];

    if (conversations.length === 0) {

      list.innerHTML = `
        <div class="conversation-empty">
          No conversations yet
        </div>
      `;

      return;
    }

    list.innerHTML = "";

    conversations.forEach(
  (conversation) => {

    // Conversation row
    const row =
      document.createElement("div");

    row.className =
      "conversation-row";


    // Conversation title button
    const button =
      document.createElement("button");

    button.type = "button";

    button.className =
      "conversation-item";

    button.textContent =
      conversation.title ||
      "New Chat";

    button.title =
      conversation.title ||
      "New Chat";

    button.onclick = () => {
      loadConversation(
        conversation.session_id
      );
    };


    // Rename button
    const renameButton =
      document.createElement("button");

    renameButton.type = "button";

    renameButton.className =
      "conversation-action rename";

    renameButton.textContent =
      "✏️";

    renameButton.title =
      "Rename conversation";

    renameButton.onclick = (event) => {

      event.stopPropagation();

      renameConversation(
        conversation.session_id,
        conversation.title ||
        "New Chat"
      );

    };


    // Delete button
    const deleteButton =
      document.createElement("button");

    deleteButton.type = "button";

    deleteButton.className =
      "conversation-action delete";

    deleteButton.textContent =
      "🗑";

    deleteButton.title =
      "Delete conversation";

    deleteButton.onclick = (event) => {

      event.stopPropagation();

      deleteConversation(
        conversation.session_id
      );

    };


    row.appendChild(button);
    row.appendChild(renameButton);
    row.appendChild(deleteButton);

    list.appendChild(row);
  }
);

  } catch (err) {

    console.error(
      "VAYORA conversation history error:",
      err
    );

    list.innerHTML = `
      <div class="conversation-empty">
        ⚠️ Could not load conversations
      </div>
    `;
  }
}

// ── LOAD ONE CONVERSATION ───────────────────────────────────────────────────

async function loadConversation(selectedSessionId) {

  const token = getAuthToken();

  if (!token) {
    return;
  }

  if (!selectedSessionId) {
    return;
  }

  try {

    const res = await fetch(
      `${API}/conversations/${encodeURIComponent(selectedSessionId)}`,
      {
        method: "GET",

        headers: {
          "Authorization":
            `Bearer ${token}`
        }
      }
    );
        // AUTH CHECK — TOKEN EXPIRED / INVALID
    if (res.status === 401) {
      clearAuthSession();

      return;
    }

    const data =
      await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Could not load conversation."
      );
    }

    // ─────────────────────────────────────────────
    // SWITCH CURRENT SESSION
    // ─────────────────────────────────────────────

    sessionId =
      selectedSessionId;

    sessionStorage.setItem(
      SESSION_STORAGE_KEY,
      sessionId
    );

    // ─────────────────────────────────────────────
    // CLEAR CURRENT CHAT DISPLAY ONLY
    // Do NOT create a new session.
    // ─────────────────────────────────────────────

    chat.innerHTML = "";

    aqiStrip.style.display =
      "none";

    lastMapLocation =
      null;

    if (mapBtn) {
      mapBtn.disabled = true;
    }

    // ─────────────────────────────────────────────
    // RESTORE MESSAGES
    // ─────────────────────────────────────────────

    const messages =
      data.messages || [];

    messages.forEach(
      (message) => {

        if (
          message.role === "user" ||
          message.role === "assistant" ||
          message.role === "agent"
        ) {

          addMessage(
            message.role === "assistant"
              ? "agent"
              : message.role,
            message.content || ""
          );

        }

      }
    );

    closeDrawer();

  } catch (err) {

    console.error(
      "VAYORA load conversation error:",
      err
    );

    chat.innerHTML = "";

    addMessage(
      "agent",
      `⚠️ Could not load this conversation: ${err.message || err}`
    );

  }

}

// ── RENAME CONVERSATION ─────────────────────────────────────────────────────

async function renameConversation(
  selectedSessionId,
  currentTitle
) {

  const token = getAuthToken();

  if (!token) {
    return;
  }

  const newTitle =
    window.prompt(
      "Rename conversation:",
      currentTitle
    );

  if (newTitle === null) {
    return;
  }

  const title =
    newTitle.trim();

  if (!title) {
    alert("Conversation title cannot be empty.");
    return;
  }

  try {

    const res = await fetch(
      `${API}/conversations/${encodeURIComponent(selectedSessionId)}`,
      {
        method: "PATCH",

        headers: {
          "Content-Type":
            "application/json",

          "Authorization":
            `Bearer ${token}`
        },

        body: JSON.stringify({
          title: title
        })
      }
    );

        // AUTH CHECK — TOKEN EXPIRED / INVALID
    if (res.status === 401) {
      clearAuthSession();
      return;
    }

    const data =
      await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Could not rename conversation."
      );
    }

    await loadConversations();

  } catch (err) {

    console.error(
      "VAYORA rename conversation error:",
      err
    );

    alert(
      `Could not rename conversation: ${
        err.message || err
      }`
    );
  }
}

// ── DELETE CONVERSATION ─────────────────────────────────────────────────────

async function deleteConversation(
  selectedSessionId
) {

  const token = getAuthToken();

  if (!token) {
    return;
  }

  const confirmed =
    window.confirm(
      "Delete this conversation?\n\nThis cannot be undone."
    );

  if (!confirmed) {
    return;
  }

  try {

    const res = await fetch(
      `${API}/conversations/${encodeURIComponent(selectedSessionId)}`,
      {
        method: "DELETE",

        headers: {
          "Authorization":
            `Bearer ${token}`
        }
      }
    );

        // AUTH CHECK — TOKEN EXPIRED / INVALID
    if (res.status === 401) {
      clearAuthSession();
      return;
    }

    const data =
      await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Could not delete conversation."
      );
    }


    // If the deleted conversation
    // is currently open, start a new session.
    if (
      sessionId === selectedSessionId
    ) {

      clearChat();

    }


    await loadConversations();

  } catch (err) {

    console.error(
      "VAYORA delete conversation error:",
      err
    );

    alert(
      `Could not delete conversation: ${
        err.message || err
      }`
    );
  }
}

function openAuthModal() {
  const overlay =
    document.getElementById("authOverlay");

  if (overlay) {
    overlay.classList.add("show");
  }

  showLoginForm();
}

function closeAuthModal() {
  const overlay =
    document.getElementById("authOverlay");

  if (overlay) {
    overlay.classList.remove("show");
  }
}

function showLoginForm() {
  document.getElementById(
    "loginForm"
  ).style.display = "flex";

  document.getElementById(
    "registerForm"
  ).style.display = "none";

  document.getElementById(
    "loginTab"
  ).classList.add("active");

  document.getElementById(
    "registerTab"
  ).classList.remove("active");

  document.getElementById(
    "authMessage"
  ).textContent = "";
}

function showRegisterForm() {
  document.getElementById(
    "loginForm"
  ).style.display = "none";

  document.getElementById(
    "registerForm"
  ).style.display = "flex";

  document.getElementById(
    "loginTab"
  ).classList.remove("active");

  document.getElementById(
    "registerTab"
  ).classList.add("active");

  document.getElementById(
    "authMessage"
  ).textContent = "";
}

async function loginUser(event) {
  event.preventDefault();

  const email =
    document.getElementById(
      "loginEmail"
    ).value.trim();

  const password =
    document.getElementById(
      "loginPassword"
    ).value;

  const message =
    document.getElementById(
      "authMessage"
    );

  message.textContent =
    "Logging in...";

  try {

    const res = await fetch(
      `${API}/auth/login`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          email,
          password
        })
      }
    );

    const data =
      await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Login failed."
      );
    }

    setAuthSession(
      data.access_token,
      data.user
    );

    message.textContent =
      "Login successful.";

    setTimeout(() => {
      closeAuthModal();
      closeDrawer();
    }, 500);

  } catch (err) {

    console.error(
      "VAYORA login error:",
      err
    );

    message.textContent =
      `⚠️ ${err.message || err}`;
  }
}

async function registerUser(event) {
  event.preventDefault();

  const name =
    document.getElementById(
      "registerName"
    ).value.trim();

  const email =
    document.getElementById(
      "registerEmail"
    ).value.trim();

  const password =
    document.getElementById(
      "registerPassword"
    ).value;

  const message =
    document.getElementById(
      "authMessage"
    );

  message.textContent =
    "Creating account...";

  try {

    const res = await fetch(
      `${API}/auth/register`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          name,
          email,
          password
        })
      }
    );

    const data =
      await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Registration failed."
      );
    }

    message.textContent =
      "Account created. You can now login.";

    document.getElementById(
      "registerForm"
    ).reset();

    setTimeout(() => {
      showLoginForm();

      document.getElementById(
        "loginEmail"
      ).value = email;
    }, 800);

  } catch (err) {

    console.error(
      "VAYORA registration error:",
      err
    );

    message.textContent =
      `⚠️ ${err.message || err}`;
  }
}

function logoutUser() {
  clearAuthSession();

  closeDrawer();

  clearChat();
}

// ── State ─────────────────────────────────────────────────────────────────────
let isListening   = false;
let recognition   = null;
let ttsEnabled    = true;
let currentSpeech = null;
let speakNextResponse = false;

const voiceSpeaking =
  document.getElementById("voiceSpeaking");

// ── SESSION MEMORY ────────────────────────────────────────────────────────────
// One conversation = one session.
// sessionStorage keeps the session during this browser tab/session.
// It also survives page refreshes.
//
// Clear Chat creates a new session so the next conversation starts fresh.

const SESSION_STORAGE_KEY = "vayora_session_id";

function getSessionId() {
  let sessionId = sessionStorage.getItem(SESSION_STORAGE_KEY);

  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }

  return sessionId;
}

function resetSessionId() {
  const newSessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
  return newSessionId;
}

// Create/load the session immediately.
let sessionId = getSessionId();


// ── DOM refs ──────────────────────────────────────────────────────────────────
const chat      = document.getElementById("chat");
const input     = document.getElementById("msgInput");
const sendBtn   = document.getElementById("sendBtn");
const micBtn    = document.getElementById("micBtn");
const aqiStrip  = document.getElementById("aqiStrip");
const modeSelect = document.getElementById("modeSelect");
const langSelect  = document.getElementById("langSelect");
const mapBtn = document.getElementById("mapBtn");
const locationBtn = document.getElementById("locationBtn");
const locationSearch = document.getElementById("locationSearch");
const locationInput = document.getElementById("locationInput");
const locationSearchBtn = document.getElementById("locationSearchBtn");

let lastMapLocation = null;

// ── Welcome ───────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
  loadConversations();
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
  
  const shouldSpeak = speakNextResponse;
  speakNextResponse = false;

  input.value = "";
  autoResize(input);
  addMessage("user", text);
  setLoading(true);

  const mode     = modeSelect.value;
  const language = langSelect.value;

  // Make sure a valid session always exists.
  sessionId = getSessionId();

  try {
    const res = await fetch(`${API}/vayora/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",

        "Authorization":
          `Bearer ${getAuthToken()}`

      },
      body: JSON.stringify({
        message: text,
        mode,
        language,

        // ─────────────────────────────────────────────
        // SESSION MEMORY
        // ─────────────────────────────────────────────
        session_id: sessionId,

        // ─────────────────────────────────────────────
        // SELECTED LOCATION
        // ─────────────────────────────────────────────
        location: window.vayoraSelectedLocation || null
      })
    });

        // AUTH CHECK — TOKEN EXPIRED / INVALID
    if (res.status === 401) {
      clearAuthSession();
      return;
    }

    const data = await res.json();

    // ─────────────────────────────────────────────
    // MAP LOCATION — use verified backend coordinates
    // No location is guessed in the frontend.
    // ─────────────────────────────────────────────

    const coordinates =
      data?.live_data?.coordinates;

    const weatherData =
      data?.live_data?.weather || null;

    const forecastData =
      data?.live_data?.forecast || null;

    if (
      data?.city &&
      coordinates &&
      Number.isFinite(Number(coordinates.latitude)) &&
      Number.isFinite(Number(coordinates.longitude))
    ) {
      lastMapLocation = {
        city: data.city,
        latitude: Number(coordinates.latitude),
        longitude: Number(coordinates.longitude),
        aqi: data.aqi,
        category: data.category,
        intent: data.intent || "",
        weather: weatherData,
        forecast: forecastData
      };

      if (mapBtn) {
        mapBtn.disabled = false;
      }
    }

    // If backend ever creates/fixes a session ID,
    // keep using the returned one.
    if (data && data.session_id) {
      sessionId = data.session_id;

      sessionStorage.setItem(
        SESSION_STORAGE_KEY,
        sessionId
      );
    }

    const reply =
      data.reply ||
      "Sorry, I couldn't process that.";

    // Update AQI strip if city data returned
    if (data.aqi !== undefined && data.city) {
      showAqiStrip(
        data.city,
        data.aqi,
        data.category,
        data.color
      );
    }

    addMessage("agent", reply);

    // TTS — speak only when the question came from microphone
    if (ttsEnabled && shouldSpeak) {
      speakText(reply);
    }

  } catch (err) {
    console.error(
      "VAYORA request error:",
      err
    );

    addMessage(
      "agent",
      `⚠️ VAYORA response error: ${err.message || err}`
    );
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
  el.style.height =
    Math.min(el.scrollHeight, 130) + "px";
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
  meta.textContent = new Date().toLocaleTimeString(
    [],
    {
      hour: "2-digit",
      minute: "2-digit"
    }
  );

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
    .replace(
      /^•\s(.+)/gm,
      "<span class='bullet'>• $1</span>"
    )
    .replace(
      /^-\s(.+)/gm,
      "<span class='bullet'>• $1</span>"
    )
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

    if (t) {
      t.remove();
    }
  }
}


// ── AQI strip ─────────────────────────────────────────────────────────────────
const AQI_COLORS = {
  green: "#22c55e",
  yellow: "#eab308",
  orange: "#f97316",
  red: "#ef4444",
  purple: "#a855f7",
  maroon: "#7f1d1d",
  gray: "#6b7280"
};

function showAqiStrip(
  city,
  aqi,
  category,
  color
) {

  aqiStrip.style.display = "flex";

  document.getElementById(
    "aqiCity"
  ).textContent = city;

  document.getElementById(
    "aqiCat"
  ).textContent = category || "";

  const pill =
    document.getElementById(
      "aqiPill"
    );

  pill.textContent =
    `AQI ${aqi}`;

  pill.style.background =
    AQI_COLORS[color] ||
    "#6b7280";

  pill.style.color =
    color === "yellow"
      ? "#1a1a00"
      : "#fff";
}


// ── Voice Input (Web Speech API) ──────────────────────────────────────────────
function toggleVoice() {

  if (
    !("webkitSpeechRecognition" in window) &&
    !("SpeechRecognition" in window)
  ) {

    alert(
      "Voice input not supported in this browser. Use Chrome or Edge."
    );

    return;
  }

  if (isListening) {

    stopListening();

    return;
  }

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  recognition =
    new SpeechRecognition();

  // ── Set language based on selector ──────────────────────────────────────────
  const lang =
    langSelect.value;

  recognition.lang =
    lang === "hi"
      ? "hi-IN"
      : lang === "hinglish"
        ? "hi-IN"
        : "en-IN";

  recognition.interimResults =
    false;

  recognition.maxAlternatives =
    1;

  recognition.onstart = () => {

    isListening = true;

    micBtn.textContent = "🔴";

    micBtn.classList.add(
      "listening"
    );

    input.placeholder =
      "Listening...";

  };

  recognition.onresult = (
    event
  ) => {

    const transcript =
      event.results[0][0].transcript;

    input.value =
      transcript;

    autoResize(input);

    stopListening();

    speakNextResponse = true;

    sendMessage();

  };

  recognition.onerror = (
    e
  ) => {

    console.error(
      "Speech error:",
      e.error
    );

    stopListening();

    if (
      e.error === "not-allowed"
    ) {

      alert(
        "Microphone access denied. Allow microphone in browser settings."
      );

    }

  };

  recognition.onend = () => {

    if (isListening) {
      stopListening();
    }

  };

  recognition.start();

}


// ── Stop listening ────────────────────────────────────────────────────────────
function stopListening() {

  if (recognition) {

    try {
      recognition.stop();
    } catch (_) {}

  }

  isListening = false;

  micBtn.textContent = "🎤";

  micBtn.classList.remove(
    "listening"
  );

  input.placeholder =
    "Ask about AQI, health, environment, remedies...";

}


// ── Text-to-Speech ────────────────────────────────────────────────────────────
function speakText(text) {

  if (
    !ttsEnabled ||
    !("speechSynthesis" in window)
  ) {

    return;
  }

  if (
    currentSpeech
  ) {

    speechSynthesis.cancel();

  }

  const cleanText =
    text
      .replace(
        /\*\*/g,
        ""
      )
      .replace(
        /\*/g,
        ""
      )
      .replace(
        /[🌫️🌤💊🌿⚠️]/gu,
        ""
      );

  currentSpeech =
    new SpeechSynthesisUtterance(
      cleanText
    );

  currentSpeech.lang =
    langSelect.value === "hi"
      ? "hi-IN"
      : "en-IN";

  currentSpeech.rate =
    1;

  currentSpeech.pitch =
    1;
      if (voiceSpeaking) {
    voiceSpeaking.classList.add("active");
    voiceSpeaking.setAttribute(
      "aria-hidden",
      "false"
    );
  }

  currentSpeech.onend = () => {
    if (voiceSpeaking) {
      voiceSpeaking.classList.remove("active");
      voiceSpeaking.setAttribute(
        "aria-hidden",
        "true"
      );
    }

    currentSpeech = null;
  };

  currentSpeech.onerror = () => {
    if (voiceSpeaking) {
      voiceSpeaking.classList.remove("active");
      voiceSpeaking.setAttribute(
        "aria-hidden",
        "true"
      );
    }

    currentSpeech = null;
  };

  speechSynthesis.speak(
    currentSpeech
  );

}


// ── Drawer ────────────────────────────────────────────────────────────────────
const drawerBtn =
  document.getElementById(
    "drawerBtn"
  );

const drawer =
  document.getElementById(
    "drawer"
  );

const overlay =
  document.getElementById(
    "overlay"
  );

function openDrawer() {

  drawer.classList.add(
    "open"
  );

  document.body.classList.add("drawer-open");

  overlay.classList.add(
    "show"
  );

}

function closeDrawer() {

  drawer.classList.remove(
    "open"
  );

  document.body.classList.remove("drawer-open");

  overlay.classList.remove(
    "show"
  );

}

if (drawerBtn) {

  drawerBtn.addEventListener(
    "click",
    () => {

      if (
        drawer.classList.contains(
          "open"
        )
      ) {

        closeDrawer();

      } else {

        openDrawer();

      }

    }
  );

}


// ── Clear chat ────────────────────────────────────────────────────────────────
function clearChat() {

  chat.innerHTML = "";

  aqiStrip.style.display =
    "none";

  lastMapLocation =
    null;

  if (mapBtn) {
    mapBtn.disabled = true;
  }

  // Create a completely new conversation.
  sessionId =
    resetSessionId();

  addMessage(
    "agent",
    `**New session started.**\n\n` +
    `I'm ready — ask me about AQI, weather, health, or the environment.`
  );

  closeDrawer();

}


// ── MAP VISUALIZATION FOUNDATION ─────────────────────────────────────────────
// VAYORA MAP
// Keeps the existing project intact.
//
// Map layers:
//   1. OpenStreetMap
//   2. AQI visualization
//   3. Current OpenWeather visualization
//   4. RainViewer radar
//   5. Esri satellite imagery
//
// IMPORTANT:
// RainViewer currently provides past radar frames.
// We use the latest available past frame.
// No fake nowcast or satellite data is created.

let vayoraMap = null;

let vayoraMapMarker = null;

let vayoraAqiCircle = null;

let vayoraWeatherMarker = null;

let vayoraRainLayer = null;

let vayoraRainEnabled = false;

let vayoraSatelliteEnabled = false;

let vayoraOsmLayer = null;

let vayoraRainLoading = false;

let vayoraSatelliteLayer = null;


// ── ESRI ATTRIBUTION ─────────────────────────────────────────────────────────

const VAYORA_ESRI_ATTRIBUTION =
  "Sources: Esri, DigitalGlobe, GeoEye, i-cubed, USDA FSA, USGS, AEX, Getmapping, Aerogrid, IGN, IGP, swisstopo, and the GIS User Community";


// ── REMOVE LAYER SAFELY ──────────────────────────────────────────────────────

function vayoraRemoveLayer(
  layer
) {

  if (
    layer &&
    vayoraMap &&
    vayoraMap.hasLayer(
      layer
    )
  ) {

    vayoraMap.removeLayer(
      layer
    );

  }

}


// ── CLEAR RAIN ───────────────────────────────────────────────────────────────

function vayoraClearRain() {

  vayoraRemoveLayer(
    vayoraRainLayer
  );

  vayoraRainLayer =
    null;

  vayoraRainEnabled =
    false;

}


// ── CLEAR AQI VISUAL ─────────────────────────────────────────────────────────

function vayoraClearAqiVisual() {

  vayoraRemoveLayer(
    vayoraAqiCircle
  );

  vayoraAqiCircle =
    null;

}


// ── CLEAR WEATHER VISUAL ─────────────────────────────────────────────────────

function vayoraClearWeatherVisual() {

  vayoraRemoveLayer(
    vayoraWeatherMarker
  );

  vayoraWeatherMarker =
    null;

}


// ── BASE MAP LAYERS ──────────────────────────────────────────────────────────

function vayoraSetBaseLayer(
  useSatellite
) {

  if (!vayoraMap) {
    return;
  }

  // ----------------------------------------------------------
  // OPENSTREETMAP
  // ----------------------------------------------------------

  if (!vayoraOsmLayer) {

    vayoraOsmLayer =
      L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          maxZoom: 19,

          attribution:
            "&copy; OpenStreetMap contributors",

          zIndex: 1
        }
      );

  }

  // ----------------------------------------------------------
  // ESRI SATELLITE
  // ----------------------------------------------------------

  if (!vayoraSatelliteLayer) {

    vayoraSatelliteLayer =
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,

          attribution:
            VAYORA_ESRI_ATTRIBUTION,

          zIndex: 1
        }
      );

  }

  // ----------------------------------------------------------
  // SHOW SATELLITE
  // ----------------------------------------------------------

  if (useSatellite) {

    vayoraRemoveLayer(
      vayoraOsmLayer
    );

    vayoraSatelliteLayer.addTo(
      vayoraMap
    );

    vayoraSatelliteEnabled =
      true;

  }

  // ----------------------------------------------------------
  // SHOW NORMAL MAP
  // ----------------------------------------------------------

  else {

    vayoraRemoveLayer(
      vayoraSatelliteLayer
    );

    vayoraOsmLayer.addTo(
      vayoraMap
    );

    vayoraSatelliteEnabled =
      false;

  }

}


// ── AQI COLOR ────────────────────────────────────────────────────────────────

function vayoraAqiColor(
  aqi
) {

  const n =
    Number(aqi);

  if (!Number.isFinite(n)) {

    return "#38bdf8";

  }

  if (n <= 50) {

    return "#22c55e";

  }

  if (n <= 100) {

    return "#eab308";

  }

  if (n <= 150) {

    return "#f97316";

  }

  if (n <= 200) {

    return "#ef4444";

  }

  if (n <= 300) {

    return "#a855f7";

  }

  return "#7f1d1d";

}


// ── MAP CONTROL BAR ──────────────────────────────────────────────────────────

function vayoraEnsureMapControls() {

  const panelTools =
    document.getElementById(
      "mapPanelTools"
    );

  const legacyTools =
    document.querySelector(
      ".weather-map-controls"
    );

  if (!panelTools) {

    console.warn(
      "VAYORA: mapPanelTools not found."
    );

    return;

  }

  // ----------------------------------------------------------
  // REMOVE OLD / DUPLICATE CONTROLS
  // ----------------------------------------------------------

  panelTools.innerHTML =
    "";

  if (legacyTools) {

    legacyTools.innerHTML =
      "";

  }

  // ----------------------------------------------------------
  // ONE SINGLE CONTROL BAR
  // ----------------------------------------------------------

  const controls = [

    [
      "map",
      "🗺 Map",
      vayoraShowMap
    ],

    [
      "aqi",
      "⚗ AQI",
      vayoraShowAqi
    ],

    [
      "weather",
      "☁ Weather",
      vayoraShowWeather
    ],

    [
      "rain",
      "🌧 Rain",
      toggleVayoraRainLayer
    ],

    [
      "satellite",
      "🛰 Satellite",
      vayoraToggleSatellite
    ]

  ];

  controls.forEach(
    (
      [
        id,
        label,
        handler
      ]
    ) => {

      const button =
        document.createElement(
          "button"
        );

      button.type =
        "button";

      button.className =
        "weather-map-btn";

      button.dataset.mapMode =
        id;

      button.textContent =
        label;

      button.addEventListener(
        "click",
        handler
      );

      panelTools.appendChild(
        button
      );

    }
  );

}


// ── ACTIVE CONTROL ───────────────────────────────────────────────────────────

function vayoraSetActiveControl(
  mode
) {

  document
    .querySelectorAll(
      "[data-map-mode]"
    )
    .forEach(
      (
        button
      ) => {

        button.classList.toggle(
          "active",
          button.dataset.mapMode === mode
        );

      }
    );

}


// ── NORMAL MAP ───────────────────────────────────────────────────────────────

function vayoraShowMap() {

  if (!vayoraMap) {

    return;

  }

  vayoraClearRain();

  vayoraClearAqiVisual();

  vayoraClearWeatherVisual();

  vayoraSetBaseLayer(
    false
  );

  vayoraSetActiveControl(
    "map"
  );

  vayoraMap.invalidateSize(
    true
  );

}


// ── AQI MAP ──────────────────────────────────────────────────────────────────

function vayoraShowAqi() {

  if (
    !vayoraMap ||
    !lastMapLocation
  ) {

    return;

  }

  vayoraClearRain();

  vayoraClearWeatherVisual();

  vayoraSetBaseLayer(
    false
  );

  vayoraClearAqiVisual();

  const lat =
    Number(
      lastMapLocation.latitude
    );

  const lon =
    Number(
      lastMapLocation.longitude
    );

  const aqi =
    Number(
      lastMapLocation.aqi
    );

  if (
    !Number.isFinite(lat) ||
    !Number.isFinite(lon)
  ) {

    console.warn(
      "VAYORA: Invalid AQI coordinates."
    );

    return;

  }

  if (
    Number.isFinite(aqi)
  ) {

    const color =
      vayoraAqiColor(
        aqi
      );

    vayoraAqiCircle =
      L.circle(
        [
          lat,
          lon
        ],
        {
          radius: 4500,

          color: color,

          fillColor: color,

          fillOpacity: 0.18,

          weight: 2
        }
      ).addTo(
        vayoraMap
      );

    vayoraAqiCircle.bindPopup(
      `<b>${lastMapLocation.city}</b>` +
      `<br>AQI ${aqi}` +
      `<br>${lastMapLocation.category || ""}`
    ).openPopup();

  }

  vayoraSetActiveControl(
    "aqi"
  );

  vayoraMap.invalidateSize(
    true
  );

}


// ── WEATHER MAP ──────────────────────────────────────────────────────────────

function vayoraShowWeather() {

  if (
    !vayoraMap ||
    !lastMapLocation
  ) {

    return;

  }

  vayoraClearRain();

  vayoraClearAqiVisual();

  vayoraSetBaseLayer(
    false
  );

  vayoraClearWeatherVisual();

  const weather =
    lastMapLocation.weather;

  const forecast =
    lastMapLocation.forecast;

  const lat =
    Number(
      lastMapLocation.latitude
    );

  const lon =
    Number(
      lastMapLocation.longitude
    );

  if (
    !Number.isFinite(lat) ||
    !Number.isFinite(lon)
  ) {

    console.warn(
      "VAYORA: Invalid weather coordinates."
    );

    return;

  }

  // ----------------------------------------------------------
  // WEATHER POPUP
  // ----------------------------------------------------------

  let html =
    `<b>${lastMapLocation.city} — Current Weather</b><br>`;

  if (
    weather &&
    typeof weather === "object"
  ) {

    if (
      weather.temperature != null
    ) {

      html +=
        `🌡 ${weather.temperature}°C<br>`;

    }

    if (
      weather.feels_like != null
    ) {

      html +=
        `Feels like ${weather.feels_like}°C<br>`;

    }

    if (
      weather.humidity != null
    ) {

      html +=
        `💧 Humidity ${weather.humidity}%<br>`;

    }

    if (
      weather.wind_speed != null
    ) {

      html +=
        `🌬 Wind ${weather.wind_speed} m/s<br>`;

    }

    if (
      weather.wind_direction != null
    ) {

      html +=
        `🧭 Direction ${weather.wind_direction}°<br>`;

    }

    if (
      weather.cloudiness != null
    ) {

      html +=
        `☁ Clouds ${weather.cloudiness}%<br>`;

    }

    if (
      weather.rain_1h != null
    ) {

      html +=
        `🌧 Rain (1h) ${weather.rain_1h} mm<br>`;

    }

    if (
      weather.visibility != null
    ) {

      html +=
        `👁 Visibility ${weather.visibility} m<br>`;

    }

    if (
      weather.description
    ) {

      html +=
        `🌤 ${weather.description}<br>`;

    }

    html +=
      `<small>Source: ${
        weather.source ||
        "OpenWeather"
      }</small>`;

  }

  else if (
    forecast &&
    Array.isArray(
      forecast.forecast
    ) &&
    forecast.forecast.length
  ) {

    const first =
      forecast.forecast[0];

    html +=
      `🌡 ${first.temperature ?? "—"}°C<br>` +
      `🌤 ${first.description ?? "Weather forecast"}<br>` +
      `<small>Source: OpenWeather forecast</small>`;

  }

  else {

    html +=
      `Current weather data is not attached to this map session.<br>`;

    html +=
      `<small>Ask VAYORA: "weather in ${
        lastMapLocation.city
      }" and reopen the map.</small>`;

  }

  // ----------------------------------------------------------
  // WEATHER MARKER
  // ----------------------------------------------------------

  vayoraWeatherMarker =
    L.marker(
      [
        lat,
        lon
      ]
    ).addTo(
      vayoraMap
    );

  vayoraWeatherMarker
    .bindPopup(
      html
    )
    .openPopup();

  vayoraSetActiveControl(
    "weather"
  );

  vayoraMap.invalidateSize(
    true
  );

}


// ── RAINVIEWER RADAR ─────────────────────────────────────────────────────────

async function toggleVayoraRainLayer() {

  if (!vayoraMap) {
    return;
  }

  // Prevent multiple fast clicks
  if (vayoraRainLoading) {
    console.log("VAYORA Rain: already loading, ignoring extra click.");
    return;
  }

  // If already ON → turn OFF
  if (vayoraRainEnabled) {

    vayoraClearRain();

    vayoraSetActiveControl("map");

    console.log("VAYORA Rain: OFF");

    return;
  }

  // Start loading lock
  vayoraRainLoading = true;

  try {

    // Clear previous visual layers
    vayoraClearRain();
    vayoraClearAqiVisual();
    vayoraClearWeatherVisual();

    vayoraSetBaseLayer(false);

    // Show loading message
    const rainStatus =
      document.getElementById("vayoraRainStatus");

    if (rainStatus) {
      rainStatus.textContent =
        "⏳ Rain radar loading...";
      rainStatus.style.display = "block";
    }

    // Get RainViewer data
    const response =
      await fetch(
        "https://api.rainviewer.com/public/weather-maps.json",
        {
          cache: "no-store"
        }
      );

    if (!response.ok) {
      throw new Error(
        `RainViewer API HTTP ${response.status}`
      );
    }

    const data =
      await response.json();

    console.log(
      "RainViewer data:",
      data
    );

    // Get past radar frames
    const frames =
      Array.isArray(data?.radar?.past)
        ? data.radar.past
        : [];

    if (!frames.length || !data.host) {
      throw new Error(
        "RainViewer returned no past radar frames"
      );
    }

    // Latest available frame
    const latestFrame =
      frames[frames.length - 1];

    if (!latestFrame || !latestFrame.path) {
      throw new Error(
        "RainViewer latest frame is invalid"
      );
    }

    // Build tile URL
    const tileUrl =
      `${data.host}` +
      `${latestFrame.path}` +
      `/256/{z}/{x}/{y}/2/1_1.png`;

    console.log(
      "VAYORA Rain URL:",
      tileUrl
    );

    // Create ONE rain layer
    vayoraRainLayer =
      L.tileLayer(
        tileUrl,
        {
          opacity: 0.72,
          minZoom: 0,
          maxNativeZoom: 7,
          maxZoom: 19,
          zIndex: 500,
          updateWhenIdle: false,
          keepBuffer: 2,
          attribution:
            "Weather data by RainViewer"
        }
      );

    // Tile loaded
    vayoraRainLayer.on(
      "tileload",
      (event) => {

        console.log(
          "VAYORA Rain tile loaded:",
          event.tile.src
        );

        if (rainStatus) {
          rainStatus.textContent =
            "🌧 Rain radar active — latest radar data loaded.";
        }
      }
    );

    // Tile error
    vayoraRainLayer.on(
      "tileerror",
      (event) => {

        console.error(
          "VAYORA Rain tile error:",
          event.tile?.src || event
        );

        if (rainStatus) {
          rainStatus.textContent =
            "⚠ Rain radar loaded, but some tiles could not be displayed.";
        }
      }
    );

    // Add layer
    vayoraRainLayer.addTo(vayoraMap);

    vayoraRainLayer.bringToFront();

    vayoraRainEnabled = true;

    vayoraSetActiveControl("rain");

    if (rainStatus) {
      rainStatus.textContent =
        "🌧 Rain radar active — checking latest radar frame...";
      rainStatus.style.display = "block";
    }

    // Refresh map
    setTimeout(() => {

      if (vayoraMap) {

        vayoraMap.invalidateSize(true);

        if (vayoraRainLayer) {
          vayoraRainLayer.bringToFront();
        }

      }

    }, 250);

    console.log(
      "VAYORA Rain layer added:",
      vayoraRainLayer
    );

  }

  catch (error) {

    vayoraClearRain();

    console.error(
      "VAYORA rain layer error:",
      error
    );

    const rainStatus =
      document.getElementById("vayoraRainStatus");

    if (rainStatus) {
      rainStatus.textContent =
        "❌ Rain radar unavailable right now.";
      rainStatus.style.display = "block";
    }

    alert(
      "Rain radar could not be loaded right now. The normal map is still available."
    );

  }

  finally {

    // Release loading lock
    vayoraRainLoading = false;

  }

}
// ── SATELLITE ────────────────────────────────────────────────────────────────

function vayoraToggleSatellite() {

  if (!vayoraMap) {

    return;

  }

  // Remove visualization layers.

  vayoraClearRain();

  vayoraClearAqiVisual();

  vayoraClearWeatherVisual();

  // Toggle satellite.

  vayoraSetBaseLayer(
    !vayoraSatelliteEnabled
  );

  vayoraSetActiveControl(
    vayoraSatelliteEnabled
      ? "satellite"
      : "map"
  );

  vayoraMap.invalidateSize(
    true
  );

}


// ── OPEN MAP PANEL ───────────────────────────────────────────────────────────

function openMapPanel(

  title =
    "VAYORA Map",

  subtitle =
    "Environmental visualization",

  latitude =
    null,

  longitude =
    null,

  locationName =
    null

) {

  const panel =
    document.getElementById(
      "mapPanel"
    );

  const overlay =
    document.getElementById(
      "mapOverlay"
    );

  const titleEl =
    document.getElementById(
      "mapPanelTitle"
    );

  const subtitleEl =
    document.getElementById(
      "mapPanelSubtitle"
    );

  if (
    !panel ||
    !overlay
  ) {

    console.error(
      "VAYORA: Map panel HTML elements not found."
    );

    return;

  }

  // ----------------------------------------------------------
  // PANEL TEXT
  // ----------------------------------------------------------

  titleEl.textContent =
    title;

  subtitleEl.textContent =
    subtitle;

  panel.classList.add(
    "show"
  );

  overlay.classList.add(
    "show"
  );

  panel.setAttribute(
    "aria-hidden",
    "false"
  );

  // ----------------------------------------------------------
  // LEAFLET CHECK
  // ----------------------------------------------------------

  if (
    typeof L === "undefined"
  ) {

    console.error(
      "Leaflet failed to load."
    );

    return;

  }

  // ----------------------------------------------------------
  // DEFAULT INDIA LOCATION
  // ----------------------------------------------------------

  const defaultLat =
    20.5937;

  const defaultLon =
    78.9629;

  const defaultZoom =
    5;

  // ----------------------------------------------------------
  // VERIFY LOCATION
  // ----------------------------------------------------------

  const hasLocation =

    typeof latitude === "number" &&

    typeof longitude === "number" &&

    Number.isFinite(latitude) &&

    Number.isFinite(longitude);

  const mapLat =
    hasLocation
      ? latitude
      : defaultLat;

  const mapLon =
    hasLocation
      ? longitude
      : defaultLon;

  const mapZoom =
    hasLocation
      ? 11
      : defaultZoom;

  // ----------------------------------------------------------
  // CREATE MAP ONLY ONCE
  // ----------------------------------------------------------

  if (!vayoraMap) {

    vayoraMap =
      L.map(
        "vayoraMap",
        {

          zoomControl:
            true,

          maxZoom:
            19,

          minZoom:
            2

        }
      )
      .setView(
        [
          mapLat,
          mapLon
        ],
        mapZoom
      );

    // --------------------------------------------------------
    // OSM BASE MAP
    // --------------------------------------------------------

    vayoraOsmLayer =
      L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {

          maxZoom:
            19,

          attribution:
            "&copy; OpenStreetMap contributors",

          zIndex:
            1

        }
      )
      .addTo(
        vayoraMap
      );

  }

  else {

    // Existing map.

    vayoraMap.setView(
      [
        mapLat,
        mapLon
      ],
      mapZoom
    );

    vayoraSetBaseLayer(
      vayoraSatelliteEnabled
    );

  }

  // ----------------------------------------------------------
  // CLEAR OLD VISUALIZATION
  // ----------------------------------------------------------

  vayoraClearRain();

  vayoraClearAqiVisual();

  vayoraClearWeatherVisual();

  // ----------------------------------------------------------
  // REMOVE OLD LOCATION MARKER
  // ----------------------------------------------------------

  if (
    vayoraMapMarker
  ) {

    vayoraRemoveLayer(
      vayoraMapMarker
    );

    vayoraMapMarker =
      null;

  }

  // ----------------------------------------------------------
  // ADD CURRENT LOCATION MARKER
  // ----------------------------------------------------------

  if (
    hasLocation
  ) {

    vayoraMapMarker =
      L.marker(
        [
          latitude,
          longitude
        ]
      )
      .addTo(
        vayoraMap
      );

    if (
      locationName
    ) {

      vayoraMapMarker
        .bindPopup(
          `<b>${locationName}</b>`
        )
        .openPopup();

    }

  }

  // ----------------------------------------------------------
  // CREATE ONE CONTROL BAR
  // ----------------------------------------------------------

  vayoraEnsureMapControls();

  vayoraSetActiveControl(
    "map"
  );

  // ----------------------------------------------------------
  // FORCE LEAFLET REFRESH
  // ----------------------------------------------------------

  setTimeout(
    () => {

      if (
        vayoraMap
      ) {

        vayoraMap.invalidateSize(
          true
        );

        vayoraSetBaseLayer(
          vayoraSatelliteEnabled
        );

      }

    },
    150
  );

}


// ── CLOSE MAP PANEL ──────────────────────────────────────────────────────────

function closeMapPanel() {

  const panel =
    document.getElementById(
      "mapPanel"
    );

  const overlay =
    document.getElementById(
      "mapOverlay"
    );

  if (
    !panel ||
    !overlay
  ) {

    return;

  }

  panel.classList.remove(
    "show"
  );

  overlay.classList.remove(
    "show"
  );

  panel.setAttribute(
    "aria-hidden",
    "true"
  );

}


// ── MAP BUTTON ───────────────────────────────────────────────────────────────

if (mapBtn) {

  mapBtn.addEventListener(
    "click",
    () => {

      if (!lastMapLocation) {
        return;
      }

      const isWeather =
        lastMapLocation.intent ===
          "WEATHER_QUERY" ||
        lastMapLocation.intent ===
          "WEATHER_FORECAST";

      const title =
        isWeather
          ? `${lastMapLocation.city} Weather Map`
          : `${lastMapLocation.city} AQI Map`;

      const subtitle =
        isWeather
          ? "Weather location"
          : "Air quality location";

      openMapPanel(
        title,
        subtitle,
        lastMapLocation.latitude,
        lastMapLocation.longitude,
        lastMapLocation.city
      );

    }
  );

}
// ── CURRENT LOCATION / GPS ─────────────────────────────────────────────

async function useCurrentLocation() {
  if (!navigator.geolocation) {
    alert("GPS location is not supported by this browser.");
    locationSearch?.classList.add("active");
    locationInput?.focus();
    return;
  }

  if (locationBtn) {
    locationBtn.disabled = true;
    locationLabel.textContent = "Locating...";
  }

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        const url =
          `https://nominatim.openstreetmap.org/reverse` +
          `?format=jsonv2` +
          `&lat=${encodeURIComponent(latitude)}` +
          `&lon=${encodeURIComponent(longitude)}` +
          `&zoom=10`;

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error("Could not identify your location.");
        }

        const result = await response.json();

        const address = result.address || {};

        const city =
          address.city ||
          address.town ||
          address.municipality ||
          address.village ||
          address.county ||
          "Current location";

        const displayName =
          result.display_name ||
          city;

        window.vayoraSelectedLocation = {
          source: "gps",
          query: city,
          name: city,
          displayName,
          latitude,
          longitude
        };

        locationLabel.textContent = city;

        locationSearch?.classList.remove("active");

        console.log(
          "VAYORA GPS location:",
          window.vayoraSelectedLocation
        );

      } catch (err) {
        console.error(
          "VAYORA GPS location error:",
          err
        );

        locationLabel.textContent = "Location";

        alert(
          `Could not determine your location: ${
            err.message || err
          }`
        );

        locationSearch?.classList.add("active");
        locationInput?.focus();

      } finally {
        if (locationBtn) {
          locationBtn.disabled = false;
        }
      }
    },

    (error) => {
      console.error(
        "VAYORA browser geolocation error:",
        error
      );

      locationLabel.textContent = "Location";

      if (error.code === error.PERMISSION_DENIED) {
        alert(
          "Location permission was denied. You can search for a location manually."
        );
      } else {
        alert(
          "Could not access your current location. You can search manually."
        );
      }

      locationSearch?.classList.add("active");
      locationInput?.focus();

      if (locationBtn) {
        locationBtn.disabled = false;
      }
    },

    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 300000
    }
  );
}

locationBtn?.addEventListener(
  "click",
  useCurrentLocation
);

// ── LOCATION SEARCH ────────────────────────────────────────────────────

async function searchLocation() {
  const query = locationInput?.value.trim();

  if (!query) {
    return;
  }

  locationSearchBtn.disabled = true;
  locationSearchBtn.textContent = "…";

  try {
    const url =
      `https://nominatim.openstreetmap.org/search` +
      `?format=jsonv2` +
      `&q=${encodeURIComponent(query)}` +
      `&limit=1`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error("Location search failed.");
    }

    const results = await response.json();

    if (!results.length) {
      alert(`Location not found: ${query}`);
      return;
    }

    const result = results[0];

    const latitude = Number(result.lat);
    const longitude = Number(result.lon);

    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude)
    ) {
      throw new Error("Invalid location coordinates.");
    }

    const displayName =
      result.display_name ||
      result.name ||
      query;

    locationLabel.textContent =
      result.name || query;

    // Keep selected location separate for now.
    // We will connect it to VAYORA requests in the next step.
    window.vayoraSelectedLocation = {
      source: "manual",
      query,
      name: result.name || query,
      displayName,
      latitude,
      longitude
    };

    locationSearch.classList.remove("active");

    console.log(
      "VAYORA selected location:",
      window.vayoraSelectedLocation
    );

  } catch (err) {
    console.error(
      "VAYORA location search error:",
      err
    );

    alert(
      `Could not search location: ${
        err.message || err
      }`
    );

  } finally {
    locationSearchBtn.disabled = false;
    locationSearchBtn.textContent = "🔎";
  }
}

locationSearchBtn?.addEventListener(
  "click",
  searchLocation
);

locationInput?.addEventListener(
  "keydown",
  (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchLocation();
    }
  }
);