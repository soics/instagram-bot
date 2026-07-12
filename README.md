# Instagram AI DM Bot

Automated DM assistant that replies to whitelisted Instagram contacts using local AI (Ollama).

Pipeline: **Instagram DM → instagrapi → Ollama (phi3:mini / llava) → DM reply → phone notification**

## How It Works

When someone on your whitelist sends a DM:

- **Text** → ollama `phi3:mini` replies in 1 short sentence
- **Image** → ollama `llava` analyzes the image and replies
- **Video / clip** → short ack: "I can only look at photos right now"
- **Anyone not on the whitelist** → silently ignored
- **Your own messages** → silently ignored

First reply is capped at 140 chars so Meta TTS reads it from the notification preview. Longer answers get a follow-up message.

## Requirements

- **Python 3.10+**
- **Ollama** running locally with `phi3:mini` and `llava` models
  ```bash
  ollama pull phi3:mini
  ollama pull llava
  ```
- **Instagram account** for the bot to log into
- **A phone** with Instagram installed (for login challenges)

## Setup

### 1. Clone & Install

```bash
git clone <repo-url>
cd instagrambot
pip install instagrapi
```

### 2. Configure Credentials

```bash
cp .env.example .env
# Edit .env with your bot account's Instagram username and password
```

### 3. Build the Whitelist

Decide who the bot will reply to. You have two options:

**Option A: Start empty (no one can trigger it)**
Leave `ALLOWED_SENDERS = {}` in `bot.py`. Safe default.

**Option B: Add specific users**
Run the ID resolver to get numeric user IDs:

```bash
python get_id.py username1 username2 username3
```

Then copy the printed IDs into `bot.py`'s `ALLOWED_SENDERS` set.

### 4. Login

```bash
python login.py
```

Do this from your phone with Instagram open. If a challenge code is sent, enter it in the terminal.

### 5. Run

```bash
python bot.py
```

## Running 24/7 (systemd)

```bash
sudo cp instagrambot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable instagrambot
sudo systemctl start instagrambot
```

View logs:

```bash
journalctl -u instagrambot -f
```

## Instagram Challenges

The bot **stops immediately** on a challenge, never retries in a loop (retries = flagged faster).

1. Stop the bot
2. Open Instagram on your phone, complete the challenge
3. Wait 15-30 minutes
4. Re-run `python login.py`
5. Restart

## Files

| File | Purpose |
|------|---------|
| `bot.py` | Main polling loop. Checks DMs every 30s, generates AI replies. |
| `login.py` | One-shot login. Creates `session.json`. |
| `get_id.py` | Resolves Instagram @handles → numeric user IDs for the whitelist. |
| `env_loader.py` | Reads `.env` into environment. Zero dependencies. |
| `instagrambot.service` | systemd unit (Restart=no by design). |

## Security

- `.env` and `session.json` are gitignored. **Never commit them.**
- Permissions are set to 600 (owner read/write only).
- The bot never uses your real Instagram — only the bot account you configure.
- Whitelist prevents random people from triggering the bot.
- All AI runs locally on your machine — no data sent to cloud APIs.
- If a session is challenged, the bot stops immediately.

## Limitations

- Meta's terms prohibit automation. This is for **educational / personal experimentation**.
- Session rotation is required every 1-2 weeks (Instagram expires them).
- Works best when the bot account is "phone-warmed" before use (send a few DMs, like a post, post a story the day before).
- Only handles text and single-image DMs. Video, reels, and stories get a generic response.
