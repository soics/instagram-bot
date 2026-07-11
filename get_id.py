#!/usr/bin/env python3
"""
Resolve one or more Instagram handles -> numeric user_ids, using the saved session.

Usage:
    python get_id.py handle1 handle2 handle3 ...

Example:
    python get_id.py quid.x thatgirl._mairin nadz_hbk scriptless_ ririi.wayzx._

Output is one line per handle:
    @handle -> 17841234567890123

Use the printed numbers in bot.py's ALLOWED_SENDERS set.
"""

from instagrapi import Client
import os
import sys

SESSION_FILE = os.path.expanduser("~/instagrambot/session.json")

if not os.path.exists(SESSION_FILE):
    print(f"ERROR: {SESSION_FILE} does not exist. Run login.py first.")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python get_id.py handle1 handle2 ...")
    sys.exit(1)

cl = Client()
cl.delay_range = (1, 2)

try:
    cl.load_settings(SESSION_FILE)
    cl.account_info()  # validate the session before lookups
except Exception as e:
    print(f"ERROR: saved session is invalid: {type(e).__name__}: {e}")
    print("Run login.py from your phone (solve any challenge first), then retry.")
    sys.exit(1)

print(f"Session OK. Looking up {len(sys.argv) - 1} handle(s)...\n")

results = []
for raw in sys.argv[1:]:
    handle = raw.lstrip("@")
    try:
        uid = cl.user_id_from_username(handle)
        results.append((handle, uid, None))
        print(f"  @{handle:30s} -> {uid}")
    except Exception as e:
        results.append((handle, None, str(e)))
        print(f"  @{handle:30s} -> ERROR: {e}")

print("")
print("Copy the numbers above into bot.py ALLOWED_SENDERS, like this:")
print("  ALLOWED_SENDERS = {")
for handle, uid, err in results:
    if uid is not None:
        print(f'      "{uid}",   # @{handle}')
    else:
        print(f'      # @{handle}  # lookup failed: {err}')
print("  }")
