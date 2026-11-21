/**
 * Native messaging bridge for Sensitive Upload Guard.
 * Uses one-shot sendNativeMessage (more reliable than long-lived ports in MV3).
 */

const HOST_NAME = "com.walled.sensitive_upload_guard";
const browserAPI = typeof browser !== "undefined" ? browser : chrome;

function sendNative(message) {
  return new Promise((resolve, reject) => {
    try {
      if (!browserAPI.runtime.sendNativeMessage) {
        reject(new Error("sendNativeMessage API unavailable"));
        return;
      }
      browserAPI.runtime.sendNativeMessage(HOST_NAME, message, (response) => {
        const err = browserAPI.runtime.lastError;
        if (err) {
          reject(new Error(err.message));
          return;
        }
        resolve(response);
      });
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
