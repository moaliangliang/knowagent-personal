/**
 * 知行 (ZhiXing) 可视化工作流编辑器
 */

// ── 步骤定义 ───────────────────────────────────

const STEP_TYPES = {
  // ── 触发器 ──────────────────
  trigger_schedule: { icon: "⏰", color: "#ef4444", category: "trigger", label: { zh: "定时触发", en: "Schedule" }, desc: { zh: "按时间自动执行", en: "Run on schedule" }, fields: ["cron"], group: "触发器" },
  trigger_interval: { icon: "🔄", color: "#f97316", category: "trigger", label: { zh: "间隔触发", en: "Interval" }, desc: { zh: "每隔 N 秒执行", en: "Run every N seconds" }, fields: ["seconds", "max_runs"], group: "触发器" },
  trigger_webhook:  { icon: "🔗", color: "#06b6d4", category: "trigger", label: { zh: "Webhook 触发", en: "Webhook" }, desc: { zh: "外部 HTTP 调用触发", en: "Triggered by HTTP call" }, fields: ["webhook_url"], group: "触发器" },

  // ── 条件分支 ──────────────────
  condition: { icon: "🔀", color: "#f59e0b", category: "logic", label: { zh: "条件分支", en: "Condition" }, desc: { zh: "如果...否则...", en: "If...else..." }, fields: ["condition_type", "condition_value", "if_actions", "else_actions"], group: "逻辑" },
  wait_until: { icon: "👁️", color: "#8b5cf6", category: "logic", label: { zh: "等待出现", en: "Wait Until" }, desc: { zh: "等待页面出现指定文字", en: "Wait for text to appear" }, fields: ["target", "timeout"], group: "逻辑" },

  // ── 数据 ──────────────────
  variable: { icon: "📦", color: "#14b8a6", category: "data", label: { zh: "变量赋值", en: "Set Variable" }, desc: { zh: "设置变量供后续使用", en: "Set a variable" }, fields: ["var_name", "var_value"], group: "数据" },
  extract:  { icon: "🔍", color: "#0ea5e9", category: "data", label: { zh: "提取数据", en: "Extract" }, desc: { zh: "从页面提取文字", en: "Extract text from page" }, fields: ["selector", "var_name"], group: "数据" },

  // ── 动作 ──────────────────
  navigate:   { icon: "🌐", color: "#667eea", category: "action", label: { zh: "打开网页", en: "Navigate" }, desc: { zh: "导航到指定 URL", en: "Go to a URL" }, fields: ["value"], group: "动作" },
  click:      { icon: "👆", color: "#764ba2", category: "action", label: { zh: "点击", en: "Click" }, desc: { zh: "点击页面元素", en: "Click an element" }, fields: ["target"], group: "动作" },
  fill:       { icon: "⌨️", color: "#f59e0b", category: "action", label: { zh: "填表", en: "Fill" }, desc: { zh: "输入表单字段", en: "Fill a form field" }, fields: ["target", "value"], group: "动作" },
  type:       { icon: "✏️", color: "#22c55e", category: "action", label: { zh: "输入", en: "Type" }, desc: { zh: "键盘输入文字", en: "Type text" }, fields: ["value"], group: "动作" },
  wait:       { icon: "⏳", color: "#06b6d4", category: "action", label: { zh: "等待", en: "Wait" }, desc: { zh: "等待指定秒数", en: "Wait for seconds" }, fields: ["seconds"], group: "动作" },
  screenshot: { icon: "📸", color: "#ec4899", category: "action", label: { zh: "截图", en: "Screenshot" }, desc: { zh: "截屏保存", en: "Take screenshot" }, fields: [], group: "动作" },
  assert:     { icon: "✅", color: "#10b981", category: "action", label: { zh: "断言", en: "Assert" }, desc: { zh: "验证页面文字", en: "Verify text on page" }, fields: ["target"], group: "动作" },
};

const _lang_wf = (navigator.language || "").startsWith("zh") ? "zh" : "en";

function _tw(zh, en) { return _lang_wf === "zh" ? zh : en; }

// ── 状态 ───────────────────────────────────────

let steps = [];
let selectedIdx = -1;
let nextId = 1;
let isRunning = false;
let savedWorkflows = [];

// Community 版步骤限制
const MAX_COMMUNITY_STEPS = 5;
let _isPro = false;

async function checkProStatus() {
  try {
    const resp = await fetch("http://localhost:9511", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "command", params: { cmd: "pro_status" } }),
    });
    const data = await resp.json();
    _isPro = data.data === "pro" || data.data === true;
  } catch (e) {
    _isPro = false;
  }
}

// ── DOM 引用 ──────────────────────────────────

const $wf = (id) => document.getElementById(id);

// ── 初始化 ─────────────────────────────────────

function initWorkflowEditor(container) {
  container.innerHTML = `
    <div id="wf-toolbar">
      <button id="wf-run-btn" class="wf-btn wf-btn-primary">▶ ${_tw("运行", "Run")}</button>
      <button id="wf-save-btn" class="wf-btn">💾 ${_tw("保存", "Save")}</button>
      <button id="wf-load-btn" class="wf-btn">📂 ${_tw("加载", "Load")}</button>
      <button id="wf-clear-btn" class="wf-btn">🗑️ ${_tw("清空", "Clear")}</button>
      <button id="wf-export-btn" class="wf-btn">📋 ${_tw("导出 YAML", "Export YAML")}</button>
      <span id="wf-step-count" style="margin-left:auto;font-size:12px;color:#999;">${_tw("0 步", "0 steps")}</span>
    </div>
    <div id="wf-body">
      <div id="wf-palette">
        <div style="font-size:11px;color:#999;padding:4px 8px;font-weight:600;">${_tw("步骤", "Steps")}</div>
        <div id="wf-step-list"></div>
      </div>
      <div id="wf-canvas">
        <div id="wf-steps"></div>
        <div id="wf-drop-hint">${_tw("从左侧拖入步骤，或点 + 添加", "Drag steps from left or click + to add")}</div>
      </div>
      <div id="wf-config">
        <div id="wf-config-header">${_tw("配置", "Config")}</div>
        <div id="wf-config-body">
          <div style="text-align:center;color:#ccc;padding:20px;font-size:13px;">${_tw("选择一个步骤进行配置", "Select a step to configure")}</div>
        </div>
      </div>
    </div>
  `;

  // 填充步骤面板（按分组）
  const stepList = $wf("wf-step-list");
  const groups = {};
  Object.entries(STEP_TYPES).forEach(([type, def]) => {
    const g = def.group || _tw("其他", "Other");
    if (!groups[g]) groups[g] = [];
    groups[g].push([type, def]);
  });

  Object.entries(groups).forEach(([gname, items]) => {
    const header = document.createElement("div");
    header.style.cssText = "font-size:10px;color:#999;padding:4px 8px;font-weight:600;border-top:1px solid #f0f0f0;";
    header.textContent = gname;
    stepList.appendChild(header);

    items.forEach(([type, def]) => {
      const el = document.createElement("div");
      el.className = "wf-palette-item";
      el.draggable = true;
      el.dataset.type = type;
      el.innerHTML = `<span class="wf-palette-icon" style="background:${def.color}">${def.icon}</span><span>${def.label[_lang_wf]}</span>`;
      el.ondragstart = (e) => {
        e.dataTransfer.setData("text/plain", type);
        e.dataTransfer.effectAllowed = "copy";
      };
      el.onclick = () => addStep(type);
      stepList.appendChild(el);
    });
  });

  // 绑定事件
  bindWfEvents();
  renderSteps();
  loadWorkflowList();

  // 检查 Pro 状态，显示限制标记
  checkProStatus().then(() => {
    const toolbar = document.getElementById("wf-toolbar");
    if (!toolbar) return;
    const badge = document.createElement("span");
    badge.style.cssText = "margin-left:auto;font-size:10px;padding:2px 8px;border-radius:4px;";
    if (_isPro) {
      badge.style.cssText += "color:#22c55e;background:#dcfce7;";
      badge.textContent = _tw("💎 Pro 无限步骤", "💎 Pro Unlimited");
    } else {
      badge.style.cssText += "color:#f59e0b;background:#fef3c7;";
      badge.textContent = _tw(`Community · ${MAX_COMMUNITY_STEPS}步限制`, `Community · ${MAX_COMMUNITY_STEPS} steps max`);
    }
    toolbar.appendChild(badge);
  });
}

// ── 步骤管理 ───────────────────────────────────

function addStep(type, config = {}) {
  const def = STEP_TYPES[type];
  if (!def) return;

  // Community 版步骤限制
  if (!_isPro && steps.length >= MAX_COMMUNITY_STEPS) {
    alert(_tw(
      `⚠️ Community 版最多 ${MAX_COMMUNITY_STEPS} 步\n升级 Pro 解锁无限步骤`,
      `⚠️ Community max ${MAX_COMMUNITY_STEPS} steps\nUpgrade to Pro for unlimited steps`
    ));
    return;
  }

  steps.push({
    id: nextId++,
    type,
    icon: def.icon,
    color: def.color,
    label: def.label[_lang_wf],
    config: { ...config },
  });
  renderSteps();
  selectStep(steps.length - 1);
}

function removeStep(idx) {
  if (idx < 0 || idx >= steps.length) return;
  steps.splice(idx, 1);
  if (selectedIdx >= steps.length) selectedIdx = steps.length - 1;
  renderSteps();
  if (selectedIdx >= 0) showConfig(selectedIdx);
}

function moveStep(from, to) {
  if (to < 0 || to >= steps.length) return;
  const [item] = steps.splice(from, 1);
  steps.splice(to, 0, item);
  selectedIdx = to;
  renderSteps();
  showConfig(to);
}

function clearSteps() {
  if (steps.length === 0) return;
  if (!confirm(_tw("确定清空所有步骤？", "Clear all steps?"))) return;
  steps = [];
  selectedIdx = -1;
  renderSteps();
  $wf("wf-config-body").innerHTML = '<div style="text-align:center;color:#ccc;padding:20px;font-size:13px;">' + _tw("选择一个步骤进行配置", "Select a step to configure") + '</div>';
}

// ── 渲染 ───────────────────────────────────────

function renderSteps() {
  const container = $wf("wf-steps");
  const hint = $wf("wf-drop-hint");
  if (!container) return;

  $wf("wf-step-count").textContent = _tw(`${steps.length} 步`, `${steps.length} steps`);

  if (steps.length === 0) {
    container.innerHTML = "";
    if (hint) hint.style.display = "block";
    return;
  }
  if (hint) hint.style.display = "none";

  container.innerHTML = steps.map((step, idx) => `
    <div class="wf-step ${idx === selectedIdx ? "wf-step-active" : ""} ${isRunning && idx === 0 ? "wf-step-running" : ""}"
         data-idx="${idx}" draggable="true"
         ondragstart="window._wfDragStart(event, ${idx})"
         ondragover="window._wfDragOver(event, ${idx})"
         ondrop="window._wfDrop(event, ${idx})"
         ondragend="window._wfDragEnd(event)"
         onclick="window._wfSelectStep(${idx})">
      <div class="wf-step-num">${idx + 1}</div>
      <span class="wf-step-icon" style="background:${step.color}">${step.icon}</span>
      <div class="wf-step-body">
        <div class="wf-step-title">${step.label}</div>
        <div class="wf-step-preview">${stepPreview(step)}</div>
      </div>
      <button class="wf-step-del" onclick="event.stopPropagation();window._wfRemoveStep(${idx})">✕</button>
    </div>
  `).join("");

  // 添加拖拽放置区
  container.innerHTML += `<div class="wf-drop-zone" ondrop="window._wfDropEnd(event)" ondragover="event.preventDefault()">+</div>`;
}

function stepPreview(step) {
  const def = STEP_TYPES[step.type];
  if (!def) return "";
  const parts = [];
  if (step.config.cron) parts.push(`⏰ ${step.config.cron}`);
  if (step.config.webhook_url) parts.push(`🔗 ${step.config.webhook_url}`);
  if (step.config.condition_type) parts.push(`🔀 ${step.config.condition_value || "..."}`);
  if (step.config.var_name) parts.push(`📦 ${step.config.var_name}=${(step.config.var_value || "").substring(0, 15)}`);
  if (step.config.selector) parts.push(`🔍 ${step.config.selector}`);
  if (step.config.target) parts.push(`🔍 ${step.config.target.substring(0, 20)}`);
  if (step.config.value) parts.push(`📝 ${step.config.value.substring(0, 20)}`);
  if (step.config.seconds) parts.push(`⏱ ${step.config.seconds}s`);
  if (step.config.timeout) parts.push(`⏱ ${step.config.timeout}s超时`);
  return parts.join(" ") || def.desc[_lang_wf];
}

// ── 选择与配置 ─────────────────────────────────

function selectStep(idx) {
  selectedIdx = idx;
  renderSteps();
  if (idx >= 0) showConfig(idx);
}

function showConfig(idx) {
  const step = steps[idx];
  if (!step) return;
  const def = STEP_TYPES[step.type];
  const body = $wf("wf-config-body");

  body.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
      <span class="wf-step-icon" style="background:${step.color}">${step.icon}</span>
      <span style="font-weight:600;font-size:14px;">${step.label}</span>
      <span style="font-size:11px;color:#999;margin-left:auto;">#${step.id}</span>
    </div>
    <button class="wf-btn wf-btn-sm" onclick="window._wfRemoveStep(${idx})" style="color:#ef4444;border-color:#ef4444;width:100%;">🗑️ ${_tw("删除此步骤", "Delete step")}</button>
  `;

  // 动态生成配置字段
  def.fields.forEach(f => {
    const fieldConfigs = {
      target:    { label: _tw("目标文字", "Target"), ph: _tw("如: 登录、提交", "e.g. Login") },
      value:     { label: _tw("输入值", "Value"), ph: _tw("输入内容", "Input value") },
      seconds:   { label: _tw("秒数", "Seconds"), ph: "1", type: "number" },
      timeout:   { label: _tw("超时(秒)", "Timeout (s)"), ph: "10", type: "number" },
      cron:      { label: _tw("Cron 表达式", "Cron expression"), ph: "0 9 * * *" },
      max_runs:  { label: _tw("最大执行次数", "Max runs"), ph: "1", type: "number" },
      webhook_url: { label: _tw("Webhook URL", "Webhook URL"), ph: "/webhook/ka-001" },
      condition_type: { label: _tw("条件类型", "Condition type"), ph: "", type: "select", options: [
        { value: "text_exists", label: _tw("页面包含文字", "Page contains text") },
        { value: "text_missing", label: _tw("页面不包含文字", "Page missing text") },
        { value: "element_exists", label: _tw("元素存在", "Element exists") },
        { value: "variable_equals", label: _tw("变量等于", "Variable equals") },
      ]},
      condition_value: { label: _tw("条件值", "Value to check"), ph: _tw("输入文字或变量名", "Text or variable") },
      var_name:  { label: _tw("变量名", "Variable name"), ph: "myVar" },
      var_value: { label: _tw("变量值", "Variable value"), ph: _tw("{{step1.result}} 引用上一步", "{{step1.result}}") },
      selector:  { label: _tw("CSS 选择器", "CSS selector"), ph: ".class or #id" },
    };

    const fc = fieldConfigs[f];
    if (!fc) return;

    if (fc.type === "select") {
      const opts = (fc.options || []).map(o =>
        `<option value="${o.value}" ${step.config[f] === o.value ? "selected" : ""}>${o.label}</option>`
      ).join("");
      body.innerHTML += `
        <div class="wf-field">
          <label>${fc.label}</label>
          <select class="wf-input" onchange="window._wfUpdateConfig(${idx}, '${f}', this.value)">
            ${opts}
          </select>
        </div>`;
    } else {
      body.innerHTML += `
        <div class="wf-field">
          <label>${fc.label}</label>
          <input class="wf-input" id="wf-cfg-${f}" value="${escapeHtml(step.config[f] || "")}" placeholder="${fc.ph}" ${fc.type === "number" ? 'type="number"' : ""} oninput="window._wfUpdateConfig(${idx}, '${f}', this.value)">
        </div>`;
    }
  });
}

function escapeHtml(s) {
  if (!s) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── 全局回调（给 DOM 事件用） ──────────────────

window._wfSelectStep = (idx) => selectStep(idx);
window._wfRemoveStep = (idx) => {
  removeStep(idx);
  // 删除后自动选中上一个
  if (steps.length > 0 && selectedIdx >= steps.length) {
    selectedIdx = steps.length - 1;
    showConfig(selectedIdx);
  }
};
window._wfUpdateConfig = (idx, key, val) => {
  if (steps[idx]) {
    steps[idx].config[key] = val;
    renderSteps();
  }
};

// 拖拽
let _dragFrom = -1;
window._wfDragStart = (e, idx) => {
  _dragFrom = idx;
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", "move");
};
window._wfDragOver = (e, idx) => {
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
};
window._wfDrop = (e, toIdx) => {
  e.preventDefault();
  const type = e.dataTransfer.getData("text/plain");
  if (type === "move" && _dragFrom >= 0) {
    moveStep(_dragFrom, toIdx);
    _dragFrom = -1;
  } else if (STEP_TYPES[type]) {
    addStep(type);
  }
};
window._wfDropEnd = (e) => {
  e.preventDefault();
  _dragFrom = -1;
};
window._wfDragEnd = (e) => {
  _dragFrom = -1;
};

// ── 生成 YAML ──────────────────────────────────

function toYaml() {
  let result = "# ZhiXing Workflow\n# 生成时间: " + new Date().toISOString() + "\n\n";

  // 添加元数据
  const hasTrigger = steps.some(s => STEP_TYPES[s.type]?.category === "trigger");
  if (hasTrigger) {
    result += "triggers:\n";
    steps.filter(s => STEP_TYPES[s.type]?.category === "trigger").forEach(s => {
      result += `  - type: ${s.type.replace("trigger_", "")}\n`;
      if (s.config.cron) result += `    cron: "${s.config.cron}"\n`;
      if (s.config.seconds) result += `    interval: ${s.config.seconds}\n`;
      if (s.config.max_runs) result += `    max_runs: ${s.config.max_runs}\n`;
      if (s.config.webhook_url) result += `    webhook: "${s.config.webhook_url}"\n`;
    });
    result += "\n";
  }

  result += "steps:\n";
  steps.filter(s => STEP_TYPES[s.type]?.category !== "trigger").forEach((s) => {
    const lines = [`  - action: ${s.type}`];
    if (s.config.condition_type) lines.push(`    condition: ${s.config.condition_type}`);
    if (s.config.condition_value) lines.push(`    value: "${s.config.condition_value}"`);
    if (s.config.target) lines.push(`    target: "${s.config.target}"`);
    if (s.config.value) lines.push(`    value: "${s.config.value}"`);
    if (s.config.seconds) lines.push(`    wait: ${s.config.seconds}`);
    if (s.config.timeout) lines.push(`    timeout: ${s.config.timeout}`);
    if (s.config.var_name) lines.push(`    var_name: "${s.config.var_name}"`);
    if (s.config.var_value) lines.push(`    var_value: "${s.config.var_value}"`);
    if (s.config.selector) lines.push(`    selector: "${s.config.selector}"`);
    result += lines.join("\n") + "\n";
  });

  return result;
}

// ── 运行 ────────────────────────────────────────

async function runWorkflow() {
  if (steps.length === 0) return;
  isRunning = true;
  renderSteps();

  const yaml = toYaml();

  // 通过 API 运行
  try {
    const resp = await fetch("http://localhost:9511", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "command",
        params: { cmd: `auto_script\n${yaml}` },
      }),
    });
    const data = await resp.json();
    alert(data.data || "✅ " + _tw("执行完成", "Done"));
  } catch (e) {
    alert("❌ " + _tw("运行失败: ", "Run failed: ") + e.message);
  }

  isRunning = false;
  renderSteps();
}

// ── 保存/加载 ──────────────────────────────────

function saveWorkflow() {
  const name = prompt(_tw("工作流名称：", "Workflow name:"));
  if (!name) return;
  try {
    const list = JSON.parse(localStorage.getItem("ka_workflows") || "[]");
    list.push({ name, steps: JSON.parse(JSON.stringify(steps)), updated: new Date().toISOString() });
    localStorage.setItem("ka_workflows", JSON.stringify(list));
    loadWorkflowList();
    alert("✅ " + _tw("已保存", "Saved"));
  } catch (e) {
    alert("❌ " + e.message);
  }
}

function loadWorkflowList() {
  try {
    savedWorkflows = JSON.parse(localStorage.getItem("ka_workflows") || "[]");
  } catch {
    savedWorkflows = [];
  }
}

function loadWorkflow(idx) {
  const wf = savedWorkflows[idx];
  if (!wf) return;
  steps = JSON.parse(JSON.stringify(wf.steps));
  selectedIdx = -1;
  nextId = (steps.reduce((m, s) => Math.max(m, s.id || 0), 0) || 0) + 1;
  renderSteps();
  $wf("wf-config-body").innerHTML = '<div style="text-align:center;color:#ccc;padding:20px;font-size:13px;">' + _tw("选择一个步骤进行配置", "Select a step to configure") + '</div>';
}

function showLoadDialog() {
  loadWorkflowList();
  if (savedWorkflows.length === 0) {
    alert(_tw("暂无保存的工作流", "No saved workflows"));
    return;
  }
  const names = savedWorkflows.map((w, i) => `${i + 1}. ${w.name}`).join("\n");
  const idx = parseInt(prompt(_tw("选择工作流：\n", "Select workflow:\n") + names)) - 1;
  if (idx >= 0 && idx < savedWorkflows.length) {
    loadWorkflow(idx);
  }
}

// ── 事件绑定 ───────────────────────────────────

function bindWfEvents() {
  $wf("wf-run-btn").onclick = runWorkflow;
  $wf("wf-save-btn").onclick = saveWorkflow;
  $wf("wf-load-btn").onclick = showLoadDialog;
  $wf("wf-clear-btn").onclick = clearSteps;
  $wf("wf-export-btn").onclick = () => {
    const yaml = toYaml();
    if (!yaml) return alert(_tw("没有步骤可导出", "No steps to export"));
    navigator.clipboard.writeText(yaml).then(() => {
      alert("✅ " + _tw("YAML 已复制到剪贴板", "YAML copied to clipboard"));
    });
  };

  // 允许从调色板拖入 canvas
  const canvas = $wf("wf-canvas");
  canvas.ondragover = (e) => e.preventDefault();
  canvas.ondrop = (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData("text/plain");
    if (STEP_TYPES[type]) addStep(type);
  };
}
