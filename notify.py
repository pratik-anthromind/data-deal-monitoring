"""Slack notifications — tiered by signal score."""

import requests
import config


def _send_slack(message: str):
    """Send a message to Slack via webhook."""
    if not config.SLACK_WEBHOOK_URL:
        print(f"  [slack] (not configured) {message[:200]}")
        return
    try:
        requests.post(
            config.SLACK_WEBHOOK_URL,
            json={"text": message},
            timeout=10,
        )
    except Exception as e:
        print(f"  [slack] Error sending: {e}")


def notify_lead(signal: dict, scores: dict):
    """Send a Slack notification for a high-intent lead, tiered by score."""
    total = scores.get("total_score", 0)
    if total < config.SCORE_THRESHOLD:
        return

    category = scores.get("category", "Unknown")
    reasoning = scores.get("reasoning", "")
    hook = scores.get("suggested_hook", "")
    source = signal.get("source", "unknown")
    url = signal.get("url", "")
    author = signal.get("author", "unknown")
    title = signal.get("title", "")[:100]

    # Score breakdown
    breakdown = (
        f"Pain:{scores.get('pain_intensity', 0)}/25 | "
        f"Urgency:{scores.get('urgency', 0)}/20 | "
        f"Commercial:{scores.get('commercial_context', 0)}/20 | "
        f"Decision-maker:{scores.get('decision_maker', 0)}/15 | "
        f"Fit:{scores.get('anthromind_fit', 0)}/20"
    )

    mention = f"<@{config.SLACK_USER_ID}> " if config.SLACK_USER_ID else ""

    if total >= 86:
        # Active Buyer — immediate alert
        msg = (
            f"{mention}:rotating_light: *ACTIVE BUYER DETECTED* (Score: {total}/100)\n\n"
            f"*{title}*\n"
            f"Source: {source} | Author: {author}\n"
            f"Category: {category}\n"
            f"{breakdown}\n\n"
            f"*Why:* {reasoning}\n"
            f"*Hook:* {hook}\n"
            f"*Link:* {url}\n\n"
            f"Engage IMMEDIATELY."
        )
    elif total >= 71:
        # Very High — priority alert
        msg = (
            f"{mention}:fire: *Priority Lead* (Score: {total}/100)\n\n"
            f"*{title}*\n"
            f"Source: {source} | Author: {author}\n"
            f"Category: {category}\n"
            f"{breakdown}\n\n"
            f"*Why:* {reasoning}\n"
            f"*Hook:* {hook}\n"
            f"*Link:* {url}\n\n"
            f"Engage within hours — consultative approach."
        )
    else:
        # High Intent (56-70) — standard notification
        msg = (
            f":mag: *New Lead* (Score: {total}/100)\n\n"
            f"*{title}*\n"
            f"Source: {source} | Author: {author}\n"
            f"Category: {category}\n"
            f"{breakdown}\n\n"
            f"*Why:* {reasoning}\n"
            f"*Hook:* {hook}\n"
            f"*Link:* {url}"
        )

    _send_slack(msg)
