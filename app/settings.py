import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_FILE = BASE_DIR / ".env"
DOTENV_SAMPLE_FILE = BASE_DIR / ".env.sample"

# 優先使用正式環境 .env；若不存在則讀取 .env.sample 作為預設設定。
_load_file = DOTENV_FILE if DOTENV_FILE.exists() else DOTENV_SAMPLE_FILE
if _load_file.exists():
    load_dotenv(_load_file, override=True)


def _parse_json_env(name: str, default: Any) -> Any:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Environment variable {name} is not valid JSON: {exc}") from exc


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"Environment variable {name} must be a boolean (true/false)")


BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")
MASTER_CHAT_ID = os.getenv("MASTER_CHAT_ID", "")

# Poll storage: Redis if REDIS_URL is set, otherwise local filesystem.
REDIS_URL = os.getenv("REDIS_URL", "")
POLL_STORE_DIR = os.getenv("POLL_STORE_DIR", "/tmp/tg_proxy_polls")

API_KEY = os.getenv("API_KEY", "your_proxy_api_key_here")

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = _parse_int_env("SERVER_PORT", 15820)

ALLOWED_CHAT_IDS = _parse_json_env("ALLOWED_CHAT_IDS", ["*"])
ALLOWED_METHODS = _parse_json_env("ALLOWED_METHODS", {"*": ["*"]})
GLOBAL_ALLOWED_METHODS = _parse_json_env("GLOBAL_ALLOWED_METHODS", ["getMe"])

if not isinstance(ALLOWED_CHAT_IDS, list):
    raise ValueError("Environment variable ALLOWED_CHAT_IDS must be a JSON array")

if not isinstance(ALLOWED_METHODS, dict):
    raise ValueError("Environment variable ALLOWED_METHODS must be a JSON object")

if not isinstance(GLOBAL_ALLOWED_METHODS, list):
    raise ValueError("Environment variable GLOBAL_ALLOWED_METHODS must be a JSON array")

# 多重身份：BOT_TOKENS 是 token 陣列，第 0 組為預設身份；
# BOT_TOKEN_PROFILES 把呼叫端帶的 profile name 對應到 BOT_TOKENS 的索引。
BOT_TOKENS = _parse_json_env("BOT_TOKENS", [BOT_TOKEN])
BOT_TOKEN_PROFILES = _parse_json_env("BOT_TOKEN_PROFILES", {})
IS_BOT_PROFILE_REQUIRED = _parse_bool_env("IS_BOT_PROFILE_REQUIRED", False)

if not isinstance(BOT_TOKENS, list) or not BOT_TOKENS:
    raise ValueError("Environment variable BOT_TOKENS must be a non-empty JSON array of bot tokens")

for position, token in enumerate(BOT_TOKENS):
    if not isinstance(token, str) or not token.strip():
        raise ValueError(f"Environment variable BOT_TOKENS[{position}] must be a non-empty string")

if not isinstance(BOT_TOKEN_PROFILES, dict):
    raise ValueError(
        "Environment variable BOT_TOKEN_PROFILES must be a JSON object mapping profile name to a BOT_TOKENS index"
    )

for profile_name, token_index in BOT_TOKEN_PROFILES.items():
    # bool 是 int 的子類，但 {"ariel": true} 幾乎必然是打錯，不要默默當成索引 1。
    if not isinstance(token_index, int) or isinstance(token_index, bool):
        raise ValueError(
            f"BOT_TOKEN_PROFILES['{profile_name}'] must be an integer index into BOT_TOKENS"
        )
    if not 0 <= token_index < len(BOT_TOKENS):
        raise ValueError(
            f"BOT_TOKEN_PROFILES['{profile_name}'] index {token_index} is out of range; "
            f"BOT_TOKENS has {len(BOT_TOKENS)} entries"
        )

if IS_BOT_PROFILE_REQUIRED and not BOT_TOKEN_PROFILES:
    raise ValueError(
        "IS_BOT_PROFILE_REQUIRED is on but BOT_TOKEN_PROFILES is empty; every request would be rejected"
    )
