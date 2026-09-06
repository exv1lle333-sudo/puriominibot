"""
Админ-панель PurioApp: веб-страница с логином на /admin для управления
пользователями мини-аппа — поиск по ID, просмотр статистики (дракон, XP,
Purio Points, серия входов, задания дня, история казино, история начислений
очков, подписка, рефералы), ручная выдача/списание Purio Points.

Пароль берётся из переменной окружения ADMIN_PANEL_PASSWORD (.env).
Сессии — простые токены в памяти процесса (сбрасываются при рестарте сервиса).
"""
import os
import secrets
import time
import logging
from functools import wraps

from aiohttp import web

import database as db
from webapp import gamedb

logger = logging.getLogger(__name__)

ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "")

# token -> время создания (простая in-memory сессия, живёт пока жив процесс)
_sessions: dict[str, float] = {}
SESSION_TTL = 60 * 60 * 12  # 12 часов


def _check_session(request: web.Request) -> bool:
    token = request.headers.get("X-Admin-Token", "")
    if not token or token not in _sessions:
        return False
    if time.time() - _sessions[token] > SESSION_TTL:
        _sessions.pop(token, None)
        return False
    return True


def _require_auth(handler):
    @wraps(handler)
    async def wrapper(request: web.Request):
        if not _check_session(request):
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        return await handler(request)
    return wrapper


def _row_to_dict(row):
    return dict(row) if row is not None else None


# ---------------- HTML СТРАНИЦА ----------------

ADMIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Purio Admin</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    background: #0f1117; color: #e6e8ee; min-height: 100vh;
  }
  .wrap { max-width: 980px; margin: 0 auto; padding: 24px 16px 60px; }
  h1 { font-size: 20px; margin: 0 0 20px; }
  .card {
    background: #171a23; border: 1px solid #262a36; border-radius: 12px;
    padding: 20px; margin-bottom: 16px;
  }
  input, button {
    font-size: 15px; border-radius: 8px; border: 1px solid #2c3140;
    background: #1d212c; color: #e6e8ee; padding: 10px 12px;
  }
  input { width: 100%; }
  button {
    cursor: pointer; background: #3a6df0; border-color: #3a6df0; color: #fff;
    font-weight: 600;
  }
  button:hover { background: #2f5bd0; }
  button.secondary { background: #262a36; border-color: #2c3140; }
  button.danger { background: #d0463a; border-color: #d0463a; }
  .row { display: flex; gap: 8px; align-items: center; }
  .login-box { max-width: 340px; margin: 80px auto; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #262a36; }
  th { color: #9aa1b2; font-weight: 500; }
  tr.user-row { cursor: pointer; }
  tr.user-row:hover { background: #1d212c; }
  .muted { color: #9aa1b2; font-size: 13px; }
  .error { color: #ff7a70; font-size: 14px; margin-top: 8px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .stat { background: #1d212c; border-radius: 8px; padding: 10px 12px; }
  .stat .label { color: #9aa1b2; font-size: 12px; }
  .stat .value { font-size: 18px; font-weight: 700; margin-top: 2px; }
  .back { margin-bottom: 12px; }
  .hidden { display: none !important; }
  .pager { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
  .badge.on { background: #1d3a2a; color: #6fe0a0; }
  .badge.off { background: #3a1d1d; color: #e08c8c; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🐉 Purio Admin</h1>

  <div id="login-view" class="login-box card">
    <div class="row" style="flex-direction:column; align-items:stretch; gap:12px;">
      <input id="login-password" type="password" placeholder="Пароль администратора">
      <button id="login-btn">Войти</button>
      <div id="login-error" class="error hidden"></div>
    </div>
  </div>

  <div id="main-view" class="hidden">
    <div class="card">
      <div class="row">
        <input id="search-input" placeholder="Поиск по Telegram ID пользователя...">
        <button id="search-btn">Найти</button>
        <button id="reset-btn" class="secondary">Сброс</button>
      </div>
    </div>

    <div id="list-view" class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Юзернейм</th><th>Имя</th><th>Баланс</th><th>Подписка до</th><th>Регистрация</th>
          </tr>
        </thead>
        <tbody id="users-tbody"></tbody>
      </table>
      <div class="pager">
        <span id="total-label" class="muted"></span>
        <div class="row">
          <button id="prev-btn" class="secondary">← Назад</button>
          <button id="next-btn" class="secondary">Вперёд →</button>
        </div>
      </div>
    </div>

    <div id="detail-view" class="hidden">
      <button class="secondary back" id="back-btn">← К списку</button>
      <div class="card" id="detail-content"></div>
    </div>
  </div>
</div>

<script>
let token = null;
let offset = 0;
const LIMIT = 20;
let currentSearch = "";

const $ = (id) => document.getElementById(id);

async function api(path, opts) {
  opts = opts || {};
  opts.headers = Object.assign({}, opts.headers, {
    "Content-Type": "application/json",
    "X-Admin-Token": token || "",
  });
  const res = await fetch(path, opts);
  const data = await res.json();
  if (res.status === 401) {
    token = null;
    showLogin();
    throw new Error("unauthorized");
  }
  return data;
}

function showLogin() {
  $("login-view").classList.remove("hidden");
  $("main-view").classList.add("hidden");
}

function showMain() {
  $("login-view").classList.add("hidden");
  $("main-view").classList.remove("hidden");
}

$("login-btn").onclick = async () => {
  const password = $("login-password").value;
  $("login-error").classList.add("hidden");
  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (!data.ok) {
      $("login-error").textContent = data.error || "Ошибка входа";
      $("login-error").classList.remove("hidden");
      return;
    }
    token = data.token;
    showMain();
    loadUsers();
  } catch (e) {
    $("login-error").textContent = "Ошибка соединения";
    $("login-error").classList.remove("hidden");
  }
};

$("login-password").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("login-btn").click();
});

function fmtTs(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString("ru-RU") + " " + d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

async function loadUsers() {
  const params = new URLSearchParams({ limit: LIMIT, offset: offset, search: currentSearch });
  const data = await api("/api/admin/users?" + params.toString());
  if (!data.ok) return;
  const tbody = $("users-tbody");
  tbody.innerHTML = "";
  data.users.forEach((u) => {
    const tr = document.createElement("tr");
    tr.className = "user-row";
    tr.innerHTML = `
      <td>${u.user_id}</td>
      <td>${u.username ? "@" + u.username : "—"}</td>
      <td>${u.full_name || "—"}</td>
      <td>${(u.balance || 0).toFixed(0)}₽</td>
      <td>${fmtTs(u.subscription_expire)}</td>
      <td class="muted">${fmtTs(u.created_at)}</td>
    `;
    tr.onclick = () => openUser(u.user_id);
    tbody.appendChild(tr);
  });
  $("total-label").textContent = `Всего: ${data.total}`;
  $("prev-btn").disabled = offset === 0;
  $("next-btn").disabled = offset + LIMIT >= data.total;
}

$("search-btn").onclick = () => {
  currentSearch = $("search-input").value.trim();
  offset = 0;
  loadUsers();
};
$("search-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("search-btn").click();
});
$("reset-btn").onclick = () => {
  currentSearch = "";
  $("search-input").value = "";
  offset = 0;
  loadUsers();
};
$("prev-btn").onclick = () => { offset = Math.max(0, offset - LIMIT); loadUsers(); };
$("next-btn").onclick = () => { offset += LIMIT; loadUsers(); };

$("back-btn").onclick = () => {
  $("detail-view").classList.add("hidden");
  $("list-view").parentElement.classList.remove("hidden");
  $("list-view").classList.remove("hidden");
  document.querySelector(".card").classList.remove("hidden");
};

async function openUser(userId) {
  const data = await api("/api/admin/user/" + userId);
  if (!data.ok) {
    alert(data.error || "Ошибка загрузки пользователя");
    return;
  }
  $("list-view").classList.add("hidden");
  $("detail-view").classList.remove("hidden");
  renderDetail(data);
}

function renderDetail(data) {
  const u = data.user;
  const g = data.game || {};
  const sub = data.subscription;
  const subActive = u.subscription_expire && u.subscription_expire > Date.now() / 1000;

  const tasksHtml = (data.tasks || []).map(t => `
    <div class="row" style="justify-content:space-between; padding:6px 0; border-bottom:1px solid #262a36;">
      <span>${t.icon || ""} ${t.title}</span>
      <span class="muted">${t.progress}/${t.target} ${t.claimed ? "✅ забрано" : (t.completed ? "🟡 выполнено" : "")}</span>
    </div>
  `).join("") || '<div class="muted">Нет данных за сегодня</div>';

  const casinoHtml = (data.casino_history || []).slice(0, 10).map(c => `
    <tr><td>${c.game}</td><td>${c.bet}</td><td>${c.payout >= 0 ? "+" : ""}${c.payout}</td><td class="muted">${fmtTs(c.created_at)}</td></tr>
  `).join("") || '<tr><td class="muted" colspan="4">Нет истории</td></tr>';

  const pointsHtml = (data.points_history || []).slice(0, 15).map(p => `
    <tr><td>${p.delta >= 0 ? "+" : ""}${p.delta}</td><td>${p.reason}</td><td class="muted">${fmtTs(p.created_at)}</td></tr>
  `).join("") || '<tr><td class="muted" colspan="3">Нет истории</td></tr>';

  const referralsHtml = (data.referrals || []).map(r => `
    <tr><td>${r.user_id}</td><td>${r.username ? "@" + r.username : "—"}</td><td class="muted">${fmtTs(r.created_at)}</td></tr>
  `).join("") || '<tr><td class="muted" colspan="3">Нет рефералов</td></tr>';

  $("detail-content").innerHTML = `
    <h2 style="margin-top:0;">${u.full_name || "Без имени"} <span class="muted">#${u.user_id}</span></h2>
    <p class="muted">${u.username ? "@" + u.username : "нет юзернейма"} · регистрация ${fmtTs(u.created_at)}</p>

    <div class="grid2">
      <div class="stat"><div class="label">Баланс</div><div class="value">${(u.balance || 0).toFixed(0)}₽</div></div>
      <div class="stat"><div class="label">Purio Points</div><div class="value">${g.points ?? 0}</div></div>
      <div class="stat"><div class="label">Уровень дракона</div><div class="value">${g.level ?? 1} (XP ${g.xp ?? 0})</div></div>
      <div class="stat"><div class="label">Серия входов</div><div class="value">${g.streak_day ?? 0} дн.</div></div>
      <div class="stat"><div class="label">Подписка</div><div class="value"><span class="badge ${subActive ? 'on' : 'off'}">${subActive ? "активна" : "неактивна"}</span></div></div>
      <div class="stat"><div class="label">Действует до</div><div class="value">${fmtTs(u.subscription_expire)}</div></div>
      <div class="stat"><div class="label">Рефералов всего</div><div class="value">${u.referral_count ?? 0}</div></div>
      <div class="stat"><div class="label">Заработано с рефералки</div><div class="value">${(u.referral_earned || 0).toFixed(0)}₽</div></div>
    </div>

    <h3>Ручное начисление / списание Purio Points</h3>
    <div class="row">
      <input id="points-delta" type="number" placeholder="Например: 100 или -50" style="max-width:200px;">
      <input id="points-reason" placeholder="Причина (необязательно)" style="max-width:260px;">
      <button id="points-submit">Применить</button>
    </div>
    <div id="points-result" class="muted" style="margin-top:8px;"></div>

    <h3>Задания на сегодня</h3>
    ${tasksHtml}

    <h3>История казино (последние 10)</h3>
    <table>
      <thead><tr><th>Игра</th><th>Ставка</th><th>Итог</th><th>Когда</th></tr></thead>
      <tbody>${casinoHtml}</tbody>
    </table>

    <h3>История начислений очков (последние 15)</h3>
    <table>
      <thead><tr><th>Изменение</th><th>Причина</th><th>Когда</th></tr></thead>
      <tbody>${pointsHtml}</tbody>
    </table>

    <h3>Рефералы</h3>
    <table>
      <thead><tr><th>ID</th><th>Юзернейм</th><th>Дата</th></tr></thead>
      <tbody>${referralsHtml}</tbody>
    </table>
  `;

  document.getElementById("points-submit").onclick = async () => {
    const delta = parseInt(document.getElementById("points-delta").value, 10);
    const reason = document.getElementById("points-reason").value.trim() || "admin_manual";
    const resultEl = document.getElementById("points-result");
    if (!delta) {
      resultEl.textContent = "Введите ненулевое число";
      return;
    }
    const res = await api("/api/admin/points/adjust", {
      method: "POST",
      body: JSON.stringify({ user_id: u.user_id, delta, reason }),
    });
    if (res.ok) {
      resultEl.textContent = `Готово. Новый баланс очков: ${res.new_balance}`;
      openUser(u.user_id);
    } else {
      resultEl.textContent = res.error || "Ошибка";
    }
  };
}
</script>
</body>
</html>
"""


async def admin_page(request: web.Request):
    return web.Response(text=ADMIN_HTML, content_type="text/html")


async def api_admin_login(request: web.Request):
    if not ADMIN_PANEL_PASSWORD:
        return web.json_response(
            {"ok": False, "error": "ADMIN_PANEL_PASSWORD не задан на сервере (проверь .env)"},
            status=500,
        )
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Некорректный запрос"}, status=400)

    password = body.get("password", "")
    if password != ADMIN_PANEL_PASSWORD:
        return web.json_response({"ok": False, "error": "Неверный пароль"}, status=403)

    token = secrets.token_hex(32)
    _sessions[token] = time.time()
    return web.json_response({"ok": True, "token": token})


@_require_auth
async def api_admin_users(request: web.Request):
    search = request.query.get("search", "").strip()
    try:
        limit = int(request.query.get("limit", 20))
        offset = int(request.query.get("offset", 0))
    except ValueError:
        limit, offset = 20, 0

    if search:
        try:
            user_id = int(search)
        except ValueError:
            return web.json_response({"ok": True, "total": 0, "users": []})
        user = await db.get_user(user_id)
        users = [user] if user else []
        total = len(users)
    else:
        users = await db.list_users(limit=limit, offset=offset)
        total = await db.count_all_users()

    return web.json_response({
        "ok": True,
        "total": total,
        "users": [_row_to_dict(u) for u in users],
    })


@_require_auth
async def api_admin_user_detail(request: web.Request):
    try:
        user_id = int(request.match_info["user_id"])
    except ValueError:
        return web.json_response({"ok": False, "error": "Некорректный ID"}, status=400)

    user = await db.get_user(user_id)
    if not user:
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)

    subscription = await db.get_subscription(user_id)
    referrals = await db.get_referrals(user_id)
    game_user = await gamedb.get_or_create_game_user(user_id)
    tasks = await gamedb.get_today_tasks(user_id)
    casino_history = await gamedb.get_casino_history(user_id, limit=20)
    points_history = await gamedb.get_points_history(user_id, limit=30)

    return web.json_response({
        "ok": True,
        "user": _row_to_dict(user),
        "subscription": _row_to_dict(subscription),
        "referrals": [_row_to_dict(r) for r in referrals],
        "game": _row_to_dict(game_user),
        "tasks": tasks,
        "casino_history": [dict(c) if not isinstance(c, dict) else c for c in casino_history],
        "points_history": [_row_to_dict(p) for p in points_history],
    })


@_require_auth
async def api_admin_points_adjust(request: web.Request):
    try:
        body = await request.json()
        user_id = int(body.get("user_id"))
        delta = int(body.get("delta"))
    except (ValueError, TypeError):
        return web.json_response({"ok": False, "error": "Некорректные данные"}, status=400)

    reason = (body.get("reason") or "admin_manual").strip()[:64]

    user = await db.get_user(user_id)
    if not user:
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)

    new_balance = await gamedb.add_points(user_id, delta, f"admin:{reason}")
    return web.json_response({"ok": True, "new_balance": new_balance})


def setup_admin_routes(app: web.Application):
    app.router.add_get("/admin", admin_page)
    app.router.add_post("/api/admin/login", api_admin_login)
    app.router.add_get("/api/admin/users", api_admin_users)
    app.router.add_get("/api/admin/user/{user_id}", api_admin_user_detail)
    app.router.add_post("/api/admin/points/adjust", api_admin_points_adjust)
    logger.info("Админ-панель PurioApp подключена на /admin")
