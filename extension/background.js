/**
 * Native messaging bridge for Sensitive Upload Guard.
 * Works in Chrome MV3 (service worker) and Firefox (background scripts).
 */

const HOST_NAME = "com.walled.sensitive_upload_guard";
const browserAPI = typeof browser !== "undefined" ? browser : chrome;

function sendNative(message) {
  return new Promise((resolve, reject) => {
    try {
      const port = browserAPI.runtime.connectNative(HOST_NAME);
      let settled = false;

      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          try {
            port.disconnect();
          } catch (_) {}
          reject(new Error("Native host timeout"));
        }
      }, 180000);

      port.onMessage.addListener((response) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        try {
          port.disconnect();
        } catch (_) {}
        resolve(response);
      });

      port.onDisconnect.addListener(() => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        const err =
          (browserAPI.runtime && browserAPI.runtime.lastError && browserAPI.runtime.lastError.message) ||
          "Native host disconnected";
        reject(new Error(err));
      });

      port.postMessage(message);
    } catch (err) {
      reject(err);
    }
  });
}

browserAPI.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || !msg.type) return false;

  if (msg.type === "ping") {
    sendNative({ op: "ping", id: msg.id || "ping" })
      .then((r) => sendResponse({ ok: true, response: r }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }

  if (msg.type === "check_prompt") {
    sendNative({
      op: "check_prompt",
      id: msg.id || `p-${Date.now()}`,
      text: msg.text || "",
    })
      .then((r) => sendResponse({ ok: true, response: r }))
      .catch((e) =>
        sendResponse({
          ok: false,
          error: String(e),
          response: { found: true, decision: "cancel" },
        })
      );
    return true;
  }

  if (msg.type === "check_file") {
    sendNative({
      op: "check_file",
      id: msg.id || `f-${Date.now()}`,
      filename: msg.filename || "upload",
      mime: msg.mime || "",
      data_base64: msg.data_base64 || "",
    })
      .then((r) => sendResponse({ ok: true, response: r }))
      .catch((e) =>
        sendResponse({
          ok: false,
          error: String(e),
          response: { found: true, decision: "cancel" },
        })
      );
    return true;
  }

  return false;
});
