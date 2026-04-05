"""
Telegram WebApp initData validation.
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qs

from fastapi import HTTPException, Request

BOT_TOKEN = os.environ.get("OSEN_BOT_TOKEN", "")
ALLOWED_USER_IDS = {7999727989}  # Dan only
MAX_AGE_SECONDS = 86400  # initData valid for 24 hours


def _validate_init_data(init_data: str) -> dict:
    """Validate Telegram WebApp initData and return parsed data."""
    parsed = parse_qs(init_data, keep_blank_values=True)

    # Extract hash
    received_hash = parsed.get("hash", [None])[0]
    if not received_hash:
        raise HTTPException(401, "Missing hash in initData")

    # Build data-check-string: alphabetically sorted key=value pairs, excluding hash
    pairs = []
    for key, values in parsed.items():
        if key == "hash":
            continue
        pairs.append(f"{key}={values[0]}")
    pairs.sort()
    data_check_string = "\n".join(pairs)

    # Compute HMAC
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(401, "Invalid initData signature")

    # Check auth_date freshness
    auth_date = parsed.get("auth_date", [None])[0]
    if auth_date:
        age = time.time() - int(auth_date)
        if age > MAX_AGE_SECONDS:
            raise HTTPException(401, "initData expired")

    # Parse user
    user_raw = parsed.get("user", [None])[0]
    if not user_raw:
        raise HTTPException(401, "No user in initData")

    user = json.loads(user_raw)
    return user


async def require_telegram_user(request: Request) -> dict:
    """FastAPI dependency: validate initData from Authorization header or query param."""
    # Try Authorization header first: "tma <initData>"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("tma "):
        init_data = auth[4:]
    else:
        # Fallback: query param
        init_data = request.query_params.get("initData", "")

    if not init_data:
        raise HTTPException(401, "No Telegram initData provided")

    user = _validate_init_data(init_data)

    # Check user whitelist
    user_id = user.get("id")
    if user_id not in ALLOWED_USER_IDS:
        raise HTTPException(403, f"User {user_id} not allowed")

    return user
