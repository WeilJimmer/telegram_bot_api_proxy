# Telegram Bot API Proxy Server Guide

Minimal guide for calling Telegram Bot API through this proxy.

API Base URL:

```text
http://192.168.100.100:15820
```

If your proxy is configured with an API key, include this header in every request:

```http
X-API-Key: proxy_api_key
```

---

## Rules

- Use JSON for requests without files.
- Use multipart/form-data for requests with files.
- Add caption when the method supports it.
- Add parse_mode only when you need text formatting.

JSON content type:

- application/json
- application/*+json

Common file fields:

- sendPhoto -> photo
- sendVideo -> video
- sendDocument -> document
- sendAudio -> audio
- sendVoice -> voice

Note:

- The standard Telegram method for generic files is sendDocument.
- This proxy maps sendFile to sendDocument automatically.
- This proxy also maps file to document automatically.

---

## Basic Fields

- chat_id: target chat ID
- caption: text attached to a file
- parse_mode: Markdown or HTML
- X-MY-NAME: which bot identity to send as (see below)

---

## Sending as a Specific Bot (X-MY-NAME)

The proxy may hold several bot tokens. Add X-MY-NAME to pick which bot sends the message. It works on every method, in JSON and in form-data, and is removed before the request reaches Telegram.

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"chat_id":"123456789","text":"Hello"}'

curl -X POST http://192.168.100.100:15820/sendPhoto \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "photo=@/path/to/photo.jpg"
```

Rules:

- If you omit X-MY-NAME, the default bot is used. Some servers are configured to require it; then omitting it returns 400.
- A name that is not configured returns 403. Do not guess names — ask the master which names exist.
- getResultFromMaster always uses the bot that created the poll, so you do not need X-MY-NAME there. If you send one, it must match the bot that asked.

---

## Examples

Replace chat_id with your real value.

### getMe

```bash
curl -X POST http://192.168.100.100:15820/getMe \
	-H "X-API-Key: proxy_api_key"
  -H "X-MY-NAME: ariel"
```

### sendMessage

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"chat_id":"123456789","text":"This is a test message"}'
```

### sendMessage with Markdown

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"chat_id":"123456789","text":"*Bold*\n_Italic_\n`code`","parse_mode":"Markdown"}'
```

### sendMessage with HTML

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"chat_id":"123456789","text":"<b>Bold</b>\n<i>Italic</i>\n<code>code</code>","parse_mode":"HTML"}'
```

### sendPhoto

```bash
curl -X POST http://192.168.100.100:15820/sendPhoto \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "photo=@/path/to/photo.jpg" \
	-F "caption=This is a photo"
```

### sendPhoto with parse_mode

```bash
curl -X POST http://192.168.100.100:15820/sendPhoto \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "photo=@/path/to/photo.jpg" \
	-F "caption=<b>Important</b> photo" \
	-F "parse_mode=HTML"
```

### sendVideo

```bash
curl -X POST http://192.168.100.100:15820/sendVideo \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "video=@/path/to/clip.mp4" \
	-F "caption=This is a video"
```

### sendDocument

```bash
curl -X POST http://192.168.100.100:15820/sendDocument \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "document=@/path/to/archive.zip" \
	-F "caption=Archive file"
```

### sendAudio

```bash
curl -X POST http://192.168.100.100:15820/sendAudio \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "audio=@/path/to/music.mp3" \
	-F "caption=Audio message"
```

### sendVoice

```bash
curl -X POST http://192.168.100.100:15820/sendVoice \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "voice=@/path/to/voice.ogg" \
	-F "caption=Voice message"
```

### sendLocation

```bash
curl -X POST http://192.168.100.100:15820/sendLocation \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"chat_id":"123456789","latitude":25.0330,"longitude":121.5654}'
```

### sendFile

Compatibility alias. The proxy rewrites:

- sendFile -> sendDocument
- file -> document

```bash
curl -X POST http://192.168.100.100:15820/sendFile \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "chat_id=123456789" \
	-F "file=@/path/to/archive.zip" \
	-F "caption=Archive file"
```

---

## Master Methods

These methods always send to the master. Do NOT add chat_id; the server fills it in.

### reportToMaster

Send an alert to the master. No reply is expected. Works with text or any file (use the same fields as sendPhoto, sendVideo, sendDocument, etc.).

```bash
# Text
curl -X POST http://192.168.100.100:15820/reportToMaster \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"text":"Task finished"}'

# Photo
curl -X POST http://192.168.100.100:15820/reportToMaster \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-F "photo=@/path/to/photo.jpg" \
	-F "caption=Result"
```

### askMasterForPermission

Ask the master a question as a poll. You get back a poll_token. options is a JSON array of 2 to 9 short strings. The master can also add their own options, so your question can be open-ended (not only yes/no).

```bash
curl -X POST http://192.168.100.100:15820/askMasterForPermission \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"question":"Allow this action?","options":["Yes","No"]}'
```

Response:

```json
{"ok": true, "poll_token": "abc-123", "telegram_poll_message_id": 456}
```

Save the poll_token. You need it to read the answer.

### getResultFromMaster

Read the poll answer. Use the poll_token from askMasterForPermission.

IMPORTANT: this CLOSES the poll. The master can no longer vote after you call it. You can only call it ONCE per token. So call it only when you actually need the final answer.

```bash
curl -X POST http://192.168.100.100:15820/getResultFromMaster \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
  -H "X-MY-NAME: ariel" \
	-d '{"poll_token":"abc-123"}'
```

Read these fields in the response (the raw poll is also kept in telegram_result):

- message: a plain sentence you can use directly. Examples: "Master chose [Yes] option." or "Master hasn't answered yet! Ask again?"
- answered: true if the master voted, false if not.
- chosen_options: the options the master picked (a list, may have more than one).

Pitfalls:

- The master is a human. They need time to see the poll and tap an option. Do NOT call getResultFromMaster right after asking. Wait first (for example tens of seconds to minutes).
- If answered is false (all votes are 0), the master has NOT answered yet. Because getResultFromMaster already closed that poll, the old poll is dead.
- When answered is false, usually you should ask AGAIN: call askMasterForPermission to make a fresh poll, wait longer, then read it once more.

---

## Errors

Common failures:

- Invalid or missing API Key
- chat_id is not in the allowlist
- method is not in the global allowlist, or this method requires chat_id
- Failed to decode JSON payload
- file upload failed because field name, path, or method is wrong
