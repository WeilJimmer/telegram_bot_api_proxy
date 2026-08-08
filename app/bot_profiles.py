"""
Bot 身份選擇：把 profile name 換成該用哪一組 bot token。

未知的 profile name 一律拒絕，不會退回預設身份 — 打錯名字要看得到錯誤，
而不是安靜地用別人的身份把訊息送出去。
"""
from typing import Optional

from fastapi import HTTPException

from app.settings import BOT_TOKENS, BOT_TOKEN_PROFILES, IS_BOT_PROFILE_REQUIRED

# 呼叫端用來指定身份的 header 名稱；proxy 用它選 bot token，不會轉發給 Telegram。
BOT_PROFILE_HEADER = "X-MY-NAME"
# 舊稱：my_name 過去是 body 欄位（JSON / form-data），現已遷移到 header，此名僅保留給錯誤訊息使用。
BOT_PROFILE_FIELD = "my_name"

_DEFAULT_BOT_TOKEN_INDEX = 0


def list_bot_profile_names() -> list[str]:
    """
    Return:
        list[str]  已設定的 profile 名稱，example: ["ariel", "bob"]；沒設定時為 []
    """
    return sorted(BOT_TOKEN_PROFILES.keys())


def assert_bot_profile_name_is_supplied(profile_name: Optional[str]) -> None:
    """
    Args:
        profile_name: 請求帶的 profile name（來自 X-MY-NAME header）, example: "ariel"；呼叫端沒帶時為 None
    Return:
        None  IS_BOT_PROFILE_REQUIRED 為開且沒帶名字 -> HTTPException 400
    """
    if IS_BOT_PROFILE_REQUIRED and profile_name is None:
        raise HTTPException(
            status_code=400,
            detail=f"{BOT_PROFILE_HEADER} header is required; allowed values: {list_bot_profile_names()}",
        )


def get_bot_token_by_profile_name(profile_name: Optional[str]) -> str:
    """
    Args:
        profile_name: profile 名稱（來自 X-MY-NAME header）, example: "ariel"；None 代表使用預設身份
    Return:
        str  要用來發送的 bot token；None -> BOT_TOKENS[0]
        名字不在 BOT_TOKEN_PROFILES 內 -> HTTPException 403
    """
    if profile_name is None:
        return BOT_TOKENS[_DEFAULT_BOT_TOKEN_INDEX]

    if profile_name not in BOT_TOKEN_PROFILES:
        raise HTTPException(
            status_code=403,
            detail=f"unknown {BOT_PROFILE_HEADER} '{profile_name}'; allowed values: {list_bot_profile_names()}",
        )

    return BOT_TOKENS[BOT_TOKEN_PROFILES[profile_name]]
