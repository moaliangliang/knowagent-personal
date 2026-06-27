// 知行 (ZhiXing) Service Worker — WebSocket 直连
const WS_URL = "ws://localhost:9510";

let ws = null;
let reconnectTimer = null;
let pending = {};      // requestId -> { resolve, reject, timer }
let reqIdCounter = 0;

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("🟢 ZhiXing WebSocket 已连接");
  };

  ws.onclose = () => {
    console.log("🔴 ZhiXing WebSocket 断开");
    ws = null;
    // 拒绝所有待处理请求
    for (const id of Object.keys(pending)) {
      pending[id].reject("连接已断开");
      clearTimeout(pending[id].timer);
      delete pending[id];
    }
    // 自动重连
    reconnectTimer = setTimeout(connect, 3000);
  };

  ws.onerror = () => {
    if (ws) ws.close();
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const reqId = data.requestId;
      if (reqId && pending[reqId]) {
        clearTimeout(pending[reqId].timer);
        pending[reqId].resolve({ ok: true, data });
        delete pending[reqId];
      }
    } catch (e) {
      console.error("WebSocket 消息解析失败:", e);
    }
  };
}

function sendRequest(payload, timeout = 10000) {
  return new Promise((resolve, reject) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      reject("未连接服务器");
      return;
    }

    const requestId = (++reqIdCounter) + "_" + Date.now().toString(36);
    const message = { ...payload, requestId };

    pending[requestId] = {
      resolve,
      reject,
      timer: setTimeout(() => {
        delete pending[requestId];
        reject("请求超时");
      }, timeout),
    };

    try {
      ws.send(JSON.stringify(message));
    } catch (e) {
      clearTimeout(pending[requestId].timer);
      delete pending[requestId];
      reject("发送失败: " + e.message);
    }
  });
}

// 监听来自 content script 的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "api_call") {
    sendRequest(request.payload)
      .then((r) => sendResponse(r))
      .catch((err) => sendResponse({ ok: false, error: err }));
    return true; // 保持通道打开
  }

  if (request.action === "ping") {
    sendRequest({ action: "ping" })
      .then(() => sendResponse({ ok: true }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
});

// 启动连接
connect();
