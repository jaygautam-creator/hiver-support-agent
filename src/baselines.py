"""
Two baselines, per the assignment: one trivial, one simple. Both cover all
three tasks, because "results vs. two baselines" is meaningless if the baselines
only exist for the easiest task.

TRIVIAL -- the "do nothing intelligent" floor:
    intent    always the majority class
    reply     one fixed canned message
    decision  always auto-handle (i.e. deploy with no humans at all)
  Its purpose is to expose how much of any headline number is just class
  imbalance. On a support corpus this floor is embarrassingly high.

SIMPLE -- what a competent engineer builds in an afternoon, no LLM:
    intent    TF-IDF + logistic regression, trained on the 50 dev labels
    reply     1-nearest-neighbour: return Apple's ACTUAL historical reply to the
              most similar past message, verbatim
    decision  TF-IDF + logistic regression on the escalate/auto label
  The 1-NN reply baseline is the important one. The agent's whole claim is that
  it grounds replies in Apple's history; this baseline IS Apple's history,
  copied. If the LLM cannot beat literal copy-paste, that is the finding.
"""
import re
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from src.config import SEED
from src.retrieve import Retriever

CANNED = ("Thanks for reaching out. We'd like to help with this. "
          "Please DM us with more details so we can take a closer look.")

# NOTE: these keyword rules are used ONLY by scripts/prelabel.py to seed the
# human verification pass. They are deliberately NOT used by SimpleBaseline.
# If the golden labels were seeded by these rules and the baseline also escalated
# by these rules, the baseline would agree with the golden set by construction
# and its escalation numbers would be inflated for a reason unrelated to skill.
PRELABEL_RULES: list[tuple[str, str]] = [
    ("E4", r"\b(burn|burnt|burning|swell|swollen|explod|fire|smoke|melted|shock(ed)?)\b"),
    ("E1", r"\b(hack|hacked|compromis|locked out|lock(ed)? me out|stolen account|"
           r"can'?t (log ?in|sign ?in)|forgot(ten)? (my )?password|reset (my )?password|"
           r"apple id|two.factor|2fa)\b"),
    ("E5", r"\b(lost (all )?(my )?(photo|data|file|contact|backup)|deleted everything|"
           r"gone forever|wiped)\b"),
    ("E2", r"\b(refund|charged|charge|billed|billing|subscription|receipt|money back|"
           r"unauthori[sz]ed (charge|purchase))\b"),
    ("E3", r"\b(repair|warrant|genius bar|apple store|replace(ment)?|cracked|"
           r"screen (broke|shatter)|service cent)\b"),
    ("E6", r"\b(switch(ing)? to (android|samsung)|never buying|lawyer|legal|sue|"
           r"trading standards|ombudsman|press|journalist)\b"),
]


@dataclass
class BaselineOutput:
    intent: str
    decision: str
    reason: str
    reason_text: str
    reply: str


class TrivialBaseline:
    """Majority intent, canned reply, never escalate."""

    name = "trivial"

    def __init__(self, majority_intent: str):
        self.majority = majority_intent

    def run(self, message: str) -> BaselineOutput:
        return BaselineOutput(
            intent=self.majority,
            decision="auto",
            reason="A4",
            reason_text="Trivial baseline auto-handles everything.",
            reply=CANNED,
        )


class SimpleBaseline:
    """TF-IDF logistic regression + 1-NN reply + keyword escalation rules."""

    name = "simple"

    def __init__(self, train: pd.DataFrame, retriever: Retriever):
        self.retriever = retriever
        self.clf = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                            strip_accents="unicode"),
            LogisticRegression(max_iter=2000, class_weight="balanced",
                               random_state=SEED),
        )
        self.clf.fit(train["customer_text"], train["intent"])

        # Escalation is learned too, not keyword-matched -- see PRELABEL_RULES.
        self.dec_clf = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                            strip_accents="unicode"),
            LogisticRegression(max_iter=2000, class_weight="balanced",
                               random_state=SEED),
        )
        self.dec_clf.fit(train["customer_text"], train["decision"])

    def _decide(self, message: str) -> tuple[str, str]:
        return str(self.dec_clf.predict([message])[0]), "-"

    def run(self, message: str) -> BaselineOutput:
        intent = self.clf.predict([message])[0]
        decision, code = self._decide(message)
        nn = self.retriever.query(message, k=1)[0]
        return BaselineOutput(
            intent=intent,
            decision=decision,
            reason=code,
            reason_text="Learned TF-IDF classifier; this baseline cites no policy clause.",
            reply=nn.brand_reply,   # Apple's real historical reply, verbatim
        )
