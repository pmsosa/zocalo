// New study: who to ask, what to ask, which models, then a cost estimate before anything runs.
import { t, lang } from "../i18n.js";
import { h, GET, POST, handle, toast, num } from "../ui.js";
import { filterEditor, describe, matches, segmented } from "./common.js";

const TEMPLATES = () => [
  [t("Yes / No"), [t("Yes"), t("No")], false],
  [t("Agree (5)"), [t("Strongly agree"), t("Somewhat agree"), t("Neither agree nor disagree"), t("Somewhat disagree"), t("Strongly disagree")], true],
  [t("Likely (4)"), [t("Very likely"), t("Somewhat likely"), t("Not very likely"), t("Not at all likely")], true],
  [t("Approve (4)"), [t("Strongly approve"), t("Somewhat approve"), t("Somewhat disapprove"), t("Strongly disapprove")], true],
];
const QTYPES = () => [["opinion", t("Opinion")], ["behaviour", t("Behaviour")], ["consumer", t("Consumer / price")], ["knowledge", t("Knowledge")], ["other", t("Other")]];

export async function render(_, v) {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const [pops, models, panels] = await Promise.all([GET("/api/populations"), GET("/api/models"), GET("/api/panels")]);
  const enabled = models.models.filter(m => m.enabled);
  v.append(h("div.page-head", h("h1", t("New study"), h("br"), h("span", t("Who, what, and with which models.")))));
  if (!pops.populations.length || !enabled.length) {
    v.append(h("div.card.empty", h("h2", t("Two things first")),
      h("p", !enabled.length ? h("a", { href: "#/settings" }, t("Add a model in Settings.")) : null, " ",
        !pops.populations.length ? h("a", { href: "#/population" }, t("Build a population.")) : null)));
    return;
  }
  const S = { kind: "survey", population_id: +(params.get("population") || pops.populations[0].id), panel_id: params.get("panel") ? +params.get("panel") : null,
    filter: {}, size: null, models: [String(enabled[0].id)], method: "spread", questions: [], config: {} };
  if (S.panel_id) { const pn = panels.panels.find(p => p.id === S.panel_id); if (pn) S.population_id = pn.population_id; }

  // ---- 1. kind + name
  const name = h("input", { type: "text", placeholder: t("Name this study (optional)") });
  const kindHelp = h("p.small.muted");
  const kinds = segmented(null, [["survey", t("Survey")], ["ab", t("A/B test")], ["treatment", t("News test")]], S.kind, k => { S.kind = k; renderKind(); renderQuestions(); });
  const kindExtra = h("div");
  function renderKind() {
    kindHelp.textContent = { survey: t("Everyone answers every question. Answers never see each other."),
      ab: t("The panel is split into matched halves. Half A sees version A of each question, half B sees version B."),
      treatment: t("Matched thirds: no news, the news, and a placebo (neutral news). The effect is treatment minus placebo, never the raw change.") }[S.kind];
    kindExtra.innerHTML = "";
    if (S.kind === "treatment") {
      const tr = h("textarea", { placeholder: t("The news or information to show, e.g. “The company's CEO said prices will rise next year.”"), oninput: () => S.config.treatment = tr.value });
      const pl = h("textarea", { placeholder: t("Placebo: neutral news of similar length, e.g. “The company moved its head office to a new building.”"), oninput: () => S.config.placebo = pl.value });
      const within = h("input", { type: "checkbox", onchange: () => S.config.within = within.checked });
      const di = h("input", { type: "checkbox", onchange: () => S.config.design_informed = di.checked });
      kindExtra.append(h("div.grid", { style: { marginTop: "10px" } }, h("label.f", t("Treatment (the news)"), tr), h("label.f", t("Placebo (neutral news)"), pl),
        h("label.tog", within, h("span", t("Also run a same-person group"), h("small", t("A further matched group answers, reads the news, then answers again in the same conversation. The gap from the between-group result shows how much asking twice exaggerates the effect.")))),
        h("label.tog", di, h("span", t("Tell the model it's an experiment"), h("small", t("Some studies found this reduces over-reaction. Leave off to compare.")))))));
    }
    if (S.kind === "ab") {
      const a = h("textarea", { placeholder: t("Optional: something half A reads first (e.g. ad copy A)"), oninput: () => S.config.stimulus_a = a.value });
      const b = h("textarea", { placeholder: t("Optional: something half B reads first (e.g. ad copy B)"), oninput: () => S.config.stimulus_b = b.value });
      kindExtra.append(h("div.fields", { style: { marginTop: "10px" } }, h("label.f", t("Shown to half A"), a), h("label.f", t("Shown to half B"), b)));
    }
  }

  // ---- 2. who
  const popSel = h("select", { onchange: () => { S.population_id = +popSel.value; S.panel_id = null; panelSel.value = ""; loadPeople(); } },
    pops.populations.map(p => h("option", { value: p.id, selected: p.id === S.population_id }, `${p.name} · ${num(p.size)}${p.source === "demo" ? " · " + t("demo") : ""}`)));
  const panelSel = h("select", { onchange: () => { S.panel_id = panelSel.value ? +panelSel.value : null; const pn = panels.panels.find(p => p.id === S.panel_id); if (pn) { S.population_id = pn.population_id; popSel.value = pn.population_id; } loadPeople(); } },
    h("option", { value: "" }, t("No saved panel")), panels.panels.map(p => h("option", { value: p.id, selected: p.id === S.panel_id }, `${p.name} · ${num(p.size)}`)));
  const sizeIn = h("input", { type: "number", min: 10, placeholder: t("everyone who matches"), oninput: () => { S.size = +sizeIn.value || null; updateWho(); } });
  const whoLine = h("div.q", { style: { fontSize: "18px", margin: "12px 0 0" } });
  const bigWarn = h("div.warn.hidden");
  const filterBox = h("div");
  let people = [], fe = null;
  async function loadPeople() {
    const d = await GET(`/api/populations/${S.population_id}/people`);
    people = d.people;
    if (S.panel_id) { const pn = panels.panels.find(p => p.id === S.panel_id); }
    fe = filterEditor(people, f => { S.filter = f; updateWho(); });
    filterBox.innerHTML = ""; filterBox.append(S.panel_id ? h("p.small.muted", t("Using the saved panel; filters below narrow it further.")) : null, fe.el);
    updateWho();
  }
  function updateWho() {
    const n = people.filter(p => matches(p, S.filter)).length;
    const k = S.size ? Math.min(S.size, n) : n;
    whoLine.innerHTML = ""; whoLine.append(describe(S.filter), h("span", ` · ${num(k)} ${t("people")}`));
    bigWarn.classList.toggle("hidden", k <= 10000);
    bigWarn.textContent = t("Over 10,000 people: this may cost a lot. Check the estimate before running.");
  }

  // ---- 3. questions
  const qBox = h("div.grid");
  function addQuestion(text = "", options = [t("Yes"), t("No")], ordered = false) {
    S.questions.push({ text, options, ordered, qtype: null, topical: false, text_b: "" });
    renderQuestions();
  }
  function renderQuestions() {
    qBox.innerHTML = "";
    S.questions.forEach((q, i) => {
      const txt = h("textarea", { rows: 2, placeholder: t("Would you pay $10 a month for an AI assistant?"), value: q.text,
        oninput: async () => { q.text = txt.value; guessType(); } });
      const opts = h("textarea", { rows: 4, value: q.options.join("\n"), oninput: () => q.options = opts.value.split("\n") });
      const type = h("select", { onchange: () => q.qtype = type.value }, QTYPES().map(([k, l]) => h("option", { value: k }, l)));
      const anchors = h("div.small.faint");
      let gt = 0;
      async function guessType() {
        clearTimeout(gt);
        gt = setTimeout(async () => {
          if (!q.text.trim()) return;
          const g = await GET(`/api/errors/guess?text=${encodeURIComponent(q.text)}`);
          if (!q.qtype) type.value = g.qtype;
          anchors.textContent = g.anchors.length ? t("Closest real poll: “{q}” ({s} {y})", { q: g.anchors[0].text.slice(0, 90), s: g.anchors[0].source, y: g.anchors[0].year || "" }) : "";
        }, 400);
      }
      if (q.qtype) type.value = q.qtype; else if (q.text) guessType();
      const top = h("input", { type: "checkbox", checked: q.topical, onchange: () => q.topical = top.checked });
      const ord = h("input", { type: "checkbox", checked: q.ordered, onchange: () => q.ordered = ord.checked });
      const tb = S.kind === "ab" ? h("label.f.wide", t("Version B of the question (leave empty to use the same text)"),
        h("textarea", { rows: 2, value: q.text_b, oninput: e => q.text_b = e.target.value })) : null;
      qBox.append(h("div.card",
        h("div.row", h("div.eyebrow", t("Question {n}", { n: i + 1 })), h("div.spacer"),
          S.questions.length > 1 ? h("button.link.small", { onclick: () => { S.questions.splice(i, 1); renderQuestions(); } }, t("remove")) : null),
        h("div.fields", h("label.f.wide", t("Question"), txt), tb,
          h("label.f", t("Options, one per line (“Not sure” is added for you)"), opts,
            h("div.chips", { style: { marginTop: "6px" } }, TEMPLATES().map(([l, o, od]) => h("button.chip", { onclick: () => { q.options = o; q.ordered = od; renderQuestions(); } }, l)))),
          h("div.grid", { style: { gap: "4px", alignContent: "start" } },
            h("label.f", t("Question type (sets the error estimate)"), type),
            h("label.tog", top, h("span", t("About recent news"), h("small", t("Topical questions are less accurate.")))),
            h("label.tog", ord, h("span", t("Options are a scale"), h("small", t("Scales are flipped, not shuffled.")))), anchors))));
    });
    qBox.append(h("button.btn.secondary", { onclick: () => addQuestion() }, t("+ add a question")));
  }

  // ---- 4. models
  const modelBox = h("div");
  enabled.forEach(m => {
    const cb = h("input", { type: "checkbox", checked: S.models.includes(String(m.id)), onchange: () => {
      S.models = cb.checked ? [...new Set([...S.models, String(m.id)])] : S.models.filter(x => x !== String(m.id)); } });
    modelBox.append(h("label.tog", cb, h("span", `${m.provider_label} · ${m.label}`,
      h("small", m.price_in == null ? t("price unknown: set it in Settings for a real estimate") : t("${a} in · ${b} out per million tokens", { a: m.price_in, b: m.price_out })))));
  });
  const method = segmented(t("answers"), [["spread", t("stated probabilities")], ["words", t("own words → options")]], S.method, k => S.method = k);

  // ---- submit
  const go = h("button.btn", { onclick: submit }, t("check the cost"));
  async function submit() {
    const qs = S.questions.filter(q => q.text.trim()).map(q => ({ ...q, options: q.options.map(o => o.trim()).filter(Boolean) }));
    if (!qs.length) return toast(t("Write at least one question."), true);
    if (qs.some(q => q.options.length < 2)) return toast(t("Every question needs at least two options."), true);
    if (!S.models.length) return toast(t("Choose at least one model."), true);
    if (S.kind === "treatment" && (!S.config.treatment || !S.config.placebo)) return toast(t("A news test needs both the news and a placebo."), true);
    go.disabled = true;
    try {
      const r = await POST("/api/studies", { name: name.value.trim() || qs[0].text.slice(0, 60), kind: S.kind, population_id: S.population_id,
        panel_id: S.panel_id, filter: S.filter, lang, questions: qs, config: { ...S.config, models: S.models, method: S.method, size: S.size } });
      location.hash = `#/studies/${r.id}`;
    } catch (e) { handle(e); go.disabled = false; }
  }

  v.append(h("div.grid", { style: { maxWidth: "980px" } },
    h("div.card", h("div.eyebrow", t("1 · kind")), h("div.row", kinds, h("div.spacer")), kindHelp, name, kindExtra),
    h("div.card", h("div.eyebrow", t("2 · who to ask")), h("div.fields", h("label.f", t("Population"), popSel), h("label.f", t("Saved panel"), panelSel)),
      h("div", { style: { height: "12px" } }), filterBox, h("label.f", { style: { marginTop: "10px", maxWidth: "260px" } }, t("How many (random sample)"), sizeIn), whoLine, bigWarn),
    h("div", h("div.eyebrow", { style: { margin: "4px 2px 8px" } }, t("3 · what to ask")), qBox),
    h("div.card", h("div.eyebrow", t("4 · models")), modelBox, h("div", { style: { marginTop: "10px" } }, method),
      h("p.small.muted", t("More than one model? Each person is asked by each model, and results show them together and separately."))),
    h("div.row", { style: { justifyContent: "flex-end" } }, go)));
  renderKind();
  const preQ = params.get("q");
  addQuestion(preQ || "", [t("Yes"), t("No")]);
  await loadPeople();
}
