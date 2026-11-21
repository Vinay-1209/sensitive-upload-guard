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

  function getComposerText() {
    const sels = window.SUG.selectors.composer;
    for (const sel of sels) {
      const el = document.querySelector(sel);
      if (!el) continue;
      if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
        return el.value || "";
      }
      if (el.isContentEditable) {
        return el.innerText || el.textContent || "";
      }
    }
    // Fallback: focused editable
    const active = document.activeElement;
    if (active) {
      if (active.tagName === "TEXTAREA" || active.tagName === "INPUT") {
        return active.value || "";
      }
      if (active.isContentEditable) {
        return active.innerText || active.textContent || "";
      }
    }
    return "";
  }

  async function approvePromptOrBlock() {
    const text = getComposerText();
    if (!text.includes(MARKER)) {
      return true;
    }
    checking = true;
    try {
      const result = await window.SUG.checkPrompt(text);
      return result && result.decision === "continue";
    } catch (e) {
      console.error("[SUG] prompt check failed", e);
      return false;
    } finally {
      checking = false;
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

    const ok = await approvePromptOrBlock();
    if (!ok) {
      return;
    }
    allowNextSubmit = true;
    // Re-trigger the original action after approval.
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
    } else if (target && typeof target.click === "function" && target.tagName === "BUTTON") {
      target.click();
    } else {
      const form = (target && target.closest && target.closest("form")) || null;
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    }
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
              return active.matches(sel) || active.closest(sel);
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

    document.addEventListener(
      "click",
      (e) => {
        const btn = e.target && e.target.closest && e.target.closest("button");
        if (!btn) return;
        const isSend = window.SUG.selectors.sendButton.some((sel) => {
          try {
            return btn.matches(sel);
          } catch (_) {
            return false;
          }
        });
        // Heuristic: aria-label / data-testid containing send/submit
        const label = `${btn.getAttribute("aria-label") || ""} ${btn.getAttribute("data-testid") || ""}`.toLowerCase();
        if (!isSend && !/send|submit/.test(label)) return;
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

  function boot() {
    if (window.SUG.site === "unknown") {
      console.info("[SUG] unsupported site");
      return;
    }
    console.info("[SUG] active on", window.SUG.site);
    installPromptHooks();
    installFileHooksV2();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
