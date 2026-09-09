# Anchoring measurement

**Blind items:** 40  |  **Verify items:** 158

| Field | Pre-labeller accuracy (blind, A) | Acceptance rate (verify, B) | Anchoring (B-A) |
|---|---|---|---|
| intent | 32.5% | 94.9% | **+62.4%** |
| decision | 77.5% | 97.5% | **+20.0%** |

A positive gap means labels on the verified items were accepted more often than the pre-labeller is actually right -- i.e. the reviewer was anchored. Every metric computed on the verified subset inherits this bias, and it flatters any system whose errors resemble the pre-labeller's.

Mitigation already in place: the pre-labeller is a keyword rule set, independent of both the Gemini agent (so no self-consistency loop) and of the simple baseline (which learns escalation rather than matching keywords).

## Time per item

| mode   |   median_seconds |
|:-------|-----------------:|
| blind  |             13.2 |
| verify |             13.3 |