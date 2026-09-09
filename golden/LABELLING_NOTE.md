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
| Conversation **openers** only | 73,863 | see below |

27.6% of inbound messages are mid-thread replies to Apple's own clarifying
question ("Yes it's updated to that one yesterday"). They carry no standalone
intent, so they are excluded from the frame and multi-turn handling is an
explicit non-goal. The `is_opener` flag is retained in the data so this is
reversible and auditable.

## Sampling scheme

**198 examples in two slices**, drawn with seed `20260909`.

**NATURAL (n=100)** - uniform random over the 73,863 openers. Preserves true
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

1. **intent** - one of 8 classes defined in `src/taxonomy.py`, with inclusion
   and exclusion criteria and a stated priority order for multi-intent messages.
2. **decision** - `auto` or `escalate`.
3. **reason** - a fixed policy code (E1-E7, A1-A4) from `ESCALATION_POLICY` in
   `src/taxonomy.py`, not free text. Free text drifts across 198 items; codes
   stay internally consistent and let the report attribute each escalation to a
   specific policy clause.

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
