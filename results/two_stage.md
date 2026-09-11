# Two-stage: decide first, then justify

The brief asks for a decision *with a stated reason*, and the stated reason is the weakest thing this system produces. The shipped agent emits intent, reply, decision and reason from one call; this variant splits it so stage 2 justifies a decision stage 1 has already fixed. The prediction was written into `scripts/two_stage.py` before the run.

| Metric | 1 call (shipped) | 2 calls | Δ |
|---|---|---|---|
| Intent accuracy | 0.600 | 0.600 | +0.000 |
| Intent macro-F1 | 0.530 | 0.513 | -0.017 |
| Decision accuracy | 0.865 | 0.919 | +0.054 |
| **Reason-code accuracy** | **0.595** | **0.676** | **+0.081** |

Escalation, the metric this report says matters most:

| | 1 call (shipped) | 2 calls |
|---|---|---|
| Precision | 0.80 | **0.83** |
| Recall | 0.73 | **0.91** |
| Missed escalations | 3 | **1** |
| Escalation rate *(human: 30%)* | 27% | 32% |

Cost: **2 calls per message instead of 1** — double the latency and double the
quota against a free tier that is already the binding constraint.

## How the predictions did

| Predicted | Observed |
|---|---|
| Reason-code accuracy improves to **0.70+** | 0.595 → **0.676**. Right direction, short of the number |
| Intent and decision barely move | Intent held exactly (0.600 → 0.600). **Decision did not** — +0.054 |
| Reply quality flat or slightly better | **Not tested.** The judge was not run on these replies |

Two of three predictions were wrong in some part, and the third was never
checked. The write-up says so rather than quietly reporting only the metric that
moved the right way.

## The honest size of it

Everything above is 2 to 3 items:

- reason codes correct: **22 → 25** of 37
- decisions correct: **32 → 34** of 37

At n=37 that is not a result. The escalation recall CI on the shipped
configuration is already [0.45, 1.00]; a two-item move sits comfortably inside it.

## Does this recover the same failures the retrieval ablation did?

Mostly no, which is worth knowing. The shipped single call misses 3 escalations.

| Recovered by | Items |
|---|---|
| k=0 ablation | `2793198_2793197` (E2), `869926_869925` (E1) |
| two-stage | `2587912_2587911` (E3), `869926_869925` (E1) |
| **both** | `869926_869925` only |

So the two changes are **not** hitting a single shared bottleneck — each recovers
a different second item, and a "one call doing three jobs is the problem" story
would be overclaiming. But the one they share is
*"help i forgot my restrictions passcode"* — the credential reset this report
singles out as the worst miss in the set, the E1 case that must never be
automated. Two independent modifications both fix it, and neither was designed
to.

## Not adopted, for the same reason k=0 was not

This variant scores better on decisions, escalations and reason codes, and it has
a design argument the ablation does not: a justification produced *after* a fixed
verdict cannot be traded against that verdict to make the pair sound coherent,
which is exactly the auditability the brief asks for when it says "with a stated
reason".

That argument is good. The evidence for it is 3 items on the set whose errors
have already been read, and adopting an architecture because it wins on 40
inspected examples is the error this report spends a section warning about —
applying a looser standard to a change that flatters the system than to one that
embarrassed it would be worse than either. The recommendation stands and the
default does not move until n=150.
