# Decision log

The 15 least-obvious decisions and why. The unabridged 22-entry working log,
including ones cut as too routine, is at `results/decisions_full_log.md`.

---

**1. "Good" is defined as correct triage, not resolution.**
Across every candidate brand, first replies on Twitter overwhelmingly acknowledge,
ask one diagnostic question, or hand off — 75% of Apple's replies point at a
resource. An agent scored on "did it resolve the issue" would measure something
this channel never does. Everything downstream follows from this.

**2. Brand chosen by measurement, then by reading real replies.**
Ranked candidates on volume, reply ratio and a measured DM-deflection rate, then
read six random replies per finalist before committing. AppleSupport won on
intent separability and having a genuine historical-resolution pattern to ground
in — not on being largest.

**3. My own brand-selection metric was wrong, and the correction is published
rather than patched.** The deflection regex counted only DM-style handoffs, so
AmazonHelp scored 0.7% while its replies say "we can't access accounts on
Twitter, please call us". Reading raw samples caught it. The table keeps its
original numbers with the caveat attached.

**4. Scoped to conversation openers; multi-turn is an explicit non-goal.**
27.6% of inbound messages are mid-thread replies to Apple's own question ("Yes
it's updated to that one yesterday") with no standalone intent. Including them
would inflate `other` and degrade every metric for a reason unrelated to the
agent. `is_opener` keeps the decision reversible.

**5. Clusters were a reading aid, not the taxonomy.**
KMeans split by vocabulary rather than intent — clusters 6, 10 and 12 were all
the same autocorrect bug in different phrasings. The taxonomy was written by hand
afterwards and deliberately does not have k classes.

**6. A 20-item pilot preceded full labelling, and it invalidated my taxonomy.**
The pilot showed the definitions were not human-applicable: one bug got three
different labels, and five items received an intent contradicting their own
reason code. Three prose definitions were replaced with mechanical tests. Finding
this at item 20 rather than 198 saved the golden set.

**7. `post_update_degradation` was merged into `software_bug` after blind
labelling used it 0 times in 40.** Expected ~15%; observed 0. The boundary failed
two independent tests. Merging a class to raise a metric would be indefensible;
merging one a careful human provably never uses is not.

**8. Escalation reasons are fixed policy codes, not free text.**
Free-text rationales drift across items and cannot be aggregated. Codes (E1–E7,
A1–A4) stay internally consistent, let the report attribute each escalation to a
clause, and make the agent scoreable on whether it cited the *right* clause —
which turned out to be its weakest output (27%).

**9. Apple's historical reply is hidden during labelling.**
Labelling while looking at Apple's actual response would encode Apple's behaviour
as ground truth, silently converting the evaluation from "is the agent right" into
"does the agent imitate Apple". Reveals are permitted but recorded per item.

**10. Two-slice golden set — natural and targeted — never pooled.**
A uniform sample starves rare classes; a purely stratified one makes every
prevalence-sensitive metric fiction. Both were drawn and are reported separately.
The natural slice carries the headline; the targeted slice is diagnostic only.

**11. Rule-seeded verification was tried, measured, and thrown away.**
To cut labelling from ~2h to ~40min, a weak rule-based pre-labeller seeded a
verification pass — with 40 items held out to be labelled blind, shown *first*, as
a control. The control fired: the pre-labeller was 32% accurate but 95% of its
labels were accepted, a **+63 point anchoring effect** at identical median
labelling time. The 158 verified labels were discarded. The measurement is the
deliverable; the shortcut was not.

**12. The pre-labeller was deliberately neither the agent nor the simple
baseline.** Seeding with the agent would make the golden set agree with the system
under evaluation by construction. Seeding with the same keyword rules the simple
baseline used would inflate that baseline — so the simple baseline was changed to
*learn* escalation, leaving keywords for pre-labelling only.

**13. Hallucinated URLs are measured, not just prompted away.**
A smoke test produced a fabricated `support.apple.com` link. Because cleaning
replaces every real URL with `<url>`, any `http` string in a reply is provably
invented — turning groundedness into an objective automated metric rather than
something only the judge can assess. The prompt was tightened *and* the metric
kept, because an unmeasured prompt fix is an assumption.

**14. Golden pair_ids are excluded from the retrieval index.**
Without this the drafter retrieves the exact message it is being evaluated on,
together with Apple's real reply, and every groundedness number becomes
meaningless.

**15. At n=40, bootstrap intervals and cross-validation replace point estimates
and a held-out split.** A fixed split would leave ~10 training labels and ~30 test
items — worse on both ends — so the simple baseline is scored on out-of-fold CV
predictions. Every headline number carries a percentile bootstrap 95% CI, because
quoting a point estimate from 40 examples is the easiest way to mislead. Macro-F1
covers only the 5 observed classes; the 2 absent ones are unmeasured, not zero.

**16. The labelling tool is treated as measurement apparatus, and tested.**
It has already corrupted the data twice: the rule-seeded `verify` mode cost 158
labels to anchoring, and an ungated confirm button put three decision-less items
into the golden set, where they remain. Neither failure crashed anything — that
is the point. A bug in a labelling tool does not announce itself, it silently
changes what the golden set *means*, and every downstream number inherits the
damage without any visible symptom. So round 2's tool is blind by construction
(pre-labels are stripped before serialisation, not merely hidden, with asserts
enforcing it), confirm is gated on completeness, and `tests/test_labeller.mjs`
exercises the state machine directly.

**17. The label export is merged by a script that refuses, not by `cat`.**
`scripts/merge_labels.py` checks taxonomy membership, decision/reason
consistency, collisions with round 1, duplicates, unknown pair_ids, and the
`was_seeded` flag, and merges nothing if any check fails. Appending 158 rows by
hand is a one-line operation whose failure mode is a quietly malformed golden
set — the most expensive possible bug here, because it would be invisible in
every table it produced.

**18. The judge's 20-message subsample is pinned, not redrawn.**
It was selected by seeded RNG over the golden set's pair_ids, which is
reproducible only while the set is a fixed size. Growing it 40 -> 198 would have
redrawn all 20 ids — 0 overlap with the cached set — spending the entire
free-tier daily judge quota to re-answer a question already settled: the judge is
saturated (a constant canned reply scores 2.95 against the agent's 2.98), so a
fresh sample buys no new information. The ids now live in
`golden/judge_subsample.json`. They are still a uniform random subsample of the
full 198, because the 40 were drawn uniformly at random from all 198 before any
label existed. The honest cost — 10% of the set judged rather than 50% — is
stated in the README rather than absorbed silently.

**19. A second annotator was run as an independent model, not as a stand-in for a
human.** The brief asks for human agreement and that gap stays open; a model
cannot close it, because two readers of the same definitions can agree and both
be wrong. What a second reader *can* establish is whether the written taxonomy is
reproducible at all. It was given exactly the human's inputs — same definitions,
same disambiguation rules, same policy codes, Apple's reply withheld, no
retrieved examples, no reply to draft — and deliberately a **different model
family** (Gemma, not Gemini), so the result is not agreement-by-shared-lineage
with the agent.

**20. The escalation policy, not the model, is the weakest link — and the second
annotator is what exposed it.** Intent reaches kappa 0.47; escalate/auto reaches
**0.08**, which is chance. The disagreement is one-directional: 22 items the
human called `auto` the annotator called `escalate`, against 1 the other way, and
escalation rates run 28% (human) / 43% (agent) / 82% (annotator). The cause is in
the codebook: E7 ends "or the agent's own confidence is low" and E6 covers
"severe dissatisfaction ... or sustained abuse" on a corpus of angry, profane
tweets, while the auto side has no positive criteria at all — it is "AUTO-HANDLE
otherwise". Seven ways out and no way to stay. So the agent's 0.91 escalation
recall is measured against a target that is not reproducible from the written
rules, and the human labels encode restraint the policy never states. The fix is
mechanical tests for E6/E7 and positive auto criteria — and it belongs *before*
the 158 round-2 labels, since relabelling under an ambiguous policy only
manufactures more ambiguous labels.

**21. A transient network error was killing whole runs, silently.**
`src/llm.py` classified retryable failures by substring, testing for `"timeout"`.
httpx raises `ReadTimeout("[Errno 60] Operation timed out")` — *timed out*, two
words — so an ordinary network blip was judged unretryable and aborted the entire
run at whatever call it struck. It killed the 40-item annotation pass twice
before being diagnosed, and it sits on the same path as the 158-call
`make repro-live`. Now matched on exception type first (`ReadTimeout`,
`ConnectTimeout`, `RemoteProtocolError`) plus a wider message list, verified
against seven cases including that `400 INVALID_ARGUMENT` and `403
PERMISSION_DENIED` still fail fast — retrying a real bug eight times wastes quota
and hides the cause.

**22. The escalation codebook was rewritten (v2) after a second annotator
measured v1 at chance.** v1 read as seven ways to escalate and no positive way
to stay: `E7` ended "...or the agent's own confidence is low", so a careful
reader reached for it whenever unsure; `E6` fired on "severe dissatisfaction or
sustained abuse" across a corpus of angry profane tweets; and the auto side had
no criteria at all, just "AUTO-HANDLE otherwise". An independent annotator
reading that text agreed with the human at kappa **0.08** and escalated 82% of
messages against the human's 28% — and 19 of the 24 disagreements were E6 or E7
alone, codes the human used **zero** times in 40 items. v2 deletes E7, gives E6
a mechanical test (a named outside party: lawyer, regulator, press, chargeback —
never tone or profanity), gives every auto case a positive code including a new
`A5` for messages with no recoverable request, and states an application order
with no "unsure" branch. Every code the human actually used (A2, A4, E1, E2, E3)
keeps its exact meaning, which is why there is a gap at A3 instead of a tidy
renumber: round-1 and round-2 labels stay comparable. The rewrite happened
*before* the remaining labels were collected, not after — relabelling against a
policy two readers apply differently just manufactures more ambiguity.
Proposal and evidence: `golden/CODEBOOK_V2_PROPOSAL.md`.

**23. The code lists were consolidated into one place because they had already
drifted four ways.** `E1..E7 / A1..A4` was typed out by hand in the agent's
response schema, the labelling UI, the second annotator, and the merge
validator. Retiring two codes in `src/taxonomy.py` would have left the agent
still able to emit them and the merge validator still willing to accept them.
All four now import `REASON_CODES` from the taxonomy, and
`scripts/make_labeller.py` asserts its UI codes match exactly — a labelling tool
offering a code the agent cannot produce silently corrupts the comparison it
exists to measure.

**24. A date was being sorted as a string, and the fix was kept even though it
moved almost nothing.** `src/data.py` claimed to keep the *first* brand reply
per customer message, and implemented it as
`sort_values("created_at_reply")` — where `created_at` is the raw Twitter string
`"Mon Oct 30 15:14:01 +0000 2017"`. Sorted as text, that orders by weekday name,
then month name. Measured blast radius: 23 of 106,623 customer messages have
more than one brand reply, and parsing the timestamp properly changes 81 of
102,086 final pairs (0.08%), **none of them in the golden set**. Fixed anyway,
with an assertion that every timestamp parses: the docstring asserted a property
the code did not have, and that is the kind of defect that is silently wrong
again at a larger scale later.

**25. The codebook rewrite was pre-registered and then measured, not just
asserted.** Before touching `src/taxonomy.py`, the expected result was written
down in `golden/CODEBOOK_V2_PROPOSAL.md` § 2: reassigning every E6/E7 escalation
to auto on the existing 40 items projects kappa **0.76**, so the prediction on
record was 0.7-0.8. The same annotator model was then re-run on the same 40 items
under v2 and returned **0.77** (agreement 41% -> 90%). The intent definitions,
which were *not* changed, act as the control: their kappa moved 0.47 -> 0.43, so
about +/-0.04 is this measurement's own noise and the escalation move of +0.69 is
far outside it. Writing the prediction down first is what makes the second number
evidence rather than a story told afterwards -- and if it had come back at 0.3,
that would have been the finding, and 158 items would not have been labelled
under v2.
