"""GitHub source — scans issues for data-quality pain signals via REST API."""

from datetime import datetime, timedelta, timezone
import requests
import config


API_URL = "https://api.github.com/search/issues"


def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in config.ALL_KEYWORDS)


def fetch_signals() -> list[dict]:
    """Fetch keyword-matching open issues from GitHub."""
    if not config.GITHUB_TOKEN:
        print("  [github] Skipping — GITHUB_TOKEN not set")
        return []

    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    signals = []
    seen_urls = set()

    # Build search queries from keyword clusters
    search_terms = (
        config.PAIN_KEYWORDS[:5]
        + config.NEED_KEYWORDS[:3]
        + config.RLHF_KEYWORDS[:3]
        + config.FRUSTRATION_KEYWORDS[:3]
    )

    for term in search_terms:
        query = f'"{term}" is:issue is:open created:>{yesterday}'
        try:
            resp = requests.get(
                API_URL,
                headers=headers,
                params={"q": query, "sort": "created", "per_page": 10},
                timeout=15,
            )
            if resp.status_code == 403:
                print("  [github] Rate limited, stopping early")
                break
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                url = item.get("html_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                body = item.get("body") or ""
                title = item.get("title", "")
                full_text = f"{title} {body}"

                if not _matches_keywords(full_text):
                    continue

                # Extract repo info
                repo_url = item.get("repository_url", "")
                repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else ""

                signals.append({
                    "source": "github",
                    "title": title,
                    "text": body[:3000],
                    "author": item.get("user", {}).get("login", ""),
                    "url": url,
                    "repo": repo_name,
                    "stars": 0,  # Would need separate API call
                    "created_at": item.get("created_at", ""),
                })

        except Exception as e:
            print(f"  [github] Error searching '{term}': {e}")

    # Also scan priority repos specifically
    for repo in config.GITHUB_PRIORITY_REPOS:
        query = f"repo:{repo} is:issue is:open created:>{yesterday}"
        try:
            resp = requests.get(
                API_URL,
                headers=headers,
                params={"q": query, "sort": "created", "per_page": 20},
                timeout=15,
            )
            if resp.status_code == 403:
                break
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                url = item.get("html_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                body = item.get("body") or ""
                title = item.get("title", "")

                if not _matches_keywords(f"{title} {body}"):
                    continue

                signals.append({
                    "source": "github",
                    "title": title,
                    "text": body[:3000],
                    "author": item.get("user", {}).get("login", ""),
                    "url": url,
                    "repo": repo,
                    "stars": 0,
                    "created_at": item.get("created_at", ""),
                })

        except Exception as e:
            print(f"  [github] Error scanning {repo}: {e}")

    print(f"  [github] Found {len(signals)} keyword-matching signals")
    return signals
