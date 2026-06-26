// 知行 (ZhiXing) Chrome 扩展 v7 — 全命令引擎 + 待办悬浮窗

// ── i18n ──────────────────────────────────────

const _lang = (navigator.language || "").startsWith("zh") ? "zh" : "en";

function _t(zh, en) {
  return _lang === "zh" ? zh : en;
}

// ── 内联样式 ─────────────────────────────────

const STYLE = `
#ka-wrapper * { box-sizing: border-box; }
#ka-btn {
  position: fixed !important; bottom: 24px !important; right: 24px !important; z-index: 2147483647 !important;
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; border: none; cursor: pointer; font-size: 24px;
  box-shadow: 0 4px 16px rgba(102,126,234,0.4);
  display: flex; align-items: center; justify-content: center;
  transition: transform .2s; user-select: none;
  font-family: -apple-system, sans-serif;
}
#ka-btn:hover { transform: scale(1.1); }
#ka-panel {
  position: fixed !important; bottom: 88px !important; right: 24px !important; z-index: 2147483646 !important;
  width: 420px; height: 560px; background: #fff;
  border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,0.18);
  display: none; flex-direction: column; overflow: hidden;
  font-family: -apple-system, "PingFang SC", sans-serif;
  font-size: 14px; color: #333; line-height: 1.5;
  animation: ka-in .2s ease-out;
}
@keyframes ka-in { from{opacity:0;transform:translateY(12px)scale(.96)} to{opacity:1;transform:translateY(0)scale(1)} }
#ka-panel.open { display: flex; }
#ka-header {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; padding: 12px 16px; display: flex;
  justify-content: space-between; align-items: center; flex-shrink: 0;
}
#ka-title { font-weight: 600; font-size: 14px; display:flex;align-items:center;gap:6px; }
#ka-close { background:none;border:none;color:rgba(255,255,255,0.7);cursor:pointer;font-size:16px;padding:2px 6px;border-radius:4px; }
#ka-close:hover { background:rgba(255,255,255,0.15);color:#fff; }
#ka-status { padding:3px 16px;font-size:11px;flex-shrink:0; }
.ka-on { color:#22c55e; } .ka-off { color:#ef4444;font-style:italic; }
#ka-info { padding:0 16px 4px;font-size:10px;color:#999;flex-shrink:0; }

/* 提醒徽标 */
#ka-badge {
  position:absolute;top:-4px;right:-4px;
  background:#ef4444;color:#fff;font-size:10px;font-weight:700;
  min-width:18px;height:18px;border-radius:10px;
  display:none;align-items:center;justify-content:center;
  padding:0 5px;box-shadow:0 1px 3px rgba(0,0,0,0.3);
  font-family:-apple-system,sans-serif;
}
#ka-btn { position:relative; }

/* 标签栏 */
#ka-tabs {
  display:flex; border-bottom:1px solid #eee; background:#fafafa; flex-shrink:0;
}
.ka-tab {
  flex:1; padding:6px; text-align:center; font-size:12px; cursor:pointer;
  color:#888; border-bottom:2px solid transparent; transition:all .2s;
}
.ka-tab.active { color:#667eea; border-bottom-color:#667eea; background:#fff; font-weight:600; }
.ka-tab:hover { color:#667eea; }

/* 待办区域 */
#ka-todo { display:none; flex-direction:column; flex:1; overflow:hidden; padding:8px 12px; background:#f5f6f8; }
#ka-todo.open { display:flex; }
.ka-ti { padding:6px 10px; margin:2px 0; background:#fff; border-radius:8px; display:flex; align-items:center; gap:8px; font-size:13px; box-shadow:0 1px 2px rgba(0,0,0,0.05); }
.ka-ti-done { opacity:.5; text-decoration:line-through; }
.ka-ti-high { border-left:3px solid #ef4444; }
.ka-ti-med { border-left:3px solid #f59e0b; }
.ka-ti-low { border-left:3px solid #22c55e; }
.ka-ti-text { flex:1; word-break:break-all; }
.ka-ti-btn { cursor:pointer; font-size:14px; opacity:.4; transition:opacity .2s; }
.ka-ti-btn:hover { opacity:1; }
#ka-todo-empty { text-align:center; color:#aaa; padding:20px; font-size:13px; }
#ka-todo-refresh { text-align:center; padding:6px; font-size:11px; color:#667eea; cursor:pointer; }
#ka-todo-header { display:flex; justify-content:space-between; align-items:center; padding:0 0 6px 0; font-size:12px; color:#666; }
#ka-todo-add { cursor:pointer; color:#667eea; font-size:12px; }
#ka-todo-input { display:flex; gap:4px; padding:4px 0; }
#ka-todo-input input { flex:1; border:1px solid #ddd; border-radius:12px; padding:4px 10px; font-size:12px; outline:none; }
#ka-todo-input input:focus { border-color:#667eea; }
#ka-todo-input button { background:#667eea; color:#fff; border:none; border-radius:12px; padding:4px 10px; font-size:11px; cursor:pointer; }

#ka-msgs {
  flex:1; overflow-y:auto; padding:8px 12px; background:#f5f6f8;
  display:flex; flex-direction:column; gap:6px;
}
.ka-msg { max-width:92%; padding:8px 12px; border-radius:10px;
  font-size:13px; line-height:1.5; word-break:break-word; white-space:pre-wrap; }
.ka-user { background:#667eea; color:#fff; align-self:flex-end; }
.ka-bot { background:#fff; color:#333; align-self:flex-start; box-shadow:0 1px 3px rgba(0,0,0,0.07); }
.ka-wait { background:#fff; color:#999; align-self:flex-start; font-style:italic; }
/* 交互按钮 */
.ka-opts { display:flex;flex-direction:column;gap:4px;margin-top:4px; }
.ka-opt {
  display:block; padding:7px 12px; background:#f0f4ff; color:#444;
  border:1px solid #e0e7ff; border-radius:8px; cursor:pointer;
  font-size:12px; text-align:left; transition:all .15s;
}
.ka-opt:hover { background:#667eea; color:#fff; border-color:#667eea; }
#ka-input-wrap { position:relative; border-top:1px solid #eee; background:#fff; flex-shrink:0; }
#ka-input-area { display:flex; gap:6px; padding:8px 12px; }
#ka-inp {
  flex:1; border:1px solid #ddd; border-radius:18px;
  padding:8px 12px; font-size:13px; outline:none;
  transition:border-color .2s;
}
#ka-inp:focus { border-color:#667eea; }
#ka-send {
  width:34px;height:34px;border-radius:50%;background:#667eea;
  color:#fff;border:none;cursor:pointer;font-size:15px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
}
#ka-send:disabled { background:#ccc; cursor:default; }
#ka-suggest {
  position:absolute; bottom:100%; left:12px; right:12px;
  max-height:200px; overflow-y:auto;
  background:#fff; border:1px solid #e0e7ff; border-radius:8px 8px 0 0;
  box-shadow:0 -4px 12px rgba(0,0,0,0.08);
  display:none;
}
.ka-sug-item {
  padding:6px 12px; cursor:pointer; font-size:12px; color:#444;
  border-bottom:1px solid #f0f0f0;
}
.ka-sug-item:hover { background:#f0f4ff; color:#667eea; }
.ka-sug-cmd { font-weight:600; }
.ka-sug-desc { color:#999; font-size:11px; margin-left:6px; }
#ka-help {
  padding:6px 12px; background:#f8f9fb; border-top:1px solid #eee;
  font-size:11px; color:#667eea; flex-shrink:0; cursor:pointer;
  text-align:center;
}
`;

function injectStyles() {
  const s = document.createElement("style");
  s.textContent = STYLE;
  document.head.appendChild(s);
}

// ── DOM ──────────────────────────────────────

function _applyI18n() {
  if (_lang !== "en") return;
  // i18n 已通过 _t() 模板文字处理，这里做运行时修复
  document.querySelectorAll("#ka-msgs .ka-bot:first-child").forEach(el => {
    if (el.textContent.includes("知行 助手")) el.textContent = "🤖 ZhiXing Assistant";
  });
}

function injectUI() {
  if (document.getElementById("ka-wrapper")) return;
  const w = document.createElement("div");
  w.id = "ka-wrapper";
  w.innerHTML = `
  <button id="ka-btn">🤖<span id="ka-badge">0</span></button>
  <div id="ka-panel">
    <div id="ka-header">
      <span id="ka-title">🤖 知行</span>
      <button id="ka-close">✕</button>
    </div>
    <div id="ka-status"><span class="ka-off">○ ${_t("未连接", "Disconnected")}</span></div>
    <div id="ka-tabs">
      <div class="ka-tab active" data-tab="chat">💬 ${_t("对话", "Chat")}</div>
      <div class="ka-tab" data-tab="todo">📋 ${_t("待办", "Tasks")}</div>
    </div>
    <div id="ka-msgs"><div class="ka-msg ka-bot">🤖 ${_t("知行 助手", "ZhiXing Assistant")}</div></div>
    <div id="ka-todo"><div id="ka-todo-loading" style="text-align:center;color:#aaa;padding:20px;">${_t("加载中...", "Loading...")}</div></div>
    <div id="ka-input-wrap">
      <div id="ka-suggest"></div>
      <div id="ka-input-area">
        <input id="ka-inp" placeholder="${_t("输入命令...", "Type a command...")}" autocomplete="off">
        <button id="ka-send">➤</button>
      </div>
    </div>
    <div style="display:flex;flex-shrink:0;border-top:1px solid #eee;">
  <div id="ka-help" style="flex:1;padding:6px 12px;background:#f8f9fb;font-size:11px;color:#667eea;cursor:pointer;text-align:center;">💡 ${_t("输入 help 查看命令", "Type help for commands")}</div>
  <div id="ka-clear" style="padding:6px 12px;background:#f8f9fb;font-size:11px;color:#999;cursor:pointer;text-align:center;border-left:1px solid #eee;">🗑️ ${_t("清除", "Clear")}</div>
</div>
  </div>`;
  document.body.appendChild(w);
}

// ── API ──────────────────────────────────────

function apiCall(payload) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: "api_call", payload }, (r) => {
      if (r?.ok) resolve(r.data);
      else reject(r?.error || "连接失败");
    });
  });
}

function apiPing() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: "ping" }, (r) => resolve(r?.ok || false));
  });
}

// ── 事件 ─────────────────────────────────────

function bindEvents() {
  let open = false;
  let currentTab = "chat";
  const btn = document.getElementById("ka-btn");
  const panel = document.getElementById("ka-panel");
  const inp = document.getElementById("ka-inp");
  const sendBtn = document.getElementById("ka-send");
  const suggest = document.getElementById("ka-suggest");
  const badge = document.getElementById("ka-badge");
  const todoEl = document.getElementById("ka-todo");
  const msgsEl = document.getElementById("ka-msgs");
  const tabs = document.querySelectorAll(".ka-tab");

  let suggestTimer = null;


  // 标签切换
  tabs.forEach(tab => {
    tab.onclick = () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentTab = tab.dataset.tab;
      if (currentTab === "todo") {
        msgsEl.style.display = "none";
        todoEl.classList.add("open");
        loadTodos();
      } else {
        msgsEl.style.display = "flex";
        todoEl.classList.remove("open");
        setTimeout(() => inp?.focus(), 200);
      }
    };
  });

  // 面板状态持久化
  function savePanelState() {
    try { sessionStorage.setItem("ka_open", JSON.stringify(open)); } catch(e) {}
  }

  btn.onclick = () => {
    open = !open;
    panel.classList.toggle("open", open);
    if (open) {
      if (currentTab === "chat") setTimeout(() => inp?.focus(), 200);
      else loadTodos();
    }
    savePanelState();
  };
  document.getElementById("ka-close").onclick = () => {
    open = false;
    panel.classList.remove("open");
    savePanelState();
  };

  // 加载待办 + 提醒事项（同步加载）
  async function loadTodos() {
    todoEl.innerHTML = '<div id="ka-todo-loading" style="text-align:center;color:#aaa;padding:20px;">加载中...</div>';
    try {
      // 同时加载待办和提醒事项
      const [todoData, remData] = await Promise.all([
        apiCall({ action: "command", params: { cmd: "待办列表" } }),
        apiCall({ action: "command", params: { cmd: "提醒列表" } }).catch(() => ({ data: "" })),
      ]);
      const todoText = todoData.data || "";
      const remText = remData.data || "";

      let html = '<div id="ka-todo-header"><span>📋 待办</span><span id="ka-todo-add">＋ 新建</span></div><div id="ka-todo-input" style="display:none"><input id="ka-todo-inp" placeholder="输入待办内容..." autocomplete="off"><button id="ka-todo-btn">添加</button></div>';
      let todoCount = 0;
      if (todoText) {
        const lines = todoText.split("\n").filter(l => l.trim());
        lines.forEach(line => {
          const isDone = line.includes("✅") || line.includes("已完成");
          const isHigh = line.includes("🔴");
          const isMed = line.includes("🟡");
          const cls = `ka-ti${isDone ? " ka-ti-done" : ""}${isHigh ? " ka-ti-high" : isMed ? " ka-ti-med" : " ka-ti-low"}`;
          const num = line.match(/[#＃](\d+)/);
          const id = num ? num[1] : "";
          if (line.includes("总计") || line.includes("待办") || !id) return;
          if (!isDone) todoCount++;
          const short = line.replace(/^\s*\d+\.\s*/, "").split("  ")[0];
          html += `<div class="${cls}">
            <span class="ka-ti-text">${short}</span>
            ${!isDone ? `<span class="ka-ti-btn" data-done="${id}">✅</span>` : ""}
            <span class="ka-ti-btn" data-del="${id}">🗑️</span>
          </div>`;
        });
      }

      if (!todoCount) {
        html += '<div id="ka-todo-empty">✅ ' + _t("暂无待办事项", "No pending tasks") + '</div>';
      }

      // macOS 提醒事项（同步显示）
      if (remText && !remText.includes("❌") && !remText.includes("暂无") && !remText.includes("无法读取")) {
        const remLines = remText.split("\n").filter(l => l.trim() && !l.includes("提醒事项") && l.length < 50);
        if (remLines.length > 0) {
          html += '<div style="font-size:11px;color:#999;padding:8px 0 2px;">📌 macOS ' + _t("提醒事项", "Reminders") + '</div>';
          remLines.slice(0, 8).forEach(line => {
            html += `<div class="ka-ti" style="padding:4px 8px;font-size:12px;"><span class="ka-ti-text">${line.replace(/✅|❌|📝/g, "").trim()}</span></div>`;
          });
        }
      }

      html += '<div id="ka-todo-refresh">🔄 ' + _t("刷新", "Refresh") + '</div>';
      todoEl.innerHTML = html;

      // 事件
      document.querySelectorAll("[data-done]").forEach(el => {
        el.onclick = async () => {
          await apiCall({ action: "command", params: { cmd: `完成待办 ${el.dataset.done}` } });
          loadTodos(); updateBadge();
        };
      });
      document.querySelectorAll("[data-del]").forEach(el => {
        el.onclick = async () => {
          await apiCall({ action: "command", params: { cmd: `删除待办 ${el.dataset.done}` } });
          loadTodos(); updateBadge();
        };
      });
      document.getElementById("ka-todo-refresh").onclick = loadTodos;
      const todoInput = document.getElementById("ka-todo-input");
      const todoInp = document.getElementById("ka-todo-inp");
      const todoBtn = document.getElementById("ka-todo-btn");
      document.getElementById("ka-todo-add").onclick = () => {
        todoInput.style.display = "flex";
        todoInp.focus();
      };
      async function addTodo() {
        const text = todoInp.value.trim();
        if (!text) return;
        todoInp.value = "";
        todoInput.style.display = "none";
        await apiCall({ action: "command", params: { cmd: `添加待办 ${text}` } });
        loadTodos();
        updateBadge();
      }
      todoBtn.onclick = addTodo;
      todoInp.onkeydown = (e) => { if (e.key === "Enter") addTodo(); };
      updateBadge();
    } catch(e) {
      todoEl.innerHTML = '<div style="text-align:center;color:#ef4444;padding:20px;">❌ 加载失败</div><div id="ka-todo-refresh">🔄 重试</div>';
      document.getElementById("ka-todo-refresh").onclick = loadTodos;
    }
  }

  // 更新徽标
  async function updateBadge() {
    try {
      const data = await apiCall({ action: "command", params: { cmd: "待办列表" } });
      const text = data.data || "";
      const m = text.match(/待办\s*(\d+)/);
      const count = m ? parseInt(m[1]) : 0;
      badge.style.display = count > 0 ? "flex" : "none";
      badge.textContent = count > 99 ? "99+" : count;
    } catch(e) { badge.style.display = "none"; }
  }
  setTimeout(updateBadge, 2000);
  setInterval(updateBadge, 30000);

  // 输入建议
  inp.oninput = () => {
    clearTimeout(suggestTimer);
    const text = inp.value.trim();
    if (text.length < 2) { suggest.style.display = "none"; return; }
    suggestTimer = setTimeout(async () => {
      try {
        const data = await apiCall({ action: "suggest", params: { cmd: text } });
        if (data.type === "suggestions") {
          const items = data.data || [];
          if (items.length > 0 && items[0] !== text) {
            suggest.innerHTML = items.slice(0, 8).map(s =>
              `<div class="ka-sug-item"><span class="ka-sug-cmd">${s}</span></div>`
            ).join("");
            suggest.style.display = "block";
            suggest.querySelectorAll(".ka-sug-item").forEach((el, i) => {
              el.onclick = () => {
                inp.value = items[i].split("→")[0].trim();
                suggest.style.display = "none";
                inp.focus();
              };
            });
            return;
          }
        }
      } catch(e) {}
      suggest.style.display = "none";
    }, 300);
  };
  inp.onkeydown = (e) => { if (e.key === "Enter") { suggest.style.display = "none"; send(); } };
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#ka-suggest") && !e.target.closest("#ka-inp")) {
      suggest.style.display = "none";
    }
  });

  async function send() {
    const text = inp.value.trim();
    if (!text) return;
    suggest.style.display = "none";

    // 仅截图操作隐藏面板，其他操作始终显示控制台
    const isScreenshot = (text === "截图" || text === "截屏") && !text.includes("复制");
    const panelEl = document.getElementById("ka-panel");
    const btnEl = document.getElementById("ka-btn");
    if (isScreenshot) {
      if (btnEl) btnEl.style.display = "none";
      if (panelEl) panelEl.style.display = "none";
    }

    addMsg(text, "user");
    inp.value = "";
    sendBtn.disabled = true;
    addMsg(_t("⏳ 处理中...", "⏳ Processing..."), "wait");

    try {
      const data = await apiCall({
        action: "command",
        params: { cmd: text, pageUrl: window.location.href, pageTitle: document.title },
      });
      document.querySelector(".ka-wait")?.remove();
      addMsg(data.data || "(空)", "bot");
      setStatus(true);
    } catch (e) {
      document.querySelector(".ka-wait")?.remove();
      addMsg(_t("❌ 连接服务器失败\n请确认 python3 server.py 已运行", "❌ Server offline\nRun: python3 server.py"), "bot");
      setStatus(false);
    }

    // 截图后恢复按钮，面板保持开启（文字类命令不恢复）
    if (isScreenshot) {
      if (btnEl) {
        btnEl.style.removeProperty("display");
        btnEl.style.display = "flex";
      }
      if (panelEl) {
        panelEl.style.display = "flex";
        panelEl.classList.add("open");
      }
    }

    sendBtn.disabled = false;
  }

  sendBtn.onclick = send;
  inp.onkeydown = (e) => { if (e.key === "Enter") { suggest.style.display = "none"; send(); } };

  document.getElementById("ka-help").onclick = () => {
    inp.value = "help";
    send();
  };
  document.getElementById("ka-clear").onclick = () => {
    const box = document.getElementById("ka-msgs");
    if (box) {
      box.innerHTML = '<div class="ka-msg ka-bot">' + _t("🗑️ 会话已清除", "🗑️ Session cleared") + '</div>';
      try { sessionStorage.removeItem("ka_msgs"); } catch(e) {}
    }
  };
}

// ── 消息 ─────────────────────────────────────

// ── 消息持久化 ──────────────────────────────

function saveMessages() {
  const box = document.getElementById("ka-msgs");
  if (!box) return;
  const msgs = [];
  box.querySelectorAll(".ka-msg").forEach(el => {
    const text = el.textContent || "";
    const cls = el.className || "";
    if (text && !text.startsWith("⏳")) {
      msgs.push({ text, type: cls.includes("ka-user") ? "user" : "bot" });
    }
  });
  // 只保留最近 50 条
  if (msgs.length > 50) msgs.splice(0, msgs.length - 50);
  try { sessionStorage.setItem("ka_msgs", JSON.stringify(msgs)); } catch(e) {}
}

function restoreMessages() {
  const box = document.getElementById("ka-msgs");
  if (!box) return;
  try {
    const saved = JSON.parse(sessionStorage.getItem("ka_msgs") || "[]");
    if (saved.length > 0) {
      box.innerHTML = "";
      saved.forEach(m => {
        const d = document.createElement("div");
        d.className = `ka-msg ka-${m.type}`;
        d.textContent = m.text;
        box.appendChild(d);
      });
    }
  } catch(e) {}
}

function addMsg(text, type) {
  const box = document.getElementById("ka-msgs");
  const w = box?.querySelector(".ka-wait");
  if (type !== "wait" && w) w.remove();

  const wrap = document.createElement("div");
  wrap.style.cssText = "display:flex;flex-direction:column;gap:2px;max-width:92%;align-self:" +
    (type === "user" ? "flex-end" : "flex-start");

  // 检测交互式 JSON 响应
  let interactiveData = null;
  if (type === "bot" && text.startsWith('{"type":"interactive"')) {
    try { interactiveData = JSON.parse(text); } catch(e) {}
  }

  const d = document.createElement("div");
  d.className = `ka-msg ka-${type}`;

  if (interactiveData) {
    d.textContent = interactiveData.message || "请选择：";
    wrap.appendChild(d);

    const optsDiv = document.createElement("div");
    optsDiv.className = "ka-opts";
    (interactiveData.options || []).forEach(opt => {
      const btn = document.createElement("button");
      btn.className = "ka-opt";
      btn.textContent = opt.label;
      btn.onclick = () => {
        const inp = document.getElementById("ka-inp");
        if (inp) { inp.value = opt.command; inp.focus(); }
        // 自动发送
        const sendBtn = document.getElementById("ka-send");
        if (sendBtn && inp) {
          const enter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true });
          inp.dispatchEvent(enter);
        }
      };
      optsDiv.appendChild(btn);
    });
    wrap.appendChild(optsDiv);
  } else {
    d.textContent = text;
    wrap.appendChild(d);
  }

  // 保存消息到 sessionStorage
  if (type !== "wait") setTimeout(saveMessages, 100);

  // 复制按钮（仅非交互式消息）
  if (!interactiveData && type !== "wait" && type !== "user" && text.length > 5) {
    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:6px;padding:0 4px;";
    const copyBtn = document.createElement("span");
    copyBtn.textContent = "📋 复制";
    copyBtn.style.cssText = "font-size:11px;color:#667eea;cursor:pointer;opacity:0.6;user-select:none;";
    copyBtn.onmouseenter = () => { copyBtn.style.opacity = "1"; };
    copyBtn.onmouseleave = () => { copyBtn.style.opacity = "0.6"; };
    copyBtn.onclick = (e) => {
      e.stopPropagation();
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.textContent = "✅ 已复制";
          setTimeout(() => { copyBtn.textContent = "📋 复制"; }, 2000);
        }).catch(() => fallbackCopy());
      } else { fallbackCopy(); }
      function fallbackCopy() {
        try {
          const ta = document.createElement("textarea");
          ta.value = text;
          ta.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0;";
          document.body.appendChild(ta);
          ta.focus(); ta.select();
          setTimeout(() => {
            document.execCommand("copy");
            document.body.removeChild(ta);
            copyBtn.textContent = "✅ 已复制";
            setTimeout(() => { copyBtn.textContent = "📋 复制"; }, 2000);
          }, 50);
        } catch(e) {
          window.prompt("复制:", text);
          copyBtn.textContent = "📋 复制";
        }
      }
    };
    btnRow.appendChild(copyBtn);
    wrap.appendChild(btnRow);
  }

  box?.appendChild(wrap);
  if (box) box.scrollTop = box.scrollHeight;
}

function setStatus(ok) {
  const el = document.getElementById("ka-status");
  if (!el) return;
  el.innerHTML = ok
    ? '<span class="ka-on">● ' + _t("已连接", "Connected") + '</span>'
    : '<span class="ka-off">○ ' + _t("未连接", "Disconnected") + '</span>';
  document.getElementById("ka-send").disabled = !ok;
}

async function checkConnection() {
  try { setStatus(await apiPing()); }
  catch(e) { setStatus(false); }
}

// ── 启动 ─────────────────────────────────────

// ── 页面导航时持久化面板状态 ──────────────────

function init() {
  injectStyles();
  injectUI();
  _applyI18n();
  bindEvents();
  setTimeout(checkConnection, 500);
  setInterval(checkConnection, 15000);

  // 恢复消息历史 + 面板状态
  restoreMessages();
  try {
    const saved = JSON.parse(sessionStorage.getItem("ka_open") || "false");
    if (saved) {
      setTimeout(() => {
        const btn = document.getElementById("ka-btn");
        if (btn) btn.click();
      }, 500);
    }
  } catch(e) {}
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
