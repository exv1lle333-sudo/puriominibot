"""
Проверка подписи Telegram WebApp initData.
Алгоритм строго по документации:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
"""
import hmac
import hashlib
import json
import time
import logging
from urllib.parse import parse_qsl

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict | None:
    """
    Возвращает {"user": {...}, "auth_date": int} если подпись верна, иначе None.
    """
    if not init_data or not bot_token:
        return None

    try:
        pairs = parse_qsl(init_data, strict_parsing=True, keep_blank_values=True)
    except ValueError:
        return None

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        logger.warning("PurioApp: невалидная подпись initData")
        return None

    auth_date = int(data.get("auth_date", "0") or 0)
    if max_age_seconds and (time.time() - auth_date) > max_age_seconds:
        logger.warning("PurioApp: initData просрочена")
        return None

    try:
        user = json.loads(data.get("user", "{}"))
    except json.JSONDecodeError:
        user = {}

    return {"user": user, "auth_date": auth_date}
