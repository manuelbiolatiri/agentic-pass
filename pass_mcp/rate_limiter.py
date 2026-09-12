import os
import json
import uuid
import hashlib
import datetime
from pathlib import Path
from typing import Optional, Tuple

CONFIG_DIR = Path.home() / ".pass_mcp"
DEVICE_ID_FILE = CONFIG_DIR / "device_id"
USAGE_FILE = CONFIG_DIR / "usage.json"
DAILY_PASS_LIMIT = 100

def get_or_create_device_id() -> str:
    """Gets or generates a persistent device/installer UUID."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if DEVICE_ID_FILE.exists():
        device_id = DEVICE_ID_FILE.read_text().strip()
        if device_id:
            return device_id

    new_id = f"dev_{uuid.uuid4().hex[:16]}"
    DEVICE_ID_FILE.write_text(new_id)
    return new_id

def _identity_for(api_key: Optional[str], device_id: str) -> str:
    """Buckets usage per business API key when one is supplied, falling back
    to the local installer device otherwise. The key itself is never stored
    on disk - only a truncated hash, so usage.json can't leak credentials.
    A caller can no longer skip the quota just by passing a non-empty
    string: any distinct string gets its own bucket, still capped, so a
    garbage key doesn't buy unlimited local quota - it just wastes its own
    100/day allowance before failing auth upstream.
    """
    key = (api_key or "").strip()
    if key:
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        return f"key_{digest}"
    return f"device_{device_id}"

def check_and_increment_rate_limit(api_key: Optional[str] = None) -> Tuple[bool, str]:
    """
    Enforces a flat quota of DAILY_PASS_LIMIT (100) pass issuances per day,
    per identity: per business API key when one is supplied, per local
    installer device otherwise. This is a client-side courtesy guard only -
    wallet-pass-api is the source of truth for whether a key is actually
    valid and for any server-side quota it chooses to enforce.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    device_id = get_or_create_device_id()
    identity = _identity_for(api_key, device_id)
    today = datetime.date.today().isoformat()

    store = {}
    if USAGE_FILE.exists():
        try:
            store = json.loads(USAGE_FILE.read_text())
            if not isinstance(store, dict):
                store = {}
        except Exception:
            store = {}

    bucket = store.get(identity) or {}
    if bucket.get("date") != today:
        bucket = {"date": today, "count": 0}

    scope = "business" if (api_key or "").strip() else f"device {device_id}"

    if bucket["count"] >= DAILY_PASS_LIMIT:
        return False, (
            f"Daily limit reached ({DAILY_PASS_LIMIT}/{DAILY_PASS_LIMIT} passes issued today for {scope})."
        )

    bucket["count"] += 1
    store[identity] = bucket
    USAGE_FILE.write_text(json.dumps(store, indent=2))

    remaining = DAILY_PASS_LIMIT - bucket["count"]
    return True, f"Pass issued ({bucket['count']}/{DAILY_PASS_LIMIT} used today for {scope}, {remaining} remaining)."
