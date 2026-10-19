/**
 * StudySphere AI - Main Coordinator & State Manager
 */

const AppState = {
  documents: [],
  selectedProvider: "gemini",
  studyMode: "qa",
  activeTab: "chat",
  isDocker: false,
};

document.addEventListener("DOMContentLoaded", async () => {
  ChatManager.init();
  StudyTools.init();
  setupNavigation();
  setupModals();
  setupUpload();
  setupSettings();
  setupThemeToggle();

  await checkSystemStatus();
  await refreshDocuments();
});

/* --------------------------------------------------------------------------
   System Status & Telemetry
   -------------------------------------------------------------------------- */
async function checkSystemStatus() {
  try {
    const health = await API.getHealth();
    AppState.isDocker = health.is_docker;
    AppState.selectedProvider = health.active_provider;

    const providerBadge = document.getElementById("active-provider-pill");
    if (providerBadge) {
      providerBadge.textContent = health.active_provider.toUpperCase();
    }

    const dockerBadge = document.getElementById("docker-status-pill");
    if (dockerBadge) {
      dockerBadge.textContent = health.is_docker ? "Docker Active" : "Local Host";
      dockerBadge.className = `badge ${health.is_docker ? "badge-emerald" : "badge-cyan"}`;
    }

    const telemetryText = document.getElementById("sys-telemetry-text");
    if (telemetryText) {
      telemetryText.textContent = `${health.total_chunks_count} chunks · ${health.vector_backend}`;
    }
  } catch (e) {
    console.error("Health check error:", e);
  }
}

/* --------------------------------------------------------------------------
   Document Management
   -------------------------------------------------------------------------- */
async function refreshDocuments() {
  try {
    const docs = await API.getDocuments();
    AppState.documents = docs;
    renderDocumentList(docs);
    updateDocumentDropdown(docs);
  } catch (e) {
    console.error("Error refreshing documents:", e);
  }
}

function renderDocumentList(docs) {
  const container = document.getElementById("sidebar-doc-list");
  if (!container) return;

  if (docs.length === 0) {
    container.innerHTML = `
      <div style="text-align:center;padding:24px 10px;color:var(--text-muted);font-size:12px;">
        No study materials uploaded yet.<br/>
        Click <strong>Upload</strong> or <strong>Load Samples</strong> below!
      </div>
    `;
    return;
  }

  container.innerHTML = "";
  docs.forEach((doc) => {
    const item = document.createElement("div");
    item.className = "doc-item";
    item.innerHTML = `
      <div class="doc-info">
        <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
        <div class="doc-meta">
          <span class="badge badge-cyan">${doc.file_type}</span>
          <span>${doc.chunks_count} chunks</span>
          <span>${(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
        </div>
      </div>
      <button class="doc-delete-btn" title="Delete document" onclick="deleteDocument('${doc.id}')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"></path><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
      </button>
    `;
    container.appendChild(item);
  });
}

function updateDocumentDropdown(docs) {
  const select = document.getElementById("doc-filter-select");
  if (!select) return;

  const currentVal = select.value;
  select.innerHTML = `<option value="all">📚 All Indexed Materials (${docs.length})</option>`;

  docs.forEach((doc) => {
    const opt = document.createElement("option");
    opt.value = doc.id;
    opt.textContent = `📄 ${doc.filename}`;
    select.appendChild(opt);
  });

  if (currentVal) select.value = currentVal;
}

async function deleteDocument(docId) {
  if (!confirm("Are you sure you want to remove this study document and its vector embeddings?")) return;
  try {
    await API.deleteDocument(docId);
    await refreshDocuments();
    await checkSystemStatus();
  } catch (e) {
    alert(`Failed to delete document: ${e.message}`);
  }
}

/* --------------------------------------------------------------------------
   Navigation & Study Modes
   -------------------------------------------------------------------------- */
function setupNavigation() {
  // Sidebar tab switching
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const targetView = tab.getAttribute("data-target");
      AppState.activeTab = targetView;

      document.querySelectorAll(".view-panel").forEach((panel) => {
        panel.classList.remove("active");
      });
      document.getElementById(`panel-${targetView}`)?.classList.add("active");
    });
  });

  // Study mode pills (Q&A, ELI5, Exam Prep, Summary)
  const modePills = document.querySelectorAll(".mode-pill");
  modePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      modePills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      AppState.studyMode = pill.getAttribute("data-mode");
    });
  });
}

/* --------------------------------------------------------------------------
   Upload & Sample Loader
   -------------------------------------------------------------------------- */
function setupUpload() {
  const uploadModal = document.getElementById("upload-modal");
  const openUploadBtn = document.getElementById("open-upload-btn");
  const closeUploadBtn = document.getElementById("close-upload-btn");
  const dropzone = document.getElementById("file-dropzone");
  const fileInput = document.getElementById("file-input");
  const sampleBtn = document.getElementById("load-samples-btn");

  if (openUploadBtn) {
    openUploadBtn.addEventListener("click", () => uploadModal.classList.add("active"));
  }

  if (closeUploadBtn) {
    closeUploadBtn.addEventListener("click", () => uploadModal.classList.remove("active"));
  }

  // Dropzone drag-and-drop
  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        handleFileUpload(e.dataTransfer.files);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) {
        handleFileUpload(fileInput.files);
      }
    });
  }

  // Sample Materials Button
  if (sampleBtn) {
    sampleBtn.addEventListener("click", async () => {
      sampleBtn.disabled = true;
      sampleBtn.innerHTML = `<span class="pulsing-dot online"></span> Indexing Samples...`;
      try {
        await API.loadSampleMaterials();
        await refreshDocuments();
        await checkSystemStatus();
        alert("✨ Pre-packaged Study Guides loaded successfully (OS Guide & ML Fundamentals)!");
      } catch (e) {
        alert(`Failed to load samples: ${e.message}`);
      } finally {
        sampleBtn.disabled = false;
        sampleBtn.innerHTML = `<span>⚡</span> Load Sample Guides`;
      }
    });
  }
}

async function handleFileUpload(files) {
  const uploadModal = document.getElementById("upload-modal");
  const statusDiv = document.getElementById("upload-progress-status");
  const formData = new FormData();

  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  statusDiv.style.display = "block";
  statusDiv.innerHTML = `<div style="display:flex;align-items:center;gap:8px;"><div class="pulsing-dot online"></div> Parsing pages & generating vector embeddings...</div>`;

  try {
    await API.uploadDocuments(formData);
    await refreshDocuments();
    await checkSystemStatus();
    uploadModal.classList.remove("active");
    statusDiv.style.display = "none";
    alert(`🎉 Successfully indexed ${files.length} document(s)!`);
  } catch (e) {
    statusDiv.innerHTML = `<div style="color:var(--accent-rose);">❌ ${e.message}</div>`;
  }
}

/* --------------------------------------------------------------------------
   Settings Modal & Citation Drawer
   -------------------------------------------------------------------------- */
function setupModals() {
  // Settings modal
  const settingsModal = document.getElementById("settings-modal");
  const openSettingsBtn = document.getElementById("open-settings-btn");
  const closeSettingsBtn = document.getElementById("close-settings-btn");

  if (openSettingsBtn) {
    openSettingsBtn.addEventListener("click", async () => {
      await loadSettingsIntoForm();
      settingsModal.classList.add("active");
    });
  }

  if (closeSettingsBtn) {
    closeSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("active"));
  }

  // Citation Drawer Close
  const closeCitBtn = document.getElementById("close-cit-drawer-btn");
  const citDrawer = document.getElementById("citation-drawer");
  if (closeCitBtn && citDrawer) {
    closeCitBtn.addEventListener("click", () => citDrawer.classList.remove("open"));
  }
}

async function loadSettingsIntoForm() {
  try {
    const config = await API.getSettings();
    document.getElementById("settings-provider-select").value = config.active_provider;
    document.getElementById("settings-gemini-key").placeholder = config.gemini?.masked_key || "Paste Google Gemini API Key...";
    document.getElementById("settings-openai-key").placeholder = config.openai?.masked_key || "Paste OpenAI API Key...";
    document.getElementById("settings-ollama-url").value = config.ollama?.base_url || "http://localhost:11434";
    const backendInput = document.getElementById("settings-backend-url");
    if (backendInput) backendInput.value = API.getBaseUrl();
  } catch (e) {
    console.error("Failed to load settings:", e);
  }
}

function setupSettings() {
  const saveBtn = document.getElementById("save-settings-btn");
  if (!saveBtn) return;

  saveBtn.addEventListener("click", async () => {
    const provider = document.getElementById("settings-provider-select").value;
    const geminiKey = document.getElementById("settings-gemini-key").value.trim();
    const openaiKey = document.getElementById("settings-openai-key").value.trim();
    const ollamaUrl = document.getElementById("settings-ollama-url").value.trim();
    const backendUrl = document.getElementById("settings-backend-url")?.value.trim() || "";

    API.setBaseUrl(backendUrl);

    const payload = { provider, backend_url: backendUrl };
    if (geminiKey) payload.gemini_api_key = geminiKey;
    if (openaiKey) payload.openai_api_key = openaiKey;
    if (ollamaUrl) payload.ollama_base_url = ollamaUrl;

    try {
      await API.updateSettings(payload);
      AppState.selectedProvider = provider;
      document.getElementById("active-provider-pill").textContent = provider.toUpperCase();
      document.getElementById("settings-modal").classList.remove("active");
      alert("✅ Configuration saved successfully!");
      await checkSystemStatus();
    } catch (e) {
      alert(`Error saving settings: ${e.message}`);
    }
  });
}

/* --------------------------------------------------------------------------
   Theme Switcher (Dark / Light)
   -------------------------------------------------------------------------- */
function setupThemeToggle() {
  const toggleBtn = document.getElementById("theme-toggle-btn");
  if (!toggleBtn) return;

  let currentTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", currentTheme);

  toggleBtn.addEventListener("click", () => {
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", currentTheme);
    localStorage.setItem("theme", currentTheme);
    toggleBtn.innerHTML = currentTheme === "dark" ? "🌙" : "☀️";
  });
}
