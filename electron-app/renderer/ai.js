/**
 * 知行 AI 对话 — 自然语言控制 Mac
 * 通过 WebSocket → server.py → AI Orchestrator → 101 个命令
 */

// ── WebSocket ────────────────────────────────────

let ws = null;
let pending = {};
let wsReqId = 0;
let wsConnected = false;
let sessionId = "";

function wsSend(payload) {
  return new Promise((resolve, reject) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      reject("未连接服务器");
      return;
    }
    const id = ++wsReqId;
    pending[id] = {
      resolve,
      reject,
      timer: setTimeout(() => { delete pending[id]; reject("请求超时"); }, 30000),
    };
    try {
      ws.send(JSON.stringify({ ...payload, requestId: id }));
    } catch (e) {
      clearTimeout(pending[id].timer);
      delete pending[id];
      reject("发送失败: " + e.message);
    }
  });
}

function connectWS() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  ws = new WebSocket("ws://localhost:9510");
  ws.onopen = () => {
    wsConnected = true;
    updateStatus(true);
  };
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      const rid = data.requestId;
      if (rid && pending[rid]) {
        clearTimeout(pending[rid].timer);
        pending[rid].resolve(data);
        delete pending[rid];
      }
    } catch (e) {}
  };
  ws.onclose = () => {
    wsConnected = false;
    ws = null;
    updateStatus(false);
    setTimeout(connectWS, 3000);
  };
  ws.onerror = () => { if (ws) ws.close(); };
}
connectWS();

// ── DOM ──────────────────────────────────────────

const SCENES = [
  { icon: "📝", label: "写日报", prompt: "帮我写今天的日报" },
  { icon: "📁", label: "整理桌面", prompt: "把桌面文件按类型整理到文件夹" },
  { icon: "📧", label: "快捷邮件", prompt: "查看收件箱，有需要回复的邮件吗" },
  { icon: "🌐", label: "翻译/润色", prompt: "翻译这段文字" },
];

// ── 状态 ─────────────────────────────────────────

function updateStatus(ok) {
  const el = document.getElementById("s-ai");
  if (el) {
    el.textContent = ok ? "AI" : "AI (离线)";
    document.getElementById("ai-send-btn").disabled = !ok;
  }
}

// ── 渲染 ─────────────────────────────────────────

function renderWelcome() {
  const msgs = document.getElementById("ai-msgs");
  msgs.innerHTML = `
    <div id="ai-welcome">
      <h2>⬡ 知行 AI</h2>
      <p>用自然语言控制你的 Mac<br>试试下面的场景，或者直接输入任何指令</p>
      <div id="ai-scenes">
        ${SCENES.map(s => `
          <button class="ai-scene-btn" data-prompt="${s.prompt}">
            <span class="ai-scene-btn-icon">${s.icon}</span>
            ${s.label}
          </button>
        `).join("")}
      </div>
    </div>
  `;
  // 场景按钮事件
  document.querySelectorAll(".ai-scene-btn").forEach(btn => {
    btn.onclick = () => {
      const prompt = btn.dataset.prompt;
      document.getElementById("ai-input-box").value = prompt;
      sendMessage();
    };
  });
}

function addMsg(text, type) {
  const msgs = document.getElementById("ai-msgs");
  const wait = msgs.querySelector(".ai-wait");
  if (type !== "wait" && wait) wait.remove();

  // 初次消息时移除欢迎页
  const welcome = document.getElementById("ai-welcome");
  if (welcome && type !== "system") welcome.remove();

  const d = document.createElement("div");
  d.className = `ai-msg ai-${type}`;
  d.textContent = text;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

// ── 发送 ─────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById("ai-input-box");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  input.style.height = "auto";

  addMsg(text, "user");
  addMsg("⚡ 知行思考中...", "wait");

  const sendBtn = document.getElementById("ai-send-btn");
  sendBtn.disabled = true;

  try {
    const response = await wsSend({
      action: "chat",
      params: { text, session_id: sessionId },
    });

    const data = response.data || {};
    const wait = document.querySelector(".ai-wait");
    if (wait) wait.remove();

    addMsg(data.reply || "(空回复)", "bot");

    if (data.session_id) sessionId = data.session_id;
  } catch (e) {
    const wait = document.querySelector(".ai-wait");
    if (wait) wait.remove();
    addMsg("❌ " + e, "bot");
  }

  sendBtn.disabled = false;
}

// ── 事件绑定 ────────────────────────────────────

function init() {
  const input = document.getElementById("ai-input-box");
  const sendBtn = document.getElementById("ai-send-btn");

  renderWelcome();

  sendBtn.onclick = sendMessage;
  input.onkeydown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };
  input.oninput = () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  };
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
