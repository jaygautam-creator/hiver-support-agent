"""
Generates golden/label.html -- a local, keyboard-driven labelling tool.

Design choices that matter for the integrity of the golden set:

  * The brand's historical reply is HIDDEN by default. If you label intent and
    escalation while looking at what Apple actually did, your labels encode
    Apple's behaviour rather than your judgement, and the evaluation quietly
    becomes "does the agent imitate Apple" instead of "is the agent right".
    Revealing is allowed but recorded per item, so its effect is auditable.

  * Escalation reasons are picked from the fixed policy codes in
    src/taxonomy.py, not typed freehand. Free text drifts over 198 items; codes
    make the labels internally consistent and let the report say which policy
    clause drove each escalation.

  * Per-item labelling time is recorded. It is the cheapest available evidence
    that the set was labelled with attention rather than clicked through, and it
    surfaces which items were genuinely hard.

Run, open the file in a browser, label, then click Export.
"""
import json
from pathlib import Path

from src.config import GOLDEN
from src.taxonomy import DISAMBIGUATION_RULES, INTENTS

ITEMS = [json.loads(l) for l in (GOLDEN / "to_label.jsonl").read_text().splitlines()]

# Merge in the rule-based pre-labels and the blind/verify assignment.
_pre = {json.loads(l)["pair_id"]: json.loads(l)
        for l in (GOLDEN / "prelabels.jsonl").read_text().splitlines()}
for _it in ITEMS:
    _it.update({k: v for k, v in _pre[_it["pair_id"]].items() if k != "pair_id"})

# BLIND ITEMS FIRST. If the 40 blind items came after 158 verifications, the
# reviewer would already have absorbed the pre-labeller's habits and the
# anchoring measurement would understate itself. Doing them cold is the point.
ITEMS.sort(key=lambda d: (d["mode"] != "blind",))
OUT = GOLDEN / "label.html"

ESC_CODES = {
    "E1": "Account security / identity",
    "E2": "Money in dispute",
    "E3": "Hardware fault / warranty / repair",
    "E4": "Safety signal (heat, swelling, injury)",
    "E5": "Data loss",
    "E6": "Churn threat / legal / press / abuse",
    "E7": "Unintelligible or low confidence",
}
AUTO_CODES = {
    "A1": "Answerable how-to",
    "A2": "Known bug -> acknowledge + version check",
    "A3": "Post-update -> standard diagnostic",
    "A4": "General feedback, no actionable fault",
}
INTENT_KEYS = list(INTENTS.keys())

html = """<!doctype html><html><head><meta charset="utf-8">
<title>Golden set labeller</title><style>
*{box-sizing:border-box}body{font:15px/1.5 -apple-system,system-ui,sans-serif;margin:0;
background:#f6f6f4;color:#1a1a18}
.wrap{max-width:900px;margin:0 auto;padding:18px}
.bar{position:sticky;top:0;background:#f6f6f4;padding:10px 0;border-bottom:1px solid #ddd;z-index:5}
.prog{height:5px;background:#e3e3df;border-radius:3px;overflow:hidden}
.prog>div{height:100%;background:#2f6f4f;width:0%;transition:width .2s}
.meta{display:flex;gap:14px;font-size:12px;color:#666;margin-top:7px;flex-wrap:wrap}
.msg{background:#fff;border:1px solid #ddd;border-radius:8px;padding:18px;margin:14px 0;
font-size:19px;line-height:1.45}
.tag{display:inline-block;font-size:11px;padding:2px 7px;border-radius:10px;background:#eceae4;
color:#555;margin-right:6px}
h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#777;margin:16px 0 7px}
.opts{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}
button.opt{text-align:left;padding:9px 11px;border:1px solid #ccc;background:#fff;border-radius:6px;
cursor:pointer;font:inherit;font-size:13px}
button.opt:hover{border-color:#2f6f4f;background:#f2f7f4}
button.opt.sel{background:#2f6f4f;color:#fff;border-color:#2f6f4f}
button.opt kbd{display:inline-block;min-width:17px;text-align:center;background:#f0efe9;color:#555;
border-radius:3px;padding:0 4px;margin-right:7px;font-size:11px;font-family:ui-monospace,monospace}
button.opt.sel kbd{background:rgba(255,255,255,.24);color:#fff}
.dec{display:grid;grid-template-columns:1fr 1fr;gap:8px}
button.dec{padding:13px;font-size:15px;font-weight:600;border-radius:6px;border:1px solid #ccc;
background:#fff;cursor:pointer;font-family:inherit}
button.dec.sel[data-v=auto]{background:#2f6f4f;color:#fff;border-color:#2f6f4f}
button.dec.sel[data-v=escalate]{background:#a5432f;color:#fff;border-color:#a5432f}
.rev{margin-top:14px}
.rev button{font:inherit;font-size:12px;padding:6px 11px;border:1px dashed #bbb;background:#fff;
border-radius:6px;cursor:pointer;color:#666}
.reply{margin-top:9px;padding:12px;background:#fffdf5;border:1px solid #e8ddb5;border-radius:7px;
font-size:14px}
.mbadge{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;
padding:4px 9px;border-radius:5px;margin-top:12px}
.mblind{background:#3b2f6b;color:#fff}
.mverify{background:#e8dfc0;color:#6b5a1f}
.rules{margin:12px 0;background:#fffdf5;border:1px solid #e8ddb5;border-radius:7px;padding:9px 12px}
.rules summary{cursor:pointer;font-size:12px;font-weight:600;color:#7a6320}
.rules pre{white-space:pre-wrap;font-size:12px;line-height:1.5;margin:8px 0 0;color:#4a4a44;
font-family:ui-monospace,monospace}
.nav{display:flex;gap:8px;margin:20px 0;align-items:center}
.nav button{font:inherit;padding:9px 15px;border:1px solid #ccc;background:#fff;border-radius:6px;
cursor:pointer}
.exp{background:#1a1a18!important;color:#fff!important;border-color:#1a1a18!important}
.hint{font-size:12px;color:#888;margin-left:auto}
.done{color:#2f6f4f;font-weight:600}
</style></head><body><div class="wrap">
<div class="bar"><div class="prog"><div id="pbar"></div></div>
<div class="meta"><span id="pos"></span><span id="cnt"></span><span id="strat"></span>
<span id="spl"></span><span class="hint">1-8 intent &middot; A/E decision &middot; code &middot; <b>Enter = confirm</b></span></div></div>
<div id="mode"></div><div class="msg" id="msg"></div>
<details class="rules"><summary>Disambiguation rules (click to expand)</summary>
<pre id="rules">__RULES__</pre></details>
<h3>Intent</h3><div class="opts" id="intents"></div>
<h3>Decision</h3><div class="dec">
<button class="dec" data-v="auto" id="bauto">Auto-handle <kbd>A</kbd></button>
<button class="dec" data-v="escalate" id="besc">Escalate <kbd>E</kbd></button></div>
<h3 id="rh">Reason</h3><div class="opts" id="reasons"></div>
<div class="rev"><button id="revbtn">Reveal Apple's actual reply (recorded)</button>
<div class="reply" id="reply" style="display:none"></div></div>
<div class="nav"><button id="prev">&larr; Prev</button>
<button id="acc" style="background:#2f6f4f;color:#fff;border-color:#2f6f4f;font-weight:600">Confirm &crarr;</button>
<button id="next">Next &rarr;</button>
<button id="exp" class="exp">Export labelled.jsonl</button><span class="hint" id="stat"></span></div>
</div><script>
const ITEMS=__ITEMS__, INTENTS=__INTENTS__, ESC=__ESC__, AUTO=__AUTO__;
const KEY='golden_labels_v2';
let S=JSON.parse(localStorage.getItem(KEY)||'{}');
let i=0, t0=Date.now();
const $=id=>document.getElementById(id);
function rec(){ const it=ITEMS[i], p=it.pair_id;
  if(!S[p]){ S[p]={};
    // Verify items arrive pre-filled from the weak rule-based pre-labeller.
    // Blind items arrive empty on purpose.
    if(it.mode==='verify'){S[p].intent=it.pre_intent;S[p].decision=it.pre_decision;
      S[p].reason=it.pre_reason;S[p].seeded=true;}
  }
  return S[p]; }
function render(){
  const it=ITEMS[i], r=rec();
  $('msg').textContent=it.customer_text;
  $('pos').textContent=`${i+1} / ${ITEMS.length}`;
  const done=Object.values(S).filter(x=>x.confirmed&&x.intent&&x.decision&&x.reason).length;
  $('mode').innerHTML = it.mode==='blind'
    ? '<span class="mbadge mblind">BLIND &middot; no pre-label &middot; label from scratch</span>'
    : '<span class="mbadge mverify">VERIFY &middot; pre-filled by rules &middot; correct if wrong</span>';
  $('cnt').innerHTML=`<span class="${done===ITEMS.length?'done':''}">${done} labelled</span>`;
  $('strat').innerHTML=`<span class="tag">${it.slice}</span><span class="tag">${it.stratum}</span>`;
  $('spl').innerHTML=`<span class="tag">${it.split}</span>`;
  $('pbar').style.width=(100*done/ITEMS.length)+'%';
  $('intents').innerHTML=INTENTS.map((n,k)=>
    `<button class="opt ${r.intent===n?'sel':''}" data-i="${n}"><kbd>${k+1}</kbd>${n}</button>`).join('');
  $('bauto').className='dec'+(r.decision==='auto'?' sel':'');
  $('besc').className='dec'+(r.decision==='escalate'?' sel':'');
  const codes=r.decision==='escalate'?ESC:(r.decision==='auto'?AUTO:{});
  $('reasons').innerHTML=Object.entries(codes).map(([c,d])=>
    `<button class="opt ${r.reason===c?'sel':''}" data-r="${c}"><kbd>${c}</kbd>${d}</button>`).join('')
    || '<span style="color:#999;font-size:13px">pick a decision first</span>';
  $('reply').style.display='none'; $('reply').textContent=it.brand_reply;
  $('revbtn').style.display=r.revealed?'none':'inline-block';
  if(r.revealed){$('reply').style.display='block';}
  t0=Date.now();
}
function set(k,v){const r=rec(); const it=ITEMS[i];
  if(it.mode==='verify' && r['pre_'+k]!==undefined){}
  if(v!==r[k]) r.changed=true;
  r[k]=v; if(k==='decision')r.reason=null;
  r.ms=(r.ms||0)+(Date.now()-t0); save(); render();}
function confirm_(){const r=rec(); r.confirmed=true;
  r.ms=(r.ms||0)+(Date.now()-t0); save(); go(1);}
function save(){localStorage.setItem(KEY,JSON.stringify(S));}
function go(d){const r=rec(); r.ms=(r.ms||0)+(Date.now()-t0); save();
  i=Math.max(0,Math.min(ITEMS.length-1,i+d)); render();}
document.addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b)return;
  if(b.dataset.i)set('intent',b.dataset.i);
  else if(b.dataset.r)set('reason',b.dataset.r);
  else if(b.classList.contains('dec'))set('decision',b.dataset.v);
  else if(b.id==='prev')go(-1); else if(b.id==='next')go(1);
  else if(b.id==='acc')confirm_();
  else if(b.id==='revbtn'){rec().revealed=true;save();render();}
  else if(b.id==='exp')exp();
});
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT')return;
  const k=e.key.toLowerCase();
  if(e.key==='Enter'||e.key===' '){e.preventDefault();confirm_();return;}
  if(k>='1'&&k<='8'){const n=INTENTS[+k-1]; if(n)set('intent',n);}
  else if(k==='a')set('decision','auto');
  else if(k==='e')set('decision','escalate');
  else if(e.key==='ArrowRight')go(1);
  else if(e.key==='ArrowLeft')go(-1);
  else{const c=e.key.toUpperCase();
    const r=rec(); const codes=r.decision==='escalate'?ESC:AUTO;
    if(codes[c])set('reason',c);}
});
function exp(){
  const out=ITEMS.map(it=>{const r=S[it.pair_id]||{};
    return JSON.stringify({...it,intent:r.intent||null,decision:r.decision||null,
      reason:r.reason||null,label_ms:r.ms||0,revealed_reply:!!r.revealed,
      confirmed:!!r.confirmed,changed_from_prelabel:!!r.changed,
      was_seeded:!!r.seeded});}).join('\\n');
  const b=new Blob([out+'\\n'],{type:'application/x-ndjson'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(b);
  a.download='labelled.jsonl'; a.click();
  const done=Object.values(S).filter(x=>x.confirmed&&x.intent&&x.decision&&x.reason).length;
  $('mode').innerHTML = it.mode==='blind'
    ? '<span class="mbadge mblind">BLIND &middot; no pre-label &middot; label from scratch</span>'
    : '<span class="mbadge mverify">VERIFY &middot; pre-filled by rules &middot; correct if wrong</span>';
  $('stat').textContent=`exported ${done}/${ITEMS.length} complete`;
}
render();
</script></body></html>"""

html = (html
        .replace("__ITEMS__", json.dumps(ITEMS, ensure_ascii=False))
        .replace("__INTENTS__", json.dumps(INTENT_KEYS))
        .replace("__ESC__", json.dumps(ESC_CODES))
        .replace("__AUTO__", json.dumps(AUTO_CODES))
        .replace("__RULES__", DISAMBIGUATION_RULES.strip()))

OUT.write_text(html)
print(f"Wrote {OUT}  ({len(ITEMS)} items)")
print(f"Open it with:  open {OUT}")
