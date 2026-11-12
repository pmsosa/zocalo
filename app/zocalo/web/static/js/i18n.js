// Translations: strings are written in English in the code; other languages map English → translation.
// Missing entries fall back to English. `{name}` placeholders are filled from `vars`.
let dict = {};
export let lang = "en";

export async function loadLang(l) {
  lang = l === "es" ? "es" : "en";
  document.documentElement.lang = lang;
  dict = {};
  if (lang !== "en") {
    try { dict = await (await fetch(`/static/i18n/${lang}.json`, { cache: "no-cache" })).json(); } catch (e) { dict = {}; }
  }
}

export function t(s, vars) {
  let out = (lang !== "en" && dict[s]) || s;
  if (vars) for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(v);
  return out;
}
