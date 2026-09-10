# Ablation: does retrieval do anything?

The same agent, prompt, model and temperature over the same **40** golden items, with **k=0** — no historical examples, taxonomy and policy only. The prediction was written into `scripts/ablate_retrieval.py` before the run.

| Metric | k=5 (shipped) | k=0 (no retrieval) | Δ |
|---|---|---|---|
| Intent macro-F1 | 0.530 | 0.556 | +0.026 |
| Intent accuracy | 0.600 | 0.625 | +0.025 |
| Escalate precision | 0.80 | 0.83 | +0.03 |
| Escalate recall | 0.73 | 0.91 | +0.18 |
| Missed escalations | 3 | 1 | -2 |
| Reason-code accuracy | 0.595 | 0.622 | +0.027 |
| **Fabricated URLs** | **0%** | **0%** | +0pp |
| Judge groundedness (n=20) | 2.75 | 2.70 | -0.05 |

Intent changed on **6 of 40** items; decision changed on **2**.

## All three predictions failed

| Predicted | Observed |
|---|---|
| Intent and escalation barely move | Intent barely moved (+0.03). **Escalation recall moved +0.18** — the opposite of "barely" |
| Groundedness drops clearly | Moved −0.05. No meaningful change |
| Fabricated URLs appear | **0% in both arms** |

**Removing the retrieval component improved every headline metric except
groundedness, which did not move.** Recall went 0.73 → 0.91 and missed
escalations 3 → 1.

**How much of that is real?** The recall delta is +0.182, 95% CI [+0.00, +0.45]
by paired bootstrap over the 11 gold escalations — it does not cross zero, but
its lower bound is zero, and the whole effect is **two items**:

- `2793198_2793197` — gold `escalate`, k=5 said `auto`, k=0 said `escalate`
- `869926_869925` — gold `escalate`, k=5 said `auto`, k=0 said `escalate`

Two items is not a result. It is a signal worth chasing on a bigger golden set,
and it is stated that way here rather than as a finding.

## The mechanism this points at

It is the same one already recorded as failure mode 3: *"Apple publishes an
article for this, and the retrieved examples show Apple linking it, so the agent
grounds correctly and escalates wrongly. Grounding and policy conflict, and
grounding wins."*

The ablation is what that hypothesis predicts. Remove the examples, the policy
stops competing with evidence of Apple self-serving the case, and the two
recovered escalations are exactly the shape the hypothesis describes. This is the
first evidence for a mechanism the report had only asserted.

Two more things fell out:

**The URL discipline is instructional, not grounding-based.** 0% fabricated URLs
survives k=0 intact. The prompt's explicit "NEVER write a URL — write `<url>`"
rule is doing that work by itself; the report previously implied the grounding
examples were what kept it honest. k=0 still writes the literal `<url>` token,
just less often (13 of 40 vs 19).

**Retrieval was suppressing the customer's language.** For the Spanish message
`1128253_1128252`, k=5 replied in English because every retrieved example was
English; k=0 replied in Spanish. That is a straightforward regression caused by
retrieval, and it interacts with the `other`/non-English taxonomy defect already
in the report.

## What is NOT being done about it

**The shipped default stays k=5.** k=0 scores better on these 40 items, and that
is precisely why it is not being adopted: this is the evaluation set, its errors
have already been read, and switching the architecture to whatever wins on 40
already-inspected examples is the same mistake as tuning a threshold on the test
set. The honest version of this decision needs the finished 150-item golden set,
where the 29 test items were not used to pick the configuration.

What would justify the switch: the same ablation on the full set, with the
recall CI clear of zero, and a groundedness check that does not rely on a judge
measured at 67% test-retest stability.


## Two replies, side by side


**iOS 11.0.03 is the worst I’ve ever seen. My battery literally went down 3% while typing this tweet. Drops WiFi**

- k=5: We know how important it is to have a reliable connection and battery life. Which iPhone model are you using, and have you tried restarting the device to see if that helps? Let us know in a DM.
- k=0: We would like to look into this with you. To start, which iPhone model are you using, and have you had a chance to restart your device since noticing these issues? <url>

**nunca me ha pasado algo así en Apple. Me compro una funda de iPhone, me dura dos meses y en el AppleStore me d**

- k=5: We would like to look into this with you. Please send us a DM so we can discuss your experience at the Apple Store further.
- k=0: Lamentamos escuchar sobre tu experiencia en la Apple Store. Nos gustaría revisar esto contigo. Por favor, envíanos un mensaje directo para poder ayudarte mejor.

**Hi there,I have got an iPhone 6 which has stopped working therefore,would it be possible to swipe it with a br**

- k=5: We want to help with your iPhone. Since your device is not working, we will need to look into your repair options. Please reach out to us via DM so we can assist you further.
- k=0: I am sorry to hear your iPhone is no longer working. I would like to look into your repair options with you. Please send us a DM to get started. <url>