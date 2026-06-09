# Telegram Bot API Proxy

A Telegram Bot API proxy server that hides bot tokens and supports chat ID allowlists with method-level access control.

---

## English

### Overview

Telegram Bot API proxy server with:

- Bot token masking
- Chat ID allowlist
- Method-level access control
- JSON and form-data request support

### Quick Start

#### 1. Create virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure environment variables (.env / .env.sample)

- The service loads .env first.
- If .env does not exist, it falls back to .env.sample.

Copy template first:

```bash
cp .env.sample .env
# Windows PowerShell
# Copy-Item .env.sample .env
```

| KEY | Description |
|------|------|
| BOT_TOKEN | Telegram Bot token |
| API_KEY | Proxy API key; set empty string to disable |
| SERVER_HOST | Bind address, default 0.0.0.0 |
| SERVER_PORT | Port, default 15820 |
| ALLOWED_CHAT_IDS | Chat ID allowlist; ["*"] allows all |
| ALLOWED_METHODS | Method allowlist by Chat ID |
| GLOBAL_ALLOWED_METHODS | Allowlist for methods without chat_id |
| MASTER_CHAT_ID | Master chat ID for reportToMaster / askMasterForPermission |
| REDIS_URL | Poll storage backend; empty uses local files |
| POLL_STORE_DIR | Poll file directory when REDIS_URL is empty, default /tmp/tg_proxy_polls |

ALLOWED_CHAT_IDS, ALLOWED_METHODS, and GLOBAL_ALLOWED_METHODS must be JSON strings.

#### 4. Start service

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 15820
```

#### 5. Install as a Linux systemd service

This installs the service, enables auto-start at boot, and starts it immediately.

```bash
chmod +x scripts/install_systemd_service.sh
sudo ./scripts/install_systemd_service.sh
```

Useful commands:

```bash
sudo systemctl status telegram-api-proxy
sudo systemctl restart telegram-api-proxy
sudo journalctl -u telegram-api-proxy -f
```

Optional variables:

```bash
sudo SERVICE_NAME=telegram-api-proxy \
SERVICE_USER=$USER \
VENV_DIR=$(pwd)/venv \
./scripts/install_systemd_service.sh
```

Uninstall service:

```bash
chmod +x scripts/uninstall_systemd_service.sh
sudo ./scripts/uninstall_systemd_service.sh
```

Optional variable:

```bash
sudo SERVICE_NAME=telegram-api-proxy ./scripts/uninstall_systemd_service.sh
```

---

### Request Examples

All requests must include X-API-Key header when API_KEY is set.

#### How JSON is detected

- If Content-Type is application/json or application/*+json, server tries to decode JSON.
- If decoding fails, or payload is not an object, server returns 400.
- Keep file upload as multipart/form-data; do not upload files via JSON.

#### Send message (JSON)

```bash
curl -X POST http://localhost:15820/sendMessage \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"chat_id": "123456789", "text": "Hello!"}'
```

#### Send message (form-data)

```bash
curl -X POST http://localhost:15820/sendMessage \
  -H "X-API-Key: your_proxy_api_key" \
  -F "chat_id=123456789" \
  -F "text=Hello!"
```

#### Upload photo

```bash
curl -X POST http://localhost:15820/sendPhoto \
  -H "X-API-Key: your_proxy_api_key" \
  -F "chat_id=123456789" \
  -F "photo=@/path/to/image.jpg"
```

#### Global method (without chat_id)

```bash
curl -X POST http://localhost:15820/getMe \
  -H "X-API-Key: your_proxy_api_key"
```

---

### Non-Official Methods

These extra methods require `MASTER_CHAT_ID` to be set. They always target the master chat; any `chat_id` in the body is ignored.

#### reportToMaster

Send a one-way alert to the master. Accepts any content (text, photo, video, document, ...). The proxy auto-detects the Telegram method from the fields you send (`photo` -> sendPhoto, `video` -> sendVideo, `document` -> sendDocument, `latitude`+`longitude` -> sendLocation, otherwise sendMessage).

```bash
# Text alert
curl -X POST http://localhost:15820/reportToMaster \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"text": "Disk space is low"}'

# Photo alert
curl -X POST http://localhost:15820/reportToMaster \
  -H "X-API-Key: your_proxy_api_key" \
  -F "photo=@/path/to/snapshot.jpg" \
  -F "caption=Camera snapshot"
```

#### askMasterForPermission

Send a poll to the master and get back a `poll_token`. The poll is non-anonymous, allows multiple answers, allows re-voting, and has no time limit. `options` must be a JSON array of 2-10 strings. If you also send media, it is delivered as a separate message before the poll.

```bash
curl -X POST http://localhost:15820/askMasterForPermission \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"question": "A stranger wants the WiFi password. Allow?", "options": ["Allow", "Deny"]}'

# Response: {"ok": true, "poll_token": "uuid...", "telegram_poll_message_id": 123}
```

#### getResultFromMaster

Stop the poll and return the vote counts. Use the `poll_token` from askMasterForPermission. Calling this **closes the poll** (the master can no longer vote), and each token works only once.

```bash
curl -X POST http://localhost:15820/getResultFromMaster \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"poll_token": "uuid..."}'
```

> **Pitfall:** The master is a human and needs time to answer. Do not call this immediately after asking. If all `voter_count` values are 0, the master had not answered yet, and the poll is now closed — usually you should call askMasterForPermission again to send a fresh poll and wait longer before reading the result.

---

### Access Control Settings

#### ALLOWED_CHAT_IDS

```dotenv
ALLOWED_CHAT_IDS=["*"]             # allow all chat_id
ALLOWED_CHAT_IDS=[123456,789012]    # allow only listed chat_id
```

#### ALLOWED_METHODS

Priority: explicit chat_id rule > wildcard "*" rule

```dotenv
# everyone can use all methods
ALLOWED_METHODS={"*":["*"]}

# default only sendMessage, but 123456789 is unrestricted
ALLOWED_METHODS={"*":["sendMessage"],"123456789":["*"]}

# each chat_id has different allowed methods
ALLOWED_METHODS={"123456789":["sendMessage","sendPhoto"],"987654321":["sendMessage"]}
```

#### GLOBAL_ALLOWED_METHODS

```dotenv
GLOBAL_ALLOWED_METHODS=["*"]                        # allow all global methods
GLOBAL_ALLOWED_METHODS=["getMe","getWebhookInfo"] # allow specific methods only
GLOBAL_ALLOWED_METHODS=[]                            # deny all
```

---

### API Docs

Swagger UI:

```
http://localhost:15820/docs
```

---

## 中文

### 簡介

隱藏 Bot Token 的 Telegram Bot API 代理伺服器，支援 Chat ID 白名單與方法層級存取控制。

### 快速開始

#### 1. 建立虛擬環境（建議）

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

#### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

#### 3. 設定環境變數（.env / .env.sample）

- 服務啟動時會優先讀取 .env。
- 若 .env 不存在，則會改讀 .env.sample。

建議先複製範本：

```bash
cp .env.sample .env
# Windows PowerShell
# Copy-Item .env.sample .env
```

| 欄位 | 說明 |
|------|------|
| BOT_TOKEN | Telegram Bot Token |
| API_KEY | 保護此代理的存取金鑰，空字串可關閉 |
| SERVER_HOST | 伺服器綁定位址，預設 0.0.0.0 |
| SERVER_PORT | 伺服器埠號，預設 15820 |
| ALLOWED_CHAT_IDS | Chat ID 白名單，["*"] 允許所有 |
| ALLOWED_METHODS | 各 Chat ID 的方法白名單 |
| GLOBAL_ALLOWED_METHODS | 不需 chat_id 的方法白名單 |
| MASTER_CHAT_ID | reportToMaster / askMasterForPermission 使用的主人 chat ID |
| REDIS_URL | 投票暫存後端，留空則使用本機檔案 |
| POLL_STORE_DIR | REDIS_URL 留空時的投票檔案目錄，預設 /tmp/tg_proxy_polls |

ALLOWED_CHAT_IDS、ALLOWED_METHODS、GLOBAL_ALLOWED_METHODS 需使用 JSON 字串格式。

#### 4. 啟動

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 15820
```

#### 5. 安裝成 Linux systemd 服務

此腳本會安裝服務、設定開機自動啟動，並立即啟動服務。

```bash
chmod +x scripts/install_systemd_service.sh
sudo ./scripts/install_systemd_service.sh
```

常用指令：

```bash
sudo systemctl status telegram-api-proxy
sudo systemctl restart telegram-api-proxy
sudo journalctl -u telegram-api-proxy -f
```

可選參數：

```bash
sudo SERVICE_NAME=telegram-api-proxy \
SERVICE_USER=$USER \
VENV_DIR=$(pwd)/venv \
./scripts/install_systemd_service.sh
```

移除服務：

```bash
chmod +x scripts/uninstall_systemd_service.sh
sudo ./scripts/uninstall_systemd_service.sh
```

可選參數：

```bash
sudo SERVICE_NAME=telegram-api-proxy ./scripts/uninstall_systemd_service.sh
```

---

### 呼叫範例

若 API_KEY 有設定，所有請求需帶上 X-API-Key Header。

#### 後端如何判斷 JSON

- 當 Content-Type 是 application/json 或 application/*+json 時，後端會嘗試做 JSON 解碼。
- 若解碼失敗或 JSON 不是物件（例如 {}），會回傳 400。
- 檔案上傳請維持 multipart/form-data，不要用 JSON 送檔案內容。

#### 發送訊息（JSON）

```bash
curl -X POST http://localhost:15820/sendMessage \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"chat_id": "123456789", "text": "Hello!"}'
```

#### 發送訊息（Form-data）

```bash
curl -X POST http://localhost:15820/sendMessage \
  -H "X-API-Key: your_proxy_api_key" \
  -F "chat_id=123456789" \
  -F "text=Hello!"
```

#### 上傳圖片

```bash
curl -X POST http://localhost:15820/sendPhoto \
  -H "X-API-Key: your_proxy_api_key" \
  -F "chat_id=123456789" \
  -F "photo=@/path/to/image.jpg"
```

#### 全域方法（無 chat_id）

```bash
curl -X POST http://localhost:15820/getMe \
  -H "X-API-Key: your_proxy_api_key"
```

---

### 非官方方法

以下額外方法需先設定 `MASTER_CHAT_ID`。它們一律送往主人，會忽略 body 內的 `chat_id`。

#### reportToMaster

向主人發送單向告警，支援任意內容（文字、圖片、影片、檔案……）。後端依你帶的欄位自動判斷 Telegram 方法（`photo` -> sendPhoto、`video` -> sendVideo、`document` -> sendDocument、`latitude`+`longitude` -> sendLocation，其餘 -> sendMessage）。

```bash
# 文字告警
curl -X POST http://localhost:15820/reportToMaster \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"text": "磁碟空間不足"}'

# 圖片告警
curl -X POST http://localhost:15820/reportToMaster \
  -H "X-API-Key: your_proxy_api_key" \
  -F "photo=@/path/to/snapshot.jpg" \
  -F "caption=監視器截圖"
```

#### askMasterForPermission

向主人發送投票並取回 `poll_token`。投票為非匿名、可複選、可重新投票、無時間限制。`options` 須為 2~10 個字串的 JSON 陣列。若同時帶媒體，會在投票前先以獨立訊息送出。

```bash
curl -X POST http://localhost:15820/askMasterForPermission \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"question": "陌生人想要 WiFi 密碼，要給嗎？", "options": ["給", "不給"]}'

# 回應：{"ok": true, "poll_token": "uuid...", "telegram_poll_message_id": 123}
```

#### getResultFromMaster

停止投票並回傳各選項票數。使用 askMasterForPermission 拿到的 `poll_token`。呼叫此方法會**關閉投票**（主人之後就無法再投），且每個 token 只能用一次。

```bash
curl -X POST http://localhost:15820/getResultFromMaster \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_proxy_api_key" \
  -d '{"poll_token": "uuid..."}'
```

> **常見陷阱：** 主人是真人，需要時間回覆。不要一問完就馬上呼叫此方法。若所有 `voter_count` 都是 0，代表主人還沒回答，而投票此時已被關閉 — 通常你應該再次呼叫 askMasterForPermission 發出新投票，並等久一點再讀取結果。

---

### 存取控制設定說明

#### ALLOWED_CHAT_IDS

```dotenv
ALLOWED_CHAT_IDS=["*"]             # 允許所有 chat_id
ALLOWED_CHAT_IDS=[123456,789012]    # 僅允許清單內的 chat_id
```

#### ALLOWED_METHODS

優先順序：明確指定的 chat_id 規則 > 萬用字元 "*" 規則

```dotenv
# 所有人可用所有方法
ALLOWED_METHODS={"*":["*"]}

# 預設只能 sendMessage，但 123456789 不受限
ALLOWED_METHODS={"*":["sendMessage"],"123456789":["*"]}

# 各 chat_id 限制不同方法
ALLOWED_METHODS={"123456789":["sendMessage","sendPhoto"],"987654321":["sendMessage"]}
```

#### GLOBAL_ALLOWED_METHODS

```dotenv
GLOBAL_ALLOWED_METHODS=["*"]                        # 允許所有全域方法
GLOBAL_ALLOWED_METHODS=["getMe","getWebhookInfo"] # 僅允許指定方法
GLOBAL_ALLOWED_METHODS=[]                            # 全部禁止
```

---

### API 文件

伺服器啟動後可訪問 Swagger UI：

```
http://localhost:15820/docs
```