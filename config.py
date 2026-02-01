import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "data-deal-monitor/1.0")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# --- Slack ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_USER_ID = os.getenv("SLACK_USER_ID", "")

# --- Google Sheets (AlphaXiv) ---
GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_SHEETS_CREDS", "credentials.json")
ALPHAXIV_SHEET_ID = os.getenv("ALPHAXIV_SHEET_ID", "")

# --- Claude ---
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-20250414")

# --- Scoring ---
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "56"))

# --- Reddit subreddits to monitor ---
SUBREDDITS = [
    "MachineLearning",
    "LocalLLaMA",
    "SaaS",
    "indiehackers",
]

# --- GitHub repos to prioritize (owner/repo) ---
GITHUB_PRIORITY_REPOS = [
    "HumanSignal/label-studio",
    "argilla-io/argilla",
    "opencv/cvat",
    "EleutherAI/lm-evaluation-harness",
]

# --- Hugging Face datasets to watch for health/discussions ---
HF_WATCHED_DATASETS = [
    "tatsu-lab/alpaca_eval",
    "lmsys/chatbot_arena_conversations",
    "HuggingFaceH4/ultrafeedback_binarized",
]

# --- Keyword clusters ---
PAIN_KEYWORDS = [
    "annotation quality", "labeling errors", "noisy labels",
    "inconsistent annotations", "bad labels", "label noise",
    "ground truth", "mislabeled", "inter-annotator agreement",
    "annotation disagreement",
]

NEED_KEYWORDS = [
    "looking for annotators", "need labeled data", "labeling service",
    "annotation service", "data labeling vendor", "outsource annotation",
    "human evaluation", "need human raters",
]

RLHF_KEYWORDS = [
    "RLHF data", "preference data", "human feedback", "reward model",
    "DPO training data", "human evaluation", "red teaming",
    "alignment data", "constitutional AI",
]

COMPETITOR_KEYWORDS = [
    "Scale AI", "Labelbox", "Snorkel", "Appen", "Surge AI", "Toloka",
    "MTurk", "Mechanical Turk", "SageMaker Ground Truth",
]

FRUSTRATION_KEYWORDS = [
    "stuck", "struggling", "failing", "doesn't work", "tried everything",
    "wasted", "threw out", "had to redo", "blocking", "bottleneck",
]

SYNTHETIC_DISILLUSIONMENT_KEYWORDS = [
    "synthetic data quality", "model collapse", "GPT-generated data",
    "synthetic vs human", "distillation not working",
    "LLM-generated training data",
]

BUDGET_KEYWORDS = [
    "cost of labeling", "labeling budget", "annotation cost",
    "too expensive", "affordable labeling", "cost per label",
]

# All keywords combined (used for fast pre-filtering)
ALL_KEYWORDS = (
    PAIN_KEYWORDS + NEED_KEYWORDS + RLHF_KEYWORDS +
    COMPETITOR_KEYWORDS + FRUSTRATION_KEYWORDS +
    SYNTHETIC_DISILLUSIONMENT_KEYWORDS + BUDGET_KEYWORDS
)

# --- Paths ---
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "signals.db"

# --- Cross-tool dedup ---
AUTO_BDR_OUTREACH_LOG = os.getenv(
    "AUTO_BDR_OUTREACH_LOG",
    str(PROJECT_DIR.parent / "auto-bdr" / "data" / "outreach_log.csv"),
)
