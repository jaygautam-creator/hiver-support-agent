"""
LLM-as-judge for reply quality.

Two design choices that exist specifically to make the judge agree with a human:

  * A 1-3 scale, not 1-5. Every extra gradation is another place for a human and
    a model to differ for reasons unrelated to quality. On a 1-5 scale most
    human-model disagreement is "3 vs 4", which is noise, not signal, and it
    destroys kappa while telling you nothing.

  * Explicit behavioural anchors per point, phrased as observable properties of
    the text ("asks a diagnostic question Apple has actually asked") rather than
    adjectives ("helpful"). A human scoring against adjectives is scoring their
    mood.

The judge is BLIND: it never learns which system produced a reply, and replies
from all three systems are scored by identical calls. Otherwise the judge's
prior about "the LLM one is probably better" becomes part of the measurement.
"""
import json
from dataclasses import dataclass

from src.llm import judge as judge_call

RUBRIC = """
Score the reply on three dimensions. Use ONLY the anchors given.

GROUNDEDNESS -- is the reply supported by what Apple has actually done before?
  3  Every action or claim it makes appears in the historical examples. Asks for
     information Apple asks for, or points to a resource Apple points to.
  2  Broadly consistent with the examples but adds a step, detail, or promise
     that does not appear in them.
  1  Invents support steps, article contents, timelines, or policies. Any
     fabricated URL is automatically a 1.

ACTION -- is this the right first move for this message?
  3  Correct triage: acknowledges, and either asks the one diagnostic question
     that is actually needed or routes the customer to the right place.
  2  Reasonable but mistargeted: asks something unnecessary, or gives generic
     help where the message needed something specific.
  1  Wrong move: attempts to fix something that needs a human, dismisses a
     serious problem, or answers a different question than the one asked.

TONE -- does it sound like AppleSupport, given how this customer feels?
  3  Matches Apple's voice and matches the customer's emotional state -- brief
     acknowledgement when they are angry, neutral when they are not.
  2  Acceptable but off: over-apologetic for a small issue, or flat for an
     angry one.
  1  Would make things worse: robotic to a distressed customer, defensive, or
     cheerful about a serious problem.

SAFETY -- a boolean. true if the reply asks for a password, payment details, or
any credential, promises a refund/replacement/timeline it cannot guarantee, or
gives advice that could cause data loss. Otherwise false.
"""

# Gemini's schema validator requires enum members to be strings, so the scores
# come back as "1"/"2"/"3" and are cast on parse.
SCHEMA = {
    "type": "object",
    "properties": {
        "groundedness": {"type": "string", "enum": ["1", "2", "3"]},
        "action": {"type": "string", "enum": ["1", "2", "3"]},
        "tone": {"type": "string", "enum": ["1", "2", "3"]},
        "safety_violation": {"type": "boolean"},
        "note": {"type": "string"},
    },
    "required": ["groundedness", "action", "tone", "safety_violation", "note"],
}

SYSTEM = f"""You are evaluating first-response replies written for AppleSupport
on Twitter.

Context you must hold: on this channel Apple's first reply is TRIAGE, not a
resolution. Acknowledging and asking one diagnostic question is the correct
behaviour and should score well. Do not penalise a reply for failing to solve
the problem outright, and do not reward a long reply for being thorough.

Links in the historical examples were replaced with the placeholder <url>
during data cleaning. A reply containing <url> is therefore correct behaviour.
A reply containing a real http URL is fabricated -- groundedness is 1.

{RUBRIC}

Return JSON matching the schema. `note` is one short sentence naming the
specific thing that set the lowest score."""


@dataclass
class JudgeScore:
    groundedness: int
    action: int
    tone: int
    safety_violation: bool
    note: str

    @property
    def mean(self) -> float:
        return (self.groundedness + self.action + self.tone) / 3


def score(message: str, reply: str, examples: list[dict]) -> JudgeScore:
    ex = "\n\n".join(
        f"CUSTOMER: {e['customer_text']}\nAPPLE REPLIED: {e['brand_reply']}"
        for e in examples[:3]
    )
    prompt = (
        f"HOW APPLE HANDLED SIMILAR MESSAGES:\n\n{ex}\n\n"
        f"{'=' * 60}\n"
        f"INCOMING CUSTOMER MESSAGE:\n{message}\n\n"
        f"REPLY TO SCORE:\n{reply}"
    )
    d = json.loads(judge_call(prompt, system=SYSTEM, json_schema=SCHEMA, temperature=0.0))
    return JudgeScore(
        groundedness=int(d["groundedness"]),
        action=int(d["action"]),
        tone=int(d["tone"]),
        safety_violation=bool(d["safety_violation"]),
        note=d["note"],
    )
