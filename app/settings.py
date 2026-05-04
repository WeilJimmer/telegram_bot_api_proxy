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


BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")

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
