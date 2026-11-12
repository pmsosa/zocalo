// The population as dots: split into area-scaled clusters (default) or a turning sphere ("explore") where
// answers pop up as speech bubbles. One dot per person; colour (and optionally shape) = category.
import { UI, h, palette, swatch } from "./ui.js";
import { t } from "./i18n.js";

const GA = Math.PI * (3 - Math.sqrt(5));

export function createDots(stage, opts) {
  const cv = h("canvas"); const bubbleLayer = h("div.bubbles");
  stage.prepend(cv); stage.append(bubbleLayer);
  const ctx = cv.getContext("2d");
  const tip = document.getElementById("tip");
  let W = 0, H = 0, people = [], cats = [], cols = [], catOf = () => 0, groupOf = null, groupOrder = null, labelOf = null;
  let layout = opts.layout || "split", selected = () => true, groups = [], tMix = 0, splitGap = 99;
  let rotY = 0, rotX = -0.32, spin = 0.0016, hover = null, drag = null, alive = true, raf = 0, bubbles = [], lastTouch = 0;
  const coarse = matchMedia("(pointer: coarse)").matches;

  function resize() {
    const r = stage.getBoundingClientRect(); const dpr = devicePixelRatio || 1;
    W = r.width; H = r.height; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    computeTargets();
  }
  const ro = new ResizeObserver(resize); ro.observe(stage);

  function setPeople(list) {
    const N = list.length;
    // keep sphere positions stable per id
    const order = list.map((p, i) => i).sort((a, b) => hash(list[a].id) - hash(list[b].id));
    order.forEach((pi, k) => {
      const y = 1 - (k + .5) / Math.max(N, 1) * 2, rad = Math.sqrt(1 - y * y), th = k * GA;
      Object.assign(list[pi], { _sx: Math.cos(th) * rad, _sy: y, _sz: Math.sin(th) * rad });
      list[pi]._x ??= W / 2; list[pi]._y ??= H / 2;
    });
    people = list; computeTargets();
  }
  function setColor(categories, fn) { cats = categories; catOf = fn; cols = palette(cats.length, opts.lastIsUnsure !== false); computeTargets(); }
  function setGroups(fn, ordering, labeller) { groupOf = fn; groupOrder = ordering || null; labelOf = labeller || null; computeTargets(); }
  function setLayout(l) { layout = l; computeTargets(); if (l !== "sphere") clearBubbles(); }
  function setSelected(fn) { selected = fn || (() => true); }
  function refreshPalette() { cols = palette(cats.length, opts.lastIsUnsure !== false); }

  function computeTargets() {
    if (!W || layout === "sphere" || !people.length) return;
    const gf = groupOf || (p => catOf(p));
    const buckets = new Map();
    for (const p of people) { const k = gf(p); if (k == null) continue; if (!buckets.has(k)) buckets.set(k, []); buckets.get(k).push(p); }
    let keys = [...buckets.keys()];
    if (groupOrder) keys.sort((a, b) => groupOrder.indexOf(a) - groupOrder.indexOf(b));
    else keys.sort((a, b) => buckets.get(b).length - buckets.get(a).length);
    if (keys.length > 12) { // fold the long tail into "Other"
      const rest = keys.slice(11).flatMap(k => buckets.get(k)); keys = keys.slice(0, 11); buckets.set("__other", rest); keys.push("__other");
    }
    const max = Math.max(1, ...keys.map(k => buckets.get(k).length));
    const narrow = W < 640;
    const perRow = narrow ? Math.min(keys.length, 2) : Math.min(keys.length, keys.length > 6 ? Math.ceil(keys.length / 2) : keys.length);
    const rows = Math.ceil(keys.length / Math.max(perRow, 1));
    const top = narrow ? 190 : 120, bottom = 70;  // on phones the title and controls sit above the dots
    const slotW = (W - 60) / perRow, slotH = (H - top - bottom) / rows;
    const rMax = Math.max(12, Math.min(slotW * .44, slotH * .36));
    splitGap = .9 * rMax * Math.sqrt(Math.PI / max);
    groups = keys.map((k, gi) => {
      const b = buckets.get(k).slice().sort((a, c) => catOf(a) - catOf(c) || hash(a.id) - hash(c.id));
      const col = gi % perRow, row = Math.floor(gi / perRow);
      const inRow = Math.min(perRow, keys.length - row * perRow);
      const cx = 30 + slotW * (col + .5) + (perRow - inRow) * slotW / 2, cy = top + slotH * (row + .45);
      const R = rMax * Math.sqrt(b.length / max);
      b.forEach((p, i) => { const rr = R * Math.sqrt((i + .5) / b.length), th = i * GA; p._gx = cx + Math.cos(th) * rr; p._gy = cy + Math.sin(th) * rr; });
      return { k, label: k === "__other" ? t("Other") : (labelOf ? labelOf(k) : String(k)), cx, cy, R, people: b };
    });
  }

  function dot(k, x, y, s) {
    if (!UI.shapes || k === 0) { ctx.fillRect(x - s / 2, y - s / 2, s, s); return; }
    ctx.beginPath();
    const m = k % 4;
    if (m === 1) ctx.arc(x, y, s * .58, 0, 7);
    else if (m === 2) { const q = s * .7; ctx.moveTo(x, y - q); ctx.lineTo(x + q, y + q * .8); ctx.lineTo(x - q, y + q * .8); }
    else if (m === 3) { const q = s * .72; ctx.moveTo(x, y - q); ctx.lineTo(x + q, y); ctx.lineTo(x, y + q); ctx.lineTo(x - q, y); }
    else ctx.rect(x - s * .6, y - s * .3, s * 1.2, s * .6);
    ctx.fill();
  }

  function frame() {
    if (!alive) return;
    raf = requestAnimationFrame(frame);
    if (!W) return;
    if (!drag && layout === "sphere" && !hover) rotY += spin;
    tMix += ((layout === "sphere" ? 0 : 1) - tMix) * .08;
    const E = tMix * tMix * (3 - 2 * tMix);
    const R = Math.min(W, H) * .36, cx = W * (W < 640 ? .5 : .56), cy = H * .55, f = 3.2;
    const c1 = Math.cos(rotY), s1 = Math.sin(rotY), c2 = Math.cos(rotX), s2 = Math.sin(rotX);
    ctx.clearRect(0, 0, W, H);
    for (const p of people) {
      const x = p._sx * c1 + p._sz * s1; let z = -p._sx * s1 + p._sz * c1; const y = p._sy;
      const y2 = y * c2 - z * s2; z = y * s2 + z * c2;
      const s = f / (f - z), px = cx + x * R * s, py = cy + y2 * R * s;
      const gx = p._gx ?? px, gy = p._gy ?? py;
      p._x = px + (gx - px) * E; p._y = py + (gy - py) * E; p._z = z * (1 - E) + E;
    }
    const sorted = people.slice().sort((a, b) => a._z - b._z);
    const anySel = people.some(p => !selected(p));
    for (const p of sorted) {
      const depth = (p._z + 1) / 2;
      let a = .18 + depth * .82;
      if (anySel && !selected(p)) a *= .13;
      let size = (1.6 + depth * 1.5) * (UI.big ? 1.7 : 1) * (UI.shapes ? 1.25 : 1);
      // in clusters, dots grow for small groups (up to 7px) but always keep a clear gap
      if (layout !== "sphere") { const fit = Math.min(Math.max(size, splitGap * .36), 7 * (UI.big ? 1.4 : 1), splitGap * (UI.shapes ? .58 : .62)); size += (fit - size) * E; }
      if (p === hover) size *= 2.2;
      ctx.globalAlpha = a;
      const k = catOf(p); ctx.fillStyle = cols[k] ?? "#999";
      dot(k, p._x, p._y, size);
    }
    ctx.globalAlpha = 1;
    for (const b of bubbles) {  // keep bubbles inside the stage
      const half = (b.el.offsetWidth || 200) / 2;
      b.el.style.left = Math.max(half + 6, Math.min(W - half - 6, b.p._x)) + "px"; b.el.style.top = Math.max((b.el.offsetHeight || 60) + 18, b.p._y) + "px";
    }
    if (hover) { ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--ink"); ctx.lineWidth = 1; ctx.strokeRect(hover._x - 5, hover._y - 5, 10, 10); }
    if (tMix > .5 && layout !== "sphere") {
      ctx.globalAlpha = (tMix - .5) * 2;
      const ink = getComputedStyle(document.documentElement).getPropertyValue("--ink");
      const slate = getComputedStyle(document.documentElement).getPropertyValue("--slate");
      const shownTotal = anySel ? people.filter(selected).length : people.length;
      for (const g of groups) {
        const shown = anySel ? g.people.filter(selected).length : g.people.length;
        ctx.textAlign = "center"; ctx.fillStyle = ink; ctx.font = "500 13px Inter, system-ui";
        const ly = g.cy + Math.max(g.R, 14) + 22;
        ctx.fillText(truncate(g.label, 26), g.cx, ly);
        ctx.fillStyle = slate; ctx.font = "400 12px Inter, system-ui";
        const extra = opts.groupNote ? opts.groupNote(g.people.filter(p => !anySel || selected(p))) : "";
        ctx.fillText(shown ? `${shown.toLocaleString()} · ${Math.round(shown / Math.max(shownTotal, 1) * 100)}%${extra ? " · " + extra : ""}` : t("not in this selection"), g.cx, ly + 17);
      }
      ctx.globalAlpha = 1;
    }
  }
  raf = requestAnimationFrame(frame);

  // ---- hover / click / drag ----
  function nearest(mx, my, touch = false) {
    let best = null, bd = touch ? (UI.big ? 28 * 28 : 24 * 24) : (UI.big ? 100 : 64);
    const anySel = people.some(p => !selected(p));
    for (const p of people) {
      if (p._z < -.15 && tMix < .5) continue;
      if (anySel && !selected(p)) continue;
      const d = (p._x - mx) ** 2 + (p._y - my) ** 2;
      if (d < bd) { bd = d; best = p; }
    }
    return best;
  }
  function pos(e) { const r = cv.getBoundingClientRect(); const pt = e.touches ? e.touches[0] : e; return [pt.clientX - r.left, pt.clientY - r.top, pt.clientX, pt.clientY]; }
  function showTip(p, cx, cy, touch = false) {
    if (!opts.tip) return;
    tip.innerHTML = ""; tip.append(opts.tip(p));
    tip.classList.toggle("touch", touch);
    if (touch) {  // a card pinned above the tab bar, with a button instead of a hidden second tap
      tip.style.left = tip.style.top = "";
      if (opts.onClick) tip.append(h("button.btn", { style: { marginTop: "10px", width: "100%", justifyContent: "center" }, onclick: () => { hideTip(); opts.onClick(p); } }, t("Talk to them")));
    } else {
      tip.style.left = Math.min(cx + 16, innerWidth - 280) + "px";
      tip.style.top = Math.min(cy + 16, innerHeight - 260) + "px";
    }
    tip.classList.add("on");
  }
  const hideTip = () => tip.classList.remove("on", "touch");
  cv.addEventListener("mousemove", e => {
    if (Date.now() - lastTouch < 800) return;  // ignore the mouse events browsers fake after a tap
    const [mx, my, cx, cy] = pos(e);
    if (drag) {
      if (layout === "sphere") { rotY += (mx - drag.x) * .006; rotX = Math.max(-1.3, Math.min(1.3, rotX + (my - drag.y) * .006)); }
      drag.moved += Math.abs(mx - drag.x) + Math.abs(my - drag.y); drag.x = mx; drag.y = my; return;
    }
    hover = nearest(mx, my);
    if (hover) showTip(hover, cx, cy); else hideTip();
  });
  cv.addEventListener("mouseleave", () => { hover = null; hideTip(); });
  cv.addEventListener("mousedown", e => { if (Date.now() - lastTouch < 800) return; const [x, y] = pos(e); drag = { x, y, moved: 0 }; cv.classList.add("dragging"); hideTip(); });
  const up = () => { if (Date.now() - lastTouch < 800) return; if (drag && drag.moved < 4 && hover && opts.onClick) opts.onClick(hover); drag = null; cv.classList.remove("dragging"); };
  addEventListener("mouseup", up);
  // touch: a tap shows the person's card (with a "Talk to them" button). Sideways swipes turn the sphere;
  // vertical swipes scroll the page.
  cv.addEventListener("touchstart", e => {
    lastTouch = Date.now();
    const [mx, my] = pos(e);
    drag = { x: mx, y: my, x0: mx, y0: my, moved: 0, p: nearest(mx, my, true), axis: null };
  }, { passive: true });
  cv.addEventListener("touchmove", e => {
    if (!drag) return; const [mx, my] = pos(e);
    if (!drag.axis && Math.abs(mx - drag.x0) + Math.abs(my - drag.y0) > 8) drag.axis = Math.abs(mx - drag.x0) > Math.abs(my - drag.y0) ? "x" : "y";
    if (layout === "sphere" && drag.axis === "x") { rotY += (mx - drag.x) * .008; e.preventDefault(); }
    drag.moved += Math.abs(mx - drag.x) + Math.abs(my - drag.y); drag.x = mx; drag.y = my;
  }, { passive: false });
  cv.addEventListener("touchend", e => {
    lastTouch = Date.now();
    if (drag && drag.moved < 8) {
      e.preventDefault();
      if (drag.p) { hover = drag.p; showTip(hover, 0, 0, true); } else { hover = null; hideTip(); }
    }
    drag = null;
  }, { passive: false });

  // ---- explore: speech bubbles ----
  function clearBubbles() { bubbles.forEach(b => b.el.remove()); bubbles = []; }
  const bubbleTimer = setInterval(() => {
    if (!alive || layout !== "sphere" || tMix > .05 || drag || hover || document.hidden || !opts.quote) return;
    const pool = people.filter(p => p._z > .55 && selected(p) && !bubbles.some(b => b.p === p) && opts.quote(p));
    if (!pool.length) return;
    const p = pool[Math.floor(Math.random() * pool.length)];
    const q = opts.quote(p); const k = catOf(p);
    const el = h("div.bub", `“${q.text}”`, h("em", swatch(cols[k], k, 8), q.who));
    bubbleLayer.append(el);
    const b = { p, el }; bubbles.push(b);
    requestAnimationFrame(() => el.classList.add("on"));
    setTimeout(() => el.classList.remove("on"), 3600);
    setTimeout(() => { el.remove(); bubbles = bubbles.filter(x => x !== b); }, 4000);
  }, 1400);

  function destroy() { alive = false; cancelAnimationFrame(raf); clearInterval(bubbleTimer); ro.disconnect(); removeEventListener("mouseup", up); hideTip(); }
  resize();
  return { setPeople, setColor, setGroups, setLayout, setSelected, refreshPalette, destroy, get layout() { return layout; } };
}

function hash(x) { let h = 2166136261; for (const c of String(x)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
function truncate(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
