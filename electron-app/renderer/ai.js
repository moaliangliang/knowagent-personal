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

  // 设置按钮
  document.getElementById("ai-settings-btn").onclick = showSettings;
  document.getElementById("ai-market-btn").onclick = showMarketplace;
}

async function showMarketplace() {
  const msgs = document.getElementById("ai-msgs");
  const welcome = document.getElementById("ai-welcome");
  if (welcome) welcome.remove();

  msgs.innerHTML = '<div class="ai-msg ai-wait" style="align-self:flex-start;">⏳ 加载技能市场...</div>';

  try {
    const resp = await wsSend({ action: "market_list", params: {} });
    const skills = resp.data || [];

    if (!Array.isArray(skills) || skills.length === 0) {
      msgs.innerHTML = `
        <div class="ai-msg ai-bot" style="align-self:flex-start;">
          📭 技能市场暂无可用技能
        </div>
      `;
      return;
    }

    let html = `
      <div class="ai-msg ai-bot" style="align-self:flex-start;width:100%;">
        <b>🏪 技能市场</b>
        <p style="font-size:12px;color:#999;margin:4px 0 12px;">点击安装即可添加社区技能</p>
        <div style="display:flex;flex-direction:column;gap:8px;">
    `;

    skills.forEach(s => {
      html += `
        <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:#f8f9fc;border-radius:10px;">
          <span style="font-size:24px;">${s.icon || "📦"}</span>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:600;font-size:13px;color:#333;">${s.name}</div>
            <div style="font-size:11px;color:#999;">${s.description || ""}</div>
            <div style="font-size:10px;color:#bbb;margin-top:2px;">${(s.tags || []).map(t => "#" + t).join(" ")}</div>
          </div>
          <button class="ai-install-btn" data-name="${s.name}" style="flex-shrink:0;padding:6px 14px;border-radius:8px;border:1px solid #667eea;background:#fff;color:#667eea;cursor:pointer;font-size:12px;font-family:inherit;">
            安装
          </button>
        </div>
      `;
    });

    html += '</div></div>';
    msgs.innerHTML = html;

    // 绑定安装按钮事件
    document.querySelectorAll(".ai-install-btn").forEach(btn => {
      btn.onclick = async () => {
        const name = btn.dataset.name;
        btn.textContent = "⏳";
        btn.disabled = true;
        try {
          const result = await wsSend({ action: "skill_install", params: { name } });
          btn.textContent = "✅ 已安装";
          btn.style.borderColor = "#22c55e";
          btn.style.color = "#22c55e";
        } catch (e) {
          btn.textContent = "❌ 失败";
          btn.style.borderColor = "#ef4444";
          btn.style.color = "#ef4444";
        }
      };
    });

    msgs.scrollTop = msgs.scrollHeight;
  } catch (e) {
    msgs.innerHTML = `<div class="ai-msg ai-bot" style="align-self:flex-start;">❌ 加载失败: ${e}</div>`;
  }
}

async function showSettings() {
  const msgs = document.getElementById("ai-msgs");
  const welcome = document.getElementById("ai-welcome");
  if (welcome) welcome.remove();

  // 读取当前配置
  let currentKey = "";
  try {
    currentKey = (await wsSend({ action: "get_config", params: { key: "llm_api_key" } })).data || "";
  } catch(e) {}

  msgs.innerHTML = `
    <div class="ai-msg ai-bot" style="align-self:flex-start;">
      <b>⚙️ 设置</b><br><br>

      <label style="font-size:12px;color:#666;">DeepSeek API Key</label><br>
      <input id="key-input" type="text"
        style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:8px;font-size:13px;margin:4px 0 12px;box-sizing:border-box;"
        placeholder="sk-..." value="${currentKey}"><br>

      <label style="font-size:12px;color:#666;">API Base URL（可选，默认 https://api.deepseek.com/v1）</label><br>
      <input id="base-input" type="text"
        style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:8px;font-size:13px;margin:4px 0 12px;box-sizing:border-box;"
        placeholder="https://api.deepseek.com/v1"><br>

      <div style="display:flex;gap:8px;">
        <button id="save-key-btn" class="ai-scene-btn" style="flex:1;background:#667eea;color:#fff;border-color:#667eea;">
          💾 保存
        </button>
        <button id="back-btn" class="ai-scene-btn" style="flex:1;">
          ↩ 返回
        </button>
      </div>
      <div id="key-status" style="margin-top:8px;font-size:12px;color:#999;"></div>
    </div>
  `;

  document.getElementById("save-key-btn").onclick = async () => {
    const key = document.getElementById("key-input").value.trim();
    const base = document.getElementById("base-input").value.trim();
    const status = document.getElementById("key-status");

    if (key) {
      await wsSend({ action: "set_config", params: { key: "llm_api_key", value: key } });
    }
    if (base) {
      await wsSend({ action: "set_config", params: { key: "base_url", value: base } });
    }
    status.textContent = "✅ 已保存！重启应用后生效";
    status.style.color = "#22c55e";
  };

  document.getElementById("back-btn").onclick = renderWelcome;
}

async function updateUsage() {
  try {
    const resp = await wsSend({ action: "get_config", params: { key: "usage" } });
    // usage is tracked server-side, shown in chat response
  } catch(e) {}
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
