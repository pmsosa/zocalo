// A study: cost check and run, then results with labelled error, the population as dots, filters,
// effects, subgroups, anchors, human-sample correction, and conversations with any respondent.
import { t, lang } from "../i18n.js";
import { h, GET, POST, DEL, api, handle, toast, palette, money, num, pct, progressBar, statusTag, confirmBox, twoTone, UI } from "../ui.js";
import { onCleanup } from "../app.js";
import { createDots } from "../dots.js";
import { bars, diffBars, errorNote, howMade, personTip, filterEditor, matches, describe, legend, segmented, FIELD_LABEL, SEX, ageBand, AGE_ORDER } from "./common.js";
import { kindLabel } from "./home.js";
import { openPersonDrawer } from "./people.js";

const ARM_LABEL = () => ({ main: t("Everyone"), A: t("Half A"), B: t("Half B"), control: t("Control (no news)"), treatment: t("Treatment (news)"),
  placebo: t("Placebo"), within_before: t("Same person · before"), within_after: t("Same person · after") });

export async function render([id], v) {
  const sid = +id;
  let st = await GET(`/api/studies/${sid}`);
  if (st.status === "draft" || st.status === "error") return renderDraft(st, v);
  if (st.status === "running") {
    const box = h("div.card", { style: { maxWidth: "640px" } });
    v.append(head(st), box);
    const tick = async () => {
      st = await GET(`/api/studies/${sid}`);
      if (!box.isConnected) return;
      if (st.status !== "running") { dispatchEvent(new HashChangeEvent("hashchange")); return; }
      box.innerHTML = "";
      box.append(h("div.eyebrow", t("running")), h("h2", `${pct(st.progress)}`), progressBar(st.progress),
        h("p.small.muted", t("Spent so far: {c}", { c: money(st.cost_actual) })),
        h("button.btn.secondary", { onclick: () => POST(`/api/studies/${sid}/cancel`) }, t("stop")));
      timer = setTimeout(tick, 1500);
    };
    let timer = 0; tick(); onCleanup(() => clearTimeout(timer));
    return;
  }
  await renderResults(st, v);
}

function head(st) {
  return h("div.page-head", h("h1", st.name, h("br"), h("span", `${t(kindLabel(st.kind))} · ${st.population?.name || ""}`)),
    h("div.actions",
      h("button.btn.secondary", { onclick: async () => { const r = await POST(`/api/studies/${st.id}/duplicate`); location.hash = `#/studies/${r.id}`; } }, t("duplicate")),
      h("button.btn.danger", { onclick: async () => { if (await confirmBox(t("Delete this study?"), t("Its answers are deleted too. Costs stay on the Usage page."), t("delete"))) { await DEL(`/api/studies/${st.id}`); location.hash = "#/"; } } }, t("delete"))));
}

async function renderDraft(st, v) {
  v.append(head(st));
  const est = await GET(`/api/studies/${st.id}/estimate`);
  const box = h("div.card", { style: { maxWidth: "720px" } },
    h("div.eyebrow", st.status === "error" ? t("couldn't run") : t("ready to run")),
    st.status_msg ? h("div.warn", st.status_msg) : null,
    h("h2", t("{n} people · {q} questions · {c} calls", { n: num(est.people), q: est.questions, c: num(est.calls) })),
    h("table.t", h("tbody", est.models.map(m => h("tr", h("td", m.name), h("td.num", num(m.calls) + " " + t("calls")),
      h("td.num", m.price_known ? money(m.cost) : t("price unknown")))))),
    h("p", h("b", { style: { fontWeight: 500 } }, t("Estimated cost: {c}", { c: money(est.cost) })), h("span.faint.small", " · " + t("this month so far: {m}", { m: money(est.month_spent) }))),
    est.big_panel ? h("div.warn", t("Over 10,000 people: this may cost a lot.")) : null,
    est.over_cap ? h("div.warn", t("This would go over your monthly cap. Raise it in Settings to run.")) : null,
    est.models.some(m => !m.price_known) ? h("div.warn", t("Some models have no price set, so the estimate is too low. Set prices in Settings.")) : null,
    h("ul.small.muted", st.questions.map(q => h("li", q.text))),
    h("div.row", { style: { justifyContent: "flex-end", marginTop: "10px" } },
      h("button.btn", { disabled: est.over_cap || null, onclick: async () => {
        let r = await POST(`/api/studies/${st.id}/run`, { lang });
        if (r.needs_confirm) {
          if (!await confirmBox(t("Run this study?"), t("Estimated cost {c} is above your confirmation threshold.", { c: money(r.estimate.cost) }), t("run"))) return;
          r = await POST(`/api/studies/${st.id}/run`, { lang, confirm: true });
        }
        dispatchEvent(new HashChangeEvent("hashchange"));
      } }, t("run study"))));
  v.append(box);
}

async function renderResults(st, v) {
  let res = await POST(`/api/studies/${st.id}/results`, { lang });
  v.append(head(st));
  if (st.status_msg) v.append(h("div.warn", { style: { marginBottom: "12px" } }, st.status_msg));
  if (!res.questions.length || !res.people.length) { v.append(h("div.card.empty", h("h2", t("No answers")), h("p", t("Every call failed. Check the model in Settings, then duplicate and run again.")))); return; }
  let qi = 0, arm = res.questions[0].main_arm, colorBy = "answer", layout = "answer", flt = {}, ansFilter = null;
  const side = h("div.side"), stage = h("div.stage", { style: { height: "min(78vh, 760px)" } });
  const mainCol = h("div.grid");
  v.append(h("div.split", side, mainCol)); mainCol.append(stage);
  const legendEl = h("div.legend"), tools = h("div.tools");
  stage.append(h("div.head", h("h2", `${num(res.people.length)} ${t("people")}`, h("br"), h("span", res.study.population?.name || ""))), tools, legendEl, h("div.hint", t("hover a dot · click to talk")));
  const q = () => res.questions[qi];
  const dots = createDots(stage, {
    tip: p => personTip(p, { ...q(), arm }),
    onClick: p => openPersonDrawer(p.id, { study: res.study, question: q(), arm, answer: p.answers?.[q().id]?.[arm], models: res.models }),
    quote: p => { const a = p.answers?.[q().id]?.[arm]; return a?.reason ? { text: a.reason, who: `${p.name.split(" ")[0]}, ${p.f.age ?? ""} · ${p.f.region || p.f.country || ""}` } : null; },
    groupNote: ps => colorBy === "answer" && layout !== "answer" ? `${Math.round(ps.reduce((s, p) => s + (p.answers?.[q().id]?.[arm]?.spread?.[0] || 0), 0) / Math.max(ps.length, 1) * 100)}% ${q().options[0].toLowerCase()}` : "",
  });
  onCleanup(() => dots.destroy());
  const inArm = p => !!p.answers?.[q().id]?.[arm];
  const pick = p => p.answers?.[q().id]?.[arm]?.pick ?? 0;

  function colour() {
    const qq = q();
    if (colorBy === "answer") { dots.setColor(qq.options, pick); legend(legendEl, qq.options, palette(qq.options.length)); }
    else {
      const f = colorBy, vals = [...new Set(res.people.map(p => f === "age_band" ? ageBand(p.f.age) : p.f[f]).filter(x => x != null))];
      if (f === "age_band") vals.sort((a, b) => AGE_ORDER.indexOf(a) - AGE_ORDER.indexOf(b));
      const idx = p => Math.max(0, vals.indexOf(f === "age_band" ? ageBand(p.f.age) : p.f[f]));
      const cats = vals.slice(0, 8);
      dots.setColor(cats.map(x => f === "sex" ? SEX(x) : x), p => Math.min(idx(p), 7));
      dots.dotsUnsure = false;
      legend(legendEl, cats.map(x => f === "sex" ? SEX(x) : x), palette(cats.length, false));
    }
  }
  function grouping() {
    if (layout === "sphere") { dots.setLayout("sphere"); return; }
    dots.setLayout("split");
    if (layout === "answer") dots.setGroups(p => q().options[pick(p)], q().options);
    else if (layout === "age_band") dots.setGroups(p => ageBand(p.f.age), AGE_ORDER);
    else dots.setGroups(p => { const x = p.f[layout]; return x == null ? null : layout === "sex" ? SEX(x) : x; });
  }
  function selection() {
    dots.setSelected(p => inArm(p) && matches(p, flt) && (ansFilter == null || pick(p) === ansFilter));
  }
  function refreshDots() {
    dots.setPeople(res.people.filter(inArm));
    colour(); grouping(); selection();
  }
  const fieldsAvail = ["party", "age_band", "sex", "region", "education", "country", "urban", "religion"].filter(f =>
    f === "age_band" ? res.people.some(p => p.f.age != null) : new Set(res.people.map(p => p.f[f]).filter(Boolean)).size > 1);
  const L = FIELD_LABEL();
  tools.append(segmented(t("layout"), [["answer", t("answer")], ...fieldsAvail.slice(0, 5).map(f => [f, L[f].toLowerCase()]), ["sphere", t("explore ✦")]], layout,
    k => { layout = k; grouping(); }),
  segmented(t("colour"), [["answer", t("answer")], ...fieldsAvail.slice(0, 3).map(f => [f, L[f].toLowerCase()])], colorBy, k => { colorBy = k; colour(); }));

  // ---- side: question + results
  const qCard = h("div.card"), effectCard = h("div"), filterCard = h("div.card"), extra = h("div.grid");
  const phone = matchMedia("(max-width: 720px)").matches;
  if (phone) {
    const fold = h("details.card", h("summary", t("Filter people")), filterCard);
    filterCard.classList.remove("card");
    side.append(qCard, stage, effectCard, fold, howMade(res));
  } else side.append(qCard, effectCard, filterCard, howMade(res));
  mainCol.append(extra);

  function renderQ() {
    const qq = q(); const a = qq.arms[arm]; const cols = palette(qq.options.length);
    const selPeople = res.people.filter(p => inArm(p) && matches(p, flt) && (ansFilter == null || pick(p) === ansFilter));
    const isSub = Object.keys(flt).length > 0 || ansFilter != null;
    // shares for the current selection: mean of stated spreads
    let share = a.share;
    if (isSub && selPeople.length) {
      share = qq.options.map((_, i) => selPeople.reduce((s, p) => s + p.answers[qq.id][arm].spread[i], 0) / selPeople.length);
    }
    let err = a.error;
    if (isSub) err = { ...err, p50: +(err.p50 * subFactor(selPeople.length)).toFixed(1), p80: +(err.p80 * subFactor(selPeople.length)).toFixed(1), warnings: [...new Set([...(err.warnings || []), "subgroup"])] };
    qCard.innerHTML = "";
    if (res.questions.length > 1) qCard.append(h("div.chips", { style: { marginBottom: "10px" } }, res.questions.map((x, i) =>
      h("button.chip", { class: i === qi ? "on" : null, onclick: () => { qi = i; arm = q().main_arm; ansFilter = null; renderAll(); } }, t("Q{n}", { n: i + 1 })))));
    const arms = Object.keys(qq.arms);
    qCard.append(h("div.eyebrow", `${isSub ? describe(flt) : t("everyone")} · ${num(selPeople.length)} ${t("people")}`), twoTone(arm === "B" && qq.text_b ? qq.text_b : qq.text));
    if (arms.length > 1) qCard.append(h("div.chips", { style: { marginBottom: "10px" } }, arms.map(x => h("button.chip", { class: x === arm ? "on" : null, onclick: () => { arm = x; renderAll(); } }, ARM_LABEL()[x] || x))));
    qCard.append(bars(qq.options, share, err, cols, isSub ? null : qq.human), errorNote(err, isSub ? null : qq.human));
    if (qq.checks?.rare_options?.length) qCard.append(h("div.warn", t("Almost nobody chose: {o}. Real people usually spread out more than simulated ones.", { o: qq.checks.rare_options.map(i => `“${qq.options[i]}”`).join(", ") })));
    if (res.models.length > 1 && a.per_model) {
      qCard.append(h("div", { style: { marginTop: "12px" } }, h("div.eyebrow", t("by model")),
        h("table.t", h("tbody", Object.entries(a.per_model).map(([mref, sh]) => h("tr", h("td.small", (res.models.find(m => m.ref === mref) || {}).name),
          h("td", h("div.bars-mini", sh.map((x, i) => h("i", { style: { width: `${x * 100}%`, background: cols[i] } })))), h("td.num.small", pct(sh[0]))))))));
    }
    // effects
    effectCard.innerHTML = "";
    const ef = qq.effects || {};
    if (st.kind === "treatment" && ef.treatment_vs_placebo) {
      effectCard.append(h("div.card", h("h3", t("Effect of the news")),
        diffBars(qq.options, ef.treatment_vs_placebo, t("treatment minus placebo (the effect)")),
        h("div", { style: { height: "10px" } }), diffBars(qq.options, ef.placebo_vs_control, t("placebo minus control (reaction to any news)")),
        ef.within_shift ? [h("div", { style: { height: "10px" } }), diffBars(qq.options, ef.within_shift, t("same person, after minus before"))] : null,
        h("div.warn", t("Models usually get the direction of an effect right but exaggerate its size. If the placebo moved answers, the model is reacting to being shown anything at all."))));
    } else if (st.kind === "ab" && ef.b_vs_a) {
      effectCard.append(h("div.card", h("h3", t("B versus A")), diffBars(qq.options, ef.b_vs_a, t("half B minus half A")),
        h("div.warn", t("Direction is more reliable than size. No significance test: simulated answers vary less than real ones."))));
    }
    renderExtra();
  }
  const subFactor = n => 1.3 + 0.35 * Math.max(0, Math.log10(Math.max(1000 / Math.max(n, 1), 1)));

  // filters + ask these people
  const askBox = h("div");
  const fe = filterEditor(res.people, f => { flt = f; selection(); renderQ(); renderAsk(); });
  const ansChips = h("div.chips", { style: { marginTop: "10px" } });
  function renderAnsChips() {
    ansChips.innerHTML = "";
    ansChips.append(h("span.small.faint", { style: { alignSelf: "center", marginRight: "4px" } }, t("answered:")),
      ...q().options.map((o, i) => h("button.chip", { class: ansFilter === i ? "on" : null, onclick: () => { ansFilter = ansFilter === i ? null : i; renderAnsChips(); selection(); renderQ(); renderAsk(); } }, o)));
  }
  function renderAsk() {
    const sel = res.people.filter(p => inArm(p) && matches(p, flt) && (ansFilter == null || pick(p) === ansFilter));
    askBox.innerHTML = "";
    askBox.append(h("div.q", { style: { fontSize: "16px", margin: "12px 0 8px" } }, describe(flt), ansFilter != null ? ` · “${q().options[ansFilter]}”` : "", h("span", ` · ${num(sel.length)}`)),
      h("div.row",
        h("button.btn.small", { disabled: !sel.length || null, onclick: () => saveAndAsk(sel, false) }, t("ask them something new")),
        h("button.btn.small.secondary", { disabled: !sel.length || null, onclick: () => saveAndAsk(sel, true) }, t("save as panel")),
        h("a.btn.small.secondary", { href: `#/chats/new?ids=${sel.slice(0, 8).map(p => p.id).join(",")}&study=${st.id}` }, t("focus group"))));
  }
  async function saveAndAsk(sel, onlySave) {
    const name = `${describe(flt)}${ansFilter != null ? ` · ${q().options[ansFilter]}` : ""} (${st.name.slice(0, 40)})`;
    const r = await POST("/api/panels", { name, population_id: st.population_id, person_ids: sel.map(p => p.id) });
    if (onlySave) toast(t("Panel saved: {n} people", { n: r.size })); else location.hash = `#/studies/new?panel=${r.id}`;
  }
  filterCard.append(h("div.eyebrow", t("who to look at")), fe.el, ansChips, askBox);

  // subgroups, anchors, human sample
  function renderExtra() {
    const qq = q(); const cols = palette(qq.options.length);
    extra.innerHTML = "";
    const subs = Object.entries(qq.subgroups || {});
    if (subs.length) {
      let field = subs[0][0];
      const tableBox = h("div");
      const drawTable = () => {
        tableBox.innerHTML = "";
        const rows = qq.subgroups[field];
        tableBox.append(h("table.t", h("thead", h("tr", h("th", L[field] || field), h("th.num", t("people")), qq.options.map((o, i) => h("th.num", h("span", { style: { color: cols[i] } }, "■ "), o)), h("th.num", t("typical error")))),
          h("tbody", rows.map(r => h("tr", h("td", field === "sex" ? SEX(r.value) : r.value), h("td.num", num(r.n)), r.share.map(x => h("td.num", pct(x))), h("td.num.faint", `±${r.error}`))))));
      };
      extra.append(h("div.card", h("div.row", h("h3", t("By group")), h("div.spacer"),
        segmented(null, subs.map(([f]) => [f, L[f] || f]), field, f => { field = f; drawTable(); })),
        h("div.scroll-x", tableBox), h("p.small.muted", t("Simulated groups tend to differ more from each other than real groups do (gaps 2–4× too large in one study). Read differences between groups as direction, not size."))));
      drawTable();
    }
    if (qq.anchors?.length) {
      extra.append(h("div.card", h("h3", t("Closest real polls")), h("p.small.muted", t("Real questions from your downloaded surveys that look most like this one. Compare by eye: they aren't the same question.")),
        qq.anchors.map(a => h("div", { style: { padding: "8px 0", borderTop: "1px solid var(--mist)" } },
          h("div.small", `“${a.text}”`), h("div.mono", `${a.source} ${a.year || ""} · ${a.country || ""} · ${t("similarity")} ${a.similarity}`),
          h("div.bars-mini", { style: { marginTop: "6px", maxWidth: "320px" } }, a.dist.map((x, i) => h("i", { title: `${a.options[i]}: ${pct(x)}`, style: { width: `${x * 100}%`, background: palette(a.options.length, false)[i] } })))))));
    }
    const file = h("input", { type: "file", accept: ".csv,text/csv", onchange: async () => {
      const fd = new FormData(); fd.append("file", file.files[0]);
      try { const r = await api("POST", `/api/studies/${st.id}/human/${qq.id}`, fd); toast(t("{n} real answers added", { n: r.rows }));
        res = await POST(`/api/studies/${st.id}/results`, { lang }); renderAll(); } catch (e) { handle(e); }
    } });
    extra.append(h("div.card", h("h3", t("Correct with real answers")),
      h("p.small.muted", t("Have a small real sample for this question? Upload a CSV with an “answer” column (option text or number) and, if you have them, age, sex, region, education, party. Each real person is paired with the most similar simulated one; the average gap corrects the result, and the bars become a real 95% confidence interval.")),
      qq.human?.error === "too_few" ? h("div.warn", t("Too few usable rows (need at least 10).")) : null,
      qq.human?.share ? h("div.small", t("Using {n} real answers.", { n: qq.human.n })) : null, file));
  }
  function renderAll() { renderAnsChips(); refreshDots(); renderQ(); renderAsk(); }
  renderAll();
}
