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

## ⚠️ Deviations from the brief — read this first

**The golden set is 40 hand-labelled examples, not the 150–250 the assignment
specifies.** This is a real shortfall and it is the main limitation of
everything below. The story is documented rather than hidden, because how it
happened is more interesting than the number:

1. 198 examples were sampled and a 20-item pilot was hand-labelled. The pilot
   showed my own taxonomy was not human-applicable (§ *Taxonomy*), so the
   definitions were rewritten.
2. To reduce labelling effort, a rule-based pre-labeller seeded a verification
   pass — with **40 items held out to be labelled blind**, as a control.
3. The control fired. The pre-labeller was **32% accurate** on the blind items,
   but **95% of its labels were accepted** during verification: a **+63 point
   anchoring effect**, at identical median labelling time (13.2s vs 13.3s).
   The verified labels tracked the pre-labeller's class distribution almost
   exactly and did not resemble the blind labels at all.
4. The 158 verified labels were **discarded**. Only the 40 blind labels survive.

So the headline numbers rest on 40 examples with wide confidence intervals, and
two intents (`how_to`, `billing_or_purchase`) have zero examples and are
**unmeasured**. Details: `golden/LABELLING_NOTE.md`, `results/anchoring.md`.

**A second deviation: no human LLM-judge agreement study was run.** The brief
asks for evidence the judge agrees with a human. `golden/judge_validation.html`
is built and ready but was not completed. In its place, `results/judge_validation.md`
reports four automated checks — synthetic defect injection with known ground
truth, a human-anchored action check reusing the 40 hand-labelled decisions,
test-retest stability, and a length-bias test. That is weaker evidence than a
human study and is labelled as such throughout.

**Status of the fix (2026-09-10).** Both gaps are tooled, neither is closed.

Gap 1 is one labelling session away. `golden/label.html` now holds the 158
unlabelled items **in blind mode** (~35 min). It did not before: as committed
through 2026-09-09 those 158 were still in the rule-seeded `verify` mode — the
exact condition measured at +62pp — so labelling them would have reproduced the
discarded pass. The generator was rewritten to make that structurally
impossible (pre-labels are stripped before serialisation, not hidden), the
round-1 bug that let three items be confirmed without a decision was fixed, and
the tool now has tests: `make test-labeller`. Details in
`golden/LABELLING_NOTE.md` § *Appendix: round 2 protocol*.

After labelling, `make merge FILE=...` validates and merges the export, and one
`make repro-live` costs **158 agent calls** — the baselines never call an LLM,
and the judge subsample is pinned (below), so nothing else re-bills.

Gap 2 is unchanged: `golden/judge_validation.html` holds 42 replies to score
(~12 min), then `make agreement`.

**A note on the judge subsample.** The judge scores a fixed 20 messages x 3
systems = 60 calls, the free-tier daily ceiling. Those 20 ids used to be drawn
at random from whatever the golden set contained, which meant growing the set
40 -> 198 would have redrawn them — sharing **0 of 20** ids with the cached set
and burning all 60 calls to re-answer a question already settled. They are now
pinned in `golden/judge_subsample.json`. They remain a uniform random subsample
of the full 198: the 40 were themselves drawn uniformly at random from all 198
candidates before any label existed (`scripts/prelabel.py`, frozen seed). The
cost is that the judged subsample is 10% of the final set rather than 50%.

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
| **A citable reason** | Every decision names a policy clause (E1–E7 / A1–A4), so a human reviewer can audit *why*, not just *what*. |

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

**Headline: the agent auto-handles 57% of messages while missing 1 of 11
escalations.** Every caveat that number deserves is in the next section.

### Intent (n=40, macro-F1 over the 5 observed classes)

| System | Accuracy [95% CI] | Macro-F1 [95% CI] |
|---|---|---|
| **agent** | **0.63 [0.47, 0.78]** | **0.56 [0.35, 0.68]** |
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
| **agent** | **0.63** | **0.91 [0.73, 1.00]** | **1** | 0.27 |
| simple | 0.00 | 0.00 | 11 | 0.00 |
| trivial | 0.00 | 0.00 | 11 | 0.14 |

Both baselines escalate **nothing**. The trivial one by construction; the simple
one because a logistic regression on ~30 imbalanced training labels collapses to
the majority class. This is where the LLM earns its place — not in
classification, where a simple model is competitive, but in recognising that a
locked-out or injured customer needs a human.

### Reply quality (paired subsample: 20 messages x 3 systems)

| System | n | Groundedness | Action | Tone | Mean | Safety violations | Fabricated URLs |
|---|---|---|---|---|---|---|---|
| agent | 20 | 2.95 | 3.00 | 3.00 | **2.98** | 0 | 0% |
| trivial (one canned reply) | 20 | 2.95 | 2.95 | 2.95 | **2.95** | 0 | 0% |
| simple (Apple's real reply, copied) | 20 | 2.65 | 2.50 | 2.70 | 2.62 | 0 | 0% |

**Do not read this table as "the agent writes the best replies."** A single
constant canned message scores 2.95 against the agent's 2.98. That gap is noise,
and it means the judge is saturated rather than that the systems are equal —
see the judge validation below.

Two things the table does support:

- **Zero fabricated URLs across all 60 replies.** A smoke test earlier produced a
  fake `support.apple.com` link; the prompt fix worked, and because cleaning
  replaces every real URL with `<url>`, this is objectively verifiable rather
  than judge-dependent.
- **Copying Apple's actual historical reply verbatim scores *worst* (2.62).**
  Authenticity does not survive retrieval mismatch: a real Apple reply aimed at a
  slightly different problem is worse than a generic acknowledgement. That is the
  clearest evidence that the LLM's contribution is *adaptation*, not wording.

### Is the judge trustworthy?

Measured in `results/judge_validation.md`, since no human agreement study was run:

| Check | Result |
|---|---|
| Detects injected credential request | 100% |
| Detects dismissive tone | 100% |
| Detects wrong action | 100% |
| Detects fabricated URL | 88% |
| Test–retest (grounding examples reordered) | 92% identical, mean abs diff 0.03 |
| Length bias (Spearman rho) | 0.18 — weak |
| **Replies scoring >= 2.9 / 3** | **85%** |

**Conclusion: the judge is a reliable gross-defect detector and not a quality
discriminator.** It catches fabrication, unsafe requests and plainly wrong
actions almost perfectly, and it is stable and largely unbiased by length. But
85% of replies sit at the ceiling, so it cannot separate adequate from good. Every
reply-quality *ranking* in this report is therefore unsupported; the safety and
groundedness *floors* are supported.

---

## What is misleading about my headline number?

*"57% auto-handled, 1 of 11 escalations missed"* is misleading in at least seven
ways, in rough order of severity.

**1. n = 40.** Below the brief's minimum. The escalation recall of 0.91 rests on
**11 gold escalations**; its 95% CI is [0.73, 1.00]. One more miss would move it
to 0.82. Every point estimate in this report should be read as its interval.

**2. Two of seven intents are unmeasured.** `how_to` and `billing_or_purchase`
have zero gold examples. Macro-F1 is over 5 classes, not 7. The agent's
`billing_or_purchase` behaviour is completely untested — and R3 routes every
disputed charge to escalation, so an untested class sits directly on the
escalation path.

**3. The one missed escalation is the worst kind.** *"help i forgot my
restrictions passcode"* was auto-handled as a `how_to`. It is a credential reset —
exactly the E1 case that must never be automated. A 91% recall figure hides that
the single failure is in the highest-cost category.

**4. Accuracy is barely above the majority-class floor.** 0.71 vs 0.67 on the
natural slice. Anyone quoting the accuracy figure would be quoting the prior.

**5. The judge cannot tell the agent apart from a canned message.** It scores one
constant reply at 2.95 and the agent at 2.98, with 85% of all replies at the
ceiling. So while the intent and escalation numbers are real measurements, any
claim that the agent writes *better replies* is not supported by my own
evaluation. This is the finding I would most want a reader to notice.

**6. The judge shares a model family — and a tier — with the agent.**
Gemini 3.5 Flash Lite judges Gemini 3.1 Flash Lite. The intended judge was a
larger model, but three full-flash models hit free-tier daily quota or sustained
503s mid-run (`results/decisions_full_log.md`, #23). Same lineage and similar
capacity means the judge likely rewards its own stylistic habits, and it is
probably a contributor to the ceiling effect above.

**7. The golden set is not free of the process that made it.** Labels came from
a single annotator (the author), on messages sampled with keyword-seeded strata
that over-select messages containing those keywords. The targeted slice makes
those classes look easier to detect than they are in the wild.

**8. `other` conflates two different things.** It means both "unintelligible"
and "not English". The agent classified Portuguese and Spanish messages by their
actual content — arguably correctly — and was marked wrong. That is a taxonomy
defect scored as a model error.

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

**4. Reason codes are unreliable even when the verdict is right — 27%.**
The agent's escalate/auto verdict is right 84% of the time but it cites the
correct clause only 27% of the time. The "stated reason" the brief explicitly
asks for is the weakest output in the system, and a reviewer auditing *why*
would be misled far more often than one auditing *what*.

**5. Over-escalation: precision 0.63.** Six false escalations against ten true
ones. Cheap relative to a miss, but at scale it is 60% wasted human review on
the escalation queue. Concentrated in hardware-adjacent complaints where a
product is criticised but nothing is actually broken.

---

## What I'd do next with one more week

1. **Finish the golden set.** 158 items already sampled and staged in blind mode;
   ~30 minutes. Every interval in this report roughly halves. Nothing else comes
   close in value per hour.
2. **Run the human judge agreement study that this report is missing**, and fix
   the rubric first. The current 1-3 anchors let almost everything score 3.
   Forced pairwise comparison ("which of these two replies is better, and why")
   would produce a discriminating signal where an absolute scale did not.
   Then a second annotator and Cohen's kappa on intent, so the label noise floor —
   and therefore the achievable ceiling — is known.
3. **Confidence + a tunable escalation threshold.** Have the agent emit a
   calibrated probability, then publish a precision/recall curve and pick an
   operating point from the cost ratio rather than accepting whatever the prompt
   produces.
4. **Split `other`; re-test the `feedback_or_complaint` boundary.** Failure modes
   1, 2 and 7 are all taxonomy problems, not model problems.
5. **An independent-family judge** and a re-run of the agreement study.
6. **Fix reason-code accuracy** — likely a two-stage call (decide, then justify
   against the policy text) rather than asking for both at once.

---

## Repo map

| Path | What it is |
|---|---|
| `src/taxonomy.py` | Intents, disambiguation rules, escalation policy — one source of truth, injected into both the agent prompt and the labelling UI |
| `src/data.py` | 2.8M rows → 73,863 openers; 7 documented cleaning rules |
| `src/retrieve.py` | TF-IDF retrieval; golden pair_ids excluded to prevent leakage |
| `src/agent.py` | Single schema-constrained call → intent + reply + decision + reason |
| `src/baselines.py` | Trivial and simple baselines, all three tasks |
| `src/judge.py` | Rubric, anchors, blind scoring |
| `src/evaluate.py` | Harness: CV, bootstrap CIs, error dumps |
| `src/cache.py` | Content-addressed LLM cache; `CACHE_OFFLINE=1` makes a miss fatal |
| `scripts/make_labeller.py` | Builds `golden/label.html` — blind-only, pre-labels stripped before serialisation |
| `scripts/merge_labels.py` | Validates a label export and merges it; refuses on any inconsistency |
| `tests/test_labeller.mjs` | Tests the labelling tool's state machine (`make test-labeller`) |
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
