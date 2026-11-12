// Pieces shared by several views: result bars with labelled error, the "How was this made?" card,
// the person card shown on hover, and the filter editor.
import { t } from "../i18n.js";
import { h, palette, swatch, pct, money, num, when } from "../ui.js";

export const FIELD_LABEL = () => ({ age_band: t("Age"), sex: t("Sex"), region: t("Region"), education: t("Education"),
  party: t("Party"), urban: t("Lives in"), religion: t("Religion"), race: t("Race/ethnicity"), country: t("Country"),
  income: t("Income"), employment: t("Work"), occupation: t("Occupation"), vote_last: t("Last vote"), ideology: t("Political views") });
export const SEX = v => v === "female" ? t("Woman") : v === "male" ? t("Man") : v;
export const ageBand = a => a == null ? null : a < 30 ? "18–29" : a < 45 ? "30–44" : a < 65 ? "45–64" : "65+";
export const AGE_ORDER = ["18–29", "30–44", "45–64", "65+"];

const WARN = {
  subgroup: () => t("Subgroup: simulated subgroups tend to look more alike, and more stereotyped, than real ones. Treat as directional."),
  knowledge: () => t("Knowledge question: models answer these far too well (often 40+ points too high on “have you heard of…”)."),
  non_us: () => t("Outside the US: published tests are almost all US-based, so the error here is a wider guess until you test it."),
  demo: () => t("Demo population: made-up people, not census records. For trying the app only."),
};

export function errorNote(err, human) {
  if (human && human.share) {
    const ci = Math.max(...human.ci95);
    return h("div.errnote", h("b", t("95% confidence interval: ±{x} pts", { x: ci.toFixed(1) })),
      h("span.mono", t("human-calibrated · corrected with {n} real answers", { n: human.n })));
  }
  if (!err) return h("div");
  const kind = { measured: t("measured in your tests"), prior: t("estimate from published evaluations, not yet tested here"),
    flat: t("flat estimate · not specific to this question") }[err.kind];
  return h("div.errnote",
    err.kind === "flat"
      ? [h("b", t("Flat error: about ±{a} pts", { a: err.p50 })), h("span", t("No tested question type matches this one well, so this is the overall error: 1 in 5 times more than ±{b} pts.", { b: err.p80 }))]
      : [h("b", t("Usually within ±{a} pts", { a: err.p50 })), h("span", t("1 in 5 times more than ±{b} pts", { b: err.p80 }))],
    h("span.mono", `${kind} · ${err.basis}`),
    (err.warnings || []).map(w => WARN[w] ? h("div.warn", WARN[w]()) : null));
}

export function bars(options, share, err, cols, human) {
  const whisk = human?.share ? null : err?.p50;
  const vals = human?.share || share;
  return h("div.res", options.map((o, i) => {
    const v = (vals[i] || 0) * 100;
    const e = human?.share ? human.ci95[i] : whisk;
    const lo = Math.max(0, v - (e || 0)), hi = Math.min(100, v + (e || 0));
    return h("div.r", h("span.lab", o), h("div.track", h("div.fill", { style: { width: `${v}%`, background: cols[i] } }),
      e ? h("div.whisk", { style: { left: `${lo}%`, width: `${hi - lo}%` } }) : null), h("span.val", `${Math.round(v)}%`));
  }));
}

export function diffBars(options, diff, label) {
  return h("div", h("div.eyebrow", label), h("div.res", options.map((o, i) => {
    const v = (diff[i] || 0) * 100;
    return h("div.r", h("span.lab", o), h("div.track", h("div.fill", { style: { left: v < 0 ? `${50 + v / 2}%` : "50%", width: `${Math.abs(v) / 2}%`, background: v < 0 ? "var(--bad)" : "var(--blue)" } }),
      h("div", { style: { position: "absolute", left: "50%", top: "-3px", bottom: "-3px", borderLeft: "1px solid var(--slate)" } })),
      h("span.val.effect", `${v > 0 ? "+" : ""}${v.toFixed(1)}`));
  })));
}

export function personTip(p, q) {
  const f = p.f || {};
  const box = h("div",
    h("div.n", p.name),
    h("div.m", [f.age, f.occupation || f.employment, [f.region, f.country].filter(Boolean).join(", ")].filter(Boolean).join(" · ")),
    h("dl.kv", [["Sex", SEX(f.sex)], ["Education", f.education], ["Party", f.party], ["Last vote", f.vote_last]].filter(x => x[1])
      .map(([k, v]) => [h("dt", t(k)), h("dd", v)])));
  if (q) {
    const a = p.answers?.[q.id]; const arm = a && (a[q.arm] || Object.values(a)[0]);
    if (arm) {
      const cols = palette(q.options.length);
      box.append(h("dl.kv", h("dt", t("Answer")), h("dd", h("b", { style: { fontWeight: 500 } }, q.options[arm.pick]))),
        h("div.spreadbar", arm.spread.map((v, i) => h("i", { style: { width: `${v * 100}%`, background: cols[i] } }))),
        h("dl.kv", { style: { color: "var(--iron)" } }, arm.spread.map((v, i) => [h("dt", q.options[i]), h("dd", pct(v))])),
        arm.reason ? h("div.small.muted", { style: { marginTop: "6px" } }, `“${arm.reason}”`) : null);
    }
  }
  box.append(h("div.mono", { style: { marginTop: "8px" } }, t("click to open")));
  return box;
}

export function howMade(res) {
  const s = res.study, cfg = s.config || {};
  const method = cfg.method === "words" ? t("own words, mapped to the options by a separate neutral call")
    : t("each person states a probability for every option; results average those");
  return h("div.card.howmade", h("h3", t("How was this made?")),
    h("dl",
      h("dt", t("People")), h("dd", `${s.population?.name} · ${s.population?.source === "demo" ? t("demo (made-up)") : s.population?.source}`),
      h("dt", t("Models")), h("dd", res.models.map(m => m.name).join(", ") || "—"),
      h("dt", t("Answering")), h("dd", method),
      h("dt", t("Order")), h("dd", t("options shuffled per person (scales flipped), “Not sure” always offered")),
      h("dt", t("Profile")), h("dd", t("facts from the record only; names are not sent")),
      s.kind === "treatment" ? [h("dt", t("Design")), h("dd", t("matched groups: control, treatment, placebo") + (cfg.within ? t(", plus a same-person group") : "") + (cfg.design_informed ? t("; told it's an experiment") : ""))] : null,
      s.kind === "ab" ? [h("dt", t("Design")), h("dd", t("matched halves; half A, half B"))] : null,
      h("dt", t("Cost")), h("dd", `${money(s.cost_actual)} · ${when(s.finished_at || s.created_at)}`)),
    h("p.small", h("a", { href: "#/methodology" }, t("Read the methodology")), " · ", h("a", { href: `/api/studies/${s.id}/export.csv` }, t("Download CSV"))));
}

// ---- filter editor ----
// people: [{f:{...}}]; returns {el, get(), set(filter), onChange}
export function filterEditor(people, onChange, extraChips = []) {
  const F = { age_min: 18, age_max: 99, fields: {} };
  const fieldsShown = ["sex", "region", "party", "education", "country", "urban", "religion", "race"];
  const values = {};
  for (const f of fieldsShown) {
    const c = new Map();
    for (const p of people) { const v = p.f?.[f]; if (v != null && v !== "") c.set(v, (c.get(v) || 0) + 1); }
    if (c.size > 1 && c.size < 80) values[f] = [...c.entries()].sort((a, b) => b[1] - a[1]).map(x => x[0]);
  }
  const L = FIELD_LABEL();
  const selects = {};
  const grid = h("div.fields");
  for (const f of Object.keys(values)) {
    const s = h("select", { onchange: () => { F.fields[f] = s.value ? [s.value] : []; changed(); } },
      h("option", { value: "" }, t("Anyone")), values[f].map(v => h("option", { value: v }, f === "sex" ? SEX(v) : v)));
    selects[f] = s;
    grid.append(h("label.f", L[f] || f, s));
  }
  const amin = h("input", { type: "number", min: 18, max: 99, value: 18, oninput: () => { F.age_min = +amin.value || 18; changed(); } });
  const amax = h("input", { type: "number", min: 18, max: 99, value: 99, oninput: () => { F.age_max = +amax.value || 99; changed(); } });
  grid.append(h("label.f", t("Age"), h("div.row", { style: { flexWrap: "nowrap" } }, amin, t("to"), amax)));
  const chips = h("div.chips");
  const quick = [[t("Everyone"), {}], [t("Women"), { fields: { sex: ["female"] } }], [t("Men under 35"), { fields: { sex: ["male"] }, age_max: 34 }],
    [t("Over 65"), { age_min: 65 }], ...extraChips];
  if (values.party) values.party.slice(0, 2).forEach(v => quick.push([v, { fields: { party: [v] } }]));
  if (values.region) quick.push([values.region[0], { fields: { region: [values.region[0]] } }]);
  quick.forEach(([label, f]) => chips.append(h("button.chip", { onclick: () => set(f) }, label)));
  function set(f) {
    F.age_min = f.age_min ?? 18; F.age_max = f.age_max ?? 99; F.fields = JSON.parse(JSON.stringify(f.fields || {}));
    F.answer = f.answer; amin.value = F.age_min; amax.value = F.age_max;
    for (const [k, s] of Object.entries(selects)) s.value = (F.fields[k] || [])[0] || "";
    changed();
  }
  function changed() { onChange && onChange(get()); }
  function get() {
    const out = {};
    if (F.age_min > 18) out.age_min = F.age_min;
    if (F.age_max < 99) out.age_max = F.age_max;
    const fl = Object.fromEntries(Object.entries(F.fields).filter(([, v]) => v && v.length));
    if (Object.keys(fl).length) out.fields = fl;
    if (F.answer != null) out.answer = F.answer;
    return out;
  }
  return { el: h("div", chips, h("div", { style: { height: "12px" } }), grid), get, set };
}

export function matches(p, flt) {
  const f = p.f || {};
  if (flt.age_min != null && (f.age == null || f.age < flt.age_min)) return false;
  if (flt.age_max != null && (f.age == null || f.age > flt.age_max)) return false;
  for (const [k, vals] of Object.entries(flt.fields || {})) {
    const v = k === "age_band" ? ageBand(f.age) : f[k];
    if (vals.length && !vals.includes(v)) return false;
  }
  return true;
}

export function describe(flt) {
  const bits = [];
  const fl = flt.fields || {};
  if (fl.sex) bits.push(fl.sex[0] === "female" ? t("women") : t("men"));
  if (flt.age_min && flt.age_max) bits.push(t("aged {a}–{b}", { a: flt.age_min, b: flt.age_max }));
  else if (flt.age_min) bits.push(t("{a} and over", { a: flt.age_min }));
  else if (flt.age_max) bits.push(t("under {a}", { a: flt.age_max + 1 }));
  for (const [k, v] of Object.entries(fl)) if (k !== "sex" && v.length) bits.push(`${(FIELD_LABEL()[k] || k).toLowerCase()}: ${v.join(", ")}`);
  if (!bits.length) return t("Everyone");
  const s = bits.join(" · ");
  return s[0].toUpperCase() + s.slice(1);
}

export function legend(el, labels, cols) {
  el.innerHTML = "";
  labels.forEach((l, k) => el.append(h("span", swatch(cols[k], k), l)));
}

export function segmented(label, items, current, onPick) {
  const el = h("div.seg", label ? h("span.t", label) : null);
  for (const [k, text] of items) {
    const b = h("button", { class: k === current ? "on" : null, onclick: () => { el.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); onPick(k); } }, text);
    el.append(b);
  }
  return el;
}

export { num };
