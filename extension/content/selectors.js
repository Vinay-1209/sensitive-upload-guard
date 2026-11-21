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

  const isTestHarness =
    host === "127.0.0.1" ||
    host === "localhost" ||
    host === "";

  const SELECTORS = {
    chatgpt: {
      composer: [
        "#prompt-textarea",
        "#mobile-composer-prompt",
        "textarea[placeholder*='Ask ChatGPT' i]",
        "textarea[aria-label*='Chat with ChatGPT' i]",
        "textarea[aria-label*='Message' i]",
        "div[contenteditable='true']#prompt-textarea",
        "div.ProseMirror[contenteditable='true']",
        "form textarea",
        "textarea",
      ],
      sendButton: [
        "button[data-testid='send-button']",
        "button[aria-label='Send message']",
        "button[aria-label*='Send' i]",
        "button[type='submit']",
        "form button[type='submit']",
      ],
      fileInput: [
        "input[type='file']",
        "#octane-mobile-composer-photos-input",
      ],
      assistant: [
        "[data-message-author-role='assistant']",
        "[data-testid*='assistant' i]",
        "article[data-testid*='conversation-turn']",
        "div[class*='assistant' i] .markdown",
        ".markdown.prose",
      ],
    },
    perplexity: {
      composer: [
        "textarea[placeholder*='Ask' i]",
        "div[contenteditable='true']",
        "textarea",
      ],
      sendButton: [
        "button[aria-label*='Submit' i]",
        "button[aria-label*='Send' i]",
        "button[type='submit']",
      ],
      fileInput: ["input[type='file']"],
      assistant: [
        ".prose",
        "[class*='answer' i]",
        "[data-testid*='answer' i]",
        "main .markdown",
      ],
    },
    test: {
      composer: ["#composer", "textarea"],
      sendButton: ["#send-btn", "button[type='submit']"],
      fileInput: ["#file-input", "input[type='file']"],
      assistant: [".assistant-reply", "#assistant"],
    },
  };

  function firstMatch(selectors) {
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el) return el;
      } catch (_) {}
    }
    return null;
  }

  global.SUG = global.SUG || {};
  global.SUG.site = isChatGPT
    ? "chatgpt"
    : isPerplexity
      ? "perplexity"
      : isTestHarness
        ? "test"
        : "unknown";
  global.SUG.selectors =
    global.SUG.site === "chatgpt"
      ? SELECTORS.chatgpt
      : global.SUG.site === "perplexity"
        ? SELECTORS.perplexity
        : global.SUG.site === "test"
          ? SELECTORS.test
          : SELECTORS.chatgpt;
  global.SUG.firstMatch = firstMatch;
  global.SUG.MARKER = "WALLED_SENSITIVE";
})(window);
