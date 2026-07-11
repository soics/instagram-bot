from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
import os
import sys

import env_loader  # noqa: F401  - loads ~/instagrambot/.env into os.environ

# Username/password come from ~/instagrambot/.env (loaded by env_loader).
USERNAME = os.getenv("IG_USERNAME", "mv.lls")
PASSWORD = os.getenv("IG_PASSWORD", "")

if not PASSWORD:
    print("ERROR: IG_PASSWORD env var is not set.")
    print("Run it like:  IG_PASSWORD='yourpassword' python login.py")
    sys.exit(1)

def challenge_code_handler(username, choice):
    print("Instagram sent a verification code.")
    code = input("Enter the code: ")
    return code

cl = Client()
cl.challenge_code_handler = challenge_code_handler
cl.delay_range = (2, 5)

try:
    cl.login(USERNAME, PASSWORD)
except ChallengeRequired:
    print("Challenge triggered, attempting to resolve...")
    try:
        cl.challenge_resolve(cl.last_json)
    except Exception as e:
        print(f"Challenge resolve failed: {e}")
        print("Open Instagram on your phone, complete the challenge there, then re-run this script.")
        sys.exit(1)

cl.dump_settings("session.json")
print(f"OK Success. session.json saved for @{USERNAME}.")
