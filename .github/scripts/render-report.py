#!/usr/bin/env python3
"""Render the cross-netcode benchmark report as one self-contained HTML page.

Usage: render-report.py <scaling.json> <out.html> [--versions versions.json] [--run-url URL] [--title TITLE]

scaling.json is the merged list of datapoints written by bench-aggregate.sh (dp-*.json). The page
embeds the data and draws small-multiple line charts (one per test, netcodes as series, connection
count on the x axis) with a metric selector, normalize-to-PurrNet and log-scale toggles, a
comparison table, and a warning list for any run that did not have all its clients. Charts use
Chart.js from cdnjs. The template is pure ASCII (HTML entities and JS unicode escapes) so it
renders correctly however the file is served.
"""
import argparse
import json
import sys
from pathlib import Path

TEMPLATE = r"""<meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {
    color-scheme: light;
    --page: #f9f9f7;
    --surface: #fcfcfb;
    --ink: #0b0b0b;
    --ink-2: #52514e;
    --muted: #898781;
    --grid: #e1e0d9;
    --axis: #c3c2b7;
    --ring: rgba(11, 11, 11, 0.10);
    --wash: rgba(11, 11, 11, 0.04);
    --accent: #2a78d6;
    --best: #006300;
    --best-wash: rgba(12, 163, 12, 0.10);
    --warn: #b45309;
    --s-purrnet: #eb6834;
    --s-fishnet: #2a78d6;
    --s-mirror: #1baf7a;
    --s-ngo: #eda100;
    --s-fusion: #e87ba4;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --page: #0d0d0d;
      --surface: #1a1a19;
      --ink: #ffffff;
      --ink-2: #c3c2b7;
      --muted: #898781;
      --grid: #2c2c2a;
      --axis: #383835;
      --ring: rgba(255, 255, 255, 0.10);
      --wash: rgba(255, 255, 255, 0.05);
      --accent: #3987e5;
      --best: #0ca30c;
      --best-wash: rgba(12, 163, 12, 0.16);
      --warn: #f0a24a;
      --s-purrnet: #d95926;
      --s-fishnet: #3987e5;
      --s-mirror: #199e70;
      --s-ngo: #c98500;
      --s-fusion: #d55181;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --page: #0d0d0d;
    --surface: #1a1a19;
    --ink: #ffffff;
    --ink-2: #c3c2b7;
    --muted: #898781;
    --grid: #2c2c2a;
    --axis: #383835;
    --ring: rgba(255, 255, 255, 0.10);
    --wash: rgba(255, 255, 255, 0.05);
    --accent: #3987e5;
    --best: #0ca30c;
    --best-wash: rgba(12, 163, 12, 0.16);
    --warn: #f0a24a;
    --s-purrnet: #d95926;
    --s-fishnet: #3987e5;
    --s-mirror: #199e70;
    --s-ngo: #c98500;
    --s-fusion: #d55181;
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--page);
    color: var(--ink);
    font-family: "Instrument Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.45;
  }
  .mono, table, .tick, .chip b, .stat { font-family: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace; font-variant-numeric: tabular-nums; }
  a { color: var(--accent); }
  .wrap { max-width: 1440px; margin: 0 auto; padding: 24px clamp(16px, 3vw, 40px) 64px; display: grid; gap: 24px; }

  header { display: grid; gap: 10px; }
  header h1 { font-size: 22px; font-weight: 600; margin: 0; letter-spacing: -0.01em; text-wrap: balance; }
  .eyebrow { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 500; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px 10px; }
  .chip { display: inline-flex; gap: 6px; align-items: baseline; padding: 4px 10px; border: 1px solid var(--ring); border-radius: 999px; color: var(--ink-2); font-size: 12px; background: var(--surface); }
  .chip b { color: var(--ink); font-weight: 500; font-size: 12px; }
  .chip .sw { width: 10px; height: 10px; border-radius: 2px; align-self: center; }

  .controls { display: grid; gap: 12px; padding: 14px 16px; background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; }
  .row { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
  .row .lbl { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 500; min-width: 64px; }
  .seg { display: flex; flex-wrap: wrap; gap: 4px; }
  .seg button, .toggle { font: inherit; font-size: 13px; padding: 5px 10px; border-radius: 6px; border: 1px solid var(--ring); background: transparent; color: var(--ink-2); cursor: pointer; }
  .seg button:hover, .toggle:hover { background: var(--wash); }
  .seg button[aria-pressed="true"], .toggle[aria-pressed="true"] { background: var(--ink); color: var(--page); border-color: var(--ink); }
  .seg button:focus-visible, .toggle:focus-visible, .legend button:focus-visible, .card:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 14px; }
  .legend button { font: inherit; font-size: 13px; display: inline-flex; align-items: center; gap: 7px; background: none; border: 0; padding: 4px 2px; color: var(--ink); cursor: pointer; }
  .legend button .sw { width: 14px; height: 3px; border-radius: 2px; position: relative; }
  .legend button .sw::after { content: ""; position: absolute; left: 50%; top: 50%; width: 8px; height: 8px; border-radius: 50%; transform: translate(-50%, -50%); background: inherit; }
  .legend button[aria-pressed="false"] { color: var(--muted); text-decoration: line-through; }
  .legend button[aria-pressed="false"] .sw { opacity: 0.35; }
  .hint { color: var(--muted); font-size: 12px; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; padding: 12px 12px 8px; display: grid; gap: 6px; cursor: pointer; text-align: left; font: inherit; color: inherit; }
  .card[aria-pressed="true"] { border-color: var(--ink); box-shadow: inset 0 0 0 1px var(--ink); }
  .card h3 { margin: 0; font-size: 13px; font-weight: 600; display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
  .card h3 small { font-weight: 400; color: var(--muted); font-size: 11px; }
  .card .cv { position: relative; height: 210px; }
  .card canvas { position: absolute; inset: 0; width: 100% !important; height: 100% !important; }

  section h2 { font-size: 15px; font-weight: 600; margin: 0 0 4px; }
  section p { margin: 0; color: var(--ink-2); max-width: 70ch; }
  .tablewrap { overflow-x: auto; border: 1px solid var(--ring); border-radius: 8px; background: var(--surface); }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { padding: 8px 12px; text-align: right; border-bottom: 1px solid var(--grid); white-space: nowrap; }
  th { color: var(--muted); font-weight: 500; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; font-family: "Instrument Sans", system-ui, sans-serif; }
  th:first-child, td:first-child { text-align: left; }
  tr:last-child td { border-bottom: 0; }
  td.best { color: var(--best); background: var(--best-wash); font-weight: 500; }
  td.na { color: var(--muted); }
  td .rel { color: var(--muted); font-size: 11px; margin-left: 6px; }
  .notes { display: grid; gap: 14px; }
  .warnings { margin: 0; padding: 10px 14px 10px 30px; border: 1px solid var(--warn); border-radius: 8px; color: var(--warn); background: var(--surface); }
  .warnings li { margin: 2px 0; }
  footer { color: var(--muted); font-size: 12px; }
  @media (prefers-reduced-motion: no-preference) { .seg button, .toggle, .card { transition: background-color 120ms ease, border-color 120ms ease; } }
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Unity netcode benchmark &#xb7; scaling run</div>
    <h1 id="title">__TITLE__</h1>
    <div class="chips" id="meta"></div>
    <div class="chips" id="versions"></div>
  </header>

  <div class="controls" role="region" aria-label="Chart controls">
    <div class="row"><span class="lbl">Metric</span><div class="seg" id="metrics" role="group" aria-label="Metric"></div></div>
    <div class="row">
      <span class="lbl">View</span>
      <button class="toggle" id="normalize" aria-pressed="false" title="Divide every value by PurrNet's value at the same connection count">Relative to PurrNet</button>
      <button class="toggle" id="logscale" aria-pressed="false">Log scale</button>
      <span class="hint" id="metric-hint"></span>
    </div>
    <div class="row"><span class="lbl">Series</span><div class="legend" id="legend" role="group" aria-label="Netcodes"></div><span class="hint">click to hide &#xb7; click a chart to open its table</span></div>
  </div>

  <div class="grid" id="charts"></div>

  <section>
    <h2 id="table-title"></h2>
    <p id="table-hint"></p>
    <div class="tablewrap" style="margin-top:10px"><table id="table"></table></div>
  </section>

  <section class="notes">
    <div>
      <h2>Run notes</h2>
      <p>Every netcode runs the same scenario: the server spawns N objects and replicates them to every client. On-wire bytes are read from the network interface (UDP/IP headers, ACKs and resends included). CPU is the whole server process, all threads, as % of one core with the frame loop capped at 60 fps; the Idle window is each netcode's baseline. Fusion is relay-based (Photon Cloud): its RTT includes the relay hop and its traffic is measured on the public interface, but the server still sends one stream per client, so its downstream is comparable.</p>
    </div>
    <ul id="warnings" class="warnings" hidden></ul>
  </section>

  <footer id="footer"></footer>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.5.1/chart.umd.min.js"></script>
<script>
const DATA = __DATA__;

const ORDER = ["purrnet", "fishnet", "mirror", "ngo", "fusion"];
const NAMES = { purrnet: "PurrNet", fishnet: "FishNet", mirror: "Mirror", ngo: "NGO", fusion: "Fusion" };
const TESTS = ["MoveY", "MoveAllAxis", "MoveWander", "SendRPC", "Static", "SpawnChurn", "ClientInput", "SyncVars"];
const TEST_DESC = {
  MoveY: "N objects, sine on Y", MoveAllAxis: "N objects, sine on a random axis", MoveWander: "N objects, wander (position + rotation)",
  SendRPC: "N objects, 1 observers RPC (float) per tick", Static: "N objects, never touched", SpawnChurn: "N alive, N/50 despawned + spawned per tick",
  ClientInput: "1 object, each client sends 1 RPC per tick", SyncVars: "N objects, 1 synced field changed per tick"
};
const kb = v => v == null ? null : v / 1024;
const idle = r => (r.server && r.server.Idle && r.server.Idle.cpuPercent) || 0;
const METRICS = [
  { id: "srvDown", label: "Server downstream", unit: "KB/s", lower: true, hint: "bytes the server puts on the wire to all clients", get: (r, t) => kb(r.server[t] && r.server[t].txBytesPerSec) },
  { id: "cliDown", label: "Per-client downstream", unit: "KB/s", lower: true, hint: "average received by one measured client", get: (r, t) => kb(r.clients[t] && r.clients[t].rxBytesPerSec) },
  { id: "srvUp", label: "Server upstream", unit: "KB/s", lower: true, hint: "bytes the server receives from all clients", get: (r, t) => kb(r.server[t] && r.server[t].rxBytesPerSec) },
  { id: "cliUp", label: "Per-client upstream", unit: "KB/s", lower: true, hint: "average sent by one measured client", get: (r, t) => kb(r.clients[t] && r.clients[t].txBytesPerSec) },
  { id: "cpu", label: "Server CPU \u2212 idle", unit: "%", lower: true, hint: "process CPU % of one core, Idle window subtracted", get: (r, t) => r.server[t] ? r.server[t].cpuPercent - idle(r) : null },
  { id: "cpuRaw", label: "Server CPU", unit: "%", lower: true, hint: "process CPU % of one core, raw", get: (r, t) => r.server[t] ? r.server[t].cpuPercent : null },
  { id: "p95", label: "Frame p95", unit: "ms", lower: true, hint: "server main-thread frame time, 95th percentile (16.7 ms = on budget)", get: (r, t) => r.server[t] ? r.server[t].p95FrameMs : null },
  { id: "p99", label: "Frame p99", unit: "ms", lower: true, hint: "server main-thread frame time, 99th percentile", get: (r, t) => r.server[t] ? r.server[t].p99FrameMs : null },
  { id: "pkts", label: "Packets out", unit: "/s", lower: true, hint: "server datagrams sent per second", get: (r, t) => r.server[t] ? r.server[t].txPacketsPerSec : null },
  { id: "gc", label: "GC collections", unit: "", lower: true, hint: "server GC collections during the window", get: (r, t) => r.server[t] ? r.server[t].gcCollections : null },
  { id: "rss", label: "Peak RSS", unit: "MB", lower: true, hint: "server peak resident memory", get: (r, t) => r.server[t] ? r.server[t].peakRssBytes / 1048576 : null },
  { id: "rtt50", label: "RTT p50", unit: "ms", lower: true, hint: "client-side, netcode-reported round trip (Fusion includes the relay hop)", get: (r, t) => r.clients[t] ? r.clients[t].rttP50Ms : null },
  { id: "rtt95", label: "RTT p95", unit: "ms", lower: true, hint: "client-side, netcode-reported round trip", get: (r, t) => r.clients[t] ? r.clients[t].rttP95Ms : null },
  { id: "inputs", label: "Inputs received", unit: "/s", lower: false, hint: "ClientInput only: server RPCs received per second (expected 20 \u00d7 connections)", get: (r, t) => r.server[t] ? r.server[t].inputsPerSec : null }
];

const runs = DATA.runs;
const netcodes = ORDER.filter(n => runs.some(r => r.netcode === n));
const sizes = [...new Set(runs.map(r => r.size || r.connections))].sort((a, b) => a - b);
const byKey = {};
runs.forEach(r => { byKey[r.netcode + "@" + (r.size || r.connections)] = r; });
const state = { metric: "srvDown", normalize: false, log: false, hidden: new Set(), test: "MoveY" };
const charts = {};

function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function metric() { return METRICS.find(m => m.id === state.metric); }
function raw(n, s, t) { const r = byKey[n + "@" + s]; if (!r) return null; const v = metric().get(r, t); return (v == null || Number.isNaN(v)) ? null : v; }
function value(n, s, t) {
  const v = raw(n, s, t);
  if (v == null) return null;
  if (!state.normalize) return v;
  const base = raw("purrnet", s, t);
  if (base == null || base === 0) return null;
  return v / base;
}
function fmt(v, unit) {
  if (v == null) return "\u2013";
  if (state.normalize) return (v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)) + "\u00d7";
  const a = Math.abs(v);
  const s = a >= 1000 ? v.toFixed(0) : a >= 100 ? v.toFixed(1) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  return unit ? s + " " + unit : s;
}

function buildHeader() {
  const meta = document.getElementById("meta");
  const first = runs[0];
  const anyTest = first && Object.values(first.server).find(t => t && t.test > 0);
  const chips = [
    ["Connections", sizes.join(" / ")],
    ["Objects per test", anyTest ? anyTest.objects : "?"],
    ["Window", anyTest ? Math.round(anyTest.windowSeconds) + " s" : "?"],
    ["Tick", (first && first.meta.tickRate) + " Hz"],
    ["Frame cap", "60 fps"],
    ["Build", first && first.meta.devBuild ? "Development" : "Release"]
  ];
  meta.innerHTML = chips.map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`).join("");
  const vers = document.getElementById("versions");
  vers.innerHTML = netcodes.map(n => `<span class="chip"><span class="sw" style="background:var(--s-${n})"></span>${NAMES[n]} <b>${(DATA.versions || {})[n] || "?"}</b></span>`).join("")
    + `<span class="chip">Unity <b>${(DATA.versions || {}).unity || (first && first.meta.unityVersion) || "?"}</b></span>`;
  const f = document.getElementById("footer");
  f.innerHTML = (DATA.runUrl ? `Source run: <a href="${DATA.runUrl}">${DATA.runUrl}</a> \u00b7 ` : "") + `Rendered ${DATA.rendered}. Lower is better on every metric except inputs received.`;
}

function buildControls() {
  const seg = document.getElementById("metrics");
  seg.innerHTML = METRICS.map(m => `<button type="button" data-id="${m.id}" aria-pressed="${m.id === state.metric}">${m.label}</button>`).join("");
  seg.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    state.metric = b.dataset.id;
    seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
    refresh();
  });
  const leg = document.getElementById("legend");
  leg.innerHTML = netcodes.map(n => `<button type="button" data-n="${n}" aria-pressed="true"><span class="sw" style="background:var(--s-${n})"></span>${NAMES[n]}</button>`).join("");
  leg.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    const n = b.dataset.n;
    if (state.hidden.has(n)) state.hidden.delete(n); else state.hidden.add(n);
    b.setAttribute("aria-pressed", !state.hidden.has(n));
    refresh();
  });
  const norm = document.getElementById("normalize");
  norm.addEventListener("click", () => { state.normalize = !state.normalize; norm.setAttribute("aria-pressed", state.normalize); refresh(); });
  const log = document.getElementById("logscale");
  log.addEventListener("click", () => { state.log = !state.log; log.setAttribute("aria-pressed", state.log); refresh(); });
}

function buildCharts() {
  const grid = document.getElementById("charts");
  grid.innerHTML = TESTS.map(t => `
    <button type="button" class="card" data-test="${t}" aria-pressed="${t === state.test}">
      <h3><span>${t}</span><small>${TEST_DESC[t]}</small></h3>
      <div class="cv"><canvas id="c-${t}" role="img" aria-label="${t}: ${metric().label} versus connections"></canvas></div>
    </button>`).join("");
  grid.addEventListener("click", e => {
    const c = e.target.closest(".card"); if (!c) return;
    state.test = c.dataset.test;
    grid.querySelectorAll(".card").forEach(x => x.setAttribute("aria-pressed", x === c));
    buildTable();
  });
  TESTS.forEach(t => {
    const ctx = document.getElementById("c-" + t).getContext("2d");
    charts[t] = new Chart(ctx, { type: "line", data: { labels: sizes.map(String), datasets: [] }, options: baseOptions(t) });
  });
  refresh();
}

function baseOptions(t) {
  const m = metric();
  const ink = css("--ink"), muted = css("--muted"), grid = css("--grid"), axis = css("--axis"), surface = css("--surface");
  return {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: surface, titleColor: ink, bodyColor: ink, borderColor: axis, borderWidth: 1, padding: 10,
        titleFont: { family: "Instrument Sans, system-ui, sans-serif", weight: "600" }, bodyFont: { family: "JetBrains Mono, monospace" },
        callbacks: {
          title: items => items.length ? items[0].label + " connections \u00b7 " + t : "",
          label: item => " " + NAMES[item.dataset.key] + "  " + fmt(item.parsed.y, m.unit)
        }
      }
    },
    scales: {
      x: { title: { display: true, text: "connections", color: muted, font: { size: 11 } }, ticks: { color: muted, font: { family: "JetBrains Mono, monospace", size: 11 } }, grid: { display: false }, border: { color: axis } },
      y: {
        type: state.log ? "logarithmic" : "linear", beginAtZero: !state.log,
        title: { display: true, text: state.normalize ? "\u00d7 PurrNet" : (m.unit || m.label), color: muted, font: { size: 11 } },
        ticks: { color: muted, font: { family: "JetBrains Mono, monospace", size: 11 }, maxTicksLimit: 6, callback: v => state.normalize ? v + "\u00d7" : (Math.abs(v) >= 1000 ? (v / 1000).toFixed(v % 1000 ? 1 : 0) + "k" : +Number(v).toFixed(2)) },
        grid: { color: grid }, border: { color: axis, dash: [] }
      }
    },
    elements: { line: { borderWidth: 2, tension: 0 }, point: { radius: 4, hoverRadius: 6, borderWidth: 2, hitRadius: 12 } }
  };
}

function refresh() {
  const m = metric();
  document.getElementById("metric-hint").textContent = m.hint + (m.lower ? " \u00b7 lower is better" : " \u00b7 higher is better");
  const surface = css("--surface");
  TESTS.forEach(t => {
    const ch = charts[t];
    ch.options = baseOptions(t);
    ch.data.datasets = netcodes.filter(n => !state.hidden.has(n)).map(n => {
      const color = css("--s-" + n);
      return { key: n, label: NAMES[n], data: sizes.map(s => value(n, s, t)), borderColor: color, backgroundColor: color, pointBackgroundColor: surface, pointBorderColor: color, spanGaps: false };
    });
    ch.update("none");
  });
  buildTable();
}

function buildTable() {
  const m = metric();
  const t = state.test;
  document.getElementById("table-title").textContent = `${t} \u2014 ${m.label}${state.normalize ? " relative to PurrNet" : (m.unit ? " (" + m.unit + ")" : "")}`;
  document.getElementById("table-hint").textContent = TEST_DESC[t] + ". " + m.hint + ". Best value per row is marked.";
  const cols = netcodes.filter(n => !state.hidden.has(n));
  let html = "<thead><tr><th>Connections</th>" + cols.map(n => `<th>${NAMES[n]}</th>`).join("") + "</tr></thead><tbody>";
  sizes.forEach(s => {
    const vals = cols.map(n => value(n, s, t));
    const present = vals.filter(v => v != null);
    const best = present.length > 1 ? (m.lower ? Math.min(...present) : Math.max(...present)) : null;
    html += `<tr><td>${s}</td>` + cols.map((n, i) => {
      const v = vals[i];
      if (v == null) return `<td class="na">\u2013</td>`;
      const r = byKey[n + "@" + s];
      const note = r && r.connections !== s ? `<span class="rel" title="actual connections">${r.connections}c</span>` : "";
      return `<td class="${v === best ? "best" : ""}">${fmt(v, m.unit)}${note}</td>`;
    }).join("") + "</tr>";
  });
  html += "</tbody>";
  document.getElementById("table").innerHTML = html;
}

function buildNotes() {
  // Every run should have all of its clients; anything else is a race or a bug worth seeing.
  const items = [];
  netcodes.forEach(n => sizes.forEach(s => {
    const r = byKey[n + "@" + s];
    if (!r) { items.push(`${NAMES[n]} at ${s}: no datapoint`); return; }
    if (r.meta.connectedAtStart !== r.meta.expectedClients)
      items.push(`${NAMES[n]} at ${s}: only ${r.meta.connectedAtStart} of ${r.meta.expectedClients} clients connected before the connect timeout`);
    else if (r.connections !== s)
      items.push(`${NAMES[n]} at ${s}: ran with ${r.connections} clients`);
    if (r.meta.serverError) items.push(`${NAMES[n]} at ${s}: server reported ${r.meta.serverError}`);
    // A test measured on fewer clients than connected means some clients never observed its
    // spawn/despawn transition (state delivery lagged); the average still stands, on fewer samples.
    const short = TESTS.filter(t => r.clients[t] && r.clients[t].n < r.meta.measuredClients).map(t => `${t} (${r.clients[t].n}/${r.meta.measuredClients})`);
    if (short.length) items.push(`${NAMES[n]} at ${s}: measured on fewer clients than connected: ${short.join(", ")}`);
  }));
  const ul = document.getElementById("warnings");
  ul.innerHTML = items.map(t => `<li>${t}</li>`).join("");
  ul.hidden = items.length === 0;
}

buildHeader();
buildControls();
buildNotes();
buildCharts();

const rethemes = () => refresh();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", rethemes);
new MutationObserver(rethemes).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scaling", help="merged datapoints (scaling.json)")
    ap.add_argument("out", help="output HTML path")
    ap.add_argument("--versions", help="versions.json from versions.sh")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--title", default="Netcode Scaling Report")
    ap.add_argument("--rendered", default="")
    args = ap.parse_args()

    runs = json.loads(Path(args.scaling).read_text(encoding="utf-8"))
    if not isinstance(runs, list):
        runs = [runs]
    import re
    for r in runs:
        # Requested size: explicit field, else parsed from the run tag (c100), else the actual count,
        # so a capped run (Fusion at 99) shares the 100 column with the others.
        if not r.get("size"):
            m = re.fullmatch(r"c(\d+)", str(r.get("tag", "")))
            r["size"] = int(m.group(1)) if m else r.get("connections")
        r.setdefault("server", {})
        r.setdefault("clients", {})
        r.setdefault("meta", {})
        for t in r["server"].values():
            if isinstance(t, dict):
                t.pop("cpuMarkers", None)

    versions = {}
    if args.versions and Path(args.versions).exists():
        versions = json.loads(Path(args.versions).read_text(encoding="utf-8"))

    from datetime import datetime, timezone
    rendered = args.rendered or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {"runs": runs, "versions": versions, "runUrl": args.run_url, "rendered": rendered}
    data_js = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")

    html = TEMPLATE.replace("__TITLE__", args.title).replace("__DATA__", data_js)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Report written to {args.out} ({len(runs)} datapoints, {len(html) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
