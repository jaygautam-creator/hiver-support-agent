# Second annotator: an independent model relabels the golden set

Annotator model: `gemma-4-31b-it` — a **different model family** from both the agent (`gemini-3.1-flash-lite`) and the judge (`gemini-3.5-flash-lite`), so agreement here is not an artifact of shared lineage.

## This is not a human agreement study

The brief asks for human agreement, and this is not it. Two raters reading the same written definitions can agree perfectly and both be wrong; nothing below shows the human labels are *correct*. `golden/human_judge.jsonl` is still unfilled and the gap is still open in the README.

What this measures is **how unambiguous the taxonomy is**. The annotator got exactly what the human got — same definitions, same disambiguation rules, same policy codes, Apple's reply withheld, no retrieved examples, no reply to draft. So a disagreement points at the *definitions*, not at either rater.

**n = 40** items (every golden item carrying a human intent)

| Field | Agreement | Cohen's kappa | Notes |
|---|---|---|---|
| intent (7 classes) | 60% | 0.43 | macro-F1 vs human 0.36 |
| decision (auto/escalate) | 90% | 0.77 | n=39 with a human decision |
| policy reason code | 62% | — | n=37, exact code match |

kappa < 0.4 poor, 0.4–0.6 moderate, 0.6–0.8 substantial, > 0.8 near-perfect.

## Reading this

- Intent kappa of **0.43** is only moderate. The definitions are not yet tight enough for two readers to apply them the same way, so some of the agent's measured intent error is definitional rather than a model failure. The confusions below say which boundaries leak.
- Escalation kappa of **0.77**: the escalate/auto boundary is the more reproducible of the two judgements, which is consistent with it being driven by explicit policy codes rather than prose definitions.
- The two raters agree on *whether* to escalate (90%) more often than on *why* (62%). Several policy codes are therefore describing overlapping situations — a codebook problem, and a real one, since the report attributes escalations to specific clauses.

## Where the two readings diverge

| Human said | Annotator said | n |
|---|---|---|
| other | software_bug | 3 |
| feedback_or_complaint | software_bug | 2 |
| feedback_or_complaint | how_to | 2 |
| software_bug | hardware_or_repair | 2 |
| feedback_or_complaint | billing_or_purchase | 1 |
| hardware_or_repair | feedback_or_complaint | 1 |
| software_bug | feedback_or_complaint | 1 |
| account_access | hardware_or_repair | 1 |
| account_access | billing_or_purchase | 1 |
| software_bug | how_to | 1 |

## By slice

| Slice | n | Intent agreement |
|---|---|---|
| natural | 24 | 71% |
| targeted | 16 | 44% |

## Re-review queue (16 items)

These are items where an independent reader of the same rules chose differently. They are **candidates for human re-review**, not corrections — the annotator has no authority over the human label. Re-reviewing them would be a second pass on the hardest items rather than on a random sample.

- `2212895_2212894` [natural] needs to get their shit together. Not about to go through Googling a tutorial on how to set up some keyboard shortcut to fix my keyboard. THIS PHONE W
    - human:     feedback_or_complaint / auto / A4
    - annotator: software_bug / escalate / E3
- `2077143_2077141` [targeted] OMG @user how can I go back to 10.3??!!? iOS11 is complete dog shit!!
    - human:     feedback_or_complaint / auto / A2
    - annotator: how_to / auto / A1
- `596931_596930` [targeted] Why does my iPad keep doing this 😭 <url>
    - human:     other / auto / A4
    - annotator: software_bug / auto / A2
- `1185047_1185045` [targeted] hi there every time I update Instagram and close the App Store and go back latter it wants to update again :/
    - human:     feedback_or_complaint / auto / A4
    - annotator: software_bug / auto / A2
- `962244_962243` [natural] Hello @user - Why macOS Sierra no longer appears in the “my purchases” section ?
    - human:     feedback_or_complaint / auto / A4
    - annotator: billing_or_purchase / escalate / E2
- `2794378_2794377` [targeted] so you make your own format but your own program won’t read it. That’s awesome, props for the thoughtfulness 😂 so all my story was to ask:please imple
    - human:     hardware_or_repair / auto / A2
    - annotator: feedback_or_complaint / auto / A4
- `1779942_1779941` [natural] wtf ? It's impossible to process an address change @user or for them to figure out how to fix it ? I cannot handle incompetence from a company that sa
    - human:     software_bug / auto / A2
    - annotator: feedback_or_complaint / auto / A4
- `2793198_2793197` [targeted] apenas compré el #Iphone8 en @user y falla muy seguido, se traba y no responde, trato de tomar fotos y la cámara aparece en negro, me llaman y no pued
    - human:     account_access / escalate / E2
    - annotator: hardware_or_repair / escalate / E3
- `1128253_1128252` [natural] nunca me ha pasado algo así en Apple. Me compro una funda de iPhone, me dura dos meses y en el AppleStore me dicen que es así.
    - human:     software_bug / auto / A2
    - annotator: hardware_or_repair / escalate / E3
- `39617_39616` [targeted] as fotos e vídeos do meu telefone não carregam mais.. como resolvo?
    - human:     other / nan / nan
    - annotator: software_bug / auto / A2
- `903665_903664` [natural] Hey @user how do I make the touchbar on a MBP permanently show the original keys that the touchbar replaces? I don't want touchbar.
    - human:     feedback_or_complaint / auto / A4
    - annotator: how_to / auto / A1
- `1130507_1130505` [natural] Hi there,I have got an iPhone 6 which has stopped working therefore,would it be possible to swipe it with a brand-new one.Thnx
    - human:     software_bug / auto / A2
    - annotator: hardware_or_repair / escalate / E3
- `2332386_2332385` [targeted] o que tá acontecendo com a bateria do meu celular depois do iOS 11.0.3?? Me explica por favor
    - human:     other / auto / nan
    - annotator: software_bug / auto / A2
- `2295702_2295700` [targeted] Dammit @user why can’t I just buy an unlocked iPhone X without having to check my phone contract? That won’t work when you are on a prepaid phone serv
    - human:     account_access / escalate / E1
    - annotator: billing_or_purchase / escalate / E2
- `2119362_2119360` [natural] ،، While I’m using IOS 11.1 Is it safe to go for IOS 11.3 update? @user 😊
    - human:     software_bug / auto / A2
    - annotator: how_to / auto / A1
- `2587912_2587911` [targeted] While updating to high Sierra we lost the Boot sector. How to repair that? Any Ideals?
    - human:     hardware_or_repair / escalate / E3
    - annotator: software_bug / escalate / E5
