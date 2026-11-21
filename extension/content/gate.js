/**
 * Intercept prompt submits and file attachments before they leave the page.
 * Clean content passes through; WALLED_SENSITIVE triggers native Continue/Cancel.
 */

(function () {
  const MARKER = (window.SUG && window.SUG.MARKER) || "WALLED_SENSITIVE";
  let checking = false;
  let allowNextSubmit = false;
  let allowNextFileChange = false;
  const approvedFiles = new WeakSet();

  function readEditable(el) {
    if (!el) return "";
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
      return el.value || "";
    }
    if (el.isContentEditable || el.getAttribute("contenteditable") === "true") {
      return el.innerText || el.textContent || "";
    }
    return "";
  }

  function getComposerText() {
    const sels = (window.SUG.selectors && window.SUG.selectors.composer) || [];
    for (const sel of sels) {
      try {
        const el = document.querySelector(sel);
        const text = readEditable(el);
        if (text && text.trim()) return text;
        if (el) return text;
      } catch (_) {}
    }
    return readEditable(document.activeElement);
  }

  async function approvePromptOrBlock() {
    const text = getComposerText();
    if (!text.includes(MARKER)) {
      return true;
    }
    try {
      const result = await window.SUG.checkPrompt(text);
      return result && result.decision === "continue";
    } catch (e) {
      console.error("[SUG] prompt check failed", e);
      return false;
    }
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
    if (!text.includes(MARKER)) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    // Lock immediately so pointerdown+click do not double-open dialogs.
    checking = true;
    let ok = false;
    try {
      ok = await approvePromptOrBlock();
    } finally {
      checking = false;
    }
    if (!ok) {
      return;
    }
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
        window.SUG.firstMatch(window.SUG.selectors.sendButton);
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
    const isSend = (window.SUG.selectors.sendButton || []).some((sel) => {
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
          window.SUG.selectors.composer.some((sel) => {
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

    // pointerdown catches SPAs that stop click; click remains as fallback
    const onPointerOrClick = (e) => {
      if (!isSendControl(e.target)) return;
      onSubmitAttempt(e);
    };
    document.addEventListener("pointerdown", onPointerOrClick, true);
    document.addEventListener("click", onPointerOrClick, true);

    document.addEventListener(
      "submit",
      (e) => {
        onSubmitAttempt(e);
      },
      true
    );
  }

  async function gateFileList(fileList) {
    const files = Array.from(fileList || []);
    for (const file of files) {
      if (approvedFiles.has(file)) continue;
      // Fast path: no marker in name and tiny text peek not applicable — always scan via host for PDF/images.
      // For speed on large files, still send to host (assignment requires inspection).
      let b64;
      try {
        b64 = await window.SUG.fileToBase64(file);
      } catch (e) {
        console.error("[SUG] file read failed", e);
        return false;
      }
      // Quick client-side text check for .txt before native round-trip when possible
      let result;
      try {
        result = await window.SUG.checkFile(file.name, file.type || "", b64);
      } catch (e) {
        console.error("[SUG] file check failed", e);
        return false;
      }
      if (result.found && result.decision !== "continue") {
        return false;
      }
      if (!result.found || result.decision === "continue") {
        approvedFiles.add(file);
      }
    }
    return true;
  }

  function clearInput(input) {
    try {
      input.value = "";
    } catch (_) {}
  }

  function installFileHooksV2() {
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
          // After approval, synthesize a drop is hard; attach via nearest file input if present.
          const input = document.querySelector("input[type='file']");
          if (input) {
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
          if (input) {
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
          }
        })();
      },
      true
    );
  }

  function showActiveBadge() {
    if (document.getElementById("sug-active-badge")) return;
    const badge = document.createElement("div");
    badge.id = "sug-active-badge";
    badge.textContent = "SUG active";
    badge.title = "Sensitive Upload Guard is monitoring this page";
    Object.assign(badge.style, {
      position: "fixed",
      zIndex: "2147483647",
      right: "12px",
      bottom: "12px",
      background: "#0b6e4f",
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
    if (window.SUG.site === "unknown") {
      console.info("[SUG] unsupported site");
      return;
    }
    console.info("[SUG] active on", window.SUG.site);
    showActiveBadge();
    installPromptHooks();
    installFileHooksV2();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
