"""
The agent: one incoming customer message -> intent, grounded reply, and an
auto/escalate decision with a cited policy reason.

All three outputs come from a SINGLE call. Three separate calls would be
cleaner conceptually but the outputs are not independent -- the right escalation
decision depends on the intent, and the reply depends on both. Splitting them
also triples the call count against a free-tier quota. The cost of this choice
is that one bad parse loses all three outputs, which is why the call is
schema-constrained.
"""
import json
from dataclasses import asdict, dataclass

from src.llm import generate
from src.retrieve import Example, Retriever
from src.taxonomy import (DISAMBIGUATION_RULES, ESCALATION_POLICY,
                          INTENTS, LABELS, PRIORITY, REASON_CODES)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": LABELS},
        "decision": {"type": "string", "enum": ["auto", "escalate"]},
        # Enum from taxonomy.py, never re-typed here: this list used to be a
        # literal, so retiring a code would have left the model still able to
        # emit it.
        "reason": {"type": "string", "enum": REASON_CODES},
        "reason_text": {"type": "string"},
        "reply": {"type": "string"},
    },
    "required": ["intent", "decision", "reason", "reason_text", "reply"],
}


@dataclass
class AgentOutput:
    intent: str
    decision: str
    reason: str
    reason_text: str
    reply: str
    retrieved: list[dict]


def _taxonomy_block() -> str:
    out = []
    for name, d in INTENTS.items():
        out.append(
            f"- {name}\n"
            f"    definition: {d['definition']}\n"
            f"    includes:   {d['includes']}\n"
            f"    excludes:   {d['excludes']}"
        )
    return "\n".join(out)


SYSTEM = f"""You are a first-response triage agent for AppleSupport on Twitter.

You do three things for each incoming customer message: classify its intent,
draft Apple's first reply, and decide whether it can be auto-handled or must go
to a human.

INTENT TAXONOMY
{_taxonomy_block()}

DISAMBIGUATION RULES -- these are mechanical tests, apply them before judgement:
{DISAMBIGUATION_RULES}

When a message carries more than one intent, apply this priority order and pick
the first that fits: {" > ".join(PRIORITY)}

ESCALATION POLICY
{ESCALATION_POLICY}

REPLY RULES
- You are writing Apple's FIRST response on a public Twitter thread, not a
  resolution. Apple's historical pattern is to acknowledge, ask one diagnostic
  question, or point to a resource -- match that.
- Ground the reply in the historical examples provided. Do not invent support
  steps, article contents, phone numbers, or policies that do not appear there.
- Under 280 characters. No hashtags. No emoji.
- NEVER write a URL. Every link in the historical examples was replaced with the
  placeholder <url> during cleaning, so you have no real link to ground in and
  any URL you produce is fabricated. Write "<url>" where Apple would link, or
  refer to the resource in words.
- If escalating, the reply should set up the handoff rather than attempt a fix.
- Never ask for a password, payment details, or any credential.

Output must satisfy the provided JSON schema. `reason` is the policy code that
drove the decision; `reason_text` is one short sentence saying why, in plain
language, naming the specific signal in the message."""


def _prompt(message: str, examples: list[Example]) -> str:
    if not examples:
        # k=0, the retrieval ablation. The header is dropped entirely rather
        # than left above an empty list: "HOW APPLE HAS HANDLED SIMILAR
        # MESSAGES:" followed by nothing invites the model to fill the gap from
        # its own priors, which is the opposite of what the ablation is testing.
        return (
            f"No historical examples are available for this message. Answer from "
            f"the taxonomy and policy alone.\n\n"
            f"{'=' * 60}\n"
            f"INCOMING CUSTOMER MESSAGE:\n{message}"
        )
    ex = "\n\n".join(
        f"[similarity {e.score:.2f}]\nCUSTOMER: {e.customer_text}\nAPPLE REPLIED: {e.brand_reply}"
        for e in examples
    )
    return (
        f"HOW APPLE HAS HANDLED SIMILAR MESSAGES:\n\n{ex}\n\n"
        f"{'=' * 60}\n"
        f"INCOMING CUSTOMER MESSAGE:\n{message}"
    )


def run(message: str, retriever: Retriever, k: int = 5) -> AgentOutput:
    examples = retriever.query(message, k=k) if k > 0 else []
    raw = generate(
        _prompt(message, examples),
        system=SYSTEM,
        json_schema=RESPONSE_SCHEMA,
        temperature=0.0,
    )
    # Schema-constrained decoding makes a malformed shape impossible, but not a
    # TRUNCATED one: if the reply runs into max_output_tokens the JSON is cut
    # off mid-string and json.loads raises a bare JSONDecodeError several frames
    # from the cause. Name the cause instead.
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Agent returned unparseable JSON ({e}); most likely the response "
            f"hit max_output_tokens and was truncated. First 200 chars: "
            f"{raw[:200]!r}"
        ) from e
    return AgentOutput(
        intent=d["intent"],
        decision=d["decision"],
        reason=d["reason"],
        reason_text=d["reason_text"],
        reply=d["reply"],
        retrieved=[asdict(e) for e in examples],
    )


if __name__ == "__main__":
    from src.retrieve import load_or_build

    r = load_or_build()
    tests = [
        "my battery has been draining insanely fast ever since the ios 11 update, phone is useless",
        "someone got into my apple id and bought £200 of apps. i cant log in anymore",
        "how do i attach a pdf to an email on my ipad?",
        "this update is absolute garbage, worst company ever, switching to android",
        "my iphone 8 gets so hot while charging i actually burnt my hand on it",
    ]
    for t in tests:
        o = run(t, r)
        print(f"\n{'=' * 70}\nMSG      {t}")
        print(f"INTENT   {o.intent}")
        print(f"DECISION {o.decision}  [{o.reason}] {o.reason_text}")
        print(f"REPLY    {o.reply}")
