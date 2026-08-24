// ==========================================================
//  CLEANER — Enhanced UI + Auto Refresh + Smart Column Panel
// ==========================================================

const $ = id => document.getElementById(id);

// ----------------------------
// Toast
// ----------------------------
function showToast(text, timeout = 2200) {
  const t = $("toast");
  if (!t) return;
  t.textContent = text;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), timeout);
}

// ----------------------------
// Loading pulse for right panel
// ----------------------------
function pulseTypesPanel() {
  const list = $("typesList");
  if (!list) return;
  list.style.opacity = "0.4";
  setTimeout(() => (list.style.opacity = "1"), 200);
}

// ----------------------------
// Update summary (left box)
// ----------------------------
function updateSummaryBox(summary) {
  $("rows").innerText = summary.rows ?? 0;
  $("columns").innerText = summary.columns ?? 0;
  $("duplicates").innerText = summary.duplicates ?? 0;
  $("missingTotal").innerText = summary.missing ?? summary.missing_values ?? 0;
  $("outliersTotal").innerText = summary.outliers ?? 0;
  $("skewedCount").innerText = summary.skewed ?? 0;
}

// ----------------------------
// Auto-refresh both panels
// ----------------------------
async function refreshAllPanels() {
  pulseTypesPanel();
  await loadColumnsAndTypes();
  await loadPreviewPanel();
}

// Refresh preview data
async function loadPreviewPanel() {
  try {
    const res = await axios.get("/clean/preview");
    $("cleanerPreview").innerHTML = res.data.html || "<div class='muted'>No preview</div>";
    updateSummaryBox(res.data.health || {});
  } catch (e) {
    console.error("Preview reload error", e);
  }
}

// ----------------------------
// Load uploaded preview
// ----------------------------
async function loadUploadedPreview() {
  try {
    const res = await axios.get("/load_uploaded");

    // Preview
    $("cleanerPreview").innerHTML =
      res.data.preview_html || "<div class='muted'>No preview available</div>";

    // Summary
    updateSummaryBox(res.data.summary || {});

    // Set filename
    if (res.data.filename) {
      $("loadedFilename").innerText = res.data.filename;
    } else {
      $("loadedFilename").innerText = "No file loaded";
    }

    await loadColumnsAndTypes();

    // Insights
    try {
      const ai = await axios.post("/upload/ai-insights", { filename: null });
      if (ai?.data?.summary) {
        $("insightText").innerText =
          `${ai.data.summary.rows} rows · ${ai.data.summary.columns} cols · duplicates ${ai.data.summary.duplicates}`;
      }
    } catch (_) {}

  } catch (err) {
    console.error("loadUploadedPreview error", err);
  if (!res.data.preview_html && !res.data.summary && !res.data.filename) {
    console.warn("No dataset found");
    return;
}
  }
}

async function cleanAction(endpoint) {
  try {
    const res = await axios.post(endpoint);

    if (res.data.preview_html) {
      $("cleanerPreview").innerHTML = res.data.preview_html;
    }

    if (res.data.summary) {
      updateSummaryBox(res.data.summary);
    }

    // 🔥 ALWAYS refresh preview + types after every cleaning action
    await loadPreviewPanel();
    await loadColumnsAndTypes();

    showToast("Action completed");
  } catch (err) {
    console.error("Clean action failed", err);
    alert(err.response?.data?.error || "Action failed");
  }
}

// ----------------------------
// Fill missing
// ----------------------------
function toggleFillPanel() {
  $("fillPanel").style.display = $("fillPanel").style.display === "none" ? "block" : "none";
}
async function doFill() {
  const method = $("fillMethod").value;
  await cleanAction(`/clean/fill_${method}`);
}

// ----------------------------
// Reset / Download
// ----------------------------
async function resetCleaner() {
  try {
    await axios.get("/clean/reset");
    await loadUploadedPreview();
    showToast("Reset to uploaded dataset");
  } catch (err) {
    console.error("Reset error", err);
    alert("Reset failed: " + (err.response?.data?.error || err));
  }
}

async function downloadCleaned() {
  try {
    const res = await axios.get("/clean/download", {
      responseType: "blob"
    });

    const blob = new Blob([res.data], { type: "text/csv" });

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;

    // optional filename fallback
    a.download = "cleaned_dataset.csv";

    document.body.appendChild(a);
    a.click();

    a.remove();
    window.URL.revokeObjectURL(url);

    showToast("Export started");
  } catch (err) {
    console.error(err);
    showToast("Export failed");
  }
}

// ----------------------------
// Columns & Types Loader
// ----------------------------
let CACHED_COLUMNS = [];
let CACHED_ROWS = 0;

async function loadColumnsAndTypes() {
  try {
    pulseTypesPanel();
    const res = await axios.get("/clean/preview");

    const types = res.data.types || {};
    const cols = Object.keys(types);
    CACHED_COLUMNS = cols;

    let html = "<ul>";
    if (!cols.length) {
      html += "<li class='muted'>No columns found</li>";
    } else {
      cols.forEach(c => {
        let t = types[c].toLowerCase();
        let color =
          t.includes("int") || t.includes("float") ? "style='color:#9cff9c'"
          : t.includes("date") ? "style='color:#ffd27f'"
          : "style='color:#aee2ff'";

        html += `<li><strong>${escapeHtml(c)}</strong> <span ${color}>(${escapeHtml(types[c])})</span></li>`;
      });
    }
    html += "</ul>";

    $("typesList").innerHTML = html;
  } catch (error) {
    $("typesList").innerHTML = "<div class='muted'>Failed to load columns</div>";
  }
}

function escapeHtml(s) {
  return String(s || "").replace(/&/g, "&amp;")
                       .replace(/</g, "&lt;")
                       .replace(/>/g, "&gt;");
}

// ----------------------------
// Formula Generator
// ----------------------------
function excelColLetter(n) {
  let s = "";
  while (n >= 0) {
    s = String.fromCharCode((n % 26) + 65) + s;
    n = Math.floor(n / 26) - 1;
  }
  return s;
}

function findColumnIndexByName(name) {
  if (!name) return -1;
  const lower = name.toLowerCase();

  for (let i = 0; i < CACHED_COLUMNS.length; i++)
    if (CACHED_COLUMNS[i].toLowerCase() === lower) return i;

  for (let i = 0; i < CACHED_COLUMNS.length; i++)
    if (CACHED_COLUMNS[i].toLowerCase().includes(lower)) return i;

  return -1;
}

function generateRangeForColIndex(idx) {
  if (idx < 0) return null;
  const start = 2;
  const end = Math.max(2, CACHED_ROWS + 1);
  return `${excelColLetter(idx)}${start}:${excelColLetter(idx)}${end}`;
}

function parseQueryToFormula(query) {
  if (!query.trim()) return { error: "Empty query" };
  const q = query.trim().toLowerCase();

  const funcs = ["sum", "avg", "average", "min", "max", "count distinct", "count", "trim"];
  for (let f of funcs) {
    if (q.startsWith(f)) {
      let col = q.replace(f, "").trim();
      let idx = findColumnIndexByName(col);
      if (idx === -1) return { error: `Column "${col}" not found` };

      switch (f) {
        case "sum": return { formula: `=SUM(${generateRangeForColIndex(idx)})` };
        case "avg":
        case "average": return { formula: `=AVERAGE(${generateRangeForColIndex(idx)})` };
        case "min": return { formula: `=MIN(${generateRangeForColIndex(idx)})` };
        case "max": return { formula: `=MAX(${generateRangeForColIndex(idx)})` };
        case "count distinct": return { formula: `=COUNTA(UNIQUE(${generateRangeForColIndex(idx)}))` };
        case "count": return { formula: `=COUNT(${generateRangeForColIndex(idx)})` };
        case "trim": return { formula: `=ARRAYFORMULA(TRIM(${generateRangeForColIndex(idx)}))` };
      }
    }
  }
  return { error: "Could not parse query" };
}

function generateFormula() {
  const q = $("nlQuery").value.trim();
  if (!q) return ($("formulaResult").innerText = "Type a query first");

  const out = parseQueryToFormula(q);
  $("formulaResult").innerText = out.error || out.formula;
  if (!out.error) window._CURRENT_FORMULA = out.formula;
}

function copyFormula() {
  if (!window._CURRENT_FORMULA) return showToast("No formula to copy");
  navigator.clipboard.writeText(window._CURRENT_FORMULA).then(() => showToast("Formula copied"));
}

function downloadFormula() {
  if (!window._CURRENT_FORMULA) return showToast("No formula to download");
  const blob = new Blob([window._CURRENT_FORMULA], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "formula.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ----------------------------
// Auto-clean
// ----------------------------
async function autoClean() {
  try {
    const res = await axios.post("/clean/auto");
    $("cleanerPreview").innerHTML = res.data.preview_html;

    updateSummaryBox(res.data.summary);
    $("autoCleanStatus").innerText = "Last Auto-Clean: ✓ Completed";
    $("autoCleanStatus").style.background = "#1d2c26";
    $("autoCleanStatus").style.color = "#b8ffd1";

    await loadColumnsAndTypes();
  } catch (err) {
    alert("Auto-clean failed.");
  }
}

// ----------------------------
// Full Cleaning Toolkit
// ----------------------------
async function removeSpecialChars() { await cleanAction("/clean/remove_special_chars"); }
async function trimSpaces() { await cleanAction("/clean/trim_spaces"); }
async function toLowerCase() { await cleanAction("/clean/to_lowercase"); }
async function toUpperCase() { await cleanAction("/clean/to_uppercase"); }
async function normalizeData() { await cleanAction("/clean/normalize"); }
async function standardizeData() { await cleanAction("/clean/standardize"); }
async function removeOutliers() { await cleanAction("/clean/remove_outliers"); }

async function dropColumn() {
  const col = prompt("Column to drop:");
  if (!col) return;
  await cleanAction(`/clean/drop_column?column=${encodeURIComponent(col)}`);
}

async function convertDtype() {
  const col = prompt("Column:");
  const dtype = prompt("New type (int/float/str/date):");
  if (!col || !dtype) return showToast("Missing input");
  await cleanAction(`/clean/convert_dtype?column=${col}&dtype=${dtype}`);
}

async function regexReplace() {
  const col = prompt("Column:");
  const pattern = prompt("Regex pattern:");
  const replacement = prompt("Replacement text:");
  if (!col || !pattern || replacement === null) return;
  await cleanAction(`/clean/regex_replace?column=${col}&pattern=${pattern}&replacement=${replacement}`);
}

async function extractSubstring() {
  const col = prompt("Column:");
  const start = prompt("Start index:");
  const end = prompt("End index (optional):");
  if (!col || start === null) return;
  await cleanAction(`/clean/extract_substring?column=${col}&start=${start}&end=${end || ""}`);
}

async function formatDate() {
  const col = prompt("Date column:");
  const fmt = prompt("Desired format (YYYY-MM-DD):");
  if (!col || !fmt) return;
  await cleanAction(`/clean/format_date?column=${col}&format=${fmt}`);
}

// ----------------------------
// Resizable panels
// ----------------------------
function makeDraggable(id) {
  const splitter = $(id);
  if (!splitter) return;

  let dragging = false, startX = 0, startLeft = 0, startRight = 0;

  splitter.addEventListener("mousedown", e => {
    dragging = true;
    startX = e.clientX;
    const left = splitter.previousElementSibling;
    const right = splitter.nextElementSibling;
    startLeft = left.getBoundingClientRect().width;
    startRight = right.getBoundingClientRect().width;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  window.addEventListener("mousemove", e => {
    if (!dragging) return;

    const dx = e.clientX - startX;
    const left = Math.max(180, startLeft + dx);
    const right = Math.max(180, startRight - dx);

    splitter.parentElement.style.gridTemplateColumns = `${left}px 8px auto 8px ${right}px`;
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });
}

// ----------------------------
// Init
// ----------------------------
window.addEventListener("DOMContentLoaded", async () => {
  await loadUploadedPreview();
  makeDraggable("splitter");
  makeDraggable("splitterR");

  const actions = {
    btnReload: loadUploadedPreview,
    btnAutoClean: autoClean,
    btnFillMissing: doFill,
    btnResetCleaner: resetCleaner,
    btnDownloadCleaned: downloadCleaned,
    btnGenerate: generateFormula,
    btnCopyFormula: copyFormula,
    btnDownloadFormula: downloadFormula,
    btnRemoveSpecial: removeSpecialChars,
    btnTrimSpaces: trimSpaces,
    btnLowerCase: toLowerCase,
    btnUpperCase: toUpperCase,
    btnNormalize: normalizeData,
    btnStandardize: standardizeData,
    btnRemoveOutliers: removeOutliers,
    btnDropColumn: dropColumn,
    btnConvertDtype: convertDtype,
    btnRegexReplace: regexReplace,
    btnExtractSubstring: extractSubstring,
    btnFormatDate: formatDate
  };

  Object.keys(actions).forEach(id => {
    const el = $(id);
    if (el) el.addEventListener("click", actions[id]);
  });

  $("nlQuery")?.addEventListener("keydown", e => {
    if (e.key === "Enter") generateFormula();
  });
  // Navigation button bindings
  const navUpload = $("btnGoUpload");
  if (navUpload) navUpload.addEventListener("click", () => { window.location.href = "/upload"; });

  const navVisualizer = $("btnGoVisualizer");
  if (navVisualizer) navVisualizer.addEventListener("click", () => { window.location.href = "/visualizer"; });

  const navScraper = $("btnGoScraper");
  if (navScraper) navScraper.addEventListener("click", () => { window.location.href = "/simplyhired"; });


});
