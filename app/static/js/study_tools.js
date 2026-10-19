/**
 * StudySphere AI - Flashcards, Practice Quiz, and Revision Guide Engine
 */

const StudyTools = {
  // Flashcards State
  flashcards: [],
  currentCardIdx: 0,
  masteredIds: new Set(),
  reviewIds: new Set(),

  // Quiz State
  quizQuestions: [],
  quizUserAnswers: {},

  init() {
    this.bindFlashcardEvents();
    this.bindQuizEvents();
    this.bindSummaryEvents();
  },

  /* ------------------------------------------------------------------------
     Flashcards Controller
     ------------------------------------------------------------------------ */
  bindFlashcardEvents() {
    const stage = document.getElementById("flashcard-stage");
    const inner = document.getElementById("flashcard-inner");
    const nextBtn = document.getElementById("fc-next-btn");
    const prevBtn = document.getElementById("fc-prev-btn");
    const genBtn = document.getElementById("gen-flashcards-btn");
    const masteredBtn = document.getElementById("fc-mastered-btn");
    const reviewBtn = document.getElementById("fc-review-btn");

    if (stage && inner) {
      stage.addEventListener("click", () => {
        inner.classList.toggle("flipped");
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => this.nextCard());
    }

    if (prevBtn) {
      prevBtn.addEventListener("click", () => this.prevCard());
    }

    if (masteredBtn) {
      masteredBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.flashcards.length === 0) return;
        const cur = this.flashcards[this.currentCardIdx];
        this.masteredIds.add(cur.id);
        this.reviewIds.delete(cur.id);
        this.nextCard();
      });
    }

    if (reviewBtn) {
      reviewBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.flashcards.length === 0) return;
        const cur = this.flashcards[this.currentCardIdx];
        this.reviewIds.add(cur.id);
        this.masteredIds.delete(cur.id);
        this.nextCard();
      });
    }

    if (genBtn) {
      genBtn.addEventListener("click", () => this.loadFlashcards());
    }

    // Keyboard navigation when on flashcard tab
    window.addEventListener("keydown", (e) => {
      const fcPanel = document.getElementById("panel-flashcards");
      if (!fcPanel || !fcPanel.classList.contains("active")) return;

      if (e.code === "Space") {
        e.preventDefault();
        inner?.classList.toggle("flipped");
      } else if (e.code === "ArrowRight") {
        this.nextCard();
      } else if (e.code === "ArrowLeft") {
        this.prevCard();
      }
    });
  },

  async loadFlashcards() {
    const btn = document.getElementById("gen-flashcards-btn");
    const topicInput = document.getElementById("fc-topic-input");
    const countSelect = document.getElementById("fc-count-select");
    const topic = topicInput?.value.trim() || "";
    const count = parseInt(countSelect?.value || "5", 10);

    const activeDocId = document.getElementById("doc-filter-select")?.value;
    const selectedDocs = activeDocId && activeDocId !== "all" ? [activeDocId] : null;

    btn.disabled = true;
    btn.innerHTML = `<span class="pulsing-dot online"></span> Generating...`;

    try {
      const res = await API.generateFlashcards(count, topic, selectedDocs, AppState.selectedProvider);
      this.flashcards = res.flashcards || [];
      this.currentCardIdx = 0;
      this.masteredIds.clear();
      this.reviewIds.clear();
      this.renderFlashcard();
    } catch (e) {
      alert(`Flashcard generation failed: ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `✨ Generate Flashcards`;
    }
  },

  renderFlashcard() {
    const inner = document.getElementById("flashcard-inner");
    const frontText = document.getElementById("fc-front-text");
    const backText = document.getElementById("fc-back-text");
    const counter = document.getElementById("fc-counter");
    const sourceBadge = document.getElementById("fc-source-badge");
    const categoryBadge = document.getElementById("fc-category-badge");
    const progressBar = document.getElementById("fc-mastery-bar");

    if (!this.flashcards.length) {
      if (frontText) frontText.textContent = "No flashcards generated yet.";
      if (backText) backText.textContent = "Click 'Generate Flashcards' above to create cards from your notes.";
      return;
    }

    inner?.classList.remove("flipped");

    const card = this.flashcards[this.currentCardIdx];
    if (frontText) frontText.textContent = card.front;
    if (backText) backText.textContent = card.back;
    if (counter) counter.textContent = `${this.currentCardIdx + 1} / ${this.flashcards.length}`;
    if (sourceBadge) sourceBadge.textContent = card.source || "Study Material";
    if (categoryBadge) categoryBadge.textContent = card.category || "Concept";

    if (progressBar) {
      const pct = Math.round((this.masteredIds.size / this.flashcards.length) * 100);
      progressBar.style.width = `${pct}%`;
      document.getElementById("fc-mastery-text").textContent = `${this.masteredIds.size} Mastered (${pct}%)`;
    }
  },

  nextCard() {
    if (!this.flashcards.length) return;
    this.currentCardIdx = (this.currentCardIdx + 1) % this.flashcards.length;
    this.renderFlashcard();
  },

  prevCard() {
    if (!this.flashcards.length) return;
    this.currentCardIdx = (this.currentCardIdx - 1 + this.flashcards.length) % this.flashcards.length;
    this.renderFlashcard();
  },

  /* ------------------------------------------------------------------------
     Quiz Controller
     ------------------------------------------------------------------------ */
  bindQuizEvents() {
    const genBtn = document.getElementById("gen-quiz-btn");
    if (genBtn) {
      genBtn.addEventListener("click", () => this.loadQuiz());
    }
  },

  async loadQuiz() {
    const btn = document.getElementById("gen-quiz-btn");
    const diffSelect = document.getElementById("quiz-diff-select");
    const countSelect = document.getElementById("quiz-count-select");
    const count = parseInt(countSelect?.value || "5", 10);
    const difficulty = diffSelect?.value || "medium";

    const activeDocId = document.getElementById("doc-filter-select")?.value;
    const selectedDocs = activeDocId && activeDocId !== "all" ? [activeDocId] : null;

    btn.disabled = true;
    btn.innerHTML = `<span class="pulsing-dot online"></span> Creating Quiz...`;

    try {
      const res = await API.generateQuiz(count, difficulty, selectedDocs, AppState.selectedProvider);
      this.quizQuestions = res.questions || [];
      this.quizUserAnswers = {};
      this.renderQuiz();
    } catch (e) {
      alert(`Quiz generation error: ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `🎯 Generate Exam Quiz`;
    }
  },

  renderQuiz() {
    const container = document.getElementById("quiz-questions-list");
    if (!container) return;

    if (!this.quizQuestions.length) {
      container.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);">No quiz generated yet. Click 'Generate Exam Quiz' to begin.</div>`;
      return;
    }

    container.innerHTML = "";

    this.quizQuestions.forEach((q, qIdx) => {
      const card = document.createElement("div");
      card.className = "quiz-card";

      const title = document.createElement("div");
      title.className = "quiz-question-title";
      title.innerHTML = `
        <span class="badge badge-cyan">Q${qIdx + 1}</span>
        <span>${q.question}</span>
      `;
      card.appendChild(title);

      const optionsDiv = document.createElement("div");
      optionsDiv.className = "quiz-options";

      q.options.forEach((opt, optIdx) => {
        const optBtn = document.createElement("div");
        optBtn.className = "quiz-option";
        optBtn.innerHTML = `
          <strong style="color:var(--text-accent);font-family:var(--font-mono);">${String.fromCharCode(65 + optIdx)}.</strong>
          <span>${opt}</span>
        `;

        optBtn.addEventListener("click", () => {
          if (this.quizUserAnswers[qIdx] !== undefined) return; // already answered
          this.quizUserAnswers[qIdx] = optIdx;

          // Reveal feedback
          const isCorrect = optIdx === q.correct_option_index;
          if (isCorrect) {
            optBtn.classList.add("correct");
          } else {
            optBtn.classList.add("wrong");
            // Highlight the correct one
            optionsDiv.children[q.correct_option_index]?.classList.add("correct");
          }

          // Show explanation
          explanationDiv.classList.add("show");
          this.updateQuizScore();
        });

        optionsDiv.appendChild(optBtn);
      });
      card.appendChild(optionsDiv);

      const explanationDiv = document.createElement("div");
      explanationDiv.className = "quiz-explanation";
      explanationDiv.innerHTML = `
        <strong>💡 Explanation:</strong> ${q.explanation}
        <div style="margin-top:6px;font-size:11px;color:var(--text-muted);">Source: ${q.source}</div>
      `;
      card.appendChild(explanationDiv);

      container.appendChild(card);
    });

    document.getElementById("quiz-score-banner").style.display = "block";
    this.updateQuizScore();
  },

  updateQuizScore() {
    const answeredCount = Object.keys(this.quizUserAnswers).length;
    let correctCount = 0;

    this.quizQuestions.forEach((q, idx) => {
      if (this.quizUserAnswers[idx] === q.correct_option_index) {
        correctCount++;
      }
    });

    const banner = document.getElementById("quiz-score-text");
    if (banner) {
      banner.textContent = `Score: ${correctCount} / ${this.quizQuestions.length} (${answeredCount} Answered)`;
    }
  },

  /* ------------------------------------------------------------------------
     Revision Guide / Summary Controller
     ------------------------------------------------------------------------ */
  bindSummaryEvents() {
    const genBtn = document.getElementById("gen-summary-btn");
    const copyBtn = document.getElementById("copy-summary-btn");

    if (genBtn) {
      genBtn.addEventListener("click", () => this.loadSummary());
    }

    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        const text = document.getElementById("summary-markdown-content")?.innerText || "";
        navigator.clipboard.writeText(text);
        copyBtn.textContent = "✅ Copied!";
        setTimeout(() => (copyBtn.textContent = "📋 Copy Markdown"), 2000);
      });
    }
  },

  async loadSummary() {
    const btn = document.getElementById("gen-summary-btn");
    const topicInput = document.getElementById("summary-topic-input");
    const topic = topicInput?.value.trim() || "";

    const activeDocId = document.getElementById("doc-filter-select")?.value;
    const selectedDocs = activeDocId && activeDocId !== "all" ? [activeDocId] : null;

    btn.disabled = true;
    btn.innerHTML = `<span class="pulsing-dot online"></span> Generating Revision Notes...`;

    try {
      const res = await API.generateSummary(topic, selectedDocs, AppState.selectedProvider);

      document.getElementById("summary-title").textContent = res.title;

      // Render Markdown
      const mdDiv = document.getElementById("summary-markdown-content");
      if (window.marked) {
        mdDiv.innerHTML = window.marked.parse(res.summary_markdown);
      } else {
        mdDiv.textContent = res.summary_markdown;
      }

      // Render Takeaways
      const takeawaysList = document.getElementById("summary-takeaways-list");
      takeawaysList.innerHTML = "";
      (res.key_takeaways || []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        takeawaysList.appendChild(li);
      });

      // Render Exam Tips
      const tipsList = document.getElementById("summary-tips-list");
      tipsList.innerHTML = "";
      (res.exam_tips || []).forEach((tip) => {
        const li = document.createElement("li");
        li.textContent = tip;
        tipsList.appendChild(li);
      });

      document.getElementById("summary-results-container").style.display = "block";
    } catch (e) {
      alert(`Summary generation failed: ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `📑 Generate Study Guide`;
    }
  },
};
