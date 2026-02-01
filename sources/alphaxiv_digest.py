"""AlphaXiv digest source — read weekly digest emails from Gmail."""

import base64
import json
import re
from pathlib import Path

import config
import storage

ARXIV_URL_RE = re.compile(r"https?://(?:arxiv\.org/abs/|alphaxiv\.org/abs/)(\d{4}\.\d{4,5})")


def _normalize_arxiv_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"


def _get_gmail_service():
    """Build Gmail API service reusing auto-bdr OAuth credentials."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    token_path = Path(config.GMAIL_TOKEN_FILE)

    # Mode 1: env var token (CI / GitHub Actions)
    if config.GMAIL_TOKEN_JSON:
        token_data = base64.b64decode(config.GMAIL_TOKEN_JSON).decode()
        creds = Credentials.from_authorized_user_info(
            json.loads(token_data), config.GMAIL_SCOPES
        )
    # Mode 2: file on disk (local dev)
    elif token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), config.GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_file = Path(config.GMAIL_CREDENTIALS_FILE)
            if not creds_file.exists():
                raise FileNotFoundError(
                    f"Gmail credentials file not found: {config.GMAIL_CREDENTIALS_FILE}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_file), config.GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save refreshed/new token if using file mode
        if not config.GMAIL_TOKEN_JSON:
            token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_text(payload: dict) -> str:
    """Recursively extract plain text from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        text = _extract_text(part)
        if text:
            return text
    return ""


def _extract_html(payload: dict) -> str:
    """Recursively extract HTML from a Gmail message payload."""
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        html = _extract_html(part)
        if html:
            return html
    return ""


def _parse_papers_from_text(text: str) -> list[dict]:
    """Extract paper titles and arXiv URLs from email text."""
    papers = []
    seen_ids = set()

    for match in ARXIV_URL_RE.finditer(text):
        arxiv_id = match.group(1)
        if arxiv_id in seen_ids:
            continue
        seen_ids.add(arxiv_id)

        # Try to find a title near the URL — look at the line before or same line
        url_pos = match.start()
        # Get the surrounding context (up to 300 chars before the URL)
        context = text[max(0, url_pos - 300):url_pos]
        lines = [l.strip() for l in context.split("\n") if l.strip()]
        title = lines[-1] if lines else f"arXiv:{arxiv_id}"
        # Clean up title — remove markdown/HTML artifacts
        title = re.sub(r"[*_#<>]", "", title).strip()
        if len(title) < 5 or title.startswith("http"):
            title = f"arXiv:{arxiv_id}"

        papers.append({"arxiv_id": arxiv_id, "title": title})

    return papers


def _parse_papers_from_html(html: str) -> list[dict]:
    """Extract paper titles and arXiv URLs from email HTML."""
    papers = []
    seen_ids = set()

    # Find links to arXiv/alphaxiv papers with anchor text as title
    for match in re.finditer(
        r'<a[^>]*href="[^"]*?(?:arxiv\.org/abs/|alphaxiv\.org/abs/)(\d{4}\.\d{4,5})[^"]*"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    ):
        arxiv_id = match.group(1)
        if arxiv_id in seen_ids:
            continue
        seen_ids.add(arxiv_id)

        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if not title or len(title) < 5:
            title = f"arXiv:{arxiv_id}"

        papers.append({"arxiv_id": arxiv_id, "title": title})

    # Fallback: find bare URLs in HTML
    for match in ARXIV_URL_RE.finditer(html):
        arxiv_id = match.group(1)
        if arxiv_id not in seen_ids:
            seen_ids.add(arxiv_id)
            papers.append({"arxiv_id": arxiv_id, "title": f"arXiv:{arxiv_id}"})

    return papers


def fetch_signals() -> list[dict]:
    """Read AlphaXiv weekly digest from Gmail and extract paper signals."""
    # Check if Gmail credentials are available
    token_path = Path(config.GMAIL_TOKEN_FILE)
    if not config.GMAIL_TOKEN_JSON and not token_path.exists():
        creds_file = Path(config.GMAIL_CREDENTIALS_FILE)
        if not creds_file.exists():
            print("  [alphaxiv_digest] Skipping — Gmail credentials not available")
            return []

    try:
        service = _get_gmail_service()
    except Exception as e:
        print(f"  [alphaxiv_digest] Error connecting to Gmail: {e}")
        return []

    try:
        results = service.users().messages().list(
            userId="me",
            q=config.ALPHAXIV_GMAIL_QUERY,
            maxResults=5,
        ).execute()
    except Exception as e:
        print(f"  [alphaxiv_digest] Error searching Gmail: {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        print("  [alphaxiv_digest] No recent digest emails found")
        return []

    all_papers = []
    seen_ids = set()

    for msg_meta in messages:
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_meta["id"],
                format="full",
            ).execute()
        except Exception:
            continue

        payload = msg.get("payload", {})

        # Try plain text first, then HTML fallback
        text = _extract_text(payload)
        papers = _parse_papers_from_text(text) if text else []

        if not papers:
            html = _extract_html(payload)
            if html:
                papers = _parse_papers_from_html(html)

        for paper in papers:
            if paper["arxiv_id"] not in seen_ids:
                seen_ids.add(paper["arxiv_id"])
                all_papers.append(paper)

    signals = []
    for paper in all_papers:
        paper_url = _normalize_arxiv_url(paper["arxiv_id"])
        if storage.is_seen(paper_url):
            continue

        signals.append({
            "source": "alphaxiv_digest",
            "title": paper["title"],
            "text": paper["title"],
            "author": "",
            "url": paper_url,
        })

    print(f"  [alphaxiv_digest] Found {len(signals)} new papers from digest emails")
    return signals
