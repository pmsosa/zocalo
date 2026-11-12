// Home: the list of studies, and a three-step start for a fresh install.
import { t } from "../i18n.js";
import { h, GET, money, when, statusTag, progressBar } from "../ui.js";
import { onCleanup } from "../app.js";

export async function render(_, v) {
  const [st, models, pops] = await Promise.all([GET("/api/studies"), GET("/api/models"), GET("/api/populations")]);
  const hasModel = models.models.some(m => m.enabled), hasPop = pops.populations.length > 0;
  v.append(h("div.page-head",
    h("h1", t("Ask anyone."), h("br"), h("span", t("The public square, simulated."))),
    h("div.actions", h("a.btn", { href: "#/studies/new" }, t("new study")))));
  if (!hasModel || !hasPop || !st.studies.length) {
    const step = (n, done, title, text, href, cta) => h("div.card", { style: { opacity: done ? .62 : 1 } },
      h("div.eyebrow", done ? t("step {n} · done", { n }) : t("step {n}", { n })), h("h3", title), h("p.muted.small", text),
      done ? null : h("a.ghost", { href }, cta));
    v.append(h("div.grid.cols-3", { style: { marginBottom: "18px" } },
      step(1, hasModel, t("Add a model"), t("Paste an API key for Gemini, Anthropic, OpenAI or any OpenAI-compatible server. Zócalo checks it and lists the models."), "#/settings", t("open settings")),
      step(2, hasPop, t("Build a population"), t("Start with a demo population of made-up people, or build a real one from census and survey data."), "#/population", t("build one")),
      step(3, st.studies.length > 0, t("Ask a question"), t("Pick who to ask, write the question, see the cost, run it. Every result shows how far off it may be."), "#/studies/new", t("new study"))));
  }
  if (!st.studies.length) return;
  const tbl = h("table.t", h("thead", h("tr", [["Study"], ["Question", "hide-phone"], ["People"], ["Status"], ["Cost", "hide-phone"], ["Created", "hide-phone"]].map(([x, c]) => h("th", { class: c }, t(x))))));
  const tb = h("tbody");
  for (const s of st.studies) {
    tb.append(h("tr.click", { onclick: () => location.hash = `#/studies/${s.id}` },
      h("td", h("b", { style: { fontWeight: 500 } }, s.name), h("div.small.faint", t(kindLabel(s.kind)))),
      h("td.hide-phone", h("span.muted", s.first_question || ""), s.n_questions > 1 ? h("span.faint", ` +${s.n_questions - 1}`) : null),
      h("td.small", s.population, s.source === "demo" ? h("span.faint", ` · ${t("demo")}`) : null),
      h("td", statusTag(s.status), s.status === "running" ? progressBar(s.progress) : null),
      h("td.num.hide-phone", money(s.cost_actual || s.cost_estimate)), h("td.small.faint.hide-phone", when(s.created_at))));
  }
  tbl.append(tb);
  v.append(h("div.card", h("div.scroll-x", tbl)));
  if (st.studies.some(s => s.status === "running")) {
    const timer = setTimeout(() => { if (location.hash === "" || location.hash === "#/") dispatchEvent(new HashChangeEvent("hashchange")); }, 3000);
    onCleanup(() => clearTimeout(timer));
  }
}

export const kindLabel = k => ({ survey: "Survey", ab: "A/B test", treatment: "News test (with placebo)" })[k] || k;
