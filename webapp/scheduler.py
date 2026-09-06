"""
Фоновые задачи PurioApp:
  * начисление Purio Points за каждый час активной подписки VPN
    (2 очка/час по умолчанию, см. config.POINTS_PER_VPN_HOUR)

Работает независимо от polling-процесса бота — просто читает ту же
таблицу users (через database.py) и активные подписки.
"""
import asyncio
import logging
import time

import database as db
from config import POINTS_PER_VPN_HOUR
from webapp import gamedb

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300  # проверяем каждые 5 минут, начисляем за прошедшие целые часы


async def _try_get_traffic_bytes(user_id: int) -> int:
    """Best-effort: пытается достать реальный трафик пользователя из Remnawave.
    Если поле недоступно/SDK отличается — просто возвращает 0, не ломая начисление очков."""
    try:
        import remnawave_client
        user = await remnawave_client.get_user_by_username(f"tg_{user_id}")
        if not user:
            return 0
        for attr in ("used_traffic_bytes", "usedTrafficBytes", "traffic_used_bytes", "used_traffic"):
            val = getattr(user, attr, None)
            if isinstance(val, (int, float)):
                return int(val)
    except Exception:
        logger.debug("Не удалось получить трафик пользователя %s из Remnawave", user_id, exc_info=True)
    return 0


async def credit_vpn_hours_once():
    """Один проход по всем пользователям: начисляет очки за прошедшие полные часы подписки."""
    now_hour = int(time.time() // 3600)
    user_ids = await db.get_all_user_ids()

    for user_id in user_ids:
        try:
            user = await db.get_user(user_id)
            if not user or not user["subscription_expire"] or user["subscription_expire"] < time.time():
                continue  # подписка неактивна — часы не капают

            last_hour = await gamedb.get_vpn_hour_state(user_id)
            if last_hour == 0:
                # первый раз видим этого пользователя — не начисляем задним числом,
                # просто фиксируем текущий час как точку отсчёта
                await gamedb.set_vpn_hour_state(user_id, now_hour)
                continue

            elapsed_hours = now_hour - last_hour
            if elapsed_hours <= 0:
                continue
            # не начисляем больше 24 часов за один проход (защита от долгого простоя сервиса)
            elapsed_hours = min(elapsed_hours, 24)

            points = elapsed_hours * POINTS_PER_VPN_HOUR
            traffic = await _try_get_traffic_bytes(user_id)

            await gamedb.add_points(user_id, points, "vpn_hourly")
            await gamedb.add_xp(user_id, elapsed_hours * 2)
            await gamedb.log_vpn_usage(user_id, hours=elapsed_hours, points_earned=points, traffic_bytes=traffic)
            await gamedb.set_vpn_hour_state(user_id, now_hour)

        except Exception:
            logger.exception("Ошибка начисления VPN-очков пользователю %s", user_id)


async def vpn_points_watcher():
    while True:
        try:
            await credit_vpn_hours_once()
        except Exception:
            logger.exception("Ошибка в фоновой задаче начисления VPN Purio Points")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
