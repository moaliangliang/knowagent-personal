/**
 * 知行 ZhiXing Desktop — 渲染进程
 * 通过 Electron IPC 直接执行命令，无需额外后端
 */




// ── i18n ──────────────────────────────────────

const _lang = navigator.language.startsWith("zh") ? "zh" : "en";

function _t(zh, en) {
  return _lang === "zh" ? zh : en;
}

// 如果系统是中文，替换 UI 文字
if (_lang === "zh") {
  document.querySelectorAll("[id^=s-]").forEach(el => {
    const map = {
      "s-disconnected": "未连接",
      "s-chat": "对话",
      "s-tasks": "待办",
      "s-workflow": "工作流",
      "s-help": "输入 help 查看命令",
      "s-clear": "清除",
    };
    if (map[el.id]) el.textContent = map[el.id];
  });
  // 更新输入框 placeholder
  document.getElementById("input-box").placeholder = "输入命令...\nShift+Enter 换行";
  document.getElementById("btn-hide").title = "隐藏";
  document.getElementById("btn-close").title = "关闭";
}

// ── 同步/更新界面 ────────────────────────────

async function showSyncSettings() {
  const status = await window.ka.syncGetStatus().catch(() => ({}));
  const hasToken = status.token || false;
  const lastSync = status.lastSync ? new Date(status.lastSync).toLocaleString() : _t("从未", "Never");

  const box = document.getElementById("msgs");
  const wrap = document.createElement("div");
  wrap.style.cssText = "display:flex;flex-direction:column;gap:4px;max-width:100%;align-self:flex-start;";

  const header = document.createElement("div");
  header.className = "msg msg-bot";
  header.style.cssText = "width:100%;font-size:12px;";
  header.innerHTML = `
    <b>⚙️ ${_t("设置", "Settings")}</b><br>
    ☁️ ${_t("云同步", "Cloud Sync")}: ${hasToken ? "✅" : "❌"}<br>
    <span style="font-size:10px;color:#999;">${_t("上次同步", "Last sync")}: ${lastSync}</span>
  `;
  wrap.appendChild(header);

  const syncRow = document.createElement("div");
  syncRow.style.cssText = "display:flex;gap:4px;";

  const syncBtn = document.createElement("button");
  syncBtn.className = "opt-btn";
  syncBtn.textContent = hasToken ? "☁️ " + _t("立即同步", "Sync Now") : "🔑 " + _t("配置 Token", "Set Token");
  syncBtn.onclick = async () => {
    if (!hasToken) {
      const token = prompt(_t("输入 GitHub Personal Access Token", "Enter GitHub Token"));
      if (token) {
        const r = await window.ka.syncSaveToken(token);
        addMsg(r.ok ? "✅ " + _t("Token 已保存", "Token saved") : "❌ " + _t("保存失败", "Failed"), "bot");
        showSyncSettings();
      }
    } else {
      addMsg("⏳ " + _t("同步中...", "Syncing..."), "wait");
      const r = await window.ka.syncPush();
      const w = document.querySelector(".msg-wait");
      if (w) w.remove();
      addMsg(r.ok ? "✅ ☁️ " + _t("同步成功", "Synced!") : "❌ " + (r.error || _t("同步失败", "Sync failed")), "bot");
    }
  };
  syncRow.appendChild(syncBtn);

  const updateBtn = document.createElement("button");
  updateBtn.className = "opt-btn";
  updateBtn.textContent = "🔄 " + _t("检查更新", "Check Updates");
  updateBtn.onclick = async () => {
    addMsg("🔄 " + _t("检查中...", "Checking..."), "wait");
    const r = await window.ka.updateCheck();
    const w = document.querySelector(".msg-wait");
    if (w) w.remove();
    addMsg(r.ok ? "🔄 OK" : "❌ " + _t("检查失败", "Check failed"), "bot");
  };
  syncRow.appendChild(updateBtn);
  wrap.appendChild(syncRow);

  // 监听更新
  window.ka.onUpdateAvailable((ver) => {
    addMsg(`🔄 ${_t("新版本", "New version")}: ${ver}`, "bot");
    window.ka.updateDownload();
  });
  window.ka.onUpdateProgress((pct) => {
    const w = document.querySelector(".msg-wait");
    if (w) w.textContent = `📥 ${pct}%`;
  });

  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
}

document.getElementById("title-text").ondblclick = showSyncSettings;

// ── 状态 ─────────────────────────────────────——

let panelOpen = true;

// ── DOM 引用 ──────────────────────────────────

const $ = (id) => document.getElementById(id);
const msgs = $("msgs");
const todoPanel = $("todo-panel");
const input = $("input-box");
const sendBtn = $("send-btn");

// ── 标题栏 ────────────────────────────────────

$("btn-hide").onclick = () => window.ka.hide();
$("btn-maximize").onclick = () => window.ka.maximize();
$("btn-close").onclick = () => window.ka.hide();

// 窗口拖动（通过 IPC 让主进程处理）
let isDragging = false, dragX = 0, dragY = 0;
$("titlebar").addEventListener("mousedown", (e) => {
  isDragging = true;
  dragX = e.screenX;
  dragY = e.screenY;
  document.body.style.cursor = "grabbing";
});
document.addEventListener("mousemove", (e) => {
  if (!isDragging) return;
  const dx = e.screenX - dragX;
  const dy = e.screenY - dragY;
  if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
    window.ka.moveBy(dx, dy);
    dragX = e.screenX;
    dragY = e.screenY;
  }
});
document.addEventListener("mouseup", () => {
  isDragging = false;
  document.body.style.cursor = "";
});

// Escape 键隐藏窗口
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") window.ka.hide();
});

// ── 标签切换 ──────────────────────────────────

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    if (tab.dataset.tab === "todo") {
      msgs.style.display = "none";
      todoPanel.classList.add("open");
      document.getElementById("wf-panel").classList.remove("open");
      loadTodos();
    } else if (tab.dataset.tab === "workflow") {
      msgs.style.display = "none";
      todoPanel.classList.remove("open");
      const wfPanel = document.getElementById("wf-panel");
      wfPanel.classList.add("open");
      // 懒加载工作流编辑器
      if (!wfPanel._wfInitialized) {
        wfPanel._wfInitialized = true;
        if (typeof initWorkflowEditor === "function") {
          initWorkflowEditor(wfPanel);
        } else {
          // 动态加载 workflow.js
          const script = document.createElement("script");
          script.src = "workflow.js";
          script.onload = () => initWorkflowEditor(wfPanel);
          document.head.appendChild(script);
        }
      }
    } else {
      msgs.style.display = "flex";
      todoPanel.classList.remove("open");
      document.getElementById("wf-panel").classList.remove("open");
      setTimeout(() => input?.focus(), 200);
    }
  };
});

// ── 命令执行（IPC 直连主进程） ──────────────────

function stripAnsi(str) {
  return str.replace(/\x1b\[[0-9;]*m/g, "");
}

async function runCommand(cmd) {
  try {
    const result = await window.ka.runCommand(cmd);
    return result;
  } catch (e) {
    return { success: false, data: `❌ 执行失败: ${e.message}` };
  }
}

// ── 消息 ──────────────────────────────────────

function addMsg(text, type) {
  const wait = msgs?.querySelector(".msg-wait");
  if (type !== "wait" && wait) wait.remove();

  const wrap = document.createElement("div");
  wrap.style.cssText = `display:flex;flex-direction:column;gap:2px;max-width:92%;align-self:${type === "user" ? "flex-end" : "flex-start"}`;

  // 检测交互 JSON
  let interactive = null;
  if (type === "bot" && text.startsWith('{"type":"interactive"')) {
    try { interactive = JSON.parse(text); } catch (e) {}
  }

  const d = document.createElement("div");
  d.className = `msg msg-${type}`;

  if (interactive) {
    d.textContent = interactive.message || "请选择：";
    wrap.appendChild(d);
    const opts = document.createElement("div");
    opts.className = "opts";
    (interactive.options || []).forEach((opt) => {
      const btn = document.createElement("button");
      btn.className = "opt-btn";
      btn.textContent = opt.label;
      btn.onclick = () => {
        input.value = opt.command;
        sendMessage();
      };
      opts.appendChild(btn);
    });
    wrap.appendChild(opts);
  } else {
    // 帮助输出：模块标题（以 🔧💬🌐 等 emoji 开头）自动加粗
    if (type === "bot" && /[🔧💬🌐📁💻🎬📅🤖📊🎵⌨️🔐📋⚡🔌🛡️]/.test(text)) {
      d.innerHTML = text.split("\n").map(line => {
        const esc = line.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
        if (/^\s*[🔧💬🌐📁💻🎬📅🤖📊🎵⌨️🔐📋⚡🔌🛡️]/.test(line)) {
          return `<b>${esc}</b>`;
        }
        return esc;
      }).join("\n");
    } else {
      d.textContent = text;
    }
    wrap.appendChild(d);

    // 复制按钮
    if (type === "bot" && text.length > 10) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;gap:6px;padding:0 4px;";
      const btn = document.createElement("span");
      btn.textContent = "📋 复制";
      btn.style.cssText = "font-size:11px;color:#667eea;cursor:pointer;opacity:0.6;";
      btn.onmouseenter = () => (btn.style.opacity = "1");
      btn.onmouseleave = () => (btn.style.opacity = "0.6");
      btn.onclick = () => {
        navigator.clipboard.writeText(text).then(() => {
          btn.textContent = "✅ 已复制";
          setTimeout(() => (btn.textContent = "📋 复制"), 2000);
        });
      };
      row.appendChild(btn);
      wrap.appendChild(row);
    }
  }

  msgs?.appendChild(wrap);
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function setStatus(ok) {
  const el = $("status-text");
  if (!el) return;
  el.className = ok ? "on" : "off";
  el.innerHTML = ok ? "● " + _t("已连接", "Connected") : "○ " + _t("未连接", "Disconnected");
  sendBtn.disabled = !ok;
}

// ── 发送 ──────────────────────────────────────

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;
  addMsg(text, "user");
  input.value = "";
  sendBtn.disabled = true;
  addMsg(_t("⏳ 处理中...", "⏳ Processing..."), "wait");

  // 截图类命令：先隐藏窗口，执行完再恢复
  const isScreenshot = /截图|screenshot|看看|ocr/i.test(text);
  if (isScreenshot) {
    window.ka.hideNoFloat(); // 隐藏窗口，不显示 Z 按钮
    await new Promise(r => setTimeout(r, 300)); // 等隐藏动画完成
  }

  const result = await runCommand(text);
  const wait = document.querySelector(".msg-wait");
  if (wait) wait.remove();
  const output = stripAnsi(result.data || "");
  if (result.success) {
    addMsg(output, "bot");
  } else {
    addMsg(output, "bot");
  }
  sendBtn.disabled = false;

  // 截图后恢复窗口
  if (isScreenshot) {
    await new Promise(r => setTimeout(r, 500));
    window.ka.toggle(); // 重新打开窗口
  }
}

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

// ── 帮助/清除 ─────────────────────────────────

$("help-btn").onclick = () => {
  input.value = "help";
  sendMessage();
};

$("clear-btn").onclick = () => {
  msgs.innerHTML = '<div class="msg msg-bot">' + _t("🗑️ 会话已清除", "🗑️ Session cleared") + '</div>';
};

// ── 设置功能 ─────────────────────────────────

// 双击标题栏打开设置
document.getElementById("title-text").ondblclick = async () => {
  const status = await window.ka.syncGetStatus().catch(() => ({}));
  const hasToken = status.token || false;
  const lastSync = status.lastSync || _t("从未", "Never");
  const hasUpdate = false;

  const msg = _t(
    `📋 设置
━━━━━━━━━━━━━━━━━━
☁️ 云同步: ${hasToken ? "✅ 已配置" : "❌ 未配置"}
   上次同步: ${lastSync}
━━━━━━━━━━━━━━━━━━
🔄 自动更新: ${hasUpdate ? "有更新可用" : "已是最新"}

输入数字选择:
1. ${hasToken ? "重新配置" : "配置"} GitHub Token
2. ${_t("立即同步", "Sync Now")}
3. ${_t("检查更新", "Check Updates")}
4. ${_t("取消", "Cancel")}`,
    `📋 Settings
━━━━━━━━━━━━━━━━━━
☁️ Cloud Sync: ${hasToken ? "✅ Configured" : "❌ Not configured"}
   Last sync: ${lastSync}
━━━━━━━━━━━━━━━━━━
🔄 Auto Update: ${hasUpdate ? "Update available" : "Up to date"}

Choose:
1. ${hasToken ? "Reconfigure" : "Configure"} GitHub Token
2. Sync Now
3. Check Updates
4. Cancel`
  );

  input.value = msg;
  sendMessage();
};

// 监听设置命令
const _origSend = sendMessage;
sendMessage = async function() {
  const text = input.value.trim();
  if (text === "1" && msgs.lastChild?.textContent?.includes("GitHub Token")) {
    const token = prompt(_t("输入 GitHub Personal Access Token：\n(需要 gist 权限)", "Enter GitHub Token:\n(needs gist scope)"));
    if (token) {
      const result = await window.ka.syncSaveToken(token);
      addMsg(result.ok ? "✅ " + _t("Token 已保存", "Token saved") : "❌ " + _t("保存失败", "Save failed"), "bot");
    }
    return;
  }
  if (text === "2" && msgs.lastChild?.textContent?.includes("GitHub Token")) {
    addMsg("⏳ " + _t("同步中...", "Syncing..."), "wait");
    const result = await window.ka.syncPush();
    document.querySelector(".msg-wait")?.remove();
    addMsg(result.ok ? "✅ " + _t("同步成功", "Synced!") : "❌ " + (result.error || _t("同步失败", "Failed")), "bot");
    return;
  }
  if (text === "3" && msgs.lastChild?.textContent?.includes("GitHub Token")) {
    const result = await window.ka.updateCheck();
    addMsg(result.ok ? "🔄 " + _t("正在检查更新...", "Checking...") : "❌ " + _t("检查失败", "Check failed"), "bot");
    return;
  }
  _origSend.call(this);
};

// ── 待办 ──────────────────────────────────────

async function loadTodos() {
  todoPanel.innerHTML = '<div style="text-align:center;color:#aaa;padding:20px;">' + _t("加载中...", "Loading...") + '</div>';
  try {
    const [todoResult, remResult] = await Promise.all([
      runCommand("待办列表"),
      runCommand("提醒列表").catch(() => ({ data: "" })),
    ]);
    const text = todoResult.data || "";
    const remText = remResult.data || "";
    let html =
      '<div style="display:flex;justify-content:space-between;padding:0 0 6px 0;font-size:12px;color:#666;"><span>📋 ' + _t("待办", "Tasks") + '</span></div>';
    const lines = text.split("\n").filter((l) => l.trim());
    let count = 0;
    lines.forEach((line) => {
      if (line.includes("总计") || line.includes("待办")) return;
      const num = line.match(/[#＃](\d+)/);
      if (!num) return;
      count++;
      const isDone = line.includes("✅");
      const isHigh = line.includes("🔴");
      const cls = `todo-item${isDone ? " todo-done" : ""}${isHigh ? " todo-high" : " todo-med"}`;
      const short = line.replace(/^\s*\d+\.\s*/, "").split("  ")[0];
      html += `<div class="${cls}"><span class="todo-text">${short}</span></div>`;
    });

    // macOS 提醒事项
    if (remText && !remText.includes("❌") && !remText.includes("无法读取")) {
      const remLines = remText.split("\n").filter(l => l.trim() && !l.includes("提醒事项") && l.length < 50);
      if (remLines.length > 0) {
        html += '<div style="font-size:11px;color:#999;padding:8px 0 2px;">📌 macOS ' + _t("提醒事项", "Reminders") + '</div>';
        remLines.slice(0, 8).forEach(line => {
          html += `<div class="todo-item" style="padding:4px 8px;font-size:12px;"><span class="todo-text">${line.replace(/✅|❌|📝/g, "").trim()}</span></div>`;
        });
      }
    }

    if (!count) html += '<div style="text-align:center;color:#aaa;padding:20px;">✅ ' + _t("暂无待办", "No tasks") + '</div>';
    html += '<div id="todo-refresh" style="text-align:center;padding:6px;font-size:11px;color:#667eea;cursor:pointer;">🔄 ' + _t("刷新", "Refresh") + '</div>';
    todoPanel.innerHTML = html;
    const refresh = todoPanel.querySelector("#todo-refresh");
    if (refresh) refresh.onclick = loadTodos;
  } catch (e) {
    todoPanel.innerHTML = '<div style="text-align:center;color:#ef4444;padding:20px;">❌ ' + _t("加载失败", "Load failed") + '</div>';
  }
}

// ── 就绪检测 ──────────────────────────────────

function checkReady() {
  setStatus(true); // IPC 直连，始终就绪
}

// ── Electron IPC ──────────────────────────────

window.ka.onFocusInput(() => setTimeout(() => input?.focus(), 200));
window.ka.onGlobalScreenshot(() => {
  input.value = "截图";
  sendMessage();
});
window.ka.onLog((msg) => addMsg(`[系统] ${msg}`, "bot"));

// 从 Launcher 接收结果
window.ka.onLauncherResult((result) => {
  addMsg(result, "bot");
});

// ── 启动 ──────────────────────────────────────

setStatus(true);
checkReady();
setInterval(checkConnection, 15000);
addMsg(_t(
  "🤖 知行已启动\n\n支持 98+ 命令，试试: 状态 / 看看 / 帮助",
  "🤖 Flow ready\n\n98+ commands. Try: status / screenshot / help"
), "bot");
