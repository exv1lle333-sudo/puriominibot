"""
PurioApp backend — aiohttp-сервер: отдаёт статический фронтенд (webapp/static)
и REST API для мини-приложения.

Запуск (из корня проекта, рядом с bot.py):
    python -m webapp.server

Требует ту же .env, что и bot.py (BOT_TOKEN и т.д.), плюс опционально
WEBAPP_HOST / WEBAPP_PORT / WEBAPP_DEV_MODE (см. config.py).
"""
import logging
import time
import asyncio
from pathlib import Path

from aiohttp import web

import database as db
import remnawave_client
from config import (
    BOT_TOKEN, TARIFFS, TARIFF_LABELS, REFERRAL_BONUS_DAYS, REFERRAL_PERCENT,
    CHANNEL_LINK, SUPPORT_USERNAME, WEBAPP_HOST, WEBAPP_PORT, WEBAPP_DEV_MODE,
    BOT_USERNAME,
)
from webapp import gamedb, casino
from webapp.telegram_auth import validate_init_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


# ---------------- AUTH HELPERS ----------------

async def _authenticate(request: web.Request) -> int:
    """Достаёт и проверяет initData из заголовка X-Init-Data.
    Возвращает telegram user_id, либо кидает web.HTTPUnauthorized."""
    init_data = request.headers.get("X-Init-Data", "")

    if not init_data and WEBAPP_DEV_MODE:
        # dev-режим: разрешаем ?dev_user_id=123 для тестирования без Telegram
        dev_id = request.query.get("dev_user_id") or request.headers.get("X-Dev-User-Id")
        if dev_id:
            dev_id = int(dev_id)
            await db.get_or_create_user(dev_id, f"dev_{dev_id}", "Dev User")
            return dev_id

    result = validate_init_data(init_data, BOT_TOKEN)
    if not result or not result["user"].get("id"):
        raise web.HTTPUnauthorized(reason="invalid_init_data")

    user = result["user"]
    # синхронизируем базовые данные пользователя с основной БД бота
    await db.get_or_create_user(
        user["id"],
        user.get("username") or "",
        f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
    )
    return int(user["id"])


def _is_sub_active(expire_ts) -> bool:
    return bool(expire_ts) and expire_ts >= time.time()


async def _sync_referral_task(user_id: int):
    """Идемпотентно синхронизирует прогресс задания "пригласи друга" по факту
    появления новых рефералов сегодня (см. gamedb.set_task_progress)."""
    referrals = await db.get_referrals(user_id)
    today_key = time.strftime("%Y%m%d", time.gmtime())
    invited_today = sum(1 for r in referrals if time.strftime("%Y%m%d", time.gmtime(r["created_at"])) == today_key)
    if invited_today:
        await gamedb.set_task_progress(user_id, "invite_friend", invited_today)


async def _dragon_payload(user_id: int) -> dict:
    gu = await gamedb.get_or_create_game_user(user_id)
    owned = await gamedb.get_user_skins(user_id)
    skins = []
    for s in gamedb.DRAGON_SKINS:
        skins.append({
            **s,
            "owned": s["code"] in owned,
            "equipped": s["code"] == gu["equipped_skin"],
            "locked": s["code"] not in owned,
        })
    return {
        "level": gu["level"],
        "xp": gu["xp"],
        "xp_needed": gamedb.xp_for_level(gu["level"]),
        "equipped_skin": gu["equipped_skin"],
        "skins": skins,
    }


# ---------------- ROUTES: AUTH / STATE ----------------

async def api_auth(request: web.Request):
    user_id = await _authenticate(request)
    streak = await gamedb.touch_daily_streak(user_id)
    return web.json_response({"ok": True, "user_id": user_id, "streak": streak})


async def api_state(request: web.Request):
    user_id = await _authenticate(request)
    gu = await gamedb.get_or_create_game_user(user_id)
    user = await db.get_user(user_id)
    week_hours = await gamedb.get_weekly_usage_series(user_id, days=7)
    dragon = await _dragon_payload(user_id)

    from config import DAILY_STREAK_REWARDS
    next_idx = min(gu["streak_day"] + 1, len(DAILY_STREAK_REWARDS) - 1)

    return web.json_response({
        "user_id": user_id,
        "username": user["username"] if user else "",
        "points": gu["points"],
        "dragon": dragon,
        "streak": {
            "day_index": gu["streak_day"],
            "rewards": DAILY_STREAK_REWARDS,
            "next_reward": DAILY_STREAK_REWARDS[next_idx],
            "week_key": gu["week_key"],
        },
        "subscription": {
            "active": _is_sub_active(user["subscription_expire"]) if user else False,
            "expires_at": user["subscription_expire"] if user else 0,
        },
        "vpn_week_series": week_hours,
        "balance_rub": user["balance"] if user else 0,
    })


# ---------------- ROUTES: TASKS ----------------

async def api_tasks(request: web.Request):
    user_id = await _authenticate(request)
    await _sync_referral_task(user_id)
    tasks = await gamedb.get_today_tasks(user_id)
    return web.json_response({"tasks": tasks})


async def api_tasks_claim(request: web.Request):
    user_id = await _authenticate(request)
    body = await request.json()
    task_code = body.get("task_code")
    result = await gamedb.claim_task(user_id, task_code)
    if result is None:
        return web.json_response({"ok": False, "error": "Задание ещё не выполнено или уже забрано"}, status=400)
    return web.json_response({"ok": True, **result})


# ---------------- ROUTES: PROFILE ----------------

async def api_profile(request: web.Request):
    user_id = await _authenticate(request)
    user = await db.get_user(user_id)
    referrals = await db.get_referrals(user_id)
    await gamedb.bump_task_progress(user_id, "check_profile", amount=1)
    await _sync_referral_task(user_id)

    bot_username = BOT_USERNAME or ""
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}" if bot_username else ""

    return web.json_response({
        "user_id": user_id,
        "username": user["username"],
        "balance_rub": user["balance"],
        "subscription_active": _is_sub_active(user["subscription_expire"]),
        "subscription_expires_at": user["subscription_expire"],
        "subscription_url": user["subscription_url"],
        "referral_link": ref_link,
        "referral_count": user["referral_count"],
        "referral_paid_count": user["referral_paid_count"],
        "referral_earned": user["referral_earned"],
        "support_username": SUPPORT_USERNAME,
        "channel_link": CHANNEL_LINK,
    })


async def api_tariffs(request: web.Request):
    await _authenticate(request)
    tariffs = [{"days": d, "price": p, "label": TARIFF_LABELS.get(d, f"{d} дней")} for d, p in TARIFFS.items()]
    return web.json_response({"tariffs": tariffs})


async def api_subscription_buy(request: web.Request):
    user_id = await _authenticate(request)
    body = await request.json()
    days = int(body.get("days", 0))
    price = TARIFFS.get(days)
    if price is None:
        return web.json_response({"ok": False, "error": "Тариф не найден"}, status=400)

    user = await db.get_user(user_id)
    if user["balance"] < price:
        return web.json_response({
            "ok": False,
            "error": f"Недостаточно средств. Не хватает {price - user['balance']:.0f}₽",
        }, status=400)

    try:
        subscription_url = await remnawave_client.provision_subscription(user_id, days)
    except Exception:
        logger.exception("Ошибка выдачи подписки через Remnawave (webapp)")
        return web.json_response({"ok": False, "error": "Не удалось выдать подписку, попробуй позже"}, status=500)

    await db.update_balance(user_id, -price)
    new_expire = await db.extend_subscription(user_id, days, subscription_url=subscription_url,
                                               tariff_days=days, price=price)
    await db.add_log(user_id, "subscription_purchased_webapp", details=f"days={days} price={price}")

    referrer_id = user["referrer_id"]
    if referrer_id:
        bonus = round(price * REFERRAL_PERCENT, 2)
        if bonus > 0:
            await db.update_balance(referrer_id, bonus)
            await db.add_referral_earned(referrer_id, bonus)

    return web.json_response({
        "ok": True,
        "subscription_url": subscription_url,
        "expires_at": new_expire,
    })


async def api_promo_activate(request: web.Request):
    user_id = await _authenticate(request)
    body = await request.json()
    code = (body.get("code") or "").strip().upper()
    if not code:
        return web.json_response({"ok": False, "error": "Введи код"}, status=400)

    promo = await db.get_promo_code(code)
    if not promo or not promo["active"]:
        return web.json_response({"ok": False, "error": "Промокод не найден"}, status=404)
    if promo["used_count"] >= promo["max_activations"]:
        return web.json_response({"ok": False, "error": "Лимит активаций исчерпан"}, status=400)
    if await db.has_user_used_promo(code, user_id):
        return web.json_response({"ok": False, "error": "Ты уже использовал этот промокод"}, status=400)

    activated = await db.activate_promo_code(code, user_id)
    if not activated:
        return web.json_response({"ok": False, "error": "Не удалось активировать промокод"}, status=400)

    try:
        subscription_url = await remnawave_client.provision_subscription(user_id, promo["days"])
        new_expire = await db.extend_subscription(user_id, promo["days"], subscription_url=subscription_url)
    except Exception:
        logger.exception("Ошибка выдачи подписки по промокоду (webapp)")
        return web.json_response({"ok": False, "error": "Промокод активирован, но не удалось выдать VPN — напиши в поддержку"}, status=500)

    return web.json_response({"ok": True, "days": promo["days"], "expires_at": new_expire})


# ---------------- ROUTES: CASINO ----------------

async def api_casino_state(request: web.Request):
    user_id = await _authenticate(request)
    gu = await gamedb.get_or_create_game_user(user_id)
    history = await gamedb.get_casino_history(user_id, limit=15)
    return web.json_response({"points": gu["points"], "history": history})


async def api_casino_dice(request: web.Request):
    user_id = await _authenticate(request)
    body = await request.json()
    bet = int(body.get("bet", 0))
    win_chance = int(body.get("win_chance", 50))

    gu = await gamedb.get_or_create_game_user(user_id)
    try:
        result = casino.play_dice(bet, gu["points"], win_chance)
    except casino.CasinoError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

    new_balance = await gamedb.add_points(user_id, result["net"], "casino_dice")
    await gamedb.record_casino_round(user_id, "dice", bet, result["payout"], result)

    return web.json_response({"ok": True, "result": result, "new_balance": new_balance})


async def api_casino_slots(request: web.Request):
    user_id = await _authenticate(request)
    body = await request.json()
    bet = int(body.get("bet", 0))

    gu = await gamedb.get_or_create_game_user(user_id)
    try:
        result = casino.play_slots(bet, gu["points"])
    except casino.CasinoError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

    new_balance = await gamedb.add_points(user_id, result["net"], "casino_slots")
    await gamedb.record_casino_round(user_id, "slots", bet, result["payout"], result)

    return web.json_response({"ok": True, "result": result, "new_balance": new_balance})


# ---------------- ROUTES: SHOP / GIFTS / DRAGON ----------------

async def api_shop(request: web.Request):
    await _authenticate(request)
    return web.json_response({
        "available": False,
        "title": "🛍 Purio Shop",
        "message": "Магазин скинов и предметов в разработке. Скоро сюда добавим скины для дракона и другие плюшки!",
    })


async def api_gifts(request: web.Request):
    await _authenticate(request)
    return web.json_response({
        "available": False,
        "title": "🎁 Обмен на подарки",
        "message": "Обмен Purio Points на подарки в разработке. Копи поинты — скоро сможешь обменять их на призы!",
    })


async def api_dragon_equip(request: web.Request):
    user_id = await _authenticate(request)
    body = await request.json()
    skin_code = body.get("skin_code")
    owned = await gamedb.get_user_skins(user_id)
    if skin_code not in owned:
        return web.json_response({"ok": False, "error": "Этот скин ещё не открыт"}, status=400)
    await gamedb.set_equipped_skin(user_id, skin_code)
    return web.json_response({"ok": True})


# ---------------- STATIC / APP ----------------

@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        try:
            resp = await handler(request)
        except web.HTTPException as exc:
            resp = exc
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Init-Data, X-Dev-User-Id"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])

    app.router.add_post("/api/auth", api_auth)
    app.router.add_get("/api/state", api_state)
    app.router.add_get("/api/tasks", api_tasks)
    app.router.add_post("/api/tasks/claim", api_tasks_claim)
    app.router.add_get("/api/profile", api_profile)
    app.router.add_get("/api/tariffs", api_tariffs)
    app.router.add_post("/api/subscription/buy", api_subscription_buy)
    app.router.add_post("/api/promo/activate", api_promo_activate)
    app.router.add_get("/api/casino/state", api_casino_state)
    app.router.add_post("/api/casino/dice", api_casino_dice)
    app.router.add_post("/api/casino/slots", api_casino_slots)
    app.router.add_get("/api/shop", api_shop)
    app.router.add_get("/api/gifts", api_gifts)
    app.router.add_post("/api/dragon/equip", api_dragon_equip)
    app.router.add_route("OPTIONS", "/{tail:.*}", lambda r: web.Response())

    app.router.add_static("/static/", STATIC_DIR, show_index=False)

    async def index(request):
        return web.FileResponse(STATIC_DIR / "index.html")

    app.router.add_get("/", index)
    app.router.add_get("/app", index)

    return app


async def _main():
    await db.init_db()
    await gamedb.init_gamedb()

    from webapp.scheduler import vpn_points_watcher
    asyncio.create_task(vpn_points_watcher())

    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()
    logger.info(f"PurioApp запущен на http://{WEBAPP_HOST}:{WEBAPP_PORT}")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(_main())
