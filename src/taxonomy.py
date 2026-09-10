"""
The intent taxonomy, written by hand after reading results/taxonomy_derivation.md.

Design rules I held myself to:
  * Small. Eight classes including `other`. More classes means a thinner golden
    set per class and a confusion matrix nobody can read.
  * Actionable. Two intents are only separate if the brand DOES something
    different about them. `post_update_degradation` and `software_bug` look
    similar but get different first responses (diagnostics vs acknowledgement),
    so they are split. That split is also the confusion pair I expect to be
    worst, which is a prediction the evaluation can falsify.
  * Mutually exclusive by a stated priority order, because real messages carry
    two intents ("my phone broke after the update AND I can't log in").

What the clustering did NOT give me: the clusters split by vocabulary, not
intent. Clusters 6, 10 and 12 are all one intent (the iOS 11 "I" -> "?"
autocorrect bug) separated only by phrasing; clusters 0, 5, 7 and 13 are all
post-update degradation. That is why the taxonomy is not k classes.
"""

INTENTS: dict[str, dict] = {
    "software_bug": {
        "definition": "RULE: something in Apple software is broken, misbehaving, "
                      "or degraded -- including after an update. Classify by the "
                      "underlying issue, never by grammatical form: 'how do I fix "
                      "this broken thing' is a bug report, not a how-to.",
        "includes": "the 'I' -> '?' autocorrect bug in every phrasing, Mail "
                    "crashing on search, Control Center not turning off Wi-Fi, "
                    "battery drain and slowness after an iOS update",
        "excludes": "nothing is broken, they just want to know how to use a "
                    "feature (-> how_to); physical damage (-> hardware_or_repair)",
        "example": "Mail app on iOS is crashing constantly when searching emails. "
                   "I can reproduce the bug easily.",
    },
    "how_to": {
        "definition": "RULE: nothing is broken. The customer wants to know how to "
                      "use a feature, where a setting lives, or whether something "
                      "is possible. If anything is malfunctioning, it is NOT this "
                      "class even when phrased as 'how do I fix...'.",
        "includes": "how do I attach a PDF, where is the Reply with Message "
                    "toggle, how to reset RAM on iPhone X, can I downgrade iOS",
        "excludes": "anything reported as broken or misbehaving "
                    "(-> software_bug / post_update_degradation)",
        "example": "how and where can i change my apple watch's name that "
                   "appears on my iphone?",
    },
    "account_access": {
        "definition": "Cannot get into, or has lost control of, an Apple ID / "
                      "iCloud account. Includes compromise, password reset, "
                      "2FA lockout, and account-security concerns.",
        "includes": "account hacked, forgot Apple ID password, can't accept "
                    "iCloud terms, locked out, unauthorised access",
        "excludes": "charges on an account the customer can still access "
                    "(-> billing_or_purchase)",
        "example": "my @user account has been hacked for MONTHS!! So much money stolen.",
    },
    "hardware_or_repair": {
        "definition": "Physical device fault, damage, warranty, repair, "
                      "replacement, or an Apple Store / service-centre experience.",
        "includes": "screen fault, paint chipping, EarPods warranty, repair "
                    "denied, replacement device also broken, Genius Bar complaint",
        "excludes": "software-caused misbehaviour on undamaged hardware",
        "example": "1 of the service centers just completely denied to "
                   "repair/replace a 33 day old under warranty phone!",
    },
    "billing_or_purchase": {
        "definition": "RULE: money is involved. Any unwanted, accidental, "
                      "unrecognised or disputed charge is this class and always "
                      "escalates (E2) -- including 'my phone bought something on "
                      "its own'. Also covers pre-sale questions about buying.",
        "includes": "charged twice, accidental purchase, phone bought an album "
                    "by itself, cancel subscription, refund request, "
                    "'thinking of buying an iPhone, will X work?'",
        "excludes": "warranty cost disputes tied to a repair (-> hardware_or_repair)",
        "example": "I'm thinking of buying an iPhone and I was wondering if "
                   "watching shows I've downloaded from iTunes is possible?",
    },
    "feedback_or_complaint": {
        "definition": "Brand criticism, frustration, or a feature request with "
                      "no specific diagnosable problem to act on. The customer "
                      "is expressing, not asking.",
        "includes": "'this update is trash', 'why can't we sort Messages like "
                    "Twitter', threats to switch to Android, general rants",
        "excludes": "an angry message that still names a specific fault -- "
                    "anger is not an intent, classify by the underlying issue",
        "example": "As much as I love Apple I'm about to switch. Get it together.",
    },
    "other": {
        "definition": "Non-English, unintelligible, spam, off-topic, or "
                      "context-free fragments with no recoverable intent.",
        "includes": "non-English messages, pure emoji, '@AppleSupport' with a "
                    "bare link and no text, replies aimed at another user",
        "excludes": "anything where an intent is recoverable with effort",
        "example": "Hi apple @user @user @user @user @user <url>",
    },
}

# Applied top-down when a message carries more than one intent. Ordered by
# customer cost of getting it wrong: a locked account or a broken device left
# sitting in a bug-report queue is a worse outcome than the reverse.
PRIORITY: list[str] = [
    "account_access",
    "hardware_or_repair",
    "billing_or_purchase",
    "software_bug",
    "how_to",
    "feedback_or_complaint",
    "other",
]

# These three rules exist because a 20-item labelling pilot showed the original
# prose definitions could not be applied consistently BY A HUMAN: the same iOS 11
# autocorrect bug was labelled software_bug, how_to and other in one sitting, and
# five messages were given intent `software_bug` with reason code A3
# ("post-update diagnostic"), which contradicts itself. A boundary a careful
# human cannot apply repeatably puts a hard ceiling on any classifier, and the
# resulting metric measures the definition rather than the system. Each rule
# replaces a judgement call with a mechanical test.
DISAMBIGUATION_RULES = """
R1. SOFTWARE PROBLEMS ARE ONE CLASS. Anything broken, misbehaving or degraded
    in Apple software is software_bug, whether or not an update is blamed. An
    earlier taxonomy split these into software_bug vs post_update_degradation;
    blind labelling used the post-update class 0 times in 40, so the boundary
    was removed rather than enforced.

R2. CLASSIFY BY ISSUE, NOT PHRASING. "How do I fix <broken thing>" is a bug
    report, not a how_to. how_to requires that nothing is malfunctioning.

R3. ANY DISPUTED CHARGE IS BILLING. Unwanted, accidental or unrecognised
    charges -- including "my phone bought it by itself" -- are
    billing_or_purchase and escalate under E2.
"""

LABELS: list[str] = list(INTENTS.keys())

# --- Escalation policy ----------------------------------------------------
# Deliberately written as an explicit, auditable policy rather than left to the
# model's judgement, because "should a human take this" is a business decision,
# not a language-understanding one. The model applies this policy; it does not
# invent it.
#
# Asymmetry that drives the whole design: wrongly auto-handling an angry
# customer with a real problem is far more costly than wrongly escalating an
# easy one. The first loses a customer; the second costs an agent two minutes.
#
# v2 (2026-09-10). v1 was measured and failed: an independent annotator applying
# the same written text reached Cohen's kappa 0.08 with the human on
# escalate/auto -- chance -- and escalated 82% of messages against the human's
# 28%. 19 of the 24 disagreements were a single pair of codes. v1's E7 ended
# "...or the agent's own confidence is low", so a conscientious reader reached
# for it whenever unsure; v1's E6 fired on "severe dissatisfaction or sustained
# abuse" over a corpus of angry profane tweets; and the auto side had no
# positive criteria at all, only "AUTO-HANDLE otherwise". Seven ways out and no
# way to stay. v2 deletes E7, gives E6 a mechanical test, gives every auto case
# a positive code, and states an application order. The codes the human actually
# used (A2, A4, E1, E2, E3) keep their exact meaning so round-1 labels stay
# comparable -- which is why there is a gap at A3 rather than a tidy renumber.
# Evidence: results/second_annotator_v1.md (v1) vs results/second_annotator.md
# (v2, same 40 items, same annotator model).
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

RETIRED -- never assign these:
  A3. "Post-update standard diagnostic". Dead since R1 merged
      post_update_degradation into software_bug; it duplicates A2, and the
      labelling pilot had already produced five self-contradictory
      software_bug + A3 rows.
  E7. "Unintelligible or the agent's own confidence is low". Deleted. Low
      confidence is not a trigger; unintelligible messages are A5.
"""

# The codes an output may carry. A3 and E7 are deliberately absent: they are
# retired, and leaving them in an enum is an invitation to keep assigning them.
ESCALATE_CODES: list[str] = ["E1", "E2", "E3", "E4", "E5", "E6"]
AUTO_CODES: list[str] = ["A1", "A2", "A4", "A5"]
REASON_CODES: list[str] = ESCALATE_CODES + AUTO_CODES
