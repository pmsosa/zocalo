// Zócalo single-page app: router, navigation, banners.
import { loadLang, t } from "./i18n.js";
import { $, h, GET, UI, saveUI, applyTheme, handle } from "./ui.js";
import * as home from "./views/home.js";
import * as newstudy from "./views/newstudy.js";
import * as study from "./views/study.js";
import * as population from "./views/population.js";
import * as people from "./views/people.js";
import * as admin from "./views/admin.js";
import * as docs from "./views/docs.js";

export const state = { me: null, cleanup: [] };

const ICONS = {
  studies: '<path d="M5 4h14v16H5z"/><path d="M8 9h8M8 13h8M8 17h5"/>',
  population: '<circle cx="7" cy="8" r="1.6"/><circle cx="12" cy="8" r="1.6"/><circle cx="17" cy="8" r="1.6"/><circle cx="7" cy="13" r="1.6"/><circle cx="12" cy="13" r="1.6"/><circle cx="17" cy="13" r="1.6"/><circle cx="12" cy="18" r="1.6"/>',
  chats: '<path d="M4 5h16v11H9l-5 4z"/>',
  tests: '<path d="M4 20h16M7 16V9M12 16V5M17 16v-4"/>',
  more: '<circle cx="6" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="18" cy="12" r="1.5"/>',
};
const NAV = [["#/", "Studies", "studies"], ["#/population", "Population", "population"], ["#/chats", "Conversations", "chats"],
  ["#/panels", "Panels"], ["#/tests", "Tests", "tests"], ["#/data", "Data"], ["#/usage", "Usage"], ["#/methodology", "Methodology"]];

const ROUTES = [
  [/^\/$/, home.render], [/^\/studies\/new$/, newstudy.render], [/^\/studies\/(\d+)$/, study.render],
  [/^\/population(?:\/(\d+))?$/, population.render], [/^\/people\/(\d+)$/, people.renderPerson],
  [/^\/chats$/, people.renderChats], [/^\/chats\/new$/, people.renderNewGroup], [/^\/chats\/(\d+)$/, people.renderChat],
  [/^\/panels$/, admin.renderPanels], [/^\/tests$/, admin.renderTests], [/^\/tests\/(\d+)$/, admin.renderTestRun],
  [/^\/data$/, admin.renderData], [/^\/usage$/, admin.renderUsage], [/^\/settings$/, admin.renderSettings],
  [/^\/methodology$/, (p, v) => docs.renderDoc("methodology", v)], [/^\/docs\/data$/, (p, v) => docs.renderDoc("data", v)],
  [/^\/login$/, docs.renderLogin], [/^\/more$/, renderMore],
];

function renderNav() {
  const path = location.hash.slice(1) || "/";
  const on = href => { const p = href.slice(1); return p === "/" ? (path === "/" || path.startsWith("/studies")) : path.startsWith(p); };
  const nav = $("#nav"); nav.innerHTML = "";
  for (const [href, label] of NAV) nav.append(h("a", { href, class: on(href) ? "on" : null }, t(label)));
  const tab = $("#tabbar"); tab.innerHTML = "";
  for (const [href, label, icon] of [["#/", "Studies", "studies"], ["#/population", "Population", "population"],
    ["#/chats", "Chats", "chats"], ["#/tests", "Tests", "tests"], ["#/more", "More", "more"]]) {
    const a = h("a", { href, class: on(href) ? "on" : null }); a.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">${ICONS[icon]}</svg>`;
    a.append(t(label)); tab.append(a);
  }
  $("#settingsBtn").title = t("Settings");
}

function renderMore() {
  const v = $("#view"); v.innerHTML = "";
  v.append(h("div.page-head", h("h1", t("More"))),
    h("div.grid", [["#/panels", "Panels", "Saved groups of people you can ask again."], ["#/data", "Data", "Census and survey files, downloads, status."],
      ["#/usage", "Usage", "What each study cost."], ["#/methodology", "Methodology", "How Zócalo works, and its limits."],
      ["#/settings", "Settings", "Models, spending, display, language, sign-in."]].map(([href, title, sub]) =>
      h("a.card", { href, style: { textDecoration: "none" } }, h("h3", t(title)), h("div.muted.small", t(sub))))));
}

function renderBanners() {
  const b = $("#banners"); b.innerHTML = "";
  if (state.me?.auth_mode === "none" && !UI.bannerClosed) {
    b.append(h("div.banner", h("span", t("Zócalo is running without sign-in: anyone who can reach this address can use it. You can turn on sign-in in "),
      h("a", { href: "#/settings" }, t("Settings")), "."),
      h("button.x", { "aria-label": t("Close"), onclick: () => { UI.bannerClosed = true; saveUI(); renderBanners(); } }, "×")));
  }
}

async function route() {
  for (const fn of state.cleanup.splice(0)) try { fn(); } catch (e) { /* view already gone */ }
  document.getElementById("tip").classList.remove("on");
  const path = location.hash.slice(1) || "/";
  if (state.me?.needs_login && path !== "/login") { location.hash = "#/login"; return; }
  renderNav();
  const v = $("#view"); v.innerHTML = ""; window.scrollTo(0, 0);
  for (const [re, fn] of ROUTES) {
    const m = path.match(re);
    if (m) { try { await fn(m.slice(1), v); } catch (e) { handle(e); } return; }
  }
  v.append(h("div.empty", h("h2", t("Not found")), h("a.ghost", { href: "#/" }, t("Back to studies"))));
}

export function onCleanup(fn) { state.cleanup.push(fn); }

async function boot() {
  applyTheme();
  await loadLang(UI.lang);
  try { state.me = await GET("/api/me"); } catch (e) { state.me = null; }
  renderBanners();
  addEventListener("hashchange", route);
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => UI.theme === "system" && applyTheme());
  await route();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}
export async function refreshMe() { state.me = await GET("/api/me"); renderBanners(); }
export async function rerender() { renderBanners(); await route(); }
boot();
