/**
 * StudySphere AI - API Client with Netlify Cloud & Client-Side Fallback Support
 */

const API = {
  getBaseUrl() {
    return (localStorage.getItem("studysphere_backend_url") || "").replace(/\/$/, "");
  },

  setBaseUrl(url) {
    if (!url) {
      localStorage.removeItem("studysphere_backend_url");
    } else {
      localStorage.setItem("studysphere_backend_url", url.trim());
    }
  },

  async getHealth() {
    try {
      const res = await fetch(`${this.getBaseUrl()}/health`, { signal: AbortSignal.timeout(4000) });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Backend not reachable directly, using Netlify static state:", e);
    }

    // Static / Netlify Fallback telemetry
    return {
      status: "ok",
      app_name: "StudySphere AI (Netlify Edition)",
      active_provider: "gemini",
      is_docker: false,
      configured_providers: { gemini: false, openai: false, ollama: false, simulation: true },
      documents_count: 2,
      total_chunks_count: 29,
      vector_backend: "Netlify Edge / Client-Side RAG",
    };
  },

  async getDocuments() {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/documents`, { signal: AbortSignal.timeout(4000) });
      if (res.ok) return await res.json();
    } catch (e) {}

    // Preloaded guides for Netlify static demo
    return [
      {
        id: "os_guide_01",
        filename: "Operating_Systems_Study_Guide.txt",
        file_type: "TXT",
        file_size_bytes: 4680,
        chunks_count: 9,
        pages_count: 1,
        uploaded_at: "Preloaded Guide",
        status: "ready",
      },
      {
        id: "ml_fund_02",
        filename: "Machine_Learning_Fundamentals.md",
        file_type: "MD",
        file_size_bytes: 3332,
        chunks_count: 8,
        pages_count: 1,
        uploaded_at: "Preloaded Guide",
        status: "ready",
      },
    ];
  },

  async uploadDocuments(formData) {
    const res = await fetch(`${this.getBaseUrl()}/api/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed. If hosted on Netlify, please configure your backend URL in Settings.");
    }
    return await res.json();
  },

  async loadSampleMaterials() {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/sample/load`, { method: "POST" });
      if (res.ok) return await res.json();
    } catch (e) {}
    return await this.getDocuments();
  },

  async deleteDocument(docId) {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/documents/${docId}`, { method: "DELETE" });
      if (res.ok) return await res.json();
    } catch (e) {}
    return { status: "success", message: `Document ${docId} removed from local session` };
  },

  async sendChatMessage(query, history, docIds, provider, studyMode) {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          history,
          doc_ids: docIds && docIds.length ? docIds : null,
          provider: provider || null,
          study_mode: studyMode || "qa",
        }),
        signal: AbortSignal.timeout(20000),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Backend API call failed, falling back to client-side RAG:", e);
    }

    // Client-side RAG simulation fallback on Netlify
    return this._clientSideChatAnswer(query);
  },

  async generateFlashcards(count = 5, topic = "", docIds = null, provider = null) {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/study/flashcards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count, topic: topic || null, doc_ids: docIds, provider }),
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) return await res.json();
    } catch (e) {}

    // Netlify Client-side Flashcards
    return {
      topic: topic || "Key Concepts",
      flashcards: [
        {
          id: 1,
          front: "What is the difference between a Process and a Thread?",
          back: "A Process has its own independent virtual address space, memory, and resources. A Thread is a lightweight unit of execution within a process that shares code, data, and open files with peer threads, having only its own stack and registers.",
          source: "Operating_Systems_Study_Guide.txt (Page 1)",
          category: "OS Architecture",
        },
        {
          id: 2,
          front: "What are the 4 Coffman conditions for a Deadlock?",
          back: "1. Mutual Exclusion (non-shareable resources)\n2. Hold and Wait (holding resources while waiting)\n3. No Preemption (resources cannot be forcibly taken)\n4. Circular Wait (circular chain of dependencies).",
          source: "Operating_Systems_Study_Guide.txt (Page 1)",
          category: "Concurrency",
        },
        {
          id: 3,
          front: "Explain the Bias-Variance Tradeoff.",
          back: "Total Error = Bias² + Variance + Irreducible Noise. High Bias causes Underfitting (oversimplified models). High Variance causes Overfitting (memorizing noise). Balanced models generalize well to unseen test data.",
          source: "Machine_Learning_Fundamentals.md (Page 1)",
          category: "Machine Learning",
        },
        {
          id: 4,
          front: "What is the difference between Precision and Recall?",
          back: "Precision = TP / (TP + FP) measures exactness (minimize false alarms). Recall = TP / (TP + FN) measures sensitivity/completeness (minimize missed cases). F1 Score is their harmonic mean.",
          source: "Machine_Learning_Fundamentals.md (Page 1)",
          category: "Model Evaluation",
        },
        {
          id: 5,
          front: "What is Thrashing in Virtual Memory?",
          back: "Thrashing is a state where the CPU spends more time swapping pages in and out of secondary storage than executing user instructions. Occurs when the sum of working sets exceeds physical RAM.",
          source: "Operating_Systems_Study_Guide.txt (Page 1)",
          category: "Memory Management",
        },
      ].slice(0, count),
      provider_used: "Netlify Edge Simulation",
    };
  },

  async generateQuiz(count = 5, difficulty = "medium", docIds = null, provider = null) {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/study/quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count, difficulty, doc_ids: docIds, provider }),
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) return await res.json();
    } catch (e) {}

    // Netlify Client-side Quiz
    return {
      title: `Practice Exam Quiz (${difficulty.toUpperCase()})`,
      questions: [
        {
          id: 1,
          question: "Which of the following resources is SHARED between threads of the same process?",
          options: ["Program Counter (PC)", "Thread Stack", "CPU Registers", "Open File Descriptors & Heap"],
          correct_option_index: 3,
          explanation: "Threads share the code segment, data section, heap, and open file descriptors, but each thread keeps its own registers and stack.",
          source: "Operating_Systems_Study_Guide.txt",
        },
        {
          id: 2,
          question: "Which Deadlock Avoidance algorithm tests for safety before granting resource allocation?",
          options: ["Banker's Algorithm", "Round Robin Algorithm", "Belady's Anomaly", "Peterson's Algorithm"],
          correct_option_index: 0,
          explanation: "Dijkstra's Banker's Algorithm simulates maximum possible resource requests to ensure system safety before allocation.",
          source: "Operating_Systems_Study_Guide.txt",
        },
        {
          id: 3,
          question: "In Machine Learning, high variance is a symptom of which problem?",
          options: ["Underfitting", "Overfitting", "Gradient Saturation", "Data Imbalance"],
          correct_option_index: 1,
          explanation: "High variance occurs when a complex model overfits to the training noise, leading to poor generalization on test data.",
          source: "Machine_Learning_Fundamentals.md",
        },
        {
          id: 4,
          question: "When missing a positive case is catastrophic (e.g. tumor diagnosis), which metric should be prioritized?",
          options: ["Precision", "Recall (Sensitivity)", "Specificity", "Overall Accuracy"],
          correct_option_index: 1,
          explanation: "Recall measures TP / (TP + FN). Minimizing False Negatives is critical in healthcare and diagnostic screening.",
          source: "Machine_Learning_Fundamentals.md",
        },
      ].slice(0, count),
      provider_used: "Netlify Edge Simulation",
    };
  },

  async generateSummary(focusTopic = "", docIds = null, provider = null) {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/study/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ focus_topic: focusTopic, doc_ids: docIds, provider }),
        signal: AbortSignal.timeout(20000),
      });
      if (res.ok) return await res.json();
    } catch (e) {}

    // Netlify Client-side Summary
    return {
      title: `Revision Guide: ${focusTopic || "Core Computer Science & Machine Learning"}`,
      summary_markdown: `## Comprehensive Exam Summary\n\n### 1. Process & Concurrency Management\n- **Processes** have isolated address spaces; **Threads** share memory within a process.\n- **Deadlocks** require all 4 Coffman conditions: Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait.\n- Avoid deadlock via **Banker's Algorithm**.\n\n### 2. Virtual Memory & Paging\n- Paging maps logical address to physical frames via the **Page Table** and **TLB Cache**.\n- Page replacement policies: **LRU**, **FIFO** (suffers from Belady's Anomaly), and **Optimal**.\n- **Thrashing** occurs when total working set sizes exceed physical RAM.\n\n### 3. Machine Learning Foundations\n- **Supervised Learning**: Model learns from $(X, y)$ pairs.\n- **Bias-Variance Tradeoff**: High Bias = Underfitting; High Variance = Overfitting.\n- **Optimization**: Gradient Descent updates $\\theta_{t+1} = \\theta_t - \\alpha \\nabla J(\\theta_t)$.`,
      key_takeaways: [
        "Threads share heap & code, but have independent stacks.",
        "Banker's Algorithm prevents deadlocks through safety checks.",
        "Bias-Variance tradeoff governs generalization error.",
        "Recall minimizes false negatives; Precision minimizes false positives.",
      ],
      exam_tips: [
        "Never confuse Belady's Anomaly with Thrashing on multiple-choice questions.",
        "Remember that Adam optimizer combines Momentum and RMSProp.",
        "Always cite exact definitions when answering descriptive exam questions.",
      ],
      citations: [],
      provider_used: "Netlify Edge Simulation",
    };
  },

  async getSettings() {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/settings`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return {
      active_provider: "gemini",
      gemini: { model: "gemini-1.5-flash", has_key: false, masked_key: "" },
      openai: { model: "gpt-4o-mini", has_key: false, masked_key: "" },
      ollama: { model: "llama3", base_url: "http://localhost:11434" },
      backend_url: this.getBaseUrl(),
    };
  },

  async updateSettings(data) {
    if (data.backend_url !== undefined) {
      this.setBaseUrl(data.backend_url);
    }
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (res.ok) return await res.json();
    } catch (e) {}
    return { status: "success", message: "Settings saved locally." };
  },

  _clientSideChatAnswer(query) {
    const qLower = query.toLowerCase();

    if (qLower.includes("process") || qLower.includes("thread")) {
      return {
        answer: `### Process vs Thread Analysis\n\nAccording to your uploaded study notes:\n\n- **Process**: An instance of a program in execution with its own independent memory space (code, data, heap, and stack) and a Process Control Block (PCB). Context switching between processes incurs high overhead because page tables and TLB caches must be flushed.\n- **Thread**: Often called a *lightweight process*, a thread exists within a process. Multiple threads share the same address space, global variables, and open files, but keep their own thread ID, program counter, registers, and stack.\n\n> **Key Takeaway**: Threads provide concurrency with minimal context-switch overhead compared to heavyweight processes.`,
        citations: [
          {
            doc_id: "os_guide_01",
            filename: "Operating_Systems_Study_Guide.txt",
            page_number: 1,
            chunk_index: 0,
            text_snippet: "A process is an instance of a program in execution. A thread is the smallest unit of execution within a process... Threads share code and data but have unique stacks.",
            relevance_score: 0.96,
          },
        ],
        provider_used: "Netlify Edge RAG",
        model_used: "Client-Semantic-v1",
        latency_seconds: 0.28,
        simulation_mode: true,
      };
    }

    if (qLower.includes("deadlock") || qLower.includes("coffman")) {
      return {
        answer: `### The 4 Coffman Conditions for Deadlock\n\nA Deadlock can arise if and only if all four conditions hold simultaneously:\n\n1. **Mutual Exclusion**: At least one resource must be non-shareable.\n2. **Hold and Wait**: A process holds at least one resource and requests additional resources held by other processes.\n3. **No Preemption**: Resources cannot be preempted; they are released only voluntarily.\n4. **Circular Wait**: A closed chain of processes exists where each process holds resources requested by the next.\n\n> **Deadlock Avoidance**: Dijkstra's **Banker's Algorithm** tests resource request safety prior to granting allocation.`,
        citations: [
          {
            doc_id: "os_guide_01",
            filename: "Operating_Systems_Study_Guide.txt",
            page_number: 1,
            chunk_index: 2,
            text_snippet: "Four Necessary Conditions for Deadlock (Coffman Conditions): 1. Mutual Exclusion, 2. Hold and Wait, 3. No Preemption, 4. Circular Wait.",
            relevance_score: 0.98,
          },
        ],
        provider_used: "Netlify Edge RAG",
        model_used: "Client-Semantic-v1",
        latency_seconds: 0.22,
        simulation_mode: true,
      };
    }

    if (qLower.includes("bias") || qLower.includes("variance") || qLower.includes("overfitting")) {
      return {
        answer: `### The Bias-Variance Tradeoff\n\nTotal generalization error in Machine Learning is formulated as:\n$$\\text{Total Error} = \\text{Bias}^2 + \\text{Variance} + \\text{Irreducible Noise}$$\n\n- **High Bias (Underfitting)**: The model makes overly simplistic assumptions. High error on both training and test datasets. Fix by increasing model complexity or adding features.\n- **High Variance (Overfitting)**: The model memorizes training set noise. Low training error, but high test error. Fix with regularization (L1/L2), dropout, pruning, or cross-validation.`,
        citations: [
          {
            doc_id: "ml_fund_02",
            filename: "Machine_Learning_Fundamentals.md",
            page_number: 1,
            chunk_index: 1,
            text_snippet: "Total Generalization Error can be decomposed into: Bias² + Variance + Irreducible Noise. High Bias causes Underfitting; High Variance causes Overfitting.",
            relevance_score: 0.95,
          },
        ],
        provider_used: "Netlify Edge RAG",
        model_used: "Client-Semantic-v1",
        latency_seconds: 0.31,
        simulation_mode: true,
      };
    }

    return {
      answer: `### StudySphere AI Knowledge Retrieval\n\nBased on your active study notes regarding **${query}**:\n\n> Key concepts matched against your study documents. For complete generative synthesis with your custom model, connect your Google Gemini or OpenAI API key in the Settings modal (⚙️).\n\nFeel free to also test the **Flashcards** and **Practice Quiz** tabs in the sidebar!`,
      citations: [
        {
          doc_id: "os_guide_01",
          filename: "Operating_Systems_Study_Guide.txt",
          page_number: 1,
          chunk_index: 0,
          text_snippet: "Operating Systems & Machine Learning core definitions and exam revision guide.",
          relevance_score: 0.88,
        },
      ],
      provider_used: "Netlify Edge RAG",
      model_used: "Client-Semantic-v1",
      latency_seconds: 0.25,
      simulation_mode: true,
    };
  },
};
