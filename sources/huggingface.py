"""Hugging Face source — dataset discussions + hub search for pain signals."""

from huggingface_hub import HfApi, list_datasets
import requests
import config


def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in config.ALL_KEYWORDS)


def _fetch_dataset_discussions() -> list[dict]:
    """Scan discussion threads on watched datasets."""
    if not config.HF_TOKEN:
        return []

    api = HfApi(token=config.HF_TOKEN)
    signals = []

    for dataset_id in config.HF_WATCHED_DATASETS:
        try:
            discussions = api.get_repo_discussions(
                dataset_id, repo_type="dataset"
            )
            for disc in discussions:
                title = disc.title or ""
                # Fetch discussion details for the full text
                try:
                    detail = api.get_discussion_details(
                        dataset_id, disc.num, repo_type="dataset"
                    )
                    # Collect text from all events/comments
                    text_parts = [title]
                    for event in getattr(detail, "events", []):
                        content = getattr(event, "content", "")
                        if content:
                            text_parts.append(content)
                    full_text = " ".join(text_parts)
                except Exception:
                    full_text = title

                if not _matches_keywords(full_text):
                    continue

                signals.append({
                    "source": "huggingface",
                    "title": title,
                    "text": full_text[:3000],
                    "author": getattr(disc, "author", ""),
                    "url": f"https://huggingface.co/datasets/{dataset_id}/discussions/{disc.num}",
                    "dataset_id": dataset_id,
                    "discussion_id": disc.num,
                    "created_at": str(getattr(disc, "created_at", "")),
                })

        except Exception as e:
            print(f"  [huggingface] Error scanning {dataset_id}: {e}")

    return signals


def _fetch_recent_datasets() -> list[dict]:
    """Search for recently created datasets in target domains."""
    if not config.HF_TOKEN:
        return []

    signals = []
    search_terms = ["annotation", "RLHF", "preference", "human-labeled", "evaluation"]

    for term in search_terms:
        try:
            datasets = list(list_datasets(
                search=term,
                sort="createdAt",
                direction=-1,
                limit=10,
                token=config.HF_TOKEN,
            ))
            for ds in datasets:
                desc = getattr(ds, "description", "") or ""
                card = getattr(ds, "card_data", None)
                card_text = ""
                if card:
                    card_text = str(getattr(card, "text", ""))
                full_text = f"{ds.id} {desc} {card_text}"

                if not _matches_keywords(full_text):
                    continue

                signals.append({
                    "source": "huggingface_dataset",
                    "title": ds.id,
                    "text": (desc or card_text)[:3000],
                    "author": ds.author or "",
                    "url": f"https://huggingface.co/datasets/{ds.id}",
                    "dataset_id": ds.id,
                    "created_at": str(getattr(ds, "created_at", "")),
                })

        except Exception as e:
            print(f"  [huggingface] Error searching '{term}': {e}")

    return signals


def _fetch_dataset_health() -> list[dict]:
    """Check dataset validity for watched datasets — flag unhealthy ones."""
    signals = []

    for dataset_id in config.HF_WATCHED_DATASETS:
        try:
            resp = requests.get(
                f"https://datasets-server.huggingface.co/is-valid?dataset={dataset_id}",
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            if not data.get("preview", True) or not data.get("viewer", True):
                signals.append({
                    "source": "huggingface_health",
                    "title": f"Dataset health issue: {dataset_id}",
                    "text": f"Dataset {dataset_id} has health issues: {data}",
                    "author": "",
                    "url": f"https://huggingface.co/datasets/{dataset_id}",
                    "dataset_id": dataset_id,
                    "created_at": "",
                })
        except Exception as e:
            print(f"  [huggingface] Error checking health for {dataset_id}: {e}")

    return signals


def fetch_signals() -> list[dict]:
    """Fetch all Hugging Face signals."""
    if not config.HF_TOKEN:
        print("  [huggingface] Skipping — HF_TOKEN not set")
        return []

    signals = []
    signals.extend(_fetch_dataset_discussions())
    signals.extend(_fetch_recent_datasets())
    signals.extend(_fetch_dataset_health())

    # Deduplicate by URL
    seen = set()
    unique = []
    for s in signals:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)

    print(f"  [huggingface] Found {len(unique)} keyword-matching signals")
    return unique
