// static/js/visualizer.js (Level 2 — interactive + dashboard + localStorage)
(async () => {
  // DOM refs
  const datasetSel = document.getElementById('vs-dataset');
  const colSel = document.getElementById('vs-column');
  const yColSel = document.getElementById('vs-y-column'); // multiple
  const colorSel = document.getElementById('vs-color');
  const chartTypeSel = document.getElementById('vs-chart-type');
  const renderBtn = document.getElementById('vs-render');
  const addCardBtn = document.getElementById('vs-add-card');
  const plotArea = document.getElementById('vs-plot-area');
  const previewTable = document.getElementById('vs-preview-table');
  const insightsDiv = document.getElementById('vs-insights');
  const recommendDiv = document.getElementById('vs-recommend');
  const filterCol = document.getElementById('vs-filter-col');
  const filterVal = document.getElementById('vs-filter-val');
  const applyFilterBtn = document.getElementById('vs-apply-filter');
  const clearFilterBtn = document.getElementById('vs-clear-filter');
  const binsInput = document.getElementById('vs-bins');
  const titleInput = document.getElementById('vs-title');
  const colorInput = document.getElementById('vs-color-input');
  const trendlineChk = document.getElementById('vs-trendline');
  const saveConfigBtn = document.getElementById('vs-save-config');
  const savedList = document.getElementById('vs-saved-list');
  const clearSavedBtn = document.getElementById('vs-clear-saved');
  const dashboardEl = document.getElementById('vs-dashboard');
  const exportDashboardBtn = document.getElementById('vs-export-dashboard');

  const downloadCsvBtn = document.getElementById('vs-download-csv');
  const themeSel = document.getElementById('vs-theme');

  let currentDataset = datasetSel.value;
  let activeFilters = null;
  let lastPlotElement = null; // plotly element
  let currentPlotMetadata = null; // used when adding to dashboard

  // --- helpers
  async function getJSON(url) {
    const r = await fetch(url);
    return r.json();
  }
  async function postJSON(url, body) {
    try {
      const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      const text = await r.text();  // first get as text
      try {
        return JSON.parse(text);    // try parse as JSON
      } catch(e) {
        // Not JSON, probably HTML error page
        return { error: `Server returned invalid JSON. Response: ${text.substring(0,200)}...` };
      }
    } catch(err) {
      return { error: `Request failed: ${err}` };
    }
  }


  // --- load columns
  async function loadColumns() {
    const data = await getJSON(`/visualizer/columns?dataset=${currentDataset}`);
    populateSelect(colSel, data.numeric.concat(data.categorical));
    populateSelectMulti(yColSel, data.numeric.concat(data.categorical));
    populateSelect(colorSel, [''].concat(data.categorical));
    populateSelect(filterCol, [''].concat(data.numeric.concat(data.categorical)));
  }

  function populateSelect(sel, values) {
    sel.innerHTML = '';
    values.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); });
  }
  function populateSelectMulti(sel, values) {
    sel.innerHTML = '';
    values.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); });
  }



  function renderPreview(rows) {
    if (!rows || rows.length === 0) { previewTable.innerHTML = '<div class="small">No preview</div>'; return; }
    const cols = Object.keys(rows[0]);
    let html = '<table><thead><tr>' + cols.map(c => `<th>${escapeHtml(c)}</th>`).join('') + '</tr></thead><tbody>';
    rows.forEach(r => {
      html += '<tr>' + cols.map(c => `<td>${escapeHtml(String(r[c] === null ? '' : r[c]))}</td>`).join('') + '</tr>';
    });
    html += '</tbody></table>';
    previewTable.innerHTML = html;
  }

  function renderInsights(ins) {
    const basic = ins.basic || {};
    let out = `<p><strong>Rows:</strong> ${basic.rows || 0}</p>`;
    out += `<p><strong>Cols:</strong> ${basic.columns || 0}</p>`;
    out += `<p><strong>Duplicates:</strong> ${basic.duplicates || 0}</p>`;
    out += `<p><strong>Missing:</strong> ${Object.values(basic.missing_per_column || {}).reduce((a,b)=>a+(b||0),0)}</p>`;
    insightsDiv.innerHTML = out;
    recommendDiv.innerHTML = `<p class="small">Suggested: ${suggestionText()}</p>`;
  }

  function suggestionText() {
    const x = colSel.value, ys = selectedY();
    if (ys.length > 1) return 'Multi-series chart (use line or stacked bar)';
    if (x && ys.length === 1) {
      // basic heuristic
      const y = ys[0];
      return 'Scatter/Line if both numeric, else Bar/Histogram';
    }
    return 'Heatmap or Scatter Matrix';
  }

  // get selected y columns array
  function selectedY() {
    return Array.from(yColSel.selectedOptions).map(o => o.value).filter(Boolean);
  }

  // --- render Plotly (supports multi-series & trendline client-side)
  async function renderPlot() {
    const chartType = chartTypeSel.value;
    const x = colSel.value || null;
    const ys = selectedY();
    const color = colorSel.value || null;
    const title = titleInput.value || null;
    const bins = parseInt(binsInput.value) || null;

    // build payload for backend (single series requested approach)
    // If multiple Y selected we'll request traces for first series and build others locally via backend calls
    // But best approach: ask backend for traces for chart_type with x,y (single) OR for histogram/heatmap use backend directly
    // We'll loop over Ys and combine traces.
    if (!x && chartType !== 'heatmap') {
      alert('Select X column (or use heatmap)');
      return;
    }

    // prepare filters (if range format "min,max" for numeric)
    let filters = activeFilters || null;

    // if multiple Y: request trace for each y sequentially from /visualizer/plotly and combine
    let combined = {data: [], layout: {}};
    try {
      if (ys.length <= 1) {
        const payload = {dataset: currentDataset, chart_type: chartType, x_column: x, y_column: ys[0] || null, filters};
        if (bins) payload.bins = bins;
        // area chart specific: if area and y provided, ensure fill set on backend (backend supports area)
        const res = await postJSON('/visualizer/plotly', payload);
        if (res.error) { plotArea.innerHTML = `<div class="small" style="color:#f66">${escapeHtml(res.error)}</div>`; return; }
        combined = res.plotly || {data: [], layout: {}};
        // if backend returned fig as plotly object (like px violin) it may not be under plotly key; handle gracefully
        if (res.plotly) {
          // ok
        } else if (res.plotly === undefined && res.plotly_obj) {
          combined = res.plotly_obj;
        }
        // overlay trendline if requested and single numeric series
        if (trendlineChk.checked && ys.length === 1 && (chartType === 'scatter' || chartType === 'line' || chartType === 'area')) {
          addTrendlineToPlotlyObject(combined, x, ys[0]);
        }
      } else {
        // multi-series: request backend per-y and combine
        for (let i = 0; i < ys.length; ++i) {
          const y = ys[i];
          const payload = {dataset: currentDataset, chart_type: chartType, x_column: x, y_column: y, filters};
          if (bins) payload.bins = bins;
          const res = await postJSON('/visualizer/plotly', payload);
          if (res.error) { console.warn('trace error', res.error); continue; }
          const p = res.plotly || res;
          // ensure trace colors differ
          p.data.forEach((t, idx) => {
            // give color if missing
            if (!t.marker && !t.line) t.marker = {color: getPaletteColor(i)};
            combined.data.push(t);
          });
          if (!combined.layout.title) combined.layout.title = p.layout && p.layout.title ? p.layout.title : '';
          // keep insights from last call (also show aggregated insights from /visualizer/insights later)
        }
        // optionally add trendlines per series
        if (trendlineChk.checked) {
          ys.forEach((y, i) => addTrendlineToPlotlyObject(combined, x, y, getPaletteColor(i)));
        }
      }

      // apply title/color overrides
      if (title) combined.layout.title = title;
      if (colorInput.value && combined.data && combined.data.length) {
        combined.data.forEach(d => {
          if (d.marker) d.marker.color = colorInput.value;
          if (d.line) d.line.color = colorInput.value;
        });
      }

      // theme adjustments
      if (themeSel && themeSel.value === 'dark') {
        combined.layout.paper_bgcolor = '#071124';
        combined.layout.plot_bgcolor = '#071124';
        combined.layout.font = Object.assign({}, combined.layout.font || {}, {color: '#e6eef6'});
      } else {
        combined.layout.paper_bgcolor = '#ffffff';
        combined.layout.plot_bgcolor = '#ffffff';
        combined.layout.font = Object.assign({}, combined.layout.font || {}, {color: '#111827'});
      }

      // render
      plotArea.innerHTML = '<div id="plotly-canvas" style="width:100%;height:520px;"></div>';
      const el = document.getElementById('plotly-canvas');
      await Plotly.newPlot(el, combined.data, combined.layout, {responsive:true});
      lastPlotElement = el;
      currentPlotMetadata = {dataset: currentDataset, chartType, x, ys, title, color: colorInput.value || null, filters};
      // refresh insights
      const ins = await postJSON('/visualizer/insights', {dataset: currentDataset});
      if (!ins.error) renderInsights(ins);
    } catch (err) {
      console.error(err);
      plotArea.innerHTML = `<div class="small" style="color:#f66">Render failed: ${escapeHtml(String(err))}</div>`;
    }
  }

  // --- trendline (simple linear regression) overlay
  function addTrendlineToPlotlyObject(plotlyObj, xCol, yCol, color) {
    try {
      // extract x and y arrays from first series where y matches (best-effort)
      // If original traces contain x/y arrays, compute fit on them.
      let xvals = null, yvals = null;
      if (plotlyObj.data && plotlyObj.data.length) {
        // try to find trace whose y length > 1
        for (let t of plotlyObj.data) {
          if (t.x && t.y && t.x.length >= 2 && t.y.length >= 2) { xvals = t.x.map(n => Number(n)); yvals = t.y.map(n => Number(n)); break; }
        }
      }
      if (!xvals || !yvals) return;
      // linear regression (y = a + b x)
      const n = xvals.length;
      const sx = xvals.reduce((a,b)=>a+b,0);
      const sy = yvals.reduce((a,b)=>a+b,0);
      const sxx = xvals.reduce((a,b)=>a+b*b,0);
      const sxy = xvals.reduce((a,b,i)=>a + b*yvals[i],0);
      const denom = (n*sxx - sx*sx);
      if (denom === 0) return;
      const b = (n*sxy - sx*sy)/denom;
      const a = (sy - b*sx)/n;
      const fitY = xvals.map(x => a + b * x);
      // overlay trace
      const tline = {x: xvals, y: fitY, type:'scatter', mode:'lines', name:'Trendline', line:{dash:'dash', width:2, color: color || '#00bcd4'}};
      plotlyObj.data.push(tline);
    } catch (e) {
      console.warn('trendline error', e);
    }
  }

  // utility palette
  function getPaletteColor(i) {
    const p = ['#3b82f6','#ef4444','#f59e0b','#10b981','#8b5cf6','#06b6d4','#f97316'];
    return p[i % p.length];
  }

  // --- saved configs (localStorage)
  function loadSavedConfigs() {
    const arr = JSON.parse(localStorage.getItem('dsa_visualizer_configs') || '[]');
    renderSavedList(arr);
  }
  function saveConfig() {
    const cfg = {
      id: Date.now(),
      dataset: datasetSel.value,
      x: colSel.value,
      ys: selectedY(),
      color: colorSel.value || null,
      chartType: chartTypeSel.value,
      title: titleInput.value || null,
      bins: binsInput.value || null,
      trendline: trendlineChk.checked
    };
    const arr = JSON.parse(localStorage.getItem('dsa_visualizer_configs') || '[]');
    arr.unshift(cfg);
    localStorage.setItem('dsa_visualizer_configs', JSON.stringify(arr));
    loadSavedConfigs();
  }
  function renderSavedList(arr) {
    savedList.innerHTML = '';
    if (!arr.length) { savedList.innerHTML = '<div class="small">No saved configs</div>'; return; }
    arr.forEach(cfg => {
      const d = document.createElement('div'); d.className = 'small saved-item';
      d.innerHTML = `<div><strong>${escapeHtml(cfg.title || cfg.chartType)}</strong><div class="small">${escapeHtml(cfg.x || '')} → ${escapeHtml((cfg.ys||[]).join(','))}</div></div>`;
      const b1 = document.createElement('button'); b1.className='btn ghost'; b1.textContent='Apply'; b1.onclick = ()=> applySaved(cfg);
      const b2 = document.createElement('button'); b2.className='btn ghost'; b2.textContent='Delete'; b2.onclick = ()=> deleteSaved(cfg.id);
      const wrap = document.createElement('div'); wrap.style.display='flex'; wrap.style.gap='6px'; wrap.appendChild(b1); wrap.appendChild(b2);
      d.appendChild(wrap);
      savedList.appendChild(d);
    });
  }
  function applySaved(cfg) {
    datasetSel.value = cfg.dataset || 'uploaded';
    currentDataset = datasetSel.value;
    loadColumns().then(()=> {
      colSel.value = cfg.x || '';
      // select Ys
      Array.from(yColSel.options).forEach(o => o.selected = (cfg.ys||[]).includes(o.value));
      chartTypeSel.value = cfg.chartType || 'bar';
      titleInput.value = cfg.title || '';
      binsInput.value = cfg.bins || '';
      trendlineChk.checked = !!cfg.trendline;
      renderPlot();
    });
  }
  function deleteSaved(id) {
    let arr = JSON.parse(localStorage.getItem('dsa_visualizer_configs') || '[]');
    arr = arr.filter(a=>a.id !== id);
    localStorage.setItem('dsa_visualizer_configs', JSON.stringify(arr));
    loadSavedConfigs();
  }
  function clearSaved() {
    localStorage.removeItem('dsa_visualizer_configs');
    loadSavedConfigs();
  }

  // --- dashboard cards (client-side persistent)
  function addCardFromCurrentPlot() {
    if (!currentPlotMetadata || !lastPlotElement) { alert('Render a chart first'); return; }
    // save a snapshot image of current plot using Plotly.toImage
    Plotly.toImage(lastPlotElement, {format:'png', width:1000, height:600}).then(dataUrl => {
      const card = {
        id: Date.now(),
        title: currentPlotMetadata.title || `${currentPlotMetadata.chartType} - ${currentPlotMetadata.x}`,
        img: dataUrl,
        meta: currentPlotMetadata
      };
      const arr = JSON.parse(localStorage.getItem('dsa_visualizer_cards') || '[]');
      arr.unshift(card);
      localStorage.setItem('dsa_visualizer_cards', JSON.stringify(arr));
      renderDashboard();
    }).catch(err => {
      console.warn('card capture failed', err);
      alert('Failed to capture chart image. Try again.');
    });
  }

  function renderDashboard() {
    const arr = JSON.parse(localStorage.getItem('dsa_visualizer_cards') || '[]');
    dashboardEl.innerHTML = '';
    if (!arr.length) { dashboardEl.innerHTML = '<div class="small">No cards yet — add charts to dashboard</div>'; return; }
    arr.forEach(card => {
      const el = document.createElement('div'); el.className='card'; el.draggable=true; el.dataset.cardId = card.id;
      el.innerHTML = `<div class="card-head"><div class="meta"><strong>${escapeHtml(card.title)}</strong><div class="small">${escapeHtml(card.meta.chartType)} • ${escapeHtml(card.meta.x)} → ${escapeHtml((card.meta.ys||[]).join(','))}</div></div>
        <div class="card-actions">
          <button class="btn ghost btn-export">PNG</button>
          <button class="btn ghost btn-remove">Remove</button>
        </div></div>
        <div class="card-body"><img src="${card.img}" style="max-width:100%;border-radius:6px" /></div>`;
      // actions
      el.querySelector('.btn-remove').onclick = () => { removeCard(card.id); };
      el.querySelector('.btn-export').onclick = () => { downloadDataUrl(card.img, `${card.title || 'card'}.png`); };
      // drag events
      el.addEventListener('dragstart', onCardDragStart);
      el.addEventListener('dragover', onCardDragOver);
      el.addEventListener('drop', onCardDrop);
      dashboardEl.appendChild(el);
    });
  }
  function removeCard(id) {
    let arr = JSON.parse(localStorage.getItem('dsa_visualizer_cards') || '[]');
    arr = arr.filter(a=>a.id !== id);
    localStorage.setItem('dsa_visualizer_cards', JSON.stringify(arr));
    renderDashboard();
  }
  function downloadDataUrl(dataUrl, filename) {
    const a = document.createElement('a'); a.href = dataUrl; a.download = filename; a.click();
  }

  // drag & drop ordering
  let dragSrcId = null;
  function onCardDragStart(e) { dragSrcId = this.dataset.cardId; e.dataTransfer.effectAllowed = 'move'; }
  function onCardDragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
  function onCardDrop(e) {
    e.preventDefault();
    const tgtId = this.dataset.cardId;
    if (!dragSrcId || !tgtId || dragSrcId === tgtId) return;
    let arr = JSON.parse(localStorage.getItem('dsa_visualizer_cards') || '[]');
    const srcIdx = arr.findIndex(c=>String(c.id)===String(dragSrcId));
    const tgtIdx = arr.findIndex(c=>String(c.id)===String(tgtId));
    if (srcIdx === -1 || tgtIdx === -1) return;
    const [item] = arr.splice(srcIdx,1);
    arr.splice(tgtIdx,0,item);
    localStorage.setItem('dsa_visualizer_cards', JSON.stringify(arr));
    renderDashboard();
  }

  // export dashboard as simple HTML with embedded images
  function exportDashboardAsHtml() {
    const arr = JSON.parse(localStorage.getItem('dsa_visualizer_cards') || '[]');
    if (!arr.length) { alert('No cards to export'); return; }
    let html = `<!doctype html><html><head><meta charset="utf-8"><title>Dashboard Export</title></head><body>`;
    html += `<h1>DataSenseAI Dashboard Export</h1>`;
    arr.forEach(c => {
      html += `<h3>${escapeHtml(c.title || '')}</h3><img src="${c.img}" style="max-width:100%;height:auto;display:block;margin-bottom:24px;border:1px solid #ccc"/>`;
    });
    html += `</body></html>`;
    const blob = new Blob([html], {type:'text/html'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'dashboard_export.html'; a.click();
    URL.revokeObjectURL(url);
  }

  // --- utility
  function escapeHtml(s){ return String(s).replace(/[&<>"'`=\/]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','=':'&#x3D;','`':'&#x60'}[c])); }

  // --- apply/clear filter
  applyFilterBtn.addEventListener('click', () => {
    const fc = filterCol.value, fv = filterVal.value.trim();
    if (!fc || !fv) { alert('Select column and value/range'); return; }
    if (fv.includes(',')) {
      const parts = fv.split(',').map(s=>s.trim()).filter(Boolean);
      if (parts.length === 2 && !isNaN(Number(parts[0])) && !isNaN(Number(parts[1]))) {
        activeFilters = {}; activeFilters[fc] = [Number(parts[0]), Number(parts[1])];
      } else {
        activeFilters = {}; activeFilters[fc] = fv;
      }
    } else {
      activeFilters = {}; activeFilters[fc] = fv;
    }
    renderPlot();
  });
  clearFilterBtn.addEventListener('click', () => { activeFilters = null; filterVal.value=''; renderPreviewAndColumns(); });

  // saved configs
  saveConfigBtn.addEventListener('click', saveConfig);
  clearSavedBtn.addEventListener('click', clearSaved);

  // render / add card
  renderBtn.addEventListener('click', renderPlot);
  addCardBtn.addEventListener('click', addCardFromCurrentPlot);

  // dashboard controls
  exportDashboardBtn.addEventListener('click', exportDashboardAsHtml);
 

  downloadCsvBtn.addEventListener('click', () => { window.location.href = '/visualizer/download'; });

  // theme
  if (themeSel) themeSel.addEventListener('change', (e) => {
    if (e.target.value === 'light') document.body.style.background = 'linear-gradient(180deg,#f8fafc 0%, #eef2ff 100%)';
    else document.body.style.background = 'linear-gradient(180deg,#020617 0%, #071022 100%)';
  });

  // initial boot
  async function renderPreviewAndColumns() {
    await loadColumns();
    await loadPreviewAndInsights();
    loadSavedConfigs();
    renderDashboard();
  }

  // load columns + preview
  async function loadPreviewAndInsights() {
    const pv = await getJSON(`/visualizer/preview?dataset=${currentDataset}`);
    if (!pv.error) renderPreview(pv.preview || []);
    const ins = await getJSON(`/visualizer/insights?dataset=${currentDataset}`);
    if (!ins.error) renderInsights(ins);
  }

  // when dataset changed
  datasetSel.addEventListener('change', async () => {
    currentDataset = datasetSel.value;
    await renderPreviewAndColumns();
  });

  // initial load
  await renderPreviewAndColumns();
  // helpful initial instruction
  plotArea.innerHTML = '<div class="small">Ready — choose columns & render. Use multi-select (Ctrl/Cmd) to plot multiple series.</div>';
})();

/* --------------------------
   Level-3 Append: AI + Advanced Filters + Live Editor
   Appends only — does NOT modify existing code.
   Paste this at the END of static/js/visualizer.js (after your existing IIFE).
   -------------------------- */
(function ext_visualizer_enhancements(){
  // small safety: wait until DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function ext_get(id) { return document.getElementById(id); }

  // -- lightweight safe JSON fetch that gracefully handles HTML error pages
  async function ext_safeFetchJSON(url, opts) {
    try {
      const r = await fetch(url, opts);
      const text = await r.text();
      try { return JSON.parse(text); }
      catch (e) { return { error: `Server returned non-JSON (first 300 chars): ${text.slice(0,300)}` }; }
    } catch (err) {
      return { error: `Request failed: ${String(err)}` };
    }
  }
  async function ext_postJSON(url, body) {
    return ext_safeFetchJSON(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  }
  async function ext_getJSON(url) { return ext_safeFetchJSON(url); }

  // -- inject AI panel into left .panel (if present)
  // function injectAIPanel() {
  //   try {
  //     const leftPanel =
          // document.querySelector('#vs-left-panel') ||
          // document.querySelector('.vs-left .panel') ||
          // document.body;
  //     if (!leftPanel) return;
  //     // avoid double-insert
  //     if (document.getElementById('ext-ai-wrap')) return;

  //     const wrap = document.createElement('div');
  //     wrap.id = 'ext-ai-wrap';
  //     wrap.style.marginTop = '12px';
  //     wrap.innerHTML = `
  //       <h4 style="margin-bottom:6px;color:#cce8ff">AI Chart Builder</h4>

  //       <input id="ext-ai-prompt"
  //         placeholder="Describe chart e.g. 'monthly sales by country'"
  //         style="width:100%;padding:8px;border-radius:8px;
  //         border:1px solid rgba(255,255,255,0.04);
  //         background:transparent;color:inherit" />

  //       <div style="display:flex;gap:8px;margin-top:8px;">
  //         <button id="ext-ai-run" class="btn">Generate</button>
  //         <button id="ext-ai-apply" class="btn ghost">Apply</button>
  //       </div>

  //       <div id="ext-ai-suggestion"
  //         style="margin-top:8px;color:#bcd9ff;font-size:13px"></div>

  //       <!-- ================= STORY MODE CONTROLS (FIX) ================= -->
  //       <hr style="margin:10px 0;opacity:0.2"/>

  //       <h4 style="margin-bottom:6px;color:#cce8ff">Story Mode</h4>

  //       <textarea id="lv34-story-input"
  //         placeholder="Write story script (e.g. sales growth journey...)"
  //         style="width:100%;height:60px;padding:8px;border-radius:8px;
  //         border:1px solid rgba(255,255,255,0.04);
  //         background:transparent;color:inherit"></textarea>

  //       <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px;">
  //         <button id="lv34-story-run" class="btn">Run</button>
  //         <button id="lv34-play" class="btn ghost">Play</button>
  //         <button id="lv34-stop" class="btn ghost">Stop</button>
  //       </div>

  //       <div style="display:flex;gap:6px;margin-top:6px;">
  //         <button id="lv34-prev" class="btn ghost" style="flex:1">Prev</button>
  //         <button id="lv34-next" class="btn ghost" style="flex:1">Next</button>
  //       </div>
  //     `;
  //     // insert at top of left panel, after heading (non-destructive)
  //     leftPanel.insertBefore(wrap, leftPanel.firstChild);
  //     // wire events
  //     document.getElementById('ext-ai-run').addEventListener('click', onAIRun);
  //     document.getElementById('ext-ai-apply').addEventListener('click', onAIApply);
  //   } catch (e) {
  //     console.warn('ext: AI panel injection failed', e);
  //   }
  // }
  // function injectAIPanel() {
  //   try {
  //     // safer target (won't break if layout changes)
  //     const leftPanel =
  //       document.querySelector('.vs-left .panel') ||
  //       document.querySelector('.vs-left') ||
  //       document.body;

  //     if (!leftPanel) return;

  //     // prevent duplicate injection
  //     if (document.getElementById('ext-ai-wrap')) return;

  //     const wrap = document.createElement('div');
  //     wrap.id = 'ext-ai-wrap';
  //     wrap.style.marginTop = '12px';
  //     wrap.style.position = 'relative';
  //     wrap.style.zIndex = '10';

  //     wrap.innerHTML = `
  //       <h4 style="margin-bottom:6px;color:#cce8ff">AI Chart Builder</h4>

  //       <input id="ext-ai-prompt"
  //         placeholder="Describe chart e.g. 'monthly sales by country'"
  //         style="width:100%;padding:8px;border-radius:8px;
  //         border:1px solid rgba(255,255,255,0.04);
  //         background:transparent;color:inherit" />

  //       <div style="display:flex;gap:8px;margin-top:8px;">
  //         <button id="ext-ai-run" class="btn">Generate</button>
  //         <button id="ext-ai-apply" class="btn ghost">Apply</button>
  //       </div>

  //       <div id="ext-ai-suggestion"
  //         style="margin-top:8px;color:#bcd9ff;font-size:13px"></div>

  //       <hr style="margin:10px 0;opacity:0.2"/>

  //       <h4 style="margin-bottom:6px;color:#cce8ff">Story Mode</h4>

  //       <textarea id="lv34-story-input"
  //         placeholder="Write story script (e.g. sales growth journey...)"
  //         style="width:100%;height:60px;padding:8px;border-radius:8px;
  //         border:1px solid rgba(255,255,255,0.04);
  //         background:transparent;color:inherit"></textarea>

  //       <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px;">
  //         <button id="lv34-story-run" class="btn">Run</button>
  //         <button id="lv34-play" class="btn ghost">Play</button>
  //         <button id="lv34-stop" class="btn ghost">Stop</button>
  //       </div>

  //       <div style="display:flex;gap:6px;margin-top:6px;">
  //         <button id="lv34-prev" class="btn ghost" style="flex:1">Prev</button>
  //         <button id="lv34-next" class="btn ghost" style="flex:1">Next</button>
  //       </div>
  //     `;

  //     leftPanel.prepend(wrap);

  //     // bind AFTER DOM insert (important fix)
  //     setTimeout(bindAIPanelEvents, 0);

  //   } catch (e) {
  //     console.warn('ext: AI panel injection failed', e);
  //   }
  // }

  function injectAIPanel() {
  try {
    const target = document.getElementById('vs-ai');

    if (!target) return;

    // prevent duplicate
    if (document.getElementById('ext-ai-wrap')) return;

    const wrap = document.createElement('div');
    wrap.id = 'ext-ai-wrap';
    wrap.style.marginTop = '12px';

    wrap.innerHTML = `
      <div class="mb-3">
        <h4 class="text-cyan-300 font-semibold mb-2">AI Chart Builder</h4>

        <input id="ext-ai-prompt"
          placeholder="Describe chart e.g. monthly sales by country"
          class="w-full p-2 rounded-lg bg-transparent border border-gray-600 text-white" />

        <div class="flex gap-2 mt-2">
          <button id="ext-ai-run" class="btn">Generate</button>
          <button id="ext-ai-apply" class="btn ghost">Apply</button>
        </div>

        <div id="ext-ai-suggestion"
          class="text-sm text-blue-300 mt-2"></div>
      </div>

      <hr class="border-gray-700 my-3"/>

      <div>
        <h4 class="text-cyan-300 font-semibold mb-2">Story Mode</h4>

        <textarea id="lv34-story-input"
          placeholder="Write story script..."
          class="w-full p-2 rounded-lg bg-transparent border border-gray-600 text-white h-20"></textarea>

        <div class="grid grid-cols-3 gap-2 mt-2">
          <button id="lv34-story-run" class="btn">Run</button>
          <button id="lv34-play" class="btn ghost">Play</button>
          <button id="lv34-stop" class="btn ghost">Stop</button>
        </div>

        <div class="flex gap-2 mt-2">
          <button id="lv34-prev" class="btn ghost flex-1">Prev</button>
          <button id="lv34-next" class="btn ghost flex-1">Next</button>
        </div>
      </div>
    `;

    // 👇 APPEND INSIDE RECOMMEND PANEL
    target.appendChild(wrap);

    // bind events safely
    setTimeout(bindAIPanelEvents, 0);

  } catch (e) {
    console.warn('injectAIPanel failed', e);
  }
  }
  function bindAIPanelEvents() {
    const safeBind = (id, event, fn) => {
      const el = document.getElementById(id);
      if (el && !el.dataset.bound) {
        el.addEventListener(event, fn);
        el.dataset.bound = "1";
      }
    };

    // AI buttons
    safeBind('ext-ai-run', 'click', onAIRun);
    safeBind('ext-ai-apply', 'click', onAIApply);

    // Story buttons
    safeBind('lv34-story-run', 'click', onRunStory);
    safeBind('lv34-play', 'click', onPlayStory);
    safeBind('lv34-stop', 'click', onStopStory);
    safeBind('lv34-prev', 'click', onPrevStory);
    safeBind('lv34-next', 'click', onNextStory);
  }



  // -- ext state
  let ext_lastSuggestion = null;

  // -- run AI prompt: POST /visualizer/ai
  async function onAIRun() {
    const promptEl = ext_get('ext-ai-prompt');
    const sugEl = ext_get('ext-ai-suggestion');
    if (!promptEl || !sugEl) return;
    const prompt = String(promptEl.value || '').trim();
    if (!prompt) { alert('Enter an AI prompt first'); return; }
    sugEl.innerHTML = 'Generating suggestion…';
    const payload = { prompt, dataset: (document.getElementById('vs-dataset') && document.getElementById('vs-dataset').value) || 'uploaded' };
    const res = await ext_postJSON('/visualizer/ai', payload);
    if (res.error) {
      sugEl.innerHTML = `<div style="color:#f66">AI error: ${escapeHtml(String(res.error).slice(0,200))}</div>`;
      ext_lastSuggestion = null;
      return;
    }
    ext_lastSuggestion = res.config || null;
    // show suggestion explanation
    const explain = (res.config && res.config.explain) ? res.config.explain : 'Suggested config';
    let html = `<div><strong>${escapeHtml(res.config.chart_type || 'chart')}</strong> — ${escapeHtml(explain)}</div>`;
    if (res.insights && res.insights.summary) {
      html += `<div class="small">Rows: ${res.insights.summary.rows || '-'} • Cols: ${res.insights.summary.columns || '-'}</div>`;
    }
    sugEl.innerHTML = html;

    // show preview plot if returned
    if (res.plotly) {
      try {
        const plotArea = document.getElementById('vs-plot-area');
        if (plotArea) {
          plotArea.innerHTML = '<div id="ext-ai-plot" style="width:100%;height:420px"></div>';
          const data = res.plotly.data || res.plotly.data || [];
          const layout = res.plotly.layout || {};
          Plotly.newPlot('ext-ai-plot', data, layout, {responsive:true});
        }
      } catch (e) { console.warn('ext: failed to render AI preview', e); }
    }
  }

  // -- apply suggestion: set DOM inputs (safe: only sets values)
  async function onAIApply() {
    if (!ext_lastSuggestion) { alert('No AI suggestion to apply — generate first'); return; }
    const sug = ext_lastSuggestion;
    // set dataset
    const dsEl = document.getElementById('vs-dataset');
    if (dsEl && sug.dataset) { try { dsEl.value = sug.dataset; } catch(e){} }
    // refresh columns then apply column values (use backend to get columns first)
    try {
      // call existing endpoint to ensure lists are updated
      await ext_getJSON(`/visualizer/columns?dataset=${(dsEl && dsEl.value) || 'uploaded'}`);
      // set x column
      if (sug.x_column) {
        const xEl = document.getElementById('vs-column');
        if (xEl) {
          // pick exact match if exists, else do a fuzzy containment match
          let found = Array.from(xEl.options).find(o => o.value === sug.x_column);
          if (!found) found = Array.from(xEl.options).find(o => o.value.toLowerCase().includes(String(sug.x_column).toLowerCase()));
          if (found) xEl.value = found.value;
        }
      }
      // set y column(s) (single)
      if (sug.y_column) {
        const yEl = document.getElementById('vs-y-column');
        if (yEl) {
          Array.from(yEl.options).forEach(o => o.selected = (o.value === sug.y_column));
        }
      }
      // set chart type
      if (sug.chart_type) {
        const ct = document.getElementById('vs-chart-type');
        if (ct) {
          const match = Array.from(ct.options).find(o => o.value.toLowerCase() === sug.chart_type.toLowerCase());
          if (match) ct.value = match.value;
        }
      }
      // set color/group
      if (sug.color) {
        const col = document.getElementById('vs-color');
        if (col) {
          const match = Array.from(col.options).find(o => o.value === sug.color || o.value.toLowerCase() === String(sug.color).toLowerCase());
          if (match) col.value = match.value;
        }
      }
      // set title
      if (sug.explain) {
        const t = document.getElementById('vs-title');
        if (t) t.value = sug.explain;
      }
      // set filters (string or range)
      if (sug.filters && Object.keys(sug.filters).length) {
        const firstKey = Object.keys(sug.filters)[0];
        const v = sug.filters[firstKey];
        const fcol = document.getElementById('vs-filter-col');
        const fval = document.getElementById('vs-filter-val');
        if (fcol) {
          // try find matching option
          const m = Array.from(fcol.options).find(o => o.value === firstKey || o.value.toLowerCase().includes(firstKey.toLowerCase()));
          if (m) fcol.value = m.value;
        }
        if (fval) fval.value = Array.isArray(v) ? `${v[0]},${v[1]}` : String(v);
      }
      // finally trigger a render using your existing Render button (click it)
      const renderBtn = document.getElementById('vs-render');
      if (renderBtn) { renderBtn.click(); }
      else { alert('Applied AI suggestion — click Render'); }
    } catch (e) {
      console.warn('ext: apply suggestion failed', e);
      alert('Could not apply suggestion automatically, please apply fields manually.');
    }
  }

  // -- advanced filter-info helper: show hints in filter input placeholder
  function wireFilterInfo() {
    const filterColEl = document.getElementById('vs-filter-col');
    const filterValEl = document.getElementById('vs-filter-val');
    if (!filterColEl || !filterValEl) return;
    filterColEl.addEventListener('change', async () => {
      const col = filterColEl.value;
      if (!col) { filterValEl.placeholder = 'Type filter value (or range min,max)'; return; }
      const info = await ext_getJSON(`/visualizer/filter-info?dataset=${(document.getElementById('vs-dataset') && document.getElementById('vs-dataset').value) || 'uploaded'}&column=${encodeURIComponent(col)}`);
      if (info.error) {
        filterValEl.placeholder = 'Type filter value (or range min,max)';
        return;
      }
      if (info.type === 'numeric') {
        filterValEl.placeholder = `Numeric range: ${info.min} , ${info.max}`;
      } else {
        const top = info.top_values ? Object.keys(info.top_values).slice(0,6).join(', ') : '';
        filterValEl.placeholder = `Top values: ${top} (or type value)`;
      }
    });
  }

  // -- small live editor hook (expose a global function to allow later UI to call it)
  window.ext_visualizer_liveEdit = function ext_visualizer_liveEdit(opts) {
    // opts example: { title: "New title", color: "#ff0000" }
    if (!opts) return;
    const titleEl = document.getElementById('vs-title');
    const colorEl = document.getElementById('vs-color-input');
    if (opts.title && titleEl) titleEl.value = opts.title;
    if (opts.color && colorEl) colorEl.value = opts.color;
    // apply changes visually by triggering existing Render button if present
    const renderBtn = document.getElementById('vs-render');
    if (renderBtn) renderBtn.click();
  };

  // -- utility escape (safe copy of existing func)
  function escapeHtml(str) {
    return String(str || '').replace(/[&<>"'`=\/]/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','=':'&#x3D;','`':'&#x60'}[c];
    });
  }

  // initialize
  function init() {
    injectAIPanel();
    wireFilterInfo();
    // add a small notice in the AI area
    const sug = ext_get('ext-ai-suggestion');
    if (sug && sug.innerHTML.trim() === '') {
      sug.innerHTML = '<div class="small">Try: "monthly sales by country" or "distribution of ages"</div>';
    }

    // safety: if AI endpoint missing, show hint
    // (this will be detected on first AI run; no further action needed)
  }
})();


/* --------------------------
   Level3+4 Append: AI Insights 2.0, Story Mode & Dashboard Composer
   Paste this after your ext_visualizer_enhancements code (at the end of file).
   -------------------------- */
(function ext_visualizer_level34(){
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // helpers (non-conflicting names)
  async function lv34_fetchJSON(url, opts) {
    try {
      const r = await fetch(url, opts);
      const text = await r.text();
      try { return JSON.parse(text); } catch(e) { return { error: 'Server returned non-JSON: ' + text.slice(0,200) }; }
    } catch(err) { return { error: 'Request failed: ' + String(err) }; }
  }

  // create control section inside right preview area (below Insights)
  function createLevelPanel() {
    const right = document.querySelector('.preview-right');
    if (!right) return;
    if (document.getElementById('lv34-panel')) return;
    const panel = document.createElement('div'); panel.id = 'lv34-panel'; panel.style.marginTop = '12px';
    panel.innerHTML = `
      <h4>AI Insights & Story</h4>
      <div style="display:flex;gap:8px;">
        <button id="lv34-insights-btn" class="btn">Get Insights</button>
        <button id="lv34-recommends-btn" class="btn ghost">Quick Recs</button>
      </div>

      <div id="lv34-insights-output" style="margin-top:8px;font-size:13px;color:#d6eefc;max-height:220px;overflow:auto"></div>
      <div style="margin-top:10px;display:flex;gap:8px;">
        <button id="lv34-save-dash" class="btn">Save Dashboard</button>
        <button id="lv34-list-dash" class="btn ghost">Load Dashboard</button>
      </div>
      <div id="lv34-dash-list" style="margin-top:8px"></div>
    `;
    right.appendChild(panel);

    // wire buttons
    document.getElementById('lv34-insights-btn').addEventListener('click', onGetInsights);
    document.getElementById('lv34-recommends-btn').addEventListener('click', onQuickRecs);
    document.getElementById('lv34-story-run').addEventListener('click', onRunStory);
    document.getElementById('lv34-play').addEventListener('click', onPlayStory);
    document.getElementById('lv34-stop').addEventListener('click', onStopStory);
    document.getElementById('lv34-prev').addEventListener('click', onPrevStory);
    document.getElementById('lv34-next').addEventListener('click', onNextStory);
    document.getElementById('lv34-save-dash').addEventListener('click', onSaveDashboard);
    document.getElementById('lv34-list-dash').addEventListener('click', onListDashboards);
  }

  // AI Insights flow
  async function onGetInsights() {
    const out = document.getElementById('lv34-insights-output');
    if (!out) return;
    out.innerHTML = 'Computing insights…';
    const dataset = (document.getElementById('vs-dataset') && document.getElementById('vs-dataset').value) || 'uploaded';
    const res = await lv34_fetchJSON(`/visualizer/ai-insights?dataset=${encodeURIComponent(dataset)}`);
    if (res.error) { out.innerHTML = `<div style="color:#f66">${escapeHtml(res.error)}</div>`; return; }
    // render summary
    const ins = res.insights || {};
    let html = `<div><strong>Rows:</strong> ${ins.summary ? ins.summary.rows : '-'} • <strong>Cols:</strong> ${ins.summary ? ins.summary.columns : '-'}</div>`;
    if (ins.time_columns && ins.time_columns.length) html += `<div class="small">Time columns detected: ${ins.time_columns.join(', ')}</div>`;
    if (ins.top_correlations && ins.top_correlations.length) {
      html += `<div style="margin-top:6px"><strong>Top correlations</strong><ul>`;
      ins.top_correlations.slice(0,6).forEach(t => html += `<li>${escapeHtml(t['x'])} ↔ ${escapeHtml(t['y'])}: ${Number(t['corr']).toFixed(2)}</li>`);
      html += `</ul></div>`;
    }
    if (ins.recommendations && ins.recommendations.length) {
      html += `<div style="margin-top:6px"><strong>Recommendations</strong><ol>`;
      ins.recommendations.forEach(r => html += `<li>${escapeHtml(r.reason || (r.type || 'chart'))} (<em>${escapeHtml(r.type)}</em>)</li>`);
      html += `</ol></div>`;
    }
    out.innerHTML = html;
    // show preview if returned
    if (res.preview && res.preview.data) {
      const parea = document.getElementById('vs-plot-area');
      if (parea) {
        parea.innerHTML = '<div id="lv34-preview" style="width:100%;height:420px"></div>';
        Plotly.newPlot('lv34-preview', res.preview.data || [], res.preview.layout || {}, {responsive:true});
      }
    }
  }

  // Quick recommendations (renders a small set of buttons to quick-render)
  async function onQuickRecs() {
    const out = document.getElementById('lv34-insights-output');
    out.innerHTML = 'Loading recommendations…';
    const dataset = (document.getElementById('vs-dataset') && document.getElementById('vs-dataset').value) || 'uploaded';
    const res = await lv34_fetchJSON(`/visualizer/ai-insights?dataset=${encodeURIComponent(dataset)}`);
    if (res.error) { out.innerHTML = `<div style="color:#f66">${escapeHtml(res.error)}</div>`; return; }
    const recs = (res.insights && res.insights.recommendations) || [];
    if (!recs.length) { out.innerHTML = 'No recommendations available'; return; }
    let html = '<div style="display:flex;flex-direction:column;gap:6px">';
    recs.forEach((r, i) => {
      html += `<button class="btn ghost lv34-rec-btn" data-idx="${i}">${escapeHtml(r.reason || r.type || 'chart')}</button>`;
    });
    html += '</div>';
    out.innerHTML = html;
    document.querySelectorAll('.lv34-rec-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const idx = Number(e.currentTarget.dataset.idx);
        const cfg = recs[idx];
        // apply cfg to fields (non-destructive)
        if (cfg.x) { const xEl = document.getElementById('vs-column'); if (xEl) { xEl.value = cfg.x; } }
        if (cfg.y) {
          const yEl = document.getElementById('vs-y-column');
          if (yEl) Array.from(yEl.options).forEach(o => o.selected = (o.value === cfg.y));
        }
        if (cfg.type) { const ct = document.getElementById('vs-chart-type'); if (ct) ct.value = cfg.type; }
        if (cfg.reason) { const t = document.getElementById('vs-title'); if (t) t.value = cfg.reason; }
        // trigger render
        const renderBtn = document.getElementById('vs-render');
        if (renderBtn) renderBtn.click();
      });
    });
  }

  // Story mode
  let storySlides = [];
  let storyIndex = 0;
  let storyTimer = null;
  async function onRunStory() {
    const script = (document.getElementById('lv34-story-input') && document.getElementById('lv34-story-input').value) || '';
    const dataset = (document.getElementById('vs-dataset') && document.getElementById('vs-dataset').value) || 'uploaded';
    const payload = { dataset, script };
    const res = await lv34_fetchJSON('/visualizer/story', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if (res.error) { alert('Story generation failed: ' + String(res.error)); return; }
    storySlides = res.slides || [];
    storyIndex = 0;
    if (storySlides.length) renderStorySlide(0);
  }
  async function renderStorySlide(i) {
    if (!storySlides || !storySlides[i]) return;
    const slide = storySlides[i];
    // apply config & caption then render using existing render mechanism:
    // config keys: type,x,y,color,filters,etc.
    try {
      if (slide.config.x) { const xEl = document.getElementById('vs-column'); if (xEl) xEl.value = slide.config.x; }
      if (slide.config.y) { const yEl = document.getElementById('vs-y-column'); if (yEl) Array.from(yEl.options).forEach(o => o.selected = (o.value === slide.config.y)); }
      if (slide.config.type) { const ct = document.getElementById('vs-chart-type'); if (ct) ct.value = slide.config.type; }
      if (slide.caption) { const t = document.getElementById('vs-title'); if (t) t.value = slide.caption; }
      // filters
      if (slide.config.filters) {
        const keys = Object.keys(slide.config.filters);
        if (keys.length) {
          const fcol = document.getElementById('vs-filter-col');
          const fval = document.getElementById('vs-filter-val');
          if (fcol) {
            const match = Array.from(fcol.options).find(o => o.value === keys[0] || o.value.toLowerCase().includes(keys[0].toLowerCase()));
            if (match) fcol.value = match.value;
          }
          if (fval) fval.value = Array.isArray(slide.config.filters[keys[0]]) ? slide.config.filters[keys[0]].join(',') : String(slide.config.filters[keys[0]]);
        }
      }
      // render (click existing button)
      const renderBtn = document.getElementById('vs-render');
      if (renderBtn) renderBtn.click();
      // show caption in insights output
      const out = document.getElementById('lv34-insights-output');
      if (out) out.innerHTML = `<div style="font-weight:600">${escapeHtml(slide.caption || '')}</div>`;
    } catch (e) {
      console.warn('show story slide failed', e);
    }
  }
  function onPlayStory() {
    if (!storySlides || !storySlides.length) { alert('No story slides loaded'); return; }
    if (storyTimer) clearInterval(storyTimer);
    storyTimer = setInterval(() => {
      renderStorySlide(storyIndex);
      storyIndex = (storyIndex + 1) % storySlides.length;
    }, 3500);
  }
  function onStopStory() { if (storyTimer) { clearInterval(storyTimer); storyTimer = null; } }
  function onPrevStory() { if (!storySlides.length) return; storyIndex = (storyIndex - 1 + storySlides.length) % storySlides.length; renderStorySlide(storyIndex); }
  function onNextStory() { if (!storySlides.length) return; storyIndex = (storyIndex + 1) % storySlides.length; renderStorySlide(storyIndex); }

  // Dashboard persistence (server)

  async function onListDashboards() {
    const listEl = document.getElementById('lv34-dash-list');
    const res = await lv34_fetchJSON('/dashboard/list');
    if (res.error) { listEl.innerHTML = `<div style="color:#f66">${escapeHtml(res.error)}</div>`; return; }
    const d = res.dashboards || [];
    if (!d.length) { listEl.innerHTML = '<div class="small">No dashboards saved</div>'; return; }
    let html = '<div style="display:flex;flex-direction:column;gap:6px">';
    d.forEach(item => html += `<div style="display:flex;justify-content:space-between;align-items:center"><div>${escapeHtml(item.title)} <span class="small">(${item.cards_count})</span></div><div><button class="btn ghost lv34-load-dash" data-id="${escapeHtml(item.id)}">Load</button> <button class="btn ghost lv34-del-dash" data-id="${escapeHtml(item.id)}">Delete</button></div></div>`);
    html += '</div>';
    listEl.innerHTML = html;
    listEl.querySelectorAll('.lv34-load-dash').forEach(b => b.addEventListener('click', async (e) => {
      const id = e.currentTarget.dataset.id;
      const res = await lv34_fetchJSON(`/dashboard/load?id=${encodeURIComponent(id)}`);
      if (res.error) return alert('Load failed: ' + String(res.error));
      // replace local cards and render
      localStorage.setItem('dsa_visualizer_cards', JSON.stringify(res.cards || [])); renderDashboard();
      alert('Dashboard loaded: ' + (res.title || ''));
    }));
    listEl.querySelectorAll('.lv34-del-dash').forEach(b => b.addEventListener('click', async (e) => {
      const id = e.currentTarget.dataset.id;
      if (!confirm('Delete dashboard?')) return;
      const res = await lv34_fetchJSON('/dashboard/delete', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ id })});
      if (res.error) return alert('Delete failed: ' + String(res.error));
      alert('Deleted'); onListDashboards();
    }));
  }

  // init
  function init() {
    createLevelPanel();
  }

  // small helper escape (safe)
  function escapeHtml(s) { return String(s || '').replace(/[&<>"'`=\/]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','=':'&#x3D;','`':'&#x60'}[c]; }); }
})();


  // Add this at the end of your visualizer.js after dashboard controls

  // ---------------- CLEAN DASHBOARD CLEAR FIX ----------------
  (function fixClearDashboard() {
    const clearDashboardBtn = document.getElementById('vs-clear-dashboard');

    if (!clearDashboardBtn) return;

    clearDashboardBtn.addEventListener('click', () => {
      if (!confirm('Are you sure you want to clear all dashboard cards?')) return;

      localStorage.removeItem('dsa_visualizer_cards');

      // safely re-render using existing function if available
      if (typeof renderDashboard === 'function') {
        renderDashboard();
      }

      const dashboardEl = document.getElementById('vs-dashboard');
      if (dashboardEl) {
        dashboardEl.innerHTML = '<div class="small">No cards yet — add charts to dashboard</div>';
      }
    });
  })();

  clearDashboardBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to clear all dashboard cards?')) {
      // Clear localStorage
      localStorage.removeItem('dsa_visualizer_cards');
      // Clear dashboard immediately
      dashboardEl.innerHTML = '<div class="small">No cards yet — add charts to dashboard</div>';
    }

  function safeGet(id) {
    return document.getElementById(id);
  }
});



