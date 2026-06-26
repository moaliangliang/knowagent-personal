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

  // 验证保存的位置是否在当前屏幕内
  let wx = cfg.x;
  let wy = cfg.y;
  if (wx === undefined || wy === undefined || wx < 0 || wy < 0 || wx > display.width || wy > display.height) {
    wx = display.x + display.width - WIN_WIDTH - 20;
    wy = display.y + 80;
  }

  mainWindow = new BrowserWindow({
    width: WIN_WIDTH,
    height: WIN_HEIGHT,
    x: wx,
    y: wy,
    frame: false,
    transparent: true,
    resizable: true,
    alwaysOnTop: cfg.alwaysOnTop !== false,
    skipTaskbar: true,
    show: false,
    minWidth: 320,
    minHeight: 400,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // 淡入效果
  mainWindow.once("ready-to-show", () => {
    mainWindow.setOpacity(0);
    mainWindow.show();
    fadeTo(1, 200);
  });

  // 记录窗口位置
  mainWindow.on("moved", () => {
    const [x, y] = mainWindow.getPosition();
    saveConfig({ x, y });
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

  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }
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
  } else {
    mainWindow.setOpacity(0);
    mainWindow.show();
    fadeTo(1, 200);
    mainWindow.setIgnoreMouseEvents(false, { forward: true });
    mainWindow.webContents.send("focus-input");
  }
}

// ── 系统托盘 ─────────────────────────────────────

function createTray() {
  // 用 Base64 内嵌图标，确保不依赖文件路径
  // 紫色圆形机器人脸图标 (22x22)
  const PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAACTklEQVR4nJ2Vv2/TQBTH3yWdADmLMzR/QQYapFbIDO5f0AxkAMGUAmcJw8jCws7CCEaKKzkLVGJwhvwH8ZCoAqnJ4qFd6VAviVjh0HvxHeeLHal8pad3vh+fe37PdwbLsixAjUWDrEpT4ZJt0wZjXA1s7DoCTYEvBIcLcUR9WzbYIWiXLcuAsi3+/N5Yu5xMDxqHD2jO8mrGCoNdttypihJy4ONnz6nPzRYT9MkogZD7XTnOanWab8JZGVTkESI0dP1DbEewBh+39xB6xcPge+j6TevF/WsC1eqFyFWDv/1UyJkE2l6HgKhsMAdowwGkcIvWJIEaU+vevzKCnQoskKANxsK1d/eEbjAWZEafi0Zr8vUyjbWyaE1l8bwHR7MAbOhRO5f+NlKP+n3yqnh8FBRh+Nq0GlrkWl4MAH4Wz1todq/zU5+vr8eoCfxtOKQKr07OmjwJqBg6NI9ateWzDj8NP8Ov6JyKiYWkVJTJ9jpVQ//gb/AlylUJRrmj2TvdF9rJZSEVNwKnQ89HUMKdfbAhRku48wX77A+qhjcDZ4M5fccIitKFA6NLB32ULibYh2Pb4Mw8wiujgCns9xLbpmS6WaZIbfgR4yHCQ2IWDkVfBR5F/dLBiagn/CWYQF23+3cnp2wN0oW8wiXEanXAXVfRefPO8b1rGRn68KG/8b2yHGpGq1IhpV9AmBIJF2Ld99R7DV8HH0uh5kW09XZbnZw10csNdCEQffXtVnLRN7Ri6hvo0oEyr4W0/u8fRM/nxh9EpaICbm5gqgwoeX8BvC1b/3APEzkAAAAASUVORK5CYII=";

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
  const isPinned = _cfg.alwaysOnTop !== false;

  function togglePin() {
    const newVal = !mainWindow.isAlwaysOnTop();
    mainWindow.setAlwaysOnTop(newVal);
    saveConfig({ alwaysOnTop: newVal });
    tray.setContextMenu(buildMenu(newVal));
  }

  function buildMenu(pinned) {
    return Menu.buildFromTemplate([
      {
        label: t("显示/隐藏", "Show/Hide"),
        accelerator: "CmdOrCtrl+Shift+K",
        click: toggleWindow,
      },
      { type: "separator" },
      {
        label: t("窗口置顶", "Always on Top"),
        type: "checkbox",
        checked: pinned,
        click: togglePin,
      },
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
        label: t("重启后端", "Restart Backend"),
        click: () => {
          stopPythonBackend();
          setTimeout(startPythonBackend, 1000);
        },
      },
      { type: "separator" },
      {
        label: t("退出", "Quit"),
        accelerator: "CmdOrCtrl+Q",
        click: () => { stopPythonBackend(); app.quit(); },
      },
    ]);
  }

  const contextMenu = buildMenu(isPinned);

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

  // 窗口置顶切换
  globalShortcut.register("CommandOrControl+Shift+P", () => {
    if (mainWindow) {
      const newVal = !mainWindow.isAlwaysOnTop();
      mainWindow.setAlwaysOnTop(newVal);
      saveConfig({ alwaysOnTop: newVal });
    }
  });
}

// ── IPC 处理 ────────────────────────────────────

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

// ── 应用生命周期 ─────────────────────────────────

app.whenReady().then(() => {
  // 隐藏 dock 图标（macOS 托盘应用）
  if (process.platform === "darwin") {
    app.dock.hide();
  }

  createTray();
  createWindow();
  registerShortcuts();
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
  stopPythonBackend();
  globalShortcut.unregisterAll();
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
