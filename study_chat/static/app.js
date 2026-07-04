const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const fileInput = document.getElementById("file-input");
const attachmentsEl = document.getElementById("attachments");
const internetToggle = document.getElementById("internet-toggle");
const internetHint = document.getElementById("internet-hint");
const statusEl = document.getElementById("status");
const startGameBtn = document.getElementById("start-game");

let sessionId = null;
/** @type {{ id: string, name: string }[]} */
let pendingFiles = [];
let busy = false;

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function setStatus(text, kind = "") {
  statusEl.textContent = text;
  statusEl.className = `status ${kind}`;
}

function renderAttachments() {
  attachmentsEl.innerHTML = "";
  pendingFiles.forEach((f) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML = `📄 ${f.name} <button type="button" aria-label="Remove">×</button>`;
    chip.querySelector("button").onclick = () => {
      pendingFiles = pendingFiles.filter((x) => x.id !== f.id);
      renderAttachments();
    };
    attachmentsEl.appendChild(chip);
  });
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
  return data;
}

async function startGame() {
  startGameBtn.disabled = true;
  startGameBtn.textContent = "Starting…";
  try {
    await api("/api/ready-for-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    addMessage("Launching Shape Shooter — switch to the game window.", "system");
    startGameBtn.textContent = "Game starting…";
  } catch (err) {
    startGameBtn.disabled = false;
    startGameBtn.textContent = "Start Game →";
    addMessage(`Could not signal launcher: ${err.message}`, "system");
  }
}

async function init() {
  startGameBtn.addEventListener("click", startGame);

  try {
    const health = await api("/api/health");
    if (!health.gemini_configured) {
      setStatus("No API key", "err");
      addMessage(
        "Gemini is not configured (add GEMINI_API_KEY to .env). You can still click Start Game when ready.",
        "system"
      );
      sendBtn.disabled = true;
    } else {
      const { session_id } = await api("/api/session", { method: "POST" });
      sessionId = session_id;
      setStatus("Ready", "ok");
      addMessage(
        "Hi! What would you like to study? Tell me the subject, your level, and any deadlines — or upload notes and I'll ask questions based on them.",
        "bot"
      );
    }
  } catch (err) {
    setStatus("Offline", "err");
    addMessage(`Could not reach the server: ${err.message}`, "system");
    sendBtn.disabled = true;
  }
}

async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api/upload?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Upload failed");
  pendingFiles.push({ id: data.file_id, name: data.name });
  renderAttachments();
  addMessage(`Uploaded: ${data.name}`, "system");
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || busy || !sessionId) return;

  busy = true;
  sendBtn.disabled = true;
  addMessage(text, "user");
  inputEl.value = "";

  const typing = document.createElement("div");
  typing.className = "typing";
  typing.textContent = "Thinking…";
  chatEl.appendChild(typing);
  chatEl.scrollTop = chatEl.scrollHeight;

  const fileIds = pendingFiles.map((f) => f.id);

  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        allow_internet: internetToggle.checked,
        file_ids: fileIds,
      }),
    });
    typing.remove();
    addMessage(data.reply, "bot");
    pendingFiles = [];
    renderAttachments();
  } catch (err) {
    typing.remove();
    addMessage(`Error: ${err.message}`, "system");
  } finally {
    busy = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

internetToggle.addEventListener("change", () => {
  if (internetToggle.checked) {
    internetHint.textContent = "Internet is ON — the assistant may search the web for this session's replies.";
    addMessage("You enabled internet search for upcoming replies.", "system");
  } else {
    internetHint.textContent = "Off by default. Turn on only when you want the assistant to search the web.";
    addMessage("Internet search turned off — replies will use chat and uploads only.", "system");
  }
});

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  fileInput.value = "";
  if (!file || !sessionId) return;
  try {
    sendBtn.disabled = true;
    await uploadFile(file);
  } catch (err) {
    addMessage(`Upload error: ${err.message}`, "system");
  } finally {
    sendBtn.disabled = false;
  }
});

init();
