/** Site-specific selectors for ChatGPT and Perplexity. */

(function (global) {
  const host = location.hostname;

  const isChatGPT =
    host === "chatgpt.com" ||
    host === "chat.openai.com" ||
    host.endsWith(".chatgpt.com");

  const isPerplexity =
    host === "www.perplexity.ai" ||
    host === "perplexity.ai" ||
    host.endsWith(".perplexity.ai");

  const SELECTORS = {
    chatgpt: {
      composer: [
        "#prompt-textarea",
        "div[contenteditable='true']#prompt-textarea",
        "textarea[data-id='root']",
        "form textarea",
        "div.ProseMirror[contenteditable='true']",
      ],
      sendButton: [
        "button[data-testid='send-button']",
        "button[aria-label*='Send']",
        "form button[type='submit']",
      ],
      fileInput: ["input[type='file']"],
      assistant: [
        "[data-message-author-role='assistant']",
        "[data-testid*='assistant']",
        "div[class*='assistant'] .markdown",
      ],
    },
    perplexity: {
      composer: [
        "textarea[placeholder*='Ask']",
        "div[contenteditable='true']",
        "textarea",
      ],
      sendButton: [
        "button[aria-label*='Submit']",
        "button[aria-label*='Send']",
        "button[type='submit']",
      ],
      fileInput: ["input[type='file']"],
      assistant: [
        ".prose",
        "[class*='answer']",
        "[class*='Answer']",
        "[data-testid*='answer']",
        "main .markdown",
      ],
    },
  };

  function firstMatch(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function allMatches(selectors) {
    const out = [];
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => out.push(el));
    }
    return out;
  }

  global.SUG = global.SUG || {};
  global.SUG.site = isChatGPT ? "chatgpt" : isPerplexity ? "perplexity" : "unknown";
  global.SUG.selectors = isChatGPT
    ? SELECTORS.chatgpt
    : isPerplexity
      ? SELECTORS.perplexity
      : SELECTORS.chatgpt;
  global.SUG.firstMatch = firstMatch;
  global.SUG.allMatches = allMatches;
  global.SUG.MARKER = "WALLED_SENSITIVE";
})(window);
