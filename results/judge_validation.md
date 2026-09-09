# Judge validation (no human agreement study)

The assignment asks for evidence that the judge agrees with a human. A blind human scoring pass was **not run** -- see README *Deviations*. These four automated checks are a weaker substitute, reported as such.


## A. Synthetic defect detection

8 real agent replies, each corrupted four ways (32 judged variants). Ground truth known by construction.

| Injected defect | Targeted dimension | Caught | Mean score on that dimension |
|---|---|---|---|
| credential_request | safety flag | 100% | - |
| dismissive | tone | 100% | 1.00 |
| fabricated_url | groundedness | 88% | 1.62 |
| wrong_action | action | 100% | 1.00 |

## B. Human-anchored ACTION check

For messages a **human** labelled `escalate`, a reply that instead auto-handles them is the wrong first move and should score low on ACTION. This is the only check here anchored to real human judgement.

- replies that correctly escalated (n=5): mean ACTION **3.00**
- no missed escalations landed in the judged subsample

## C. Test-retest stability

Rescored 12 replies with the grounding examples reordered (same content, different order).

- identical overall score: **92%**
- mean absolute difference: **0.028** on a 1-3 scale

## D. Length bias

Spearman correlation between reply length and judge mean score across all 60 judged replies: **rho = 0.18**.
A strongly positive rho would mean the judge rewards verbosity rather than quality.

## Verdict

**85% of all judged replies scored >= 2.9 out of 3.**

The judge reliably detects *gross* defects -- fabricated links, credential requests, obviously wrong actions. It does **not** discriminate between adequate and good replies: in the main results a single constant canned message scores 2.95 against the agent's 2.98. Reply-quality differences in this report are therefore **not supported by the judge**, and the rubric needs either harsher anchors or forced pairwise comparison before any such claim can be made.