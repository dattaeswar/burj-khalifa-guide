/**
 * app.js - Client-side logic for Burj Khalifa Guide
 * Handles SSE streaming, markdown formatting, theme toggling, and conversational state.
 */

function initApp() {
  // Elements
  const chatContainer = document.getElementById("chat-container");
  const messagesList = document.getElementById("messages-list");
  const emptyState = document.getElementById("empty-state");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const charCounter = document.getElementById("char-counter");
  const newChatBtn = document.getElementById("new-chat-btn");
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  const statusIndicator = document.getElementById("status-indicator");

  if (!userInput || !sendBtn) {
    console.error("Required DOM elements missing");
    return;
  }

  // State
  let conversationHistory = []; // [{role, content}]
  let isGenerating = false;
  const MAX_INPUT_CHARS = 1000;

  // -------------------------------------------------------------
  // Theme Toggle & Persistence
  // -------------------------------------------------------------
  const savedTheme = localStorage.getItem("burj_guide_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("burj_guide_theme", newTheme);
    });
  }

  // -------------------------------------------------------------
  // Health Check
  // -------------------------------------------------------------
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        if (data.knowledge_base_loaded && statusIndicator) {
          statusIndicator.style.background = "#10B981";
          statusIndicator.title = `Knowledge Base Active (${data.sections_count} Sections) • Model: ${data.model}`;
        } else if (statusIndicator) {
          statusIndicator.style.background = "#F59E0B";
          statusIndicator.title = "Knowledge Base is indexing or degraded";
        }
      }
    } catch {
      if (statusIndicator) {
        statusIndicator.style.background = "#EF4444";
        statusIndicator.title = "Offline / Server Disconnected";
      }
    }
  }
  checkHealth();

  // -------------------------------------------------------------
  // Markdown & XSS Escaping Helper
  // -------------------------------------------------------------
  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";

    // 1. Escape HTML for XSS prevention
    let escaped = escapeHtml(text);

    // 2. Bold text: **text**
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // 3. Inline code: `text`
    escaped = escaped.replace(/`([^`]+)`/g, "<code>$1</code>");

    // 4. Source Citation Badge (lines starting with "Source: Section ...")
    escaped = escaped.replace(
      /^(Source:\s*Section\s*(\d+)[\s\S]*?)$/gim,
      `<div class="citation-badge">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
        <span>$1</span>
      </div>`
    );

    // 5. Line-by-line processing for lists and paragraphs
    const lines = escaped.split("\n");
    let result = [];
    let inList = false;
    let listType = ""; // 'ul' or 'ol'

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Check bullet list item (- or *)
      const bulletMatch = line.match(/^[-*]\s+(.*)$/);
      // Check numbered list item (1. 2.)
      const numMatch = line.match(/^(\d+)\.\s+(.*)$/);

      if (bulletMatch) {
        if (!inList || listType !== "ul") {
          if (inList) result.push(`</${listType}>`);
          result.push("<ul>");
          inList = true;
          listType = "ul";
        }
        result.push(`<li>${bulletMatch[1]}</li>`);
      } else if (numMatch) {
        if (!inList || listType !== "ol") {
          if (inList) result.push(`</${listType}>`);
          result.push("<ol>");
          inList = true;
          listType = "ol";
        }
        result.push(`<li>${numMatch[2]}</li>`);
      } else {
        if (inList) {
          result.push(`</${listType}>`);
          inList = false;
          listType = "";
        }
        if (line.length > 0) {
          if (line.startsWith('<div class="citation-badge">')) {
            result.push(line);
          } else {
            result.push(`<p>${line}</p>`);
          }
        }
      }
    }

    if (inList) {
      result.push(`</${listType}>`);
    }

    return result.join("");
  }

  // -------------------------------------------------------------
  // UI Helpers: Scroll, Input Auto-Resize, Counters
  // -------------------------------------------------------------
  function scrollToBottom() {
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }

  function updateCharCounter() {
    const length = userInput.value.length;
    if (charCounter) {
      charCounter.textContent = `${length} / ${MAX_INPUT_CHARS}`;
    }

    if (length > MAX_INPUT_CHARS) {
      if (charCounter) charCounter.className = "char-counter exceeded";
      sendBtn.disabled = true;
    } else if (length >= MAX_INPUT_CHARS * 0.85) {
      if (charCounter) charCounter.className = "char-counter warning";
      sendBtn.disabled = isGenerating || length === 0;
    } else {
      if (charCounter) charCounter.className = "char-counter";
      sendBtn.disabled = isGenerating || length === 0;
    }
  }

  function resizeTextarea() {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
  }

  userInput.addEventListener("input", () => {
    updateCharCounter();
    resizeTextarea();
  });

  userInput.addEventListener("keyup", () => {
    updateCharCounter();
  });

  userInput.addEventListener("change", () => {
    updateCharCounter();
  });

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isGenerating && userInput.value.trim().length > 0) {
        handleSubmit();
      }
    }
  });

  if (sendBtn) {
    sendBtn.addEventListener("click", (e) => {
      e.preventDefault();
      if (!isGenerating && userInput.value.trim().length > 0) {
        handleSubmit();
      }
    });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!isGenerating && userInput.value.trim().length > 0) {
        handleSubmit();
      }
    });
  }

  // -------------------------------------------------------------
  // Render Messages
  // -------------------------------------------------------------
  function appendUserMessage(text) {
    if (emptyState) {
      emptyState.style.display = "none";
    }

    const row = document.createElement("div");
    row.className = "message-row user";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = `<p>${escapeHtml(text)}</p>`;

    row.appendChild(bubble);
    messagesList.appendChild(row);
    scrollToBottom();
  }

  function createAssistantMessageSlot() {
    const row = document.createElement("div");
    row.className = "message-row assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar avatar-assistant";
    avatar.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 2v20M8 22h8M9 6h6M8 11h8M7 16h10M12 2l-3 20M12 2l3 20" />
    </svg>`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = `
      <div class="typing-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesList.appendChild(row);
    scrollToBottom();

    return { row, bubble };
  }

  // -------------------------------------------------------------
  // Handle Chat Submission & SSE Stream
  // -------------------------------------------------------------
  async function handleSubmit(overrideText = null) {
    const text = (overrideText !== null ? overrideText : userInput.value).trim();
    if (!text || isGenerating) return;

    if (text.length > MAX_INPUT_CHARS) {
      alert(`Message cannot exceed ${MAX_INPUT_CHARS} characters.`);
      return;
    }

    // Reset input
    if (overrideText === null) {
      userInput.value = "";
      userInput.style.height = "auto";
      updateCharCounter();
    }

    // Append to UI & history
    appendUserMessage(text);
    conversationHistory.push({ role: "user", content: text });

    // Prepare assistant bubble
    const { bubble } = createAssistantMessageSlot();
    isGenerating = true;
    sendBtn.disabled = true;

    let fullReply = "";
    let hasReceivedTokens = false;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: conversationHistory
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errMessage = errorData.detail || errorData.error || `Server error (${response.status})`;
        bubble.innerHTML = `<div class="error-notice">⚠️ ${escapeHtml(errMessage)}</div>`;
        isGenerating = false;
        sendBtn.disabled = userInput.value.trim().length === 0;
        return;
      }

      // Stream reader
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          const trimmedBlock = block.trim();
          if (!trimmedBlock.startsWith("data:")) continue;

          const dataPayload = trimmedBlock.replace(/^data:\s*/, "");
          if (dataPayload === "[DONE]") {
            break;
          }

          try {
            const parsed = JSON.parse(dataPayload);
            if (parsed.error) {
              bubble.innerHTML = `<div class="error-notice">⚠️ ${escapeHtml(parsed.error)}</div>`;
              fullReply = "";
              break;
            }
            if (parsed.text) {
              if (!hasReceivedTokens) {
                bubble.innerHTML = "";
                hasReceivedTokens = true;
              }
              fullReply += parsed.text;
              bubble.innerHTML = formatMarkdown(fullReply);
              scrollToBottom();
            }
          } catch (e) {
            console.error("Failed to parse SSE JSON payload:", dataPayload, e);
          }
        }
      }

      if (fullReply) {
        conversationHistory.push({ role: "assistant", content: fullReply });
      }

    } catch (err) {
      console.error("Chat error:", err);
      bubble.innerHTML = `<div class="error-notice">⚠️ Connection error: Unable to reach the server. Please verify your connection.</div>`;
    } finally {
      isGenerating = false;
      updateCharCounter();
      userInput.focus();
    }
  }

  // -------------------------------------------------------------
  // Suggested Questions Chips
  // -------------------------------------------------------------
  document.querySelectorAll(".suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-question");
      if (q && !isGenerating) {
        handleSubmit(q);
      }
    });
  });

  // -------------------------------------------------------------
  // New Chat
  // -------------------------------------------------------------
  if (newChatBtn) {
    newChatBtn.addEventListener("click", () => {
      conversationHistory = [];
      isGenerating = false;
      userInput.value = "";
      userInput.style.height = "auto";
      updateCharCounter();

      // Clear messages except empty state
      messagesList.innerHTML = "";
      if (emptyState) {
        emptyState.style.display = "flex";
        messagesList.appendChild(emptyState);
      }
      userInput.focus();
    });
  }

  // Initial setup
  updateCharCounter();
  userInput.focus();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}
