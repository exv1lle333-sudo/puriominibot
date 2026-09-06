// ===================== PurioApp frontend =====================
const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) {
  tg.ready();
  tg.expand();
  try { tg.setHeaderColor('#14102a'); } catch (e) {}
  try { tg.setBackgroundColor('#0d0a17'); } catch (e) {}
}

const INIT_DATA = tg && tg.initData ? tg.initData : "";
// Позволяет открывать в обычном браузере для отладки: /?dev_user_id=123
const DEV_USER_ID = new URLSearchParams(location.search).get("dev_user_id");

async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (INIT_DATA) headers["X-Init-Data"] = INIT_DATA;
  if (!INIT_DATA && DEV_USER_ID) headers["X-Dev-User-Id"] = DEV_USER_ID;

  const url = path + (!INIT_DATA && DEV_USER_ID ? (path.includes("?") ? "&" : "?") + "dev_user_id=" + DEV_USER_ID : "");
  const resp = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await resp.json(); } catch (e) {}
  if (!resp.ok) {
    const err = new Error((data && data.error) || "Ошибка сети");
    err.data = data;
    throw err;
  }
  return data;
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove("show"), 2200);
}

function haptic(type = "light") {
  if (!tg || !tg.HapticFeedback) return;
  try {
    if (type === "success" || type === "error" || type === "warning") tg.HapticFeedback.notificationOccurred(type);
    else tg.HapticFeedback.impactOccurred(type);
  } catch (e) {}
}

function fmtNum(n) { return Math.round(n).toLocaleString("ru-RU"); }
function fmtDate(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// ===================== NAV =====================
const Nav = {
  go(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("page-" + page).classList.add("active");
    document.querySelector(`.nav-btn[data-page="${page}"]`).classList.add("active");
    if (page === "tasks") loadTasks();
    if (page === "vpn") loadVpn();
    if (page === "casino") loadCasino();
    if (page === "profile") loadProfile();
  }
};
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => { haptic(); Nav.go(btn.dataset.page); });
});

// ===================== HOME / STATE =====================
let STATE = null;

async function loadState() {
  STATE = await api("/api/state");
  renderTop();
  renderDragon();
  renderStreak();
  renderHomeStats();
  renderTasksTeaser();
}

function renderTop() {
  document.getElementById("topPointsValue").textContent = fmtNum(STATE.points);
  document.getElementById("topLevel").textContent = STATE.dragon.level;
  document.getElementById("topSubStatus").textContent = STATE.subscription.active
    ? "VPN активен ✅"
    : "VPN не активен";
}

function renderDragon() {
  const d = STATE.dragon;
  document.getElementById("homeLevelText").textContent = `· Ур. ${d.level}`;
  const pct = Math.min(100, Math.round((d.xp / d.xp_needed) * 100));
  document.getElementById("xpFill").style.width = pct + "%";
  document.getElementById("xpText").textContent = `${d.xp} / ${d.xp_needed} XP`;
  const CIRC = 327;
  document.getElementById("ringFg").style.strokeDashoffset = CIRC - (CIRC * pct / 100);
}

function renderStreak() {
  const s = STATE.streak;
  const row = document.getElementById("streakRow");
  row.innerHTML = "";
  s.rewards.forEach((reward, i) => {
    const div = document.createElement("div");
    div.className = "streak-day";
    if (i < s.day_index) div.classList.add("done");
    if (i === s.day_index) { div.classList.add("done", "today"); }
    div.innerHTML = `<div class="n">Д${i + 1}</div><div>+${reward}</div>`;
    row.appendChild(div);
  });
  document.getElementById("streakWeekLabel").textContent = "";
  document.getElementById("streakHint").textContent =
    `Завтра за вход получишь +${s.next_reward} поинтов. Пропустишь день — серия начнётся заново.`;
}

function renderHomeStats() {
  const series = STATE.vpn_week_series || [];
  const hours = series.reduce((a, d) => a + (d.hours || 0), 0);
  const points = series.reduce((a, d) => a + (d.points || 0), 0);
  document.getElementById("homeVpnHours").textContent = hours + "ч";
  document.getElementById("homeVpnPoints").textContent = fmtNum(points);
}

async function renderTasksTeaser() {
  const { tasks } = await api("/api/tasks");
  const list = document.getElementById("teaserList");
  list.innerHTML = "";
  tasks.slice(0, 3).forEach(t => {
    const div = document.createElement("div");
    div.className = "teaser-item" + (t.completed ? " done" : "");
    div.textContent = `${t.icon} ${t.title} ${t.completed ? "✓" : `(${t.progress}/${t.target})`}`;
    list.appendChild(div);
  });
}

// ===================== TASKS =====================
async function loadTasks() {
  const { tasks } = await api("/api/tasks");
  const list = document.getElementById("tasksList");
  list.innerHTML = "";
  tasks.forEach(t => {
    const pct = Math.min(100, Math.round((t.progress / t.target) * 100));
    const card = document.createElement("div");
    card.className = "task-card";
    let btnClass = "task-claim", btnText = "В процессе";
    if (t.claimed) { btnClass += " claimed"; btnText = "✓ Забрано"; }
    else if (t.completed) { btnClass += " ready"; btnText = "Забрать"; }
    card.innerHTML = `
      <div class="task-ico">${t.icon}</div>
      <div class="task-body">
        <div class="task-title">${t.title}</div>
        <div class="task-desc">${t.desc}</div>
        <div class="task-progress-bar"><div class="task-progress-fill" style="width:${pct}%"></div></div>
        <div class="task-reward">+${t.reward_points} ✦ · +${t.reward_xp} XP</div>
      </div>
      <button class="${btnClass}" ${(!t.completed || t.claimed) ? "disabled" : ""} data-code="${t.code}">${btnText}</button>
    `;
    list.appendChild(card);
  });
  list.querySelectorAll(".task-claim.ready").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const res = await api("/api/tasks/claim", { method: "POST", body: { task_code: btn.dataset.code } });
        haptic("success");
        toast(`+${res.points_awarded} поинтов, +${res.xp_awarded} XP${res.leveled_up ? " · Новый уровень! 🎉" : ""}`);
        await loadState();
        await loadTasks();
      } catch (e) {
        haptic("error");
        toast(e.message);
      }
    });
  });
}

// ===================== VPN =====================
async function loadVpn() {
  await loadState();
  const s = STATE.subscription;
  document.getElementById("subStatusLine").textContent = s.active
    ? `✅ Активна до ${fmtDate(s.expires_at)}`
    : "❌ Подписка не активна";
  const actions = document.getElementById("subActions");
  actions.innerHTML = `<a class="btn btn-secondary" href="https://t.me" onclick="return false;" style="display:none"></a>`;
  actions.innerHTML = "";
  if (tg && tg.openTelegramLink) {
    // ничего — покупка ниже через тарифы
  }

  drawVpnChart(STATE.vpn_week_series || []);
  await loadTariffs();

  document.getElementById("promoBtn").onclick = async () => {
    const code = document.getElementById("promoInput").value.trim();
    if (!code) return;
    try {
      const res = await api("/api/promo/activate", { method: "POST", body: { code } });
      haptic("success");
      toast(`Промокод активирован: +${res.days} дней VPN!`);
      document.getElementById("promoInput").value = "";
      await loadVpn();
    } catch (e) {
      haptic("error");
      toast(e.message);
    }
  };
}

async function loadTariffs() {
  const { tariffs } = await api("/api/tariffs");
  const el = document.getElementById("tariffsList");
  el.innerHTML = "";
  tariffs.forEach(t => {
    const row = document.createElement("div");
    row.className = "tariff-row";
    row.innerHTML = `<div class="tariff-label">${t.label}</div><button class="btn btn-primary" data-days="${t.days}">Купить</button>`;
    el.appendChild(row);
  });
  el.querySelectorAll("button[data-days]").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const res = await api("/api/subscription/buy", { method: "POST", body: { days: Number(btn.dataset.days) } });
        haptic("success");
        toast("Подписка оформлена! ✅");
        await loadVpn();
      } catch (e) {
        haptic("error");
        toast(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function drawVpnChart(series) {
  const canvas = document.getElementById("vpnChart");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const days = [...series];
  while (days.length < 7) days.unshift({ day_key: "", hours: 0 });

  const max = Math.max(1, ...days.map(d => d.hours || 0));
  const barW = W / days.length;
  days.forEach((d, i) => {
    const h = ((d.hours || 0) / max) * (H - 24);
    const x = i * barW + barW * 0.25;
    const grad = ctx.createLinearGradient(0, H - h, 0, H);
    grad.addColorStop(0, "#a855f7");
    grad.addColorStop(1, "#7c3aed");
    ctx.fillStyle = grad;
    const w = barW * 0.5;
    const y = H - h - 16;
    roundRect(ctx, x, y, w, h, 5);
    ctx.fill();
    ctx.fillStyle = "#9a90b8";
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    const label = d.day_key ? d.day_key.slice(6, 8) + "." + d.day_key.slice(4, 6) : "";
    ctx.fillText(label, x + w / 2, H - 4);
  });
}
function roundRect(ctx, x, y, w, h, r) {
  if (h < 1) h = 1;
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// ===================== CASINO =====================
let casinoGame = "dice";

document.querySelectorAll(".tswitch").forEach(btn => {
  btn.addEventListener("click", () => {
    haptic();
    casinoGame = btn.dataset.game;
    document.querySelectorAll(".tswitch").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".game-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("game-" + casinoGame).classList.add("active");
  });
});

function betQuickButtons(containerId, inputId, balanceGetter) {
  const el = document.getElementById(containerId);
  el.innerHTML = "";
  [10, 50, 100, "MAX"].forEach(v => {
    const b = document.createElement("button");
    b.textContent = v === "MAX" ? "MAX" : "+" + v;
    b.addEventListener("click", () => {
      const input = document.getElementById(inputId);
      if (v === "MAX") input.value = Math.max(1, Math.floor(balanceGetter()));
      else input.value = Math.max(1, (Number(input.value) || 0) + v);
    });
    el.appendChild(b);
  });
}

let casinoBalance = 0;

async function loadCasino() {
  const data = await api("/api/casino/state");
  casinoBalance = data.points;
  document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);
  renderCasinoHistory(data.history);
  betQuickButtons("diceBetQuick", "diceBet", () => casinoBalance);
  betQuickButtons("slotBetQuick", "slotBet", () => casinoBalance);
  renderPaytable();
}

function renderPaytable() {
  document.getElementById("paytable").innerHTML = `
    🐉🐉🐉 x15 &nbsp; 7️⃣7️⃣7️⃣ x40 &nbsp; 💎💎💎 x8<br>
    🔥🔥🔥 x5 &nbsp; ⭐⭐⭐ x3 &nbsp; 🍀🍀🍀 x2<br>
    любые два 🐉 — x1.5
  `;
}

function renderCasinoHistory(history) {
  const el = document.getElementById("casinoHistory");
  if (!history.length) { el.innerHTML = '<div class="muted small">Пока пусто — сделай первую ставку!</div>'; return; }
  el.innerHTML = "";
  history.forEach(h => {
    const won = h.payout > h.bet;
    const net = h.payout - h.bet;
    const row = document.createElement("div");
    row.className = "hist-row";
    const gameLabel = h.game === "dice" ? "🎲 Кости" : "🎰 Слоты";
    row.innerHTML = `<span>${gameLabel} · ставка ${h.bet}</span><span class="${net >= 0 ? "hist-win" : "hist-lose"}">${net >= 0 ? "+" : ""}${net}</span>`;
    el.appendChild(row);
  });
}

// ---- DICE ----
const diceChance = document.getElementById("diceChance");
function updateDiceMultiplier() {
  const chance = Number(diceChance.value);
  const mult = (99 / chance).toFixed(2);
  document.getElementById("diceChanceVal").textContent = chance + "%";
  document.getElementById("diceMultVal").textContent = "x" + mult;
  document.getElementById("diceMarker").style.left = chance + "%";
  document.getElementById("diceFill").style.width = chance + "%";
}
diceChance.addEventListener("input", updateDiceMultiplier);
updateDiceMultiplier();

document.getElementById("diceRollBtn").addEventListener("click", async () => {
  const bet = Number(document.getElementById("diceBet").value);
  const win_chance = Number(diceChance.value);
  const btn = document.getElementById("diceRollBtn");
  btn.disabled = true;
  try {
    const { result, new_balance } = await api("/api/casino/dice", { method: "POST", body: { bet, win_chance } });
    casinoBalance = new_balance;
    document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);
    const marker = document.getElementById("diceMarker");
    const label = document.getElementById("diceRollValue");
    marker.style.left = result.roll + "%";
    label.style.left = result.roll + "%";
    label.textContent = result.roll;
    haptic(result.won ? "success" : "error");
    toast(result.won ? `Победа! +${result.net} ✦` : `Мимо... -${bet} ✦`);
    await loadCasino();
    await loadState();
  } catch (e) {
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

// ---- SLOTS ----
document.getElementById("slotSpinBtn").addEventListener("click", async () => {
  const bet = Number(document.getElementById("slotBet").value);
  const btn = document.getElementById("slotSpinBtn");
  btn.disabled = true;
  const reelEls = [0, 1, 2].map(i => document.getElementById("reel" + i));
  reelEls.forEach(r => r.classList.add("spin"));
  document.getElementById("slotResult").textContent = "Крутим…";

  try {
    const spinPromise = api("/api/casino/slots", { method: "POST", body: { bet } });
    await new Promise(r => setTimeout(r, 700)); // небольшая анимация перед результатом
    const { result, new_balance } = await spinPromise;
    reelEls.forEach((r, i) => { r.classList.remove("spin"); r.textContent = result.reels[i]; });
    casinoBalance = new_balance;
    document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);
    document.getElementById("slotResult").textContent = result.won
      ? `${result.win_label} Выигрыш +${result.net} ✦`
      : "Не повезло, попробуй ещё раз";
    haptic(result.won ? "success" : "error");
    await loadCasino();
    await loadState();
  } catch (e) {
    reelEls.forEach(r => r.classList.remove("spin"));
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

// ===================== PROFILE =====================
async function loadProfile() {
  const [p] = await Promise.all([api("/api/profile")]);
  document.getElementById("profBalance").textContent = fmtNum(p.balance_rub) + " ₽";
  document.getElementById("profSub").textContent = p.subscription_active
    ? "Активна до " + fmtDate(p.subscription_expires_at)
    : "Не активна";
  document.getElementById("profLevel").textContent = STATE ? STATE.dragon.level : "1";
  document.getElementById("profPoints").textContent = STATE ? fmtNum(STATE.points) : "0";

  document.getElementById("refCount").textContent = p.referral_count;
  document.getElementById("refPaid").textContent = p.referral_paid_count;
  document.getElementById("refEarned").textContent = fmtNum(p.referral_earned) + " ₽";
  document.getElementById("refLinkInput").value = p.referral_link || "ссылка появится после /start в боте";

  document.getElementById("supportLink").href = "https://t.me/" + (p.support_username || "").replace("@", "");
  document.getElementById("channelLink").href = p.channel_link || "#";

  document.getElementById("refCopyBtn").onclick = () => {
    const input = document.getElementById("refLinkInput");
    input.select();
    navigator.clipboard && navigator.clipboard.writeText(input.value).catch(() => {});
    haptic("success");
    toast("Ссылка скопирована!");
  };

  renderSkins();
}

function renderSkins() {
  if (!STATE) return;
  const grid = document.getElementById("skinsGrid");
  grid.innerHTML = "";
  STATE.dragon.skins.forEach(s => {
    const div = document.createElement("div");
    div.className = "skin-item" + (s.owned ? " unlocked" : "") + (s.equipped ? " equipped" : "");
    div.innerHTML = `
      ${s.locked ? `<div class="skin-lock">🔒</div>` : ""}
      <svg viewBox="0 0 200 200"><use href="#dragon-svg"/></svg>
      <div class="skin-name">${s.name}</div>
      <div class="muted" style="font-size:9px;">${s.coming_soon ? "скоро" : (s.owned ? (s.equipped ? "надет" : "есть") : s.price + " ✦")}</div>
    `;
    if (s.owned && !s.equipped) {
      div.style.cursor = "pointer";
      div.addEventListener("click", async () => {
        try {
          await api("/api/dragon/equip", { method: "POST", body: { skin_code: s.code } });
          haptic("success");
          await loadState();
          renderSkins();
        } catch (e) { toast(e.message); }
      });
    }
    grid.appendChild(div);
  });
}

// ===================== INIT =====================
(async function init() {
  try {
    await api("/api/auth", { method: "POST" });
  } catch (e) {
    console.error("auth failed", e);
    toast("Не удалось авторизоваться. Открой приложение через кнопку в боте.");
    return;
  }
  await loadState();
})();
