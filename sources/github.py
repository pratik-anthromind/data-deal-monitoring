"""GitHub source — scans issues for data-quality pain signals via REST API."""

from datetime import datetime, timedelta, timezone
import requests
import config


API_URL = "https://api.github.com/search/issues"


def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in config.ALL_KEYWORDS)


def _get_headers() -> dict:
    return {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def _lookback_date() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=config.GITHUB_LOOKBACK_DAYS)).strftime("%Y-%m-%d")


def _make_signal(item: dict, repo_name: str = "") -> dict:
    if not repo_name:
        repo_url = item.get("repository_url", "")
        repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else ""
    return {
        "source": "github",
        "title": item.get("title", ""),
        "text": (item.get("body") or "")[:3000],
        "author": item.get("user", {}).get("login", ""),
        "url": item.get("html_url", ""),
        "repo": repo_name,
        "stars": 0,
        "created_at": item.get("created_at", ""),
    }


def fetch_signals() -> list[dict]:
    """Fetch pain signals from GitHub — broad OR queries + priority repo scans."""
    if not config.GITHUB_TOKEN:
        print("  [github] Skipping — GITHUB_TOKEN not set")
        return []

    headers = _get_headers()
    since = _lookback_date()
    signals = []
    seen_urls = set()

    # --- Phase 1: Broad OR queries (Plan C) ---
    # 5 queries replace the old 14 narrow per-keyword queries.
    # Keywords are in the query itself so no _matches_keywords() pre-filter needed.
    for query_terms in config.GITHUB_SEARCH_QUERIES:
        query = f"({query_terms}) is:issue is:open created:>{since}"
        try:
            resp = requests.get(
                API_URL,
                headers=headers,
                params={"q": query, "sort": "created", "per_page": 25},
                timeout=15,
            )
            if resp.status_code == 403:
                print("  [github] Rate limited on keyword search, stopping early")
                break
            if resp.status_code == 422:
                print(f"  [github] Query rejected (422): {query_terms[:60]}...")
                continue
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
                signals.append(_make_signal(item))

        except Exception as e:
            print(f"  [github] Error on query '{query_terms[:50]}...': {e}")

    print(f"  [github] Keyword queries found {len(signals)} signals")

    # --- Phase 2: Priority repo scans (Plan A + B) ---
    # No _matches_keywords() pre-filter — pass everything to Claude.
    # Volume is small (~5-20 issues/day per repo). Claude's prompt handles false positives.
    repo_count = 0
    for repo in config.GITHUB_PRIORITY_REPOS:
        query = f"repo:{repo} is:issue is:open created:>{since}"
        try:
            resp = requests.get(
                API_URL,
                headers=headers,
                params={"q": query, "sort": "created", "per_page": 25},
                timeout=15,
            )
            if resp.status_code == 403:
                print("  [github] Rate limited on repo scan, stopping early")
                break
            if resp.status_code == 422:
                print(f"  [github] Repo scan rejected (422) for {repo}, skipping")
                continue
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                url = item.get("html_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                signals.append(_make_signal(item, repo_name=repo))
                repo_count += 1

        except Exception as e:
            print(f"  [github] Error scanning {repo}: {e}")

    print(f"  [github] Priority repos added {repo_count} signals")
    print(f"  [github] Total: {len(signals)} signals")
    return signals
