// Tests golden/label.html -- the labelling tool that produces the golden set.
//
// This is tested because the tool has already put two defects INTO the data:
//
//   1. Round 1's rule-seeded "verify" mode anchored the labeller by +62pp, and
//      158 labels had to be thrown away (results/anchoring.md).
//   2. Confirm was not gated on completeness, so three items entered the golden
//      set with an intent but no decision. They are still there, carried as
//      intent-only rows by src/evaluate.py's `decision_complete` flag.
//
// A labelling tool is measurement apparatus. A silent bug in it does not crash
// anything -- it quietly changes what the golden set means, and every number in
// the report inherits the damage. So the state machine is exercised directly.
//
// Run: make test-labeller
//
// The DOM is shimmed rather than using jsdom: these assertions are about the
// state machine (rec / set / confirm_ / exp), not about layout or styling.

import fs from 'fs';
const html = fs.readFileSync(process.argv[2] || new URL("../golden/label.html", import.meta.url), "utf8");
const js = html.slice(html.indexOf('<script>') + 8, html.lastIndexOf('</script>'));

const els = {};
const mk = () => ({ textContent:'', innerHTML:'', style:{}, dataset:{},
                    addEventListener(){}, appendChild(){}, click(){} });
const store = {};
globalThis.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k,v) => { store[k] = v; },
};
globalThis.document = {
  getElementById: id => (els[id] ||= mk()),
  createElement: () => ({ ...mk(), set href(v){}, set download(v){} }),
  addEventListener(){},
};
globalThis.URL = { createObjectURL: () => 'blob:x' };
globalThis.Blob = class { constructor(parts){ globalThis.__EXPORT__ = parts[0]; } };

const mod = new Function(js + `
  ; return {get i(){return i}, set i(v){i=v}, ITEMS, S, rec, set:set, confirm_, exp, go, render};
`);
const api = mod();
export {};
globalThis.__api = api;
globalThis.__els = els;
globalThis.__store = store;

// ---- assertions ----
let fails = 0;
const ok = (name, cond, extra='') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);
  if (!cond) fails++;
};

ok('158 items loaded', api.ITEMS.length === 158, `got ${api.ITEMS.length}`);
ok('all blind', api.ITEMS.every(i => i.mode === 'blind'));
ok('no pre_* in data', !api.ITEMS.some(i => Object.keys(i).some(k => k.startsWith('pre_'))));

// A fresh record must be EMPTY -- the anchoring fix.
const r0 = api.rec();
ok('fresh record is empty (no seeding)',
   Object.keys(r0).length === 0, JSON.stringify(r0));

// Confirm must refuse while incomplete, at every partial stage.
api.confirm_();
ok('confirm blocked with nothing set', api.rec().confirmed !== true);
ok('  and says what is missing', /still need/.test(__els.stat.textContent),
   JSON.stringify(__els.stat.textContent));

api.set('intent', 'software_bug');
api.confirm_();
ok('confirm blocked with intent only', api.rec().confirmed !== true);

api.set('decision', 'auto');
api.confirm_();
ok('confirm blocked without reason', api.rec().confirmed !== true);

api.set('reason', 'A1');
const before = api.i;
api.confirm_();
ok('confirm accepted when complete', api.ITEMS[before].pair_id in api.S &&
   api.S[api.ITEMS[before].pair_id].confirmed === true);
ok('advances to next item', api.i === before + 1);

// Changing decision must clear the now-mismatched reason code.
api.set('decision', 'escalate');
api.set('reason', 'E3');
api.set('decision', 'auto');
ok('changing decision clears reason', api.rec().reason === null,
   JSON.stringify(api.rec().reason));

// Export shape.
api.exp();
const lines = globalThis.__EXPORT__.trim().split('\n').map(JSON.parse);
ok('export has 158 rows', lines.length === 158);
ok('export never marks was_seeded', lines.every(r => r.was_seeded === false));
ok('export carries no pre_* fields',
   !lines.some(r => Object.keys(r).some(k => k.startsWith('pre_'))));
// Only item 0 ever got an intent; item 1 got a decision but no intent.
ok('untouched rows export as null', lines.filter(r => r.intent === null).length === 157,
   `${lines.filter(r => r.intent === null).length} null`);
ok('partial row exports decision without intent',
   lines[1].intent === null && lines[1].decision === 'auto');

// Storage key must be the fresh one.
ok('writes to golden_labels_v3', 'golden_labels_v3' in __store,
   Object.keys(__store).join(','));

console.log(fails ? `\n${fails} FAILURE(S)` : '\nall checks passed');
process.exit(fails ? 1 : 0);
