/* booth_2 播放逻辑测试：打桩 DOM / Audio / rAF / setTimeout，
   按 timings 的 cue 时刻逐步驱动 slides.html 的内联 script，
   验证：cue 揭示、CQ04 选中与拦截条、加非洲后重算 5,060、翻页与循环。 */
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "slides.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

// ---- 解析静态结构：每页 data-cue 元素 ----
const pages = [...html.matchAll(/<section class="pg" data-id="(s\d)">([\s\S]*?)<\/section>/g)];
const cuesByPage = {};
for (const m of pages) {
  cuesByPage[m[1]] = [...m[2].matchAll(/data-cue="([^"]+)"/g)].map((x) => x[1]);
}

let fails = 0;
const check = (cond, msg) => {
  console.log((cond ? "  [ok] " : "  [FAIL] ") + msg);
  if (!cond) fails++;
};

// ---- DOM stub ----
function classList(el) {
  return {
    add: (...cs) => cs.forEach((c) => el._cls.add(c)),
    remove: (...cs) => cs.forEach((c) => el._cls.delete(c)),
    toggle: (c, f) => { if (f === undefined) { el._cls.has(c) ? el._cls.delete(c) : el._cls.add(c); } else if (f) el._cls.add(c); else el._cls.delete(c); },
    contains: (c) => el._cls.has(c),
  };
}
function makeEl(id) {
  const el = {
    id, _cls: new Set(), textContent: "", innerHTML: "", value: "",
    style: {}, dataset: {}, children: [], offsetWidth: 0,
    classList: null, scrollIntoView() {}, appendChild(c) { this.children.push(c); },
    querySelector() { return null; }, querySelectorAll() { return []; },
  };
  el.classList = classList(el);
  return el;
}

const ids = {};
const getEl = (id) => (ids[id] = ids[id] || makeEl(id));

// 每页 section stub + 其 data-cue 元素 stub
const pgStubs = Object.keys(cuesByPage).map((pid) => {
  const sec = makeEl("pg-" + pid);
  sec.dataset.id = pid;
  const cueEls = {};
  for (const c of cuesByPage[pid]) {
    const e = makeEl("cue-" + pid + "-" + c);
    e.dataset.cue = c;
    cueEls[c] = e;
  }
  sec._cueEls = cueEls;
  sec.querySelectorAll = (sel) => {
    if (sel === "[data-cue]") return Object.values(cueEls);
    const m = sel.match(/^\[data-cue="([^"]+)"\]$/);
    if (m) return cueEls[m[1]] ? [cueEls[m[1]]] : [];
    return [];
  };
  return sec;
});
const blockEl = makeEl("cq-block");
blockEl.dataset.cue = "block";

const rafQueue = [];
const timeouts = [];
let audioStub = null;

const sandbox = {
  console,
  document: {
    getElementById: getEl,
    querySelector: (sel) => {
      if (sel === "#cap span") return getEl("cap-span");
      if (sel === "#prog i") return getEl("prog-i");
      if (sel === "#dots") return getEl("dots");
      if (sel === "#pg") return getEl("pg");
      if (sel === "#snd-hint") return getEl("snd-hint");
      return getEl("q-" + sel.replace(/\W/g, ""));
    },
    querySelectorAll: (sel) => {
      if (sel === ".pg") return pgStubs;
      if (sel === ".block") return [blockEl];
      const m = sel.match(/^\.block\[data-cue="([^"]+)"\]$/);
      if (m) return m[1] === "block" ? [blockEl] : [];
      return [];
    },
    createElement: () => makeEl("created"),
  },
  window: { addEventListener() {}, innerWidth: 1280, innerHeight: 720 },
  requestAnimationFrame: (cb) => { rafQueue.push(cb); return rafQueue.length; },
  cancelAnimationFrame: () => {},
  setTimeout: (cb, ms) => { timeouts.push({ cb, ms }); return timeouts.length; },
  Audio: function (src) {
    audioStub = {
      src, currentTime: 0, preload: "", onended: null, onerror: null,
      _paused: false,
      play() { this._paused = false; return Promise.resolve(); },
      pause() { this._paused = true; },
    };
    return audioStub;
  },
};
sandbox.window.document = sandbox.document;

console.log("== 执行 slides.html 内联 script ==");
try {
  vm.runInNewContext(script, sandbox, { filename: "slides-inline.js" });
  check(true, "script 执行无异常");
} catch (e) {
  check(false, "script 执行失败：" + e.message);
  process.exit(1);
}

// ---- 驱动：步进到指定时刻 ----
let now = 0;
function seek(t) {
  now = t;
  audioStub.currentTime = t;
  const q = rafQueue.splice(0);
  for (const cb of q) cb(now * 1000);
}
function flushTimeouts() {
  const due = timeouts.splice(0);
  for (const { cb } of due) cb();
}
const page = () => pgStubs.find((p) => p._cls.has("on"));
const curId = () => { const p = page(); return p ? p.dataset.id : null; };

// ---- 从 slides.html 内联 timings 取 cue 时刻与时长（TTS 波动后无需改测试）----
const T = JSON.parse(html.match(/const T = (\{[\s\S]*?\});\r?\nconst pgs/)[1]);
const cue = (sid, k) => T.slides.find((s) => s.id === sid).cues[k];
const dur = (sid) => T.slides.find((s) => s.id === sid).duration;

// 初始：go(0) 已同步执行（startAudio 里 play() promise 是微任务，audioOk 稍后才 true）
(async () => {
  await Promise.resolve(); await Promise.resolve(); // 让 go(0) 的 audio.play().then 先跑（audioOk=true）
  console.log("== 初始状态 ==");
  check(curId() === "s1", "初始页 = s1（实际 " + curId() + "）");
  check(getEl("md-pool").textContent === "4,820", "默认企业池 4,820（实际 " + getEl("md-pool").textContent + "）");
  check(getEl("bv-h").textContent === "1,350", "高匹配 1,350（实际 " + getEl("bv-h").textContent + "）");

  console.log("== s1 cue 揭示 ==");
  const s1 = pgStubs[0];
  seek(cue("s1", "pipe") + 0.4);
  check(s1._cueEls.pipe._cls.has("on"), "pipe 揭示");
  seek(cue("s1", "survey") + 0.5);
  check(s1._cueEls.survey._cls.has("on"), "survey 揭示");
  seek(cue("s1", "cards") + 0.5);
  check(s1._cueEls.cards._cls.has("on"), "cards 揭示");

  console.log("== s1 → s2 自动翻页 ==");
  seek(dur("s1") + 0.2);   // s1 口播结束 → finish()
  flushTimeouts();     // 700ms 延翻
  await Promise.resolve(); await Promise.resolve(); // 让 audio.play().then 生效
  check(curId() === "s2", "自动翻到 s2（实际 " + curId() + "）");

  console.log("== s2 cue 与动作 ==");
  const s2 = pgStubs[1];
  seek(cue("s2", "open") + 2);   // open 动作 cue → CQ04 选中（不挂元素）
  check(getEl("cq-detail").innerHTML.includes("运营成本降 30%"), "open 动作：详情面板切到 CQ04");
  seek(cue("s2", "block") + 0.5);
  check(blockEl._cls.has("on"), "红色拦截条弹出");
  console.log("  [debug] s2 cue 状态：" + JSON.stringify(Object.fromEntries(
    Object.entries(s2._cueEls).map(([k, e]) => [k, e._cls.has("on")]))));
  check(s2._cueEls.matrix._cls.has("on"), "matrix cue 揭示");
  check(s2._cueEls.recheck._cls.has("on"), "recheck cue 揭示");

  console.log("== s2 → s3 自动翻页 ==");
  seek(dur("s2") + 0.1);
  flushTimeouts();
  await Promise.resolve(); await Promise.resolve();
  check(curId() === "s3", "自动翻到 s3（实际 " + curId() + "）");

  console.log("== s3 加非洲重算 ==");
  const s3 = pgStubs[2];
  seek(cue("s3", "edit") + 0.5);
  check(getEl("md-region").textContent.includes("非洲"), "目标区域自动加「非洲」：" + getEl("md-region").textContent);
  seek(cue("s3", "rerun") + 0.3);
  check(getEl("md-pool").textContent === "5,060", "重算后企业池 5,060（实际 " + getEl("md-pool").textContent + "）");
  seek(cue("s3", "bars") + 0.2);
  check(s3._cueEls.bars._cls.has("on"), "bars cue 揭示");
  check(s3._cueEls.eval._cls.has("on"), "eval cue 揭示");

  console.log("== s3 → s4 → 回封面（循环） ==");
  seek(dur("s3") + 0.1);
  flushTimeouts();
  await Promise.resolve(); await Promise.resolve();
  check(curId() === "s4", "自动翻到 s4（实际 " + curId() + "）");
  const s4 = pgStubs[3];
  seek(cue("s4", "note") + 1.6);   // 同时越过 s4 结尾触发 finish
  check(s4._cueEls.note._cls.has("on"), "note cue 揭示");
  seek(dur("s4") + 0.1);
  flushTimeouts();
  await Promise.resolve(); await Promise.resolve();
  check(curId() === "s1", "s4 播完回到 s1（循环，实际 " + curId() + "）");
  check(getEl("md-region").textContent.includes("非洲"),
    "回 s1 后区域仍带非洲（重置发生在进入 s3 时，不是回 s1 时）");
  check(getEl("md-pool").textContent === "5,060",
    "回 s1 后企业池保持 s3 结束值 5,060（s1 无企业池显示，实际 " + getEl("md-pool").textContent + "）");

  console.log("== 第二轮：进入 s3 时重置 ==");
  seek(dur("s1") + 0.2); flushTimeouts(); await Promise.resolve(); await Promise.resolve();
  check(curId() === "s2", "第二轮翻到 s2（实际 " + curId() + "）");
  seek(dur("s2") + 0.1); flushTimeouts(); await Promise.resolve(); await Promise.resolve();
  check(curId() === "s3", "第二轮翻到 s3（实际 " + curId() + "）");
  check(getEl("md-region").textContent === "中国华东、华南公交集团、澳洲、东南亚、拉美、中东",
    "进入 s3 时区域重置为默认（实际 " + getEl("md-region").textContent + "）");
  check(getEl("md-pool").textContent === "4,820", "进入 s3 时企业池重置为 4,820（实际 " + getEl("md-pool").textContent + "）");

  console.log();
  if (fails) { console.log(fails + " 项不通过"); process.exit(1); }
  console.log("播放逻辑全部通过 ✅");
})().catch((e) => { console.error("驱动过程异常：", e); process.exit(1); });
