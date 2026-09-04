#!/usr/bin/env python3
"""Render the cross-netcode benchmark report as one self-contained HTML page.

Usage: render-report.py <scaling.json> <out.html> [--versions versions.json] [--run-url URL] [--title TITLE]

scaling.json is the merged list of datapoints written by bench-aggregate.sh (dp-*.json); each is one
netcode in one session (connections x tick rate). The page is built to be read top-down:

  1. Scorecard: one row per netcode for the selected session. Bandwidth and CPU are shown as the
     geometric mean over the load tests of "this netcode / best netcode in that test", so 1.0x is
     the best everywhere and 2.0x means twice the best on average. GC, frame p99, peak RSS and a
     win count sit next to them.
  2. How it scales: per netcode, the cost multiplier from the smallest to the largest connection
     count and from the lowest to the highest tick rate (only when both sessions exist).
  3. Per-test bar charts for one metric in the selected session, with relative-to-PurrNet and log
     toggles, and a detail table (rows = sessions) for the clicked test.
  4. Run notes and warnings (missing clients, mismatched CPU models or tick rates).

Charts use Chart.js from cdnjs. The template is pure ASCII (HTML entities and JS unicode escapes)
so it renders correctly however the file is served.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
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
  .mono, table, .chip b { font-family: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace; font-variant-numeric: tabular-nums; }
  a { color: var(--accent); }
  .wrap { max-width: 1440px; margin: 0 auto; padding: 24px clamp(16px, 3vw, 40px) 64px; display: grid; gap: 28px; }

  header { display: grid; gap: 10px; }
  header h1 { font-size: 22px; font-weight: 600; margin: 0; letter-spacing: -0.01em; text-wrap: balance; }
  .eyebrow { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 500; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px 10px; }
  .chip { display: inline-flex; gap: 6px; align-items: baseline; padding: 4px 10px; border: 1px solid var(--ring); border-radius: 999px; color: var(--ink-2); font-size: 12px; background: var(--surface); }
  .chip b { color: var(--ink); font-weight: 500; font-size: 12px; }
  .chip .sw { width: 10px; height: 10px; border-radius: 2px; align-self: center; }

  section { display: grid; gap: 10px; }
  section h2 { font-size: 16px; font-weight: 600; margin: 0; display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: baseline; }
  section h2 .hint { font-weight: 400; }
  section > p { margin: 0; color: var(--ink-2); max-width: 78ch; }
  .hint { color: var(--muted); font-size: 12px; }

  .controls { display: grid; gap: 12px; padding: 14px 16px; background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; }
  .row { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
  .row .lbl { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 500; min-width: 64px; }
  .seg { display: flex; flex-wrap: wrap; gap: 4px; }
  .seg button, .toggle { font: inherit; font-size: 13px; padding: 5px 10px; border-radius: 6px; border: 1px solid var(--ring); background: transparent; color: var(--ink-2); cursor: pointer; }
  .seg button:hover, .toggle:hover { background: var(--wash); }
  .seg button[aria-pressed="true"], .toggle[aria-pressed="true"] { background: var(--ink); color: var(--page); border-color: var(--ink); }
  .seg button:focus-visible, .toggle:focus-visible, .card:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .tablewrap { overflow-x: auto; border: 1px solid var(--ring); border-radius: 8px; background: var(--surface); }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { padding: 8px 12px; text-align: right; border-bottom: 1px solid var(--grid); white-space: nowrap; }
  th { color: var(--muted); font-weight: 500; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; font-family: "Instrument Sans", system-ui, sans-serif; }
  th:first-child, td:first-child { text-align: left; }
  tr:last-child td { border-bottom: 0; }
  td.best { color: var(--best); background: var(--best-wash); font-weight: 500; }
  td.na { color: var(--muted); }
  td .rel { color: var(--muted); font-size: 11px; margin-left: 6px; }
  td.name { font-family: "Instrument Sans", system-ui, sans-serif; font-weight: 500; }
  td.name .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 8px; vertical-align: -1px; }
  td .sub { color: var(--muted); font-size: 11px; margin-left: 6px; font-weight: 400; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; padding: 12px 12px 8px; display: grid; gap: 6px; cursor: pointer; text-align: left; font: inherit; color: inherit; }
  .card[aria-pressed="true"] { border-color: var(--ink); box-shadow: inset 0 0 0 1px var(--ink); }
  .card h3 { margin: 0; font-size: 13px; font-weight: 600; display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
  .card h3 small { font-weight: 400; color: var(--muted); font-size: 11px; text-align: right; }
  .card .cv { position: relative; height: 170px; }
  .card canvas { position: absolute; inset: 0; width: 100% !important; height: 100% !important; }

  .warnings { margin: 0; padding: 10px 14px 10px 30px; border: 1px solid var(--warn); border-radius: 8px; color: var(--warn); background: var(--surface); }
  .warnings li { margin: 2px 0; }
  footer { color: var(--muted); font-size: 12px; }
  @media (prefers-reduced-motion: no-preference) { .seg button, .toggle, .card { transition: background-color 120ms ease, border-color 120ms ease; } }
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Unity netcode benchmark</div>
    <h1 id="title">__TITLE__</h1>
    <div class="chips" id="meta"></div>
    <div class="chips" id="versions"></div>
  </header>

  <section>
    <h2>At a glance <span class="hint">&#xb7; one row per netcode, lower is better everywhere</span></h2>
    <div class="row"><span class="lbl">Session</span><div class="seg" id="scenarios" role="group" aria-label="Session"></div></div>
    <div class="tablewrap"><table id="scorecard"></table></div>
    <p id="score-hint"></p>
  </section>

  <section id="scaling-section" hidden>
    <h2>How it scales <span class="hint">&#xb7; cost multiplier when the load grows; closer to 1&#xd7; means better amortisation</span></h2>
    <div class="tablewrap"><table id="scaling"></table></div>
    <p id="scaling-hint"></p>
  </section>

  <section>
    <h2>Per test <span class="hint" id="charts-hint"></span></h2>
    <div class="controls" role="region" aria-label="Chart controls">
      <div class="row"><span class="lbl">Metric</span><div class="seg" id="metrics" role="group" aria-label="Metric"></div></div>
      <div class="row">
        <span class="lbl">View</span>
        <button class="toggle" id="normalize" aria-pressed="false" title="Divide every value by PurrNet's value in the same test and session">Relative to PurrNet</button>
        <button class="toggle" id="logscale" aria-pressed="false">Log scale</button>
        <span class="hint" id="metric-hint"></span>
      </div>
    </div>
    <div class="grid" id="charts"></div>
  </section>

  <section>
    <h2 id="table-title"></h2>
    <p id="table-hint"></p>
    <div class="tablewrap"><table id="table"></table></div>
  </section>

  <section>
    <h2>Run notes</h2>
    <p>Every netcode runs the same scenario: the server spawns N objects and replicates them to every client. On-wire bytes are read from the network interface (UDP/IP headers, ACKs and resends included). CPU is the whole server process, all threads, as % of one core with the frame loop capped at 60 fps; nothing is subtracted, so the Idle row is what holding N connections costs on its own. Fusion is relay-based (Photon Cloud): its RTT includes the relay hop and its traffic is measured on the public interface, but the server still sends one stream per client, so its downstream is comparable. Every session runs all netcodes on the same server machine and the same client machines, so numbers are comparable across netcodes within a session.</p>
    <ul id="warnings" class="warnings" hidden></ul>
  </section>

  <footer id="footer"></footer>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.5.1/chart.umd.min.js"></script>
<script>
const DATA = __DATA__;

const ORDER = ["purrnet", "fishnet", "mirror", "ngo", "fusion"];
const NAMES = { purrnet: "PurrNet", fishnet: "FishNet", mirror: "Mirror", ngo: "NGO", fusion: "Fusion" };
const TESTS = ["Idle", "MoveY", "MoveWander", "SyncVars", "SendRPC", "ClientInput", "Static", "SpawnChurn"];
const TEST_DESC = {
  Idle: "baseline · connected, nothing spawned", MoveY: "replication · N objects, sine on Y",
  MoveWander: "replication · N objects, wander (position + rotation)", SyncVars: "replication · N objects, 1 synced field changed per tick",
  SendRPC: "messaging · N objects, 1 observers RPC (float) per tick", ClientInput: "messaging · 1 object, each client sends 1 RPC per tick",
  Static: "lifecycle · N objects, never touched", SpawnChurn: "lifecycle · N alive, N/50 despawned + spawned per tick"
};
// Tests that carry real load; Idle and Static sit at the noise floor and would only add noise to averages.
const SCORE_TESTS = ["MoveY", "MoveWander", "SyncVars", "SendRPC", "ClientInput", "SpawnChurn"];
const kb = v => v == null ? null : v / 1024;
const METRICS = [
  { id: "srvDown", label: "Server downstream", unit: "KB/s", lower: true, hint: "bytes the server puts on the wire to all clients", get: (r, t) => kb(r.server[t] && r.server[t].txBytesPerSec) },
  { id: "cpu", label: "Server CPU", unit: "%", lower: true, hint: "whole process CPU as % of one core, nothing subtracted", get: (r, t) => r.server[t] ? r.server[t].cpuPercent : null },
  { id: "cliDown", label: "Per-client downstream", unit: "KB/s", lower: true, hint: "average received by one measured client", get: (r, t) => kb(r.clients[t] && r.clients[t].rxBytesPerSec) },
  { id: "srvUp", label: "Server upstream", unit: "KB/s", lower: true, hint: "bytes the server receives from all clients", get: (r, t) => kb(r.server[t] && r.server[t].rxBytesPerSec) },
  { id: "cliUp", label: "Per-client upstream", unit: "KB/s", lower: true, hint: "average sent by one measured client", get: (r, t) => kb(r.clients[t] && r.clients[t].txBytesPerSec) },
  { id: "p95", label: "Frame p95", unit: "ms", lower: true, hint: "server main-thread frame time, 95th percentile (16.7 ms = on budget)", get: (r, t) => r.server[t] ? r.server[t].p95FrameMs : null },
  { id: "p99", label: "Frame p99", unit: "ms", lower: true, hint: "server main-thread frame time, 99th percentile", get: (r, t) => r.server[t] ? r.server[t].p99FrameMs : null },
  { id: "pkts", label: "Packets out", unit: "/s", lower: true, hint: "server datagrams sent per second", get: (r, t) => r.server[t] ? r.server[t].txPacketsPerSec : null },
  { id: "alloc", label: "GC alloc", unit: "KB/s", lower: true, hint: "managed bytes the server allocates per second, all threads; the garbage the collections are made of", get: (r, t) => r.server[t] && r.server[t].gcAllocBytesPerSec >= 0 ? r.server[t].gcAllocBytesPerSec / 1024 : null },
  { id: "gc", label: "GC collections", unit: "", lower: true, hint: "server GC collections during the window (each test starts on a freshly collected heap)", get: (r, t) => r.server[t] ? r.server[t].gcCollections : null },
  { id: "rss", label: "Peak RSS", unit: "MB", lower: true, hint: "server peak resident memory", get: (r, t) => r.server[t] ? r.server[t].peakRssBytes / 1048576 : null },
  { id: "rtt50", label: "RTT p50", unit: "ms", lower: true, hint: "client-side, netcode-reported round trip (Fusion includes the relay hop)", get: (r, t) => r.clients[t] ? r.clients[t].rttP50Ms : null },
  { id: "rtt95", label: "RTT p95", unit: "ms", lower: true, hint: "client-side, netcode-reported round trip", get: (r, t) => r.clients[t] ? r.clients[t].rttP95Ms : null },
  { id: "inputs", label: "Inputs received", unit: "/s", lower: false, hint: "ClientInput only: server RPCs received per second (expected tick × connections)", get: (r, t) => r.server[t] ? r.server[t].inputsPerSec : null }
];

const runs = DATA.runs;
const netcodes = ORDER.filter(n => runs.some(r => r.netcode === n));
// A session is one connection count at one tick rate; every netcode ran in it on the same machines.
const scenarios = [...new Map(runs.map(r => [r.size + "@" + r.tick, { size: r.size, tick: r.tick, key: r.size + "@" + r.tick }])).values()]
  .sort((a, b) => a.size - b.size || a.tick - b.tick);
const sizes = [...new Set(scenarios.map(s => s.size))].sort((a, b) => a - b);
const ticks = [...new Set(scenarios.map(s => s.tick))].sort((a, b) => a - b);
const byKey = {};
runs.forEach(r => { byKey[r.netcode + "@" + r.size + "@" + r.tick] = r; });
const run = (n, sc) => byKey[n + "@" + sc.key];
const scLabel = sc => sc.size + " connections · " + sc.tick + " Hz";
// Reference session: the largest connection count at the lowest tick rate that has it.
const reference = scenarios.filter(s => s.size === sizes[sizes.length - 1]).sort((a, b) => a.tick - b.tick)[0];
const state = { scenario: reference, metric: "srvDown", normalize: false, log: false, test: "MoveWander" };
const charts = {};

function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function metricById(id) { return METRICS.find(m => m.id === id); }
function metric() { return metricById(state.metric); }
function rawM(mid, n, sc, t) { const r = run(n, sc); if (!r) return null; const v = metricById(mid).get(r, t); return (v == null || Number.isNaN(v)) ? null : v; }
function raw(n, sc, t) { return rawM(state.metric, n, sc, t); }
function value(n, sc, t) {
  const v = raw(n, sc, t);
  if (v == null) return null;
  if (!state.normalize) return v;
  const base = raw("purrnet", sc, t);
  if (base == null || base === 0) return null;
  return v / base;
}
function fmt(v, unit) {
  if (v == null) return "–";
  if (state.normalize) return fmtX(v);
  const a = Math.abs(v);
  const s = a >= 1000 ? v.toFixed(0) : a >= 100 ? v.toFixed(1) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  return unit ? s + " " + unit : s;
}
function fmtX(v) { return v == null ? "–" : (v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)) + "×"; }
function geomean(xs) { const v = xs.filter(x => x != null && x > 0); return v.length ? Math.exp(v.reduce((a, x) => a + Math.log(x), 0) / v.length) : null; }
const chip = n => `<span class="sw" style="background:var(--s-${n})"></span>${NAMES[n]}`;

function buildHeader() {
  const meta = document.getElementById("meta");
  const first = runs[0];
  const anyTest = first && Object.values(first.server).find(t => t && t.test > 0);
  const chips = [
    ["Sessions", scenarios.map(s => s.size + "c @ " + s.tick + " Hz").join(" · ")],
    ["Objects per test", anyTest ? anyTest.objects : "?"],
    ["Window", anyTest ? Math.round(anyTest.windowSeconds) + " s" : "?"],
    ["Frame cap", "60 fps"],
    ["Build", first && first.meta.devBuild ? "Development" : "Release"]
  ];
  meta.innerHTML = chips.map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`).join("");
  const vers = document.getElementById("versions");
  vers.innerHTML = netcodes.map(n => `<span class="chip"><span class="sw" style="background:var(--s-${n})"></span>${NAMES[n]} <b>${(DATA.versions || {})[n] || "?"}</b></span>`).join("")
    + `<span class="chip">Unity <b>${(DATA.versions || {}).unity || (first && first.meta.unityVersion) || "?"}</b></span>`;
  const f = document.getElementById("footer");
  f.innerHTML = (DATA.runUrl ? `Source run: <a href="${DATA.runUrl}">${DATA.runUrl}</a> · ` : "") + `Rendered ${DATA.rendered}. Lower is better on every metric except inputs received.`;
}

// ---- Scorecard: per netcode, how far from the best across the load tests, in one session.
const GOALS = [
  { id: "srvDown", label: "Bandwidth", tol: 0 },
  { id: "cpu", label: "Server CPU", tol: 0.5 },
  { id: "alloc", label: "GC alloc", tol: 0 }
];
function score(sc) {
  // rel[goal][netcode] = per-test ratios of value / best value in that test; wins = tests won.
  const rel = {}, wins = {};
  GOALS.forEach(g => { rel[g.id] = {}; wins[g.id] = {}; netcodes.forEach(n => { rel[g.id][n] = []; wins[g.id][n] = 0; }); });
  SCORE_TESTS.forEach(t => GOALS.forEach(g => {
    const vals = netcodes.map(n => ({ n, v: rawM(g.id, n, sc, t) })).filter(x => x.v != null);
    if (!vals.length) return;
    const best = Math.min(...vals.map(x => x.v));
    vals.forEach(x => {
      if (x.v - best <= g.tol) wins[g.id][x.n]++;
      if (best > 0) rel[g.id][x.n].push(x.v / best);
    });
  }));
  return { rel, wins };
}
function buildScorecard() {
  const sc = state.scenario;
  const { rel, wins } = score(sc);
  const rows = netcodes.map(n => {
    const r = run(n, sc);
    const have = r ? SCORE_TESTS.filter(t => r.server[t]) : [];
    return {
      n,
      bw: geomean(rel.srvDown[n]),
      cpu: geomean(rel.cpu[n]),
      alloc: geomean(rel.alloc[n]),
      gc: have.length ? have.reduce((a, t) => a + r.server[t].gcCollections, 0) : null,
      p99: have.length ? Math.max(...have.map(t => r.server[t].p99FrameMs)) : null,
      rss: have.length ? Math.max(...have.map(t => r.server[t].peakRssBytes / 1048576)) : null,
      wins: GOALS.reduce((a, g) => a + wins[g.id][n], 0),
      conns: r ? r.connections : null
    };
  });
  const best = key => { const v = rows.map(r => r[key]).filter(x => x != null); return v.length > 1 ? Math.min(...v) : null; };
  const bestWins = Math.max(...rows.map(r => r.wins));
  const cell = (r, key, f, lowerBest = true) => r[key] == null ? `<td class="na">–</td>` : `<td class="${(lowerBest ? r[key] === best(key) : r[key] === bestWins) ? "best" : ""}">${f(r[key])}</td>`;
  const cols = ["Netcode", "Bandwidth", "Server CPU", "GC alloc", "Collections", "Frame p99", "Peak RSS", "Wins"];
  document.getElementById("scorecard").innerHTML =
    "<thead><tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>" +
    rows.map(r => `<tr><td class="name">${chip(r.n)}${r.conns != null && r.conns !== sc.size ? `<span class="sub">${r.conns} clients</span>` : ""}</td>` +
      cell(r, "bw", fmtX) + cell(r, "cpu", fmtX) + cell(r, "alloc", fmtX) + cell(r, "gc", v => String(v)) + cell(r, "p99", v => v.toFixed(2) + " ms") + cell(r, "rss", v => v.toFixed(0) + " MB") +
      cell(r, "wins", v => v + " / " + (SCORE_TESTS.length * GOALS.length), false) + "</tr>").join("") + "</tbody>";
  document.getElementById("score-hint").textContent =
    scLabel(sc) + ". Bandwidth (server downstream) and server CPU are the geometric mean over the " + SCORE_TESTS.length +
    " load tests of this netcode's value divided by the best netcode's value in that test: 1.00× is the best in every test, 2× is twice the best on average. " +
    "GC alloc is the same ratio for managed bytes allocated per second. Collections is the sum over those tests; frame p99 and peak RSS are the worst of them. Wins counts tests where the netcode had the lowest bandwidth, CPU (within 0.5 points) or allocation; ties share the win.";
}

// ---- How it scales: multiplier between the smallest and largest connection count (at the base tick)
//      and between the lowest and highest tick rate (at the largest connection count).
function multiplier(n, from, to, mid) {
  const ratios = SCORE_TESTS.map(t => { const a = rawM(mid, n, from, t), b = rawM(mid, n, to, t); return (a > 0 && b != null) ? b / a : null; });
  return geomean(ratios);
}
function buildScaling() {
  const axes = [];
  const baseTick = ticks[0];
  const bySize = scenarios.filter(s => s.tick === baseTick);
  if (bySize.length > 1) axes.push({ from: bySize[0], to: bySize[bySize.length - 1], label: bySize[0].size + " → " + bySize[bySize.length - 1].size + " connections", note: "at " + baseTick + " Hz" });
  const bigSize = sizes[sizes.length - 1];
  const byTick = scenarios.filter(s => s.size === bigSize);
  if (byTick.length > 1) axes.push({ from: byTick[0], to: byTick[byTick.length - 1], label: byTick[0].tick + " → " + byTick[byTick.length - 1].tick + " Hz", note: "at " + bigSize + " connections" });
  const section = document.getElementById("scaling-section");
  if (!axes.length) { section.hidden = true; return; }
  section.hidden = false;
  const goals = [{ id: "srvDown", label: "Bandwidth" }, { id: "cpu", label: "Server CPU" }];
  const cols = axes.flatMap(a => goals.map(g => ({ a, g })));
  const rows = netcodes.map(n => ({ n, cells: cols.map(c => multiplier(n, c.a.from, c.a.to, c.g.id)) }));
  const bestPer = cols.map((_, i) => { const v = rows.map(r => r.cells[i]).filter(x => x != null); return v.length > 1 ? Math.min(...v) : null; });
  document.getElementById("scaling").innerHTML =
    "<thead><tr><th>Netcode</th>" + cols.map(c => `<th>${c.g.label}<br>${c.a.label}</th>`).join("") + "</tr></thead><tbody>" +
    rows.map(r => `<tr><td class="name">${chip(r.n)}</td>` + r.cells.map((v, i) => v == null ? `<td class="na">–</td>` : `<td class="${v === bestPer[i] ? "best" : ""}">${fmtX(v)}</td>`).join("") + "</tr>").join("") + "</tbody>";
  const lin = axes.map(a => a.label + " (" + a.note + "): a netcode whose cost is linear in that axis lands at " + fmtX((a.to.size / a.from.size) * (a.to.tick / a.from.tick))).join("; ");
  document.getElementById("scaling-hint").textContent = "Geometric mean over the load tests of the ratio between the two sessions. " + lin + ". Below that the netcode amortises; above it the per-unit cost grows.";
}

// ---- Per-test bar charts for the selected metric and session.
function buildControls() {
  const scs = document.getElementById("scenarios");
  scs.innerHTML = scenarios.map(s => `<button type="button" data-key="${s.key}" aria-pressed="${s.key === state.scenario.key}">${scLabel(s)}</button>`).join("");
  scs.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    state.scenario = scenarios.find(s => s.key === b.dataset.key);
    scs.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
    buildScorecard();
    refresh();
  });
  const seg = document.getElementById("metrics");
  seg.innerHTML = METRICS.map(m => `<button type="button" data-id="${m.id}" aria-pressed="${m.id === state.metric}">${m.label}</button>`).join("");
  seg.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    state.metric = b.dataset.id;
    seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
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
      <div class="cv"><canvas id="c-${t}" role="img" aria-label="${t}: ${metric().label} per netcode"></canvas></div>
    </button>`).join("");
  grid.addEventListener("click", e => {
    const c = e.target.closest(".card"); if (!c) return;
    state.test = c.dataset.test;
    grid.querySelectorAll(".card").forEach(x => x.setAttribute("aria-pressed", x === c));
    buildTable();
  });
  TESTS.forEach(t => {
    const ctx = document.getElementById("c-" + t).getContext("2d");
    charts[t] = new Chart(ctx, { type: "bar", data: { labels: netcodes.map(n => NAMES[n]), datasets: [] }, options: baseOptions(t) });
  });
  refresh();
}

function baseOptions(t) {
  const m = metric();
  const ink = css("--ink"), muted = css("--muted"), grid = css("--grid"), axis = css("--axis"), surface = css("--surface");
  return {
    indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: surface, titleColor: ink, bodyColor: ink, borderColor: axis, borderWidth: 1, padding: 10,
        titleFont: { family: "Instrument Sans, system-ui, sans-serif", weight: "600" }, bodyFont: { family: "JetBrains Mono, monospace" },
        callbacks: { title: items => items.length ? t + " · " + scLabel(state.scenario) : "", label: item => " " + item.label + "  " + fmt(item.parsed.x, m.unit) }
      }
    },
    scales: {
      x: {
        type: state.log ? "logarithmic" : "linear", beginAtZero: !state.log,
        title: { display: true, text: state.normalize ? "× PurrNet" : (m.unit || m.label), color: muted, font: { size: 11 } },
        ticks: { color: muted, font: { family: "JetBrains Mono, monospace", size: 11 }, maxTicksLimit: 6, callback: v => state.normalize ? v + "×" : (Math.abs(v) >= 1000 ? (v / 1000).toFixed(v % 1000 ? 1 : 0) + "k" : +Number(v).toFixed(2)) },
        grid: { color: grid }, border: { color: axis, dash: [] }
      },
      y: { ticks: { color: ink, font: { family: "Instrument Sans, system-ui, sans-serif", size: 12 } }, grid: { display: false }, border: { color: axis } }
    }
  };
}

function refresh() {
  const m = metric();
  document.getElementById("metric-hint").textContent = m.hint + (m.lower ? " · lower is better" : " · higher is better");
  document.getElementById("charts-hint").textContent = "· " + scLabel(state.scenario) + " · click a chart to open its table";
  const colors = netcodes.map(n => css("--s-" + n));
  TESTS.forEach(t => {
    const ch = charts[t];
    ch.options = baseOptions(t);
    ch.data.datasets = [{ data: netcodes.map(n => value(n, state.scenario, t)), backgroundColor: colors, borderColor: colors, borderWidth: 0, borderRadius: 3, barPercentage: 0.7, categoryPercentage: 0.8 }];
    ch.update("none");
  });
  buildTable();
}

// ---- Detail table for the clicked test: rows = sessions, columns = netcodes.
function buildTable() {
  const m = metric();
  const t = state.test;
  document.getElementById("table-title").textContent = t + " — " + m.label + (state.normalize ? " relative to PurrNet" : (m.unit ? " (" + m.unit + ")" : ""));
  document.getElementById("table-hint").textContent = TEST_DESC[t] + ". " + m.hint + ". Best value per row is marked; every session is a row.";
  let html = "<thead><tr><th>Session</th>" + netcodes.map(n => `<th>${NAMES[n]}</th>`).join("") + "</tr></thead><tbody>";
  scenarios.forEach(sc => {
    const vals = netcodes.map(n => value(n, sc, t));
    const present = vals.filter(v => v != null);
    const best = present.length > 1 ? (m.lower ? Math.min(...present) : Math.max(...present)) : null;
    html += `<tr><td>${scLabel(sc)}</td>` + netcodes.map((n, i) => {
      const v = vals[i];
      if (v == null) return `<td class="na">–</td>`;
      const r = run(n, sc);
      const note = r && r.connections !== sc.size ? `<span class="rel" title="actual connections">${r.connections}c</span>` : "";
      return `<td class="${v === best ? "best" : ""}">${fmt(v, m.unit)}${note}</td>`;
    }).join("") + "</tr>";
  });
  html += "</tbody>";
  document.getElementById("table").innerHTML = html;
}

function buildNotes() {
  // Every run should have all of its clients at the requested tick; anything else is worth seeing.
  const items = [];
  netcodes.forEach(n => scenarios.forEach(sc => {
    const r = run(n, sc);
    const where = NAMES[n] + " at " + scLabel(sc);
    if (!r) { items.push(where + ": no datapoint"); return; }
    if (r.meta.connectedAtStart !== r.meta.expectedClients)
      items.push(`${where}: only ${r.meta.connectedAtStart} of ${r.meta.expectedClients} clients connected before the connect timeout`);
    else if (r.connections !== sc.size)
      items.push(`${where}: ran with ${r.connections} clients`);
    if (r.meta.tickRate && r.meta.tickRate !== sc.tick)
      items.push(`${where}: the netcode reported a ${r.meta.tickRate} Hz tick, not the requested ${sc.tick} Hz`);
    if (r.meta.serverError) items.push(`${where}: server reported ${r.meta.serverError}`);
    // A test measured on fewer clients than connected means some clients never observed its
    // spawn/despawn transition (state delivery lagged); the average still stands, on fewer samples.
    const short = TESTS.filter(t => r.clients[t] && r.clients[t].n < r.meta.measuredClients).map(t => `${t} (${r.clients[t].n}/${r.meta.measuredClients})`);
    if (short.length) items.push(`${where}: measured on fewer clients than connected: ${short.join(", ")}`);
  }));
  // All netcodes of one session are meant to run on the same server machine; if the CPU models
  // differ the session did not run that way and CPU is not comparable inside it.
  scenarios.forEach(sc => {
    const models = {};
    netcodes.forEach(n => { const r = run(n, sc); if (r && r.meta.cpuModel) models[NAMES[n]] = r.meta.cpuModel; });
    const distinct = [...new Set(Object.values(models))];
    if (distinct.length > 1)
      items.push(`${scLabel(sc)}: servers ran on different CPU models (${Object.entries(models).map(([n, m]) => `${n}: ${m}`).join("; ")}), so CPU is not comparable across netcodes in that session`);
  });
  const ul = document.getElementById("warnings");
  ul.innerHTML = items.map(t => `<li>${t}</li>`).join("");
  ul.hidden = items.length === 0;
}

buildHeader();
buildControls();
buildScorecard();
buildScaling();
buildNotes();
buildCharts();

const rethemes = () => refresh();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", rethemes);
new MutationObserver(rethemes).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
</script>
"""


def normalise(runs):
    """Fill size/tick from the run tag for datapoints written before those fields existed."""
    for r in runs:
        m = re.fullmatch(r"c(\d+)(?:t(\d+))?", str(r.get("tag", "")))
        if not r.get("size"):
            r["size"] = int(m.group(1)) if m else r.get("connections")
        if not r.get("tick"):
            r["tick"] = int(m.group(2)) if m and m.group(2) else (r.get("meta", {}).get("tickRate") or 0)
        r.setdefault("server", {})
        r.setdefault("clients", {})
        r.setdefault("meta", {})
        for t in r["server"].values():
            if isinstance(t, dict):
                t.pop("cpuMarkers", None)
    return runs


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
    runs = normalise(runs)

    versions = {}
    if args.versions and Path(args.versions).exists():
        versions = json.loads(Path(args.versions).read_text(encoding="utf-8"))

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
