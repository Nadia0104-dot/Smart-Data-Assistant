// ================= GLOBAL STATE =================
let eventSource = null;
let allJobs = [];
let filteredJobs = [];
let resumeSkills = [];
let activePortal = "simplyhired";

// ================= DOM READY =================
document.addEventListener("DOMContentLoaded", () => {

  // ================= ELEMENTS =================
  const stopBtn = document.getElementById("stopBtn");
  const clearBtn = document.getElementById("clearBtn");

  const analyzeResumeBtn = document.getElementById("analyzeResumeBtn");
  const rankJobsBtn = document.getElementById("rankJobsBtn");

  const generateSummaryBtn = document.getElementById("generateSummaryBtn");
  const marketBtn = document.getElementById("marketBtn");

  const exportCsvBtn = document.getElementById("exportCsvBtn");
  const exportJsonBtn = document.getElementById("exportJsonBtn");

  const resultsArea = document.getElementById("resultsArea");
  const statusBox = document.getElementById("statusBox");
  const liveCount = document.getElementById("liveCount");
  const progressBar = document.getElementById("progressBar");
  const logArea = document.getElementById("logArea");

  const searchInput = document.getElementById("searchInput");
  const jobPreview = document.getElementById("jobPreview");

  const jobInput = document.getElementById("jobInput");
  const locationInput = document.getElementById("locationInput");

  const resumeText = document.getElementById("resumeText");

  const fullDesc = document.getElementById("fullDesc");

  // ================= HELPERS =================
  function appendLog(msg) {
    const p = document.createElement("div");
    p.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    logArea.appendChild(p);
    logArea.scrollTop = logArea.scrollHeight;
  }

  function resetResults() {
    allJobs = [];
    filteredJobs = [];

    resultsArea.innerHTML = `
      <div class="col-span-full text-center text-gray-500">
        AI results will appear here
      </div>
    `;

    liveCount.textContent = "0";
    progressBar.style.width = "0%";

    exportCsvBtn.style.display = "none";
    exportJsonBtn.style.display = "none";

    document.getElementById("jobPreview").innerHTML = "Select a job";
  }

  // ================= PORTALS =================
  document.querySelectorAll(".portal-btn").forEach(btn => {

    btn.addEventListener("click", () => {

      document.querySelectorAll(".portal-btn").forEach(b => {
        b.classList.remove("bg-cyan-500");
      });

      btn.classList.add("bg-cyan-500");

      activePortal = btn.dataset.portal;

      startScraper(activePortal);
    });
  });

  // ================= SCRAPER =================
  function startScraper(portal) {

    const job = jobInput.value.trim();
    const location = locationInput.value.trim();

    if (!job || !location) {
      alert("Enter job & location");
      return;
    }

    resetResults();

    statusBox.textContent = `Scraping ${portal}...`;

    appendLog(`🚀 Starting ${portal} scraper...`);

    if (eventSource) {
      eventSource.close();
    }

    const url =
      `/api/scrape?portal=${encodeURIComponent(portal)}` +
      `&job=${encodeURIComponent(job)}` +
      `&location=${encodeURIComponent(location)}` +
      `&pages=1` +
      `&full=${fullDesc.checked}`;

    eventSource = new EventSource(url);

    eventSource.onmessage = (e) => {

      let data;

      try {
        data = JSON.parse(e.data);
      } catch {
        appendLog(e.data);
        return;
      }

      if (data.log) {
        appendLog(data.log);
      }

      if (data.job) {
        addJob(data.job);
      }

      if (data.progress) {
        progressBar.style.width = `${data.progress}%`;
      }

      if (data.done) {

        appendLog("✅ Scraping completed");

        statusBox.textContent = "Completed";

        eventSource.close();

        processJobs(allJobs);
      }
    };

    eventSource.onerror = () => {

      if (eventSource.readyState === EventSource.CLOSED) {
        appendLog("❌ Stream closed");
      } else {
        appendLog("⚠ Connection interrupted");
      }
    };
  }

  stopBtn.onclick = () => {

    if (eventSource) {
      eventSource.close();
    }

    appendLog("⛔ Scraper stopped");

    statusBox.textContent = "Stopped";
  };

  clearBtn.onclick = resetResults;

  // ================= ADD JOB =================
  function addJob(job) {

    if (!job) return;

    allJobs.push(job);

    renderResults(allJobs);

    liveCount.textContent = allJobs.length;
  }

  // ================= AI PROCESS =================
  async function processJobs(jobs) {

    appendLog("🧠 Running AI enrichment...");

    try {

      const res = await fetch("/api/enrich_jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          jobs,
          resume_skills: resumeSkills
        })
      });

      const data = await res.json();

      allJobs = data.jobs || [];

      renderResults(allJobs);

      appendLog("✅ AI enrichment completed");

    } catch (err) {

      console.error(err);

      appendLog("❌ AI enrichment failed");
    }
  }

  // ================= RENDER =================
  function renderResults(jobs) {

    resultsArea.innerHTML = "";

    if (!jobs.length) {

      resultsArea.innerHTML = `
        <div class="col-span-full text-gray-500 text-center">
          No jobs found
        </div>
      `;

      return;
    }

    jobs.forEach(job => {

      const card = document.createElement("div");

      card.className =
        "panel cursor-pointer hover:border-cyan-400 transition";

      card.innerHTML = `
        <div class="font-semibold text-white">
          ${job.title || "Untitled"}
        </div>

        <div class="text-sm text-gray-400">
          ${job.company || ""}
        </div>

        <div class="text-sm mt-1">
          📍 ${job.location || ""}
        </div>

        ${
          job.score !== undefined
          ? `<div class="mt-2 text-cyan-400">🎯 Match ${job.score}%</div>`
          : ""
        }

        ${
          job.salary_estimate
          ? `<div class="text-green-400">💰 ${job.salary_estimate}</div>`
          : ""
        }
      `;

      card.onclick = () => showPreview(job);

      resultsArea.appendChild(card);
    });

    exportCsvBtn.style.display = "inline-block";
    exportJsonBtn.style.display = "inline-block";
  }

  // ================= PREVIEW =================
  function showPreview(job) {

    jobPreview.innerHTML = `
      <h3 class="text-lg font-semibold mb-2">${job.title || ""}</h3>

      <p>${job.company || ""}</p>

      <p class="mb-2">${job.location || ""}</p>

      <p><b>Match:</b> ${job.score || 0}%</p>

      <p><b>Salary:</b> ${job.salary_estimate || "N/A"}</p>

      <p class="mt-2">
        <b>Skills:</b>
        ${(job.skills || []).join(", ")}
      </p>

      <pre class="whitespace-pre-wrap text-xs mt-3 text-gray-300">
${job.description || job.snippet || "No description"}
      </pre>
    `;
  }

  // ================= SEARCH =================
  searchInput.oninput = () => {

    const q = searchInput.value.toLowerCase();

    filteredJobs = allJobs.filter(j =>
      JSON.stringify(j).toLowerCase().includes(q)
    );

    renderResults(filteredJobs);
  };

   // ================= ANALYZE RESUME =================
  analyzeResumeBtn.onclick = async () => {

    const text = resumeText.value.trim();

    if (!text) {
      alert("Paste resume or skills");
      return;
    }

    appendLog("📄 Analyzing resume...");

    try {

      const res = await fetch("/api/analyze_resume_text", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ text })
      });

      const data = await res.json();

      resumeSkills = data.skills || [];

      appendLog(`✅ Found ${resumeSkills.length} skills`);

      appendLog(resumeSkills.join(", "));

    } catch (err) {

      console.error(err);

      appendLog("❌ Resume analysis failed");
    }
  };

  // ================= MATCH SCORE =================
  rankJobsBtn.onclick = async () => {

    if (!allJobs.length) {
      alert("No jobs available");
      return;
    }

    appendLog("🧠 Calculating job match scores...");

    try {

      const res = await fetch("/api/rank_jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          jobs: allJobs
        })
      });

      const data = await res.json();

      allJobs = data.jobs || [];

      renderResults(allJobs);

      appendLog("✅ Ranking complete");

    } catch (err) {

      console.error(err);

      appendLog("❌ Ranking failed");
    }
  };

  // ================= AI SUMMARY =================
  if (generateSummaryBtn) {

    generateSummaryBtn.onclick = async () => {

      if (!allJobs.length) {
        alert("No jobs available");
        return;
      }

      appendLog("🧠 Generating AI insights...");

      try {

        const res = await fetch("/api/ai_insight", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            jobs: allJobs
          })
        });

        const data = await res.json();

        document.getElementById("aiSummary").textContent =
          data.insight || "No insight";

        appendLog("✅ Insights generated");

      } catch (err) {

        console.error(err);

        appendLog("❌ Insight generation failed");
      }
    };
  }

  // ================= MARKET =================
  if (marketBtn) {

    marketBtn.onclick = async () => {

      if (!allJobs.length) return;

      appendLog("📊 Loading market trends...");

      try {

        const res = await fetch("/api/analytics", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            jobs: allJobs
          })
        });

        const data = await res.json();

        const charts = document.getElementById("chartsContainer");

        charts.outerHTML = `
          <div id="chartsContainer" class="text-xs whitespace-pre-wrap text-gray-300">
🔥 Skills:
${JSON.stringify(data.skills, null, 2)}

🏢 Companies:
${JSON.stringify(data.companies, null, 2)}

📍 Locations:
${JSON.stringify(data.locations, null, 2)}
          </div>
        `;

        appendLog("✅ Market analytics loaded");

      } catch (err) {

        console.error(err);

        appendLog("❌ Analytics failed");
      }
    };
  }


  // ================= EXPORT HELPERS =================
  function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }

  function getExportPayload() {
    return {
      jobs: allJobs,
      exported_at: new Date().toISOString(),
      total_jobs: allJobs.length,
      portal: activePortal,
      query: {
        job: document.getElementById("jobInput").value,
        location: document.getElementById("locationInput").value
      }
    };
  }

  // ================= EXPORT CSV =================
  exportCsvBtn.onclick = async () => {

    if (!allJobs.length) {
      alert("No jobs to export");
      return;
    }

    appendLog("📄 Preparing CSV export...");

    try {

      const res = await fetch("/api/export/csv", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(getExportPayload())
      });

      if (!res.ok) throw new Error("CSV export failed");

      const blob = await res.blob();

      const filename = `jobs_${activePortal}_${Date.now()}.csv`;

      downloadBlob(blob, filename);

      appendLog("✅ CSV exported successfully");

    } catch (err) {
      console.error(err);
      appendLog("❌ CSV export failed");
    }
  };

  // ================= EXPORT EXCEL =================
  document.getElementById("exportExcelBtn")?.addEventListener("click", async () => {

    if (!allJobs.length) {
      alert("No jobs to export");
      return;
    }

    appendLog("📊 Preparing Excel export...");

    try {

      const res = await fetch("/api/export/excel", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(getExportPayload())
      });

      if (!res.ok) throw new Error("Excel export failed");

      const blob = await res.blob();

      const filename = `jobs_${activePortal}_${Date.now()}.xlsx`;

      downloadBlob(blob, filename);

      appendLog("✅ Excel exported successfully");

    } catch (err) {
      console.error(err);
      appendLog("❌ Excel export failed");
    }
  });

  // ================= EXPORT JSON =================
  exportJsonBtn.onclick = async () => {

    if (!allJobs.length) {
      alert("No jobs to export");
      return;
    }

    appendLog("🧠 Preparing JSON export...");

    try {

      const blob = new Blob(
        [JSON.stringify(getExportPayload(), null, 2)],
        { type: "application/json" }
      );

      const filename = `jobs_${activePortal}_${Date.now()}.json`;

      downloadBlob(blob, filename);

      appendLog("✅ JSON exported successfully");

    } catch (err) {
      console.error(err);
      appendLog("❌ JSON export failed");
    }
  };

});