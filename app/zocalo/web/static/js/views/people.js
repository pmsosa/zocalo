// People and conversations: the quick drawer, a person's page, interviews, focus groups and debates.
import { t } from "../i18n.js";
import { h, GET, POST, DEL, handle, toast, num, pct, when, confirmBox, palette } from "../ui.js";
import { onCleanup } from "../app.js";
import { SEX, FIELD_LABEL } from "./common.js";

let drawer = null;
async function defaultModel(pref) {
  if (pref) return pref;
  const m = (await GET("/api/models")).models.filter(x => x.enabled);
  return m.length ? String(m[0].id) : null;
}

// ---- drawer: talk to one person without leaving the page ----
export async function openPersonDrawer(pid, ctx = {}) {
  if (drawer) drawer.remove();
  const p = await GET(`/api/people/${pid}`);
  const rec = p.record;
  const msgs = h("div.msgs");
  const input = h("input", { type: "text", placeholder: t("Ask a follow-up…"), autocomplete: "off" });
  let chatId = null;
  const model = await defaultModel(ctx.models?.[0]?.ref);
  const say = (cls, text, who) => { const m = h("div.msg." + cls, who ? h("span.who", who) : null, text); msgs.append(m); msgs.scrollTop = 1e9; return m; };
  if (ctx.question && ctx.answer) {
    say("sys", t("You asked: “{q}”", { q: ctx.question.text }));
    const a = ctx.answer, top = a.spread.indexOf(Math.max(...a.spread));
    say("them", `${a.reason || ctx.question.options[a.pick]}`);
    say("sys", ctx.question.options.map((o, i) => `${o} ${pct(a.spread[i])}`).join(" · "));
  } else say("sys", t("Ask them anything. They answer as this person, from their record only."));
  const send = async e => {
    e.preventDefault();
    const text = input.value.trim(); if (!text) return;
    if (!model) return toast(t("Add a model in Settings first."), true);
    input.value = ""; say("me", text); const typing = say("them", "…");
    try {
      let c;
      if (!chatId) {
        const opening = ctx.question && ctx.answer
          ? `(Earlier you were asked: "${ctx.question.text}" and answered "${ctx.question.options[ctx.answer.pick]}".)\n${text}` : text;
        c = await POST("/api/chats", { kind: "interview", person_ids: [pid], model, study_id: ctx.study?.id, title: ctx.question?.text?.slice(0, 80), opening });
        chatId = c.id;
      } else c = await POST(`/api/chats/${chatId}/say`, { text });
      const last = c.messages.filter(m => m.role === "person").pop();
      typing.textContent = last ? last.content : "";
      const drift = c.messages.filter(m => m.role === "drift").pop();
      if (drift && !drift.meta.consistent) say("sys", t("Drift check: asked again, they answered differently from their record."));
    } catch (err) { typing.remove(); handle(err); }
  };
  drawer = h("aside.drawer",
    h("div.dh", h("div.row", h("div", h("div.name", p.name), h("div.small.muted", [rec.age, rec.occupation || rec.employment, [rec.region, rec.country_name || rec.country].filter(Boolean).join(", ")].filter(Boolean).join(" · "))),
      h("div.spacer"), h("button.x", { "aria-label": t("Close"), onclick: () => close() }, "×")),
      h("div.branchinfo", h("span", t("base record")), " ", h("b", rec.provenance?.ref || `#${p.id}`), ` (${t("unchanged")})`, h("br"),
        t("each conversation runs on its own branch · facts restated every turn"))),
    msgs,
    h("div.row", { style: { padding: "0 18px 10px", gap: "14px" } },
      h("a.ghost.small", { href: `#/people/${pid}`, onclick: () => close() }, t("full profile")),
      h("a.ghost.small", { href: `#/chats/new?ids=${pid}&kind=debate${ctx.study ? "&study=" + ctx.study.id : ""}`, onclick: () => close() }, t("debate someone"))),
    h("form.compose", { onsubmit: send }, input, h("button.btn", t("send"))));
  document.body.append(drawer);
  requestAnimationFrame(() => drawer.classList.add("on"));
  const esc = e => { if (e.key === "Escape") close(); };
  addEventListener("keydown", esc);
  function close() { drawer?.classList.remove("on"); const d = drawer; setTimeout(() => d?.remove(), 300); drawer = null; removeEventListener("keydown", esc); }
  onCleanup(close);
}

// ---- a person's page ----
export async function renderPerson([id], v) {
  const p = await GET(`/api/people/${id}`);
  const rec = p.record, L = FIELD_LABEL();
  v.append(h("div.page-head", h("h1", p.name, h("br"), h("span", p.summary)),
    h("div.actions", h("button.btn", { onclick: () => openPersonDrawer(+id, {}) }, t("talk to them")),
      h("a.btn.secondary", { href: `#/chats/new?ids=${id}&kind=debate` }, t("debate")))));
  const facts = Object.entries({ age: rec.age, sex: SEX(rec.sex), country: rec.country_name || rec.country, region: rec.region, urban: rec.urban,
    education: rec.education, employment: rec.employment, occupation: rec.occupation, income: rec.income, household: rec.household, marital: rec.marital,
    race: rec.race, religion: rec.religion, religiosity: rec.religiosity, party: rec.party, ideology: rec.ideology, vote_last: rec.vote_last }).filter(([, x]) => x != null && x !== "");
  v.append(h("div.grid.cols-2",
    h("div.card", h("h3", t("Record")), h("dl.kv", { style: { gridTemplateColumns: "140px 1fr", fontSize: "13px", gap: "6px 12px" } },
      facts.map(([k, x]) => [h("dt", L[k] || t({ age: "Age", household: "Household", marital: "Marital status", religiosity: "Religious practice" }[k] || k)), h("dd", String(x))])),
      rec.views?.length ? [h("h3", { style: { marginTop: "14px" } }, t("Their own past answers")), h("ul.small", rec.views.map(x => h("li", `${x.q} → `, h("b", { style: { fontWeight: 500 } }, x.a))))] : null,
      h("div.branchinfo", t("Where this comes from: "), rec.provenance?.note || rec.provenance?.source || "—", rec.provenance?.attitudes ? h("div", rec.provenance.attitudes) : null)),
    h("div.grid", { style: { alignContent: "start" } },
      h("div.card", h("h3", t("What the model sees")), h("pre.small", { style: { whiteSpace: "pre-wrap", fontFamily: "var(--mono)", fontSize: "11px", margin: 0, color: "var(--iron)" } }, p.profile_text),
        h("p.small.faint", t("Their name is not sent. Nothing else is added."))),
      p.answers.length ? h("div.card", h("h3", t("Answers in studies")), h("table.t", h("tbody", p.answers.map(a => {
        const opts = JSON.parse(a.options_json), sp = JSON.parse(a.spread_json || "[]"); const k = sp.indexOf(Math.max(...sp));
        return h("tr.click", { onclick: () => location.hash = `#/studies/${a.study_id}` }, h("td.small", a.text), h("td.small", h("b", { style: { fontWeight: 500 } }, opts[k] || ""), a.arm !== "main" ? h("span.faint", ` · ${a.arm}`) : null));
      })))) : null,
      p.chats.length ? h("div.card", h("h3", t("Conversations")), p.chats.map(c => h("div", h("a", { href: `#/chats/${c.id}` }, `${t(c.kind)} · ${c.title || ""}`), h("span.small.faint", " " + when(c.created_at))))) : null,
      p.branches.length ? h("div.card", h("h3", t("Branches")), h("p.small.muted", t("Changes layered on the base record. The base never changes.")),
        h("ul.small", p.branches.slice(-12).map(b => h("li", b.name, h("span.faint", " · " + when(b.created_at)))))) : null)));
}

// ---- conversations list ----
export async function renderChats(_, v) {
  const d = await GET("/api/chats");
  v.append(h("div.page-head", h("h1", t("Conversations"), h("br"), h("span", t("Interviews, focus groups and debates."))),
    h("div.actions", h("a.btn", { href: "#/chats/new?kind=focus" }, t("new focus group")), h("a.btn.secondary", { href: "#/chats/new?kind=debate" }, t("new debate")))));
  if (!d.chats.length) { v.append(h("div.card.empty", h("h2", t("No conversations yet")), h("p", t("Click any person's dot to talk to them, or start a focus group.")))); return; }
  v.append(h("div.card", h("table.t", h("tbody", d.chats.map(c => h("tr.click", { onclick: () => location.hash = `#/chats/${c.id}` },
    h("td", h("span.tag", t(c.kind))), h("td", c.title || "—"), h("td.small.muted", c.people), h("td.num.small", `${c.n} ${t("messages")}`), h("td.small.faint", when(c.created_at))))))));
}

// ---- new focus group / debate ----
export async function renderNewGroup(_, v) {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  let kind = params.get("kind") || "focus";
  const ids = (params.get("ids") || "").split(",").filter(Boolean).map(Number);
  const models = (await GET("/api/models")).models.filter(m => m.enabled);
  const pops = (await GET("/api/populations")).populations;
  if (!models.length) { v.append(h("div.card.empty", h("h2", t("Add a model first")), h("a.ghost", { href: "#/settings" }, t("open settings")))); return; }
  v.append(h("div.page-head", h("h1", kind === "debate" ? t("New debate") : t("New focus group"), h("br"),
    h("span", kind === "debate" ? t("Two people, pinned positions.") : t("A few people, one moderator: you.")))));
  const chosen = [];
  for (const id of ids) { try { chosen.push(await GET(`/api/people/${id}`)); } catch (e) { /* gone */ } }
  const list = h("div.grid");
  const stances = {};
  function drawList() {
    list.innerHTML = "";
    chosen.forEach((p, i) => list.append(h("div.card", h("div.row", h("b", { style: { fontWeight: 500 } }, p.name), h("span.small.muted", p.summary), h("div.spacer"),
      h("button.link.small", { onclick: () => { chosen.splice(i, 1); drawList(); } }, t("remove"))),
      kind === "debate" ? h("label.f", { style: { marginTop: "8px" } }, t("Their position (pinned)"), h("input", { type: "text", value: stances[p.id] || "", placeholder: t("e.g. For a four-day week, even with a pay cut"), oninput: e => stances[p.id] = e.target.value })) : null)));
  }
  drawList();
  const popSel = h("select", pops.map(p => h("option", { value: p.id }, p.name)));
  const addRandom = h("button.btn.secondary.small", { onclick: async () => {
    const d = await GET(`/api/populations/${popSel.value}/people?limit=5000`);
    const pool = d.people.filter(p => !chosen.some(c => c.id === p.id));
    const p = pool[Math.floor(Math.random() * pool.length)];
    if (p) { chosen.push(await GET(`/api/people/${p.id}`)); drawList(); }
  } }, t("add a random person"));
  const modelSel = h("select", models.map(m => h("option", { value: m.id }, `${m.provider_label} · ${m.label}`)));
  const topic = h("textarea", { placeholder: kind === "debate" ? t("The question they debate, e.g. Should cities ban cars downtown?") : t("Your opening question to the group") });
  const rounds = h("input", { type: "number", value: 3, min: 1, max: 8 });
  const go = h("button.btn", { onclick: async () => {
    if (chosen.length < (kind === "debate" ? 2 : 2)) return toast(t("Add at least two people."), true);
    if (!topic.value.trim()) return toast(t("Write the question."), true);
    if (kind === "debate" && chosen.some(p => !stances[p.id])) return toast(t("Give each side a position."), true);
    go.disabled = true; go.textContent = t("starting…");
    try {
      const c = await POST("/api/chats", { kind, person_ids: chosen.map(p => p.id), model: modelSel.value, title: topic.value.trim().slice(0, 100),
        stances, study_id: params.get("study") ? +params.get("study") : null, opening: kind === "focus" ? topic.value.trim() : null });
      if (kind === "debate") { go.textContent = t("debating…"); await POST(`/api/chats/${c.id}/debate`, { question: topic.value.trim(), rounds: +rounds.value || 3 }); }
      location.hash = `#/chats/${c.id}`;
    } catch (e) { handle(e); go.disabled = false; go.textContent = t("start"); }
  } }, t("start"));
  v.append(h("div.grid", { style: { maxWidth: "760px" } },
    h("div.card", h("div.eyebrow", t("people")), list, h("div.row", { style: { marginTop: "10px" } }, popSel, addRandom),
      h("p.small.muted", t("Tip: pick people from a study or the population page (filter, then “focus group”)."))),
    h("div.card", h("div.fields", h("label.f.wide", kind === "debate" ? t("Question") : t("Opening question"), topic), h("label.f", t("Model"), modelSel),
      kind === "debate" ? h("label.f", t("Rounds"), rounds) : null),
      kind === "debate" ? h("p.small.muted", t("Before the debate each side answers alone (a no-discussion branch); afterwards they answer again, so you can see how far each moved. Simulated debates drift into agreement far more than real ones.")) : null),
    h("div.row", { style: { justifyContent: "flex-end" } }, go)));
}

// ---- a conversation ----
export async function renderChat([id], v) {
  let c = await GET(`/api/chats/${id}`);
  const names = Object.fromEntries(c.members.map(m => [m.person_id, m.name]));
  v.append(h("div.page-head", h("h1", c.title || t(c.kind), h("br"), h("span", `${t(c.kind)} · ${c.members.map(m => m.name).join(", ")}`)),
    h("div.actions", h("button.btn.secondary", { onclick: async () => { try { c = await POST(`/api/chats/${id}/drift`); draw(); } catch (e) { handle(e); } } }, t("drift check")),
      h("button.btn.danger", { onclick: async () => { if (await confirmBox(t("Delete this conversation?"), "", t("delete"))) { await DEL(`/api/chats/${id}`); location.hash = "#/chats"; } } }, t("delete")))));
  const msgs = h("div.msgs", { style: { maxHeight: "none", padding: "16px 4px" } });
  const deb = h("div");
  const input = h("input", { type: "text", placeholder: c.kind === "debate" ? t("Ask the debaters something…") : t("Say something to the group…"), autocomplete: "off" });
  function draw() {
    msgs.innerHTML = "";
    for (const m of c.messages) {
      if (m.role === "user") msgs.append(h("div.msg.me", m.content));
      else if (m.role === "person") msgs.append(h("div.msg.them", h("span.who", names[m.person_id] + (m.meta.round ? ` · ${t("round")} ${m.meta.round}` : m.meta.final ? ` · ${t("final answer")}` : "")), m.content));
      else if (m.role === "drift") msgs.append(h("div.msg.sys", `${t("Drift check")} · ${names[m.person_id]}: ${m.meta.consistent ? t("consistent with their record") : t("differs from their record")} — ${m.content}`));
    }
    deb.innerHTML = "";
    if (c.config.debate) {
      deb.append(h("div.card", h("h3", t("Did anyone move?")), h("table.t", h("thead", h("tr", h("th", ""), h("th", t("Before (alone)")), h("th", t("After the debate")))),
        h("tbody", c.members.map(m => h("tr", h("td", h("b", { style: { fontWeight: 500 } }, m.name), m.stance ? h("div.small.faint", m.stance) : null),
          h("td.small", c.config.debate.before[m.person_id] || ""), h("td.small", c.config.debate.after[m.person_id] || ""))))),
        h("div.warn", t("Simulated groups reach full agreement far more often than real people (85–96% vs 51% in one study). Don't read a consensus here as a forecast."))));
    }
  }
  draw();
  const form = h("form.compose", { style: { borderTop: "0", padding: "0" }, onsubmit: async e => {
    e.preventDefault(); const text = input.value.trim(); if (!text) return;
    input.value = ""; input.disabled = true; msgs.append(h("div.msg.me", text), h("div.msg.them", "…"));
    try { c = await POST(`/api/chats/${id}/say`, { text }); draw(); } catch (err) { handle(err); draw(); }
    input.disabled = false; input.focus();
  } }, input, h("button.btn", t("send")));
  v.append(h("div.grid", { style: { maxWidth: "860px" } }, deb, h("div.card", msgs, form)));
}
