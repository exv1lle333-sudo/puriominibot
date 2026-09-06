"""
PurioApp — мини-приложение (Telegram WebApp) для PurioBot.

Отдельный aiohttp-сервис, который работает НАД той же SQLite базой, что и
основной бот (data/bot.db). Ничего в логике самого бота (bot.py, handlers/*)
не ломает — только добавляет новые таблицы для геймификации.

Запуск:  python -m webapp.server
"""
