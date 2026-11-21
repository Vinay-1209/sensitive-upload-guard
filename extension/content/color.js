/** Recolor AI-generated responses on ChatGPT and Perplexity. */

(function () {
  const CLASS = "sug-ai-response";

  function paint(root) {
    const sels = (window.SUG && window.SUG.selectors && window.SUG.selectors.assistant) || [];
    for (const sel of sels) {
      root.querySelectorAll(sel).forEach((el) => {
        if (!el.classList.contains(CLASS)) {
          el.classList.add(CLASS);
        }
      });
    }
  }

  function start() {
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
