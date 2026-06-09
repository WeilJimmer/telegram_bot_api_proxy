from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.settings import BOT_TOKEN, MASTER_CHAT_ID, TELEGRAM_API_BASE
from app.poll_store import generate_poll_token, load_poll, save_poll

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

_MEDIA_FIELDS = {f for f, _ in _MEDIA_FIELD_TO_METHOD}


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


def _has_media(
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
) -> bool:
    all_keys: set[str] = set()
    if json_body:
        all_keys.update(json_body.keys())
    all_keys.update(form_fields.keys())
    all_keys.update(file_fields.keys())
    return bool(all_keys & (_MEDIA_FIELDS | {"latitude", "longitude"}))


async def _send_to_telegram(
    tg_method: str,
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
    raw_body: Optional[bytes],
    content_type: str,
) -> dict[str, Any]:
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
        return resp.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")


# ── reportToMaster ─────────────────────────────────────────────────────────────

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


# ── askMasterForPermission ──────────────────────────────────────────────────────

async def handle_ask_master_for_permission(
    question: str,
    options: list[str],
    media_json_body: Optional[dict[str, Any]],
    media_form_fields: dict,
    media_file_fields: dict,
    content_type: str,
) -> dict[str, Any]:
    if not MASTER_CHAT_ID:
        raise HTTPException(status_code=503, detail="MASTER_CHAT_ID is not configured on the proxy server")

    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    if len(question) > 300:
        raise HTTPException(status_code=400, detail="question must be 300 characters or fewer (Telegram limit)")

    if not options or len(options) < 2:
        raise HTTPException(status_code=400, detail="at least 2 options are required")
    if len(options) > 10:
        raise HTTPException(status_code=400, detail="at most 10 options are allowed (Telegram limit)")
    for opt in options:
        if not opt or not opt.strip():
            raise HTTPException(status_code=400, detail="option text must not be empty")
        if len(opt) > 100:
            raise HTTPException(status_code=400, detail=f"option '{opt[:20]}…' exceeds 100 characters (Telegram limit)")

    # Step 1: If media is present, send it first as a standalone message.
    if _has_media(media_json_body, media_form_fields, media_file_fields):
        media_tg_method = _detect_tg_method(media_json_body, media_form_fields, media_file_fields)

        if media_json_body is not None:
            media_json_body["chat_id"] = MASTER_CHAT_ID
            if "file" in media_json_body and media_tg_method == "sendDocument":
                media_json_body.setdefault("document", media_json_body.pop("file"))
        elif media_form_fields or media_file_fields:
            media_form_fields["chat_id"] = str(MASTER_CHAT_ID)
            if "file" in media_file_fields and media_tg_method == "sendDocument":
                media_file_fields["document"] = media_file_fields.pop("file")

        await _send_to_telegram(
            media_tg_method,
            media_json_body,
            media_form_fields,
            media_file_fields,
            None,
            content_type,
        )

    # Step 2: Send the poll to master.
    poll_payload: dict[str, Any] = {
        "chat_id": MASTER_CHAT_ID,
        "question": question.strip(),
        "options": [{"text": opt.strip()} for opt in options],
        "type": "regular",
        "is_anonymous": False,
        "allows_multiple_answers": True,
    }

    poll_resp = await _send_to_telegram(
        "sendPoll",
        poll_payload,
        {},
        {},
        None,
        "application/json",
    )

    if not poll_resp.get("ok"):
        raise HTTPException(
            status_code=502,
            detail=f"Telegram sendPoll failed: {poll_resp.get('description', poll_resp)}",
        )

    telegram_poll_message_id: int = poll_resp["result"]["message_id"]
    poll_token = generate_poll_token()

    save_poll(poll_token, {
        "poll_token": poll_token,
        "telegram_poll_message_id": telegram_poll_message_id,
        "master_chat_id": str(MASTER_CHAT_ID),
        "question": question.strip(),
        "options": [opt.strip() for opt in options],
    })

    return {
        "ok": True,
        "poll_token": poll_token,
        "telegram_poll_message_id": telegram_poll_message_id,
    }


# ── getResultFromMaster ─────────────────────────────────────────────────────────

async def handle_get_result_from_master(poll_token: str) -> tuple[Any, int]:
    if not poll_token or not poll_token.strip():
        raise HTTPException(status_code=400, detail="poll_token is required")

    poll_data = load_poll(poll_token.strip())
    if poll_data is None:
        raise HTTPException(status_code=404, detail=f"poll_token '{poll_token}' not found")

    stop_poll_resp = await _send_to_telegram(
        "stopPoll",
        {
            "chat_id": poll_data["master_chat_id"],
            "message_id": poll_data["telegram_poll_message_id"],
        },
        {},
        {},
        None,
        "application/json",
    )

    return {
        "ok": stop_poll_resp.get("ok"),
        "poll_token": poll_token,
        "question": poll_data["question"],
        "options": poll_data["options"],
        "telegram_result": stop_poll_resp,
    }, (200 if stop_poll_resp.get("ok") else 502)
