// Populations: build one (demo or from real data), then explore it as dots with filters.
import { t } from "../i18n.js";
import { h, GET, POST, DEL, handle, toast, num, when, confirmBox, palette, statusTag } from "../ui.js";
import { onCleanup } from "../app.js";
import { createDots } from "../dots.js";
import { personTip, filterEditor, matches, describe, legend, segmented, FIELD_LABEL, SEX, ageBand, AGE_ORDER } from "./common.js";
import { openPersonDrawer } from "./people.js";

export async function render([id], v) {
  const d = await GET("/api/populations");
  const pops = d.populations;
  d.sources = null;  // fetched only when building, because listing countries can be slow
  v.append(h("div.page-head", h("h1", t("Population"), h("br"), h("span", t("Who your simulated people are."))),
    h("div.actions", pops.length ? h("button.btn.secondary", { onclick: () => buildForm(d.sources) }, t("build another")) : null)));
  if (!pops.length) { v.append(buildCard(d.sources)); return; }
  const cur = pops.find(p => p.id === +id) || pops[0];
  const pick = h("select", { onchange: () => location.hash = `#/population/${pick.value}` },
    pops.map(p => h("option", { value: p.id, selected: p.id === cur.id }, `${p.name} · ${num(p.size)}`)));
  const data = await GET(`/api/populations/${cur.id}/people`);
  const people = data.people;
  const meta = data.population.meta || {};
  const side = h("div.side"), stage = h("div.stage", { style: { height: "min(78vh, 760px)" } });
  v.append(h("div.split", side, stage));
  const L = FIELD_LABEL();
  const fields = ["party", "age_band", "sex", "region", "education", "religion", "urban", "race", "country", "vote_last", "ideology"].filter(f =>
    f === "age_band" ? people.some(p => p.f.age != null) : new Set(people.map(p => p.f[f]).filter(Boolean)).size > 1);
  let colorBy = fields[0] || "sex", layout = colorBy, flt = {};
  const legendEl = h("div.legend"), tools = h("div.tools");
  stage.append(h("div.head", h("h2", data.population.name.split("·")[0].trim() + ".", h("br"), h("span", `${num(people.length)} ${t("people")}`))), tools, legendEl, h("div.hint", t("hover a dot · click to talk")));
  const dots = createDots(stage, { tip: p => personTip(p), onClick: p => openPersonDrawer(p.id, {}), lastIsUnsure: false,
    quote: p => ({ text: [p.f.occupation || p.f.employment, p.f.region].filter(Boolean).join(", ") || p.name, who: `${p.name.split(" ")[0]}, ${p.f.age ?? ""}` }) });
  onCleanup(() => dots.destroy());
  dots.setPeople(people);
  const val = (p, f) => f === "age_band" ? ageBand(p.f.age) : p.f[f];
  function values(f) {
    const c = new Map(); for (const p of people) { const x = val(p, f); if (x != null) c.set(x, (c.get(x) || 0) + 1); }
    let vs = [...c.entries()].sort((a, b) => b[1] - a[1]).map(x => x[0]);
    if (f === "age_band") vs = AGE_ORDER.filter(x => c.has(x));
    return vs;
  }
  function colour() {
    const vs = values(colorBy).slice(0, 8);
    dots.setColor(vs.map(x => colorBy === "sex" ? SEX(x) : x), p => { const i = vs.indexOf(val(p, colorBy)); return i < 0 ? 7 : i; });
    legend(legendEl, vs.map(x => colorBy === "sex" ? SEX(x) : x), palette(vs.length, false));
  }
  function grouping() {
    if (layout === "sphere") return dots.setLayout("sphere");
    dots.setLayout("split");
    dots.setGroups(p => { const x = val(p, layout); return x == null ? null : layout === "sex" ? SEX(x) : x; }, layout === "age_band" ? AGE_ORDER : null);
  }
  tools.append(segmented(t("layout"), [...fields.slice(0, 5).map(f => [f, (L[f] || f).toLowerCase()]), ["sphere", t("explore ✦")]], layout, k => { layout = k; grouping(); }),
    segmented(t("colour"), fields.slice(0, 5).map(f => [f, (L[f] || f).toLowerCase()]), colorBy, k => { colorBy = k; colour(); }));
  colour(); grouping();

  const who = h("div.q", { style: { fontSize: "16px", margin: "12px 0 8px" } });
  const fe = filterEditor(people, f => { flt = f; dots.setSelected(p => matches(p, flt)); upd(); });
  function upd() {
    const sel = people.filter(p => matches(p, flt));
    who.innerHTML = ""; who.append(describe(flt), h("span", ` · ${num(sel.length)}`));
    actions.innerHTML = "";
    actions.append(h("button.btn.small", { disabled: !sel.length || null, onclick: async () => {
      const r = await POST("/api/panels", { name: `${describe(flt)} · ${data.population.name}`, population_id: cur.id, person_ids: sel.map(p => p.id) });
      location.hash = `#/studies/new?panel=${r.id}`; } }, t("ask them")),
      h("button.btn.small.secondary", { disabled: !sel.length || null, onclick: async () => {
        const r = await POST("/api/panels", { name: `${describe(flt)} · ${data.population.name}`, population_id: cur.id, person_ids: sel.map(p => p.id) });
        toast(t("Panel saved: {n} people", { n: r.size })); } }, t("save as panel")),
      h("a.btn.small.secondary", { href: `#/chats/new?ids=${sel.slice(0, 6).map(p => p.id).join(",")}` }, t("focus group")));
  }
  const actions = h("div.row");
  const src = { demo: t("Made-up people from rounded country shares. For trying the app; don't rely on results.") }[data.population.source];
  const phone = matchMedia("(max-width: 720px)").matches;
  side.append(h("div.card", h("div.eyebrow", t("population")), pick,
      h("p.small.muted", { style: { margin: "10px 0 0" } }, src || meta.description || t("Built from {s}.", { s: data.population.source })),
      meta.weights ? h("p.small.faint", meta.weights) : null,
      h("div.row", { style: { marginTop: "8px" } }, h("span.mono", `${data.population.country} · ${data.population.source} · ${when(data.population.created_at)}`),
        h("div.spacer"), h("button.link.small", { onclick: async () => {
          if (await confirmBox(t("Delete this population?"), t("Its people are deleted too. Studies that use it must be deleted first."), t("delete"))) {
            try { await DEL(`/api/populations/${cur.id}`); location.hash = "#/population"; } catch (e) { handle(e); } } } }, t("delete")))),
    phone ? h("details.card", h("summary", t("Filter people")), fe.el, who, actions) : h("div.card", h("div.eyebrow", t("who to look at")), fe.el, who, actions));
  if (phone) side.insertBefore(stage, side.children[1]);
  upd();
}

function buildCard(sourcesIn) {
  const box = h("div.card", { style: { maxWidth: "640px" } }, h("h2", t("Build a population")), h("p.small.muted", t("Checking which data is available…")));
  (async () => {
    const sources = sourcesIn || (await GET("/api/populations/sources")).sources;
    box.replaceWith(buildForm_(sources));
  })().catch(handle);
  return box;
}

function buildForm_(sources) {
  const S = { source: "demo", country: "US", size: 2000 };
  const name = h("input", { type: "text", placeholder: t("Name (optional)") });
  const srcSel = h("select", { onchange: () => { S.source = srcSel.value; countries(); } },
    sources.map(s => h("option", { value: s.id, disabled: !s.ready || null }, `${t(s.name)}${s.ready ? "" : " · " + t("not downloaded")}`)));
  const cSel = h("select", { onchange: () => S.country = cSel.value });
  const size = h("input", { type: "number", value: 2000, min: 10, oninput: () => S.size = +size.value });
  const note = h("p.small.muted");
  function countries() {
    const s = sources.find(x => x.id === S.source);
    cSel.innerHTML = "";
    (s?.countries || []).forEach(c => cSel.append(h("option", { value: c.code }, c.name)));
    S.country = s?.countries?.[0]?.code;
    note.textContent = s?.note || (s?.kind === "demo" ? t("Made-up people from rounded country shares. Good for learning the app; not for real answers.") : "");
  }
  countries();
  const status = h("div");
  const go = h("button.btn", { onclick: async () => {
    if (!S.country) return toast(t("Choose a country."), true);
    go.disabled = true;
    try {
      const r = await POST("/api/populations", { name: name.value.trim() || null, source: S.source, country: S.country, size: S.size });
      const poll = async () => {
        const j = await GET(`/api/populations/jobs/${r.job}`);
        status.innerHTML = ""; status.append(statusTag(j.status), " ", h("span.small.muted", j.message || ""));
        if (j.status === "running") setTimeout(poll, 1000);
        else if (j.status === "done") location.hash = `#/population/${j.population_id}`;
        else go.disabled = false;
      };
      poll();
    } catch (e) { handle(e); go.disabled = false; }
  } }, t("build"));
  const sizeWarn = h("p.small.faint", t("Most studies use 1,000–2,000 people. You can ask a random sample of them later."));
  return h("div.card", { style: { maxWidth: "640px" } }, h("h2", t("Build a population")),
    h("div.fields", h("label.f", t("From"), srcSel), h("label.f", t("Country"), cSel), h("label.f", t("People"), size), h("label.f", t("Name"), name)),
    note, sizeWarn, h("p.small", h("a", { href: "#/data" }, t("Get real census and survey data on the Data page."))), h("div.row", go, status));
}

async function buildForm(sources) {
  const back = h("div.modal-back", { onclick: e => { if (e.target === back) back.remove(); } }, h("div", { style: { width: "min(640px,100%)" } }, buildCard(null)));
  document.body.append(back);
  onCleanup(() => back.remove());
}
