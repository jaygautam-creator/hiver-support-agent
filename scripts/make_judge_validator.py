"""
Generates golden/judge_validation.html -- you score replies on the SAME rubric
the LLM judge uses, so the two can be compared.

This is assignment deliverable #3's explicit requirement: "evidence of how well
your judge agrees with a human."

Blinding, which is the whole point:
  * You never see which system wrote the reply (agent / simple / trivial).
  * You never see the LLM judge's scores.
  * Replies are shuffled with a frozen seed.
Without all three, you would be scoring your expectations rather than the text.

Sampling: stratified across the three systems so each gets equal support. If
only the agent's replies were scored, the agreement estimate would only be valid
for text the agent produces -- and the judge's job is to rank systems against
each other.
"""
import json
import random
from pathlib import Path

from src.config import GOLDEN, RESULTS, SEED
from src.judge import RUBRIC

PREDS = RESULTS / "predictions.jsonl"
OUT = GOLDEN / "judge_validation.html"
PER_SYSTEM = 14


def main() -> None:
    if not PREDS.exists():
        raise SystemExit(f"{PREDS} not found -- run `python3 -m src.evaluate` first.")

    rows = [json.loads(l) for l in PREDS.read_text().splitlines()]
    rng = random.Random(SEED)

    picked = []
    for sysname in ("agent", "simple", "trivial"):
        pool = [r for r in rows if r["system"] == sysname]
        picked += rng.sample(pool, min(PER_SYSTEM, len(pool)))
    rng.shuffle(picked)

    items = [{
        "uid": f'{r["pair_id"]}::{r["system"]}',
        "customer_text": r["customer_text"],
        "reply": r["reply"],
        # examples give you the same grounding context the judge had
        "examples": [
            {"c": e["customer_text"], "a": e["brand_reply"]}
            for e in (json.loads(r["retrieved"]) or [])[:3]
        ],
    } for r in picked]

    html = """<!doctype html><html><head><meta charset="utf-8">
<title>Judge validation</title><style>
*{box-sizing:border-box}body{font:15px/1.55 -apple-system,system-ui,sans-serif;margin:0;
background:#f6f6f4;color:#1a1a18}
.wrap{max-width:880px;margin:0 auto;padding:18px}
.bar{position:sticky;top:0;background:#f6f6f4;padding:10px 0;border-bottom:1px solid #ddd;z-index:5}
.prog{height:5px;background:#e3e3df;border-radius:3px;overflow:hidden}
.prog>div{height:100%;background:#2f6f4f;width:0%;transition:width .2s}
.meta{display:flex;gap:14px;font-size:12px;color:#666;margin-top:7px}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:15px;margin:12px 0}
.card h4{margin:0 0 7px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#888}
.cust{font-size:17px}
.rep{font-size:16px;background:#f3f7f4;border-left:3px solid #2f6f4f;padding:11px 13px;border-radius:5px}
details{margin:10px 0;font-size:13px}
details pre{white-space:pre-wrap;font-family:inherit;color:#555;background:#fffdf5;
border:1px solid #e8ddb5;border-radius:6px;padding:10px}
h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#777;margin:15px 0 6px}
.row{display:grid;grid-template-columns:120px 1fr;gap:9px;align-items:center;margin-bottom:7px}
.row .lbl{font-size:13px;font-weight:600}
.btns{display:flex;gap:6px}
.btns button{flex:1;padding:9px;border:1px solid #ccc;background:#fff;border-radius:6px;
cursor:pointer;font:inherit}
.btns button.sel{background:#2f6f4f;color:#fff;border-color:#2f6f4f}
.safe button.sel{background:#a5432f;border-color:#a5432f}
.nav{display:flex;gap:8px;margin:18px 0}
.nav button{font:inherit;padding:9px 15px;border:1px solid #ccc;background:#fff;
border-radius:6px;cursor:pointer}
.exp{background:#1a1a18!important;color:#fff!important;border-color:#1a1a18!important}
.hint{font-size:12px;color:#888;margin-left:auto;align-self:center}
</style></head><body><div class="wrap">
<div class="bar"><div class="prog"><div id="pbar"></div></div>
<div class="meta"><span id="pos"></span><span id="cnt"></span>
<span class="hint">G/A/T rows: keys 1-3 &middot; S toggles safety &middot; Enter next</span></div></div>
<div class="card"><h4>Customer message</h4><div class="cust" id="cust"></div></div>
<div class="card"><h4>Reply to score</h4><div class="rep" id="rep"></div></div>
<details><summary>How Apple handled similar messages (same context the judge saw)</summary>
<pre id="ex"></pre></details>
<details><summary>Rubric anchors</summary><pre>__RUBRIC__</pre></details>
<h3>Groundedness</h3><div class="btns" id="g"></div>
<h3>Action</h3><div class="btns" id="a"></div>
<h3>Tone</h3><div class="btns" id="t"></div>
<h3>Safety violation</h3><div class="btns safe" id="s"></div>
<div class="nav"><button id="prev">&larr;</button><button id="next">&rarr;</button>
<button id="exp" class="exp">Export human_judge.jsonl</button><span class="hint" id="stat"></span></div>
</div><script>
const ITEMS=__ITEMS__, KEY='judge_human_v1';
let S=JSON.parse(localStorage.getItem(KEY)||'{}'), i=0;
const $=id=>document.getElementById(id);
function rec(){const u=ITEMS[i].uid; return S[u]=S[u]||{};}
function render(){
  const it=ITEMS[i], r=rec();
  $('cust').textContent=it.customer_text; $('rep').textContent=it.reply;
  $('ex').textContent=it.examples.map(e=>`CUSTOMER: ${e.c}\\nAPPLE: ${e.a}`).join('\\n\\n')||'(none)';
  $('pos').textContent=`${i+1} / ${ITEMS.length}`;
  const done=Object.values(S).filter(x=>x.g&&x.a&&x.t&&x.s!==undefined).length;
  $('cnt').textContent=`${done} scored`;
  $('pbar').style.width=(100*done/ITEMS.length)+'%';
  for(const f of ['g','a','t'])
    $(f).innerHTML=[1,2,3].map(v=>
      `<button data-f="${f}" data-v="${v}" class="${r[f]===v?'sel':''}">${v}</button>`).join('');
  $('s').innerHTML=[['false','No'],['true','Yes - unsafe']].map(([v,l])=>
    `<button data-f="s" data-v="${v}" class="${String(r.s)===v?'sel':''}">${l}</button>`).join('');
}
function set(f,v){const r=rec(); r[f]=(f==='s')?(v==='true'):+v;
  localStorage.setItem(KEY,JSON.stringify(S)); render();}
function go(d){i=Math.max(0,Math.min(ITEMS.length-1,i+d)); render();}
document.addEventListener('click',e=>{const b=e.target.closest('button'); if(!b)return;
  if(b.dataset.f)set(b.dataset.f,b.dataset.v);
  else if(b.id==='prev')go(-1); else if(b.id==='next')go(1); else if(b.id==='exp')exp();});
document.addEventListener('keydown',e=>{
  const r=rec(); const k=e.key.toLowerCase();
  if(k>='1'&&k<='3'){ const f=!r.g?'g':(!r.a?'a':'t'); set(f,k); }
  else if(k==='s')set('s',String(!r.s));
  else if(e.key==='Enter'){e.preventDefault();go(1);}
  else if(e.key==='ArrowRight')go(1); else if(e.key==='ArrowLeft')go(-1);});
function exp(){
  const out=ITEMS.map(it=>{const r=S[it.uid]||{};
    return JSON.stringify({uid:it.uid,h_groundedness:r.g??null,h_action:r.a??null,
      h_tone:r.t??null,h_safety:r.s??null});}).join('\\n');
  const b=new Blob([out+'\\n'],{type:'application/x-ndjson'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(b);
  a.download='human_judge.jsonl'; a.click();
  $('stat').textContent='exported';
}
render();
</script></body></html>"""

    html = (html.replace("__ITEMS__", json.dumps(items, ensure_ascii=False))
                .replace("__RUBRIC__", RUBRIC.strip()))
    OUT.write_text(html)
    print(f"Wrote {OUT}  ({len(items)} replies, {PER_SYSTEM} per system, system hidden)")


if __name__ == "__main__":
    main()
