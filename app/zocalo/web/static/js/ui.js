// Small helpers shared by every view: elements, API calls, formatting, colours, dialogs.
import { t, lang } from "./i18n.js";

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// h("div.card#x", {onclick}, child, "text", [more]) — tiny element builder
export function h(spec, attrs, ...kids) {
  if (attrs == null || typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs)) { kids.unshift(attrs); attrs = {}; }
  const m = spec.match(/^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i);
  const el = document.createElement(m[1] || "div");
  for (const part of (m[2] || "").match(/[.#][\w-]+/g) || []) {
    if (part[0] === ".") el.classList.add(part.slice(1)); else el.id = part.slice(1);
  }
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k === "value") el.value = v;
    else if (k === "checked") el.checked = !!v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  add(el, kids);
  return el;
}
function add(el, kids) {
  for (const k of kids) {
    if (k == null || k === false) continue;
    if (Array.isArray(k)) add(el, k);
    else el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// ---- API ----
export class ApiError extends Error { constructor(msg, status) { super(msg); this.status = status; } }
export async function api(method, path, body, opts = {}) {
  const init = { method, headers: {}, credentials: "same-origin" };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) { init.body = JSON.stringify(body); init.headers["Content-Type"] = "application/json"; }
  const r = await fetch(path, init);
  if (r.status === 401 && !opts.allow401) { location.hash = "#/login"; throw new ApiError(t("Please sign in."), 401); }
  let data = null;
  const ct = r.headers.get("content-type") || "";
  data = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new ApiError((data && data.detail) || r.statusText, r.status);
  return data;
}
export const GET = p => api("GET", p);
export const POST = (p, b) => api("POST", p, b ?? {});
export const PUT = (p, b) => api("PUT", p, b);
export const DEL = p => api("DELETE", p);

// ---- UI settings (stored in this browser) ----
export const UI = Object.assign({ theme: "light", lang: "en", cb: false, shapes: false, big: false, bannerClosed: false },
  JSON.parse(localStorage.getItem("zocalo-ui") || "{}"));
export function saveUI() { localStorage.setItem("zocalo-ui", JSON.stringify(UI)); }
export function applyTheme() {
  const dark = UI.theme === "dark" || (UI.theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  const mark = document.getElementById("brandMark");
  if (mark) mark.src = `/static/icons/small-${dark ? "dark" : "light"}.svg`;  // the favicon SVG follows the browser's own theme
  document.querySelectorAll('meta[name="theme-color"]').forEach(m => m.content = dark ? "#1c1c1a" : "#efefe4");
}
export const isDark = () => document.documentElement.dataset.theme === "dark";

// ---- colours: quiet house palette, or Okabe–Ito (distinct for common colour blindness) ----
const BASE = ["#5d8cd7", "#2b2b29", "#b8735c", "#8fb59a", "#9b8ac4", "#c9a227", "#6aa6a6", "#a86b8f"];
const BASE_DARK = ["#7aa3e6", "#e6e4dc", "#e08a70", "#8fc49f", "#b3a3e0", "#e0bd45", "#7cc2c2", "#d08bb3"];
const OKABE = ["#0072B2", "#D55E00", "#CC79A7", "#009E73", "#E69F00", "#56B4E9", "#F0E442", "#000000"];
const OKABE_DARK = ["#56B4E9", "#E69F00", "#CC79A7", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#ffffff"];
export function palette(n, withUnsure = true) {
  const p = UI.cb ? (isDark() ? OKABE_DARK : OKABE) : (isDark() ? BASE_DARK : BASE);
  const unsure = isDark() ? "#6c6b66" : "#b9b9b2";
  const cols = Array.from({ length: n }, (_, i) => p[i % p.length]);
  if (withUnsure && n > 1) cols[n - 1] = UI.cb ? (isDark() ? "#9a9a9a" : "#8a8a8a") : unsure;
  return cols;
}
export function swatch(col, k, size = 10) {
  const shapes = ['<rect x="1" y="1" width="8" height="8"/>', '<circle cx="5" cy="5" r="4.4"/>', '<path d="M5 .5 9.5 9H.5z"/>',
    '<path d="M5 0 10 5 5 10 0 5z"/>', '<path d="M1 3h8v4H1z"/>', '<path d="M3 1h4v8H3z"/>', '<circle cx="5" cy="5" r="2.6"/>', '<path d="M1 1h8L5 9z"/>'];
  const span = document.createElement("span");
  span.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 10 10" style="margin-right:6px;vertical-align:-1px" fill="${col}">${UI.shapes ? shapes[k % shapes.length] : shapes[0]}</svg>`;
  return span.firstChild;
}

// ---- formatting ----
export const pct = (x, d = 0) => `${(x * 100).toFixed(d)}%`;
export const money = x => x == null ? "—" : x < 0.01 && x > 0 ? `$${x.toFixed(4)}` : `$${x.toFixed(2)}`;
export const num = x => (x ?? 0).toLocaleString(lang === "es" ? "es-MX" : "en-US");
export const when = ts => ts ? new Date(ts * 1000).toLocaleString(lang === "es" ? "es-MX" : "en-US", { dateStyle: "medium", timeStyle: "short" }) : "—";

// ---- feedback ----
export function toast(msg, bad = false) {
  const el = h("div.toast" + (bad ? ".bad" : ""), msg);
  document.body.append(el);
  setTimeout(() => el.remove(), bad ? 6000 : 3000);
}
export function modal(title, body, actions = []) {
  return new Promise(resolve => {
    const close = v => { back.remove(); resolve(v); };
    const back = h("div.modal-back", { onclick: e => { if (e.target === back) close(null); } },
      h("div.modal", { role: "dialog", "aria-modal": "true" }, h("h2", title), body,
        h("div.row", { style: { justifyContent: "flex-end", marginTop: "16px" } },
          actions.map(([label, val, cls]) => h("button.btn" + (cls ? "." + cls : ""), { onclick: () => close(typeof val === "function" ? val() : val) }, label)))));
    document.body.append(back);
    setTimeout(() => { const f = back.querySelector("input,textarea,select,button"); f && f.focus(); }, 30);
  });
}
export async function confirmBox(title, text, okLabel) {
  return modal(title, h("p.muted", text), [[t("Cancel"), false, "secondary"], [okLabel || t("OK"), true]]);
}
export function handle(e) { console.error(e); if (!(e instanceof ApiError && e.status === 401)) toast(e.message || String(e), true); }

// options text: first part ink, rest slate (the two-tone headline)
export function twoTone(text, el = "h2.q") {
  const words = String(text).split(" "), cut = Math.max(1, Math.ceil(words.length * 0.55));
  return h(el, words.slice(0, cut).join(" ") + " ", h("span", words.slice(cut).join(" ")));
}

export function progressBar(x) { return h("div.progress", h("i", { style: { width: `${Math.round((x || 0) * 100)}%` } })); }
export function statusTag(status) {
  const cls = { done: "ok", ready: "ok", ok: "ok", running: "run", queued: "run", error: "bad", stopped: "bad", missing: "bad" }[status] || "";
  return h("span.tag" + (cls ? "." + cls : ""), t(status));
}
