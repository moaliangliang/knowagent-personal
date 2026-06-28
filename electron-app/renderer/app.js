/**
 * 知行 ZhiXing Desktop — 主渲染进程
 * 只负责窗口管理、标签切换、待办/工作流面板
 * WebSocket 连接由 ai.js 统一管理
 */

// ── i18n ──────────────────────────────────────

const _lang = navigator.language.startsWith("zh") ? "zh" : "en";
function _t(zh, en) { return _lang === "zh" ? zh : en; }

if (_lang === "zh") {
  document.querySelectorAll("[id^=s-]").forEach(el => {
    const map = {
      "s-ai": "对话", "s-workflow": "工作流", "s-tasks": "待办",
    };
    if (map[el.id]) el.textContent = map[el.id];
  });
}

// ── DOM ──────────────────────────────────────

const $ = (id) => document.getElementById(id);
const todoPanel = $("todo-panel");

// ── 标题栏 ────────────────────────────────────

$("btn-hide").onclick = () => window.ka.hide();
$("btn-close").onclick = () => window.ka.hide();

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") window.ka.hide();
});

// ── 标签切换 ──────────────────────────────────

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("open"));

    const tabName = tab.dataset.tab;
    if (tabName === "ai") {
      $("ai-panel").classList.add("open");
      setTimeout(() => $("ai-input-box")?.focus(), 200);
    } else if (tabName === "todo") {
      todoPanel.classList.add("open");
      loadTodos();
    } else if (tabName === "workflow") {
      const wfPanel = $("wf-panel");
      wfPanel.classList.add("open");
      if (!wfPanel._wfInitialized) {
        wfPanel._wfInitialized = true;
        if (typeof initWorkflowEditor === "function") {
          initWorkflowEditor(wfPanel);
        } else {
          const script = document.createElement("script");
          script.src = "workflow.js";
          script.onload = () => initWorkflowEditor(wfPanel);
          document.head.appendChild(script);
        }
      }
    }
  };
});

// ── 待办 ──────────────────────────────────────

async function runCommand(cmd) {
  try {
    const resp = await fetch(`http://localhost:9511/command?cmd=${encodeURIComponent(cmd)}`);
    const data = await resp.json();
    return { success: true, data: data.data || "" };
  } catch (e) {
    return { success: false, data: "❌ 连接失败: " + e.message };
  }
}

async function loadTodos() {
  todoPanel.innerHTML = '<div style="text-align:center;color:#aaa;padding:20px;">' + _t("加载中...", "Loading...") + '</div>';
  try {
    const [todoResult, remResult] = await Promise.all([
      runCommand("待办列表"),
      runCommand("提醒列表").catch(() => ({ data: "" })),
    ]);
    const text = todoResult.data || "";
    const remText = remResult.data || "";
    let html = '<div style="display:flex;justify-content:space-between;padding:0 0 6px 0;font-size:12px;color:#666;"><span>📋 ' + _t("待办", "Tasks") + '</span></div>';
    const lines = text.split("\n").filter(l => l.trim());
    let count = 0;
    lines.forEach(line => {
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

// ── Electron IPC ──────────────────────────────

window.ka.onFocusInput(() => setTimeout(() => $("ai-input-box")?.focus(), 200));
window.ka.onGlobalScreenshot(() => {
  const input = $("ai-input-box");
  if (input) { input.value = "截图"; input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" })); }
});
window.ka.onLog((msg) => console.log("[ZhiXing]", msg));
window.ka.onLauncherResult((result) => console.log("[Launcher]", result));
