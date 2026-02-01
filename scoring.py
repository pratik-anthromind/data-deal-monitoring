"""Claude Haiku multi-dimensional intent scoring for data-deal signals."""

import json
from anthropic import Anthropic
import config

client = None


def _get_client() -> Anthropic:
    global client
    if client is None:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return client


SCORING_PROMPT = """You are a lead-scoring analyst for Anthromind, a company that provides expert human data annotation, RLHF preference data, and evaluation services for AI/ML teams. Your job is to score signals from Reddit, GitHub, Hugging Face, and research papers to determine if they indicate a real potential customer.

Score this signal across 5 dimensions. Be rigorous — most signals are noise.

## Dimension 1: Pain Intensity (0-25 pts)
- 0-5: Theoretical discussion, no personal pain
- 6-10: Early exploration ("thinking about", "curious how")
- 11-15: Active problem ("we're struggling with", "our model isn't working because")
- 16-20: Quantified impact ("wasted $X", "delayed Y weeks", "accuracy dropped Z%")
- 21-25: Crisis ("blocking our launch", "tried everything", "biggest customer threatening to leave")
Modifiers: +3 if multiple failed approaches described. +2 if cost quantified. -5 if pain is past tense with resolution.

## Dimension 2: Urgency (0-20 pts)
- 0-4: No time context
- 5-8: Ongoing concern, no deadline
- 9-12: Active current project ("we're currently", "right now")
- 13-16: Near-term deadline ("need by Q2", "launching next month")
- 17-20: Immediate ("this week", "ASAP", "blocking everything")
Post recency penalty: if the post is old, reduce score.

## Dimension 3: Commercial Context (0-20 pts)
- 0-4: Hobby or academic — no commercial signals
- 5-8: Ambiguous
- 9-12: Startup signals ("our startup", "building a product")
- 13-16: Established company (team size, existing customers mentioned)
- 17-20: Enterprise (large scale, compliance language, existing vendor contracts)
Evidence: "our product/customers/users" = commercial. Data scale 100K+ = likely commercial.

## Dimension 4: Decision-Maker Proximity (0-15 pts)
- 0-3: Unknown role
- 4-6: Individual contributor at a company
- 7-9: Team lead or senior IC
- 10-12: Manager or director
- 13-15: Founder, CTO, VP, or explicit budget owner
Proxy: discusses budget tradeoffs = likely has authority.

## Dimension 5: Anthromind Fit (0-20 pts)
- 0-4: Doesn't match (raw data collection, not annotation)
- 5-8: Tangential (ML engineering help, not data services)
- 9-12: General fit — annotation needed but simple tasks
- 13-16: Strong fit — expert annotation, RLHF, specialized curation
- 17-20: Perfect — needs exactly what Anthromind offers + frustrated with commodity alternatives
Amplifiers: domain expertise needed (medical, legal, code) +3. Quality over speed +2. RLHF/preference data +3. Simple binary classification at massive scale -5.

## Category Classification
Classify into exactly one category:
- Annotation Quality
- Dataset Bias/Gaps
- RLHF/Eval Bottleneck
- Ground Truth
- Synthetic Data Disillusionment
- Competitor Frustration
- Budget/Scaling

## False Positive Filters
Score LOW (total < 30) if the signal is:
- Academic theoretician writing about problems, not experiencing them
- Student with a class project (no budget, small scale)
- Solved problem (past tense with resolution)
- Competitor marketing (selling, not buying)
- News sharing with no personal context
- Tool builder who solved tooling but doesn't need workforce

Real pain is past/present tense with consequences. Academic discussion is general tense without personal stakes.

Respond with ONLY valid JSON, no markdown fences:
{
  "pain_intensity": <int 0-25>,
  "urgency": <int 0-20>,
  "commercial_context": <int 0-20>,
  "decision_maker": <int 0-15>,
  "anthromind_fit": <int 0-20>,
  "total_score": <int 0-100>,
  "category": "<one of the 7 categories>",
  "reasoning": "<2-3 sentence explanation of the score>",
  "suggested_hook": "<1 sentence engagement hook if score >= 56, else empty string>"
}"""


def score_signal(signal: dict) -> dict:
    """Score a signal using Claude Haiku. Returns scores dict."""
    if not config.ANTHROPIC_API_KEY:
        print("  [scoring] Skipping — ANTHROPIC_API_KEY not set")
        return {
            "pain_intensity": 0, "urgency": 0, "commercial_context": 0,
            "decision_maker": 0, "anthromind_fit": 0, "total_score": 0,
            "category": "", "reasoning": "No API key", "suggested_hook": "",
        }

    source_context = f"Source: {signal.get('source', 'unknown')}"
    if signal.get("subreddit"):
        source_context += f" (r/{signal['subreddit']})"
    if signal.get("repo"):
        source_context += f" (repo: {signal['repo']})"
    if signal.get("dataset_id"):
        source_context += f" (dataset: {signal['dataset_id']})"

    user_message = f"""{source_context}
Author: {signal.get('author', 'unknown')}
Title: {signal.get('title', '')}

Content:
{signal.get('text', '')[:2000]}"""

    try:
        response = _get_client().messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=500,
            messages=[
                {"role": "user", "content": user_message},
            ],
            system=SCORING_PROMPT,
        )

        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        scores = json.loads(text)

        # Validate and clamp scores
        scores["pain_intensity"] = max(0, min(25, int(scores.get("pain_intensity", 0))))
        scores["urgency"] = max(0, min(20, int(scores.get("urgency", 0))))
        scores["commercial_context"] = max(0, min(20, int(scores.get("commercial_context", 0))))
        scores["decision_maker"] = max(0, min(15, int(scores.get("decision_maker", 0))))
        scores["anthromind_fit"] = max(0, min(20, int(scores.get("anthromind_fit", 0))))

        # Recompute total from components
        scores["total_score"] = (
            scores["pain_intensity"]
            + scores["urgency"]
            + scores["commercial_context"]
            + scores["decision_maker"]
            + scores["anthromind_fit"]
        )

        return scores

    except json.JSONDecodeError as e:
        print(f"  [scoring] JSON parse error: {e}")
        return {
            "pain_intensity": 0, "urgency": 0, "commercial_context": 0,
            "decision_maker": 0, "anthromind_fit": 0, "total_score": 0,
            "category": "", "reasoning": f"Parse error: {e}",
            "suggested_hook": "",
        }
    except Exception as e:
        print(f"  [scoring] Error: {e}")
        return {
            "pain_intensity": 0, "urgency": 0, "commercial_context": 0,
            "decision_maker": 0, "anthromind_fit": 0, "total_score": 0,
            "category": "", "reasoning": f"Error: {e}",
            "suggested_hook": "",
        }
