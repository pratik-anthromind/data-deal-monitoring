"""Reddit source — scans subreddits for data-quality pain signals using PRAW."""

import time
import praw
import config


def _matches_keywords(text: str) -> bool:
    """Fast pre-filter: check if text contains any keyword."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in config.ALL_KEYWORDS)


def _submission_to_signal(submission) -> dict:
    return {
        "source": "reddit",
        "title": submission.title,
        "text": (submission.selftext or "")[:3000],
        "author": str(submission.author) if submission.author else "[deleted]",
        "url": f"https://reddit.com{submission.permalink}",
        "subreddit": str(submission.subreddit),
        "score": submission.score,
        "flair": submission.link_flair_text or "",
        "created_utc": submission.created_utc,
    }


def _comment_to_signal(comment, submission_title: str) -> dict:
    return {
        "source": "reddit_comment",
        "title": f"Re: {submission_title}",
        "text": (comment.body or "")[:3000],
        "author": str(comment.author) if comment.author else "[deleted]",
        "url": f"https://reddit.com{comment.permalink}",
        "subreddit": str(comment.subreddit),
        "score": comment.score,
        "flair": "",
        "created_utc": comment.created_utc,
    }


def fetch_signals() -> list[dict]:
    """Fetch keyword-matching posts and comments from configured subreddits."""
    if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET:
        print("  [reddit] Skipping — REDDIT_CLIENT_ID/SECRET not set")
        return []

    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )

    signals = []
    cutoff = time.time() - 48 * 3600  # 48 hours ago

    for sub_name in config.SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)

            # Scan new posts
            for submission in subreddit.new(limit=100):
                if submission.created_utc < cutoff:
                    continue
                full_text = f"{submission.title} {submission.selftext}"
                if not _matches_keywords(full_text):
                    continue
                signals.append(_submission_to_signal(submission))

                # Scan top-level comments on matching posts
                submission.comments.replace_more(limit=0)
                for comment in submission.comments[:20]:
                    if _matches_keywords(comment.body or ""):
                        signals.append(
                            _comment_to_signal(comment, submission.title)
                        )

            # Also do keyword searches (catches posts where keyword is less obvious)
            for keyword in config.NEED_KEYWORDS + config.RLHF_KEYWORDS[:3]:
                for submission in subreddit.search(
                    keyword, sort="new", time_filter="day", limit=10
                ):
                    if submission.created_utc < cutoff:
                        continue
                    signals.append(_submission_to_signal(submission))

        except Exception as e:
            print(f"  [reddit] Error scanning r/{sub_name}: {e}")

    # Deduplicate by URL
    seen = set()
    unique = []
    for s in signals:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)

    print(f"  [reddit] Found {len(unique)} keyword-matching signals")
    return unique
