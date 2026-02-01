# Data Deal Monitoring

Automated discovery of high-intent AI data prospects for Anthromind. Monitors developer platforms for signals of data quality pain — labeling issues, evaluation bottlenecks, dataset complaints, competitor frustration — and surfaces only true leads to Slack.

Based on: `Finding Hidden Data Deals.pdf`

**Cost target:** <$1/month (all free APIs + Claude Haiku scoring)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env
# Edit .env with your keys (each source gracefully skips if its key is missing)

# Run the monitor
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
│   ├── reddit.py                # PRAW keyword monitor (100 req/min free)
│   ├── github.py                # GitHub Search API (30 req/min free)
│   ├── huggingface.py           # Dataset Viewer + Hub discussions (1,000 req/5min free)
│   └── alphaxiv.py              # Pull curated papers from Google Sheet
├── scoring.py                   # Claude Haiku multi-dimensional intent scoring
├── storage.py                   # SQLite for dedup + history tracking
├── notify.py                    # Slack webhook — only fires for true leads
├── requirements.txt
├── .env.example
└── .gitignore
```

**Dependencies:** `python-dotenv`, `anthropic`, `requests`, `praw`, `huggingface_hub`, `gspread`, `google-auth`

Follows the same patterns as `signals-tool` and `auto-bdr`: modular sources, `config.py` as single source of truth, `python-dotenv` for env management, graceful degradation if a source fails.

---

## Intent Signal Strategy

The difference between a useful monitoring tool and a spammy one is whether we catch real pain or just keyword noise. The system uses a two-stage approach: **keyword filtering** (fast, cheap) followed by **Claude Haiku intent scoring** (smart, still cheap).

### Pain Signal Categories

Each signal gets classified into one of these categories by Haiku:

| Category | What it looks like | Why it's a lead |
|---|---|---|
| **Annotation Quality** | "Our annotators disagree 40% of the time", "had to throw out a batch of labels" | They need expert, consistent annotation |
| **Dataset Bias/Gaps** | "Model fails on edge cases", "training set over-represents X" | They need curated, representative data |
| **RLHF/Eval Bottleneck** | "Can't find evaluators who understand our domain", "reward model is hacking" | RLHF requires sustained skilled human judgment — Anthromind's sweet spot |
| **Ground Truth** | "We need board-certified radiologists to label", "our 3 researchers label manually" | They value quality but can't scale their internal team |
| **Synthetic Data Disillusionment** | "Generated 100K with GPT-4 but model plateaued", "distillation not working" | They tried the cheap path, hit its ceiling, now ready to invest in human data |
| **Competitor Frustration** | "Scale AI quality dropped", "looking for Labelbox alternative" | Active buyer, switching from a competitor |
| **Budget/Scaling** | "Labeling is our biggest cost center", "need quality AND reasonable cost" | Already spending money, looking for better value |

### High-Intent vs. Low-Intent Signals

**True leads say things like:**
- "We tried X and it failed" (past tense failure + present tense urgency)
- "Can anyone recommend a labeling service for [domain]?" (active buying)
- "Our team of 3 has been labeling manually for months. This doesn't scale." (scaling wall)
- "We're paying enterprise prices to Scale but getting crowd-quality results" (competitor churn)
- "Our model works on English but falls apart on [language]" (coverage gap with production consequence)

**False positives to filter out:**
- Academic theoreticians ("In this survey, we propose..." — writing about problems, not experiencing them)
- Students ("How do I label 500 tweets for my class project?" — no budget, small scale)
- Solved problems ("Here's how we fixed it..." — past tense with resolution, not seeking help)
- Competitor marketing ("Introducing our new annotation platform..." — selling, not buying)
- News sharing (link posts with brief "interesting" commentary, no personal context)
- Tool builders who solved tooling but may not need workforce (unless they explicitly say they need annotators)

**Key differentiator:** Real pain is past/present tense with consequences. Academic discussion is general tense without personal stakes.

### Platform-Specific Signal Patterns

**Reddit:**
- `r/LocalLLaMA` — highest practitioner concentration. People fine-tuning models and needing data. "My fine-tuned model is worse than base" is often a data quality issue.
- `r/MachineLearning` — look for [D] Discussion and [P] Project tags. "We deployed and discovered [data issue] in production" = commercial context.
- `r/SaaS` + `r/indiehackers` — founders with budget and authority. "Building an AI product and the data piece is killing us."
- **Comments are often better signals than posts.** Someone replying "yeah, we have the same issue and haven't solved it" IS a lead.
- Posts older than 48 hours get dramatically less engagement — prioritize fresh signals.

**GitHub:**
- Pain is indirect. Issues on ML framework repos describe *symptoms* whose root cause is data quality.
- Issues on labeling tool repos (Label Studio, Argilla, CVAT) where users describe workflows breaking at scale — they have tooling, need workforce.
- Feature requests on eval frameworks (lm-evaluation-harness) for custom eval criteria — building serious eval pipeline.
- Stalled PRs that modify training data with months of quality discussion — they care about quality but lack resources.

**Hugging Face:**
- Dataset discussion threads: comments reporting specific errors ("Row 45321 has label X but should be Y") = someone doing quality validation for a real use case.
- "Is this dataset suitable for [commercial use case]?" = commercial intent.
- Model discussions: "I fine-tuned on [dataset] and got poor results" = possible data quality root cause.
- People building annotation/evaluation Spaces = actively working on the problem.

---

## Scoring Framework (`scoring.py`)

Each signal is scored by Claude Haiku across 5 dimensions. Total score 0-100.

### Dimension 1: Pain Intensity (0-25 pts)

| Score | Signal |
|---|---|
| 0-5 | Theoretical discussion, no personal pain |
| 6-10 | Early exploration ("thinking about", "curious how") |
| 11-15 | Active problem ("we're struggling with", "our model isn't working because") |
| 16-20 | Quantified impact ("wasted $X", "delayed Y weeks", "accuracy dropped Z%") |
| 21-25 | Crisis ("blocking our launch", "tried everything", "biggest customer threatening to leave") |

Modifiers: +3 if multiple failed approaches described. +2 if cost quantified in dollars/time. -5 if pain in past tense with resolution.

### Dimension 2: Urgency (0-20 pts)

| Score | Signal |
|---|---|
| 0-4 | No time context |
| 5-8 | Ongoing concern, no deadline |
| 9-12 | Active current project ("we're currently", "right now") |
| 13-16 | Near-term deadline ("need by Q2", "launching next month") |
| 17-20 | Immediate ("this week", "ASAP", "blocking everything") |

Post recency penalty: 1-3 days old = -2, 1-2 weeks = -5, >2 weeks = -10.

### Dimension 3: Commercial Context (0-20 pts)

| Score | Signal |
|---|---|
| 0-4 | Hobby or academic — no commercial signals |
| 5-8 | Ambiguous |
| 9-12 | Startup signals ("our startup", "building a product") |
| 13-16 | Established company (team size, existing customers mentioned) |
| 17-20 | Enterprise (large scale, compliance language, existing vendor contracts) |

Evidence: "our product/customers/users" = commercial. Data scale 100K+ = likely commercial. Post history about building products, hiring, fundraising.

### Dimension 4: Decision-Maker Proximity (0-15 pts)

| Score | Signal |
|---|---|
| 0-3 | Unknown role |
| 4-6 | Individual contributor at a company |
| 7-9 | Team lead or senior IC |
| 10-12 | Manager or director |
| 13-15 | Founder, CTO, VP, or explicit budget owner |

Proxy: discusses budget tradeoffs = likely has authority. Posts in r/indiehackers = likely founder. "I need to convince my manager" = influencer, not decider (lower but still valuable).

### Dimension 5: Anthromind Fit (0-20 pts)

| Score | Signal |
|---|---|
| 0-4 | Doesn't match (raw data collection, not annotation) |
| 5-8 | Tangential (ML engineering help, not data services) |
| 9-12 | General fit — annotation needed but simple tasks |
| 13-16 | Strong fit — expert annotation, RLHF, specialized curation |
| 17-20 | Perfect — needs exactly what Anthromind offers + frustrated with commodity alternatives |

Amplifiers: domain expertise needed (medical, legal, code) +3. Quality over speed +2. RLHF/preference data +3. Simple binary classification at massive scale -5.

### Score Thresholds

| Total (0-100) | Classification | Action |
|---|---|---|
| 0-40 | Noise / Low Intent | Log to SQLite only. No notification. |
| 41-55 | Moderate | Log. No Slack. Available for manual review. |
| 56-70 | High Intent | **Send to Slack.** Engage within 24hrs with genuine value first. |
| 71-85 | Very High | **Priority Slack alert.** Engage within hours. Consultative approach. |
| 86-100 | Active Buyer | **Immediate Slack alert.** This person is looking for exactly what Anthromind offers right now. |

**Slack threshold: score >= 56** (configurable via `SCORE_THRESHOLD`)

---

## Keyword Clusters (`config.py`)

### Pain/Failure Keywords
```
"annotation quality", "labeling errors", "noisy labels", "inconsistent annotations",
"bad labels", "label noise", "ground truth", "mislabeled",
"inter-annotator agreement", "annotation disagreement"
```

### Need/Search Keywords
```
"looking for annotators", "need labeled data", "labeling service",
"annotation service", "data labeling vendor", "outsource annotation",
"human evaluation", "need human raters"
```

### RLHF-Specific Keywords
```
"RLHF data", "preference data", "human feedback", "reward model",
"DPO training data", "human evaluation", "red teaming",
"alignment data", "constitutional AI"
```

### Competitor Keywords
```
"Scale AI", "Labelbox", "Snorkel", "Appen", "Surge AI", "Toloka",
"MTurk", "Mechanical Turk", "SageMaker Ground Truth"
```

### Frustration Markers
```
"stuck", "struggling", "failing", "doesn't work", "tried everything",
"wasted", "threw out", "had to redo", "blocking", "bottleneck"
```

### Synthetic Data Disillusionment
```
"synthetic data quality", "model collapse", "GPT-generated data",
"synthetic vs human", "distillation not working", "LLM-generated training data"
```

### Budget Keywords
```
"cost of labeling", "labeling budget", "annotation cost",
"too expensive", "affordable labeling", "cost per label"
```

---

## Source Modules

### 1. `sources/reddit.py`
- PRAW to scan `r/MachineLearning`, `r/LocalLLaMA`, `r/SaaS`, `r/indiehackers`
- `subreddit.new(limit=100)` + `subreddit.search(query, sort="new", time_filter="day")`
- Also scan top comments on matching posts (comments often contain better signals)
- Pre-filter with keyword clusters before sending to Haiku
- Return: `{source, title, text, author, url, score, subreddit, created_utc, flair}`
- **Auth:** Reddit script app — free, 100 req/min

### 2. `sources/github.py`
- GitHub REST Search API (`/search/issues`) with PAT
- Search each keyword with: `is:issue is:open created:>YESTERDAY`
- Prioritize repos: labeling tools (Label Studio, Argilla, CVAT), ML frameworks, eval frameworks
- Return: `{source, title, text, repo, url, author, stars, created_at}`
- **Auth:** PAT — free, 30 search req/min

### 3. `sources/huggingface.py`
- **Dataset health:** `/is-valid` + `/statistics` for watched datasets
- **Discussions:** `huggingface_hub` `get_repo_discussions()` scanning for pain keywords
- **New datasets:** Hub API search for recent datasets in target domains
- Return: `{source, title, text, dataset_id, url, discussion_id, created_at}`
- **Auth:** Free HF token — 1,000 req/5min

### 4. `sources/alphaxiv.py`
- Pull from Google Sheet (manually curated AlphaXiv papers)
- `gspread` + Google service account (reuse auto-bdr credentials)
- Expected columns: title, abstract/notes, authors, paper_url, date_added
- Only process rows added since last run (track via `date_added` or "processed" column)
- Return: `{source, title, text, authors, paper_url, added_date}`
- **Auth:** Google Sheets API via service account/OAuth

---

## Storage (`storage.py`)

- SQLite at `data/signals.db`
- Tables:
  - `signals` — all raw signals: source, text, url, scores (all 5 dimensions + total), category, timestamp
  - `seen_urls` — dedup to avoid re-processing
- Cross-tool dedup: read `auto-bdr/data/outreach_log.csv` to skip already-contacted prospects
- Simple `sqlite3` — no ORM

---

## Notifications (`notify.py`)

- Slack incoming webhook (free)
- **Only fires for score >= 56** (High Intent and above)
- Format varies by score tier:
  - 56-70: standard lead notification
  - 71-85: priority flag
  - 86-100: urgent, @mention
- Message includes: score, category, pain summary, hook for engagement, source link
- Gracefully skip if `SLACK_WEBHOOK_URL` not set (print to stdout)

---

## Required API Keys (all free)

| Key | Where to get it | Free limit |
|---|---|---|
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | https://www.reddit.com/prefs/apps (script app) | 100 req/min |
| `GITHUB_TOKEN` | https://github.com/settings/tokens (PAT) | 30 search req/min |
| `HF_TOKEN` | https://huggingface.co/settings/tokens | 1,000 req/5min |
| `ANTHROPIC_API_KEY` | Anthropic console | Pay-per-use (~$0.20/mo) |
| `SLACK_WEBHOOK_URL` | Slack app incoming webhooks | Unlimited |
| `GOOGLE_SHEETS_CREDS` | Google Cloud Console (reuse from auto-bdr) | Free |
| `ALPHAXIV_SHEET_ID` | Your Google Sheet ID for curated papers | N/A |

---

## Governance

- All outreach drafts require human review before sending
- Global suppression: once a prospect is contacted on any channel, suppress everywhere
- Respect platform TOS — no automated posting on Reddit/AlphaXiv
- Evidence retention: log why each prospect was flagged and what signal triggered it
- Rate-limit API calls to stay within free tiers

---

## Implementation Order

1. **`config.py`** + **`.env.example`** + **`.gitignore`** + **`requirements.txt`**
2. **`storage.py`** — SQLite schema, dedup logic, seen_urls tracking
3. **`sources/reddit.py`** — first source (easiest to test, richest signals)
4. **`sources/github.py`** — second source
5. **`sources/huggingface.py`** — third source (dataset health + discussions)
6. **`sources/alphaxiv.py`** — fourth source (Google Sheet reader)
7. **`scoring.py`** — Claude Haiku 5-dimension scoring with structured JSON
8. **`notify.py`** — Slack webhook, tiered by score
9. **`monitor.py`** — main orchestrator
10. End-to-end test with real API keys

---

## Cost Projection (daily runs)

| Service | Monthly cost |
|---|---|
| Reddit API (PRAW) | Free |
| GitHub API | Free |
| Hugging Face API | Free |
| Google Sheets API | Free |
| Claude Haiku (scoring ~20 leads/day) | ~$0.20 |
| **Total** | **< $1/mo** |
