from instagrapi import Client
import ollama
import time
import requests
import os
import json
import random
import re
import signal
import traceback

import env_loader  # noqa: F401  - loads ~/instagrambot/.env into os.environ

# CONFIG
# Username/password come from ~/instagrambot/.env (loaded by env_loader).
# IG_USERNAME and IG_PASSWORD are required — no defaults.
USERNAME       = os.getenv("IG_USERNAME")
PASSWORD       = os.getenv("IG_PASSWORD")

if not USERNAME or not PASSWORD:
    print("FATAL: IG_USERNAME and IG_PASSWORD must be set in ~/instagrambot/.env")
    raise SystemExit(1)
CHECK_INTERVAL = 30                      # 30s - faster replies, still gentle on Instagram
TTS_MAX_CHARS  = 140                     # Meta reads ~140 chars from the notification preview
IMAGE_DIR      = os.path.expanduser("~/instagrambot/img_cache")
SEEN_FILE      = os.path.expanduser("~/instagrambot/seen.json")
SESSION_FILE   = os.path.expanduser("~/instagrambot/session.json")
os.makedirs(IMAGE_DIR, exist_ok=True)

# Whitelist of numeric Instagram user_ids the bot will reply to.
# Use get_id.py to resolve handles -> ids. Empty set = reply to no one (safe).
ALLOWED_SENDERS = {}
# END CONFIG


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[seen] read failed: {e}")
    return set()

def save_seen(seen):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen), f)
    except OSError as e:
        print(f"[seen] write failed: {e}")

seen_messages = load_seen()

# LOGIN: load saved session ONLY. No auto fresh-login.
cl = Client()
cl.delay_range = (2, 5)

if not os.path.exists(SESSION_FILE):
    print(f"FATAL: {SESSION_FILE} missing.")
    print("Run login.py ONCE from your phone (solve any challenges first), then start bot.py.")
    raise SystemExit(1)

try:
    cl.load_settings(SESSION_FILE)
    me = cl.account_info()
    print(f"OK Session loaded - logged in as @{me.username}")
except Exception as e:
    print(f"FATAL: saved session is invalid: {type(e).__name__}: {e}")
    print("")
    print("DO NOT keep retrying. Do this instead:")
    print("  1. Stop this bot (Ctrl+C).")
    print("  2. Open Instagram on your phone, complete any challenge/checkpoint.")
    print("  3. Wait 15 minutes.")
    print("  4. Run:  python login.py")
    print("  5. After login.py succeeds, run:  python bot.py")
    raise SystemExit(1)

my_user_id = str(cl.user_id)
print(f"my user_id = {my_user_id}")
print(f"poll={CHECK_INTERVAL}s  seen={len(seen_messages)}  whitelist={len(ALLOWED_SENDERS)} user(s)")

# First-run helper: print recent DM senders so you can build the whitelist
def show_recent_senders():
    try:
        threads = cl.direct_threads(amount=10)
        print("")
        print("Recent DM senders (copy the user_id values you want into ALLOWED_SENDERS):")
        seen_uids = set()
        for t in threads:
            for m in cl.direct_messages(t.id, amount=5):
                uid = str(m.user_id)
                if uid == my_user_id or uid in seen_uids:
                    continue
                seen_uids.add(uid)
                try:
                    u = cl.user_info(m.user_id)
                    handle = f"@{u.username}"
                except Exception:
                    handle = "(unknown)"
                in_wl = "OK in whitelist" if uid in ALLOWED_SENDERS else "  add me"
                print(f"  {in_wl}  {uid}  {handle}")
        print("")
    except Exception as e:
        print(f"[sender list] failed: {e}")

# DISABLED on startup — the call to direct_threads() can hang on a freshly-loaded
# session, and the whitelist is already filled. If you ever need to rebuild the
# whitelist, uncomment the line below.
# show_recent_senders()

# AI
def ask_ai(image_path=None, text=None):
    try:
        if image_path and os.path.exists(image_path):
            prompt = (
                "Look at this image carefully. "
                "If it contains a math problem or any question, give only the direct answer in one short sentence. "
                "If it is just a regular image, describe what you see in one short sentence."
            )
            result = ollama.chat(
                model="llava:latest",
                messages=[{"role": "user", "content": prompt, "images": [image_path]}]
            )
        else:
            prompt = (
                f"{text}\n\n"
                "Reply in one short sentence. Be direct. No preamble, no 'Sure!', no explanation unless asked."
            )
            result = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": prompt}]
            )
        return result["message"]["content"].strip()
    except Exception as e:
        print(f"  [AI error] {e}")
        return None

# Format reply for Meta TTS notification preview
def format_for_tts(text):
    if not text:
        return None
    first = re.split(r'(?<=[.!?])\s', text.strip(), maxsplit=1)[0]
    if len(first) > TTS_MAX_CHARS:
        first = first[:TTS_MAX_CHARS - 1].rstrip() + "..."
    return first

# IMAGE DOWNLOAD
def download_image(url, dest_path):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
            "Accept": "*/*",
        }
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return dest_path
    except Exception as e:
        print(f"  [download error] {e}")
        return None

# GET IMAGE URL SAFELY
def get_media_url(media):
    try:
        if hasattr(media, "image_versions2") and media.image_versions2:
            for c in media.image_versions2.candidates:
                if getattr(c, "url", None):
                    return str(c.url)
        if hasattr(media, "thumbnail_url") and media.thumbnail_url:
            return str(media.thumbnail_url)
        if hasattr(media, "video_versions") and media.video_versions:
            for v in media.video_versions:
                if getattr(v, "url", None):
                    return str(v.url)
    except Exception as e:
        print(f"  [media url error] {e}")
    return None

# SEED: mark existing thread messages as seen (no reply)
def seed_seen():
    try:
        threads = cl.direct_threads(amount=10)
        added = 0
        for thread in threads:
            for m in cl.direct_messages(thread.id, amount=5):
                if m.id not in seen_messages:
                    seen_messages.add(m.id)
                    added += 1
        if added:
            save_seen(seen_messages)
            print(f"OK Seeded {added} historic messages as seen")
    except Exception as e:
        print(f"[seed] failed: {e}")

seed_seen()

# Watchdog helper: hard timeout on instagrapi calls so a hung API request
# doesn't freeze the bot forever. SIGALRM-based, main-thread only.
class CallTimeout(Exception):
    pass

def _alarm_handler(signum, frame):
    raise CallTimeout("instagrapi call exceeded timeout")

def _with_timeout(seconds, fn, *args, **kwargs):
    """Run fn(*args, **kwargs) with a hard wall-clock timeout via SIGALRM."""
    old = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(seconds)
    try:
        return fn(*args, **kwargs)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

# CHECK DMs
def check_dms():
    try:
        threads = _with_timeout(30, cl.direct_threads, amount=10)
    except CallTimeout:
        print("  [warn] direct_threads timed out, skipping this cycle")
        return
    except Exception as e:
        print(f"  [warn] direct_threads failed: {e}")
        return

    for thread in threads:
        thread_id = getattr(thread, "pk", None) or getattr(thread, "id", None)
        if not thread_id:
            continue

        try:
            messages = _with_timeout(20, cl.direct_messages, thread_id, amount=5)
        except CallTimeout:
            print(f"  [warn] thread {thread_id} fetch timed out, skipping")
            continue
        except Exception as e:
            print(f"  [thread {thread_id}] fetch failed: {e}")
            continue

        for message in messages:
            if message.id in seen_messages:
                continue

            # Mark seen FIRST so retries don't double-reply
            seen_messages.add(message.id)
            save_seen(seen_messages)

            # Skip our own messages
            if str(message.user_id) == my_user_id:
                continue

            # Whitelist gate: reply only to allowed senders
            if ALLOWED_SENDERS and str(message.user_id) not in ALLOWED_SENDERS:
                print(f"  [skip] user {message.user_id} not in whitelist")
                continue

            item_type = getattr(message, "item_type", "")
            print(f"[{thread_id}] new {item_type} from {message.user_id}")

            try:
                reply_full = None

                if item_type == "text" and getattr(message, "text", None):
                    print(f"  -> text: {message.text[:60]}")
                    reply_full = ask_ai(text=message.text)

                elif item_type in ("media", "photo"):
                    media = getattr(message, "media", None)
                    if media:
                        url = get_media_url(media)
                        if url:
                            img_path = os.path.join(IMAGE_DIR, f"{message.id}.jpg")
                            if download_image(url, img_path):
                                print("  -> image received")
                                reply_full = ask_ai(image_path=img_path)

                elif item_type in ("clip", "reel_clip", "story_share", "video_call_event"):
                    reply_full = "Got your video - I can only look at photos right now."

                if reply_full:
                    short = format_for_tts(reply_full)
                    cl.direct_send(short, thread_ids=[thread_id])
                    print(f"  OK replied (TTS): {short}")
                    if reply_full.strip() != short and len(reply_full.strip()) > len(short) + 5:
                        time.sleep(random.uniform(2, 4))
                        cl.direct_send(reply_full, thread_ids=[thread_id])
                        print(f"  OK follow-up sent")
                    time.sleep(random.uniform(2, 5))

            except Exception as e:
                msg = str(e).lower()
                if "challenge" in msg or "checkpoint" in msg or "feedback" in msg:
                    print(f"[AUTH] Instagram wants verification: {e}")
                    print("Stop the bot, complete the challenge on your phone, then restart.")
                    raise SystemExit(1)
                print(f"  [reply error] {type(e).__name__}: {e}")

# RUN
print(f"Bot running. Checking every {CHECK_INTERVAL}s. Ctrl+C to stop.\n")
while True:
    try:
        check_dms()
    except SystemExit:
        raise
    except Exception as e:
        msg = str(e).lower()
        if "challenge" in msg or "checkpoint" in msg or "feedback" in msg:
            print(f"[AUTH] {e}")
            print("Stopping. Solve the challenge on your phone, then restart me manually.")
            raise SystemExit(1)
        print(f"[loop] {type(e).__name__}: {e}")
    time.sleep(CHECK_INTERVAL)
