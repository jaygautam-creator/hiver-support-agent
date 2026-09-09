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
