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

# --- AlphaXiv Web Scraping ---
ALPHAXIV_TRENDING_URL = os.getenv("ALPHAXIV_TRENDING_URL", "https://alphaxiv.org/explore")

# --- AlphaXiv Gmail Digest ---
ALPHAXIV_GMAIL_QUERY = os.getenv(
    "ALPHAXIV_GMAIL_QUERY",
    'from:contact@alphaxiv.org subject:"Trending Papers" newer_than:7d',
)

# --- Gmail OAuth (reuses auto-bdr credentials) ---
GMAIL_CREDENTIALS_FILE = os.getenv(
    "GMAIL_CREDENTIALS_FILE",
    str(PROJECT_DIR.parent / "auto-bdr" / "client_secret_360799449442-9kqasva5frsqjbu03s3bdl28r5djt21g.apps.googleusercontent.com.json"),
)
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", str(PROJECT_DIR.parent / "auto-bdr" / "token.json"))
GMAIL_TOKEN_JSON = os.getenv("GMAIL_TOKEN_JSON", "")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# --- Claude ---
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# --- Scoring ---
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "71"))
HF_SCORE_THRESHOLD = int(os.getenv("HF_SCORE_THRESHOLD", "20"))

# --- Reddit subreddits to monitor ---
SUBREDDITS = [
    "MachineLearning",
    "LocalLLaMA",
    "SaaS",
    "indiehackers",
]

# --- GitHub repos to prioritize (owner/repo) ---
# Focus: repos where ML practitioners doing post-training (RLHF, DPO, fine-tune, eval)
# file issues about data quality. These users ARE the ICP, not researchers or tool devs.
GITHUB_PRIORITY_REPOS = [
    # Annotation / label quality tools — users here have noisy label pain
    "HumanSignal/label-studio",
    "argilla-io/argilla",
    "cleanlab/cleanlab",       # Tool for finding label noise — users ARE experiencing it
    "snorkel-team/snorkel",    # Programmatic labeling frustration
    # RLHF / post-training — preference data quality complaints live here
    "huggingface/trl",         # RLHF/DPO/PPO library, post-training teams
    # Eval reliability — teams discovering ground truth is noisy
    "EleutherAI/lm-evaluation-harness",
    "openai/evals",
    "confident-ai/deepeval",   # LLM eval reliability, direct ICP
    # Fine-tuning practitioners — training data quality complaints
    "huggingface/peft",          # Parameter-efficient fine-tuning, active practitioner community
    "axolotl-ai-co/axolotl",     # Fine-tuning framework, lots of training data pain
]

# --- GitHub repos to exclude from global keyword searches ---
# These consistently produce false positives: tool bug trackers, personal pages, etc.
GITHUB_EXCLUDED_REPOS = [
    "anthropics/claude-code",       # Claude Code bug tracker — not annotation buyers
    "anthropics/anthropic-sdk-python",
    "anthropics/claude-cookbook",
]

# --- GitHub global search queries (Plan C: broad OR queries, replaces narrow per-keyword loop) ---
# Each query appends: is:issue is:open created:>{lookback} + repo exclusions
GITHUB_SEARCH_QUERIES = [
    # Core annotation pain
    '"annotation quality" OR "label noise" OR "noisy labels" OR "bad labels" OR "mislabeled" OR "inter-annotator"',
    # RLHF/preference data (post-training specific)
    '"preference data" OR "RLHF data" OR "reward model" OR "DPO data" OR "alignment data"',
    # Buying intent — direct vendor search
    '"looking for annotators" OR "labeling service" OR "annotation vendor" OR "need labeled data" OR "human raters"',
    # Competitor frustration
    '"Scale AI" OR "Appen" OR "MTurk" OR "Surge AI" OR "Labelbox" OR "Toloka"',
    # Synthetic disillusionment + training data failure
    '"synthetic data" OR "GPT-generated" OR "model collapse" OR "LLM-generated" "quality" OR "not working" OR "degraded"',
]

# --- Lookback window for GitHub issue scanning ---
GITHUB_LOOKBACK_DAYS = 14

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
    "LLM-generated training data", "LLM-generated labels",
    "AI-generated training data", "synthetic not working", "synthetic data failure",
]

POST_TRAINING_KEYWORDS = [
    "fine-tune not working", "fine-tuning quality", "RLHF not converging",
    "reward hacking", "preference disagreement", "eval not reliable",
    "benchmark noise", "ground truth noise", "evaluation reliability",
    "training data noise", "annotation consistency",
]

BUDGET_KEYWORDS = [
    "cost of labeling", "labeling budget", "annotation cost",
    "too expensive", "affordable labeling", "cost per label",
]

# All keywords combined (used for fast pre-filtering)
ALL_KEYWORDS = (
    PAIN_KEYWORDS + NEED_KEYWORDS + RLHF_KEYWORDS +
    COMPETITOR_KEYWORDS + FRUSTRATION_KEYWORDS +
    SYNTHETIC_DISILLUSIONMENT_KEYWORDS + BUDGET_KEYWORDS +
    POST_TRAINING_KEYWORDS
)

# --- Paths ---
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "signals.db"

# --- Cross-tool dedup ---
AUTO_BDR_OUTREACH_LOG = os.getenv(
    "AUTO_BDR_OUTREACH_LOG",
    str(PROJECT_DIR.parent / "auto-bdr" / "data" / "outreach_log.csv"),
)
