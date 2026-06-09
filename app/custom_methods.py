from typing import Any, Optional

import httpx
from fastapi import HTTPException, Request

from app.settings import BOT_TOKEN, MASTER_CHAT_ID, TELEGRAM_API_BASE

# Ordered by priority: more specific (typed media) before generic document.
_MEDIA_FIELD_TO_METHOD = [
    ("photo",      "sendPhoto"),
    ("video",      "sendVideo"),
    ("audio",      "sendAudio"),
    ("animation",  "sendAnimation"),
    ("voice",      "sendVoice"),
    ("video_note", "sendVideoNote"),
    ("sticker",    "sendSticker"),
    ("document",   "sendDocument"),
    ("file",       "sendDocument"),   # non-standard alias
]


def _detect_tg_method(
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
) -> str:
    all_keys: set[str] = set()
    if json_body:
        all_keys.update(json_body.keys())
    all_keys.update(form_fields.keys())
    all_keys.update(file_fields.keys())

    if "latitude" in all_keys and "longitude" in all_keys:
        return "sendLocation"

    for field, method in _MEDIA_FIELD_TO_METHOD:
        if field in all_keys:
            return method

    return "sendMessage"


async def handle_report_to_master(
    json_body: Optional[dict[str, Any]],
    form_fields: dict,
    file_fields: dict,
    raw_body: Optional[bytes],
    content_type: str,
) -> tuple[Any, int]:
    if not MASTER_CHAT_ID:
        raise HTTPException(status_code=503, detail="MASTER_CHAT_ID is not configured on the proxy server")

    tg_method = _detect_tg_method(json_body, form_fields, file_fields)

    # Inject master chat_id and normalise file→document alias.
    if json_body is not None:
        json_body["chat_id"] = MASTER_CHAT_ID
        if "file" in json_body and tg_method == "sendDocument":
            json_body.setdefault("document", json_body.pop("file"))
    elif form_fields or file_fields:
        form_fields["chat_id"] = str(MASTER_CHAT_ID)
        if "file" in file_fields and tg_method == "sendDocument":
            file_fields["document"] = file_fields.pop("file")

    target_url = f"{TELEGRAM_API_BASE}/bot{BOT_TOKEN}/{tg_method}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if json_body is not None:
                resp = await client.post(target_url, json=json_body)
            elif form_fields or file_fields:
                resp = await client.post(
                    target_url,
                    data=form_fields or None,
                    files=file_fields or None,
                )
            else:
                resp = await client.post(
                    target_url,
                    content=raw_body,
                    headers={"content-type": content_type} if content_type else {},
                )
        return resp.json(), resp.status_code
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")
