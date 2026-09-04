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
  td .sub.stall { color: var(--warn); }

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
    <div class="row"><span class="lbl">Session</span><div class="seg scenarios" role="group" aria-label="Session"></div></div>
    <div class="tablewrap"><table id="scorecard"></table></div>
    <p id="score-hint"></p>
  </section>

  <section id="scaling-section" hidden>
    <h2>What one more costs <span class="hint">&#xb7; marginal server cost of a connection and of a tick per second; lower is better</span></h2>
    <div class="tablewrap"><table id="scaling"></table></div>
    <p id="scaling-hint"></p>
  </section>

  <section>
    <h2>Per test <span class="hint" id="charts-hint"></span></h2>
    <div class="controls" role="region" aria-label="Chart controls">
      <div class="row"><span class="lbl">Session</span><div class="seg scenarios" role="group" aria-label="Session"></div></div>
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
<p>Every netcode runs the same scenario: the server spawns N objects and replicates them to every client. On-wire bytes are read from the network interface (UDP/IP headers, ACKs and resends included). CPU is the whole server process, all threads, as % of one core with the frame loop capped at 60 fps; nothing is subtracted, so the Idle row is what holding N connections costs on its own. Fusion is relay-based (Photon Cloud): its traffic is measured on the public interface, but the server still sends one stream per client, so its downstream is comparable. Every session runs all netcodes on the same server machine and the same client machines, so numbers are comparable across netcodes within a session. Networking defaults are retained except for the documented compatibility and workload changes in the README: FishNet's Tugboat packet size lowered from 1350 to 1200 for the 1280-byte tailnet, NGO's Unity Transport packet queue raised from 128 to 4096, and NGO's NetworkTransforms set to unreliable deltas, which is how the other four deliver transforms out of the box. For the tick-driven SyncVars scenario, the four FishNet fields also have their additional 0.1-second send interval removed after initialization; channel and permissions remain unchanged. Benchmark workload scheduling is also documented there: Mirror uses an application-level tick loop without changing Unity physics timing; the other projects use native ticks. Generated/received counts, frame-sampled client-visible field changes and field silence accompany final-state checks. Field silence is time since a value last changed locally, not time since the server wrote it. These checks do not establish equal one-way latency or replication precision.</p>
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
// tol: values this close to the best count as tied ({rel: fraction of the best} or {abs: units}).
// Cross-test comparison metrics only; single-test workload/delivery diagnostics stay in raw data and notes.
const METRICS = [
  { id: "srvDown", label: "Server downstream", unit: "KB/s", lower: true, tol: { rel: 0.01 }, hint: "bytes the server puts on the wire to all clients", get: (r, t) => kb(r.server[t] && r.server[t].txBytesPerSec) },
  { id: "cpu", label: "Server CPU", unit: "%", lower: true, tol: { abs: 0.5 }, hint: "whole process CPU as % of one core, nothing subtracted", get: (r, t) => r.server[t] ? r.server[t].cpuPercent : null },
  { id: "cliDown", label: "Per-client downstream", unit: "KB/s", lower: true, tol: { rel: 0.01 }, hint: "average received by one measured client", get: (r, t) => kb(r.clients[t] && r.clients[t].rxBytesPerSec) },
  { id: "srvUp", label: "Server upstream", unit: "KB/s", lower: true, tol: { rel: 0.01 }, hint: "bytes the server receives from all clients", get: (r, t) => kb(r.server[t] && r.server[t].rxBytesPerSec) },
  { id: "cliUp", label: "Per-client upstream", unit: "KB/s", lower: true, tol: { rel: 0.01 }, hint: "average sent by one measured client", get: (r, t) => kb(r.clients[t] && r.clients[t].txBytesPerSec) },
  { id: "p99", label: "Frame p99", unit: "ms", lower: true, tol: { abs: 0.2 }, hint: "server main-thread frame time, 99th percentile; the loop is capped at 60 fps, so 16.7 ms is on budget and anything above means the server could not keep up", get: (r, t) => r.server[t] ? r.server[t].p99FrameMs : null },
  { id: "pkts", label: "Packets out", unit: "/s", lower: true, tol: { rel: 0.01 }, hint: "server datagrams sent per second", get: (r, t) => r.server[t] ? r.server[t].txPacketsPerSec : null },
  { id: "alloc", label: "GC alloc", unit: "KB/s", lower: true, tol: { rel: 0.02 }, hint: "managed bytes the server allocates per second, all threads, from heap growth between frames; the garbage the collections are made of", get: (r, t) => r.server[t] && r.server[t].gcAllocBytesPerSec >= 0 ? r.server[t].gcAllocBytesPerSec / 1024 : null },
  { id: "gc", label: "GC collections", unit: "", lower: true, tol: { abs: 0 }, hint: "server GC collections during the window (each test starts on a freshly collected heap)", get: (r, t) => r.server[t] ? r.server[t].gcCollections : null },
  { id: "rss", label: "Peak RSS", unit: "MB", lower: true, tol: { rel: 0.02 }, hint: "server peak resident memory", get: (r, t) => r.server[t] ? r.server[t].peakRssBytes / 1048576 : null },
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
// Only offer metrics the dataset actually has (older runs lack allocation; some lack client bandwidth).
const hasAny = m => runs.some(r => TESTS.some(t => { const v = m.get(r, t); return v != null && !Number.isNaN(v); }));
const AVAILABLE = METRICS.filter(hasAny);
const state = { scenario: reference, metric: AVAILABLE.some(m => m.id === "srvDown") ? "srvDown" : (AVAILABLE[0] || METRICS[0]).id, normalize: false, log: false, test: "MoveWander" };
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
function fmtKb(v) { return v == null ? "–" : v >= 1024 ? (v / 1024).toFixed(2) + " MB/s" : v >= 100 ? v.toFixed(0) + " KB/s" : v.toFixed(1) + " KB/s"; }
function fmtPct(v) { return v == null ? "–" : v.toFixed(1) + "%"; }
function mean(xs) { const v = xs.filter(x => x != null); return v.length ? v.reduce((a, x) => a + x, 0) / v.length : null; }
function geomean(xs) { const v = xs.filter(x => x != null && x > 0); return v.length ? Math.exp(v.reduce((a, x) => a + Math.log(x), 0) / v.length) : null; }
// Indices of the values that share the best, within tol ({rel} or {abs}); empty when fewer than two
// values exist or when every value ties, since a highlight then says nothing.
// A value that renders as the same text as the best is tied too: a mark between two "0.14 KB/s" cells
// would only be reporting digits the reader cannot see.
function bestSet(vals, lower = true, tol = { rel: 0.01 }, fmtFn = null) {
  const present = vals.map((v, i) => [v, i]).filter(([v]) => v != null && !Number.isNaN(v));
  if (present.length < 2) return new Set();
  const best = lower ? Math.min(...present.map(([v]) => v)) : Math.max(...present.map(([v]) => v));
  const eps = tol.abs != null ? tol.abs : Math.abs(best) * tol.rel;
  const bestText = fmtFn ? fmtFn(best) : null;
  const set = new Set(present.filter(([v]) => Math.abs(v - best) <= eps || (fmtFn && fmtFn(v) === bestText)).map(([, i]) => i));
  return set.size === present.length ? new Set() : set;
}
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
  f.innerHTML = (DATA.runUrl ? `Source run: <a href="${DATA.runUrl}">${DATA.runUrl}</a> · ` : "") + `Rendered ${DATA.rendered}. Lower is better on cost metrics. Workload and receipt rates are diagnostic: compare them with the expected load, not a higher-is-better ranking.`;
}

// ---- Scorecard: per netcode, how far from the best across the load tests, in one session.
const GOALS = [
  { id: "srvDown", label: "Bandwidth", tol: 0 },
  { id: "cpu", label: "Server CPU", tol: 0.5 },
  { id: "alloc", label: "GC alloc", tol: 0 }
];
const goalsInUse = GOALS.filter(g => AVAILABLE.some(m => m.id === g.id));
// A server that did not keep up in a test: frame p99 past twice the 60 fps budget, a sixth of its
// frames dropped, clients lost, or memory run away to four times its own Idle footprint. Its
// bandwidth and CPU then describe a stall, not the netcode, so the test is left out of scoring.
function stalled(n, sc, t) {
  const r = run(n, sc); if (!r) return false;
  if (r.meta.serverError) return true;
  const w = r.server[t]; if (!w) return false;
  const idleRss = r.server.Idle ? r.server.Idle.peakRssBytes : 0;
  return w.p99FrameMs > 33.3 || (w.avgFps > 0 && w.avgFps < 54) ||
    (r.meta.expectedClients > 0 && w.connections < 0.9 * r.meta.expectedClients) ||
    (idleRss > 0 && w.peakRssBytes > 4 * idleRss);
}
function stalledAnywhere(n, sc) { return SCORE_TESTS.some(t => stalled(n, sc, t)); }
function score(sc) {
  // rel[goal][netcode] = per-test ratios of value / best value in that test; wins = tests won.
  const rel = {}, wins = {};
  GOALS.forEach(g => { rel[g.id] = {}; wins[g.id] = {}; netcodes.forEach(n => { rel[g.id][n] = []; wins[g.id][n] = 0; }); });
  SCORE_TESTS.forEach(t => goalsInUse.forEach(g => {
    const vals = netcodes.map(n => ({ n, v: stalled(n, sc, t) ? null : rawM(g.id, n, sc, t) })).filter(x => x.v != null);
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
    // Plain averages over the load tests, in the metric's own unit. A netcode that stalled in any of
    // them gets no average: one over the tests it survived would not compare with the others'.
    const avg = mid => stalledAnywhere(n, sc) ? null : mean(SCORE_TESTS.map(t => rawM(mid, n, sc, t)));
    return {
      n,
      stalls: r ? SCORE_TESTS.filter(t => stalled(n, sc, t)).length : 0,
      err: r && r.meta.serverError ? r.meta.serverError : null,
      bw: avg("srvDown"),
      cpu: avg("cpu"),
      alloc: avg("alloc"),
      gc: have.length ? have.reduce((a, t) => a + r.server[t].gcCollections, 0) : null,
      p99: have.length ? Math.max(...have.map(t => r.server[t].p99FrameMs)) : null,
      rss: have.length ? Math.max(...have.map(t => r.server[t].peakRssBytes / 1048576)) : null,
      wins: goalsInUse.reduce((a, g) => a + wins[g.id][n], 0),
      conns: r ? r.connections : null
    };
  });
  const TOL = { bw: { rel: 0.02 }, cpu: { rel: 0.02 }, alloc: { rel: 0.02 }, gc: { abs: 0 }, p99: { abs: 0.2 }, rss: { rel: 0.02 }, wins: { abs: 0 } };
  const FMT = { bw: fmtKb, cpu: fmtPct, alloc: fmtKb, gc: String, p99: v => v.toFixed(1), rss: v => v.toFixed(0), wins: String };
  const bests = {};
  Object.keys(TOL).forEach(k => { bests[k] = bestSet(rows.map(r => r[k]), k !== "wins", TOL[k], FMT[k]); });
  const cell = (r, i, key, f) => r[key] == null ? `<td class="na">–</td>` : `<td class="${bests[key].has(i) ? "best" : ""}">${f(r[key])}</td>`;
  const COLS = [
    ["Bandwidth", "bw", fmtKb], ["Server CPU", "cpu", fmtPct], ["GC alloc", "alloc", fmtKb], ["Collections", "gc", v => String(v)],
    ["Frame p99", "p99", v => v.toFixed(1) + " ms"], ["Peak RSS", "rss", v => v.toFixed(0) + " MB"], ["Wins", "wins", v => v + " / " + (SCORE_TESTS.length * goalsInUse.length)]
  ].filter(([, key]) => rows.some(r => r[key] != null));
  document.getElementById("scorecard").innerHTML =
    "<thead><tr><th>Netcode</th>" + COLS.map(([label]) => `<th>${label}</th>`).join("") + "</tr></thead><tbody>" +
    rows.map((r, i) => `<tr><td class="name">${chip(r.n)}${r.conns != null && r.conns !== sc.size ? `<span class="sub">${r.conns} clients</span>` : ""}${r.err ? `<span class="sub stall">${r.err}</span>` : r.stalls ? `<span class="sub stall">stalled in ${r.stalls} of ${SCORE_TESTS.length} tests</span>` : ""}</td>` +
      COLS.map(([, key, f]) => cell(r, i, key, f)).join("") + "</tr>").join("") + "</tbody>";
  document.getElementById("score-hint").textContent =
    scLabel(sc) + ". Averages over the " + SCORE_TESTS.length + " load tests: bandwidth is what the server puts on the wire to all clients, CPU is the whole server process as a share of one core, GC alloc is managed bytes allocated per second. " +
    "Collections is the sum over those tests; frame p99 and peak RSS are the worst of them (the loop is capped at 60 fps, so 16.7 ms means every test stayed on budget). Wins counts tests where the netcode had the lowest bandwidth, CPU (within 0.5 points) or allocation; ties share the win. Nothing is marked best when the column is a tie. A netcode that stalled in any test shows no averages, since one over the tests it survived would not compare. A test counts as stalled when the server's frame p99 passed twice the budget, it dropped more than a sixth of its frames, it lost clients, or its memory ran to four times its Idle footprint: it wins nothing and stays out of the averages, since a server that stopped serving also stops spending.";
}

// ---- What one more costs: (cost at the larger session - cost at the smaller) / (units added), averaged
//      over the load tests. Unlike a multiplier this does not flatter a netcode with an expensive floor.
function marginal(n, from, to, mid, units) {
  // A server that fell over in either session has no measurable marginal cost.
  if (stalledAnywhere(n, from) || stalledAnywhere(n, to)) return null;
  const deltas = SCORE_TESTS.map(t => {
    if (stalled(n, from, t) || stalled(n, to, t)) return null;
    const a = rawM(mid, n, from, t), b = rawM(mid, n, to, t);
    return (a != null && b != null) ? (b - a) / units : null;
  }).filter(v => v != null);
  return deltas.length ? deltas.reduce((x, y) => x + y, 0) / deltas.length : null;
}
function fmtCost(v, unit) { return v == null ? "–" : (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(3)) + " " + unit; }
function buildScaling() {
  const axes = [];
  const baseTick = ticks[0];
  const bySize = scenarios.filter(s => s.tick === baseTick);
  if (bySize.length > 1) axes.push({ from: bySize[0], to: bySize[bySize.length - 1], label: "per connection", units: bySize[bySize.length - 1].size - bySize[0].size, note: bySize[0].size + " → " + bySize[bySize.length - 1].size + " connections at " + baseTick + " Hz" });
  const bigSize = sizes[sizes.length - 1];
  const byTick = scenarios.filter(s => s.size === bigSize);
  if (byTick.length > 1) axes.push({ from: byTick[0], to: byTick[byTick.length - 1], label: "per Hz", units: byTick[byTick.length - 1].tick - byTick[0].tick, note: byTick[0].tick + " → " + byTick[byTick.length - 1].tick + " Hz at " + bigSize + " connections" });
  const section = document.getElementById("scaling-section");
  if (!axes.length) { section.hidden = true; return; }
  section.hidden = false;
  const goals = [{ id: "srvDown", label: "Bandwidth", unit: "KB/s" }, { id: "cpu", label: "Server CPU", unit: "pts" }];
  const cols = axes.flatMap(a => goals.map(g => ({ a, g })));
  const rows = netcodes.map(n => ({ n, cells: cols.map(c => marginal(n, c.a.from, c.a.to, c.g.id, c.a.units)) }));
  // Marginal costs divide two noisy readings, so a wider tolerance than the raw metrics get.
  const bestPer = cols.map((c, i) => bestSet(rows.map(r => r.cells[i]), true, { rel: 0.05 }, v => fmtCost(v, c.g.unit)));
  document.getElementById("scaling").innerHTML =
    "<thead><tr><th>Netcode</th>" + cols.map(c => `<th>${c.g.label}<br>${c.a.label}</th>`).join("") + "</tr></thead><tbody>" +
    rows.map((r, ri) => `<tr><td class="name">${chip(r.n)}</td>` + r.cells.map((v, i) => v == null ? `<td class="na">–</td>` : `<td class="${bestPer[i].has(ri) ? "best" : ""}">${fmtCost(v, cols[i].g.unit)}</td>`).join("") + "</tr>").join("") + "</tbody>";
  document.getElementById("scaling-hint").textContent = "Difference between the two sessions divided by what was added, averaged over the load tests: " + axes.map(a => a.label + " from " + a.note).join("; ") +
    ". Bandwidth in KB/s, CPU in percentage points of one core. A dash means the server stalled somewhere in one of the two sessions, so its cost could not be measured.";
}

// ---- Per-test bar charts for the selected metric and session.
function buildControls() {
  // The session drives the scorecard, the charts and the table, so the selector appears above each.
  const groups = [...document.querySelectorAll(".scenarios")];
  groups.forEach(g => {
    g.innerHTML = scenarios.map(s => `<button type="button" data-key="${s.key}" aria-pressed="${s.key === state.scenario.key}">${scLabel(s)}</button>`).join("");
    g.addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      state.scenario = scenarios.find(s => s.key === b.dataset.key);
      groups.forEach(x => x.querySelectorAll("button").forEach(y => y.setAttribute("aria-pressed", y.dataset.key === state.scenario.key)));
      buildScorecard();
      refresh();
    });
  });
  const seg = document.getElementById("metrics");
  seg.innerHTML = AVAILABLE.map(m => `<button type="button" data-id="${m.id}" aria-pressed="${m.id === state.metric}">${m.label}</button>`).join("");
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
  let empty = 0;
  TESTS.forEach(t => {
    const ch = charts[t];
    const data = netcodes.map(n => value(n, state.scenario, t));
    if (data.every(v => v == null)) empty++;
    ch.options = baseOptions(t);
    ch.data.datasets = [{ data, backgroundColor: colors, borderColor: colors, borderWidth: 0, borderRadius: 3, barPercentage: 0.7, categoryPercentage: 0.8 }];
    ch.update("none");
  });
  if (empty === TESTS.length)
    document.getElementById("charts-hint").textContent += " · no " + m.label.toLowerCase() + " data in this session (its client results are missing); pick another session or metric";
  buildTable();
}

// ---- Detail table for the clicked test: rows = sessions, columns = netcodes.
function buildTable() {
  const m = metric();
  const t = state.test;
  document.getElementById("table-title").textContent = t + " — " + m.label + (state.normalize ? " relative to PurrNet" : (m.unit ? " (" + m.unit + ")" : ""));
  document.getElementById("table-hint").textContent = TEST_DESC[t] + ". " + m.hint + ". The best value per row is marked, shared when tied, not at all when the whole row ties.";
  let html = "<thead><tr><th>Session</th>" + netcodes.map(n => `<th>${NAMES[n]}</th>`).join("") + "</tr></thead><tbody>";
  scenarios.forEach(sc => {
    const vals = netcodes.map(n => value(n, sc, t));
    const best = bestSet(vals, m.lower, state.normalize ? { rel: 0.02 } : m.tol, v => fmt(v, m.unit));
    html += `<tr><td>${scLabel(sc)}</td>` + netcodes.map((n, i) => {
      const v = vals[i];
      if (v == null) return `<td class="na">–</td>`;
      const r = run(n, sc);
      const note = r && r.connections !== sc.size ? `<span class="rel" title="actual connections">${r.connections}c</span>` : "";
      return `<td class="${best.has(i) ? "best" : ""}">${fmt(v, m.unit)}${note}</td>`;
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
    const rpc = r.clients.SendRPC;
    if (rpc && rpc.rpcDeliveryChecked > 0)
      items.push(`${where}: complete reliable RPC delivery on ${rpc.rpcDeliveryMatched}/${rpc.rpcDeliveryChecked} checked clients (spawn through despawn, including warmup and delivery grace).`);
    const sync = r.clients.SyncVars;
    if (sync && sync.syncObservationClients > 0) {
      const expected = r.server.SyncVars ? r.server.SyncVars.objects * r.meta.tickRate : null;
      items.push(`${where}: client-visible SyncVar changes ${sync.syncObservedChangesPerSec.toFixed(1)}/s per client (nominal ${expected == null ? "unknown" : expected}/s); longest observed field silence ${sync.syncSilenceMaxMs.toFixed(1)} ms, on ${sync.syncObservationClients}/${r.meta.measuredClients} measured clients. Frame-sampled observations, not per-mutation delivery or one-way latency.`);
    }
    if (r.server.SyncVars && Object.hasOwn(r.server.SyncVars, "syncObservationAvailable") &&
        (!sync || !sync.syncObservationClients || sync.syncObservationClients < r.meta.measuredClients))
      items.push(`${where}: client-visible SyncVar observation is missing or incomplete; no freshness conclusion can be drawn from final-state matching alone.`);
    if (sync && sync.syncStateChecked > 0)
      items.push(`${where}: exact final SyncVar state matched on ${sync.syncStateMatched}/${sync.syncStateChecked} checked clients. A mismatch is diagnostic; native precision and delivery delay need investigation.`);
    ["SendRPC", "SyncVars"].forEach(t => {
      const s = r.server[t], c = r.clients[t];
      if (s && Object.hasOwn(s, "deliveryComplete") && (!s.deliveryComplete || !c || (t === "SendRPC" ? c.rpcDeliveryChecked : c.syncStateChecked) < r.meta.measuredClients))
        items.push(`${where}: ${t} delivery validation is incomplete; missing checks are not passes.`);
    });
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
