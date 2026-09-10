# Decision log

Non-obvious choices and why. (Assignment asks for 10-15.)

<!-- Filled in as the build proceeds; trimmed to the least-obvious 15 at the end. -->

1. **Committed the LLM response cache to the repo.** The assignment caps
   reproduction at 15 minutes. Replaying hashed responses makes `make repro`
   run offline in ~1 minute and produce byte-identical numbers, and
   `CACHE_OFFLINE=1` turns a cache miss into a hard error so the committed
   numbers are provably the committed cache's.

2. **Google AI Studio free tier, not a paid API.** The assignment permits any
   LLM API or open model. Running on a free tier costs nothing and forced a
   design that is disciplined about call volume (every call cached, judge run
   once per system). The tradeoff is rate limits, absorbed by the disk cache.

3. **Agent model and judge model are different, but same family.** Gemini 2.5
   Flash drafts, 2.5 Pro judges. A judge that shares weights with the generator
   tends to reward its own stylistic habits. Using different sizes reduces but
   does not remove this; the residual bias is stated in the report's
   "misleading headline number" section rather than hidden. An independent-family
   judge (e.g. Claude Sonnet) would be the correct fix given a budget.


4. **Brand chosen by measurement, not volume.** Ranked candidates on inbound
   volume, reply ratio, and a measured DM-deflection rate
   (`results/brand_deflection.md`), then read 6 random real replies per finalist
   before committing. AppleSupport won on intent separability + a real
   historical-resolution pattern to ground in, not on being biggest.

5. **My own deflection metric was wrong, and the fix changed the reading.** The
   regex counted only DM-style handoffs, so AmazonHelp scored 0.7% deflection
   while its replies actually say "we can't access accounts on Twitter, please
   call us" -- deflection by another name. Reading raw samples caught it. The
   published table keeps the original numbers with this caveat attached rather
   than silently re-scoring.

6. **"Good" is defined as correct triage, not resolution.** Across every
   candidate brand, first replies on Twitter overwhelmingly ask a clarifying
   question, link a help resource, or hand off. An agent judged on "did it
   resolve the issue" would be measuring something this channel never does.
   The target is the brand's actual first-response behaviour.

7. **Scoped to conversation openers (73,859 of 102,086 pairs); multi-turn is an
   explicit non-goal.** 27.6% of inbound messages are mid-thread replies to the
   brand's own clarifying question -- "Yes it's updated to that one yesterday",
   "Can't even type that without errors". These have no standalone intent, and
   including them would have inflated an `other` class and made every metric
   look worse for a reason that has nothing to do with the agent. Handling them
   needs conversation state, which is the single biggest thing I chose not to
   build. The flag is kept in the data (`is_opener`) so the decision is
   reversible and auditable.

8. **Two-slice golden set instead of one.** A uniform random 198 would leave
   `account_access` with ~3 examples and an F1 that is pure noise; a purely
   stratified 198 would make every prevalence-sensitive metric a fiction. So
   both were drawn (100 natural + 98 targeted) and are reported separately. The
   natural slice carries the headline; the targeted slice is diagnostic only.

9. **Escalation reasons are fixed policy codes, not free text.** Free-text
   rationales drift over 198 items and cannot be aggregated. Codes (E1-E7,
   A1-A4) keep the labels internally consistent and let the report say which
   policy clause drove each escalation -- and let the agent be scored on
   whether it cited the *right* clause, not just the right verdict.

10. **Apple's historical reply is hidden during labelling.** Labelling while
    looking at Apple's actual response would encode Apple's behaviour as ground
    truth, converting the evaluation from "is the agent right" into "does the
    agent imitate Apple". Reveals are allowed but recorded per item so the
    effect is measurable rather than assumed away.

11. **dev/test split assigned before any label existed.** Assigning it after
    labelling would let item difficulty leak into the split.

12. **Hallucinated support URLs are measured, not just prompted away.** A
    five-message smoke test produced `https://support.apple.com/en-us/HT205754`
    -- a fabricated article link. Because cleaning rule 4 replaces every real URL
    with `<url>`, any `http` string in a generated reply is provably invented.
    That turns groundedness into an objective automated metric instead of
    something only the LLM judge can assess. The prompt was tightened AND the
    metric kept, because a prompt fix that is not measured is an assumption.

13. **One LLM call produces intent, reply and decision together.** They are not
    independent -- the escalation decision depends on the intent and the reply
    depends on both -- and three calls would triple the load against a free-tier
    quota. Cost of the choice: a single bad parse loses all three outputs, which
    is why the call is schema-constrained rather than prompted for JSON.

14. **TF-IDF retrieval (word 1-2 grams + char 3-5 grams), not embeddings.**
    73k documents through a free-tier embedding API is hours of rate-limited
    calls for a component the assignment is not testing. Char n-grams also
    handle this corpus's misspellings and "ios11"/"iOS 11" variation well. It is
    deterministic and fully explainable live. Stated tradeoff: probably some
    recall loss on paraphrases with no lexical overlap.

15. **Golden-set pair_ids are excluded from the retrieval index.** Without this
    the drafter retrieves the exact message being evaluated along with Apple's
    real reply, and every groundedness number becomes meaningless.

16. **A 20-item pilot preceded the full labelling run, and it changed the
    taxonomy.** The pilot showed my own prose definitions were not
    human-applicable: one bug got three different labels, and five items got an
    intent that contradicted their own reason code. Three definitions were
    replaced with mechanical tests (R1 update-mentioned, R2 classify-by-issue,
    R3 any-disputed-charge). Finding this at item 20 rather than item 198 saved
    the golden set; shipping the original definitions would have produced a
    metric measuring my prose rather than the agent.

17. **The v1 pilot labels are kept rather than overwritten.** The v1-vs-v2
    disagreement on those 20 items quantifies how much of the labelling noise
    came from the definitions instead of the labeller, and it is honest evidence
    that the taxonomy was revised for a stated reason rather than to raise a
    number.

18. **The agent prompt and the human labelling UI share one source of truth.**
    `DISAMBIGUATION_RULES` is injected into both. Scoring a model against rules
    it was never given measures documentation drift, not capability.

19. **Golden set built by rule-seeded verification, with the shortcut measured
    rather than hidden.** Hand-labelling 198 items was ~2 hours; verification is
    ~40 minutes. The obvious risk is that verification is biased toward
    accepting whatever is already on screen. Rather than assert the bias is
    small, 40 randomly chosen items (frozen seed) are labelled BLIND and shown
    FIRST, before the reviewer has seen any pre-label. Comparing pre-labeller
    accuracy on those 40 against the acceptance rate on the other 158 estimates
    the anchoring effect directly. That number goes in the misleading-headline
    section because every metric on the verified subset inherits it.

20. **The pre-labeller is keyword rules, not the agent and not the simple
    baseline.** Seeding with the agent would make the golden set agree with the
    system under evaluation by construction. Seeding with the same keyword rules
    the simple baseline used would inflate that baseline instead -- so the simple
    baseline was changed to LEARN escalation, leaving the keyword rules used
    only for pre-labelling.

21. **Judge model switched from gemini-3.8-flash to gemini-3.6-flash mid-run.**
    3.8 returned HTTP 503 "high demand" often enough to exhaust the retry budget
    and kill an evaluation run; 3.6 tested 3/3 reliable. The judge is still a
    different and larger model than the agent (3.1-flash-lite). Free-tier
    availability, not capability, drove this -- worth stating because it means
    the judge model is not the one a paid deployment would choose.

22. **Retry policy distinguishes 503 from 429.** "High demand" on the free tier
    persists for minutes, so it gets a 180s backoff ceiling against 60s for a
    plain rate limit. Without this the harness fails on transient capacity
    rather than on anything about the systems being measured.

23. **Judge model settled on gemini-3.5-flash after burning two others' daily
    quota.** 3.8-flash returned persistent 503s; 3.6-flash was then exhausted by
    my own mistake -- a 6-worker concurrency experiment on a rate-limited free
    tier produced 42 retries, zero completed calls, and a 429 daily quota block.
    The lesson is recorded because it is a real property of building on a free
    tier: the binding constraint is request RATE, and concurrency above it makes
    throughput strictly worse. Final settings: 3 workers behind a global 6.5s
    interval (~9 req/min). The judge remains a larger, different model than the
    agent (3.1-flash-lite).
