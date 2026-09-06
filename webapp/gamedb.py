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

from config import DB_PATH, DAILY_STREAK_REWARDS

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
         price=0, min_level=1, coming_soon=0),
    dict(code="shadow", name="Теневой дракон", desc="Скоро появится в Purio Shop.",
         price=500, min_level=5, coming_soon=1),
    dict(code="golden", name="Золотой дракон", desc="Скоро появится в Purio Shop.",
         price=1500, min_level=10, coming_soon=1),
    dict(code="storm", name="Штормовой дракон", desc="Скоро появится в Purio Shop.",
         price=3000, min_level=15, coming_soon=1),
]


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
    """Начисляет XP дракону, пересчитывает уровень. Возвращает (level, xp_в_текущем_уровне, level_up?)."""
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
    return level, xp, leveled_up


async def set_equipped_skin(user_id: int, skin_code: str):
    await _db.execute("UPDATE game_users SET equipped_skin = ?, updated_at = ? WHERE user_id = ?",
                       (skin_code, _now(), user_id))
    await _db.commit()


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
    if row["week_key"] != week:
        # новая неделя — серия обнуляется, начинаем с дня 0 (награда за 1-й день)
        new_day_index = 0
    elif row["last_streak_day_key"] == yesterday:
        # заходил вчера — продолжаем серию (максимум 7 дней в таблице наград)
        new_day_index = min(row["streak_day"] + 1, len(DAILY_STREAK_REWARDS) - 1)
    else:
        # пропустил день(и) на этой же неделе — серия начинается заново
        new_day_index = 0

    reward = DAILY_STREAK_REWARDS[new_day_index]

    await _db.execute(
        "UPDATE game_users SET streak_day = ?, last_streak_day_key = ?, last_seen_day_key = ?, "
        "week_key = ?, updated_at = ? WHERE user_id = ?",
        (new_day_index, today, today, week, _now(), user_id),
    )
    await _db.commit()

    await add_points(user_id, reward, "daily_streak")
    await add_xp(user_id, max(reward // 2, 3))
    await bump_task_progress(user_id, "open_app", amount=1)

    return {"day_index": new_day_index, "reward": reward, "is_new_day": True, "week_key": week}


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
