/**
 * ZhiXing (知行) Desktop — Electron 主进程 v2
 *
 * 功能：
 *   - 系统托盘 + 透明浮窗
 *   - 全局快捷键 (Cmd+Shift+K / Cmd+Shift+Esc)
 *   - Python 后端自动管理
 *   - 窗口位置记忆
 *   - 淡入淡出动画
 *   - 开机自启
 *   - 中英文自动适配
 */

const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage, screen, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

// ── 自动更新 ───────────────────────────────────

let updateChecker = null;
try {
  const { autoUpdater } = require("electron-updater");
  autoUpdater.autoDownload = false;
  autoUpdater.setFeedURL({
    provider: "github",
    owner: "zhixing-ai",
    repo: "zhixing",
  });

  autoUpdater.on("update-available", (info) => {
    const win = BrowserWindow.getAllWindows()[0];
    if (win) win.webContents.send("update-available", info.version);
  });

  autoUpdater.on("download-progress", (p) => {
    const win = BrowserWindow.getAllWindows()[0];
    if (win) win.webContents.send("update-progress", Math.round(p.percent));
  });

  autoUpdater.on("update-downloaded", () => {
    dialog.showMessageBox({
      type: "info",
      title: "ZhiXing",
      message: t("新版本已下载，是否立即重启安装？", "Update downloaded. Restart now?"),
      buttons: [t("重启", "Restart"), t("稍后", "Later")],
    }).then(({ response }) => {
      if (response === 0) autoUpdater.quitAndInstall();
    });
  });

  updateChecker = autoUpdater;
} catch (e) {
  console.log("[AutoUpdate] 未启用 (electron-updater 未安装)");
}

// ── 云同步 ─────────────────────────────────────

const sync = require("./sync");

// ── 常量 ─────────────────────────────────────────

const PYTHON_SERVER = fs.existsSync("/tmp/ka_proxy.py")
  ? "/tmp/ka_proxy.py"
  : path.join(__dirname, "..", "chrome-extension", "server.py");
const isDev = process.env.NODE_ENV === "development";

// 窗口配置
const WIN_WIDTH = 420;
const WIN_HEIGHT = 600;

let mainWindow = null;
let launcherWindow = null;
let floatBtn = null;
let tray = null;
let pythonProcess = null;

// ── i18n ─────────────────────────────────────────

const isCN = app.getLocale().startsWith("zh");

function t(zh, en) {
  return isCN ? zh : en;
}

// ── 配置持久化 ──────────────────────────────────

const CONFIG_PATH = path.join(app.getPath("userData"), "config.json");

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf-8"));
  } catch {
    return { x: undefined, y: undefined, autoStart: false };
  }
}

function saveConfig(data) {
  try {
    const cfg = { ...loadConfig(), ...data };
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg));
  } catch (e) {
    console.error("保存配置失败:", e.message);
  }
}

// ── Python 后端管理 ──────────────────────────────

function startPythonBackend() {
  // 端口冲突检测：如果 9510 已被占用，不再重复启动
  const { execSync } = require("child_process");
  try {
    const existing = execSync(`lsof -ti :9510 2>/dev/null`, { encoding: "utf-8", timeout: 5000 }).trim();
    if (existing) {
      console.log(`[Python] 端口 9510 已被占用(PID ${existing})，跳过启动`);
      return;
    }
  } catch (e) { /* lsof 未找到进程，正常 */ }

  const pythonCmd = process.platform === "win32" ? "python" : "python3";
  try {
    pythonProcess = spawn(pythonCmd, [PYTHON_SERVER], {
      cwd: path.dirname(PYTHON_SERVER),
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, ZHIXING_PRO: "1" },
    });
    pythonProcess.stdout.on("data", (d) => console.log(`[Python] ${d}`));
    pythonProcess.stderr.on("data", (d) => console.error(`[Python] ${d}`));
    pythonProcess.on("close", (code) => {
      console.log(`[Python] 退出: ${code}`);
      pythonProcess = null;
    });
  } catch (e) {
    console.error("[Python] 启动失败:", e.message);
  }
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// ── 窗口管理 ─────────────────────────────────────

function createWindow() {
  const cfg = loadConfig();
  const display = screen.getPrimaryDisplay().workArea;

  // 验证保存的位置是否在当前屏幕内，默认靠右
  let wx = cfg.x;
  let wy = cfg.y;
  if (wx === undefined || wy === undefined || wx < 0 || wy < 0 || wx > display.width || wy > display.height) {
    wx = display.x + display.width - WIN_WIDTH - 20;
    wy = display.y + Math.floor((display.height - WIN_HEIGHT) / 3);
  }

  mainWindow = new BrowserWindow({
    width: WIN_WIDTH,
    height: WIN_HEIGHT,
    x: wx,
    y: wy,
    frame: false,
    transparent: false,
    backgroundColor: "#1a1a2e",
    resizable: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: true,     // 启动时直接显示（不再依赖 ready-to-show 事件）
    minWidth: 320,
    minHeight: 400,
    maxWidth: 520,
    maxHeight: 900,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // 在所有桌面空间可见（切换 Space 不丢失）
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // 默认显示 + 淡入效果
  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.setAlwaysOnTop(true, "floating");
    fadeTo(1, 200);
  });

  // 窗口隐藏或最小化时显示浮动按钮
  mainWindow.on("hide", () => {
    if (floatBtn && !floatBtn.isDestroyed()) {
      floatBtn.show();
      floatBtn.setAlwaysOnTop(true, "screen-saver");
    }
  });
  mainWindow.on("minimize", () => {
    if (floatBtn && !floatBtn.isDestroyed()) {
      floatBtn.show();
      floatBtn.setAlwaysOnTop(true, "screen-saver");
    }
  });

  // 记录窗口位置
  mainWindow.on("moved", () => {
    const [x, y] = mainWindow.getPosition();
    saveConfig({ x, y });
  });

  // 每次窗口获得焦点时重新确保置顶（修复 alwaysOnTop 有时丢失的问题）
  mainWindow.on("focus", () => {
    mainWindow.setAlwaysOnTop(true, "floating");
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  });

  // 初始化云同步
  const syncCfg = sync.loadSyncConfig(app.getPath("userData"));
  if (syncCfg.token) {
    sync.init(syncCfg.token, syncCfg.gistId || "");
    if (syncCfg.autoSync) {
      // 启动时拉取
      sync.pull(app.getPath("userData")).then(() => {
        mainWindow?.webContents.send("log", t("云同步已更新", "Cloud sync updated"));
      }).catch(() => {});
    }
  }

  // ── 浮动按钮 ─────────────────────────────
  createFloatBtn();

  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }
}

// ── 全局浮动按钮 ─────────────────────────────

const BTN_SIZE = 42;

function createFloatBtn() {
  if (floatBtn) return;
  const display = screen.getPrimaryDisplay().workArea;

  floatBtn = new BrowserWindow({
    width: BTN_SIZE,
    height: BTN_SIZE,
    x: display.x + display.width - BTN_SIZE - 20,
    y: Math.floor(display.y + display.height / 2),
    frame: false,
    transparent: true,
    skipTaskbar: true,
    show: false,
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 用原生 macOS 窗口级别确保在所有应用之上
  floatBtn.setAlwaysOnTop(true, "screen-saver");

  floatBtn.loadURL(`data:text/html,
    <!DOCTYPE html>
    <html>
    <head><style>
      * { margin:0; padding:0; box-sizing:border-box; user-select:none;
          -webkit-app-region: no-drag; }
      body {
        width: ${BTN_SIZE}px; height: ${BTN_SIZE}px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(0,180,255,0.15);
        border-radius: 50%;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(0,180,255,0.3);
        cursor: pointer;
        transition: all 0.2s;
        font-size: 20px;
      }
      body:hover { background: rgba(0,180,255,0.3); transform: scale(1.1); }
      body:active { transform: scale(0.95); }
    </style></head>
    <body><img id="float-icon" style="width:32px;height:32px;border-radius:50%;" src="data:image/png;base64,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" /></body>
    <script>
      document.body.onclick = () => {
        window.electronAPI && window.electronAPI.toggleMainWindow();
      };
    </script>
    </html>`);

  floatBtn.on("blur", () => {});
  floatBtn.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  floatBtn.setIgnoreMouseEvents(false);
  floatBtn.show();
}

// ── Launcher 窗口 ────────────────────────────

function toggleLauncher() {
  if (!launcherWindow) {
    launcherWindow = new BrowserWindow({
      width: 520,
      height: 80,
      frame: false,
      transparent: true,
      resizable: false,
      alwaysOnTop: true,
      skipTaskbar: true,
      show: false,
      webPreferences: {
        preload: path.join(__dirname, "preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    launcherWindow.loadFile(path.join(__dirname, "renderer", "launcher.html"));

    // 失去焦点自动关闭
    launcherWindow.on("blur", () => {
      launcherWindow.hide();
    });

    launcherWindow.on("close", (e) => {
      if (!app.isQuitting) {
        e.preventDefault();
        launcherWindow.hide();
      }
    });
  }

  if (launcherWindow.isVisible()) {
    launcherWindow.hide();
  } else {
    // 居中显示
    const cursor = screen.getCursorScreenPoint();
    const display = screen.getDisplayNearestPoint(cursor);
    const bounds = display.workArea;
    launcherWindow.setPosition(
      bounds.x + (bounds.width - 520) / 2,
      bounds.y + bounds.height * 0.2
    );
    launcherWindow.show();
    launcherWindow.webContents.send("focus-input");
    launcherWindow.focus();
  }
}

function fadeTo(opacity, duration = 150) {
  if (!mainWindow) return;
  const steps = 8;
  const step = (opacity - (mainWindow.getOpacity() || 0)) / steps;
  const interval = duration / steps;
  let i = 0;
  const timer = setInterval(() => {
    i++;
    const current = mainWindow.getOpacity() || 0;
    mainWindow.setOpacity(Math.min(1, Math.max(0, current + step)));
    if (i >= steps) {
      clearInterval(timer);
      mainWindow.setOpacity(opacity);
    }
  }, interval);
}

function toggleWindow() {
  if (!mainWindow) return;
  if (mainWindow.isVisible()) {
    fadeTo(0, 120);
    setTimeout(() => mainWindow.hide(), 120);
    if (floatBtn && !floatBtn.isDestroyed()) { floatBtn.show(); floatBtn.setAlwaysOnTop(true, "screen-saver"); }
  } else {
    if (floatBtn && !floatBtn.isDestroyed()) floatBtn.hide();
    mainWindow.setOpacity(0);
    mainWindow.show();
    fadeTo(1, 200);
    mainWindow.setIgnoreMouseEvents(false, { forward: true });
    mainWindow.webContents.send("focus-input");
  }
}

// ── 系统托盘 ─────────────────────────────────────

function createTray() {
  // 用 Base64 内嵌统一品牌图标（紫色渐变圆 + 白「知」）
  const PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAABwElEQVR4nM2Vv0scQRTHPyspxE475fA/OOwEUwQC11gIwQgWIkiIRo2emlMJCOkEQcUfCaiJxYEoCDEE0h4ICgoWgmgjKQJBIlic3WExbyNv9c7du931XBD8wjDLzLzPvnnz3gw8BfV8uih7rRUKmvhXC7wA4kAMqAJywBlwDOx8naw7Lxv87uNf7bqA10ACqPRZdgVkgC0gvTJVH76F/xHVO/6nOhDal/odGaxS+7wqPHGxRbcfSe8/nGbd9gVwf/KkFjEa02gSU6P2Dgd4duet0dNPDAwehdp/+dxQMqY2t1mgB62czYLHlkjcEqm0RAhqftDB/kP3GrWPF3scC/JycbnRdzzZe+CXr7ECOPl2D0Q0+Uu08K3JFzrUvR9UXQ7HCcXi6nMNfg4xuFsg9M2uZ11RyxWH4iz/PZ9+6e8LMNy1HX4P3JS7CyyitX81t5bwK1/u++lIZyZf5seePLZss2PZxpmNIss22jLK8YDnNprPLZGtyGCRrNorxwN2ZJs0UWWbJbd9yTmkWr/rLZXSOwmoKQOZBZaA2dkfbZeBYIDRV5vaPeg+nvnZ7pkMzZyxlvV7X5DpXx2+L8ij6RoWCTMaKGk+pgAAAABJRU5ErkJggg==";

  let trayImage;

  if (process.platform === "darwin") {
    trayImage = nativeImage.createFromDataURL("data:image/png;base64," + PNG_BASE64);
  } else if (process.platform === "win32") {
    trayImage = nativeImage.createFromPath(path.join(__dirname, "build", "tray.ico"));
  } else {
    trayImage = nativeImage.createFromPath(path.join(__dirname, "build", "tray.png"));
  }

  console.log("[Tray] 图标大小:", trayImage.getSize());
  tray = new Tray(trayImage);
  tray.setToolTip("ZhiXing");

  const _cfg = loadConfig();
  const isAutoStart = _cfg.autoStart || false;

  function buildMenu() {
    return Menu.buildFromTemplate([
      {
        label: t("显示/隐藏", "Show/Hide"),
        accelerator: "CmdOrCtrl+Shift+K",
        click: toggleWindow,
      },
      { type: "separator" },
      {
        label: t("开机自启", "Launch at Login"),
        type: "checkbox",
        checked: isAutoStart,
        click: (item) => {
          app.setLoginItemSettings({ openAtLogin: item.checked });
          saveConfig({ autoStart: item.checked });
        },
      },
      { type: "separator" },
      {
        label: t("重启应用", "Restart App"),
        click: () => { app.relaunch(); app.quit(); },
      },
      { type: "separator" },
      {
        label: t("退出", "Quit"),
        accelerator: "CmdOrCtrl+Q",
        click: () => { stopPythonBackend(); app.quit(); },
      },
    ]);
  }

  const contextMenu = buildMenu();

  tray.setContextMenu(contextMenu);
  tray.on("click", toggleWindow);
}

// ── 全局快捷键 ───────────────────────────────────

function registerShortcuts() {
  // 主窗口切换
  globalShortcut.register("CommandOrControl+Shift+K", toggleWindow);

  // 截图
  globalShortcut.register("CommandOrControl+Shift+Escape", () => {
    if (mainWindow) mainWindow.webContents.send("global-screenshot");
  });

  // 快速启动器
  globalShortcut.register("CommandOrControl+Space", toggleLauncher);

  // 窗口置顶已禁用（alwaysOnTop: false）
}

// ── IPC 处理 ────────────────────────────────────

// ── 命令执行 ─── 渲染进程通过 WebSocket 直连 server.py，不再走 IPC ──

ipcMain.handle("launcher-hide", () => {
  if (launcherWindow) launcherWindow.hide();
});

ipcMain.handle("launcher-show-result", (event, result) => {
  // 主窗口显示结果
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send("launcher-result", result);
  }
  // 关闭 launcher
  if (launcherWindow) launcherWindow.hide();
});

ipcMain.handle("toggle-window", () => toggleWindow());
ipcMain.handle("hide-window", () => {
  if (mainWindow) {
    fadeTo(0, 100);
    setTimeout(() => {
      mainWindow.hide();
      if (floatBtn && !floatBtn.isDestroyed()) {
        floatBtn.show();
        floatBtn.setAlwaysOnTop(true, "screen-saver");
      }
    }, 100);
  }
});

ipcMain.handle("hide-window-nofloat", () => {
  if (mainWindow) {
    fadeTo(0, 100);
    setTimeout(() => mainWindow.hide(), 100);
  }
});
ipcMain.handle("get-platform", () => process.platform);
ipcMain.handle("get-lang", () => isCN ? "zh" : "en");

// ── 云同步 IPC ────────────────────────────────

ipcMain.handle("sync-push", async () => {
  try {
    const result = await sync.push(app.getPath("userData"));
    // 保存 gistId
    const cfg = sync.loadSyncConfig(app.getPath("userData"));
    cfg.gistId = result.gistId;
    cfg.lastSync = new Date().toISOString();
    sync.saveSyncConfig(app.getPath("userData"), cfg);
    return { ok: true, gistId: result.gistId };
  } catch (e) {
    return { ok: false, error: e.message };
  }
});

ipcMain.handle("sync-pull", async () => {
  try {
    const result = await sync.pull(app.getPath("userData"));
    return { ok: true, syncedAt: result.syncedAt };
  } catch (e) {
    return { ok: false, error: e.message };
  }
});

ipcMain.handle("sync-save-token", (event, token) => {
  const cfg = sync.loadSyncConfig(app.getPath("userData"));
  cfg.token = token;
  cfg.autoSync = true;
  sync.saveSyncConfig(app.getPath("userData"), cfg);
  sync.init(token, cfg.gistId || "");
  return { ok: true };
});

ipcMain.handle("sync-get-status", () => {
  const cfg = sync.loadSyncConfig(app.getPath("userData"));
  return { token: !!cfg.token, gistId: cfg.gistId, lastSync: cfg.lastSync, autoSync: cfg.autoSync };
});

// ── 自动更新 IPC ──────────────────────────────

ipcMain.handle("update-check", async () => {
  try {
    if (updateChecker) {
      updateChecker.checkForUpdates();
      return { ok: true };
    }
    return { ok: false, error: "auto-updater 未安装" };
  } catch (e) {
    return { ok: false, error: e.message };
  }
});

ipcMain.handle("update-download", () => {
  try {
    if (updateChecker) {
      updateChecker.downloadUpdate();
      return { ok: true };
    }
    return { ok: false };
  } catch (e) {
    return { ok: false };
  }
});

// 窗口拖动
ipcMain.handle("move-window", (event, dx, dy) => {
  if (!mainWindow) return;
  const [x, y] = mainWindow.getPosition();
  mainWindow.setPosition(x + dx, y + dy);
});

// ── 应用生命周期 ─────────────────────────────────

app.whenReady().then(() => {
  // 隐藏 dock 图标（macOS 托盘应用）
  if (process.platform === "darwin") {
    app.dock.hide();
  }

  createTray();
  createWindow();
  registerShortcuts();
  // 启动 Python WebSocket 后端（端口检测防冲突）
  // Chrome 扩展和 Electron 渲染进程共用同一后端
  startPythonBackend();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
    else toggleWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (floatBtn) { floatBtn.destroy(); floatBtn = null; }
  globalShortcut.unregisterAll();
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
