// Settings, usage, data sources, tests (the harness) and panels.
import { t, lang, loadLang } from "../i18n.js";
import { h, GET, POST, PUT, DEL, handle, toast, money, num, pct, when, statusTag, progressBar, confirmBox, UI, saveUI, applyTheme, modal } from "../ui.js";
import { onCleanup, refreshMe, rerender, state } from "../app.js";
import { segmented } from "./common.js";

// ================= settings =================
export async function renderSettings(_, v) {
  const [s, prov, models] = await Promise.all([GET("/api/settings"), GET("/api/providers"), GET("/api/models")]);
  v.append(h("div.page-head", h("h1", t("Settings"))));
  const col1 = h("div.grid", { style: { alignContent: "start" } }), col2 = h("div.grid", { style: { alignContent: "start" } });
  v.append(h("div.grid.cols-2", col1, col2));

  // ---- models
  const provList = h("div.grid");
  function drawProviders(p, m) {
    provList.innerHTML = "";
    if (!p.providers.length) provList.append(h("p.small.muted", t("No providers yet. Add one below.")));
    for (const pr of p.providers) {
      const mine = m.models.filter(x => x.provider_id === pr.id);
      const addSel = h("select", h("option", { value: "" }, t("add a model…")), pr.models.filter(x => !mine.some(y => y.model_id === x.id)).map(x => h("option", { value: x.id }, x.label === x.id ? x.id : `${x.label} (${x.id})`)));
      addSel.onchange = async () => { if (!addSel.value) return; await POST("/api/models", { provider_id: pr.id, model_id: addSel.value }); refresh(); };
      provList.append(h("div.card", { style: { padding: "12px 14px" } },
        h("div.row", h("b", { style: { fontWeight: 500 } }, pr.label), h("span.tag" + (pr.status === "ok" ? ".ok" : ".bad"), pr.status === "ok" ? t("healthy") : t("error")),
          pr.key_hint ? h("span.mono", t("key {k}", { k: pr.key_hint })) : null, h("div.spacer"),
          h("button.link.small", { onclick: async () => { await POST(`/api/providers/${pr.id}/check`); refresh(); toast(t("Checked")); } }, t("check")),
          h("button.link.small", { onclick: async () => { if (await confirmBox(t("Remove {p}?", { p: pr.label }), t("Its models are removed too. Past results keep their records."), t("remove"))) { await DEL(`/api/providers/${pr.id}`); refresh(); } } }, t("remove"))),
        pr.status !== "ok" ? h("div.warn", pr.status_msg) : h("div.small.faint", `${pr.kind_name} · ${pr.status_msg} · ${t("checked")} ${when(pr.checked_at)}`),
        h("table.t", { style: { marginTop: "8px" } }, h("thead", h("tr", h("th", t("Model")), h("th.num", t("$ in / M")), h("th.num", t("$ out / M")), h("th", ""))),
          h("tbody", mine.map(x => {
            const pin = h("input", { type: "number", step: "0.01", value: x.price_in ?? "", style: { width: "80px" }, onchange: () => PUT(`/api/models/${x.id}`, { price_in: pin.value }) });
            const pout = h("input", { type: "number", step: "0.01", value: x.price_out ?? "", style: { width: "80px" }, onchange: () => PUT(`/api/models/${x.id}`, { price_out: pout.value }) });
            return h("tr", h("td.small", x.label, x.price_in == null ? h("div.small", { style: { color: "var(--bad)" } }, t("set a price")) : null), h("td.num", pin), h("td.num", pout),
              h("td", h("button.link.small", { onclick: async () => { await DEL(`/api/models/${x.id}`); refresh(); } }, t("remove"))));
          }))), h("div", { style: { marginTop: "8px" } }, addSel)));
    }
  }
  async function refresh() { const [p, m] = await Promise.all([GET("/api/providers"), GET("/api/models")]); drawProviders(p, m); }
  drawProviders(prov, models);

  // add-provider form: paste a key, it's checked at once, pick models from the list
  const kindSel = h("select", Object.entries(prov.kinds).map(([k, x]) => h("option", { value: k }, x.name)));
  const base = h("input", { type: "text", placeholder: "https://…/v1" });
  const baseRow = h("label.f", t("Server address"), base);
  const key = h("input", { type: "password", placeholder: t("Paste your API key"), autocomplete: "off" });
  const status = h("div.small", { style: { minHeight: "20px" } });
  const modelPick = h("select", { multiple: true, size: 6, style: { display: "none" } });
  const search = h("input", { type: "search", placeholder: t("filter models"), style: { display: "none" } });
  const addBtn = h("button.btn", { disabled: true }, t("add provider"));
  let listing = [], timer = 0;
  function showBase() { const k = kindSel.value; baseRow.style.display = ["litellm", "openai_compat"].includes(k) ? "" : "none"; base.value = prov.kinds[k].base_url || ""; check(); }
  function drawModels() {
    const q = search.value.toLowerCase(); modelPick.innerHTML = "";
    listing.filter(m => !q || (m.id + m.label).toLowerCase().includes(q)).slice(0, 300).forEach(m => modelPick.append(h("option", { value: m.id }, m.label === m.id ? m.id : `${m.label} · ${m.id}`)));
  }
  function check() {
    clearTimeout(timer); addBtn.disabled = true;
    const needsKey = prov.kinds[kindSel.value].key;
    if (needsKey && key.value.trim().length < 8) { status.textContent = ""; modelPick.style.display = search.style.display = "none"; return; }
    status.textContent = t("Checking…");
    timer = setTimeout(async () => {
      const r = await POST("/api/providers/test", { kind: kindSel.value, key: key.value.trim(), base_url: base.value.trim() });
      if (r.ok) {
        listing = r.models; status.innerHTML = ""; status.append(h("span.tag.ok", t("key works")), " ", t("{n} models available. Pick the ones to use:", { n: r.models.length }));
        modelPick.style.display = search.style.display = ""; drawModels(); addBtn.disabled = false;
      } else { status.innerHTML = ""; status.append(h("span.tag.bad", t("didn't work")), " ", h("span.small.muted", r.message)); modelPick.style.display = search.style.display = "none"; }
    }, 600);
  }
  kindSel.onchange = showBase; key.oninput = check; base.oninput = check; search.oninput = drawModels;
  addBtn.onclick = async () => {
    const chosen = [...modelPick.selectedOptions].map(o => o.value);
    if (!chosen.length) return toast(t("Pick at least one model."), true);
    try {
      const r = await POST("/api/providers", { kind: kindSel.value, key: key.value.trim(), base_url: base.value.trim(), models: chosen });
      key.value = ""; status.textContent = ""; modelPick.style.display = search.style.display = "none"; addBtn.disabled = true; refresh();
      const bad = Object.entries(r.failed_models || {});
      if (bad.length) toast(t("Provider added, but these models failed a test call and weren't added: {m}", { m: bad.map(([k, v]) => `${k} (${v.slice(0, 80)})`).join("; ") }), true);
      else toast(t("Provider added"));
    }
    catch (e) { handle(e); }
  };
  showBase();
  col1.append(h("div.card", h("h2", t("Models")), h("p.small.muted", t("Keys are stored encrypted and never shown again. Model quality matters a lot: in Pew's 2026 test the best model was off by 11 points on average, a small one by 17.")),
    provList, h("hr"), h("h3", t("Add a provider")), h("div.fields", h("label.f", t("Provider"), kindSel), baseRow, h("label.f.wide", t("API key"), key)),
    status, search, modelPick, h("div.row", { style: { marginTop: "10px" } }, addBtn)));

  // ---- spending
  const cap = h("input", { type: "number", min: 0, step: "1", value: s.monthly_cap ?? "", placeholder: t("unlimited") });
  const conf = h("input", { type: "number", min: 0, step: "0.5", value: s.confirm_above ?? "", placeholder: t("never ask") });
  const conc = h("input", { type: "number", min: 1, max: 32, value: s.concurrency });
  col1.append(h("div.card", h("h2", t("Spending")),
    h("div.fields", h("label.f", t("Monthly cap ($)"), cap), h("label.f", t("Ask before runs above ($)"), conf), h("label.f", t("Calls at once"), conc)),
    h("p.small.muted", t("Unlimited by default. With a cap, runs stop when the month's spending reaches it. See the Usage page for what each study cost.")),
    h("button.btn.small", { onclick: async () => { await PUT("/api/settings", { monthly_cap: cap.value, confirm_above: conf.value, concurrency: conc.value }); toast(t("Saved")); } }, t("save"))));

  // ---- display (this browser)
  const tog = (key, title, sub) => { const cb = h("input", { type: "checkbox", checked: UI[key], onchange: () => { UI[key] = cb.checked; saveUI(); toast(t("Saved")); } });
    return h("label.tog", cb, h("span", title, h("small", sub))); };
  col2.append(h("div.card", h("h2", t("Display")),
    h("div.row", { style: { marginBottom: "10px" } }, segmented(t("theme"), [["light", t("light")], ["dark", t("dark")], ["system", t("system")]], UI.theme, k => { UI.theme = k; saveUI(); applyTheme(); }),
      segmented(t("language"), [["en", "English"], ["es", "Español"]], UI.lang, async k => { UI.lang = k; saveUI(); await loadLang(k); rerender(); })),
    tog("cb", t("Colour-blind friendly colours"), t("Strong blue, orange and pink that stay distinct for every common type of colour blindness.")),
    tog("shapes", t("Shapes as well as colours"), t("Squares, circles, triangles and diamonds, so groups never depend on colour alone.")),
    tog("big", t("Larger dots"), t("Easier to see and to tap.")),
    h("p.small.faint", t("Display settings are saved in this browser."))));

  // ---- sign-in
  const signin = h("div.card", h("h2", t("Sign-in")));
  if (s.auth_mode === "none") {
    const u = h("input", { type: "text", placeholder: t("username") }), p1 = h("input", { type: "password", placeholder: t("password (8+ characters)") });
    signin.append(h("p.small.muted", t("Zócalo is running without sign-in, for one person on their own machine. Create an admin account to turn sign-in on; you can then invite others.")),
      h("div.fields", u, p1), h("button.btn.small", { style: { marginTop: "10px" }, onclick: async () => {
        try { await POST("/api/auth/setup", { username: u.value, password: p1.value }); await refreshMe(); toast(t("Sign-in is on. You're signed in.")); rerender(); } catch (e) { handle(e); } } }, t("turn on sign-in")));
  } else {
    const us = await GET("/api/users").catch(() => null);
    signin.append(h("p.small.muted", t("Signed in as {u}.", { u: state.me?.user?.username || "?" })));
    if (us) {
      signin.append(h("table.t", h("tbody", us.users.map(x => h("tr", h("td", x.username), h("td.small.faint", x.is_admin ? t("admin") : ""),
        h("td", x.id !== state.me?.user?.id ? h("button.link.small", { onclick: async () => { if (await confirmBox(t("Remove {u}?", { u: x.username }), "", t("remove"))) { await DEL(`/api/users/${x.id}`); rerender(); } } }, t("remove")) : null))))),
        h("button.btn.small.secondary", { style: { marginTop: "10px" }, onclick: async () => { const r = await POST("/api/users/invite"); await modal(t("Invite code"), h("div", h("p.small.muted", t("Send this code. They open Zócalo, choose “I have an invite”, and pick a username and password.")), h("pre.mono", { style: { fontSize: "14px" } }, r.code)), [[t("Done"), true]]); } }, t("create an invite")));
    }
    signin.append(h("button.btn.small.secondary", { style: { marginTop: "10px", marginLeft: "6px" }, onclick: async () => { await POST("/api/auth/logout"); location.hash = "#/login"; location.reload(); } }, t("sign out")));
  }
  col2.append(signin);

  // ---- data
  const nc = h("input", { type: "checkbox", checked: s.allow_noncommercial, onchange: () => PUT("/api/settings", { allow_noncommercial: nc.checked }) });
  const dd = h("input", { type: "text", value: s.datasets_path, disabled: !s.datasets_editable || null });
  col2.append(h("div.card", h("h2", t("Data")),
    h("label.f", t("Dataset folder"), dd),
    s.datasets_editable ? h("button.btn.small", { style: { marginTop: "8px" }, onclick: async () => { await PUT("/api/settings", { datasets_dir: dd.value }); toast(t("Saved")); } }, t("save"))
      : h("p.small.muted", t("Set when Zócalo was deployed: {p}. To move it, redeploy with --datasets-dir.", { p: s.datasets_host || s.datasets_path })),
    s.datasets_present ? null : h("div.warn", t("The dataset folder isn't there right now (an external drive unplugged?). Downloads and real populations wait until it's back.")),
    h("label.tog", { style: { marginTop: "8px" } }, nc, h("span", t("Use non-commercial data"), h("small", t("Some sources (WVS, ESS, GlobalOpinionQA, SimBench) allow non-commercial use only. Turn this off if you use Zócalo commercially.")))),
    h("p.mono", `Zócalo ${s.version}`)));
}

// ================= usage =================
export async function renderUsage(_, v) {
  const u = await GET("/api/usage");
  v.append(h("div.page-head", h("h1", t("Usage"), h("br"), h("span", t("{m} this month · {a} in total", { m: money(u.month_spent), a: money(u.total) })))));
  const purposeName = p => ({ study: t("studies"), chat: t("conversations"), test: t("tests") })[p] || p;
  v.append(h("div.grid.cols-3", { style: { marginBottom: "14px" } },
    h("div.card", h("div.eyebrow", t("this month")), h("h2", money(u.month_spent)), h("div.small.muted", u.monthly_cap ? t("cap {c}", { c: money(u.monthly_cap) }) : t("no cap"))),
    h("div.card", h("div.eyebrow", t("all time")), h("h2", money(u.total)), h("div.small.muted", `${num(u.calls)} ${t("calls")}`)),
    h("div.card", h("div.eyebrow", t("by kind")), u.by_purpose.map(p => h("div.row", h("span", purposeName(p.purpose)), h("div.spacer"), h("span.num", money(p.cost)))))));
  v.append(h("div.grid.cols-2",
    h("div.card", h("h3", t("By study")), h("table.t", h("thead", h("tr", h("th", t("Study")), h("th.num", t("calls")), h("th.num", t("tokens")), h("th.num", t("cost")))),
      h("tbody", u.by_study.map(r => h("tr" + (r.study_id ? ".click" : ""), { onclick: r.study_id ? () => location.hash = `#/studies/${r.study_id}` : null },
        h("td", r.name || (r.study_id ? t("deleted study") : t("not part of a study"))), h("td.num", num(r.calls)), h("td.num", num((r.tokens_in || 0) + (r.tokens_out || 0))), h("td.num", money(r.cost))))))),
    h("div.grid", { style: { alignContent: "start" } },
      h("div.card", h("h3", t("By model")), h("table.t", h("tbody", u.by_model.map(r => h("tr", h("td.small", r.name), h("td.num", num(r.calls)), h("td.num", money(r.cost))))))),
      h("div.card", h("h3", t("By month")), h("table.t", h("tbody", u.by_month.map(r => h("tr", h("td", r.month), h("td.num", num(r.calls)), h("td.num", money(r.cost))))))))));
}

// ================= data =================
export async function renderData(_, v) {
  const d = await GET(`/api/data?lang=${lang}`);
  v.append(h("div.page-head", h("h1", t("Data"), h("br"), h("span", t("Census and survey files Zócalo learns from."))),
    h("div.actions", h("a.btn.secondary", { href: "#/docs/data" }, t("download guide")))));
  if (!d.present) v.append(h("div.warn", { style: { marginBottom: "12px" } }, t("The dataset folder ({p}) isn't there right now. If it's on an external drive, plug it in.", { p: d.path })));
  const groups = [["population", t("People: census and population records")], ["opinion", t("Opinions: survey answers")], ["testset", t("Tests: ready-made benchmarks")], ["consumer", t("Spending")]];
  for (const [g, title] of groups) {
    const items = d.sources.filter(s => s.group === g);
    if (!items.length) continue;
    v.append(h("div.card", { style: { marginBottom: "14px" } }, h("h3", title), h("table.t", h("tbody", items.map(s => {
      const act = s.status === "ready" ? (s.indexable ? h("button.link.small", { onclick: async () => { try { await POST(`/api/data/${s.id}/index`); toast(t("Indexing questions…")); } catch (e) { handle(e); } } }, s.indexed ? t("re-index") : t("index questions")) : null)
        : s.access === "auto" ? h("button.btn.small", { disabled: (s.status === "downloading" || !d.present) || null, onclick: async () => { try { await POST(`/api/data/${s.id}/download`); toast(t("Downloading…")); setTimeout(() => dispatchEvent(new HashChangeEvent("hashchange")), 1500); } catch (e) { handle(e); } } }, t("download"))
        : h("button.link.small", { onclick: () => modal(s.name, h("div.doc.small", { html: s.instructions_html }), [[t("Done"), true]]) }, t("how to get it"));
      return h("tr", h("td", h("b", { style: { fontWeight: 500 } }, s.name), h("div.small.muted", s.description), h("div.mono", `${s.licence}${s.noncommercial ? " · " + t("non-commercial") : ""} · ${s.size || ""}`)),
        h("td", statusTag(s.status), s.status === "downloading" ? progressBar(s.progress) : null, s.message ? h("div.small.faint", s.message) : null),
        h("td.num", act));
    })))));
  }
  if (d.sources.some(s => s.status === "downloading" || s.status === "indexing")) {
    const timer = setTimeout(() => location.hash === "#/data" && dispatchEvent(new HashChangeEvent("hashchange")), 2500); onCleanup(() => clearTimeout(timer));
  }
}

// ================= tests =================
export async function renderTests(_, v) {
  const [d, models, pops] = await Promise.all([GET("/api/tests"), GET("/api/models"), GET("/api/populations")]);
  v.append(h("div.page-head", h("h1", t("Tests"), h("br"), h("span", t("How wrong is it? Measured, not assumed.")))));
  // error table
  v.append(h("div.card", { style: { marginBottom: "14px" } }, h("h3", t("Error by question type")),
    h("p.small.muted", t("These numbers set the error shown on every result. Until your own tests cover a type (20+ questions), Zócalo uses figures from published evaluations.")),
    h("div.scroll-x", h("table.t", h("thead", h("tr", h("th", t("Type")), h("th.num", t("published: typical")), h("th.num", t("1 in 5 over")), h("th.num", t("yours: typical")), h("th.num", t("1 in 5 over")), h("th.num", t("questions tested")))),
      h("tbody", d.error_table.map(r => h("tr", h("td", t(r.qtype) + (r.topical ? ` · ${t("topical")}` : "")), h("td.num", `±${r.prior_p50}`), h("td.num", `±${r.prior_p80}`),
        h("td.num", r.measured_p50 != null ? `±${r.measured_p50.toFixed(1)}` : "—"), h("td.num", r.measured_p80 != null ? `±${r.measured_p80.toFixed(1)}` : "—"), h("td.num", r.items))))))));
  // new run
  const ts = h("select", d.testsets.map(x => h("option", { value: x.id, disabled: !x.ready || null }, `${x.name}${x.ready ? "" : " · " + t("not downloaded")}`)));
  const meth = h("select", [["population", t("simulated people (the real method)")], ["aggregate", t("baseline: ask the model for the shares directly")],
    ["anchor", t("baseline: closest other real poll")], ["uniform", t("baseline: every option equal")], ["knn", t("baseline: similar real respondents (no AI)")]].map(([k, l]) => h("option", { value: k }, l)));
  const mod = h("select", models.models.filter(m => m.enabled).map(m => h("option", { value: m.id }, `${m.provider_label} · ${m.label}`)));
  const nItems = h("input", { type: "number", value: 10, min: 1, max: 500 });
  const nPeople = h("input", { type: "number", value: 30, min: 5, max: 2000 });
  const country = h("input", { type: "text", placeholder: t("e.g. US, MX, DE (optional)") });
  const desc = h("p.small.muted");
  const showDesc = () => { const x = d.testsets.find(y => y.id === ts.value); desc.textContent = x ? x.description : ""; };
  ts.onchange = showDesc; showDesc();
  v.append(h("div.card", { style: { marginBottom: "14px" } }, h("h3", t("Run a test")), desc,
    h("div.fields", h("label.f", t("Test set"), ts), h("label.f", t("Method"), meth), h("label.f", t("Model"), mod), h("label.f", t("Country"), country),
      h("label.f", t("Questions"), nItems), h("label.f", t("People per question"), nPeople)),
    h("p.small.faint", t("Calls ≈ questions × people. Start small: 10 × 30 is 300 calls.")),
    h("button.btn", { onclick: async () => { try { const r = await POST("/api/tests", { testset: ts.value, method: meth.value, model: mod.value, n_items: +nItems.value, n_people: +nPeople.value, country: country.value.trim().toUpperCase() || null }); location.hash = `#/tests/${r.id}`; } catch (e) { handle(e); } } }, t("run test"))));
  // scoreboard
  if (d.runs.length) {
    v.append(h("div.card", h("h3", t("Scoreboard")), h("p.small.muted", t("Mean error per question in points (lower is better). Pew's 2026 silicon-samples study: 12.4 points on average, 28% of questions over 15.")),
      h("div.scroll-x", h("table.t", h("thead", h("tr", ["Test set", "Method", "Model", "Questions", "Mean error", "Typical", "Over 15", "Missed options", "Spread", "Ranges held", "Cost", ""].map(x => h("th", t(x))))),
        h("tbody", d.runs.map(r => h("tr.click", { onclick: () => location.hash = `#/tests/${r.id}` }, h("td.small", r.testset), h("td.small", t(r.method)), h("td.small", r.model_name),
          r.metrics ? [h("td.num", r.metrics.items), h("td.num", r.metrics.mae_mean), h("td.num", r.metrics.mae_p50), h("td.num", pct(r.metrics.share_over_15)), h("td.num", r.metrics.missed_options),
            h("td.num", r.metrics.spread_ratio ?? "—"), h("td.num", r.metrics.coverage_p80 != null ? pct(r.metrics.coverage_p80) : "—"), h("td.num", money(r.metrics.cost))]
            : h("td", { colspan: 8 }, statusTag(r.status), r.status === "running" ? progressBar(r.progress) : null, h("span.small.faint", " " + (r.status_msg || ""))),
          h("td.small.faint", when(r.created_at))))))),
      h("p.small.faint", t("“Spread” is simulated over real spread on scales (below 1 = answers too bunched). “Ranges held” is how often the shown 1-in-5 error range covered the real error (should be about 80%).")),
      h("p.small.faint", t("The no-AI “similar respondents” baseline sees other respondents' real answers to the same question, so its overall error is a ceiling for questions that have already been asked, not a fair rival. Compare its individual accuracy instead."))));
    if (d.runs.some(r => r.status === "running" || r.status === "queued")) { const tm = setTimeout(() => location.hash === "#/tests" && dispatchEvent(new HashChangeEvent("hashchange")), 3000); onCleanup(() => clearTimeout(tm)); }
  }
}

export async function renderTestRun([id], v) {
  const r = await GET(`/api/tests/${id}`);
  v.append(h("div.page-head", h("h1", r.testset, h("br"), h("span", `${t(r.method)} · ${r.model_name}`)),
    h("div.actions", r.status === "running" ? h("button.btn.secondary", { onclick: () => POST(`/api/tests/${id}/cancel`) }, t("stop")) : null,
      h("button.btn.danger", { onclick: async () => { await DEL(`/api/tests/${id}`); location.hash = "#/tests"; } }, t("delete")))));
  if (r.status === "running" || r.status === "queued") { v.append(progressBar(r.progress)); const tm = setTimeout(() => dispatchEvent(new HashChangeEvent("hashchange")), 2500); onCleanup(() => clearTimeout(tm)); }
  if (r.status_msg) v.append(h("div.warn", r.status_msg));
  const m = r.metrics;
  if (m) v.append(h("div.grid.cols-3", { style: { margin: "12px 0" } },
    h("div.card", h("div.eyebrow", t("mean error")), h("h2", `${m.mae_mean} ${t("pts")}`), h("div.small.muted", t("typical {a}, 1 in 5 over {b}", { a: m.mae_p50, b: m.mae_p80 }))),
    h("div.card", h("div.eyebrow", t("questions over 15 pts")), h("h2", pct(m.share_over_15)), h("div.small.muted", t("{n} options real people chose were almost never simulated", { n: m.missed_options }))),
    h("div.card", h("div.eyebrow", t("ranges held")), h("h2", m.coverage_p80 != null ? pct(m.coverage_p80) : "—"), h("div.small.muted", m.individual_accuracy != null ? t("individual accuracy {a}", { a: pct(m.individual_accuracy) }) : t("should be about 80%")))));
  v.append(h("div.card", h("div.scroll-x", h("table.t", h("thead", h("tr", h("th", t("Question")), h("th", t("real vs simulated")), h("th.num", t("error")), h("th.num", t("worst option")))),
    h("tbody", r.items.map(i => h("tr", h("td.small", i.meta.text, h("div.mono", `${i.qtype}${i.meta.country ? " · " + i.meta.country : ""}`)),
      h("td", { style: { minWidth: "220px" } }, i.meta.options.map((o, k) => h("div.small", { style: { display: "grid", gridTemplateColumns: "1fr 44px 44px", gap: "6px" } },
        h("span.faint", o.length > 40 ? o.slice(0, 39) + "…" : o), h("span.num", pct(i.real[k])), h("span.num", { style: { color: "var(--blue)" } }, pct(i.sim[k]))))),
      h("td.num", i.abs_error.toFixed(1)), h("td.num", i.meta.max.toFixed(1))))))),
    h("p.small.faint", t("Left number: real share. Blue: simulated."))));
}

// ================= panels =================
export async function renderPanels(_, v) {
  const d = await GET("/api/panels");
  v.append(h("div.page-head", h("h1", t("Panels"), h("br"), h("span", t("The same people, asked again.")))));
  if (!d.panels.length) { v.append(h("div.card.empty", h("h2", t("No panels yet")), h("p", t("Filter a population or a study's respondents, then “save as panel”.")))); return; }
  v.append(h("div.card", h("table.t", h("tbody", d.panels.map(p => h("tr", h("td", h("b", { style: { fontWeight: 500 } }, p.name)), h("td.small.muted", p.population), h("td.num", num(p.size)), h("td.small.faint", when(p.created_at)),
    h("td.num", h("a.btn.small", { href: `#/studies/new?panel=${p.id}` }, t("ask them")), " ", h("button.link.small", { onclick: async () => { if (await confirmBox(t("Delete this panel?"), t("The people stay in their population."), t("delete"))) { await DEL(`/api/panels/${p.id}`); rerender(); } } }, t("delete")))))))));
}
