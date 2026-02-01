"""Main orchestrator — scans all sources, scores signals, notifies on leads."""

import sys
import time

import config
import storage
import scoring
import notify
from sources import reddit, github, huggingface, alphaxiv_web, alphaxiv_digest


def run():
    print("=" * 60)
    print("Data Deal Monitor")
    print("=" * 60)

    # Initialize database
    storage.init_db()

    # Collect signals from all sources (graceful degradation)
    all_signals = []
    sources = [
        ("Reddit", reddit.fetch_signals),
        ("GitHub", github.fetch_signals),
        ("Hugging Face", huggingface.fetch_signals),
        ("AlphaXiv Web", alphaxiv_web.fetch_signals),
        ("AlphaXiv Digest", alphaxiv_digest.fetch_signals),
    ]

    for name, fetch_fn in sources:
        print(f"\nScanning {name}...")
        try:
            signals = fetch_fn()
            all_signals.extend(signals)
        except Exception as e:
            print(f"  [{name}] Fatal error: {e}")

    print(f"\nTotal raw signals: {len(all_signals)}")

    # Dedup against seen URLs
    new_signals = []
    for signal in all_signals:
        url = signal.get("url", "")
        if not url:
            continue
        if storage.is_seen(url):
            continue
        # Cross-tool dedup with auto-bdr
        author = signal.get("author", "")
        if author and storage.is_in_outreach_log(author):
            storage.mark_seen(url)
            continue
        new_signals.append(signal)

    print(f"New (unseen) signals: {len(new_signals)}")

    if not new_signals:
        print("\nNo new signals to process.")
        return

    # Score each signal with Claude Haiku
    print(f"\nScoring {len(new_signals)} signals with Claude Haiku...")
    leads_found = 0
    total_scored = 0

    for i, signal in enumerate(new_signals, 1):
        url = signal.get("url", "")
        title = signal.get("title", "")[:60]
        print(f"  [{i}/{len(new_signals)}] {title}...")

        scores = scoring.score_signal(signal)
        total = scores.get("total_score", 0)
        total_scored += 1

        # Save to database
        storage.save_signal(signal, scores)
        storage.mark_seen(url)

        # Notify if above threshold
        if total >= config.SCORE_THRESHOLD:
            leads_found += 1
            notify.notify_lead(signal, scores)
            storage.mark_notified(url)
            tier = "ACTIVE BUYER" if total >= 86 else "PRIORITY" if total >= 71 else "Lead"
            print(f"    -> {tier} (score: {total}) — {scores.get('category', '')}")
        else:
            print(f"    -> Logged (score: {total})")

        # Small delay to respect API rate limits
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 60)
    print(f"Scored: {total_scored} | Leads sent to Slack: {leads_found}")
    print(f"Threshold: {config.SCORE_THRESHOLD}/100")
    print("=" * 60)


if __name__ == "__main__":
    run()
