/**
 * Injected by the desktop app (NOT a browser extension).
 * Gates prompts/uploads before transmit; recolors assistant replies.
 */
(function () {
  if (window.__SUG_BOOTED) return;
  window.__SUG_BOOTED = true;

  const host = location.hostname;
  const isChatGPT =
    host === "chatgpt.com" ||
    host === "chat.openai.com" ||
    host.endsWith(".chatgpt.com");
  const isPerplexity =
    host === "www.perplexity.ai" ||
    host === "perplexity.ai" ||
    host.endsWith(".perplexity.ai");
  const isTestHarness =
    host === "127.0.0.1" || host === "localhost" || host === "";

  if (window.top !== window) {
    return; // top frame only
  }

  const site = isChatGPT
    ? "chatgpt"
    : isPerplexity
      ? "perplexity"
      : isTestHarness
        ? "test"
        : "unknown";

  if (site === "unknown") {
    return;
  }

  const SELECTORS = {
    chatgpt: {
      composer: [
        "#prompt-textarea",
        "div.ProseMirror[contenteditable='true']",
        "[contenteditable='true'][aria-label*='Ask ChatGPT' i]",
        "textarea[aria-label*='Ask ChatGPT' i]",
        "textarea[aria-label*='Message' i]",
        "#pending-home-input",
        "form textarea",
        "textarea",
      ],
      sendButton: [
        "button[data-testid='send-button']",
        "button[aria-label='Send message']",
        "button[aria-label*='Send' i]",
        "button[type='submit']",
      ],
      assistant: [
        "[data-message-author-role='assistant']",
        "[data-testid*='assistant-message' i]",
        "[data-testid*='assistant' i] .markdown",
        "div[class*='assistant' i] .markdown",
      ],
    },
    perplexity: {
      composer: [
        "[role='textbox'][contenteditable='true']",
        "[contenteditable='true'][aria-label*='Ask' i]",
        "div[contenteditable='true']",
        "textarea[placeholder*='Ask' i]",
        "textarea",
      ],
      sendButton: [
        "button[aria-label*='Submit' i]",
        "button[aria-label*='Send' i]",
        "button[type='submit']",
        "button[aria-label*='Search' i]",
      ],
      assistant: [
        "[data-testid*='answer' i]",
        "[class*='answer' i] .prose",
        "main .prose",
        "[class*='markdown' i]",
      ],
    },
    test: {
      composer: ["#composer", "textarea"],
      sendButton: ["#send-btn", "button[type='submit']"],
      assistant: [".assistant-reply", "#assistant"],
    },
  };

  const selectors = SELECTORS[site];
  const MARKER = "WALLED_SENSITIVE";
  const CLASS = "sug-ai-response";
  const COLOR = "#0b6e4f";

  window.SUG = {
    site,
    selectors,
    MARKER,
    firstMatch(sels) {
      for (const sel of sels || []) {
        try {
          const el = document.querySelector(sel);
          if (el) return el;
        } catch (_) {}
      }
      return null;
    },
  };

  async function callPython(payload) {
    if (typeof window.__sug_check !== "function") {
      console.error("[SUG] binding missing — fail closed");
      return { ok: false, found: true, decision: "cancel", error: "binding missing" };
    }
    try {
      return await window.__sug_check(payload);
    } catch (e) {
      console.error("[SUG] binding error", e);
      return { ok: false, found: true, decision: "cancel", error: String(e) };
    }
  }

  window.SUG.checkPrompt = (text) => callPython({ kind: "check_prompt", text });
  window.SUG.checkFile = (filename, mime, data_base64) =>
    callPython({ kind: "check_file", filename, mime, data_base64 });

  window.SUG.fileToBase64 = function (file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result || "";
        resolve(String(result).split(",")[1] || "");
      };
      reader.onerror = () => reject(reader.error || new Error("read failed"));
      reader.readAsDataURL(file);
    });
  };

  function readEditable(el) {
    if (!el) return "";
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") return el.value || "";
    if (el.isContentEditable || el.getAttribute("contenteditable") === "true") {
      return el.innerText || el.textContent || "";
    }
    return "";
  }

  function getComposerText() {
    for (const sel of selectors.composer || []) {
      try {
        const el = document.querySelector(sel);
        const text = readEditable(el);
        if (text && text.trim()) return text;
        if (el) return text;
      } catch (_) {}
    }
    return readEditable(document.activeElement);
  }

  let checking = false;
  let allowNextSubmit = false;
  let allowNextFileChange = false;
  const approvedFiles = new WeakSet();

  async function approvePromptOrBlock() {
    const text = getComposerText();
    if (!text.includes(MARKER)) return true;
    const result = await window.SUG.checkPrompt(text);
    return result && result.decision === "continue";
  }

  async function onSubmitAttempt(event) {
    if (allowNextSubmit) {
      allowNextSubmit = false;
      return;
    }
    if (checking) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return;
    }

    const text = getComposerText();
    if (!text.includes(MARKER)) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    checking = true;
    let ok = false;
    try {
      ok = await approvePromptOrBlock();
    } finally {
      checking = false;
    }
    if (!ok) return;

    allowNextSubmit = true;
    const target = event.target;
    if (event.type === "keydown") {
      const el = document.activeElement || target;
      el.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "Enter",
          code: "Enter",
          keyCode: 13,
          which: 13,
          bubbles: true,
          cancelable: true,
        })
      );
    } else {
      const btn =
        (target && target.closest && target.closest("button, [role='button']")) ||
        window.SUG.firstMatch(selectors.sendButton);
      if (btn && typeof btn.click === "function") {
        btn.click();
      } else {
        const form = (target && target.closest && target.closest("form")) || null;
        if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
      }
    }
  }

  function isSendControl(el) {
    if (!el) return false;
    const btn = el.closest ? el.closest("button, [role='button'], input[type='submit']") : el;
    if (!btn) return false;
    const isSend = (selectors.sendButton || []).some((sel) => {
      try {
        return btn.matches(sel);
      } catch (_) {
        return false;
      }
    });
    const label = `${btn.getAttribute("aria-label") || ""} ${btn.getAttribute("data-testid") || ""} ${btn.id || ""} ${btn.textContent || ""}`.toLowerCase();
    return isSend || /send|submit/.test(label);
  }

  function installPromptHooks() {
    document.addEventListener(
      "keydown",
      (e) => {
        if (e.key !== "Enter" || e.shiftKey) return;
        const active = document.activeElement;
        if (!active) return;
        const inComposer =
          active.matches &&
          selectors.composer.some((sel) => {
            try {
              return active.matches(sel) || !!active.closest(sel);
            } catch (_) {
              return false;
            }
          });
        if (!inComposer && !active.isContentEditable && active.tagName !== "TEXTAREA") {
          return;
        }
        onSubmitAttempt(e);
      },
      true
    );

    const onPointerOrClick = (e) => {
      if (!isSendControl(e.target)) return;
      onSubmitAttempt(e);
    };
    document.addEventListener("pointerdown", onPointerOrClick, true);
    document.addEventListener("click", onPointerOrClick, true);
    document.addEventListener("submit", (e) => onSubmitAttempt(e), true);
  }

  async function gateFileList(fileList) {
    const files = Array.from(fileList || []);
    for (const file of files) {
      if (approvedFiles.has(file)) continue;
      let b64;
      try {
        b64 = await window.SUG.fileToBase64(file);
      } catch (e) {
        console.error("[SUG] file read failed", e);
        return false;
      }
      let result;
      try {
        result = await window.SUG.checkFile(file.name, file.type || "", b64);
      } catch (e) {
        console.error("[SUG] file check failed", e);
        return false;
      }
      if (result.found && result.decision !== "continue") return false;
      approvedFiles.add(file);
    }
    return true;
  }

  function clearInput(input) {
    try {
      input.value = "";
    } catch (_) {}
  }

  function installFileHooks() {
    const pending = new WeakMap();

    document.addEventListener(
      "change",
      (e) => {
        const input = e.target;
        if (!input || input.type !== "file" || !input.files || !input.files.length) return;
        if (allowNextFileChange) {
          allowNextFileChange = false;
          return;
        }
        const files = Array.from(input.files);
        if (files.every((f) => approvedFiles.has(f))) return;
        if (pending.get(input)) {
          e.stopImmediatePropagation();
          e.preventDefault();
          return;
        }
        e.stopImmediatePropagation();
        e.preventDefault();
        pending.set(input, true);
        (async () => {
          try {
            const ok = await gateFileList(files);
            if (!ok) {
              clearInput(input);
              return;
            }
            allowNextFileChange = true;
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } finally {
            pending.delete(input);
          }
        })();
      },
      true
    );

    document.addEventListener(
      "drop",
      (e) => {
        const dt = e.dataTransfer;
        if (!dt || !dt.files || !dt.files.length) return;
        const files = Array.from(dt.files);
        if (files.every((f) => approvedFiles.has(f))) return;
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        (async () => {
          const ok = await gateFileList(files);
          if (!ok) return;
          const input = document.querySelector("input[type='file']");
          if (!input) return;
          try {
            const transfer = new DataTransfer();
            files.forEach((f) => {
              approvedFiles.add(f);
              transfer.items.add(f);
            });
            input.files = transfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } catch (err) {
            console.warn("[SUG] could not re-attach dropped files", err);
          }
        })();
      },
      true
    );

    document.addEventListener(
      "paste",
      (e) => {
        const items = e.clipboardData && e.clipboardData.items;
        if (!items) return;
        const files = [];
        for (const item of items) {
          if (item.kind === "file") {
            const f = item.getAsFile();
            if (f) files.push(f);
          }
        }
        if (!files.length) return;
        if (files.every((f) => approvedFiles.has(f))) return;
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        (async () => {
          const ok = await gateFileList(files);
          if (!ok) return;
          const input = document.querySelector("input[type='file']");
          if (!input) return;
          try {
            const transfer = new DataTransfer();
            files.forEach((f) => {
              approvedFiles.add(f);
              transfer.items.add(f);
            });
            input.files = transfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } catch (err) {
            console.warn("[SUG] could not re-attach pasted files", err);
          }
        })();
      },
      true
    );
  }

  function injectColorStyles() {
    const css = `.${CLASS}, .${CLASS} * { color: ${COLOR} !important; }`;
    try {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(css);
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
    } catch (_) {
      const style = document.createElement("style");
      style.textContent = css;
      (document.head || document.documentElement).appendChild(style);
    }
  }

  function paint(root) {
    for (const sel of selectors.assistant || []) {
      try {
        root.querySelectorAll(sel).forEach((el) => {
          if (!el.classList.contains(CLASS)) {
            el.classList.add(CLASS);
            try {
              el.style.setProperty("color", COLOR, "important");
            } catch (_) {}
          }
        });
      } catch (_) {}
    }
  }

  function installColor() {
    injectColorStyles();
    paint(document);
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "childList") {
          m.addedNodes.forEach((n) => {
            if (n.nodeType === 1) paint(n);
          });
        }
      }
      paint(document);
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
  }

  function showActiveBadge() {
    if (document.getElementById("sug-active-badge")) return;
    const badge = document.createElement("div");
    badge.id = "sug-active-badge";
    badge.textContent = "SUG active";
    badge.title = "Sensitive Upload Guard desktop app is monitoring this page";
    Object.assign(badge.style, {
      position: "fixed",
      zIndex: "2147483647",
      right: "12px",
      bottom: "12px",
      background: COLOR,
      color: "#fff",
      font: "600 12px system-ui,sans-serif",
      padding: "6px 10px",
      borderRadius: "999px",
      boxShadow: "0 2px 8px rgba(0,0,0,.25)",
      pointerEvents: "none",
    });
    document.documentElement.appendChild(badge);
  }

  function boot() {
    console.info("[SUG] desktop inject active on", site);
    showActiveBadge();
    installPromptHooks();
    installFileHooks();
    installColor();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
