from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from config import API_KEY, BOT_TOKEN, TELEGRAM_API_BASE
from app.validator import is_chat_id_allowed, is_method_allowed, is_global_method_allowed

router = APIRouter()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: Optional[str] = Depends(_api_key_header)) -> Optional[str]:
    """驗證代理 API Key，若 config 未設定則跳過"""
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return key


@router.post("/{method}", summary="代理 Telegram Bot API")
async def proxy_telegram(
    method: str,
    request: Request,
    _: Optional[str] = Depends(verify_api_key),
):
    content_type = request.headers.get("content-type", "")

    # ── Step 1：解析 Request Body ──────────────────────────
    json_body:   Optional[dict] = None
    form_fields: dict = {}
    file_fields: dict = {}
    raw_body:    Optional[bytes] = None
    chat_id:     Optional[str] = None

    try:
        if "application/json" in content_type:
            json_body  = await request.json()
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
        raise HTTPException(status_code=400, detail=f"請求解析失敗: {exc}")

    # ── Step 2：存取控制驗證 ────────────────────────────────
    if chat_id:
        if not is_chat_id_allowed(chat_id):
            raise HTTPException(
                status_code=403,
                detail=f"chat_id {chat_id} 不在允許清單中",
            )
        if not is_method_allowed(chat_id, method):
            raise HTTPException(
                status_code=403,
                detail=f"chat_id {chat_id} 不允許使用方法 '{method}'",
            )
    else:
        if not is_global_method_allowed(method):
            raise HTTPException(
                status_code=403,
                detail=f"方法 '{method}' 不在全域允許清單，或此方法需要 chat_id",
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
        raise HTTPException(status_code=502, detail=f"上游請求失敗: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"伺服器內部錯誤: {exc}")