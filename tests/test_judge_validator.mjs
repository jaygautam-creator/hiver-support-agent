// Tests golden/judge_validation.html -- the blind reply-scoring tool whose
// export becomes the human side of the judge agreement study.
//
// It exists because the first version had a silent wrong-field write: the
// keyboard handler picked its target field by looking for the first UNSET one,
// so once an item was fully scored, every number key wrote to TONE. Trying to
// correct groundedness changed tone instead, with nothing on screen to say so.
// Scoring is done by keyboard, so that bug would have corrupted the agreement
// data in a way no later check could detect.
//
// Run: make test-judge-validator

import fs from 'fs';
const html = fs.readFileSync(
  process.argv[2] || new URL('../golden/judge_validation.html', import.meta.url), 'utf8');
const js = html.slice(html.indexOf('<script>') + 8, html.lastIndexOf('</script>'));

const els = {};
const mk = () => ({ textContent:'', innerHTML:'', style:{}, dataset:{},
                    addEventListener(){}, click(){} });
const store = {};
globalThis.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k,v) => { store[k] = v; },
};
const handlers = {};
globalThis.document = {
  getElementById: id => (els[id] ||= mk()),
  createElement: () => ({ ...mk(), set href(v){}, set download(v){} }),
  addEventListener: (ev, fn) => { handlers[ev] = fn; },
};
globalThis.URL = { createObjectURL: () => 'blob:x' };
globalThis.Blob = class { constructor(p){ globalThis.__EXPORT__ = p[0]; } };

const api = new Function(js + `
  ; return {ITEMS, S, rec, set:set, go, exp, render,
            get F(){return F}, set F(v){F=v}, firstUnset};
`)();

let fails = 0;
const ok = (n, c, x='') => { console.log(`${c?'PASS':'FAIL'}  ${n}${x?'  '+x:''}`);
                             if (!c) fails++; };
const key = k => handlers.keydown({ key: k, preventDefault(){} });

ok('42 replies loaded', api.ITEMS.length === 42, `got ${api.ITEMS.length}`);
ok('system is hidden from the scorer',
   !api.ITEMS.some(it => 'system' in it), Object.keys(api.ITEMS[0]).join(','));

// Score an item fully by keyboard: 1 -> groundedness, 2 -> action, 3 -> tone.
key('1'); key('2'); key('3');
let r = api.rec();
ok('keyboard fills g, a, t in order',
   r.g === 1 && r.a === 2 && r.t === 3, JSON.stringify(r));

// THE REGRESSION. With everything set, a number key must not silently hit tone.
const toneBefore = r.t;
api.F = 'g';
key('2');
r = api.rec();
ok('correcting groundedness does NOT overwrite tone',
   r.g === 2 && r.t === toneBefore, `g=${r.g} t=${r.t} (tone was ${toneBefore})`);

// Explicit field selection.
key('a'); key('3');
r = api.rec();
ok('A selects action, then a number scores it', r.a === 3, JSON.stringify(r));
key('t'); key('1');
ok('T selects tone, then a number scores it', api.rec().t === 1);

// Safety toggles independently of the score cursor.
const tBefore = api.rec().t;
key('s');
ok('S flags safety', api.rec().s === true);
ok('  and does not disturb the scores', api.rec().t === tBefore);
key('s');
ok('S toggles back', api.rec().s === false);

// Moving to a fresh item resets the cursor to the first unscored field.
api.go(1);
ok('cursor resets on a new item', api.F === 'g', `F=${api.F}`);
ok('new item starts unscored', Object.keys(api.rec()).length === 0);

// Export shape.
api.exp();
const lines = globalThis.__EXPORT__.trim().split('\n').map(JSON.parse);
ok('export has 42 rows', lines.length === 42);
ok('export keys match judge_agreement.py',
   ['uid','h_groundedness','h_action','h_tone','h_safety']
     .every(k => k in lines[0]), Object.keys(lines[0]).join(','));
ok('unscored rows export as null',
   lines[2].h_groundedness === null && lines[2].h_tone === null);
ok('uid carries pair_id::system for the join',
   /::(agent|simple|trivial)$/.test(lines[0].uid), lines[0].uid);
ok('writes to judge_human_v2', 'judge_human_v2' in store, Object.keys(store).join(','));

console.log(fails ? `\n${fails} FAILURE(S)` : '\nall checks passed');
process.exit(fails ? 1 : 0);
