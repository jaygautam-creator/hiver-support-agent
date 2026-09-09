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
ESCALATION_POLICY = """
ESCALATE to a human when ANY of these hold:
  E1. Account security or identity -- compromised account, lockout, password
      reset. Identity cannot be verified over public Twitter.
  E2. Money is in dispute -- a charge, refund, or subscription the customer
      wants changed on their account.
  E3. Physical hardware fault, warranty, or repair -- needs inspection, a
      service record, or a store.
  E4. Safety signal -- overheating, swelling, burning, or any injury risk.
  E5. Data loss -- photos, backups, or files reported gone.
  E6. Severe dissatisfaction or churn threat -- explicit intent to leave, legal
      language, press mention, or sustained abuse.
  E7. The message is unintelligible or the agent's own confidence is low.

AUTO-HANDLE otherwise, which in practice means:
  A1. how_to questions answerable with public instructions.
  A2. Known software bugs where the brand's historical reply is an
      acknowledgement plus a version check.
  A3. A software fault where the historical first response is a standard
      diagnostic question (which iOS version, which device).
  A4. General feedback with no actionable fault.
"""
