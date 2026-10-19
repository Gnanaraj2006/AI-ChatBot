/**
 * StudySphere AI - Chat Engine & UI
 */

const ChatManager = {
  history: [],
  isThinking: false,

  init() {
    this.chatForm = document.getElementById("chat-form");
    this.chatInput = document.getElementById("chat-input");
    this.sendBtn = document.getElementById("send-btn");
    this.messagesContainer = document.getElementById("chat-messages");
    this.welcomeHero = document.getElementById("welcome-hero");
    this.micBtn = document.getElementById("mic-btn");

    this.bindEvents();
    this.setupSpeechRecognition();
  },

  bindEvents() {
    // Auto-resizing textarea
    this.chatInput.addEventListener("input", () => {
      this.chatInput.style.height = "auto";
      this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 160) + "px";
    });

    // Enter to submit (Shift+Enter for newline)
    this.chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.submitQuery();
      }
    });

    this.sendBtn.addEventListener("click", () => this.submitQuery());

    // Suggestion chips click
    document.querySelectorAll(".suggestion-card").forEach((card) => {
      card.addEventListener("click", () => {
        const text = card.getAttribute("data-prompt");
        if (text) {
          this.chatInput.value = text;
          this.submitQuery();
        }
      });
    });
  },

  setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (this.micBtn) this.micBtn.style.display = "none";
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    let recognizing = false;

    this.micBtn.addEventListener("click", () => {
      if (recognizing) {
        recognition.stop();
        return;
      }
      try {
        recognition.start();
        recognizing = true;
        this.micBtn.classList.add("btn-danger");
      } catch (e) {
        console.error("Speech recognition error:", e);
      }
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this.chatInput.value += (this.chatInput.value ? " " : "") + transcript;
      this.chatInput.dispatchEvent(new Event("input"));
    };

    recognition.onend = () => {
      recognizing = false;
      this.micBtn.classList.remove("btn-danger");
    };

    recognition.onerror = () => {
      recognizing = false;
      this.micBtn.classList.remove("btn-danger");
    };
  },

  async submitQuery() {
    const query = this.chatInput.value.trim();
    if (!query || this.isThinking) return;

    if (this.welcomeHero) {
      this.welcomeHero.style.display = "none";
    }

    // Append User Message
    this.appendMessage("user", query);
    this.chatInput.value = "";
    this.chatInput.style.height = "auto";
    this.isThinking = true;

    // Show Typing Indicator
    const typingIndicator = this.appendTypingIndicator();

    try {
      const activeDocId = document.getElementById("doc-filter-select")?.value;
      const selectedDocs = activeDocId && activeDocId !== "all" ? [activeDocId] : null;
      const studyMode = AppState.studyMode || "qa";

      const response = await API.sendChatMessage(
        query,
        this.history,
        selectedDocs,
        AppState.selectedProvider,
        studyMode
      );

      // Remove typing indicator
      typingIndicator.remove();

      // Render Assistant Response
      this.appendMessage("assistant", response.answer, {
        provider: response.provider_used,
        model: response.model_used,
        latency: response.latency_seconds,
        citations: response.citations || [],
        simulation: response.simulation_mode,
      });

      this.history.push({ role: "user", content: query });
      this.history.push({ role: "assistant", content: response.answer });
    } catch (err) {
      typingIndicator.remove();
      this.appendMessage(
        "assistant",
        `⚠️ **Error encountered:** ${err.message}. Please check your connection or try again.`
      );
    } finally {
      this.isThinking = false;
    }
  },

  appendMessage(role, content, meta = null) {
    const row = document.createElement("div");
    row.className = `message-row ${role === "user" ? "user-row" : "ai-row"}`;

    if (role === "assistant") {
      const avatar = document.createElement("div");
      avatar.className = "message-avatar avatar-ai";
      avatar.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"></path><rect x="3" y="10" width="18" height="12" rx="4"></rect><circle cx="8" cy="15" r="1.5"></circle><circle cx="16" cy="15" r="1.5"></circle></svg>`;
      row.appendChild(avatar);
    }

    const body = document.createElement("div");
    body.className = "message-body";

    const bubble = document.createElement("div");
    bubble.className = `bubble ${role === "user" ? "user-bubble" : "ai-bubble"}`;

    if (role === "user") {
      bubble.textContent = content;
    } else {
      // Parse markdown using marked.js
      if (window.marked) {
        bubble.innerHTML = window.marked.parse(content);
      } else {
        bubble.textContent = content;
      }

      // Syntax highlight code blocks
      if (window.hljs) {
        bubble.querySelectorAll("pre code").forEach((block) => {
          window.hljs.highlightElement(block);
        });
      }

      // Render KaTeX math if library present
      if (window.renderMathInElement) {
        try {
          window.renderMathInElement(bubble, {
            delimiters: [
              { left: "$$", right: "$$", display: true },
              { left: "$", right: "$", display: false },
            ],
            throwOnError: false,
          });
        } catch (e) {
          console.warn("KaTeX render error:", e);
        }
      }

      // Add Citations if present
      if (meta && meta.citations && meta.citations.length > 0) {
        const citWrapper = document.createElement("div");
        citWrapper.className = "citations-wrapper";
        citWrapper.innerHTML = `
          <div class="citations-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            Verified Sources (${meta.citations.length})
          </div>
          <div class="citations-list"></div>
        `;

        const list = citWrapper.querySelector(".citations-list");
        meta.citations.forEach((c) => {
          const chip = document.createElement("button");
          chip.className = "citation-chip";
          chip.innerHTML = `
            <span>📄 ${c.filename} · P.${c.page_number}</span>
            <span class="badge badge-cyan">${Math.round(c.relevance_score * 100)}% Match</span>
          `;
          chip.addEventListener("click", () => this.openCitationDrawer(c));
          list.appendChild(chip);
        });

        bubble.appendChild(citWrapper);
      }

      // Metadata Bar
      if (meta) {
        const metaBar = document.createElement("div");
        metaBar.className = "ai-meta-bar";
        metaBar.innerHTML = `
          <span class="badge ${meta.simulation ? "badge-amber" : "badge-violet"}">${meta.provider}</span>
          <span>⚡ ${meta.latency}s</span>
          <button class="btn btn-icon" style="width:26px;height:26px;font-size:11px;" title="Copy to clipboard" onclick="navigator.clipboard.writeText(${JSON.stringify(content)})">📋</button>
        `;
        body.appendChild(metaBar);
      }
    }

    body.prepend(bubble);

    if (role === "user") {
      const avatar = document.createElement("div");
      avatar.className = "message-avatar avatar-user";
      avatar.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
      row.appendChild(avatar);
    }

    row.appendChild(body);
    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
  },

  appendTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row ai-row";
    row.innerHTML = `
      <div class="message-avatar avatar-ai">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"></path><rect x="3" y="10" width="18" height="12" rx="4"></rect></svg>
      </div>
      <div class="message-body">
        <div class="bubble ai-bubble" style="display:flex;align-items:center;gap:6px;padding:12px 18px;">
          <div class="pulsing-dot online"></div>
          <span style="font-size:13px;color:var(--text-secondary);">Synthesizing study notes...</span>
        </div>
      </div>
    `;
    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
    return row;
  },

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  },

  openCitationDrawer(citation) {
    const drawer = document.getElementById("citation-drawer");
    if (!drawer) return;

    document.getElementById("cit-file-title").textContent = citation.filename;
    document.getElementById("cit-page-badge").textContent = `Page ${citation.page_number}`;
    document.getElementById("cit-relevance-text").textContent = `${Math.round(citation.relevance_score * 100)}% Semantic Match`;
    document.getElementById("cit-relevance-bar").style.width = `${Math.round(citation.relevance_score * 100)}%`;
    document.getElementById("cit-snippet-content").textContent = citation.text_snippet;

    drawer.classList.add("open");
  },

  clearChat() {
    this.history = [];
    this.messagesContainer.innerHTML = "";
    if (this.welcomeHero) {
      this.welcomeHero.style.display = "block";
      this.messagesContainer.appendChild(this.welcomeHero);
    }
  },
};
