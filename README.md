# Data Deal Monitoring

A **read-only** monitoring tool that tracks public discussions and publications related to data annotation, labeling quality, and RLHF across developer platforms. Built for personal market research into the AI data services landscape.

All platform interactions are strictly read-only — no posting, commenting, voting, or any form of engagement. The tool only reads publicly available content.

**Cost target:** <$1/month (all free-tier APIs + Claude Haiku for classification)

---

## What It Does

Scans public posts, issues, dataset discussions, and research papers for conversations about data quality challenges in ML/AI — annotation errors, RLHF bottlenecks, labeling workflows, synthetic data limitations, etc.

Signals are classified by topic category and relevance using Claude Haiku, stored in a local SQLite database, and optionally forwarded to a personal Slack channel for review.

This is a passive listener. It does not interact with any platform or user.

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys (each source gracefully skips if its key is missing)
python monitor.py
```

Each source skips gracefully if its API key isn't configured — you can start with just `ANTHROPIC_API_KEY` and one source, then add more over time.

---

## Architecture

```
data-deal-monitoring/
├── monitor.py                   # Main entry point — orchestrates all sources
├── config.py                    # API keys, keywords, thresholds, subreddits
├── sources/
│   ├── __init__.py
│   ├── reddit.py                # PRAW read-only keyword monitor
│   ├── github.py                # GitHub Search API (public issues only)
│   ├── huggingface.py           # Dataset discussions + hub search
│   ├── alphaxiv_web.py          # Scrape AlphaXiv trending papers
│   ├── alphaxiv_digest.py       # Read AlphaXiv weekly digest from Gmail
│   └── alphaxiv_sheets.py       # (Legacy) Google Sheets reader — not active
├── scoring.py                   # Claude Haiku topic classification + relevance scoring
├── storage.py                   # SQLite for dedup + history tracking
├── notify.py                    # Slack webhook for personal alerts
├── requirements.txt
├── .env.example
└── .gitignore
```

**Dependencies:** `python-dotenv`, `anthropic`, `requests`, `praw`, `huggingface_hub`, `google-api-python-client`, `google-auth-oauthlib`

---

## Sources (All Read-Only)

### Reddit (`sources/reddit.py`)
- Uses PRAW in **read-only mode** to search a small set of subreddits for keyword matches
- Monitored subreddits: `r/MachineLearning`, `r/LocalLLaMA`, `r/SaaS`, `r/indiehackers`
- Reads post titles and body text only — no comments, no posting, no voting
- Auth: Reddit script app (free, 100 req/min)

### GitHub (`sources/github.py`)
- GitHub REST Search API (`/search/issues`) — public issues only
- Searches for open issues mentioning data quality keywords on ML-related repos
- Auth: Personal access token (free, 30 search req/min)

### Hugging Face (`sources/huggingface.py`)
- Dataset health checks via `/is-valid` + `/statistics` endpoints
- Discussion threads on watched datasets via `huggingface_hub`
- Auth: Free HF token (1,000 req/5min)

### AlphaXiv Web (`sources/alphaxiv_web.py`)
- Scrapes the public AlphaXiv trending page for recently discussed papers
- Extracts paper metadata (title, arXiv ID, authors) from page HTML
- No authentication required

### AlphaXiv Digest (`sources/alphaxiv_digest.py`)
- Reads the weekly AlphaXiv digest email from personal Gmail (sent by `contact@alphaxiv.org`)
- Extracts arXiv paper URLs and titles from the email body
- Auth: Gmail OAuth (read-only scope, reuses existing credentials)

---

## Signal Classification

Signals are classified into topic categories using Claude Haiku:

| Category | Example Signal |
|---|---|
| **Annotation Quality** | "Our annotators disagree 40% of the time" |
| **Dataset Bias/Gaps** | "Model fails on edge cases in production" |
| **RLHF/Eval Bottleneck** | "Can't find evaluators who understand our domain" |
| **Ground Truth** | "Our 3 researchers label manually — doesn't scale" |
| **Synthetic Data Limitations** | "Generated 100K with GPT-4 but model plateaued" |
| **Tooling/Workflow** | "Looking for a Labelbox alternative" |
| **Budget/Scaling** | "Labeling is our biggest cost center" |

### Relevance Scoring (0-100)

Each signal is scored across 5 dimensions to filter noise from substantive discussions:

- **Pain Intensity** (0-25) — Is someone describing a real problem vs. theoretical discussion?
- **Urgency** (0-20) — Active problem vs. hypothetical?
- **Commercial Context** (0-20) — Production use case vs. hobby/academic?
- **Decision-Maker Proximity** (0-15) — Posted by someone with context on the problem?
- **Topic Fit** (0-20) — How relevant to data annotation/quality research?

Signals scoring >= 56 are forwarded to Slack for review. Everything is logged to SQLite regardless of score.

---

## Keyword Clusters

The tool pre-filters content using keyword clusters before sending to Claude for classification:

- **Quality issues:** annotation quality, labeling errors, noisy labels, mislabeled, inter-annotator agreement
- **Needs:** looking for annotators, need labeled data, labeling service, human evaluation
- **RLHF-specific:** RLHF data, preference data, human feedback, reward model, DPO training data
- **Tooling:** Scale AI, Labelbox, Snorkel, Appen, Surge AI, Toloka
- **Frustration:** stuck, struggling, bottleneck, tried everything
- **Synthetic data:** synthetic data quality, model collapse, GPT-generated data
- **Cost:** cost of labeling, labeling budget, annotation cost

---

## Storage

- SQLite at `data/signals.db`
- `signals` table — all classified signals with scores, category, source, timestamp
- `seen_urls` table — dedup to avoid re-processing the same content
- No ORM — direct `sqlite3`

---

## Required API Keys (all free tier)

| Key | Where to get it | Free limit |
|---|---|---|
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | https://www.reddit.com/prefs/apps (script app) | 100 req/min |
| `GITHUB_TOKEN` | https://github.com/settings/tokens (PAT) | 30 search req/min |
| `HF_TOKEN` | https://huggingface.co/settings/tokens | 1,000 req/5min |
| `ANTHROPIC_API_KEY` | Anthropic console | Pay-per-use (~$0.20/mo) |
| `SLACK_WEBHOOK_URL` | Slack app incoming webhooks | Unlimited |
| `GMAIL_CREDENTIALS_FILE` | Google Cloud Console (OAuth) | Free |

---

## Platform Compliance

- **Read-only access on all platforms** — no posting, commenting, voting, or messaging
- Rate-limited API calls to stay within free tiers
- Respects each platform's Terms of Service
- No automated engagement of any kind
- All data stored locally
