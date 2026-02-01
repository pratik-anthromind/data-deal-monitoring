"""AlphaXiv web source — scrape trending papers from alphaxiv.org/explore."""

import json
import re

import requests

import config
import storage


ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def _normalize_arxiv_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"


def _extract_papers_from_json(html: str) -> list[dict]:
    """Try to extract paper data from embedded JSON/React state in the HTML."""
    papers = []

    # AlphaXiv embeds paper data as JSON in script tags (Next.js / React hydration)
    for match in re.finditer(r'<script[^>]*>\s*self\.__next_d\.push\(\[.*?,(.*?)\]\)\s*</script>', html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "title" in item:
                        papers.append(item)
            elif isinstance(data, dict) and "title" in data:
                papers.append(data)
        except (json.JSONDecodeError, TypeError):
            continue

    # Also try __NEXT_DATA__ script tag
    next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))
            # Navigate common Next.js structures
            props = next_data.get("props", {}).get("pageProps", {})
            for key in ("papers", "articles", "posts", "trending", "data"):
                items = props.get(key, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and ("title" in item or "arxiv_id" in item):
                            papers.append(item)
        except (json.JSONDecodeError, TypeError):
            pass

    return papers


def _extract_papers_fallback(html: str) -> list[dict]:
    """Fallback: regex-extract arXiv IDs and surrounding titles from HTML."""
    papers = []
    seen_ids = set()

    # Look for links to arXiv papers with nearby title text
    for match in re.finditer(
        r'<a[^>]*href="[^"]*?(?:arxiv\.org/abs/|alphaxiv\.org/abs/)(\d{4}\.\d{4,5})[^"]*"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    ):
        arxiv_id = match.group(1)
        title_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if arxiv_id not in seen_ids and title_text:
            seen_ids.add(arxiv_id)
            papers.append({"arxiv_id": arxiv_id, "title": title_text})

    # Also grab bare arXiv IDs from any links we might have missed
    for match in re.finditer(r'href="[^"]*?(?:arxiv\.org|alphaxiv\.org)/abs/(\d{4}\.\d{4,5})', html):
        arxiv_id = match.group(1)
        if arxiv_id not in seen_ids:
            seen_ids.add(arxiv_id)
            papers.append({"arxiv_id": arxiv_id, "title": f"arXiv:{arxiv_id}"})

    return papers


def fetch_signals() -> list[dict]:
    """Scrape AlphaXiv trending page for new papers."""
    url = config.ALPHAXIV_TRENDING_URL
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "data-deal-monitor/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"  [alphaxiv_web] Error fetching {url}: {e}")
        return []

    html = resp.text

    # Try structured JSON extraction first, fall back to regex
    papers = _extract_papers_from_json(html)
    if not papers:
        papers = _extract_papers_fallback(html)

    if not papers:
        print("  [alphaxiv_web] No papers found on trending page")
        return []

    signals = []
    for paper in papers:
        arxiv_id = paper.get("arxiv_id", "")
        if not arxiv_id:
            # Try to extract from a URL field or paper_id
            for field in ("id", "paper_id", "url", "link"):
                val = str(paper.get(field, ""))
                id_match = ARXIV_ID_RE.search(val)
                if id_match:
                    arxiv_id = id_match.group(1)
                    break

        if not arxiv_id:
            continue

        paper_url = _normalize_arxiv_url(arxiv_id)
        if storage.is_seen(paper_url):
            continue

        title = paper.get("title", f"arXiv:{arxiv_id}")
        abstract = paper.get("abstract", "") or paper.get("summary", "")
        authors = paper.get("authors", "")
        if isinstance(authors, list):
            authors = ", ".join(str(a.get("name", a) if isinstance(a, dict) else a) for a in authors)

        signals.append({
            "source": "alphaxiv",
            "title": title,
            "text": f"{title}\n\n{abstract}" if abstract else title,
            "author": authors,
            "url": paper_url,
        })

    print(f"  [alphaxiv_web] Found {len(signals)} new papers")
    return signals
