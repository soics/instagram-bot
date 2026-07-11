# @mv.lls Instagram AI DM Bot

Bot account: `@mv.lls` (your main Instagram)
Pipeline: Meta glasses → Instagram DM → laptop (ollama) → DM reply → phone notification → Meta TTS

## What this is NOT

This is **not** a hosted 24/7 customer-service chatbot. It is a controlled local automation tool that runs on a single laptop, responds only to a whitelist of 5 approved contacts, and uses a local Ollama instance (not a cloud API). When the terminal or systemd service is stopped, no automation runs. It is not a production service — it is a personal tool.

Instagram's terms of service prohibit automated activity. This project is for educational and personal experimentation purposes. Use at your own risk.

## What it does

When someone on the whitelist DMs `@mv.lls`:

- **Text message** → ollama `phi3:mini` replies in one short sentence
- **Image** → image is downloaded, ollama `llava` analyses it, reply is sent
- **Video / clip** → short ack ("I can only look at photos right now")
- **Anyone NOT on the whitelist** → silently ignored
- **Our own messages** → silently ignored

The reply is capped at 140 characters for the first line so Meta TTS reads it aloud from the Instagram notification preview. Longer answers get a follow-up message.

## Files

| File | Purpose |
|---|---|
| `bot.py` | Main polling loop. Checks DMs every 60s, generates replies via ollama. |
| `login.py` | One-shot login. Creates `session.json` for `@mv.lls`. |
| `get_id.py` | Resolves Instagram handles to numeric user IDs for the whitelist. |
| `env_loader.py` | Zero-dependency `.env` reader. Respects existing env vars for systemd override. |
| `instagrambot.service` | systemd unit file. `Restart=no` by design. |
| `.env` | Credentials. Mode 600. **Never commit.** |
| `session.json` | Saved Instagram login session. Mode 600. **Never commit.** |
| `seen.json` | Set of message IDs already processed. Runtime state. Cleared on reset. |
| `img_cache/` | Per-message downloaded images. Cleared on reset. |

## Whitelist

Currently allowed to trigger the bot:

- `57759830475`  # @mv.lls
- `10878327026`  # @quid.x
- `39917953709`  # @thatgirl._mairin
- `78185684634`  # @nadz_hbk
- `1455678182`   # @scriptless_

To change the whitelist, edit the `ALLOWED_SENDERS` set in `bot.py` and restart.

## Requirements

- Python 3.10+
- [ollama](https://ollama.com) running locally with `phi3:mini` and `llava` models
- `instagrapi` library (`pip install instagrapi`)
- An Instagram account (the bot logs in as `@mv.lls`)

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd instagrambot
pip install instagrapi

# 2. Set up credentials
cp .env.example .env   # then fill in IG_USERNAME and IG_PASSWORD

# 3. Login once (do this from your phone with Instagram open)
python login.py

# 4. Run
python bot.py
```

## Running manually

```bash
cd ~/instagrambot
source ~/botenv/bin/activate
python bot.py
```

Stop with `Ctrl+C`. Useful for testing or when you only need the bot for a short window.

## Running with systemd (24/7)

```bash
sudo cp ~/instagrambot/instagrambot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable instagrambot
sudo systemctl start instagrambot
```

Watch logs:

```bash
journalctl -u instagrambot -f
```

Stop:

```bash
sudo systemctl stop instagrambot
```

## The Thursday sequence

1. **Tuesday night** — Phone-warm `@mv.lls`: send 3-4 DMs, like a post, post a story. Run `python login.py` to create `session.json`.
2. **Wednesday** — Phone-warm 2-3 more times (~15 min total). Do not touch the laptop. Let the session age.
3. **Thursday morning** — Start the bot. Test from a whitelisted account. Expect reply in under 90s.

## If Instagram challenges the session

The bot is built to **STOP** on a challenge, not loop. You'll see:

```
[AUTH] Instagram wants verification: <details>
Stopping. Solve the challenge on your phone, then restart me manually.
```

Steps:
1. Stop the bot.
2. Open Instagram on your phone, complete the challenge.
3. Wait 15-30 minutes.
4. Re-run `python login.py` to refresh the session.
5. Restart the bot.

Do NOT immediately retry. Every failed attempt deepens the flag.

## Security

- `.env` is mode 600. Never commit, paste, or share.
- `session.json` is a permanent login cookie. Treat it like a password.
- Rotate the `@mv.lls` password periodically and re-run `login.py`.
- Do not edit `seen.json` by hand — a typo can cause the bot to re-reply (and look bot-shaped to Instagram).

## Architecture

```
Instagram DM ──→ instagrapi ──→ bot.py
                                    │
                            ┌───────┴───────┐
                            │               │
                       text message      image message
                            │               │
                            ▼               ▼
                      phi3:mini (ollama)  llava (ollama)
                            │               │
                            └───────┬───────┘
                                    ▼
                              DM reply
```
