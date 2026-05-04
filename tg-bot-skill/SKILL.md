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
- sendDocument -> document
- sendAudio -> audio
- sendVoice -> voice

Note:

- The standard Telegram method for generic files is sendDocument.
- Use sendFile only if your upstream explicitly supports it.

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

```bash
curl -X POST http://192.168.100.100:15820/sendFile \
	-H "X-API-Key: proxy_api_key" \
	-F "chat_id=123456789" \
	-F "file=@/path/to/archive.zip" \
	-F "caption=Archive file"
```

---

## Errors

Common failures:

- Invalid or missing API Key
- chat_id is not in the allowlist
- method is not in the global allowlist, or this method requires chat_id
- Failed to decode JSON payload
- file upload failed because field name, path, or method is wrong
