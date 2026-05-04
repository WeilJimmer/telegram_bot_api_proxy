# Telegram Bot API Proxy

隱藏 Bot Token 的 Telegram Bot API 代理伺服器，支援 Chat ID 白名單與方法層級存取控制。

---

## 快速開始

### 1. 建立虛擬環境（建議）

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數（`.env` / `.env.sample`）

- 服務啟動時會**優先讀取 `.env`**。
- 若 `.env` 不存在，則會改讀 `.env.sample`。

建議先複製範本：

```bash
cp .env.sample .env
# Windows PowerShell
# Copy-Item .env.sample .env
```

| 欄位 | 說明 |
|------|------|
| `BOT_TOKEN` | Telegram Bot Token |
| `API_KEY` | 保護此代理的存取金鑰，空字串可關閉 |
| `SERVER_HOST` | 伺服器綁定位址，預設 `0.0.0.0` |
| `SERVER_PORT` | 伺服器埠號，預設 `15820` |
| `ALLOWED_CHAT_IDS` | Chat ID 白名單，`["*"]` 允許所有 |
| `ALLOWED_METHODS` | 各 Chat ID 的方法白名單 |
| `GLOBAL_ALLOWED_METHODS` | 不需 chat_id 的方法白名單 |

> `ALLOWED_CHAT_IDS`、`ALLOWED_METHODS`、`GLOBAL_ALLOWED_METHODS` 需使用 JSON 字串格式。

### 4. 啟動

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 15820
```

---

## 呼叫範例

> 所有請求需帶上 `X-API-Key` Header（若 `API_KEY` 有設定）

### 後端如何判斷 JSON

- 當 `Content-Type` 是 `application/json` 或 `application/*+json` 時，後端會嘗試做 JSON 解碼。
- 若解碼失敗或 JSON 不是物件（例如不是 `{}`），會回傳 `400`。
- 檔案上傳請維持 `multipart/form-data`，不要用 JSON 送檔案內容。

### 發送訊息（JSON）

```bash
curl -X POST http://localhost:15820/sendMessage \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"chat_id": "123456789", "text": "Hello!"}'
```

### 發送訊息（Form-data）

```bash
curl -X POST http://localhost:15820/sendMessage \
  -H "X-API-Key: your_proxy_api_key" \
  -F "chat_id=123456789" \
  -F "text=Hello!"
```

### 上傳圖片

```bash
curl -X POST http://localhost:15820/sendPhoto \
  -H "X-API-Key: your_proxy_api_key" \
  -F "chat_id=123456789" \
  -F "photo=@/path/to/image.jpg"
```

### 全域方法（無 chat_id）

```bash
curl -X POST http://localhost:15820/getMe \
  -H "X-API-Key: your_proxy_api_key"
```

---

## 存取控制設定說明

### ALLOWED_CHAT_IDS

```dotenv
ALLOWED_CHAT_IDS=["*"]             # 允許所有 chat_id
ALLOWED_CHAT_IDS=[123456,789012]    # 僅允許清單內的 chat_id
```

### ALLOWED_METHODS

優先順序：**明確指定的 chat_id 規則 > 萬用字元 `"*"` 規則**

```dotenv
# 所有人可用所有方法
ALLOWED_METHODS={"*":["*"]}

# 預設只能 sendMessage，但 123456789 不受限
ALLOWED_METHODS={"*":["sendMessage"],"123456789":["*"]}

# 各 chat_id 限制不同方法
ALLOWED_METHODS={"123456789":["sendMessage","sendPhoto"],"987654321":["sendMessage"]}
```

### GLOBAL_ALLOWED_METHODS

```dotenv
GLOBAL_ALLOWED_METHODS=["*"]                        # 允許所有全域方法
GLOBAL_ALLOWED_METHODS=["getMe","getWebhookInfo"] # 僅允許指定方法
GLOBAL_ALLOWED_METHODS=[]                            # 全部禁止
```

---

## API 文件

伺服器啟動後可訪問 Swagger UI：

```
http://localhost:15820/docs
```