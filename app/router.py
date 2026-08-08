from typing import Any, NamedTuple, Optional

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from app.settings import API_KEY, TELEGRAM_API_BASE
from app.bot_profiles import (
    BOT_PROFILE_HEADER,
    assert_bot_profile_name_is_supplied,
    get_bot_token_by_profile_name,
)
from app.validator import is_chat_id_allowed, is_method_allowed, is_global_method_allowed
from app.custom_methods import (
    handle_ask_master_for_permission,
    handle_get_result_from_master,
    handle_report_to_master,
)

router = APIRouter()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ParsedRequest(NamedTuple):
    json_body: Optional[dict[str, Any]]
    form_fields: dict
    file_fields: dict
    raw_body: Optional[bytes]
    chat_id: Optional[str]
    bot_profile_name: Optional[str]
    bot_token: str


def _is_json_content_type(content_type: str) -> bool:
    mime_type = content_type.split(";", 1)[0].strip().lower()
    return mime_type == "application/json" or mime_type.endswith("+json")


def _normalize_method_and_fields(
    method: str,
    json_body: Optional[dict[str, Any]],
    form_fields: dict,
    file_fields: dict,
) -> str:
    if method != "sendFile":
        return method

    if json_body is not None and "file" in json_body:
        json_body.setdefault("document", json_body.pop("file"))

    if "file" in form_fields:
        form_fields.setdefault("document", form_fields.pop("file"))

    if "file" in file_fields:
        file_fields.setdefault("document", file_fields.pop("file"))

    return "sendDocument"


async def verify_api_key(key: Optional[str] = Depends(_api_key_header)) -> Optional[str]:
    """驗證代理 API Key，若 config 未設定則跳過"""
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return key


def _get_bot_profile_name_from_header(request: Request) -> Optional[str]:
    """
    Args:
        request: 進來的 FastAPI Request, example: POST /sendMessage (header X-MY-NAME: ariel)
    Return:
        Optional[str]  從 X-MY-NAME header 讀到的 profile name；呼叫端沒帶時為 None
        header 存在但值為空字串 -> 回傳空字串，之後會被當成未知名字拒絕（403）
    """
    raw_profile_name = request.headers.get(BOT_PROFILE_HEADER)
    if raw_profile_name is None:
        return None
    return str(raw_profile_name).strip()


async def _parse_request_body(request: Request) -> ParsedRequest:
    """
    Args:
        request: 進來的 FastAPI Request, example: POST /sendMessage
    Return:
        ParsedRequest  不含該次要使用的 bot_token
        body 無法解析 -> HTTPException 400
    """
    content_type = request.headers.get("content-type", "")
    is_json_request = _is_json_content_type(content_type)

    json_body:   Optional[dict[str, Any]] = None
    form_fields: dict = {}
    file_fields: dict = {}
    raw_body:    Optional[bytes] = None
    chat_id:     Optional[str] = None

    try:
        if is_json_request:
            raw_payload = await request.body()
            try:
                parsed = json.loads(raw_payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=400, detail=f"Failed to decode JSON payload: {exc}")

            if not isinstance(parsed, dict):
                raise HTTPException(status_code=400, detail="JSON body must be an object, for example {\"chat_id\":\"123\",\"text\":\"hi\"}")

            json_body = parsed
            raw_cid   = json_body.get("chat_id")
            chat_id   = str(raw_cid) if raw_cid is not None else None

        elif (
            "multipart/form-data" in content_type
            or "application/x-www-form-urlencoded" in content_type
        ):
            form    = await request.form()
            raw_cid = form.get("chat_id")
            chat_id = str(raw_cid) if raw_cid else None

            for key, value in form.items():
                if hasattr(value, "read"):
                    file_fields[key] = (
                        value.filename,
                        await value.read(),
                        value.content_type,
                    )
                else:
                    form_fields[key] = value

        else:
            raw_body = await request.body()

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse request body: {exc}")

    profile_name = _get_bot_profile_name_from_header(request)
    assert_bot_profile_name_is_supplied(profile_name)
    bot_token = get_bot_token_by_profile_name(profile_name)

    return ParsedRequest(
        json_body, form_fields, file_fields, raw_body, chat_id, profile_name, bot_token
    )


@router.post("/askMasterForPermission", summary="Send a poll to master and return a poll token (non-official)")
async def ask_master_for_permission(
    request: Request,
    _: Optional[str] = Depends(verify_api_key),
):
    """Ask the master for permission via a Telegram poll.

    Accepts JSON or multipart/form-data. Special fields (stripped before forwarding):
    - question (str, required): Poll question text, max 300 chars.
    - options (JSON array | str, required): 2–10 option strings, max 100 chars each.

    Any media fields (photo/video/audio/document/file/animation/voice/video_note/sticker
    or latitude+longitude) are sent as a separate message to master BEFORE the poll.

    Returns poll_token to be used later with getResultFromMaster.
    """
    content_type = request.headers.get("content-type", "")
    parsed = await _parse_request_body(request)
    json_body, form_fields, file_fields = parsed.json_body, parsed.form_fields, parsed.file_fields

    # Extract question and options; leave only media fields in the body dicts.
    if json_body is not None:
        question = json_body.pop("question", "")
        raw_options = json_body.pop("options", [])
    else:
        question = str(form_fields.pop("question", ""))
        raw_options = form_fields.pop("options", "[]")

    if isinstance(raw_options, str):
        try:
            options = json.loads(raw_options)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"options must be a JSON array: {exc}")
    else:
        options = raw_options

    if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
        raise HTTPException(status_code=400, detail="options must be a JSON array of strings")

    result = await handle_ask_master_for_permission(
        parsed.bot_profile_name,
        parsed.bot_token,
        question,
        options,
        json_body,
        form_fields,
        file_fields,
        content_type,
    )
    return JSONResponse(content=result)


@router.post("/getResultFromMaster", summary="Stop a master poll and retrieve results (non-official)")
async def get_result_from_master(
    request: Request,
    _: Optional[str] = Depends(verify_api_key),
):
    """Stop the Telegram poll identified by poll_token and return the vote results.

    Accepts JSON or multipart/form-data with:
    - poll_token (str, required): the token returned by askMasterForPermission.

    Calls Telegram stopPoll; once stopped the poll cannot be stopped again.
    The poll is always read back with the bot that created it, so X-MY-NAME is
    optional here; if given it must match the bot that asked.
    """
    parsed = await _parse_request_body(request)

    if parsed.json_body is not None:
        poll_token = str(parsed.json_body.get("poll_token", ""))
    else:
        poll_token = str(parsed.form_fields.get("poll_token", ""))

    result, status_code = await handle_get_result_from_master(parsed.bot_profile_name, poll_token)
    return JSONResponse(content=result, status_code=status_code)


@router.post("/reportToMaster", summary="Report to master (non-official)")
async def report_to_master(
    request: Request,
    _: Optional[str] = Depends(verify_api_key),
):
    """Send any supported content to the configured MASTER_CHAT_ID.

    The Telegram method is auto-detected from the payload fields
    (photo/video/audio/animation/voice/video_note/sticker/document/file/location → text fallback).
    The chat_id in the payload is ignored; MASTER_CHAT_ID from server config is always used.
    """
    content_type = request.headers.get("content-type", "")
    parsed = await _parse_request_body(request)

    result, status_code = await handle_report_to_master(
        parsed.bot_token,
        parsed.json_body,
        parsed.form_fields,
        parsed.file_fields,
        parsed.raw_body,
        content_type,
    )
    return JSONResponse(content=result, status_code=status_code)


@router.post("/{method}", summary="Proxy Telegram Bot API")
async def proxy_telegram(
    method: str,
    request: Request,
    _: Optional[str] = Depends(verify_api_key),
):
    content_type = request.headers.get("content-type", "")
    parsed = await _parse_request_body(request)
    json_body, form_fields, file_fields = parsed.json_body, parsed.form_fields, parsed.file_fields
    raw_body, chat_id = parsed.raw_body, parsed.chat_id

    method = _normalize_method_and_fields(method, json_body, form_fields, file_fields)

    # ── Step 2：存取控制驗證 ────────────────────────────────
    if chat_id:
        if not is_chat_id_allowed(chat_id):
            raise HTTPException(
                status_code=403,
                detail=f"chat_id {chat_id} is not in the allowlist",
            )
        if not is_method_allowed(chat_id, method):
            raise HTTPException(
                status_code=403,
                detail=f"chat_id {chat_id} is not allowed to use method '{method}'",
            )
    else:
        if not is_global_method_allowed(method):
            raise HTTPException(
                status_code=403,
                detail=f"method '{method}' is not in the global allowlist, or this method requires chat_id",
            )

    # ── Step 3：轉發至 Telegram API ─────────────────────────
    target_url = f"{TELEGRAM_API_BASE}/bot{parsed.bot_token}/{method}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:

            if json_body is not None:
                resp = await client.post(target_url, json=json_body)

            elif form_fields or file_fields:
                resp = await client.post(
                    target_url,
                    data=form_fields  or None,
                    files=file_fields or None,
                )

            else:
                resp = await client.post(
                    target_url,
                    content=raw_body,
                    headers={"content-type": content_type} if content_type else {},
                )

        return JSONResponse(content=resp.json(), status_code=resp.status_code)

    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")
