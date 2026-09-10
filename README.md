# AppleSupport first-response agent

An AI triage agent for **@AppleSupport** built from the Kaggle *Customer Support
on Twitter* corpus. For each incoming customer message it produces three things:

1. an **intent**, from a 7-class taxonomy derived from the data;
2. a **reply**, grounded in how Apple has historically answered similar messages;
3. an **auto-handle / escalate decision**, citing a specific policy clause.

The evaluation is the point of this repo, so it is documented before the system.

---

## Reproduce the headline results

```bash
pip install -r requirements.txt          # pinned
cp .env.example .env                     # add a free Google AI Studio key
make repro                               # ~60s, offline, from the committed cache
```

`make repro` sets `CACHE_OFFLINE=1`, so every LLM response is replayed from the
committed content-addressed cache and **a cache miss is a hard error**. That is
deliberate: it proves the numbers in `results/` came from the committed cache and
not from a re-run that happened to land differently.

To re-issue every call against the live API instead: `make repro-live`.

Rebuilding from the raw 2.8M-row dump (not required — the subsample is
committed):

```bash
./scripts/download_data.sh               # needs a Kaggle token
make survey                              # per-brand stats -> results/brand_survey.md
python3 -m src.data --brand AppleSupport # -> data/brand_subsample.parquet
```

---

## Where this falls short of the brief

Two deliverables are not met. Both are stated here, measured where they can be
measured, and expanded in full in § *The two open gaps* — nothing below is
softened to compensate.

| Brief asks for | This repo has | Effect |
|---|---|---|
| 150–250 hand-labelled examples | **40** | Every interval is roughly twice as wide as it should be; 2 of 7 intents have zero examples and are unmeasured |
| Evidence the LLM judge agrees with a human | **No human study.** 4 automated checks instead | Reply-quality *rankings* are unsupported; safety and groundedness *floors* are supported |

A third, independent measurement partly covers the second gap without closing
it: an annotator model of a different family relabelled the golden set from the
same written rules, which is a test of whether the *taxonomy* is reproducible
rather than whether the *judge* is right. It found the escalation codebook was
unreproducible (kappa 0.08, chance), the codebook was rewritten, and the rerun
reached kappa 0.77 — § *Is the taxonomy reproducible?*

The short version of how the golden set ended at 40: 198 items were sampled, a
rule-based pre-labeller was used to seed a faster verification pass, and **40
items were held back to be labelled blind as a control**. The control fired —
the pre-labeller was 32% accurate on the blind items but 95% of its labels were
accepted during verification, a **+62 point anchoring effect** at identical
labelling speed. The 158 verified labels were discarded and only the 40 blind
ones survive. Both gaps are fully tooled and are one working session from
closing; the tooling and its own bugs are documented in § *The two open gaps*.

---

## Problem framing

### What "good" means for AppleSupport

Measured, not assumed. Across every candidate brand, **first replies on Twitter
are triage, not resolution** — 75% of Apple's replies point at a resource, and
about half hand off to DM (`results/brand_deflection.md`). An agent scored on
"did it solve the problem" would be measuring something this channel never does.

So "good" is defined as:

| Property | Why it is the right target |
|---|---|
| **Correct triage** | Acknowledge, ask the one diagnostic question Apple actually asks, or route. |
| **High escalation recall** | Costs are asymmetric. Wrongly auto-handling a locked-out or injured customer loses them; wrongly escalating an easy one costs an agent two minutes. Recall on `escalate` is the metric that matters, not accuracy. |
| **Groundedness** | Replies must reflect Apple's historical behaviour, not invented support advice. Made objective: cleaning replaced every real URL with `<url>`, so any `http` link in a reply is provably fabricated. |
| **A citable reason** | Every decision names a policy clause (E1–E6 / A1, A2, A4, A5), so a human reviewer can audit *why*, not just *what*. The clause list is one string in `src/taxonomy.py`, injected into the agent prompt, the labelling UI and the second annotator alike. |

### Brand selection

Chosen by measurement, not volume. Candidates were ranked on inbound volume,
reply ratio, and a measured DM-deflection rate, then six random real replies per
finalist were read before committing. AppleSupport won on intent separability
and having a real historical-resolution pattern to ground in.

That process also caught a bug in my own metric: the deflection regex counted
only DM-style handoffs, so AmazonHelp scored 0.7% while its replies actually say
*"we can't access accounts on Twitter, please call us"*. The published table
keeps the original numbers with the caveat attached rather than being quietly
re-scored.

### What I chose **not** to build

- **Multi-turn conversation state.** 27.6% of inbound messages are mid-thread
  replies to Apple's own question (*"Yes it's updated to that one yesterday"*)
  with no standalone intent. Scoped out; `is_opener` keeps it reversible.
- **Embedding-based retrieval.** TF-IDF word + char n-grams instead. 73k
  documents through a free-tier embedding API is hours of rate-limited calls for
  a component the assignment is not testing, and char n-grams handle this
  corpus's misspellings well.
- **A confidence-calibrated escalation threshold.** The agent emits a decision,
  not a probability, so there is no operating curve to tune. This is the first
  thing I would add (§ *One more week*).
- **Fine-tuning.** 40 labels.
- **A UI, streaming, or an agent framework.** Nothing in the brief asks for
  them, and each is surface area to defend in review.

---

## Taxonomy

7 intents, derived from the data and then twice revised **by evidence**:

`software_bug` · `how_to` · `account_access` · `hardware_or_repair` ·
`billing_or_purchase` · `feedback_or_complaint` · `other`

Derivation: TF-IDF + KMeans over 4,000 openers (`results/taxonomy_derivation.md`),
read by hand. Clusters were a reading aid, not the answer — they split by
vocabulary, not intent: clusters 6, 10 and 12 were all the same iOS 11 autocorrect
bug in different phrasings, and 0, 5, 7 and 13 were all post-update degradation.

**Two revisions, both forced by data:**

- *After the 20-item pilot:* the same bug was labelled `software_bug`, `how_to`
  and `other` in one sitting, and five items got an intent contradicting their own
  reason code. Three prose definitions were replaced with mechanical tests
  (`DISAMBIGUATION_RULES`).
- *After blind labelling:* `post_update_degradation` was used **0 times in 40**
  against an expected ~15%. The class was merged into `software_bug`. Merging a
  class to raise a score would be indefensible; merging one that a careful human
  provably never uses is not.

---

## Results

Full tables with confidence intervals: `results/main_table.md`.

**Headline: the agent escalates 27% of messages against the human's 30%, with
precision 0.80 and 3 of 11 escalations missed.** Every caveat that number
deserves is in the next section, and the escalation figures moved a lot in the
last revision — § *Rewriting the escalation codebook*.

### Intent (n=40, macro-F1 over the 5 observed classes)

| System | Accuracy [95% CI] | Macro-F1 [95% CI] |
|---|---|---|
| **agent** | **0.60 [0.45, 0.75]** | **0.53 [0.34, 0.66]** |
| simple (TF-IDF + LogReg, out-of-fold CV) | 0.50 [0.35, 0.65] | 0.24 [0.12, 0.35] |
| trivial (majority class) | 0.48 [0.33, 0.62] | 0.13 [0.10, 0.15] |

On the natural slice (n=24, true prevalence) the agent scores 0.71 accuracy
against the trivial baseline's 0.67 — **statistically indistinguishable**, with
intervals overlapping almost entirely. On macro-F1 the intervals do not overlap
(0.58 [0.32, 0.72] vs 0.20 [0.16, 0.23]). That gap between the two metrics is the
single most important thing in this report: **accuracy here mostly measures the
class prior.**

### Escalation (n=37 with decision labels, 11 gold escalations)

| System | Precision | Recall [95% CI] | Missed escalations | Reason-code accuracy |
|---|---|---|---|---|
| **agent** | **0.80** | **0.73 [0.45, 1.00]** | **3** | **0.60** |
| simple | 0.00 | 0.00 | 11 | 0.00 |
| trivial | 0.00 | 0.00 | 11 | 0.14 |

Both baselines escalate **nothing**. The trivial one by construction; the simple
one because a logistic regression on ~30 imbalanced training labels collapses to
the majority class. This is where the LLM earns its place — not in
classification, where a simple model is competitive, but in recognising that a
locked-out or injured customer needs a human.

**All three missed escalations, in full:**

| Message | Gold | Agent said |
|---|---|---|
| *"help i forgot my restrictions passcode"* | `account_access` / E1 | `how_to` / auto / A1 |
| *"apenas compré el #Iphone8 ... Fraude"* | `account_access` / E2 | `software_bug` / auto / A2 |
| *"While updating to high Sierra we lost the Boot sector. How to repair that?"* | `hardware_or_repair` / E3 | `software_bug` / auto / A2 |

The first is a genuine and serious miss — a credential reset auto-handled, which
is exactly the case E1 exists for. The other two are contested labels rather
than clean failures: on both, the independent second annotator disagreed with the
human gold label too (it called the second `hardware_or_repair`/E3 and the third
`software_bug`/E5). Counting them as agent errors is the conservative reading,
and that is how they are counted above.

### Rewriting the escalation codebook, and what it cost

The escalation policy is prose in `src/taxonomy.py` that is injected verbatim
into the agent prompt, the labelling UI, and the second annotator. Version 1 was
measured and **failed**: an independent annotator reading the same text agreed
with the human at Cohen's kappa **0.08** — chance — and escalated 82% of messages
against the human's 28%. Reading it explains why. `E7` ended *"...or the agent's
own confidence is low"*, so a careful reader reached for it whenever unsure;
`E6` fired on *"severe dissatisfaction or sustained abuse"* across a corpus of
angry, profane tweets; and the auto side had no criteria at all, only
"AUTO-HANDLE otherwise". Seven ways out and no way to stay.

v2 deletes E7, replaces E6 with a mechanical test (a **named outside party** —
lawyer, regulator, press, chargeback — never tone or profanity), gives every
auto case a positive code including a new `A5` for messages with no recoverable
request, and states an application order with no "unsure" branch. Codes the
human actually used (A2, A4, E1, E2, E3) keep their exact meanings, so round-1
labels stay comparable — which is why there is a gap at A3 rather than a tidy
renumber. Full proposal: `golden/CODEBOOK_V2_PROPOSAL.md`.

**Same 40 labels, same model, only the policy text changed:**

| | v1 | v2 |
|---|---|---|
| Agent escalation rate | 43% | **27%** *(human gold: 30%)* |
| Escalate precision | 0.63 | **0.80** |
| Escalate recall | 0.91 | **0.73** |
| Missed escalations | 1 | **3** |
| Reason-code accuracy | 0.27 | **0.60** |
| Intent macro-F1 | 0.56 | 0.53 |
| Judge mean, agent replies | 2.98 | 2.80 |

Three things worth reading carefully here.

**The escalate-bias was in the policy text, not the model.** Under v1 the agent
escalated 43% against the human's 30%, drifting the same direction the second
annotator did — because it was reading the same escalate-biased document. Under
v2 it escalates 27%. Nothing about the model changed. That is the cleanest
evidence in this report that a prompt-resident *policy* is a component you can
get wrong and measure, not a detail.

**The reason-code gain is mostly mechanical, and saying so matters.**
Accuracy went 0.27 → 0.60: 13 items became correct and 1 became wrong. But **9
of those 13** come from retiring `A3` alone — a code the human used zero times
and the agent used twelve. Only 4 of the 13 come from the rewritten criteria.
The headline improvement is real but it is largely the removal of a wrong
option, not the model reasoning better.

**Recall got worse, and that is the metric this report says matters most.**
0.91 → 0.73, one miss becoming three. The honest reading is that v1's recall was
partly purchased by a policy that told everyone to escalate when unsure: at a 43%
escalation rate you catch more true escalations because you catch more of
everything. v2 trades 2 misses for 6 fewer false escalations and a reason code
that is right twice as often. Whether that trade is correct is a business call
about the cost ratio, not something this evaluation can settle — and with a
recall CI of [0.45, 1.00] at n=11, it cannot settle it either way.

### Does retrieval actually do anything? (ablation)

The brief asks for replies "grounded in how that brand has historically resolved
similar issues", and this repo answers that with a 73k-document TF-IDF index. It
is the single most expensive component here and nothing had ever tested whether
removing it changes anything. `results/ablation_retrieval.md`: same agent, same
prompt, same model, same 40 items, **k=0** — no examples, taxonomy and policy
only. Three predictions were written into `scripts/ablate_retrieval.py` before
the run. **All three failed.**

| Metric | k=5 (shipped) | k=0 (no retrieval) | Δ |
|---|---|---|---|
| Intent macro-F1 | 0.53 | 0.56 | +0.03 |
| Escalate precision | 0.80 | 0.83 | +0.03 |
| **Escalate recall** | **0.73** | **0.91** | **+0.18** |
| Missed escalations | 3 | 1 | −2 |
| Reason-code accuracy | 0.60 | 0.62 | +0.03 |
| Judge groundedness | 2.75 | 2.70 | −0.05 |
| Fabricated URLs | 0% | 0% | 0pp |

**Removing the grounding component improved every headline metric, and the one
metric it exists to protect did not move.**

The honest size of that: the recall delta is +0.182, 95% CI [+0.00, +0.45] by
paired bootstrap over 11 gold escalations — it does not cross zero, but its lower
bound *is* zero and the entire effect is **two items**. Two items is not a
result. It is a signal.

**It points at a mechanism the report had only asserted.** Failure mode 3 says:
*Apple publishes an article for this, the retrieved examples show Apple linking
it, so the agent grounds correctly and escalates wrongly — grounding and policy
conflict, and grounding wins.* Removing the examples is what that hypothesis
predicts, and the two recovered escalations are exactly its shape. This is the
first evidence for it rather than a story about it.

**Two things this also settles.** The 0% fabricated-URL rate survives k=0
intact, so that discipline comes from the prompt's explicit "never write a URL"
instruction, not from the grounding — the report previously implied the examples
were what kept it honest, and that was wrong. And retrieval was *suppressing the
customer's language*: on a Spanish message, k=5 replied in English because every
retrieved example was English, while k=0 replied in Spanish.

**The shipped default stays k=5, and the reason matters.** k=0 wins on these 40
items, which is exactly why it is not being adopted. This is the evaluation set,
its errors have already been read, and switching architecture to whatever scores
best on 40 already-inspected examples is the same error as tuning a threshold on
the test set — the one this report spends a section warning about. Adopting it
needs the finished 150-item set, the recall CI clear of zero, and a groundedness
check that does not depend on a judge measured at 67% test-retest stability.

### Is the taxonomy reproducible? (second annotator)

This is the measurement that forced the codebook rewrite above, so it is
reported in full rather than summarised.

An independent model — `gemma-4-31b-it`, a **different family** from both the
agent and the judge — relabelled all 40 golden items from **exactly what the
human labeller saw**: same definitions, same disambiguation rules, same policy
codes, Apple's reply withheld, no retrieved examples, no reply to draft. It is
doing the labelling task, not the agent's.

**This is not the human agreement study the brief asks for** — that gap is still
open (§ *Where this falls short*). Two readers of the same definitions can agree
and both be wrong, so nothing here shows the labels are *correct*. What it
measures is whether the written taxonomy is **reproducible**.

**Codebook v1** (`results/second_annotator_v1.md`):

| Field | Agreement | Cohen's kappa |
|---|---|---|
| intent (7 classes) | 62% | 0.47 |
| escalate / auto | 41% | **0.08** |
| policy reason code | 24% | — |

On the escalation half the answer was no: **kappa 0.08 is chance.** And the
disagreement was one-directional, which is what made it diagnostic rather than
just noisy — 22 items the human marked `auto` the annotator marked `escalate`,
and only 1 went the other way:

| | escalation rate under v1 |
|---|---|
| human (gold) | 28% |
| agent | 43% |
| second annotator | 82% |

<sub>Agent and human rates are over the 37 items carrying a decision label — the
same denominator every escalation metric in this report uses. Over all 40 rows
the v1 agent rate is 42.5%; the two figures are the same measurement on
different denominators.</sub>

Its two most-used codes were **E7** (11 uses) and **E6** (8) — **19 of the 24
disagreements, and codes the human used zero times in 40 items.** That is not a
tendency inside the disagreement; it is the whole of it. Reading the two clauses
literally explains the effect, and the rewrite in the section above follows
directly from them.

**Codebook v2, same 40 items, same annotator model, pre-registered.** The
prediction written down before the run was kappa 0.7–0.8
(`golden/CODEBOOK_V2_PROPOSAL.md` § 2, from a paper projection of 0.76):

| Field | v1 agreement | v1 kappa | v2 agreement | v2 kappa |
|---|---|---|---|---|
| intent (7 classes) | 62% | 0.47 | 60% | 0.43 |
| escalate / auto | 41% | **0.08** | **90%** | **0.77** |
| policy reason code | 24% | — | **62%** | — |

**Escalate/auto went from chance to substantial agreement, and the intent
definitions were the control.** Nothing about the intent taxonomy changed between
these two runs, and its kappa moved 0.47 → 0.43 — so roughly ±0.04 is this
measurement's own noise floor, and the escalation move of +0.69 is nowhere near
it. The annotator's escalation rate fell from 82% to 38% against the human's 28%,
and E7 and E6 — 19 of the 24 v1 disagreements between them — are now used **zero
times**, because one no longer exists and the other requires a named outside
party. The four remaining disagreements are all E3/E2 boundary calls on specific
messages, which is an ordinary labelling dispute rather than a broken rule.

**What this does and does not license.** It says the escalation policy is now
*reproducible*: two independent readers of the same document reach substantially
the same decisions. It says nothing about whether those decisions are *right* —
that still needs a human, and both raters here could be wrong together. It is
also, unavoidably, somewhat in-sample: v2 was written after seeing which codes
the human had used, so it encodes their revealed restraint and fits the round-1
labels partly by construction. The honest test is items labelled *after* the
codebook was frozen — the remaining 158 — and that test has not been run.

**Intent is now the weaker half, and it is untouched.** At kappa 0.43 the intent
definitions are only moderately reproducible, which caps any intent score this
report can claim: some of the agent's measured intent error is definitional, not
a model failure. The confusion table below says which boundaries leak —
`feedback_or_complaint` against everything, and `other` against `software_bug`,
which are the same two boundaries as failure modes 1 and 2. They are the obvious
next target, and the pilot's `DISAMBIGUATION_RULES` are the template for how.


**The practical output.** The report emits a **30-item re-review queue**: exactly
the items where an independent reader chose differently. That is a better second
pass than a random sample, and it is the most useful thing this exercise
produced.

### Reply quality (paired subsample: 20 messages x 3 systems)

| System | n | Groundedness | Action | Tone | Mean | Safety violations | Fabricated URLs |
|---|---|---|---|---|---|---|---|
| trivial (one canned reply) | 20 | 2.95 | 2.95 | 2.95 | **2.95** | 0 | 0% |
| agent | 20 | 2.75 | 2.90 | 2.75 | **2.80** | 0 | 0% |
| simple (Apple's real reply, copied) | 20 | 2.65 | 2.50 | 2.70 | 2.62 | 0 | 0% |

**A single constant canned message beats the agent on this judge.** It did under
codebook v1 too, in the other direction and by the same tiny margin (2.95 vs
2.98). Both gaps are inside the noise of a saturated judge, which is the actual
finding: § *Is the judge trustworthy?* shows 85% of all replies sitting at the
ceiling. This table cannot rank the three systems and is not used to.

Three things it does support:

- **Zero fabricated URLs across all 60 replies.** A smoke test earlier produced a
  fake `support.apple.com` link; the prompt fix worked, and because cleaning
  replaces every real URL with `<url>`, this is objectively verifiable rather
  than judge-dependent.
- **Copying Apple's actual historical reply verbatim scores *worst* (2.62).**
  Authenticity does not survive retrieval mismatch: a real Apple reply aimed at a
  slightly different problem is worse than a generic acknowledgement. That is the
  clearest evidence that the LLM's contribution is *adaptation*, not wording.
- **Editing the escalation policy changed the replies.** The agent's mean moved
  2.98 → 2.80 when the only thing that changed was the policy prose in its system
  prompt. Retrieval was identical on 38 of 40 items and differed only in ordering
  on the other 2, so the replies moved because the *decision* half of the prompt
  moved. `src/agent.py` gets intent, reply and decision from one call, and its
  docstring flags exactly this coupling as the cost of that design; this is the
  first time it has been measured. Read it as suggestive only — a 0.18 shift on a
  saturated 1–3 scale at n=20 is weak evidence, and the same section that
  supplies this number says it cannot discriminate quality.

### Is the judge trustworthy?

Measured in `results/judge_validation.md`, since no human agreement study was
run. All four checks were re-run against the current replies.

| Check | Result |
|---|---|
| Detects injected credential request | 100% |
| Detects dismissive tone | 100% |
| Detects wrong action | 100% |
| Detects fabricated URL | 100% |
| Test–retest (grounding examples reordered) | 67% identical, mean abs diff 0.19 |
| Length bias (Spearman rho) | −0.05 — none |
| **Replies scoring ≥ 2.9 / 3** | **75%** |

**Conclusion: the judge is a reliable gross-defect detector and not a quality
discriminator.** It catches fabrication, unsafe requests and plainly wrong
actions perfectly, and it is not biased by length. But three quarters of replies
sit at the ceiling, so it cannot separate adequate from good. Every
reply-quality *ranking* in this report is therefore unsupported; the safety and
groundedness *floors* are supported.

**Two things got worse when this was re-measured, and both are reported rather
than the older, better numbers.** Test-retest stability fell from 92% identical
(mean abs diff 0.03) to **67% (0.19)**: reordering the grounding examples,
without changing a word of their content, moves the judge's score a third of the
time. That is a bigger effect than most of the between-system differences this
judge is being asked to detect, and it is an independent reason not to trust the
reply-quality ranking.

And check B — the only one anchored to real human judgement — now **fails
outright**. For messages a human labelled `escalate`, replies that correctly
escalated and replies that wrongly auto-handled both score a mean ACTION of
**3.00**. The judge does not penalise the human-identified error at all. Any
ACTION-based claim in this report is unsupported, and the report makes none.

## The two open gaps

### Gap 1 — the golden set is 40, not 150

1. 198 examples were sampled and a 20-item pilot was hand-labelled. The pilot
   showed my own taxonomy was not human-applicable (§ *Taxonomy*), so the
   definitions were rewritten.
2. To reduce labelling effort, a rule-based pre-labeller seeded a verification
   pass — with **40 items held out to be labelled blind**, as a control.
3. The control fired. The pre-labeller was **32.5% accurate** on the blind items,
   but **94.9% of its labels were accepted** during verification: a **+62.4 point
   anchoring effect**, at identical median labelling time (13.2s vs 13.3s). The
   verified labels tracked the pre-labeller's class distribution almost exactly
   and did not resemble the blind labels at all.
4. The 158 verified labels were **discarded**. Only the 40 blind labels survive.

Details: `golden/LABELLING_NOTE.md`, `results/anchoring.md`.

**Status.** `golden/label.html` now holds the 158 unlabelled items **in blind
mode** (~35 minutes of work). It did not before: as committed through
2026-09-09 those 158 were still in the rule-seeded `verify` mode — the exact
condition measured at +62pp — so labelling them would have reproduced the pass
that was just thrown away. The generator was rewritten to make that structurally
impossible (pre-labels are stripped before serialisation, not merely hidden),
the round-1 bug that let three items be confirmed without a decision was fixed,
and the tool now has tests: `make test-labeller`.

After labelling, `make merge FILE=...` validates and merges the export, and one
`make repro-live` costs 158 agent calls — the baselines never call an LLM and
the judge subsample is pinned, so nothing else re-bills.

### Gap 2 — no human judge-agreement study

The brief asks for evidence the judge agrees with a human.
`golden/judge_validation.html` is built and holds 42 replies to score (~12
minutes), then `make agreement`. It was not completed. In its place,
`results/judge_validation.md` reports four automated checks — synthetic defect
injection with known ground truth, a human-anchored ACTION check that reuses the
40 hand-labelled decisions, test-retest stability, and a length-bias test. That
is weaker evidence than a human study and is labelled as such throughout.

**The tool that collects those scores had a bug that would have corrupted them.**
Its keyboard handler picked its target field by looking for the first *unset*
one, so once an item was fully scored every number key silently wrote to
**tone**: correcting groundedness changed tone instead, with nothing on screen to
say so. Fixed with a visible active-field cursor and covered by
`tests/test_judge_validator.mjs`. Both labelling tools are treated as measurement
apparatus and tested, because a silent bug in one does not crash anything — it
just quietly changes what the data means, and both had already done it once.

**Partly addressed, and it found something.** A human study is still missing, but
an independent model of a different family relabelled the golden set from the
same written definitions the human used. That measurement is what forced the
escalation codebook rewrite: § *Is the taxonomy reproducible?*

### A note on the judge subsample

The judge scores a fixed 20 messages x 3 systems = 60 calls, the free-tier daily
ceiling. Those 20 ids used to be drawn at random from whatever the golden set
contained, which meant growing the set 40 → 198 would have redrawn them —
sharing **0 of 20** ids with the cached set and burning all 60 calls to
re-answer a question already settled. They are now pinned in
`golden/judge_subsample.json`. They remain a uniform random subsample of the
full 198: the 40 were themselves drawn uniformly at random from all 198
candidates before any label existed (`scripts/prelabel.py`, frozen seed). The
cost is that the judged subsample is 10% of the final set rather than 50%.

---

## What is misleading about my headline number?

*"Escalates at 27% against the human's 30%, precision 0.80"* is misleading in at
least ten ways, in rough order of severity.

**1. n = 40.** Below the brief's minimum of 150. The escalation recall of 0.73
rests on **11 gold escalations** and its 95% CI is [0.45, 1.00] — an interval so
wide it is compatible with a system that catches half of them and one that
catches all of them. Every point estimate in this report should be read as its
interval, and most of the intervals here do not support the sentence they sit
under.

**2. The codebook that now reaches kappa 0.77 was written after looking at the
labels it is measured against.** v2 was drafted knowing which codes the human had
actually used across the 40 items, so it encodes their revealed restraint and
fits those labels partly by construction. The 0.77 is in-sample. The honest test
is items labelled *after* the codebook was frozen — the remaining 158 — and that
test has not been run. The gold labels themselves are also still v1 labels: no
code the human used changed meaning, so on paper nothing moves, but "on paper"
is an argument and not a re-verification.

**3. A version of this system with the retrieval component deleted scores
better on every headline number.** Recall 0.73 → 0.91, macro-F1 0.53 → 0.56,
groundedness unchanged (§ *Does retrieval actually do anything?*). The effect is
two items and its CI touches zero, so it is a signal rather than a result — but
the headline is quoted for the shipped configuration, and a cheaper
configuration beat it on this set. Anyone reading the architecture as
load-bearing should read that section first.

**4. Two of seven intents are unmeasured.** `how_to` and `billing_or_purchase`
have zero gold examples. Macro-F1 is over 5 classes, not 7. The agent's
`billing_or_purchase` behaviour is completely untested — and R3 routes every
disputed charge to escalation, so an untested class sits directly on the
escalation path.

**5. Recall went *down* in the last revision, and the report leads with the
metrics that went up.** 0.91 → 0.73, one miss becoming three. The section above
argues that v1's recall was partly bought by an escalate-when-unsure policy, and
I believe that argument — but a reader should notice that I rewrote a document,
the number this report calls most important got worse, and the headline sentence
now quotes precision and escalation rate instead. Both framings are in
§ *Rewriting the escalation codebook*; the older one is not deleted.

**6. One of the three misses is the worst kind.** *"help i forgot my restrictions
passcode"* was auto-handled as a `how_to`. It is a credential reset — exactly the
E1 case that must never be automated, and it survived the codebook rewrite
untouched.

**7. Accuracy is barely above the majority-class floor.** 0.71 vs 0.67 on the
natural slice. Anyone quoting the accuracy figure would be quoting the prior.

**8. The judge cannot tell the agent apart from a canned message.** One constant
reply scores 2.95 and the agent 2.80, with 85% of all replies at the ceiling.
Under v1 the same comparison ran 2.95 vs 2.98 — the ordering flipped and neither
gap means anything. So while the intent and escalation numbers are real
measurements, any claim that the agent writes *better replies* is not supported
by my own evaluation. This is the finding I would most want a reader to notice.

**9. The judge shares a model family — and a tier — with the agent.**
Gemini 3.5 Flash Lite judges Gemini 3.1 Flash Lite. The intended judge was a
larger model, but three full-flash models hit free-tier daily quota or sustained
503s mid-run (`results/decisions_full_log.md`, #23). Same lineage and similar
capacity means the judge likely rewards its own stylistic habits, and it is
probably a contributor to the ceiling effect above.

**10. The golden set is not free of the process that made it.** Labels came from
a single annotator (the author), on messages sampled with keyword-seeded strata
that over-select messages containing those keywords. The targeted slice makes
those classes look easier to detect than they are in the wild. `other` also
conflates "unintelligible" with "not English": the agent classified Portuguese
and Spanish messages by their actual content — arguably correctly — and was
marked wrong for it. That is a taxonomy defect scored as a model error.

---

## Top 5 failure modes

**1. `feedback_or_complaint` is never predicted — 0 of 5 correct.**
> *"OMG @user how can I go back to 10.3??!!? iOS11 is complete dog shit!!"* → agent: `how_to`
> *"needs to get their shit together... THIS PHONE WAS $800. GET IT FIXED"* → agent: `software_bug`

*Hypothesis:* the agent is instructed to be a support agent, so it extracts an
actionable request from every message. It reads literally ("how can I go back"
is a how-to); the human reads pragmatically (this person is venting). Genuinely
contested — but a support system that can't recognise pure venting will keep
sending troubleshooting steps to people who want acknowledgement.

**2. Non-English messages are classified by content, not routed to `other`.**
> *"as fotos e vídeos do meu telefone não carregam mais.. como resolvo?"* → agent: `software_bug`; gold: `other`

*Hypothesis:* this is my taxonomy's fault, not the agent's. The LLM understands
Portuguese fine and identified the issue correctly. `other` should be split into
`unintelligible` and `non_english`, with the latter routed by language rather
than treated as noise.

**3. Credential-adjacent how-tos are auto-handled.**
> *"help i forgot my restrictions passcode"* → agent: `how_to` / auto / A1

*Hypothesis:* Apple publishes an article for this, and the retrieved examples
show Apple linking it, so the agent grounds correctly and escalates wrongly. The
policy (E1) treats credentials as identity; the retrieval evidence says
"documented self-serve". Grounding and policy conflict, and grounding wins.

**4. Reason codes are still the weakest output, even after the codebook fix.**
The agent's escalate/auto verdict is right 86% of the time; it cites the correct
clause 60% of the time. That is up from 27% under codebook v1, but most of the
gain came from deleting a code the human never used (§ *Rewriting the escalation
codebook*), not from better reasoning. The "stated reason" the brief explicitly
asks for is still the output a reviewer auditing *why* would be misled by most
often.

**5. Under-escalation is now the larger error, and it reversed direction.**
Under v1 the failure was over-escalation: 6 false escalations against 10 true,
precision 0.63. Under v2 it is 2 false against 8 true (precision 0.80) but 3
missed. The system moved from wasting human review to occasionally not asking
for it. That is the more expensive direction to fail in, by this report's own
cost argument, and it happened because I rewrote the policy — not because the
model changed.

---

## What I'd do next with one more week

1. **Finish the golden set.** 158 items already sampled and staged in blind
   mode; ~35 minutes, and only 110 of them are needed to clear the brief's
   minimum of 150. Every interval in this report roughly halves, and `how_to`
   and `billing_or_purchase` stop being unmeasured. Nothing else comes close in
   value per hour.
2. **Re-verify the 40 existing labels against codebook v2.** No code the round-1
   labeller used changed meaning, so on paper nothing needs to move — but "on
   paper" is an argument, not a check, and the escalation numbers are measured
   against those labels. Four rows are known to need completing (three carry no
   reason code, one no decision at all).
3. **Run the human judge agreement study that this report is missing**, and fix
   the rubric first. The current 1–3 anchors let almost everything score 3.
   Forced pairwise comparison ("which of these two replies is better, and why")
   would produce a discriminating signal where an absolute scale did not.
4. **Settle the retrieval ablation on the finished set.** k=0 currently beats
   k=5 on every headline metric with groundedness unchanged, on two items and a
   CI that touches zero. On 150 labels that question is answerable, and the
   answer decides whether the most expensive component in the repo stays. If it
   holds, the right design is probably retrieval for the *reply* and no
   retrieval for the *decision* — the failure-mode-3 mechanism says the examples
   are what pull the decision toward auto.
5. **Split the reply out of the single call.** Rewriting the escalation policy
   moved the *replies* (§ *Reply quality*) even though retrieval was unchanged —
   evidence that one call doing three jobs couples them. Two calls, decide then
   draft, would decouple that and probably help reason-code accuracy at the same
   time, since the model would justify a decision it had already made rather
   than producing both at once.
6. **Confidence + a tunable escalation threshold.** Have the agent emit a
   calibrated probability, then publish a precision/recall curve and pick an
   operating point from the cost ratio rather than accepting whatever the prompt
   produces. With v2 the system moved from over- to under-escalating; a
   threshold makes that a dial instead of a side effect of prose.
7. **Split `other` into `unintelligible` and `non_english`.** Failure modes 1
   and 2 are taxonomy problems, not model problems.
8. **An independent-family judge** and a re-run of the agreement study.

---

## Repo map

| Path | What it is |
|---|---|
| `src/taxonomy.py` | Intents, disambiguation rules, escalation policy — one source of truth, injected into both the agent prompt and the labelling UI |
| `src/data.py` | 2.8M rows → 73,859 openers; 7 documented cleaning rules |
| `src/retrieve.py` | TF-IDF retrieval; golden pair_ids excluded to prevent leakage |
| `src/agent.py` | Single schema-constrained call → intent + reply + decision + reason |
| `src/baselines.py` | Trivial and simple baselines, all three tasks |
| `src/judge.py` | Rubric, anchors, blind scoring |
| `src/evaluate.py` | Harness: CV, bootstrap CIs, error dumps |
| `src/cache.py` | Content-addressed LLM cache; `CACHE_OFFLINE=1` makes a miss fatal |
| `scripts/make_labeller.py` | Builds `golden/label.html` — blind-only, pre-labels stripped before serialisation |
| `scripts/merge_labels.py` | Validates a label export and merges it; refuses on any inconsistency |
| `tests/test_labeller.mjs` | Tests the labelling tool's state machine (`make test-labeller`) |
| `scripts/second_annotator.py` | An independent model relabels the golden set; measures whether the taxonomy is reproducible (`make second-annotator`) |
| `scripts/build_golden_sample.py` | Draws the 198-item sampling frame, natural + targeted strata (`make sample`) |
| `scripts/validate_judge.py` | The four automated judge checks (`make validate-judge`) |
| `scripts/ablate_retrieval.py` | k=0 ablation: does the retrieval component earn its place? (`make ablate`) |
| `tests/test_judge_validator.mjs` | Tests the reply-scoring tool, incl. a regression for the wrong-field write |
| `golden/judge_subsample.json` | The 20 pinned judge messages, and why they are pinned |
| `golden/LABELLING_NOTE.md` | Sampling frame, scheme, protocol, limitations, round-2 appendix |
| `DECISIONS.md` | Decision log |
| `results/` | All committed outputs |

## Citations

- Dataset: Thought Vector, *Customer Support on Twitter* (Kaggle), CC BY-NC-SA 4.0.
- Metrics: scikit-learn (`f1_score`, `cohen_kappa_score`, `StratifiedKFold`).
- Percentile bootstrap CIs: standard method, implemented directly in
  `src/evaluate.py:bootstrap_ci`.
- Quadratic-weighted kappa for ordinal rubric agreement: standard practice in
  human-agreement studies; `scikit-learn` implementation.
- LLM: Google Gemini via AI Studio free tier. No model was fine-tuned.
- Code was written with AI assistance; every design decision is recorded with
  its reasoning in `DECISIONS.md`.
