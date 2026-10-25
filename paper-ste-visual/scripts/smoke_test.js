#!/usr/bin/env node
// Smoke test for a built page: loads it in jsdom, clicks the main controls and
// reports script errors. Needs jsdom:  npm install jsdom   (once, in any folder)
// Usage: node smoke_test.js page.html
const fs = require("fs");
const { JSDOM, VirtualConsole } = require("jsdom");

const file = process.argv[2];
if (!file) { console.log("usage: node smoke_test.js page.html"); process.exit(2); }
const html = fs.readFileSync(file, "utf8").replace(/<link[^>]*>/g, "");
const errs = [];
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => errs.push(e.message));
vc.on("error", (e) => errs.push(String(e)));
const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc });
const d = dom.window.document;

setTimeout(() => {
  const report = {
    sections: d.querySelectorAll("section").length,
    diagrams: d.querySelectorAll("figure.diagram").length,
    charts: d.querySelectorAll(".chart").length,
    tableRows: d.querySelectorAll(".tbl tbody tr").length,
    badges: d.querySelectorAll(".wc").length,
    overLimit: d.querySelectorAll(".wc.over").length,
    stats: d.getElementById("stats").textContent,
  };
  // exercise controls
  d.querySelectorAll(".anim-ctl button").forEach((b) => b.click());
  d.querySelectorAll(".scen .chip").forEach((b) => b.click());
  d.querySelectorAll(".chart .chip").forEach((b) => b.click());
  ["lang-en", "lang-zh", "lang-both"].forEach((id) => d.getElementById(id).click());
  setTimeout(() => {
    report.errors = errs;
    console.log(JSON.stringify(report, null, 2));
    process.exit(errs.length ? 1 : 0);
  }, 1200);
}, 400);
