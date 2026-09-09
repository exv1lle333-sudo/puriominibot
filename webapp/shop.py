"""
Purio Shop — косметика, Mystery Box, Колесо удачи, бустеры, титулы.

Экономическая логика (см. подробный комментарий в config.py, раздел
"PURIO SHOP / КОСМЕТИКА / ГЕЙМИФИКАЦИЯ 2.0"):
  * Косметика ничего не стоит нам в рублях -> она "поинт-синк": чем больше
    игроки тратят на неё Purio Points, тем меньше они выводят через обмен
    очков на рубли. Цены невысокие и достижимые за 1-3 дня активности.
  * Mystery Box и Колесо удачи всегда имеют отрицательный матожидание в
    очках (house edge) — как и остальные игры Purio Casino.
  * Бесплатные раздачи (ежедневный кейс, 1 бесплатный спин колеса в день)
    по ценности сопоставимы с наградой за серию входов.
  * XP-бустеры ускоряют ТОЛЬКО прокачку уровня дракона, а не заработок
    Purio Points — поэтому не увеличивают количество очков в обороте.

Этот модуль — чистые данные и чистые функции (бросок кубика/колеса,
выбор награды). Все обращения к БД — в webapp/gamedb.py.
"""
import hashlib
import random
import secrets

from config import (
    MYSTERY_BOX_TIERS, MYSTERY_BOX_HOUSE_EDGE,
    WHEEL_SPIN_COST, WHEEL_HOUSE_EDGE, WHEEL_FREE_SPINS_PER_DAY,
    DAILY_CASE_MIN_REWARD, DAILY_CASE_MAX_REWARD,
    STREAK_SHIELD_PRICE, XP_BOOSTERS, WEEKLY_SHOP_SIZE,
)

# ==================== КАТАЛОГ КОСМЕТИКИ ====================
# type:   clothing / frame / effect / nickname_color / badge / animation / title
# rarity: common / rare / epic / legendary
# price:  цена в Purio Points, None = не продаётся напрямую (достижение или
#         только из Mystery Box / Колеса удачи)
# limited: True -> ограниченный тираж, см. LIMITED_STOCK ниже
# rotating: True -> доступен для покупки только в те недели, когда попадает
#           в еженедельную ротацию (см. get_weekly_rotation)

COSMETICS = [
    # ---------- ОДЕЖДА / АКСЕССУАРЫ ДРАКОНА ----------
    dict(code="cloth_scarf_red", type="clothing", rarity="common",
         name="Красный шарфик", icon="🧣", desc="Классика — маленький дракон в шарфике.",
         price=1800),
    dict(code="cloth_glasses", type="clothing", rarity="common",
         name="Крутые очки", icon="🕶️", desc="Для дракона со вкусом.", price=2600),
    dict(code="cloth_pilot_cap", type="clothing", rarity="common",
         name="Кепка пилота", icon="🧢", desc="Готов покорять облака.", price=3200),
    dict(code="cloth_cape_hero", type="clothing", rarity="rare",
         name="Плащ героя", icon="🦸", desc="Плащ настоящего защитника сети.", price=9000),
    dict(code="cloth_crown_mini", type="clothing", rarity="rare",
         name="Мини-корона", icon="👑", desc="Маленькая корона для маленького короля.", price=12000),
    dict(code="cloth_armor_gold", type="clothing", rarity="epic",
         name="Золотая броня", icon="🛡️", desc="Броня, выкованная из чистого золота.", price=32000),
    dict(code="cloth_wings_ice", type="clothing", rarity="legendary",
         name="Ледяные крылья", icon="❄️", desc="Ограниченная серия — растают, если не успеть.",
         price=45000, limited=True, stock=300),

    # ---------- РАМКИ АВАТАРА ----------
    dict(code="frame_gold", type="frame", rarity="common",
         name="Золотая рамка", icon="🖼️", desc="Простая, но благородная.", price=4000),
    dict(code="frame_neon", type="frame", rarity="common",
         name="Неоновая рамка", icon="🟣", desc="Светится в тёмной теме приложения.", price=7500),
    dict(code="frame_fire", type="frame", rarity="rare",
         name="Огненная рамка", icon="🔥", desc="Пылает вокруг твоего аватара.", price=14000),
    dict(code="frame_galaxy", type="frame", rarity="epic",
         name="Галактическая рамка", icon="🌌", desc="Кусочек космоса вокруг профиля.", price=26000),
    dict(code="frame_royal", type="frame", rarity="legendary",
         name="Королевская рамка", icon="👑", desc="Ограниченный тираж — всего 200 штук.",
         price=60000, limited=True, stock=200),
    dict(code="frame_retro", type="frame", rarity="rare",
         name="Ретро-рамка", icon="📼", desc="Эксклюзив недели — доступен только в ротации.",
         price=10000, rotating=True),

    # ---------- ЭФФЕКТЫ ПРОФИЛЯ ----------
    dict(code="fx_sparkles", type="effect", rarity="common",
         name="Искры", icon="✨", desc="Лёгкое мерцание вокруг профиля.", price=5000),
    dict(code="fx_snow", type="effect", rarity="common",
         name="Снегопад", icon="❄️", desc="Тихий снег на фоне профиля.", price=8000),
    dict(code="fx_flames", type="effect", rarity="rare",
         name="Пламя", icon="🔥", desc="Профиль в языках пламени.", price=16000),
    dict(code="fx_aurora", type="effect", rarity="epic",
         name="Северное сияние", icon="🌈", desc="Переливающееся сияние по краям профиля.",
         price=30000),
    dict(code="fx_matrix", type="effect", rarity="epic",
         name="Матрица", icon="🟩", desc="Эксклюзив недели — доступен только в ротации.",
         price=20000, rotating=True),
    dict(code="fx_hearts", type="effect", rarity="rare",
         name="Сердечки", icon="💞", desc="Эксклюзив недели — доступен только в ротации.",
         price=11000, rotating=True),

    # ---------- ЦВЕТНЫЕ НИКНЕЙМЫ ----------
    dict(code="nick_violet", type="nickname_color", rarity="common",
         name="Фиолетовый ник", icon="🟣", desc="Фирменный цвет Purio.", price=3000),
    dict(code="nick_gold", type="nickname_color", rarity="rare",
         name="Золотой ник", icon="🟡", desc="Ник цвета золота.", price=6000),
    dict(code="nick_crimson", type="nickname_color", rarity="rare",
         name="Багровый ник", icon="🔴", desc="Для тех, кто любит выделяться.", price=6000),
    dict(code="nick_cyan", type="nickname_color", rarity="rare",
         name="Бирюзовый ник", icon="🔵", desc="Свежий и холодный оттенок.", price=6000),
    dict(code="nick_rainbow", type="nickname_color", rarity="epic",
         name="Радужный ник", icon="🌈", desc="Переливается всеми цветами.", price=22000),
    dict(code="nick_ocean", type="nickname_color", rarity="rare",
         name="Океанский ник", icon="🌊", desc="Эксклюзив недели — доступен только в ротации.",
         price=8000, rotating=True),
    dict(code="nick_sunset", type="nickname_color", rarity="rare",
         name="Закатный ник", icon="🌅", desc="Эксклюзив недели — доступен только в ротации.",
         price=8000, rotating=True),

    # ---------- ЗНАЧКИ / БЕЙДЖИ (можно носить до 3 одновременно) ----------
    dict(code="badge_early_bird", type="badge", rarity="common",
         name="Ранняя пташка", icon="🐦", desc="Заходишь в приложение по утрам.", price=2000),
    dict(code="badge_night_owl", type="badge", rarity="common",
         name="Ночная сова", icon="🦉", desc="Активен по ночам.", price=2000),
    dict(code="badge_gambler", type="badge", rarity="rare",
         name="Азартный игрок", icon="🎲", desc="Любит Purio Casino.", price=5000),
    dict(code="badge_grinder", type="badge", rarity="rare",
         name="Трудяга", icon="⚙️", desc="Фармит очки каждый день.", price=5000),
    dict(code="badge_whale", type="badge", rarity="epic",
         name="Кит", icon="🐋", desc="Статусный значок для больших транжир.", price=40000),
    dict(code="badge_lucky", type="badge", rarity="epic",
         name="Счастливчик", icon="🍀", desc="Выпадает только из Mystery Box или Колеса удачи.",
         price=None),
    dict(code="badge_comet", type="badge", rarity="rare",
         name="Комета", icon="☄️", desc="Эксклюзив недели — доступен только в ротации.",
         price=6000, rotating=True),

    # ---------- АНИМАЦИЯ ПРОФИЛЯ ----------
    dict(code="anim_pulse", type="animation", rarity="common",
         name="Пульсация", icon="💓", desc="Профиль мягко пульсирует.", price=9000),
    dict(code="anim_shake", type="animation", rarity="rare",
         name="Тряска дракона", icon="🌀", desc="Дракон подрагивает от нетерпения.", price=12000),
    dict(code="anim_glow", type="animation", rarity="rare",
         name="Свечение", icon="💡", desc="Мягкое пульсирующее свечение.", price=14000),
    dict(code="anim_fireworks", type="animation", rarity="epic",
         name="Фейерверк", icon="🎆", desc="Эксклюзив недели — доступен только в ротации.",
         price=25000, rotating=True),
    dict(code="anim_confetti", type="animation", rarity="rare",
         name="Конфетти", icon="🎊", desc="Эксклюзив недели — доступен только в ротации.",
         price=9000, rotating=True),

    # ---------- ТИТУЛЫ ----------
    dict(code="title_newbie", type="title", rarity="common",
         name="Новичок Purio", icon="🌱", desc="Стартовый флекс для новеньких.", price=1500),
    dict(code="title_grinder", type="title", rarity="rare",
         name="Трудяга", icon="⚙️", desc="За тех, кто фармит каждый день.", price=8000),
    dict(code="title_high_roller", type="title", rarity="epic",
         name="Хайроллер", icon="🎰", desc="Для смелых ставок в Purio Casino.", price=15000),
    dict(code="title_vip", type="title", rarity="epic",
         name="VIP", icon="💎", desc="Статус для настоящих ценителей Purio.", price=30000),
    dict(code="title_founder", type="title", rarity="legendary",
         name="Founder", icon="🏛️", desc="Выдаётся автоматически первым пользователям бота.",
         price=None, achievement="founder"),
    dict(code="title_og", type="title", rarity="legendary",
         name="OG", icon="🦴", desc="Достигни 12 уровня дракона, чтобы получить титул.",
         price=None, achievement="og"),
    dict(code="title_legend", type="title", rarity="legendary",
         name="Legend", icon="🏆", desc="Достигни максимального 20 уровня дракона.",
         price=None, achievement="legend"),
]

COSMETICS_BY_CODE = {c["code"]: c for c in COSMETICS}
COSMETICS_BY_TYPE: dict[str, list[dict]] = {}
for _c in COSMETICS:
    COSMETICS_BY_TYPE.setdefault(_c["type"], []).append(_c)

# Типы, которые можно "надеть" — по одному предмету на слот (кроме badge).
EQUIP_SLOTS = ["clothing", "frame", "effect", "nickname_color", "animation", "title"]
BADGE_MAX_EQUIPPED = 3

# Предметы, покупаемые только из Mystery Box / Колеса удачи (price=None и
# не achievement) — они не показываются в обычном разделе "Купить".
LOOT_ONLY_CODES = {c["code"] for c in COSMETICS if c.get("price") is None and not c.get("achievement")}

# Предметы с ограниченным тиражом (глобальный стоклимит на всех игроков).
LIMITED_ITEMS = {c["code"]: c["stock"] for c in COSMETICS if c.get("limited")}

# Предметы, доступные только во время еженедельной ротации.
ROTATING_CODES = [c["code"] for c in COSMETICS if c.get("rotating")]

ACHIEVEMENT_TITLES = {c["achievement"]: c["code"] for c in COSMETICS if c.get("achievement")}


def get_weekly_rotation(week_key: str) -> list[str]:
    """Детерминированно выбирает, какие ротационные позиции доступны на
    этой неделе — одинаково для всех пользователей, меняется каждую
    ISO-неделю. Если ротационных позиций меньше лимита — отдаём все."""
    if not ROTATING_CODES:
        return []
    seed = int(hashlib.sha256(week_key.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    pool = sorted(ROTATING_CODES)  # стабильный порядок перед сэмплированием
    rng.shuffle(pool)
    return pool[:WEEKLY_SHOP_SIZE]


def is_purchasable_now(code: str, week_key: str) -> bool:
    item = COSMETICS_BY_CODE.get(code)
    if not item or item.get("price") is None:
        return False
    if item.get("rotating"):
        return code in get_weekly_rotation(week_key)
    return True


# ==================== MYSTERY BOX ====================

class ShopError(Exception):
    pass


def _pick_weighted(options: list[tuple[str, float]]) -> str:
    """Взвешенный случайный выбор на CSPRNG (secrets), без внешних зависимостей."""
    total = sum(w for _, w in options)
    r = (secrets.randbelow(10_000_000) / 10_000_000) * total
    upto = 0.0
    for key, w in options:
        upto += w
        if r <= upto:
            return key
    return options[-1][0]


def _random_cosmetic(rarity: str, owned: set[str], exclude_types: set[str] | None = None) -> dict | None:
    """Случайный ещё не открытый предмет заданной редкости (не achievement,
    не loot-only повторно вручную, но badge_lucky и т.п. МОГУТ выпасть)."""
    candidates = [
        c for c in COSMETICS
        if c["rarity"] == rarity and c["code"] not in owned and not c.get("achievement")
        and (not exclude_types or c["type"] not in exclude_types)
    ]
    if not candidates:
        return None
    return secrets.choice(candidates)


def roll_mystery_box(tier: str, owned: set[str], level: int) -> dict:
    """Разыгрывает содержимое Mystery Box. Возвращает
    {"kind": "points"|"item"|"booster", ...}."""
    if tier not in MYSTERY_BOX_TIERS:
        raise ShopError("Неизвестный тип бокса")

    price = MYSTERY_BOX_TIERS[tier]["price"]

    if tier == "common":
        table = [
            ("points_small", 60), ("common_item", 25),
            ("rare_item", 10), ("booster", 4), ("epic_item", 1),
        ]
        points_range = (int(price * 0.2), int(price * 0.45))
    elif tier == "rare":
        table = [
            ("points_small", 45), ("rare_item", 30),
            ("epic_item", 15), ("booster", 8), ("legendary_item", 2),
        ]
        points_range = (int(price * 0.2), int(price * 0.45))
    else:  # epic
        table = [
            ("points_small", 35), ("epic_item", 30),
            ("rare_item", 20), ("legendary_item", 10), ("jackpot", 5),
        ]
        points_range = (int(price * 0.2), int(price * 0.45))

    outcome = _pick_weighted(table)

    if outcome == "points_small":
        lo, hi = points_range
        amount = lo + secrets.randbelow(max(hi - lo, 1))
        return {"kind": "points", "amount": amount}

    if outcome == "jackpot":
        amount = int(price * 2.4)
        return {"kind": "points", "amount": amount, "jackpot": True}

    if outcome == "booster":
        code = secrets.choice(list(XP_BOOSTERS.keys()))
        return {"kind": "booster", "booster_code": code}

    rarity_map = {"common_item": "common", "rare_item": "rare",
                  "epic_item": "epic", "legendary_item": "legendary"}
    rarity = rarity_map[outcome]
    item = _random_cosmetic(rarity, owned)
    if item is None:
        # всё уже открыто на этой редкости (или пул пуст) — компенсируем очками
        lo, hi = points_range
        amount = lo + secrets.randbelow(max(hi - lo, 1))
        return {"kind": "points", "amount": amount, "fallback": True}
    return {"kind": "item", "item_code": item["code"]}


def roll_daily_case() -> dict:
    """Бесплатный ежедневный кейс — небольшая гарантированная награда очками,
    сопоставимая по ценности с наградой за день серии входов."""
    amount = DAILY_CASE_MIN_REWARD + secrets.randbelow(DAILY_CASE_MAX_REWARD - DAILY_CASE_MIN_REWARD + 1)
    return {"kind": "points", "amount": amount}


# ==================== КОЛЕСО УДАЧИ ====================

# (множитель ставки, вес). Матожидание ≈ 0.835 -> house edge ≈ 16.5%,
# что примерно соответствует WHEEL_HOUSE_EDGE и сопоставимо с house edge
# остальных игр Purio Casino.
WHEEL_SEGMENTS = [
    (0.0, 68), (0.5, 48), (1.0, 36), (1.5, 24),
    (2.0, 14), (3.0, 6), (5.0, 3), (10.0, 1),
]


def roll_wheel(bet: int) -> dict:
    total_weight = sum(w for _, w in WHEEL_SEGMENTS)
    r = secrets.randbelow(total_weight)
    upto = 0
    chosen_mult = WHEEL_SEGMENTS[-1][0]
    for mult, w in WHEEL_SEGMENTS:
        upto += w
        if r < upto:
            chosen_mult = mult
            break
    payout = int(round(bet * chosen_mult))
    return {
        "multiplier": chosen_mult,
        "bet": bet,
        "payout": payout,
        "net": payout - bet,
        "won": chosen_mult > 1.0,
    }


__all__ = [
    "COSMETICS", "COSMETICS_BY_CODE", "COSMETICS_BY_TYPE", "EQUIP_SLOTS",
    "BADGE_MAX_EQUIPPED", "LOOT_ONLY_CODES", "LIMITED_ITEMS", "ROTATING_CODES",
    "ACHIEVEMENT_TITLES", "ShopError", "get_weekly_rotation", "is_purchasable_now",
    "roll_mystery_box", "roll_daily_case", "roll_wheel", "WHEEL_SEGMENTS",
]
