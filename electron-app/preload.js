/**
 * ZhiXing (知行) Desktop — Preload 脚本
 */

const { contextBridge, ipcRenderer } = require("electron");

// Launcher 窗口专用 API
contextBridge.exposeInMainWorld("electronAPI", {
  hideWindow: () => ipcRenderer.invoke("launcher-hide"),
  showResult: (result) => ipcRenderer.invoke("launcher-show-result", result),
});

contextBridge.exposeInMainWorld("ka", {
  // 窗口
  toggle: () => ipcRenderer.invoke("toggle-window"),
  hide: () => ipcRenderer.invoke("hide-window"),

  // 系统
  platform: () => ipcRenderer.invoke("get-platform"),
  lang: () => ipcRenderer.invoke("get-lang"),

  // 事件
  onFocusInput: (cb) => ipcRenderer.on("focus-input", () => cb()),
  onGlobalScreenshot: (cb) => ipcRenderer.on("global-screenshot", () => cb()),
  onLog: (cb) => ipcRenderer.on("log", (_, msg) => cb(msg)),
  onLauncherResult: (cb) => ipcRenderer.on("launcher-result", (_, msg) => cb(msg)),

  // ── 云同步 ──
  syncPush: () => ipcRenderer.invoke("sync-push"),
  syncPull: () => ipcRenderer.invoke("sync-pull"),
  syncSaveToken: (token) => ipcRenderer.invoke("sync-save-token", token),
  syncGetStatus: () => ipcRenderer.invoke("sync-get-status"),

  // ── 自动更新 ──
  updateCheck: () => ipcRenderer.invoke("update-check"),
  updateDownload: () => ipcRenderer.invoke("update-download"),
  onUpdateAvailable: (cb) => ipcRenderer.on("update-available", (_, v) => cb(v)),
  onUpdateProgress: (cb) => ipcRenderer.on("update-progress", (_, p) => cb(p)),
});
