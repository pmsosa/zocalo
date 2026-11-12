// Documents (methodology, data guide) and the sign-in page.
import { t, lang } from "../i18n.js";
import { h, GET, POST, api, handle } from "../ui.js";
import { refreshMe } from "../app.js";

export async function renderDoc(name, v) {
  const d = await GET(`/api/docs/${name}?lang=${lang}`);
  const body = h("article.doc", { html: d.html });
  const toc = h("nav.toc");
  body.querySelectorAll("h2").forEach(el => { if (!el.id) el.id = el.textContent.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    toc.append(h("a", { href: `#${location.hash.slice(1).split("#")[0]}`, onclick: e => { e.preventDefault(); el.scrollIntoView({ behavior: "smooth" }); } }, el.textContent)); });
  if (lang !== "en" && d.lang === "en") v.append(h("div.warn", { style: { marginBottom: "12px" } }, t("This document isn't translated yet; showing English.")));
  v.append(h("div.split", { style: { gridTemplateColumns: "220px minmax(0,1fr)" } }, h("div.side", toc), body));
}

export async function renderLogin(_, v) {
  const me = await GET("/api/me");
  if (!me.needs_login && !me.needs_setup) { location.hash = "#/"; return; }
  const u = h("input", { type: "text", placeholder: t("username"), autocomplete: "username" });
  const p = h("input", { type: "password", placeholder: t("password"), autocomplete: me.needs_setup ? "new-password" : "current-password" });
  const code = h("input", { type: "text", placeholder: t("invite code") });
  let mode = me.needs_setup ? "setup" : "login";
  const box = h("div.card.lift.login");
  function draw() {
    box.innerHTML = "";
    box.append(h("img", { src: "/static/icons/mark-light.svg", alt: "", style: { width: "40px", marginBottom: "12px" } }),
      h("h2", mode === "setup" ? t("Create the admin account") : mode === "join" ? t("Join with an invite") : t("Sign in to Zócalo")),
      mode === "join" ? code : null, u, h("div", { style: { height: "8px" } }), p,
      h("button.btn", { style: { marginTop: "12px", width: "100%", justifyContent: "center" }, onclick: submit }, mode === "setup" ? t("create account") : mode === "join" ? t("join") : t("sign in")),
      mode !== "setup" ? h("p.small", { style: { marginTop: "12px" } }, h("button.link", { onclick: () => { mode = mode === "join" ? "login" : "join"; draw(); } }, mode === "join" ? t("I have an account") : t("I have an invite"))) : null);
  }
  async function submit() {
    try {
      const path = mode === "setup" ? "/api/auth/setup" : mode === "join" ? "/api/auth/join" : "/api/auth/login";
      await api("POST", path, { username: u.value, password: p.value, code: code.value }, { allow401: true });
      await refreshMe(); location.hash = "#/";
    } catch (e) { handle(e); }
  }
  p.addEventListener("keydown", e => e.key === "Enter" && submit());
  draw();
  v.append(box);
}
