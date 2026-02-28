---
name: serverchan-notify
description: Send WeChat notifications to the user via ServerChan (Server酱). Use when the user asks to be notified on WeChat, or for urgent alerts that need mobile attention.
---

# ServerChan Notification Skill

Sends push notifications to WeChat using the ServerChan Turbo API.

## Configuration

The SendKey is stored securely in `config.json`.

## Usage

```bash
# Send using default key from config
python3 scripts/send.py --title "Hello"

# Override key if needed
python3 scripts/send.py --key <OTHER_KEY> --title "Alert"
```
