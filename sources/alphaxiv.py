"""AlphaXiv source — pull curated papers from a Google Sheet."""

import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

import config
import storage


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def fetch_signals() -> list[dict]:
    """Fetch new rows from the curated AlphaXiv Google Sheet."""
    if not config.ALPHAXIV_SHEET_ID:
        print("  [alphaxiv] Skipping — ALPHAXIV_SHEET_ID not set")
        return []

    creds_path = Path(config.GOOGLE_SHEETS_CREDS)
    if not creds_path.is_absolute():
        creds_path = config.PROJECT_DIR / creds_path
    if not creds_path.exists():
        # Try auto-bdr credentials as fallback
        fallback = config.PROJECT_DIR.parent / "auto-bdr" / "credentials.json"
        if fallback.exists():
            creds_path = fallback
        else:
            print("  [alphaxiv] Skipping — credentials file not found")
            return []

    try:
        credentials = Credentials.from_service_account_file(
            str(creds_path), scopes=SCOPES
        )
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(config.ALPHAXIV_SHEET_ID).sheet1
        rows = sheet.get_all_records()
    except Exception as e:
        print(f"  [alphaxiv] Error connecting to Google Sheet: {e}")
        return []

    signals = []
    for row in rows:
        title = str(row.get("title", "") or row.get("Title", ""))
        abstract = str(
            row.get("abstract", "")
            or row.get("Abstract", "")
            or row.get("notes", "")
            or row.get("Notes", "")
        )
        paper_url = str(
            row.get("paper_url", "")
            or row.get("Paper URL", "")
            or row.get("url", "")
            or row.get("URL", "")
        )
        authors = str(row.get("authors", "") or row.get("Authors", ""))
        date_added = str(row.get("date_added", "") or row.get("Date Added", ""))

        if not paper_url or not title:
            continue

        # Skip if already processed
        if storage.is_seen(paper_url):
            continue

        signals.append({
            "source": "alphaxiv",
            "title": title,
            "text": f"{title}\n\n{abstract}",
            "author": authors,
            "url": paper_url,
            "added_date": date_added,
        })

    print(f"  [alphaxiv] Found {len(signals)} new papers")
    return signals
