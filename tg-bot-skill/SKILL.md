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

---

## Examples

Replace chat_id with your real value.

### getMe

```bash
curl -X POST http://192.168.100.100:15820/getMe \
	-H "X-API-Key: proxy_api_key"
```

### sendMessage

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"chat_id":"123456789","text":"This is a test message"}'
```

### sendMessage with Markdown

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"chat_id":"123456789","text":"*Bold*\n_Italic_\n`code`","parse_mode":"Markdown"}'
```

### sendMessage with HTML

```bash
curl -X POST http://192.168.100.100:15820/sendMessage \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"chat_id":"123456789","text":"<b>Bold</b>\n<i>Italic</i>\n<code>code</code>","parse_mode":"HTML"}'
```

### sendPhoto

```bash
curl -X POST http://192.168.100.100:15820/sendPhoto \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "photo=@/path/to/photo.jpg" \
	-F "caption=This is a photo"
```

### sendPhoto with parse_mode

```bash
curl -X POST http://192.168.100.100:15820/sendPhoto \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "photo=@/path/to/photo.jpg" \
	-F "caption=<b>Important</b> photo" \
	-F "parse_mode=HTML"
```

### sendVideo

```bash
curl -X POST http://192.168.100.100:15820/sendVideo \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "video=@/path/to/clip.mp4" \
	-F "caption=This is a video"
```

### sendDocument

```bash
curl -X POST http://192.168.100.100:15820/sendDocument \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "document=@/path/to/archive.zip" \
	-F "caption=Archive file"
```

### sendAudio

```bash
curl -X POST http://192.168.100.100:15820/sendAudio \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "audio=@/path/to/music.mp3" \
	-F "caption=Audio message"
```

### sendVoice

```bash
curl -X POST http://192.168.100.100:15820/sendVoice \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "voice=@/path/to/voice.ogg" \
	-F "caption=Voice message"
```

### sendLocation

```bash
curl -X POST http://192.168.100.100:15820/sendLocation \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"chat_id":"123456789","latitude":25.0330,"longitude":121.5654}'
```

### sendFile

Compatibility alias. The proxy rewrites:

- sendFile -> sendDocument
- file -> document

```bash
curl -X POST http://192.168.100.100:15820/sendFile \
	-H "X-API-Key: proxy_api_key" \
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
	-d '{"text":"Task finished"}'

# Photo
curl -X POST http://192.168.100.100:15820/reportToMaster \
	-H "X-API-Key: proxy_api_key" \
	-F "photo=@/path/to/photo.jpg" \
	-F "caption=Result"
```

### askMasterForPermission

Ask the master a yes/no style question as a poll. You get back a poll_token. options is a JSON array of 2 to 10 short strings.

```bash
curl -X POST http://192.168.100.100:15820/askMasterForPermission \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"question":"Allow this action?","options":["Yes","No"]}'
```

Response:

```json
{"ok": true, "poll_token": "abc-123", "telegram_poll_message_id": 456}
```

Save the poll_token. You need it to read the answer.

### getResultFromMaster

Read the poll answer. Use the poll_token from askMasterForPermission. Call this only once per token.

```bash
curl -X POST http://192.168.100.100:15820/getResultFromMaster \
	-H "Content-Type: application/json" \
	-H "X-API-Key: proxy_api_key" \
	-d '{"poll_token":"abc-123"}'
```

The answer is inside telegram_result.result.options, where each option has a voter_count.

---

## Errors

Common failures:

- Invalid or missing API Key
- chat_id is not in the allowlist
- method is not in the global allowlist, or this method requires chat_id
- Failed to decode JSON payload
- file upload failed because field name, path, or method is wrong
