"""
Poll token storage backend.

Defaults to local filesystem (POLL_STORE_DIR).
Set REDIS_URL to switch to Redis instead.
"""
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from app.settings import POLL_STORE_DIR, REDIS_URL

_redis_client = None
if REDIS_URL:
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    except ImportError as exc:
        raise RuntimeError(
            "The 'redis' package is required when REDIS_URL is set. "
            "Run: pip install redis"
        ) from exc


def generate_poll_token() -> str:
    return str(uuid.uuid4())


def save_poll(poll_token: str, data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    if _redis_client:
        _redis_client.set(f"tg_poll:{poll_token}", payload)
        return
    path = Path(POLL_STORE_DIR) / f"{poll_token}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def load_poll(poll_token: str) -> Optional[dict[str, Any]]:
    if _redis_client:
        raw = _redis_client.get(f"tg_poll:{poll_token}")
        return json.loads(raw) if raw else None
    path = Path(POLL_STORE_DIR) / f"{poll_token}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
