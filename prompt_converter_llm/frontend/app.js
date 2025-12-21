// ============================================
// Utility Functions
// ============================================

function getBaseUrl() {
  const input = document.getElementById("backendBaseUrl");
  return (input?.value || "http://localhost:8000").replace(/\/+$/, "");
}

function showToast(message, type = "info", timeout = 3500) {
  const toast = document.getElementById("toast");
  if (!toast) return;

  toast.textContent = message;
  toast.classList.remove("toast--error", "toast--success", "toast--show");

  if (type === "error") toast.classList.add("toast--error");
  if (type === "success") toast.classList.add("toast--success");

  void toast.offsetWidth; // Force reflow
  toast.classList.add("toast--show");

  if (timeout) {
    setTimeout(() => {
      toast.classList.remove("toast--show");
    }, timeout);
  }
}

function setStatusPill(id, text, state = "idle") {
  const pill = document.getElementById(id);
  if (!pill) return;
  pill.textContent = text;
  pill.classList.remove("busy", "error");
  if (state === "busy") pill.classList.add("busy");
  if (state === "error") pill.classList.add("error");
}

function showLoading(tab = null, show = true) {
  // Show loading indicator in specific tab instead of full screen
  if (tab) {
    const loadingEl = document.getElementById(`${tab}Loading`);
    if (loadingEl) {
      loadingEl.style.display = show ? "flex" : "none";
    }
  }
}

async function safeFetch(path, options = {}) {
  const base = getBaseUrl();
  const url = `${base}${path}`;

  const resp = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = resp.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await resp.json().catch(() => ({}))
    : await resp.text().catch(() => "");

  if (!resp.ok) {
    const detail =
      (body && body.detail) ||
      (typeof body === "string" ? body : JSON.stringify(body));
    throw new Error(detail || `HTTP ${resp.status}`);
  }

  return body;
}

// ============================================
// Theme Toggle
// ============================================

function initThemeToggle() {
  const themeToggle = document.getElementById("themeToggle");
  const body = document.body;
  const themeIcon = themeToggle?.querySelector(".theme-icon");

  // Load saved theme or default to dark
  const savedTheme = localStorage.getItem("theme") || "dark";
  body.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme, themeIcon);

  themeToggle?.addEventListener("click", () => {
    const currentTheme = body.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    body.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateThemeIcon(newTheme, themeIcon);
  });
}

function updateThemeIcon(theme, icon) {
  if (!icon) return;
  icon.textContent = theme === "dark" ? "☀️" : "🌙";
}

// ============================================
// Render Functions
// ============================================

function renderEngines(engines) {
  const select = document.getElementById("dbEngineSelect");
  if (!select) return;
  select.innerHTML = "";

  const all = engines["Database Engine"] || engines.databases || [];
  all.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name.toLowerCase();
    opt.textContent = name;
    select.appendChild(opt);
  });
}

function renderSearchResults(results, onSelect) {
  const container = document.getElementById("tableSearchResults");
  const countLabel = document.getElementById("tablesCountLabel");
  if (!container) return;
  container.innerHTML = "";

  if (!results || !results.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `
      <div class="empty-state-icon">🔍</div>
      <div class="empty-state-text">No tables found. Try a different keyword.</div>
    `;
    container.appendChild(empty);
    if (countLabel) countLabel.textContent = "0 found";
    return;
  }

  if (countLabel) countLabel.textContent = `${results.length} found`;

  results.forEach((row) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "table-item";

    const name = document.createElement("div");
    name.className = "table-item-name";
    name.textContent = `${row.catalog}.${row.schema}.${row.table}`;

    const meta = document.createElement("div");
    meta.className = "table-item-meta";
    meta.textContent = row.comment || "No description available for this table.";

    item.appendChild(name);
    item.appendChild(meta);

    item.addEventListener("click", () => onSelect(row));
    container.appendChild(item);
  });
}

function renderSelectedTables(selected) {
  const container = document.getElementById("selectedTables");
  const sessionTables = document.getElementById("sessionTables");
  if (!container) return;
  container.innerHTML = "";

  if (!selected.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `
      <div class="empty-state-icon">📋</div>
      <div class="empty-state-text">No tables pinned to context yet.</div>
    `;
    container.appendChild(empty);
    if (sessionTables) sessionTables.textContent = "0 tables";
    return;
  }

  selected.forEach((tbl, idx) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = `${tbl.catalog}.${tbl.schema}.${tbl.table}`;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip-remove";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "Remove table");
    btn.addEventListener("click", () => {
      selected.splice(idx, 1);
      renderSelectedTables(selected);
    });

    chip.appendChild(btn);
    container.appendChild(chip);
  });

  if (sessionTables) {
    sessionTables.textContent =
      selected.length === 1
        ? "1 table"
        : `${selected.length.toString()} tables`;
  }
}

function setSqlOutput(sqlText) {
  const el = document.getElementById("sqlOutput");
  if (!el) return;
  // Clear any loading indicator
  showLoading("sql", false);
  el.textContent = sqlText || "";
}

function setLogsOutput(text) {
  const el = document.getElementById("logsOutput");
  if (!el) return;
  el.textContent = text || "";
}

// Store current results for CSV download
let currentResults = [];

function renderResults(data) {
  const container = document.getElementById("resultsOutput");
  const downloadBtn = document.getElementById("downloadCsvBtn");
  if (!container) return;
  container.innerHTML = "";

  currentResults = data || [];

  if (downloadBtn) {
    if (data && Array.isArray(data) && data.length > 0) {
      downloadBtn.style.display = "inline-flex";
    } else {
      downloadBtn.style.display = "none";
    }
  }

  if (!data || !Array.isArray(data) || !data.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `
      <div class="empty-state-icon">📊</div>
      <div class="empty-state-text">No rows returned.</div>
    `;
    container.appendChild(empty);
    return;
  }

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");

  const first = data[0];
  const cols = Object.keys(first);

  const headerRow = document.createElement("tr");
  cols.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  data.forEach((row) => {
    const tr = document.createElement("tr");
    cols.forEach((c) => {
      const td = document.createElement("td");
      const val = row[c];
      td.textContent =
        val === null || val === undefined ? "" : String(val).slice(0, 200);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
}

// ============================================
// CSV Download
// ============================================

async function downloadCsv() {
  if (!currentResults || !currentResults.length) {
    showToast("No data available to download.", "error");
    return;
  }

  const downloadBtn = document.getElementById("downloadCsvBtn");
  const requestedFilename = `query_results_${new Date().toISOString().split('T')[0]}.csv`;
  
  if (downloadBtn) {
    downloadBtn.disabled = true;
    const originalHTML = downloadBtn.innerHTML;
    downloadBtn.innerHTML = `
      <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      <span>Downloading...</span>
    `;
  }

  try {
    const base = getBaseUrl();
    const url = `${base}/v1/csv_report`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: currentResults,
        filename: requestedFilename
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    const csvContent = await response.text();
    const blob = new Blob([csvContent], { type: "text/csv" });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    
    const contentDisposition = response.headers.get("Content-Disposition");
    let filename = requestedFilename;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    showToast("CSV downloaded successfully!", "success");
  } catch (e) {
    showToast(`Failed to download CSV: ${e.message}`, "error", 6000);
  } finally {
    if (downloadBtn) {
      downloadBtn.disabled = false;
      downloadBtn.innerHTML = `
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <span>Download CSV</span>
      `;
    }
  }
}

// ============================================
// Tab System
// ============================================

function setupTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = {
    sql: document.getElementById("sqlTab"),
    results: document.getElementById("resultsTab"),
    logs: document.getElementById("logsTab"),
  };

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      
      // Remove active class from all tabs and panels
      tabButtons.forEach((b) => b.classList.remove("active"));
      Object.values(tabPanels).forEach((p) => p?.classList.remove("active"));

      // Add active class to clicked tab and corresponding panel
      btn.classList.add("active");
      if (tabPanels[target]) {
        tabPanels[target].classList.add("active");
      }
    });
  });
}

// ============================================
// Main Initialization
// ============================================

document.addEventListener("DOMContentLoaded", async () => {
  // Initialize theme toggle
  initThemeToggle();

  // Setup tabs
  setupTabs();

  const selectedTables = [];

  // Load engines on startup
  try {
    const engines = await safeFetch("/v1/query_engines", { method: "GET" });
    renderEngines(engines);
  } catch (e) {
    console.warn("Could not load engines on startup:", e);
  }

  // Connection status elements
  const apiHealthPill = document.getElementById("apiHealthPill");
  const apiHealthText = document.getElementById("apiHealthText");

  // Test connection button
  document
    .getElementById("testConnectionBtn")
    ?.addEventListener("click", async () => {
      if (apiHealthText) apiHealthText.textContent = "Backend: testing…";
      try {
        await safeFetch("/v1/query_engines", { method: "GET" });
        if (apiHealthText) apiHealthText.textContent = "Backend: reachable";
        if (apiHealthPill) apiHealthPill.classList.add("online");
        showToast("Backend reachable.", "success");
      } catch (e) {
        if (apiHealthText) apiHealthText.textContent = "Backend: error";
        if (apiHealthPill) apiHealthPill.classList.remove("online");
        showToast(`Backend not reachable: ${e.message}`, "error", 5500);
      }
    });

  // New session button
  document
    .getElementById("newSessionBtn")
    ?.addEventListener("click", () => {
      selectedTables.splice(0, selectedTables.length);
      renderSelectedTables(selectedTables);
      setSqlOutput("");
      setLogsOutput("");
      renderResults([]);
      const promptEl = document.getElementById("userPrompt");
      if (promptEl) promptEl.value = "";
      const downloadBtn = document.getElementById("downloadCsvBtn");
      if (downloadBtn) downloadBtn.style.display = "none";
      showToast("Session cleared.", "success");
    });

  // Load metadata button
  document
    .getElementById("loadMetadataBtn")
    ?.addEventListener("click", async () => {
      setStatusPill("metadataStatus", "loading…", "busy");
      setLogsOutput("");
      try {
        const data = await safeFetch("/v1/metadata", { method: "GET" });
        
        console.log("Metadata response:", data);
        
        let rows = [];
        if (data) {
          if (Array.isArray(data.result)) {
            rows = data.result;
          } else if (Array.isArray(data)) {
            rows = data;
          } else if (data.status === 'SUCCESS' && Array.isArray(data.result)) {
            rows = data.result;
          } else if (data.result && typeof data.result === 'object' && !Array.isArray(data.result)) {
            const resultKeys = Object.keys(data.result);
            if (resultKeys.length > 0 && Array.isArray(data.result[resultKeys[0]])) {
              rows = data.result[resultKeys[0]];
            }
          }
        }
        
        const tableMap = new Map();
        
        rows.forEach((row) => {
          const catalog = row.catalog_name || row.catalog || '';
          const schema = row.schema_name || row.schema || '';
          const table = row.table_name || row.table || '';
          const comment = row.table_comment || row.comment || null;
          
          if (catalog && schema && table) {
            const key = `${catalog}.${schema}.${table}`;
            if (!tableMap.has(key)) {
              tableMap.set(key, {
                catalog: catalog,
                schema: schema,
                table: table,
                comment: comment
              });
            }
          }
        });
        
        const uniqueTables = Array.from(tableMap.values());
        
        let outputMessage = `Metadata loaded successfully.\n\n`;
        outputMessage += `Response Status: ${data?.status || 'N/A'}\n`;
        outputMessage += `Total Metadata Rows: ${rows.length}\n`;
        outputMessage += `Unique Tables Found: ${uniqueTables.length}\n\n`;
        
        if (rows.length > 0) {
          outputMessage += `Sample Metadata Row:\n`;
          outputMessage += `${JSON.stringify(rows[0], null, 2)}\n\n`;
          if (uniqueTables.length > 0) {
            outputMessage += `Sample Table:\n`;
            outputMessage += `${JSON.stringify(uniqueTables[0], null, 2)}\n\n`;
          }
        } else {
          outputMessage += `No rows found in expected format.\n\n`;
          outputMessage += `Full Response:\n${JSON.stringify(data, null, 2)}\n\n`;
        }
        
        setLogsOutput(outputMessage);
        
        if (uniqueTables.length > 0) {
          renderSearchResults(uniqueTables, (row) => {
            const exists = selectedTables.some(
              (t) =>
                t.catalog === row.catalog &&
                t.schema === row.schema &&
                t.table === row.table
            );
            if (!exists) {
              selectedTables.push({
                catalog: row.catalog,
                schema: row.schema,
                table: row.table,
              });
              renderSelectedTables(selectedTables);
            }
          });
          showToast(`Metadata loaded: ${uniqueTables.length} tables available.`, "success");
        } else {
          renderSearchResults([], () => {});
          showToast(`Metadata loaded but no tables found.`, "info");
        }
        
        setStatusPill("metadataStatus", "ready", "idle");
      } catch (e) {
        setStatusPill("metadataStatus", "error", "error");
        const errorMessage = `Error loading metadata:\n${e.message}\n\nStack trace:\n${e.stack || 'N/A'}`;
        setLogsOutput(errorMessage);
        renderSearchResults([], () => {});
        
        const logsTab = document.querySelector('.tab-btn[data-tab="logs"]');
        if (logsTab) {
          logsTab.click();
        }
        
        showToast(`Failed to load metadata: ${e.message}`, "error", 6500);
      }
    });

  // Search tables button
  document
    .getElementById("searchTablesBtn")
    ?.addEventListener("click", async () => {
      const input = document.getElementById("tableSearchInput");
      if (!input) return;
      const q = (input.value || "").trim();
      if (!q) {
        showToast("Enter a table name or keyword to search.", "error");
        return;
      }
      try {
        const data = await safeFetch(
          `/v1/search_tables?table=${encodeURIComponent(q)}`,
          { method: "GET" }
        );
        renderSearchResults(data, (row) => {
          const exists = selectedTables.some(
            (t) =>
              t.catalog === row.catalog &&
              t.schema === row.schema &&
              t.table === row.table
          );
          if (!exists) {
            selectedTables.push({
              catalog: row.catalog,
              schema: row.schema,
              table: row.table,
            });
            renderSelectedTables(selectedTables);
          }
        });
      } catch (e) {
        showToast(`Search failed: ${e.message}`, "error", 6000);
      }
    });

  // CSV Download button
  document
    .getElementById("downloadCsvBtn")
    ?.addEventListener("click", downloadCsv);

  // Run LLM query button
  document
    .getElementById("runLlmBtn")
    ?.addEventListener("click", async () => {
      const engineSel = document.getElementById("dbEngineSelect");
      const promptEl = document.getElementById("userPrompt");
      if (!engineSel || !promptEl) return;

      const db_selection = engineSel.value || "databricks";
      const user_input = (promptEl.value || "").trim();

      if (!user_input) {
        showToast("Please enter a question for the LLM.", "error");
        return;
      }

      if (!selectedTables.length) {
        showToast("Select at least one table for context.", "error");
        return;
      }

      setStatusPill("llmStatus", "running…", "busy");
      setSqlOutput("");
      renderResults([]);
      const downloadBtn = document.getElementById("downloadCsvBtn");
      if (downloadBtn) downloadBtn.style.display = "none";

      const sessionDb = document.getElementById("sessionDb");
      if (sessionDb) sessionDb.textContent = `Engine: ${db_selection}`;

      const payload = {
        db_selection,
        user_input,
        selected_tables: selectedTables.map((t) => ({
          catalog: t.catalog,
          schema: t.schema,
          table: t.table,
        })),
      };

      try {
        // Show loading in SQL tab first
        showLoading("sql", true);
        showLoading("results", true);
        
        // Switch to SQL tab to show loading
        const sqlTab = document.querySelector('.tab-btn[data-tab="sql"]');
        if (sqlTab) sqlTab.click();
        
        const resp = await safeFetch("/v1/llm", {
          method: "POST",
          body: JSON.stringify(payload),
        });

        // Hide loading indicators
        showLoading("sql", false);
        showLoading("results", false);

        // Display SQL in SQL tab - prioritize llm_generated_sql
        if (resp && resp.llm_generated_sql) {
          setSqlOutput(resp.llm_generated_sql);
        } else if (resp && resp.sql) {
          // Fallback for error responses
          setSqlOutput(resp.sql);
        } else if (typeof resp === "string") {
          setSqlOutput(resp);
        } else if (resp && resp.detail) {
          setSqlOutput(`Error: ${resp.detail}`);
        } else {
          setSqlOutput("No SQL generated");
        }

        // Display results in Results tab
        if (resp && resp.result && Array.isArray(resp.result)) {
          renderResults(resp.result);
        } else if (resp && resp.results && Array.isArray(resp.results)) {
          renderResults(resp.results);
        } else {
          // Clear results if none available
          renderResults([]);
        }

        setStatusPill("llmStatus", "done", "idle");
        showToast("Query completed.", "success");
      } catch (e) {
        showLoading("sql", false);
        showLoading("results", false);
        setStatusPill("llmStatus", "error", "error");
        setSqlOutput("");
        setLogsOutput(`LLM / execution error:\n${e.message}`);
        showToast(`LLM query failed: ${e.message}`, "error", 7500);
      }
    });

  // Allow Enter key to trigger search
  document
    .getElementById("tableSearchInput")
    ?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        document.getElementById("searchTablesBtn")?.click();
      }
    });
});
