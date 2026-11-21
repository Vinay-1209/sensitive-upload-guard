/** Promise wrapper around extension background ↔ native host. */

(function (global) {
  const browserAPI = typeof browser !== "undefined" ? browser : chrome;

  function send(message) {
    return new Promise((resolve, reject) => {
      try {
        browserAPI.runtime.sendMessage(message, (response) => {
          const err = browserAPI.runtime.lastError;
          if (err) {
            reject(new Error(err.message));
            return;
          }
          resolve(response);
        });
      } catch (e) {
        reject(e);
      }
    });
  }

  async function checkPrompt(text) {
    const res = await send({ type: "check_prompt", text, id: `p-${Date.now()}` });
    const body = (res && res.response) || {};
    if (!res || res.ok === false) {
      return { found: true, decision: "cancel", error: res && res.error };
    }
    return body;
  }

  async function checkFile(filename, mime, dataBase64) {
    const res = await send({
      type: "check_file",
      filename,
      mime,
      data_base64: dataBase64,
      id: `f-${Date.now()}`,
    });
    const body = (res && res.response) || {};
    if (!res || res.ok === false) {
      return { found: true, decision: "cancel", error: res && res.error };
    }
    return body;
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result || "";
        const base64 = String(result).split(",")[1] || "";
        resolve(base64);
      };
      reader.onerror = () => reject(reader.error || new Error("read failed"));
      reader.readAsDataURL(file);
    });
  }

  global.SUG = global.SUG || {};
  global.SUG.checkPrompt = checkPrompt;
  global.SUG.checkFile = checkFile;
  global.SUG.fileToBase64 = fileToBase64;
})(window);
