from typing import List
from app.settings import ALLOWED_CHAT_IDS, ALLOWED_METHODS, GLOBAL_ALLOWED_METHODS


def is_chat_id_allowed(chat_id: str) -> bool:
    """
    檢查 chat_id 是否在允許清單中。
    ALLOWED_CHAT_IDS 含 "*" 時直接放行。
    """
    if "*" in ALLOWED_CHAT_IDS:
        return True
    return str(chat_id) in [str(c) for c in ALLOWED_CHAT_IDS]


def is_method_allowed(chat_id: str, method: str) -> bool:
    """
    檢查 chat_id 是否可呼叫指定方法。
    優先使用明確規則，否則回退至 "*" 萬用字元規則。
    """
    chat_id_str = str(chat_id)

    # 優先：chat_id 明確規則
    if chat_id_str in ALLOWED_METHODS:
        allowed: List = ALLOWED_METHODS[chat_id_str]
        return "*" in allowed or method in allowed

    # 回退：萬用字元規則
    if "*" in ALLOWED_METHODS:
        allowed: List = ALLOWED_METHODS["*"]
        return "*" in allowed or method in allowed

    return False


def is_global_method_allowed(method: str) -> bool:
    """
    檢查不需要 chat_id 的全域方法是否被允許（如 getMe）。
    """
    if "*" in GLOBAL_ALLOWED_METHODS:
        return True
    return method in GLOBAL_ALLOWED_METHODS