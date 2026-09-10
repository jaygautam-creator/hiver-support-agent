# Choosing an operating point

The report says escalation costs are asymmetric and then never uses the asymmetry. Precision and recall are not the answer to "should we deploy this" -- they are inputs to a cost question whose other input is a business number this repo does not contain.

Let **R** = (cost of a missed escalation) / (cost of a false escalation). Expected cost per **1,000 inbound messages** at the **natural-slice** escalation prevalence of **21%** (n=24), in units of one false escalation (≈ two minutes of agent time). The pooled golden set reads 30%, but that includes the targeted slice, which over-samples escalation-flavoured messages by design — using it would inflate every row here while looking like a deployment estimate:

| System | R=1 | R=2 | R=5 | R=10 | R=20 | R=50 | R=100 |
|---|---|---|---|---|---|---|---|
| agent | 125 | 167 | 292 | 500 | 917 | 2,167 | 4,250 |
| simple | 250 | 458 | 1,083 | 2,125 | 4,208 | 10,458 | 20,875 |
| trivial | 208 | 417 | 1,042 | 2,083 | 4,167 | 10,417 | 20,833 |
| agent (k=0, not shipped) | 83 | 83 | 83 | 83 | 83 | 83 | 83 |

`trivial` and `simple` escalate nothing, so their cost is purely R × every escalation that exists — the "deploy no triage at all" column.

## What this changes

**The agent beats escalating nothing at every R tested (R=1, R=2, R=5, R=10, R=20, R=50, R=100).** 

**The k=0 ablation is cheaper at every tested R, and there is no crossover.** Same false escalations (2 vs 2), fewer misses (0 vs 1), so it dominates the shipped configuration at *any* cost ratio. Its row is flat because it misses nothing on this slice, so its cost does not grow with R at all.

**That flat row rests on one message.** The natural slice holds 5 gold escalations; k=5 misses one of them and k=0 misses none. A single item is not a dominance result, and this table would look completely different if that one message had gone the other way. A crossover would have been the more useful outcome — it would have made this a business question with a real answer. What is actually here is a hint, at n=24, that retrieval is not paying for itself, and not enough evidence to act on.

## What this does not license

Every count here comes from **n=24** with **5** gold escalations. The escalation recall CI is [0.45, 1.00]; propagating that through these costs would produce intervals wider than the differences between the rows. This table shows the *shape* of the decision and which input is missing. It does not show which system to deploy, and it is not used to pick one.

The missing input is a real cost ratio. For a support channel, R is usually estimated from the value of a retained customer against a loaded agent-minute — it is a number a support organisation already has, and it belongs in the config, not in a model.