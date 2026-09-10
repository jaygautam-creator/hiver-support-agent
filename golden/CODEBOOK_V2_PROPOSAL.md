# Proposed rewrite of the escalation codebook (v2) — awaiting sign-off

Status: **proposal only.** Nothing in `src/taxonomy.py` has been touched.

Why now: `results/second_annotator.md` shows escalate/auto kappa 0.08 between the
human and an independent reader of the same written policy. Labelling the
remaining 158 items under that policy manufactures 158 ambiguous labels.

---

## 1. What the round-1 labels actually reveal

Codes the human used across all 40 items:

| | A1 | A2 | A3 | A4 | A5 | E1 | E2 | E3 | E4 | E5 | E6 | E7 | (blank) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| human | 0 | 21 | 0 | 5 | – | 6 | 1 | 4 | 0 | 0 | **0** | **0** | 3 |
| annotator | 3 | 1 | 1 | 2 | – | 5 | 1 | 6 | 0 | 2 | **8** | **11** | 0 |

**The human never once used E6 or E7. The annotator used them 19 times.** That is
the entire disagreement, not a tendency within it.

Second: the human's decisions are a near-deterministic function of intent.

| intent | decision / code | n |
|---|---|---|
| account_access | escalate / E1 (6), E2 (1) | 7 |
| hardware_or_repair | escalate / E3 | 4 |
| hardware_or_repair | auto / A2 | 1 |
| software_bug | auto / A2 | 19 |
| feedback_or_complaint | auto / A4 (4), A2 (1) | 5 |
| other | auto / A4 (1), blank (2), no decision (1) | 4 |

39 of 40 follow the rule *escalate iff intent ∈ {account_access,
billing_or_purchase, hardware_or_repair}*. The single exception is
`2794378_2794377`, which the annotator also thought was mislabelled as hardware.

So the operative policy — the one that produced the gold labels — is already
intent-driven. E1/E2/E3 are restatements of three intent classes. **v2 does not
create that coupling; it writes down a coupling that already exists and is
currently hidden.** The consequence has to go in the README: once this is
explicit, the escalation metric is largely not independent evidence from the
intent metric, except on the cross-cutting triggers (safety, data loss, and the
named-external-party case).

## 2. What the fix is worth, before doing it

Recomputing agreement on the existing 40 with every E6/E7 escalation reassigned
to auto — i.e. exactly what deleting E7 and narrowing E6 would do:

| | agreement | kappa |
|---|---|---|
| as measured | 41% | **0.08** (chance) |
| E6/E7 neutralised | 90% | **0.76** (substantial) |

This is a **projection on paper, not a rerun.** It is the ceiling the rewrite is
aiming at, and §6 proposes actually measuring it.

---

## 3. Proposed replacement for `ESCALATION_POLICY`

Three changes: E7 deleted, E6 given a mechanical test, the auto side given
positive criteria and a tie-break. **Code numbers for everything the human
already used (A2, A4, E1, E2, E3) keep their exact meaning**, so round-1 labels
stay comparable with round-2 — that is why there is a gap at A3 rather than a
tidy renumbering.

```
ESCALATION_POLICY = """
HOW TO APPLY. Work down the ESCALATE triggers in the order E4, E5, E1, E2, E3,
E6. The first that fires decides the case and supplies the reason code. If none
fires, the message is AUTO-HANDLE and you must name a positive A-code for it.
There is no "unsure" branch: uncertainty is not an escalation trigger.

Two evidence bars, deliberately different:
  * E1-E5 are RISK triggers. Reasonable suspicion is enough. Wrongly escalating
    costs an agent two minutes; wrongly auto-handling a locked-out or injured
    customer loses a customer.
  * E6 is a NON-RISK trigger. It requires an explicit statement in the message
    itself. Tone, severity and inference never fire it.

ESCALATE to a human when ANY of these hold:
  E1. ACCOUNT SECURITY OR IDENTITY. Cannot sign in, locked out, password reset,
      2FA, or the account is or may be compromised. Identity cannot be verified
      over public Twitter. Intent account_access always fires E1.
  E2. MONEY IN DISPUTE. A specific charge, refund, subscription or order the
      customer wants changed on their account. Intent billing_or_purchase fires
      E2 except for pre-sale "should I buy / will this work" questions, which
      are A1.
  E3. PHYSICAL HARDWARE. A device fault needing inspection, a warranty or repair
      claim, or a service-centre outcome to review. Intent hardware_or_repair
      always fires E3.
  E4. SAFETY. Heat, swelling, smoke, fire, shock, or any injury. Fires
      regardless of intent.
  E5. DATA LOSS. Photos, messages, backups or files reported gone, deleted,
      wiped or unrecoverable. "Won't load", "won't sync", "won't open" is NOT
      data loss -- that is a software fault (A2).
  E6. NAMED EXTERNAL ESCALATION. The customer states in the message that they
      have involved or will involve a named outside party: a lawyer or legal
      action, a regulator or consumer-protection body, the press or a
      journalist, or a card chargeback / payment dispute.
      E6 does NOT fire on profanity, insults, sarcasm, capitals, repetition,
      "worst ever", "this is unacceptable", demands to fix something, or threats
      to switch to another brand. This corpus is angry public tweets; anger is
      the medium, not a signal. Those are A4.

AUTO-HANDLE otherwise. Every auto case takes one of these positive codes:
  A1. ANSWERABLE QUESTION. Nothing is malfunctioning and the answer is public:
      how to use a feature, where a setting lives, whether something is
      possible, or a pre-sale question.
  A2. SOFTWARE FAULT, STANDARD FIRST RESPONSE. Apple software is broken,
      degraded or misbehaving and the right first move is an acknowledgement
      plus a version/device check or one diagnostic question. No physical
      damage, nothing reported gone.
  A4. FEEDBACK WITH NO DIAGNOSABLE FAULT. Criticism, venting, or a feature
      request naming no specific fault to act on. Severity does not change this;
      only E6's named outside party does.
  A5. NO RECOVERABLE REQUEST. Unintelligible, context-free, or not in a
      supported language, so no reply can be drafted without inventing the
      customer's problem. The auto response is one clarifying question or a
      language redirect. A human cannot do better from the same text, so this is
      auto, not escalate.

RETIRED -- never assign:
  A3. "Post-update standard diagnostic". Dead since R1 merged
      post_update_degradation into software_bug; it duplicates A2 and the pilot
      already found software_bug+A3 self-contradictory.
  E7. "Unintelligible or the agent's own confidence is low". Deleted. Low
      confidence is not a trigger; unintelligible messages are A5.
"""
```

## 4. What this does to the existing 40 labels

Nothing, almost. No code the human used changed meaning, so **no intent or
decision label needs revisiting.** Only the four incomplete rows need a value:

| pair_id | current | under v2 |
|---|---|---|
| `431360_431359` "Sent you a DM @user" | other / auto / — | other / auto / **A5** |
| `2332386_2332385` (pt, battery after iOS 11.0.3) | other / auto / — | other / auto / **A5** |
| `39617_39616` (pt, photos won't load) | other / **no decision** / — | other / **auto** / **A5** |
| `2794378_2794377` | hardware_or_repair / auto / A2 | flagged as a probable intent error, independent of v2 |

`39617` is the round-1 ungated-confirm bug, already fixed in the tool. Note v2's
E5 wording deliberately excludes it: "não carregam" is won't-load, not gone —
which is exactly the call the annotator got wrong under v1.

My recommendation: **fill those four, re-label nothing else.** Doing a full
re-pass would cost ~25 minutes and, on this evidence, change nothing.

## 5. The caveat that has to ship with this

v2 was written **after** seeing which codes the human used. It encodes the
human's revealed restraint, so it fits the round-1 labels by construction and the
0.76 projection in §2 is in-sample. The reproducibility claim cannot rest on the
40. It has to be re-tested on items labelled after the codebook was frozen — the
158 — or it is circular. This needs to be said in the README in those words.

## 6. Recommended order of operations

1. You approve, amend, or reject §3.
2. Freeze v2 into `src/taxonomy.py` and mirror `ESC_CODES` / `AUTO_CODES` in
   `scripts/make_labeller.py` (retire A3/E7, add A5) — they must not drift.
3. **Re-run the second annotator on the same 40 under v2, before labelling.**
   ~40 min at gemma's ~1 call/min, fully cached. This turns §2's paper number
   into a measurement, and it is pre-registered: the prediction on record is
   kappa ≈ 0.7-0.8. If it comes back at 0.3, v2 is not the fix and labelling 158
   items under it would be the same mistake at larger scale.
4. Fill the four rows in §4.
5. Only then: label the 158.

Step 3 is the one I would defend hardest. It is the difference between "I
rewrote the codebook" and "I rewrote the codebook and showed it worked".

## 7. Costs you are agreeing to

- Editing `src/taxonomy.py` changes the agent prompt, invalidating the response
  cache: a full `make repro-live` (158 + 40 items), not a resume.
- The headline escalation numbers **will move**. The agent currently escalates
  42% against the human's 28%, drifting the same way the annotator did because
  it reads the same escalate-biased text. Under v2 that drift should shrink, so
  precision should rise and recall may fall. The 0.91 [0.73, 1.00] recall in the
  README is not portable across this change and will be recomputed, not edited.
- A3 and E7 disappearing must be noted in `DECISIONS.md` and in
  `golden/LABELLING_NOTE.md`, which is otherwise deliberately unrevised.
