"""
Authenticity judge — the last gate before any content goes out.

Runs a fast LLM check on generated posts and replies to catch AI-sounding
content before it hits the timeline. Uses the cheap/fast model (Groq Llama)
since this is a binary quality gate, not a generation task.

A post that fails the judge is either regenerated with feedback or skipped.
This is not optional — AI-sounding content damages credibility permanently
and cannot be undone once posted.

Scoring: 1-10 where:
  1-4: Clearly AI-written. Generic, data dump, over-explained. BLOCK.
  5-6: Borderline. Has some personality but still feels automated. BLOCK.
  7-8: Passes. Sounds like a real person who trades DeFi. ALLOW.
  9-10: Great. Would make a real DeFi trader stop scrolling. ALLOW.

The threshold is 7. Below 7 = rewrite with feedback or skip.
"""
from __future__ import annotations

import logging

from bot.brain.llm import complete as llm_complete

log = logging.getLogger(__name__)

_MIN_SCORE = 7

_JUDGE_SYSTEM = """\
You are an expert at detecting AI-generated content on crypto Twitter.
Your job: score whether a post sounds like it was written by a real DeFi
trader with money in the game, or by an AI trying to sound like one.

SCORE 1-4 (block — clearly AI):
- Data dumps with no opinion ("Protocol X TVL up 15% in 24h")
- Formal structure: premise → explanation → conclusion
- Contains "worth noting", "significant", "ecosystem", "the space", "it's interesting"
- Explains things the audience already knows
- No clear stance, balanced to the point of saying nothing
- Sounds like a press release or newsletter summary
- Perfect grammar throughout, very formal

SCORE 5-6 (block — borderline):
- Has some personality but still feels like a bot wrote it
- Opinion present but hedged too much ("could be", "might mean", "possibly")
- Data included but not integrated with a real angle
- Reads like it was assembled from parts rather than thought

SCORE 7-8 (allow — sounds real):
- Has a clear opinion or observation that required being IN the space to notice
- Specific enough that a random person couldn't have written it
- Sounds like something you'd say to a friend who also trades DeFi
- Natural voice — could be casual, could be direct, not always perfect grammar

SCORE 9-10 (allow — excellent):
- Would make a real DeFi trader stop scrolling and say "someone else sees this"
- Contains an insight, humor, or honesty that's rare
- Doesn't feel like content — feels like a thought

OUTPUT FORMAT (exactly this, nothing else):
SCORE: [1-10]
REASON: [one sentence — the specific thing that makes it sound AI or real]
FEEDBACK: [if score < 7: one specific instruction to fix it. If score >= 7: NONE]
"""


def judge(content: str, content_type: str = "post") -> dict:
    """
    Score content for authenticity. Returns dict with score, reason, feedback.

    content_type: "post" or "reply"

    Always returns a dict — never raises. On LLM failure, returns score=7
    (fail open — don't block posts due to judge errors).
    """
    if not content or len(content) < 10:
        return {"score": 1, "reason": "Too short to evaluate", "feedback": "Generate actual content"}

    prompt = (
        f'Score this crypto {content_type} for authenticity '
        f'(does it sound like a real DeFi trader or like AI?):\n\n'
        f'"{content}"\n\n'
        f'Remember: score 7+ = allow, below 7 = block.\n'
        f'Output exactly: SCORE, REASON, FEEDBACK (three lines).'
    )

    try:
        raw = llm_complete(
            system=_JUDGE_SYSTEM,
            user=prompt,
            max_tokens=120,
            temperature=0.2,   # Low temp — consistent judging, not creative
        )

        if not raw:
            log.debug("Judge: no response, failing open with score=7")
            return {"score": 7, "reason": "No response", "feedback": "NONE"}

        result: dict = {"score": 7, "reason": "", "feedback": "NONE"}
        for line in raw.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("SCORE:"):
                try:
                    result["score"] = int(line.split(":", 1)[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            elif line.upper().startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("FEEDBACK:"):
                result["feedback"] = line.split(":", 1)[1].strip()

        log.debug("Judge [%s] score=%d: %s", content_type, result["score"], content[:60])
        return result

    except Exception as exc:
        log.warning("Authenticity judge error: %s — failing open", exc)
        return {"score": 7, "reason": "Judge error", "feedback": "NONE"}


def passes(content: str, content_type: str = "post") -> tuple[bool, dict]:
    """
    Returns (passes: bool, judge_result: dict).
    Simple wrapper for the common use case.
    """
    result = judge(content, content_type)
    ok = result["score"] >= _MIN_SCORE
    if not ok:
        log.info(
            "Authenticity FAILED (score=%d): %s | Reason: %s | Fix: %s",
            result["score"], content[:60], result["reason"], result["feedback"],
        )
    return ok, result
