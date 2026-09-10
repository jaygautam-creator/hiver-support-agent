# Golden set: how it was sampled and labelled

Required deliverable #2. **Written before labelling began.** Nothing in this
file was revised after seeing model results.

## Sampling frame

Source: `thoughtvector/customer-support-on-twitter` (Kaggle), 2,811,774 rows.

Narrowed in three documented steps:

| Step | Rows | Why |
|---|---|---|
| Full dump | 2,811,774 | - |
| AppleSupport customer->first-reply pairs | 102,086 | one brand, as the assignment requires |
| Conversation **openers** only | 73,859 | see below |

27.6% of inbound messages are mid-thread replies to Apple's own clarifying
question ("Yes it's updated to that one yesterday"). They carry no standalone
intent, so they are excluded from the frame and multi-turn handling is an
explicit non-goal. The `is_opener` flag is retained in the data so this is
reversible and auditable.

## Sampling scheme

**198 examples in two slices**, drawn with seed `20260909`.

**NATURAL (n=100)** - uniform random over the 73,859 openers. Preserves true
class prevalence, so a metric computed on this slice estimates live
performance. Useless alone for rare classes: `account_access` lands ~3
examples and its F1 would be noise.

**TARGETED (n=98)** - keyword-seeded oversampling, 14 per stratum, of the
classes the natural slice starves plus three deliberately hard regions:

| Stratum | Pool | Drawn |
|---|---|---|
| account_access | 2,972 | 14 |
| hardware_or_repair | 1,827 | 14 |
| billing_or_purchase | 5,577 | 14 |
| how_to | 3,693 | 14 |
| hard_nonenglish | 1,550 | 14 |
| hard_short (15-45 chars) | 6,853 | 14 |
| hard_profanity | 10,402 | 14 |

**Metrics are reported on both slices separately and never silently pooled.**
The targeted slice is the diagnostic; the natural slice is the deployment
estimate. Pooling them into one headline is the easiest available way to
publish a misleading number.

**Known bias, stated up front:** keyword-seeded strata over-select messages that
literally contain those keywords, so the targeted slice makes those classes look
easier to detect than they are in the wild. That is precisely why the natural
slice exists and why it carries the headline.

## Splits

`dev` (50) / `test` (148), assigned by position **before any label existed**, so
the split cannot have been influenced by which items turned out to be easy.
The test split is opened once, at the end.

## Label definitions

Three fields per example:

1. **intent** - one of 7 classes defined in `src/taxonomy.py`, with inclusion
   and exclusion criteria and a stated priority order for multi-intent messages.
   (This line read "8 classes" until 2026-09-10: a stale count left over from
   before the pilot collapsed `post_update_degradation` into `software_bug`,
   described below. Corrected rather than left standing, and flagged here
   because the rest of this file is deliberately unrevised.)
2. **decision** - `auto` or `escalate`.
3. **reason** - a fixed policy code from `ESCALATION_POLICY` in
   `src/taxonomy.py`, not free text. Free text drifts across 198 items; codes
   stay internally consistent and let the report attribute each escalation to a
   specific policy clause.

   Round 1 was labelled under codebook **v1** (E1-E7 / A1-A4). Round 2 is
   labelled under **v2** (E1-E6 / A1, A2, A4, A5), because v1 was measured and
   failed: a second annotator reading the same text agreed with the human at
   kappa 0.08 on escalate/auto. Every code the round-1 labeller actually used
   (A2, A4, E1, E2, E3) keeps its exact meaning in v2, so the two rounds remain
   comparable; the retired codes are A3 and E7, which round 1 used zero times.
   See `golden/CODEBOOK_V2_PROPOSAL.md` and `results/second_annotator.md`.

## Pilot, and the taxonomy revision it forced

A 20-item pilot was labelled before committing to the full set. It found that
the **original definitions could not be applied consistently by a human**:

- The same iOS 11 "I" -> "?" autocorrect bug was labelled `software_bug`,
  `how_to` and `other` in one sitting -- the definitions never said whether to
  classify by grammatical form or underlying issue.
- Five messages received intent `software_bug` with reason code `A3`
  ("post-update diagnostic"), which is self-contradictory. The
  `software_bug` / `post_update_degradation` boundary asked for a judgement
  nobody can make repeatably.
- An unwanted iTunes charge ("my phone bought an album on its own") was labelled
  `how_to`/auto while an explicit accidental purchase was labelled
  `billing_or_purchase`/escalate.

A boundary a careful human cannot apply repeatably puts a hard ceiling on any
classifier, and the resulting metric measures the definition rather than the
system. Three prose definitions were therefore replaced with mechanical tests
(`DISAMBIGUATION_RULES` in `src/taxonomy.py`), and the pilot items were
re-labelled under them.

The v1 pilot labels are kept at `golden/pilot_v1_labels.jsonl`. The
disagreement between v1 and v2 on those 20 items is reported as evidence of how
much the definitions -- not the labeller -- were driving the noise.

Observed pilot cost: median 22.9s per item, 75th percentile 61s, max 4m38s
("my charger broke" -- short, context-free messages are the expensive ones).

## Protocol

- Labelled in `golden/label.html`, one item at a time, in shuffled order so
  stratum runs cannot prime the labeller.
- **Apple's actual reply is hidden by default.** Labelling while looking at what
  Apple did would encode Apple's behaviour rather than independent judgement,
  which silently turns the evaluation into "does the agent imitate Apple"
  instead of "is the agent right". Reveals are permitted but recorded per item
  (`revealed_reply`) so their effect can be measured.
- Per-item labelling time recorded (`label_ms`).

## Intra-annotator agreement

<!-- Filled after the second pass: 40 items re-labelled >=24h later, blind to
     the first pass. Reported as Cohen's kappa per field. -->

## Known limitations of this set

<!-- Completed after labelling. -->

---

# Appendix: round 2 protocol (added 2026-09-10, after round 1)

Everything above was written before any labelling. This appendix is appended,
not merged into the body, so that claim stays literally true.

## What round 1 left

| | Items | Status |
|---|---|---|
| Blind control group | 40 | **Kept.** The golden set as it stands. |
| Rule-seeded verification pass | 158 | **Discarded** (+62pp anchoring, `results/anchoring.md`). |

40 is below the brief's 150-250. Round 2 relabels those 158 from scratch.

## What changed in the tool before round 2 began

Round 1's tool put two defects into the data. Both are fixed in
`scripts/make_labeller.py`, and the fixes are enforced rather than intended:

1. **Anchoring.** The "verify" mode is gone. `make label` now drops every
   pair_id already present in `labelled.jsonl` and forces `mode="blind"` on
   what remains, and the `pre_*` fields are **stripped before serialisation** —
   the pre-labels are not hidden in the page, they are absent from it. Two
   asserts in the generator fail the build if either invariant breaks.

2. **Incomplete confirms.** Round 1's confirm button was not gated on
   completeness, so three items (`39617_39616`, `431360_431359`,
   `2332386_2332385`, all `intent: other`) entered the golden set with an
   intent but no decision. They are still there, carried as intent-only rows by
   `decision_complete` in `src/evaluate.py`. Confirm now refuses until intent,
   decision and reason are all set, and names what is missing.

A third change guards the browser rather than the code: the localStorage key
moved `golden_labels_v2` -> `v3`, because round 1's seeded state is still in the
browser and would otherwise be restored, pre-filled, on open.

`tests/test_labeller.mjs` (`make test-labeller`) exercises the tool's state
machine directly — a labelling tool is measurement apparatus, and a silent bug
in it does not crash anything, it just quietly changes what the golden set
means.

## Round 2 procedure

1. `make label` — regenerates the tool with the 158 unlabelled items, blind.
2. Label them. Reveals stay permitted and recorded (`revealed_reply`).
3. Export, then `make merge FILE=~/Downloads/labelled.jsonl` — validates the
   export (taxonomy membership, decision/reason consistency, no collisions with
   round 1, nothing seeded) and refuses to merge if anything is off.
4. `make repro-live` — re-runs the agent over the new messages.
5. `make repro` — confirms the committed cache reproduces the result offline.

## What round 2 does not fix

The 40 round-1 labels and the 158 round-2 labels come from **the same single
annotator**, a day apart (2026-09-09 / 2026-09-10). There is still no second
annotator, so inter-annotator agreement remains unmeasurable and the
intra-annotator section above remains unfilled. The proximity cuts both ways:
the taxonomy is fresh, but round 1's habits are also fresh, so the two halves
are not independent. Any claim about label quality
rests on the protocol, not on a measured agreement number.
