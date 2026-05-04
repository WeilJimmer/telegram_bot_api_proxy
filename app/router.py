from typing import Any, Optional

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from app.settings import API_KEY, BOT_TOKEN, TELEGRAM_API_BASE
from app.validator import is_chat_id_allowed, is_method_allowed, is_global_method_allowed

router = APIRouter()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _is_json_content_type(content_type: str) -> bool:
    """判斷 Content-Type 是否為 JSON（含 application/*+json）。"""
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


@router.post("/{method}", summary="Proxy Telegram Bot API")
async def proxy_telegram(
    method: str,
    request: Request,
    _: Optional[str] = Depends(verify_api_key),
):
    content_type = request.headers.get("content-type", "")
    is_json_request = _is_json_content_type(content_type)

    # ── Step 1：解析 Request Body ──────────────────────────
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
            raw_cid    = json_body.get("chat_id")
            chat_id    = str(raw_cid) if raw_cid is not None else None

        elif (
            "multipart/form-data" in content_type
            or "application/x-www-form-urlencoded" in content_type
        ):
            form    = await request.form()
            raw_cid = form.get("chat_id")
            chat_id = str(raw_cid) if raw_cid else None

            for key, value in form.items():
                if hasattr(value, "read"):                        # UploadFile
                    file_fields[key] = (
                        value.filename,
                        await value.read(),
                        value.content_type,
                    )
                else:
                    form_fields[key] = value

        else:
            raw_body = await request.body()

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse request body: {exc}")

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
    target_url = f"{TELEGRAM_API_BASE}/bot{BOT_TOKEN}/{method}"

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