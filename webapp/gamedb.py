"""
Отдельные таблицы для геймификации PurioApp: очки, уровень дракона, скины,
задания, серия входов, история VPN-часов и казино.

Работают в ТОЙ ЖЕ базе (config.DB_PATH), что и основной бот, но через
собственное asqlite-соединение — чтобы модуль можно было запускать как
отдельный процесс (webapp/server.py), не завися от процесса bot.py.
"""
import time
import json
import logging
import aiosqlite

import database as db
from config import (
    DB_PATH, DAILY_STREAK_REWARDS,
    TAP_ENERGY_MAX, TAP_ENERGY_REGEN_SECONDS, TAP_DAILY_CAP,
    TAP_REWARD_TIERS, POINTS_TO_RUB_RATE, MIN_EXCHANGE_POINTS,
    MYSTERY_BOX_TIERS, WHEEL_SPIN_COST, WHEEL_FREE_SPINS_PER_DAY,
    STREAK_SHIELD_PRICE, XP_BOOSTERS, FOUNDER_CUTOFF_TS,
)
from webapp import casino
from webapp import shop

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


def _now() -> int:
    return int(time.time())


def _today_key(ts: int | None = None) -> str:
    """Календарный день в UTC как YYYYMMDD (int-строка) — ключ для дневных заданий."""
    t = time.gmtime(ts if ts is not None else _now())
    return time.strftime("%Y%m%d", t)


def _iso_week_key(ts: int | None = None) -> str:
    """ISO-неделя (год-неделя) — используется, чтобы серия входов обнулялась каждую неделю."""
    import datetime as _dt
    d = _dt.datetime.utcfromtimestamp(ts if ts is not None else _now())
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


TASKS_CATALOG = [
    dict(code="open_app", title="Открой PurioApp", desc="Просто загляни в приложение сегодня",
         icon="📲", reward_points=5, reward_xp=5, target=1),
    dict(code="vpn_1h", title="1 час под защитой", desc="Проведи 1 час с активным VPN",
         icon="🌐", reward_points=15, reward_xp=10, target=1),
    dict(code="vpn_3h", title="3 часа под защитой", desc="Проведи 3 часа с активным VPN",
         icon="🛡️", reward_points=35, reward_xp=25, target=3),
    dict(code="play_casino", title="Испытай удачу", desc="Сделай хотя бы одну ставку в Purio Casino",
         icon="🎰", reward_points=10, reward_xp=5, target=1),
    dict(code="check_profile", title="Загляни в профиль", desc="Проверь баланс и подписку",
         icon="👤", reward_points=5, reward_xp=5, target=1),
    dict(code="invite_friend", title="Пригласи друга", desc="Приведи нового пользователя по своей ссылке",
         icon="🤝", reward_points=40, reward_xp=30, target=1),
]
TASKS_BY_CODE = {t["code"]: t for t in TASKS_CATALOG}

DRAGON_SKINS = [
    dict(code="default", name="Обычный дракон", desc="Твой стартовый малыш — фиолетовый дракончик Пурио.",
         min_level=1),
    dict(code="shadow", name="Теневой дракон", desc="Открывается на 5 уровне — тёмная чешуя ночного охотника.",
         min_level=5),
    dict(code="golden", name="Золотой дракон", desc="Открывается на 10 уровне — сияющая золотая чешуя.",
         min_level=10),
    dict(code="storm", name="Штормовой дракон", desc="Открывается на 15 уровне — грозовой окрас с ледяными искрами.",
         min_level=15),
    dict(code="cosmic", name="Космический дракон", desc="Открывается на 20 уровне — редчайший облик, достойный легенды.",
         min_level=20),
]
DRAGON_SKINS_BY_CODE = {s["code"]: s for s in DRAGON_SKINS}


def xp_for_level(level: int) -> int:
    """Сколько XP нужно НАБРАТЬ на этом уровне, чтобы перейти на следующий."""
    return 100 + (level - 1) * 60


async def init_gamedb():
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS game_users (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            equipped_skin TEXT DEFAULT 'default',
            week_key TEXT DEFAULT '',
            streak_day INTEGER DEFAULT 0,
            last_streak_day_key TEXT DEFAULT '',
            last_seen_day_key TEXT DEFAULT '',
            created_at INTEGER,
            updated_at INTEGER
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS points_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            delta INTEGER,
            reason TEXT,
            created_at INTEGER
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            user_id INTEGER,
            day_key TEXT,
            task_code TEXT,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, day_key, task_code)
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS vpn_hour_state (
            user_id INTEGER PRIMARY KEY,
            last_credited_hour INTEGER DEFAULT 0
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS vpn_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day_key TEXT,
            hours INTEGER DEFAULT 0,
            traffic_bytes INTEGER DEFAULT 0,
            points_earned INTEGER DEFAULT 0,
            created_at INTEGER
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS casino_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game TEXT,
            bet INTEGER,
            payout INTEGER,
            result_json TEXT,
            created_at INTEGER
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id INTEGER,
            skin_code TEXT,
            unlocked_at INTEGER,
            PRIMARY KEY (user_id, skin_code)
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS tap_state (
            user_id INTEGER PRIMARY KEY,
            energy INTEGER DEFAULT 500,
            energy_updated_at INTEGER,
            day_key TEXT DEFAULT '',
            day_points INTEGER DEFAULT 0
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS crash_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bet INTEGER,
            crash_point REAL,
            started_at INTEGER,
            resolved INTEGER DEFAULT 0,
            won INTEGER DEFAULT 0,
            payout INTEGER DEFAULT 0,
            cashout_multiplier REAL,
            created_at INTEGER
        )
    """)
    # ---------- PURIO SHOP: косметика, боксы, колесо, бустеры ----------
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_items (
            user_id INTEGER,
            item_code TEXT,
            acquired_at INTEGER,
            source TEXT,
            PRIMARY KEY (user_id, item_code)
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_equipped_badges (
            user_id INTEGER,
            slot INTEGER,
            badge_code TEXT,
            PRIMARY KEY (user_id, slot)
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_boosters (
            user_id INTEGER PRIMARY KEY,
            multiplier INTEGER DEFAULT 1,
            expires_at INTEGER DEFAULT 0
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS daily_case_state (
            user_id INTEGER PRIMARY KEY,
            last_claim_day_key TEXT DEFAULT ''
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS wheel_state (
            user_id INTEGER PRIMARY KEY,
            last_free_spin_day_key TEXT DEFAULT ''
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS mystery_box_state (
            user_id INTEGER,
            day_key TEXT,
            box_code TEXT,
            opened_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, day_key, box_code)
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS limited_stock (
            item_code TEXT PRIMARY KEY,
            remaining INTEGER
        )
    """)
    await _db.commit()

    # Лёгкие миграции для баз, созданных до появления Purio Shop 2.0 —
    # каждая обёрнута в свой try/except, как в database.py (столбец уже
    # существует -> просто пропускаем).
    migrations = [
        "ALTER TABLE game_users ADD COLUMN equipped_clothing TEXT DEFAULT ''",
        "ALTER TABLE game_users ADD COLUMN equipped_frame TEXT DEFAULT ''",
        "ALTER TABLE game_users ADD COLUMN equipped_effect TEXT DEFAULT ''",
        "ALTER TABLE game_users ADD COLUMN equipped_nickname_color TEXT DEFAULT ''",
        "ALTER TABLE game_users ADD COLUMN equipped_animation TEXT DEFAULT ''",
        "ALTER TABLE game_users ADD COLUMN equipped_title TEXT DEFAULT ''",
        "ALTER TABLE game_users ADD COLUMN streak_shields INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            await _db.execute(sql)
            await _db.commit()
        except Exception:
            pass

    # Инициализация остатков лимитированных предметов (только если ещё не заведены).
    for code, stock in shop.LIMITED_ITEMS.items():
        await _db.execute(
            "INSERT OR IGNORE INTO limited_stock (item_code, remaining) VALUES (?, ?)",
            (code, stock),
        )
    await _db.commit()

    logger.info("Игровая БД (PurioApp) инициализирована")


# ---------------- GAME USER ----------------

async def get_game_user(user_id: int) -> aiosqlite.Row | None:
    cur = await _db.execute("SELECT * FROM game_users WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def get_or_create_game_user(user_id: int) -> aiosqlite.Row:
    row = await get_game_user(user_id)
    if row:
        return row
    now = _now()
    await _db.execute(
        "INSERT INTO game_users (user_id, points, xp, level, equipped_skin, week_key, "
        "streak_day, last_streak_day_key, last_seen_day_key, created_at, updated_at) "
        "VALUES (?, 0, 0, 1, 'default', ?, 0, '', '', ?, ?)",
        (user_id, _iso_week_key(), now, now),
    )
    await _db.execute(
        "INSERT OR IGNORE INTO user_skins (user_id, skin_code, unlocked_at) VALUES (?, 'default', ?)",
        (user_id, now),
    )
    await _db.commit()
    return await get_game_user(user_id)


async def add_points(user_id: int, delta: int, reason: str) -> int:
    """Начисляет/списывает очки (delta может быть отрицательным). Возвращает новый баланс."""
    await get_or_create_game_user(user_id)
    await _db.execute("UPDATE game_users SET points = MAX(points + ?, 0), updated_at = ? WHERE user_id = ?",
                       (delta, _now(), user_id))
    await _db.execute(
        "INSERT INTO points_ledger (user_id, delta, reason, created_at) VALUES (?, ?, ?, ?)",
        (user_id, delta, reason, _now()),
    )
    await _db.commit()
    row = await get_game_user(user_id)
    return row["points"]


async def add_xp(user_id: int, delta_xp: int) -> tuple[int, int, bool]:
    """Начисляет XP дракону, пересчитывает уровень. Возвращает (level, xp_в_текущем_уровне, level_up?).

    Если у игрока активен XP-бустер (см. buy_booster/get_active_booster),
    delta_xp умножается на его множитель. Бустеры влияют ТОЛЬКО на XP
    (скорость прокачки уровня/скинов), а не на Purio Points — это сделано
    специально, чтобы бустеры не увеличивали объём очков в обороте и не
    били по марже обмена очков на рубли (см. config.py)."""
    booster = await get_active_booster(user_id)
    if booster and delta_xp > 0:
        delta_xp = delta_xp * booster["multiplier"]

    row = await get_or_create_game_user(user_id)
    level = row["level"]
    xp = row["xp"] + delta_xp
    leveled_up = False
    while xp >= xp_for_level(level):
        xp -= xp_for_level(level)
        level += 1
        leveled_up = True
    await _db.execute(
        "UPDATE game_users SET xp = ?, level = ?, updated_at = ? WHERE user_id = ?",
        (xp, level, _now(), user_id),
    )
    await _db.commit()
    if leveled_up:
        await sync_achievement_titles(user_id, level)
    return level, xp, leveled_up


async def set_equipped_skin(user_id: int, skin_code: str):
    await _db.execute("UPDATE game_users SET equipped_skin = ?, updated_at = ? WHERE user_id = ?",
                       (skin_code, _now(), user_id))
    await _db.commit()


async def sync_unlocked_skins(user_id: int, level: int) -> list[str]:
    """Открывает (навсегда) все скины, для которых пройден требуемый уровень.
    Идемпотентно — можно звать при каждом запросе состояния дракона.
    Возвращает список кодов скинов, которые были открыты только что."""
    owned_before = await get_user_skins(user_id)
    newly_unlocked = []
    now = _now()
    for s in DRAGON_SKINS:
        if s["min_level"] <= level and s["code"] not in owned_before:
            await _db.execute(
                "INSERT OR IGNORE INTO user_skins (user_id, skin_code, unlocked_at) VALUES (?, ?, ?)",
                (user_id, s["code"], now),
            )
            newly_unlocked.append(s["code"])
    if newly_unlocked:
        await _db.commit()
    return newly_unlocked


async def get_points_history(user_id: int, limit: int = 20) -> list[aiosqlite.Row]:
    cur = await _db.execute(
        "SELECT * FROM points_ledger WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    return await cur.fetchall()


# ---------------- DAILY STREAK (серия входов, сброс каждую неделю) ----------------

async def touch_daily_streak(user_id: int) -> dict:
    """
    Вызывается при каждом открытии приложения. Если это первый визит за
    сегодня — продвигает серию (или начинает заново, если пропущен день),
    начисляет очки за день серии. Каждую новую ISO-неделю серия стартует с нуля.
    Возвращает {day_index, reward, is_new_day, week_key}.
    """
    row = await get_or_create_game_user(user_id)
    today = _today_key()
    week = _iso_week_key()

    if row["last_seen_day_key"] == today:
        # уже заходил сегодня — просто отдаём текущее состояние
        return {
            "day_index": row["streak_day"],
            "reward": 0,
            "is_new_day": False,
            "week_key": row["week_key"],
        }

    yesterday = _today_key(_now() - 86400)
    shield_used = False
    if row["week_key"] != week:
        # новая неделя — серия обнуляется, начинаем с дня 0 (награда за 1-й день)
        new_day_index = 0
    elif row["last_streak_day_key"] == yesterday:
        # заходил вчера — продолжаем серию (максимум 7 дней в таблице наград)
        new_day_index = min(row["streak_day"] + 1, len(DAILY_STREAK_REWARDS) - 1)
    elif row["streak_shields"] > 0:
        # пропустил день(и), но есть "Защита стрика" (см. buy_streak_shield) —
        # тратим один заряд и продолжаем серию как ни в чём не бывало.
        new_day_index = min(row["streak_day"] + 1, len(DAILY_STREAK_REWARDS) - 1)
        shield_used = True
    else:
        # пропустил день(и) на этой же неделе и защиты нет — серия начинается заново
        new_day_index = 0

    reward = DAILY_STREAK_REWARDS[new_day_index]

    if shield_used:
        await _db.execute(
            "UPDATE game_users SET streak_day = ?, last_streak_day_key = ?, last_seen_day_key = ?, "
            "week_key = ?, streak_shields = streak_shields - 1, updated_at = ? WHERE user_id = ?",
            (new_day_index, today, today, week, _now(), user_id),
        )
    else:
        await _db.execute(
            "UPDATE game_users SET streak_day = ?, last_streak_day_key = ?, last_seen_day_key = ?, "
            "week_key = ?, updated_at = ? WHERE user_id = ?",
            (new_day_index, today, today, week, _now(), user_id),
        )
    await _db.commit()

    await add_points(user_id, reward, "daily_streak")
    await add_xp(user_id, max(reward // 2, 3))
    await bump_task_progress(user_id, "open_app", amount=1)
    await sync_founder_title(user_id)

    return {
        "day_index": new_day_index, "reward": reward, "is_new_day": True,
        "week_key": week, "shield_used": shield_used,
    }


# ---------------- DAILY TASKS ----------------

async def get_today_tasks(user_id: int) -> list[dict]:
    today = _today_key()
    cur = await _db.execute(
        "SELECT * FROM user_tasks WHERE user_id = ? AND day_key = ?", (user_id, today)
    )
    rows = {r["task_code"]: r for r in await cur.fetchall()}

    result = []
    for t in TASKS_CATALOG:
        r = rows.get(t["code"])
        progress = r["progress"] if r else 0
        completed = bool(r["completed"]) if r else False
        claimed = bool(r["claimed"]) if r else False
        result.append({
            **t,
            "progress": min(progress, t["target"]),
            "completed": completed,
            "claimed": claimed,
        })
    return result


async def bump_task_progress(user_id: int, task_code: str, amount: int = 1) -> bool:
    """Увеличивает прогресс задания на сегодня. Возвращает True, если задание только что выполнено."""
    if task_code not in TASKS_BY_CODE:
        return False
    task = TASKS_BY_CODE[task_code]
    today = _today_key()

    cur = await _db.execute(
        "SELECT * FROM user_tasks WHERE user_id = ? AND day_key = ? AND task_code = ?",
        (user_id, today, task_code),
    )
    row = await cur.fetchone()

    if row is None:
        progress = amount
        await _db.execute(
            "INSERT INTO user_tasks (user_id, day_key, task_code, progress, completed, claimed) "
            "VALUES (?, ?, ?, ?, 0, 0)",
            (user_id, today, task_code, progress),
        )
    else:
        if row["completed"]:
            await _db.commit()
            return False
        progress = row["progress"] + amount
        await _db.execute(
            "UPDATE user_tasks SET progress = ? WHERE user_id = ? AND day_key = ? AND task_code = ?",
            (progress, user_id, today, task_code),
        )

    just_completed = progress >= task["target"]
    if just_completed:
        await _db.execute(
            "UPDATE user_tasks SET completed = 1 WHERE user_id = ? AND day_key = ? AND task_code = ?",
            (user_id, today, task_code),
        )
    await _db.commit()
    return just_completed


async def set_task_progress(user_id: int, task_code: str, progress: int) -> bool:
    """Идемпотентно ВЫСТАВЛЯЕТ прогресс задания на сегодня (в отличие от
    bump_task_progress, которое прибавляет). Нужно там, где прогресс считается
    заново при каждом запросе (например, кол-во рефералов за сегодня), чтобы
    повторные вызовы не накручивали значение. Возвращает True, если задание
    только что стало выполненным."""
    if task_code not in TASKS_BY_CODE:
        return False
    task = TASKS_BY_CODE[task_code]
    today = _today_key()

    cur = await _db.execute(
        "SELECT * FROM user_tasks WHERE user_id = ? AND day_key = ? AND task_code = ?",
        (user_id, today, task_code),
    )
    row = await cur.fetchone()
    if row and row["completed"]:
        return False

    if row is None:
        await _db.execute(
            "INSERT INTO user_tasks (user_id, day_key, task_code, progress, completed, claimed) "
            "VALUES (?, ?, ?, ?, 0, 0)",
            (user_id, today, task_code, progress),
        )
    else:
        if progress <= row["progress"]:
            await _db.commit()
            return False
        await _db.execute(
            "UPDATE user_tasks SET progress = ? WHERE user_id = ? AND day_key = ? AND task_code = ?",
            (progress, user_id, today, task_code),
        )

    just_completed = progress >= task["target"]
    if just_completed:
        await _db.execute(
            "UPDATE user_tasks SET completed = 1 WHERE user_id = ? AND day_key = ? AND task_code = ?",
            (user_id, today, task_code),
        )
    await _db.commit()
    return just_completed


async def claim_task(user_id: int, task_code: str) -> dict | None:
    if task_code not in TASKS_BY_CODE:
        return None
    today = _today_key()
    cur = await _db.execute(
        "SELECT * FROM user_tasks WHERE user_id = ? AND day_key = ? AND task_code = ?",
        (user_id, today, task_code),
    )
    row = await cur.fetchone()
    if not row or not row["completed"] or row["claimed"]:
        return None

    task = TASKS_BY_CODE[task_code]
    await _db.execute(
        "UPDATE user_tasks SET claimed = 1 WHERE user_id = ? AND day_key = ? AND task_code = ?",
        (user_id, today, task_code),
    )
    await _db.commit()

    new_balance = await add_points(user_id, task["reward_points"], f"task:{task_code}")
    level, xp, leveled_up = await add_xp(user_id, task["reward_xp"])
    return {
        "points_awarded": task["reward_points"],
        "xp_awarded": task["reward_xp"],
        "new_balance": new_balance,
        "level": level,
        "leveled_up": leveled_up,
    }


# ---------------- VPN HOURLY CREDIT ----------------

async def get_vpn_hour_state(user_id: int) -> int:
    cur = await _db.execute("SELECT last_credited_hour FROM vpn_hour_state WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return row["last_credited_hour"] if row else 0


async def set_vpn_hour_state(user_id: int, hour_bucket: int):
    await _db.execute(
        "INSERT INTO vpn_hour_state (user_id, last_credited_hour) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET last_credited_hour = excluded.last_credited_hour",
        (user_id, hour_bucket),
    )
    await _db.commit()


async def log_vpn_usage(user_id: int, hours: int, points_earned: int, traffic_bytes: int = 0):
    today = _today_key()
    await _db.execute(
        "INSERT INTO vpn_usage_log (user_id, day_key, hours, traffic_bytes, points_earned, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, today, hours, traffic_bytes, points_earned, _now()),
    )
    await _db.commit()
    await bump_task_progress(user_id, "vpn_1h", amount=hours)
    await bump_task_progress(user_id, "vpn_3h", amount=hours)


async def get_weekly_usage_series(user_id: int, days: int = 7) -> list[dict]:
    """Часы онлайн по дням за последние `days` дней (для графика на вкладке VPN)."""
    cur = await _db.execute(
        "SELECT day_key, SUM(hours) as hours, SUM(points_earned) as points, SUM(traffic_bytes) as traffic "
        "FROM vpn_usage_log WHERE user_id = ? GROUP BY day_key ORDER BY day_key DESC LIMIT ?",
        (user_id, days),
    )
    rows = await cur.fetchall()
    return [dict(r) for r in reversed(rows)]


# ---------------- TAPALKA (Purio Tap) ----------------
# Энергия копится сама со временем (TAP_ENERGY_REGEN_SECONDS на 1 единицу),
# каждый тап тратит 1 энергию и даёт tap_reward_for_level(level) очков —
# награда растёт вместе с уровнем дракона. Дневной лимит очков (TAP_DAILY_CAP)
# при этом не меняется от уровня, поэтому честное использование VPN всегда
# остаётся выгоднее фарма тапалкой, на любом уровне.

def tap_reward_for_level(level: int) -> int:
    reward = TAP_REWARD_TIERS[0][1]
    for min_level, r in TAP_REWARD_TIERS:
        if level >= min_level:
            reward = r
    return reward


async def _get_tap_row(user_id: int) -> aiosqlite.Row | None:
    cur = await _db.execute("SELECT * FROM tap_state WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def _ensure_tap_row(user_id: int) -> aiosqlite.Row:
    row = await _get_tap_row(user_id)
    if row:
        return row
    now = _now()
    await _db.execute(
        "INSERT INTO tap_state (user_id, energy, energy_updated_at, day_key, day_points) "
        "VALUES (?, ?, ?, ?, 0)",
        (user_id, TAP_ENERGY_MAX, now, _today_key()),
    )
    await _db.commit()
    return await _get_tap_row(user_id)


def _tap_energy_now(row: aiosqlite.Row, now: int | None = None) -> int:
    now = now if now is not None else _now()
    elapsed = max(0, now - row["energy_updated_at"])
    regen = elapsed // TAP_ENERGY_REGEN_SECONDS
    return min(TAP_ENERGY_MAX, row["energy"] + regen)


async def get_tap_state(user_id: int) -> dict:
    gu = await get_or_create_game_user(user_id)
    row = await _ensure_tap_row(user_id)
    today = _today_key()
    day_points = row["day_points"] if row["day_key"] == today else 0
    reward = tap_reward_for_level(gu["level"])
    return {
        "energy": _tap_energy_now(row),
        "energy_max": TAP_ENERGY_MAX,
        "regen_seconds": TAP_ENERGY_REGEN_SECONDS,
        "reward_per_tap": reward,
        "level": gu["level"],
        "day_points": day_points,
        "day_cap": TAP_DAILY_CAP,
    }


async def do_taps(user_id: int, count: int) -> dict:
    """Списывает энергию за count тапов (столько, сколько реально доступно —
    по энергии и по дневному лимиту очков) и начисляет очки. Возвращает
    итоговое состояние, чтобы клиент мог свериться с сервером."""
    gu = await get_or_create_game_user(user_id)
    reward = tap_reward_for_level(gu["level"])
    count = max(1, min(int(count), TAP_ENERGY_MAX))

    row = await _ensure_tap_row(user_id)
    now = _now()
    today = _today_key()
    energy = _tap_energy_now(row, now)
    day_points = row["day_points"] if row["day_key"] == today else 0

    remaining_cap = max(0, TAP_DAILY_CAP - day_points)
    accepted_taps = max(0, min(count, energy, remaining_cap // max(reward, 1)))
    points_earned = accepted_taps * reward

    new_energy = energy - accepted_taps

    # БАГ (исправлено): раньше energy_updated_at всегда сбрасывался на now,
    # из-за чего "недокопленный" остаток времени до следующей единицы энергии
    # (elapsed % TAP_ENERGY_REGEN_SECONDS) терялся при каждом тапе — игрок
    # копил энергию заметно медленнее, чем должен был. Теперь сохраняем
    # только реально "потраченное" на восстановление время, а остаток —
    # переносим на следующий цикл (если энергия не уже на максимуме).
    if new_energy >= TAP_ENERGY_MAX:
        new_energy_updated_at = now
    else:
        elapsed = max(0, now - row["energy_updated_at"])
        consumed_seconds = (elapsed // TAP_ENERGY_REGEN_SECONDS) * TAP_ENERGY_REGEN_SECONDS
        new_energy_updated_at = row["energy_updated_at"] + consumed_seconds
    new_day_points = day_points + points_earned

    await _db.execute(
        "UPDATE tap_state SET energy = ?, energy_updated_at = ?, day_key = ?, day_points = ? "
        "WHERE user_id = ?",
        (new_energy, new_energy_updated_at, today, new_day_points, user_id),
    )
    await _db.commit()

    new_balance = None
    if points_earned > 0:
        new_balance = await add_points(user_id, points_earned, "tap")
        await add_xp(user_id, max(1, points_earned // 10))
    else:
        gu2 = await get_or_create_game_user(user_id)
        new_balance = gu2["points"]

    return {
        "taps_accepted": accepted_taps,
        "points_earned": points_earned,
        "reward_per_tap": reward,
        "energy": new_energy,
        "energy_max": TAP_ENERGY_MAX,
        "regen_seconds": TAP_ENERGY_REGEN_SECONDS,
        "day_points": new_day_points,
        "day_cap": TAP_DAILY_CAP,
        "new_balance": new_balance,
        "capped": accepted_taps < count,
    }


# ---------------- ОБМЕН PURIO POINTS НА РУБЛИ ----------------
# Курс: POINTS_TO_RUB_RATE очков = 1₽ (по умолчанию 1000 очков = 1₽,
# т.е. 100 000 очков = 100₽). Обменянные рубли зачисляются на баланс
# пользователя (database.balance) — им можно сразу оплатить подписку.

class ExchangeError(Exception):
    pass


async def exchange_points_to_balance(user_id: int, points: int) -> dict:
    points = int(points)
    if points < MIN_EXCHANGE_POINTS:
        raise ExchangeError(f"Минимальная сумма обмена — {MIN_EXCHANGE_POINTS} ✦")

    gu = await get_or_create_game_user(user_id)
    if points > gu["points"]:
        raise ExchangeError("Недостаточно Purio Points")

    rub = round(points / POINTS_TO_RUB_RATE, 2)
    if rub <= 0:
        raise ExchangeError("Слишком маленькая сумма для обмена")

    new_points_balance = await add_points(user_id, -points, "exchange_to_balance")
    await db.update_balance(user_id, rub)
    user = await db.get_user(user_id)

    return {
        "points_spent": points,
        "rub_credited": rub,
        "new_points_balance": new_points_balance,
        "new_rub_balance": user["balance"],
    }


# ---------------- CASINO ----------------

async def record_casino_round(user_id: int, game: str, bet: int, payout: int, result: dict):
    await _db.execute(
        "INSERT INTO casino_rounds (user_id, game, bet, payout, result_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, game, bet, payout, json.dumps(result, ensure_ascii=False), _now()),
    )
    await _db.commit()
    await bump_task_progress(user_id, "play_casino", amount=1)


async def get_casino_history(user_id: int, limit: int = 15) -> list[dict]:
    cur = await _db.execute(
        "SELECT * FROM casino_rounds WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cur.fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["result"] = json.loads(d.pop("result_json"))
        out.append(d)
    return out


# ---------------- SKINS ----------------

async def get_user_skins(user_id: int) -> set[str]:
    cur = await _db.execute("SELECT skin_code FROM user_skins WHERE user_id = ?", (user_id,))
    rows = await cur.fetchall()
    return {r["skin_code"] for r in rows}


# ---------------- CASINO: CRASH ----------------

async def get_active_crash_round(user_id: int) -> aiosqlite.Row | None:
    cur = await _db.execute(
        "SELECT * FROM crash_rounds WHERE user_id = ? AND resolved = 0 ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return await cur.fetchone()


async def start_crash_round(user_id: int, bet: int) -> dict:
    """Создаёт новый раунд Crash: списывает ставку сразу и определяет
    (втайне от клиента) точку взрыва. Если у игрока уже есть активный
    зависший раунд старше CRASH_ROUND_TIMEOUT_SECONDS — он автоматически
    засчитывается как проигрыш перед стартом нового."""
    active = await get_active_crash_round(user_id)
    now = _now()
    if active:
        if now - active["started_at"] < casino.CRASH_ROUND_TIMEOUT_SECONDS:
            raise casino.CasinoError("У тебя уже есть активный раунд Crash — сначала заверши его")
        await _db.execute(
            "UPDATE crash_rounds SET resolved = 1, won = 0, payout = 0, "
            "cashout_multiplier = crash_point WHERE id = ?",
            (active["id"],),
        )
        await _db.commit()

    gu = await get_or_create_game_user(user_id)
    casino._validate_bet(bet, gu["points"])

    crash_point = casino.generate_crash_point()
    await _db.execute(
        "INSERT INTO crash_rounds (user_id, bet, crash_point, started_at, resolved, won, "
        "payout, cashout_multiplier, created_at) VALUES (?, ?, ?, ?, 0, 0, 0, 0, ?)",
        (user_id, bet, crash_point, now, now),
    )
    await _db.commit()
    new_balance = await add_points(user_id, -bet, "casino_crash_bet")

    round_row = await get_active_crash_round(user_id)
    return {"round_id": round_row["id"], "bet": bet, "started_at": now, "new_balance": new_balance}


async def crash_cashout(user_id: int, round_id: int) -> dict:
    cur = await _db.execute(
        "SELECT * FROM crash_rounds WHERE id = ? AND user_id = ?", (round_id, user_id)
    )
    r = await cur.fetchone()
    if not r or r["resolved"]:
        raise casino.CasinoError("Раунд не найден или уже завершён")

    now = _now()
    elapsed = now - r["started_at"]
    current_mult = casino.crash_multiplier_at(elapsed)
    crashed = current_mult >= r["crash_point"]

    if crashed:
        won, payout, mult = 0, 0, r["crash_point"]
    else:
        won, mult = 1, current_mult
        payout = int(round(r["bet"] * mult))

    await _db.execute(
        "UPDATE crash_rounds SET resolved = 1, won = ?, payout = ?, cashout_multiplier = ? WHERE id = ?",
        (won, payout, mult, round_id),
    )
    await _db.commit()

    if payout > 0:
        new_balance = await add_points(user_id, payout, "casino_crash_win")
    else:
        gu = await get_or_create_game_user(user_id)
        new_balance = gu["points"]

    await record_casino_round(user_id, "crash", r["bet"], payout, {
        "crash_point": r["crash_point"],
        "cashout_multiplier": mult,
        "won": bool(won),
    })

    return {
        "won": bool(won),
        "busted": crashed,
        "crash_point": r["crash_point"] if crashed else None,
        "multiplier": round(mult, 2),
        "bet": r["bet"],
        "payout": payout,
        "new_balance": new_balance,
    }


async def get_crash_round_state(user_id: int) -> dict | None:
    """Текущее состояние активного раунда — для синхронизации графика на клиенте
    (не раскрывает crash_point, пока раунд не завершён).

    `busted` — сработала ли точка взрыва к текущему моменту. Само число
    crash_point всё ещё не отдаётся клиенту заранее — только факт "уже
    рвануло или нет", ровно в момент, когда это произошло на сервере.
    Клиент использует это поле, чтобы сразу остановить график и не ждать,
    пока игрок сам нажмёт «Забрать»."""
    r = await get_active_crash_round(user_id)
    if not r:
        return None
    now = _now()
    elapsed = now - r["started_at"]
    current_mult = casino.crash_multiplier_at(elapsed)
    return {
        "round_id": r["id"],
        "bet": r["bet"],
        "started_at": r["started_at"],
        "elapsed": elapsed,
        "multiplier": round(current_mult, 2),
        "busted": current_mult >= r["crash_point"],
    }


# ==================== PURIO SHOP: ИНВЕНТАРЬ / ЭКИПИРОВКА ====================

async def get_user_items(user_id: int) -> set[str]:
    cur = await _db.execute("SELECT item_code FROM user_items WHERE user_id = ?", (user_id,))
    rows = await cur.fetchall()
    return {r["item_code"] for r in rows}


async def _grant_item(user_id: int, item_code: str, source: str):
    await _db.execute(
        "INSERT OR IGNORE INTO user_items (user_id, item_code, acquired_at, source) VALUES (?, ?, ?, ?)",
        (user_id, item_code, _now(), source),
    )
    await _db.commit()


async def get_equipped_badges(user_id: int) -> list[str]:
    cur = await _db.execute(
        "SELECT badge_code FROM user_equipped_badges WHERE user_id = ? ORDER BY slot", (user_id,)
    )
    rows = await cur.fetchall()
    return [r["badge_code"] for r in rows]


async def get_profile_cosmetics(user_id: int) -> dict:
    """Полное состояние косметики пользователя — для профиля в мини-аппе и
    (текстово) в самом боте."""
    gu = await get_or_create_game_user(user_id)
    owned = await get_user_items(user_id)
    badges = await get_equipped_badges(user_id)
    return {
        "owned": sorted(owned),
        "equipped": {
            "clothing": gu["equipped_clothing"] or "",
            "frame": gu["equipped_frame"] or "",
            "effect": gu["equipped_effect"] or "",
            "nickname_color": gu["equipped_nickname_color"] or "",
            "animation": gu["equipped_animation"] or "",
            "title": gu["equipped_title"] or "",
            "badges": badges,
        },
        "streak_shields": gu["streak_shields"],
    }


async def _limited_stock_remaining(item_code: str) -> int | None:
    cur = await _db.execute("SELECT remaining FROM limited_stock WHERE item_code = ?", (item_code,))
    row = await cur.fetchone()
    return row["remaining"] if row else None


async def buy_cosmetic(user_id: int, item_code: str) -> dict:
    """Покупка предмета косметики за Purio Points."""
    item = shop.COSMETICS_BY_CODE.get(item_code)
    if not item or item.get("price") is None:
        raise shop.ShopError("Этот предмет нельзя купить напрямую")

    week = _iso_week_key()
    if not shop.is_purchasable_now(item_code, week):
        raise shop.ShopError("Этот предмет сейчас недоступен (не в ротации на этой неделе)")

    owned = await get_user_items(user_id)
    if item_code in owned:
        raise shop.ShopError("У тебя уже есть этот предмет")

    if item.get("limited"):
        remaining = await _limited_stock_remaining(item_code)
        if remaining is not None and remaining <= 0:
            raise shop.ShopError("Тираж этого предмета распродан")

    gu = await get_or_create_game_user(user_id)
    price = item["price"]
    if gu["points"] < price:
        raise shop.ShopError("Недостаточно Purio Points")

    if item.get("limited"):
        cur = await _db.execute(
            "UPDATE limited_stock SET remaining = remaining - 1 WHERE item_code = ? AND remaining > 0",
            (item_code,),
        )
        await _db.commit()
        if cur.rowcount == 0:
            raise shop.ShopError("Тираж этого предмета распродан")

    new_balance = await add_points(user_id, -price, f"shop_buy:{item_code}")
    await _grant_item(user_id, item_code, "shop")

    return {"item_code": item_code, "price": price, "new_balance": new_balance}


async def equip_cosmetic(user_id: int, item_type: str, item_code: str) -> dict:
    """Экипирует (или снимает, если item_code == '') предмет одного из
    одиночных слотов (clothing/frame/effect/nickname_color/animation/title).
    Для значков используется equip_badge (можно носить до 3 сразу)."""
    if item_type not in shop.EQUIP_SLOTS:
        raise shop.ShopError("Неизвестный тип предмета")

    if item_code:
        owned = await get_user_items(user_id)
        item = shop.COSMETICS_BY_CODE.get(item_code)
        if not item or item["type"] != item_type:
            raise shop.ShopError("Предмет не найден")
        if item_code not in owned:
            raise shop.ShopError("Этот предмет ещё не открыт")

    column = f"equipped_{item_type}"
    await _db.execute(
        f"UPDATE game_users SET {column} = ?, updated_at = ? WHERE user_id = ?",
        (item_code, _now(), user_id),
    )
    await _db.commit()
    return {"ok": True, "type": item_type, "item_code": item_code}


async def equip_badge(user_id: int, slot: int, badge_code: str) -> dict:
    """slot — 0, 1 или 2 (до BADGE_MAX_EQUIPPED значков сразу). badge_code=''
    снимает значок из слота."""
    if slot < 0 or slot >= shop.BADGE_MAX_EQUIPPED:
        raise shop.ShopError("Некорректный слот значка")

    if badge_code:
        owned = await get_user_items(user_id)
        item = shop.COSMETICS_BY_CODE.get(badge_code)
        if not item or item["type"] != "badge":
            raise shop.ShopError("Значок не найден")
        if badge_code not in owned:
            raise shop.ShopError("Этот значок ещё не открыт")
        await _db.execute(
            "INSERT INTO user_equipped_badges (user_id, slot, badge_code) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, slot) DO UPDATE SET badge_code = excluded.badge_code",
            (user_id, slot, badge_code),
        )
    else:
        await _db.execute(
            "DELETE FROM user_equipped_badges WHERE user_id = ? AND slot = ?", (user_id, slot)
        )
    await _db.commit()
    return {"ok": True, "slot": slot, "badge_code": badge_code}


async def get_shop_catalog(user_id: int) -> dict:
    """Полный каталог магазина для мини-аппы: цены, владение, ротация недели,
    остатки лимитированных предметов."""
    week = _iso_week_key()
    rotation = shop.get_weekly_rotation(week)
    owned = await get_user_items(user_id)

    items = []
    for c in shop.COSMETICS:
        if c["code"] in shop.LOOT_ONLY_CODES:
            continue  # эти показываются только как "выпадает из бокса", не продаются
        entry = {**c, "owned": c["code"] in owned}
        if c.get("achievement"):
            entry["purchasable"] = False
        elif c.get("rotating"):
            entry["purchasable"] = c["code"] in rotation
        else:
            entry["purchasable"] = True
        if c.get("limited"):
            entry["stock_remaining"] = await _limited_stock_remaining(c["code"])
        items.append(entry)

    return {
        "items": items,
        "week_key": week,
        "rotating_this_week": rotation,
    }


# ==================== ДОСТИЖЕНИЯ / ТИТУЛЫ ====================

async def sync_achievement_titles(user_id: int, level: int) -> list[str]:
    """Выдаёт титулы OG (12 ур.) и Legend (20 ур. — максимум), если игрок
    их ещё не получил. Не покупаются за очки — только достижение."""
    newly = []
    owned = await get_user_items(user_id)
    if level >= 12 and "title_og" not in owned:
        await _grant_item(user_id, "title_og", "achievement")
        newly.append("title_og")
    if level >= 20 and "title_legend" not in owned:
        await _grant_item(user_id, "title_legend", "achievement")
        newly.append("title_legend")
    return newly


async def sync_founder_title(user_id: int) -> bool:
    """Выдаёт титул Founder, если пользователь зарегистрирован до
    config.FOUNDER_CUTOFF_TS (0 = отключено)."""
    if not FOUNDER_CUTOFF_TS:
        return False
    owned = await get_user_items(user_id)
    if "title_founder" in owned:
        return False
    user = await db.get_user(user_id)
    if not user or not user["created_at"] or user["created_at"] > FOUNDER_CUTOFF_TS:
        return False
    await _grant_item(user_id, "title_founder", "achievement")
    return True


# ==================== MYSTERY BOX ====================

async def _mystery_box_opened_today(user_id: int, tier: str) -> int:
    today = _today_key()
    cur = await _db.execute(
        "SELECT opened_count FROM mystery_box_state WHERE user_id = ? AND day_key = ? AND box_code = ?",
        (user_id, today, tier),
    )
    row = await cur.fetchone()
    return row["opened_count"] if row else 0


async def open_mystery_box(user_id: int, tier: str) -> dict:
    if tier not in MYSTERY_BOX_TIERS:
        raise shop.ShopError("Неизвестный тип бокса")

    cfg = MYSTERY_BOX_TIERS[tier]
    opened_today = await _mystery_box_opened_today(user_id, tier)
    if opened_today >= cfg["daily_limit"]:
        raise shop.ShopError(f"Дневной лимит открытий этого бокса исчерпан ({cfg['daily_limit']}/день)")

    gu = await get_or_create_game_user(user_id)
    if gu["points"] < cfg["price"]:
        raise shop.ShopError("Недостаточно Purio Points")

    owned = await get_user_items(user_id)
    result = shop.roll_mystery_box(tier, owned, gu["level"])

    new_balance = await add_points(user_id, -cfg["price"], f"mystery_box_open:{tier}")

    today = _today_key()
    await _db.execute(
        "INSERT INTO mystery_box_state (user_id, day_key, box_code, opened_count) VALUES (?, ?, ?, 1) "
        "ON CONFLICT(user_id, day_key, box_code) DO UPDATE SET opened_count = opened_count + 1",
        (user_id, today, tier),
    )
    await _db.commit()

    payload = await _apply_box_reward(user_id, result)
    payload["opened_today"] = opened_today + 1
    payload["daily_limit"] = cfg["daily_limit"]
    return payload


async def claim_daily_case(user_id: int) -> dict:
    today = _today_key()
    cur = await _db.execute(
        "SELECT last_claim_day_key FROM daily_case_state WHERE user_id = ?", (user_id,)
    )
    row = await cur.fetchone()
    if row and row["last_claim_day_key"] == today:
        raise shop.ShopError("Бесплатный кейс на сегодня уже забран — приходи завтра")

    result = shop.roll_daily_case()
    await _db.execute(
        "INSERT INTO daily_case_state (user_id, last_claim_day_key) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET last_claim_day_key = excluded.last_claim_day_key",
        (user_id, today),
    )
    await _db.commit()
    return await _apply_box_reward(user_id, result)


async def _apply_box_reward(user_id: int, result: dict) -> dict:
    """Начисляет награду из Mystery Box / бесплатного кейса / колеса удачи
    (points / item / booster) и возвращает единый payload для клиента."""
    kind = result["kind"]
    if kind == "points":
        new_balance = await add_points(user_id, result["amount"], "mystery_box_reward")
        return {"kind": "points", "amount": result["amount"], "new_balance": new_balance,
                "jackpot": result.get("jackpot", False), "fallback": result.get("fallback", False)}

    if kind == "item":
        item_code = result["item_code"]
        await _grant_item(user_id, item_code, "mystery_box")
        gu = await get_or_create_game_user(user_id)
        item = shop.COSMETICS_BY_CODE.get(item_code, {})
        return {"kind": "item", "item_code": item_code, "item": item, "new_balance": gu["points"]}

    if kind == "booster":
        booster_code = result["booster_code"]
        cfg = XP_BOOSTERS[booster_code]
        await _grant_active_booster(user_id, cfg["multiplier"], cfg["duration_seconds"])
        gu = await get_or_create_game_user(user_id)
        return {"kind": "booster", "booster_code": booster_code, "new_balance": gu["points"]}

    gu = await get_or_create_game_user(user_id)
    return {"kind": kind, "new_balance": gu["points"]}


# ==================== КОЛЕСО УДАЧИ ====================

async def _wheel_free_spin_available(user_id: int) -> bool:
    if WHEEL_FREE_SPINS_PER_DAY <= 0:
        return False
    today = _today_key()
    cur = await _db.execute(
        "SELECT last_free_spin_day_key FROM wheel_state WHERE user_id = ?", (user_id,)
    )
    row = await cur.fetchone()
    return not row or row["last_free_spin_day_key"] != today


async def get_wheel_state(user_id: int) -> dict:
    return {
        "spin_cost": WHEEL_SPIN_COST,
        "free_spin_available": await _wheel_free_spin_available(user_id),
    }


async def spin_wheel(user_id: int, use_free: bool = False) -> dict:
    gu = await get_or_create_game_user(user_id)
    today = _today_key()

    if use_free:
        if not await _wheel_free_spin_available(user_id):
            raise shop.ShopError("Бесплатный спин на сегодня уже использован")
        cost = 0
    else:
        cost = WHEEL_SPIN_COST
        if gu["points"] < cost:
            raise shop.ShopError("Недостаточно Purio Points")

    # Ставка для расчёта множителя всегда WHEEL_SPIN_COST (даже для бесплатного
    # спина) — иначе бесплатный спин был бы бесполезен (0 очков * любой множитель = 0).
    result = shop.roll_wheel(WHEEL_SPIN_COST)

    if cost:
        await add_points(user_id, -cost, "wheel_spin")
    if use_free:
        await _db.execute(
            "INSERT INTO wheel_state (user_id, last_free_spin_day_key) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET last_free_spin_day_key = excluded.last_free_spin_day_key",
            (user_id, today),
        )
        await _db.commit()

    new_balance = await add_points(user_id, result["payout"], "wheel_reward")
    await record_casino_round(user_id, "wheel", cost, result["payout"], result)

    return {
        "multiplier": result["multiplier"],
        "payout": result["payout"],
        "cost": cost,
        "used_free_spin": use_free,
        "new_balance": new_balance,
    }


# ==================== БУСТЕРЫ XP ====================

async def _grant_active_booster(user_id: int, multiplier: int, duration_seconds: int):
    now = _now()
    cur = await _db.execute("SELECT * FROM user_boosters WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    base_ts = now
    new_multiplier = multiplier
    if row and row["expires_at"] > now:
        base_ts = row["expires_at"]
        new_multiplier = max(row["multiplier"], multiplier)
    new_expires = base_ts + duration_seconds
    await _db.execute(
        "INSERT INTO user_boosters (user_id, multiplier, expires_at) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET multiplier = excluded.multiplier, expires_at = excluded.expires_at",
        (user_id, new_multiplier, new_expires),
    )
    await _db.commit()


async def buy_booster(user_id: int, booster_code: str) -> dict:
    cfg = XP_BOOSTERS.get(booster_code)
    if not cfg:
        raise shop.ShopError("Неизвестный бустер")

    gu = await get_or_create_game_user(user_id)
    if gu["points"] < cfg["price"]:
        raise shop.ShopError("Недостаточно Purio Points")

    new_balance = await add_points(user_id, -cfg["price"], f"booster_buy:{booster_code}")
    await _grant_active_booster(user_id, cfg["multiplier"], cfg["duration_seconds"])
    booster = await get_active_booster(user_id)
    return {"booster": booster, "new_balance": new_balance}


async def get_active_booster(user_id: int) -> dict | None:
    cur = await _db.execute("SELECT * FROM user_boosters WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    if not row or row["expires_at"] <= _now():
        return None
    return {"multiplier": row["multiplier"], "expires_at": row["expires_at"]}


# ==================== ЗАЩИТА СТРИКА ====================

async def buy_streak_shield(user_id: int) -> dict:
    gu = await get_or_create_game_user(user_id)
    if gu["points"] < STREAK_SHIELD_PRICE:
        raise shop.ShopError("Недостаточно Purio Points")
    new_balance = await add_points(user_id, -STREAK_SHIELD_PRICE, "streak_shield_buy")
    await _db.execute(
        "UPDATE game_users SET streak_shields = streak_shields + 1, updated_at = ? WHERE user_id = ?",
        (_now(), user_id),
    )
    await _db.commit()
    gu2 = await get_or_create_game_user(user_id)
    return {"streak_shields": gu2["streak_shields"], "new_balance": new_balance}
