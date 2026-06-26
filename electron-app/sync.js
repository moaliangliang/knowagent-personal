/**
 * ZhiXing (知行) 云同步模块
 *
 * 使用 GitHub Gist 作为免费同步后端。
 * 数据: 配置、工作流、待办
 *
 * 使用方法:
 *   1. 生成 GitHub Personal Access Token (需要 gist 权限)
 *   2. 在设置中输入 Token
 *   3. 自动同步或手动触发
 */

const https = require("https");
const fs = require("fs");
const path = require("path");

const GIST_FILENAME = "zhixing-backup.json";
const GIST_DESC = "ZhiXing 跨设备同步";

let _token = "";
let _gistId = "";

// ── 配置管理 ───────────────────────────────────

function getConfigPath(userDataPath) {
  return path.join(userDataPath, "sync-config.json");
}

function loadSyncConfig(userDataPath) {
  try {
    return JSON.parse(fs.readFileSync(getConfigPath(userDataPath), "utf-8"));
  } catch {
    return { token: "", gistId: "", lastSync: null, autoSync: false };
  }
}

function saveSyncConfig(userDataPath, cfg) {
  fs.writeFileSync(getConfigPath(userDataPath), JSON.stringify(cfg, null, 2));
}

// ── 收集同步数据 ───────────────────────────────

function collectData(userDataPath) {
  const data = {};

  // 工作流
  try {
    const wfPath = path.join(userDataPath, "workflows.json");
    if (fs.existsSync(wfPath)) {
      data.workflows = JSON.parse(fs.readFileSync(wfPath, "utf-8"));
    }
  } catch {}

  // 配置
  try {
    const cfgPath = path.join(userDataPath, "config.json");
    if (fs.existsSync(cfgPath)) {
      const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf-8"));
      // 不同步 token
      delete cfg.token;
      data.config = cfg;
    }
  } catch {}

  // 待办
  try {
    const todoPath = path.join(userDataPath, "todos.json");
    if (fs.existsSync(todoPath)) {
      data.todos = JSON.parse(fs.readFileSync(todoPath, "utf-8"));
    }
  } catch {}

  data._meta = {
    version: "0.1.0",
    syncedAt: new Date().toISOString(),
    platform: process.platform,
  };

  return data;
}

// ── GitHub Gist API ────────────────────────────

function gistRequest(method, path, body) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: "api.github.com",
      path: `/gists${path}`,
      method,
      headers: {
        "User-Agent": "ZhiXing",
        "Authorization": `token ${_token}`,
        "Accept": "application/vnd.github.v3+json",
      },
    };

    if (body) {
      opts.headers["Content-Type"] = "application/json";
    }

    const req = https.request(opts, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, data });
        }
      });
    });

    req.on("error", reject);
    req.setTimeout(15000, () => { req.destroy(); reject(new Error("Timeout")); });

    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

// ── 推送到云端 ─────────────────────────────────

async function push(userDataPath) {
  if (!_token) throw new Error("未设置 GitHub Token");

  const payload = {
    description: GIST_DESC,
    public: false,
    files: {
      [GIST_FILENAME]: {
        content: JSON.stringify(collectData(userDataPath), null, 2),
      },
    },
  };

  if (_gistId) {
    // 更新已有 Gist
    const res = await gistRequest("PATCH", `/${_gistId}`, payload);
    if (res.status === 200) return { ok: true, gistId: _gistId };
    throw new Error(`Push 失败 (${res.status})`);
  } else {
    // 创建新 Gist
    const res = await gistRequest("POST", "", payload);
    if (res.status === 201) {
      _gistId = res.data.id;
      return { ok: true, gistId: res.data.id };
    }
    throw new Error(`创建 Gist 失败 (${res.status})`);
  }
}

// ── 从云端拉取 ─────────────────────────────────

async function pull(userDataPath) {
  if (!_token || !_gistId) throw new Error("未配置同步");

  const res = await gistRequest("GET", `/${_gistId}`);
  if (res.status !== 200) throw new Error(`Pull 失败 (${res.status})`);

  const content = res.data.files?.[GIST_FILENAME]?.content;
  if (!content) throw new Error("Gist 内容为空");

  const remote = JSON.parse(content);
  const local = collectData(userDataPath);

  // 合并数据
  if (remote.workflows && (!local.workflows || remote._meta?.syncedAt > local._meta?.syncedAt)) {
    fs.writeFileSync(
      path.join(userDataPath, "workflows.json"),
      JSON.stringify(remote.workflows, null, 2)
    );
  }
  if (remote.todos && (!local.todos || remote._meta?.syncedAt > local._meta?.syncedAt)) {
    fs.writeFileSync(
      path.join(userDataPath, "todos.json"),
      JSON.stringify(remote.todos, null, 2)
    );
  }

  return { ok: true, syncedAt: remote._meta?.syncedAt };
}

// ── 公共 API ───────────────────────────────────

function init(token, gistId) {
  _token = token;
  _gistId = gistId;
}

function getStatus() {
  return {
    configured: !!_token,
    gistId: _gistId || null,
  };
}

function isConfigured() {
  return !!_token;
}

module.exports = { push, pull, init, getStatus, isConfigured, loadSyncConfig, saveSyncConfig };
