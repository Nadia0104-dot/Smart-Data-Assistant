let globalData = [];

async function startScraping() {

    const btn = document.getElementById("startBtn");
    const urls = document.getElementById("urls").value
        .split("\n")
        .map(u => u.trim())
        .filter(Boolean);

    if (!urls.length) {
        alert("Add Google Maps URLs first");
        return;
    }

    // RESET
    globalData = [];

    document.getElementById("resultsBody").innerHTML = "";
    document.getElementById("logs").innerHTML = "";
    document.getElementById("total").innerText = "0";


    const progressFill = document.getElementById("progress-fill");

    progressFill.style.width = "0%";

    btn.disabled = true;
    btn.innerHTML = `
        <span class="inline-block animate-spin mr-2">
            <i class="fas fa-spinner"></i>
        </span>
        Running...
    `;

    setStatus("Starting scraper...", "text-yellow-400");

    log("🚀 Scraper started");

    try {

        const response = await fetch("/scrape-stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ urls })
        });

        if (!response.ok) {
            throw new Error("Server error");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = "";

        while (true) {

            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const parts = buffer.split("\n\n");

            buffer = parts.pop();

            for (const part of parts) {

                if (!part.startsWith("data:")) continue;

                try {

                    const json = JSON.parse(
                        part.replace("data: ", "").trim()
                    );

                    // =========================
                    // PROGRESS
                    // =========================
                    if (json.type === "progress") {

                        const percent = (
                            (json.current / json.total) * 100
                        ).toFixed(0);

                        progressFill.style.width = `${percent}%`;

                        setStatus(
                            `Scraping ${json.current} / ${json.total}`,
                            "text-cyan-400"
                        );

                        log(`⚡ Progress ${json.current}/${json.total}`);
                    }

                    // =========================
                    // DATA
                    // =========================
                    if (json.type === "data") {

                        globalData.push(json.row);

                        appendRow(json.row);

                        updateMetrics(globalData);

                        log(`✅ ${json.row.Name || "Business scraped"}`);
                    }

                    // =========================
                    // DONE
                    // =========================
                    if (json.type === "done") {

                        progressFill.style.width = "100%";

                        setStatus(
                            `Completed (${globalData.length} results)`,
                            "text-green-400"
                        );

                        log("🎉 Scraping completed");

                        btn.disabled = false;

                        btn.innerHTML = "🚀 Start Scraping";
                    }

                } catch (err) {

                    console.log("JSON Parse Error:", err);
                }
            }
        }

    } catch (err) {

        console.log(err);

        setStatus("Scraping failed", "text-red-400");

        log("❌ Scraper failed");

        btn.disabled = false;
        btn.innerHTML = "🚀 Start Scraping";
    }
}

function appendRow(d) {

    const tbody = document.getElementById("resultsBody");

    const row = `
        <tr class="border-b border-gray-800 hover:bg-gray-900/40 transition">

            <td class="px-4 py-3 text-sm text-white">
                ${d.Name || "-"}
            </td>

            <td class="px-4 py-3 text-sm">
                ${
                    d.maps_url
                        ? `
                        <a
                            href="${d.maps_url}"
                            target="_blank"
                            class="text-cyan-400 hover:text-cyan-300 underline"
                        >
                            Open
                        </a>
                        `
                        : "-"
                }
            </td>

            <td class="px-4 py-3 text-sm text-gray-300">
                ${d.Rating || "-"}
            </td>

            <td class="px-4 py-3 text-sm text-gray-300 max-w-xs break-words">
                ${d.address || "-"}
            </td>

            <td class="px-4 py-3 text-sm text-gray-300">
                ${d.phone || "-"}
            </td>

            <td class="px-4 py-3 text-sm">
                ${
                    d.website_url
                        ? `
                        <a
                            href="${d.website_url}"
                            target="_blank"
                            class="text-green-400 hover:text-green-300 underline"
                        >
                            Visit
                        </a>
                        `
                        : "-"
                }
            </td>

        </tr>
    `;

    tbody.insertAdjacentHTML("beforeend", row);
}

function log(msg) {

    const logs = document.getElementById("logs");

    const time = new Date().toLocaleTimeString();

    logs.innerHTML += `
        <div class="text-gray-300 text-sm border-b border-gray-800 pb-1">
            <span class="text-gray-500 mr-2">${time}</span>
            ${msg}
        </div>
    `;

    logs.scrollTop = logs.scrollHeight;
}

function updateMetrics(data) {

    const total = data.length;

    document.getElementById("total").innerText = total;


}

function downloadCSV() {

    if (!globalData.length) {
        alert("No data available");
        return;
    }

    const headers = [
        "Name",
        "maps_url",
        "Rating",
        "address",
        "phone",
        "website_url"
    ];

    const rows = globalData.map(d => [
        d.Name || "",
        d.maps_url || "",
        d.Rating || "",
        d.address || "",
        d.phone || "",
        d.website_url || ""
    ]);

    const csv = [
        headers,
        ...rows
    ]
    .map(row =>
        row.map(value =>
            `"${String(value).replace(/"/g, '""')}"`
        ).join(",")
    )
    .join("\n");

    const blob = new Blob(
        [csv],
        { type: "text/csv;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");

    a.href = url;
    a.download = "maps_leads.csv";

    document.body.appendChild(a);

    a.click();

    document.body.removeChild(a);
}

function copyData() {

    if (!globalData.length) {
        alert("No data to copy");
        return;
    }

    // COPY CLEAN TABLE FORMAT
    const headers = [
        "Name",
        "maps_url",
        "Rating",
        "address",
        "phone",
        "website_url"
    ];

    let text = headers.join("\t") + "\n";

    globalData.forEach(d => {

        text += [
            d.Name || "",
            d.maps_url || "",
            d.Rating || "",
            d.address || "",
            d.phone || "",
            d.website_url || ""
        ].join("\t") + "\n";
    });

    navigator.clipboard.writeText(text);

    setStatus("Copied table data", "text-green-400");

    log("📋 Data copied");
}

function setStatus(text, color = "text-cyan-400") {

    const box = document.getElementById("statusBox");

    box.className = `${color} text-sm font-medium`;

    box.innerText = text;
}

function filterTable() {

    const input = document
        .getElementById("search")
        .value
        .toLowerCase();

    const rows = document.querySelectorAll("#resultsBody tr");

    rows.forEach(row => {

        const text = row.innerText.toLowerCase();

        row.style.display =
            text.includes(input)
                ? ""
                : "none";
    });
}