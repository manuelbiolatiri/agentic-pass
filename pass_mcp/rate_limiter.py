import os
import json
import uuid
import datetime
from pathlib import Path
from typing import Tuple

CONFIG_DIR = Path.home() / ".pass_mcp"
DEVICE_ID_FILE = CONFIG_DIR / "device_id"
USAGE_FILE = CONFIG_DIR / "usage.json"
DAILY_FREE_PASS_LIMIT = 100

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

def check_and_increment_rate_limit(has_api_key: bool = False) -> Tuple[bool, str]:
    """
    Checks if the current device/installer is allowed to issue a pass.
    If has_api_key is True, bypasses local rate limit.
    Otherwise, enforces hardcoded 10 passes per day.
    """
    if has_api_key:
        return True, "API Key authenticated: Unlimited quota."

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    device_id = get_or_create_device_id()

    usage_data = {"date": today, "count": 0, "device_id": device_id}

    if USAGE_FILE.exists():
        try:
            stored = json.loads(USAGE_FILE.read_text())
            if stored.get("date") == today:
                usage_data["count"] = stored.get("count", 0)
        except Exception:
            pass

    if usage_data["count"] >= DAILY_FREE_PASS_LIMIT:
        return False, (
            f"Daily free limit reached ({DAILY_FREE_PASS_LIMIT}/{DAILY_FREE_PASS_LIMIT} passes issued today for device {device_id}). "
            f"Set WALLETKIT_API_KEY environment variable for unlimited pass issuance."
        )

    # Increment count
    usage_data["count"] += 1
    USAGE_FILE.write_text(json.dumps(usage_data, indent=2))

    remaining = DAILY_FREE_PASS_LIMIT - usage_data["count"]
    return True, f"Free daily pass issued ({usage_data['count']}/{DAILY_FREE_PASS_LIMIT} used today, {remaining} remaining)."
