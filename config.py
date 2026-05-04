# ============================================================
#  Telegram Bot API Proxy — 設定檔
# ============================================================

# ---------- Telegram ----------
BOT_TOKEN        = "your_bot_token_here"
TELEGRAM_API_BASE = "https://api.telegram.org"

# ---------- Server ----------
# 伺服器監聽位址與埠號
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 15820

# ---------- Proxy Auth ----------
# 調用此代理時需在 Header 帶上：X-API-Key: <API_KEY>
# 設為 "" 或 None 可關閉驗證
API_KEY = "your_proxy_api_key_here"

# ---------- Access Control ----------

# 允許的 Chat ID 清單
# ["*"]          → 允許所有 chat_id（不過濾）
# [123456, 789]  → 僅允許清單內的 chat_id
ALLOWED_CHAT_IDS = ["*"]

# 各 Chat ID 允許呼叫的 Telegram Bot API 方法
#
# Key   : chat_id 字串 或 "*"（萬用，套用至未明確指定的 chat_id）
# Value : 允許的方法清單，或 ["*"] 代表允許所有方法
#
# 優先順序：明確指定的 chat_id 規則  >  萬用字元 "*" 規則
#
# 範例：
# ALLOWED_METHODS = {
#     "*":          ["sendMessage"],                        # 預設只能 sendMessage
#     "123456789":  ["*"],                                  # 此 ID 可用所有方法
#     "987654321":  ["sendMessage", "sendPhoto", "sendDocument"],
# }
ALLOWED_METHODS = {
    "*": ["*"],
}

# 不帶 chat_id 的全域方法白名單（例如 getMe、setWebhook）
# ["*"] → 全部允許
# []    → 全部禁止
GLOBAL_ALLOWED_METHODS = ["getMe"]