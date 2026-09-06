"""
Purio Casino — мини-игры на Purio Points.

Игры:
  * dice  — классические "кости" (roll under), как в 1win/stake: игрок
            выбирает шанс выигрыша (2-95%), множитель считается с учётом
            комиссии казино (house edge).
  * slots — трёхбарабанный слот с драконьей тематикой и фиксированной
            таблицей выплат.

Оба используют системный CSPRNG (secrets), результат всегда считается
на сервере — клиент только показывает анимацию.
"""
import secrets

from config import CASINO_DICE_HOUSE_EDGE

MIN_BET = 1
MAX_BET = 100_000

DICE_MIN_CHANCE = 2
DICE_MAX_CHANCE = 95

SLOT_SYMBOLS = ["🍀", "⭐", "🔥", "💎", "🐉", "7️⃣"]
# веса — чем реже символ, тем он ценнее (для честного, но азартного распределения)
SLOT_WEIGHTS = [30, 24, 18, 14, 10, 4]

# выплата за три одинаковых символа (множитель ставки)
SLOT_TRIPLE_PAYOUT = {
    "🍀": 2, "⭐": 3, "🔥": 5, "💎": 8, "🐉": 15, "7️⃣": 40,
}
# выплата за любые два дракона на линии (утешительный приз)
SLOT_TWO_DRAGONS_PAYOUT = 1.5


class CasinoError(Exception):
    pass


def _validate_bet(bet: int, balance: int):
    if not isinstance(bet, int) or bet < MIN_BET:
        raise CasinoError(f"Минимальная ставка — {MIN_BET} поинт")
    if bet > MAX_BET:
        raise CasinoError(f"Максимальная ставка — {MAX_BET} поинтов")
    if bet > balance:
        raise CasinoError("Недостаточно Purio Points")


def play_dice(bet: int, balance: int, win_chance: int) -> dict:
    """
    win_chance — шанс победы в процентах (2..95), выбирает игрок.
    Чем ниже шанс — тем выше множитель.
    """
    _validate_bet(bet, balance)
    win_chance = max(DICE_MIN_CHANCE, min(DICE_MAX_CHANCE, int(win_chance)))

    multiplier = round((100 - CASINO_DICE_HOUSE_EDGE * 100) / win_chance, 4)
    roll = secrets.randbelow(10000) / 100  # 0.00 .. 99.99
    won = roll < win_chance

    payout = int(round(bet * multiplier)) if won else 0
    net = payout - bet

    return {
        "roll": round(roll, 2),
        "win_chance": win_chance,
        "multiplier": multiplier,
        "won": won,
        "bet": bet,
        "payout": payout,
        "net": net,
    }


def play_slots(bet: int, balance: int) -> dict:
    _validate_bet(bet, balance)

    reels = [secrets.choice(
        [s for s, w in zip(SLOT_SYMBOLS, SLOT_WEIGHTS) for _ in range(w)]
    ) for _ in range(3)]

    payout = 0
    win_label = None
    if reels[0] == reels[1] == reels[2]:
        mult = SLOT_TRIPLE_PAYOUT[reels[0]]
        payout = int(round(bet * mult))
        win_label = f"Три {reels[0]}! x{mult}"
    elif reels.count("🐉") >= 2:
        payout = int(round(bet * SLOT_TWO_DRAGONS_PAYOUT))
        win_label = f"Два дракона! x{SLOT_TWO_DRAGONS_PAYOUT}"

    net = payout - bet
    return {
        "reels": reels,
        "won": payout > 0,
        "win_label": win_label,
        "bet": bet,
        "payout": payout,
        "net": net,
    }
