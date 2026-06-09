from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.settings import BOT_TOKEN, MASTER_CHAT_ID, TELEGRAM_API_BASE
from app.poll_store import delete_poll, generate_poll_token, load_poll, save_poll

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
_LOCATION_FIELDS = {"latitude", "longitude"}


def _collect_keys(
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
) -> set[str]:
    all_keys: set[str] = set()
    if json_body:
        all_keys.update(json_body.keys())
    all_keys.update(form_fields.keys())
    all_keys.update(file_fields.keys())
    return all_keys


def _detect_tg_method(
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
) -> str:
    all_keys = _collect_keys(json_body, form_fields, file_fields)

    if _LOCATION_FIELDS <= all_keys:
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
    all_keys = _collect_keys(json_body, form_fields, file_fields)
    return bool(all_keys & (_MEDIA_FIELDS | _LOCATION_FIELDS))


def _prepare_master_payload(
    tg_method: str,
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
) -> None:
    """Lock the payload to MASTER_CHAT_ID and normalise the file→document alias, in place."""
    if json_body is not None:
        json_body["chat_id"] = MASTER_CHAT_ID
        if tg_method == "sendDocument" and "file" in json_body:
            json_body.setdefault("document", json_body.pop("file"))
    elif form_fields or file_fields:
        form_fields["chat_id"] = str(MASTER_CHAT_ID)
        if tg_method == "sendDocument" and "file" in file_fields:
            file_fields["document"] = file_fields.pop("file")


async def _send_to_telegram(
    tg_method: str,
    json_body: Optional[dict],
    form_fields: dict,
    file_fields: dict,
    raw_body: Optional[bytes] = None,
    content_type: str = "",
) -> tuple[dict[str, Any], int]:
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
    _prepare_master_payload(tg_method, json_body, form_fields, file_fields)

    return await _send_to_telegram(
        tg_method, json_body, form_fields, file_fields, raw_body, content_type
    )


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
    if len(options) > 9:
        raise HTTPException(status_code=400, detail="at most 9 options are allowed (the master may add more, up to Telegram's limit of 10)")
    for opt in options:
        if not opt or not opt.strip():
            raise HTTPException(status_code=400, detail="option text must not be empty")
        if len(opt) > 100:
            raise HTTPException(status_code=400, detail=f"option '{opt[:20]}…' exceeds 100 characters (Telegram limit)")

    # Step 1: If media is present, send it first as a standalone message.
    if _has_media(media_json_body, media_form_fields, media_file_fields):
        media_tg_method = _detect_tg_method(media_json_body, media_form_fields, media_file_fields)
        _prepare_master_payload(media_tg_method, media_json_body, media_form_fields, media_file_fields)
        await _send_to_telegram(
            media_tg_method, media_json_body, media_form_fields, media_file_fields, None, content_type
        )

    # Step 2: Send the poll to master.
    poll_payload: dict[str, Any] = {
        "chat_id": MASTER_CHAT_ID,
        "question": question.strip(),
        "options": [{"text": opt.strip()} for opt in options],
        "type": "regular",
        "is_anonymous": False,
        "allows_multiple_answers": True,
        "allow_adding_options": True,
    }

    poll_resp, _ = await _send_to_telegram("sendPoll", poll_payload, {}, {})

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

def _summarize_poll_result(stop_poll_resp: dict) -> tuple[bool, list[str], str]:
    """Turn a stopPoll response into (answered, chosen_options, human_message)."""
    poll = stop_poll_resp.get("result") or {}
    options = poll.get("options") or []

    chosen = [opt.get("text", "") for opt in options if opt.get("voter_count", 0) > 0]

    if not chosen:
        return False, [], "Master hasn't answered yet! Ask again?"

    if len(chosen) == 1:
        return True, chosen, f"Master chose [{chosen[0]}] option."

    joined = ", ".join(f"[{text}]" for text in chosen)
    return True, chosen, f"Master chose {joined} options."



async def handle_get_result_from_master(poll_token: str) -> tuple[Any, int]:
    if not poll_token or not poll_token.strip():
        raise HTTPException(status_code=400, detail="poll_token is required")

    poll_token = poll_token.strip()
    poll_data = load_poll(poll_token)
    if poll_data is None:
        raise HTTPException(status_code=404, detail=f"poll_token '{poll_token}' not found")

    stop_poll_resp, _ = await _send_to_telegram(
        "stopPoll",
        {
            "chat_id": poll_data["master_chat_id"],
            "message_id": poll_data["telegram_poll_message_id"],
        },
        {},
        {},
    )

    succeeded = bool(stop_poll_resp.get("ok"))
    if not succeeded:
        return {
            "ok": False,
            "poll_token": poll_token,
            "question": poll_data["question"],
            "options": poll_data["options"],
            "answered": False,
            "chosen_options": [],
            "message": f"Failed to read the poll: {stop_poll_resp.get('description', stop_poll_resp)}",
            "telegram_result": stop_poll_resp,
        }, 502

    # Poll is now in a terminal state and cannot be stopped again; drop the token.
    delete_poll(poll_token)

    answered, chosen_options, message = _summarize_poll_result(stop_poll_resp)

    return {
        "ok": True,
        "poll_token": poll_token,
        "question": poll_data["question"],
        "options": poll_data["options"],
        "answered": answered,
        "chosen_options": chosen_options,
        "message": message,
        "telegram_result": stop_poll_resp,
    }, 200
