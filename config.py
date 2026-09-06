"""
Конфигурация бота.
Все секреты берутся из .env файла (см. .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============ TELEGRAM ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID администраторов бота (им доступна админ-панель)
ADMIN_IDS = {6243421380, 6848143236}

# Канал, подписка на который обязательна для использования бота
# Указывать с @ в начале
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@PurioVPN")
# Ссылка на канал для кнопки "Наш канал"
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/PurioVPN")

# Юзернейм бота без @ (нужен для формирования реферальных ссылок).
# Можно оставить пустым — бот сам подставит его при старте через getMe().
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# Контакт поддержки
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@PurioSupport")

# ============ REMNAWAVE ============
REMNAWAVE_BASE_URL = os.getenv("REMNAWAVE_BASE_URL", "https://panel.example.com")
REMNAWAVE_API_TOKEN = os.getenv("REMNAWAVE_API_TOKEN", "")
# UUID внутреннего сквада, в который добавлять пользователей
REMNAWAVE_SQUAD_UUID = os.getenv("REMNAWAVE_SQUAD_UUID", "")

# ============ PLATEGA (платежи) ============
PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID", "")
PLATEGA_SECRET = os.getenv("PLATEGA_SECRET", "")
# На эту страницу пользователь вернётся после оплаты (просто информационная)
PLATEGA_RETURN_URL = os.getenv("PLATEGA_RETURN_URL", "https://t.me/PurioVPN")

# Автоматически включается, как только в .env заполнены оба ключа Platega.
ENABLE_PLATEGA = bool(PLATEGA_MERCHANT_ID and PLATEGA_SECRET)

# ============ БАЛАНС / ПОПОЛНЕНИЕ ============
# Пользователь сам вводит сумму пополнения (текстом), поэтому вместо
# фиксированного списка сумм задаём только допустимые границы.
TOPUP_MIN_AMOUNT = float(os.getenv("TOPUP_MIN_AMOUNT", "50"))
TOPUP_MAX_AMOUNT = float(os.getenv("TOPUP_MAX_AMOUNT", "100000"))

# ============ ТАРИФЫ ПОДПИСКИ ============
# ключ — количество дней, значение — цена в рублях
# сделаны так, чтобы длинные периоды были выгоднее (меньше цена в пересчёте на месяц)
TARIFFS = {
    30: 129,    # 1 месяц  -> 149р/мес
    60: 239,    # 2 месяца -> 125р/мес
    180: 589,   # 6 месяцев -> ~116р/мес
    365: 1067,  # 12 месяцев -> ~107р/мес
}
TARIFF_LABELS = {
    30: "1 месяц — 129₽",
    60: "2 месяца — 239₽",
    180: "6 месяцев — 589₽",
    365: "12 месяцев — 1067₽",
}

# ============ РЕФЕРАЛЬНАЯ ПРОГРАММА ============
REFERRAL_BONUS_DAYS = 3        # дней подписки за каждого приглашённого (за первую покупку)
REFERRAL_PERCENT = 0.07        # % от суммы КАЖДОЙ покупки подписки рефералом (7%),
                                # начисляется деньгами на баланс пригласившего сразу при покупке

# ============ ПРОЧЕЕ ============
# По умолчанию файл БД лежит в подпапке data/ — она добавлена в .gitignore,
# поэтому `git pull` / обновление бота из GitHub никогда её не затронет.
DB_PATH = os.getenv("DB_PATH", "data/bot.db")

# Ссылки на политику конфиденциальности и пользовательское соглашение.
# Просто вставьте свои ссылки в .env — кнопки в разделе "Поддержка" появятся
# автоматически. Если оставить пустым, бот покажет запасной текст ниже.
PRIVACY_POLICY_URL = os.getenv("PRIVACY_POLICY_URL", "")
TERMS_OF_USE_URL = os.getenv("TERMS_OF_USE_URL", "")

PRIVACY_POLICY_TEXT = (
    "📄 <b>Политика конфиденциальности</b>\n\n"
    "Мы собираем минимально необходимые данные для работы сервиса: "
    "ваш Telegram ID, юзернейм и статистику использования бота. "
    "Данные не передаются третьим лицам и используются исключительно "
    "для предоставления VPN-услуг и работы реферальной программы.\n\n"
    "Продолжая пользоваться ботом, вы соглашаетесь с данной политикой.\n\n"
    "⚠️ Ссылка на полную версию документа ещё не добавлена администратором "
    "(PRIVACY_POLICY_URL в .env)."
)
TERMS_OF_USE_TEXT = (
    "📃 <b>Пользовательское соглашение</b>\n\n"
    "Полный текст пользовательского соглашения появится здесь, как только "
    "администратор укажет ссылку на него в .env (TERMS_OF_USE_URL).\n\n"
    "Используя бота, вы соглашаетесь с условиями предоставления услуг."
)

# ============ ТИКЕТЫ ПОДДЕРЖКИ ============
TICKETS_PAGE_SIZE = 5

# ============ ПРИЛОЖЕНИЕ HAPP (инструкция подключения) ============
# Официальный сайт Happ — там ссылки на все платформы (App Store, Google Play, Windows/macOS/Linux).
HAPP_DOWNLOAD_URL = os.getenv("HAPP_DOWNLOAD_URL", "https://happ.su")

# ============ PURIO APP (мини-приложение / Telegram WebApp) ============
# Публичный HTTPS-адрес, на котором крутится webapp/server.py (см. README в папке webapp).
# Именно этот URL нужно вставить в BotFather -> Bot Settings -> Menu Button / Web App,
# а также он используется для кнопки "🚀 Purio App" в главном меню бота.
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# Порт и хост, на которых слушает встроенный сервер мини-аппы (webapp/server.py).
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))

# DEV-режим для мини-аппы: разрешает открывать её в обычном браузере без
# настоящей Telegram initData (подставляется тестовый пользователь).
# На проде держать False.
WEBAPP_DEV_MODE = os.getenv("WEBAPP_DEV_MODE", "false").lower() == "true"

# ============ PURIO POINTS / ИГРОВАЯ ЭКОНОМИКА ============
# Сколько Purio Points начисляется за каждый полный час активной подписки VPN.
POINTS_PER_VPN_HOUR = int(os.getenv("POINTS_PER_VPN_HOUR", "2"))

# Награда за дневную серию входов (день 1..7), каждую неделю обнуляется.
DAILY_STREAK_REWARDS = [10, 15, 20, 25, 30, 40, 60]

# Комиссия казино (house edge) для игры "Кости", в долях (0.01 = 1%).
CASINO_DICE_HOUSE_EDGE = float(os.getenv("CASINO_DICE_HOUSE_EDGE", "0.01"))
