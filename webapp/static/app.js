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
<<<<<<< HEAD
  async go(page) {
    if (page === "tap") page = "home";
    const target = document.getElementById("page-" + page);
    if (!target) {
      toast("Раздел не найден");
      return;
    }
    haptic();
    document.querySelectorAll(".page").forEach(p => {
      p.classList.toggle("active", p === target);
    });
    const parent = {
      tasks: "home",
      casino: "home",
      shop: "profile",
    }[page] || page;
    document.querySelectorAll(".nav-btn").forEach(b => {
      const active = b.dataset.page === parent;
      b.classList.toggle("active", active);
      if (active) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    window.scrollTo({ top: 0, behavior: "auto" });
    try {
      if (page === "home") {
        await loadState();
        await loadTap();
      }
      if (page === "tasks") await loadTasks();
      if (page === "vpn") await loadVpn();
      if (page === "casino") await loadCasino();
      if (page === "profile") await loadProfile();
      if (page === "shop") await loadShop();
    } catch (e) {
      toast(e.message || "Не удалось загрузить раздел");
    }
  }
};
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => Nav.go(btn.dataset.page));
=======
  go(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("page-" + page).classList.add("active");
    // БАГ (исправлено): querySelector возвращал null для страниц без кнопки в
    // нижней навигации (например "shop", открываемой карточкой из профиля),
    // и .classList.add на null валил весь переход по странице. Теперь просто
    // не подсвечиваем несуществующую кнопку вместо падения с ошибкой.
    const navBtn = document.querySelector(`.nav-btn[data-page="${page}"]`);
    if (navBtn) navBtn.classList.add("active");
    if (page === "tasks") loadTasks();
    if (page === "vpn") loadVpn();
    if (page === "tap") loadTap();
    if (page === "casino") loadCasino();
    if (page === "profile") loadProfile();
    if (page === "shop") loadShop();
  }
};
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => { haptic(); Nav.go(btn.dataset.page); });
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
});

// ===================== DRAGON SKINS (visual filters) =====================
// Скины дракона — единая 3D-модель, разный цвет через CSS filter (пока нет
// отдельных артов под каждый скин). Ключ — skin_code с бэкенда.
const SKIN_FILTERS = {
  default: "",
  shadow: "hue-rotate(195deg) saturate(1.3) brightness(0.65)",
  golden: "hue-rotate(70deg) saturate(1.8) brightness(1.35)",
  storm: "hue-rotate(150deg) saturate(1.6) brightness(1.05)",
  cosmic: "hue-rotate(-90deg) saturate(2) brightness(1.15)",
};
<<<<<<< HEAD
// Аксессуары рисуются отдельно от тела: фильтр скина их не перекрашивает.
const PURIO_CLOTHES = {
  cloth_scarf_red: {
    front: `
      <path d="M111 118 L132 123 L126 157 L113 151Z"
            fill="#db274d" stroke="#921b3b" stroke-width="2"/>
      <path d="M65 109 Q100 123 135 109 L136 121
               Q100 139 64 121Z"
            fill="#fa4560" stroke="#a02041" stroke-width="2"/>
      <path d="M70 115 Q100 128 129 115"
            fill="none" stroke="#ff98a5" stroke-width="3"/>
      <path d="M116 144 L128 149 M115 149 L127 154"
            stroke="#ffadb6" stroke-width="2"/>
    `
  },
  cloth_glasses: {
    front: `
      <g fill="#21182f" stroke="#e1cef5" stroke-width="3">
        <path d="M59 64 L94 64 L91 83 Q76 94 62 81Z"/>
        <path d="M106 64 L141 64 L138 81 Q124 94 109 83Z"/>
      </g>
      <path d="M94 69 Q100 64 106 69 M51 64 L59 67 M141 67 L149 64"
            fill="none" stroke="#eee0ff" stroke-width="3"/>
      <path d="M67 69 L78 82 M115 69 L126 82"
            stroke="#9786bd" stroke-width="3"/>
    `
  },
  cloth_pilot_cap: {
    front: `
      <path d="M60 49 Q64 23 102 24 Q139 26 143 51Z"
            fill="#4756c5" stroke="#283477" stroke-width="2"/>
      <path d="M58 49 Q107 39 145 49 L151 56 Q102 51 58 58Z"
            fill="#7787f4" stroke="#283477" stroke-width="2"/>
      <path d="M96 27 L103 43" stroke="#a9b8ff" stroke-width="3"/>
      <circle cx="115" cy="37" r="6" fill="#f9d578"/>
    `
  },
  cloth_cape_hero: {
    back: `
      <path d="M64 109 Q100 119 136 109 L158 179
               Q125 169 100 184 Q75 169 42 179Z"
            fill="#d02d64" stroke="#861743" stroke-width="3"/>
      <path d="M72 119 L60 167 M128 119 L140 167"
            stroke="#f56a95" stroke-width="3"/>
    `,
    front: `<circle cx="100" cy="119" r="6" fill="#ffda75"
                    stroke="#b67d28" stroke-width="2"/>`
  },
  cloth_crown_mini: {
    front: `
      <path d="M72 42 L67 18 L87 29 L100 9 L113 29 L133 18 L128 42Z"
            fill="#ffce50" stroke="#b27b22" stroke-width="2"/>
      <path d="M73 39 L127 39 L125 48 L75 48Z"
            fill="#ffe28e" stroke="#b27b22" stroke-width="2"/>
      <path d="M100 26 L105 33 L100 40 L95 33Z" fill="#c142eb"/>
      <circle cx="80" cy="34" r="3" fill="#f05c7e"/>
      <circle cx="120" cy="34" r="3" fill="#65dceb"/>
    `
  },
  cloth_armor_gold: {
    front: `
      <path d="M72 122 L85 116 Q100 127 115 116 L128 122
               L123 159 L100 173 L77 159Z"
            fill="#e9b844" stroke="#946122" stroke-width="3"/>
      <path d="M100 126 L100 163 M80 142 L120 142"
            stroke="#ffe6a0" stroke-width="3"/>
      <path d="M100 132 L107 142 L100 153 L93 142Z"
            fill="#9b4de0" stroke="#ffe49a" stroke-width="2"/>
      <path d="M53 120 Q65 111 77 120 L72 133 L53 133Z
               M123 120 Q135 111 147 120 L147 133 L128 133Z"
            fill="#ffdb77" stroke="#946122" stroke-width="2"/>
    `
  },
  cloth_wings_ice: {
    back: `
      <g fill="#a5efff" stroke="#4ca0dc" stroke-width="2">
        <path d="M66 136 L8 73 L15 114 L28 108 L30 139
                 L43 126 L49 153Z"/>
        <path d="M134 136 L192 73 L185 114 L172 108 L170 139
                 L157 126 L151 153Z"/>
      </g>
      <path d="M62 135 L16 88 M138 135 L184 88"
            stroke="#efffff" stroke-width="3"/>
    `
  }
};

function applyEquippedSkinVisuals(skinCode) {
  const clothing = STATE?.cosmetics?.equipped?.clothing || "";
  const art = PURIO_CLOTHES[clothing] || {};
  const filter = SKIN_FILTERS[skinCode] || "";
  [
    document.getElementById("dragonBig"),
    document.getElementById("tapDragon"),
    document.querySelector("#topDragon .dragon-mini"),
  ].forEach(el => {
    if (!el) return;
    el.setAttribute("viewBox", "0 0 200 200");

    // Только константная SVG-разметка. Данные API не вставляются в HTML.
    const key = skinCode + "|" + clothing;
    if (el.dataset.purioLook === key) return;
    el.dataset.purioLook = key;
    el.style.removeProperty("filter");
    el.innerHTML = `
      <g class="purio-accessory">${art.back || ""}</g>
      <g class="purio-body"><use href="#dragon-svg"/></g>
      <g class="purio-accessory">${art.front || ""}</g>
    `;
    el.querySelector(".purio-body").style.filter = filter || "none";
=======
function applyEquippedSkinVisuals(skinCode) {
  const filter = SKIN_FILTERS[skinCode] || "";
  const dragonEls = [
    document.getElementById("dragonBig"),
    document.getElementById("tapDragon"),
    document.querySelector("#topDragon .dragon-mini"),
  ];
  dragonEls.forEach(el => {
    if (el) el.style.filter = filter ? filter + " drop-shadow(0 4px 10px #7c3aed55)" : "";
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  });
}

// ===================== HOME / STATE =====================
let STATE = null;

async function loadState() {
  STATE = await api("/api/state");
  renderTop();
  renderDragon();
  renderStreak();
  renderHomeStats();
<<<<<<< HEAD
  void renderTasksTeaser().catch(() => {
    document.getElementById("teaserList").textContent =
      "Не удалось загрузить задания. Открой раздел ещё раз.";
  });
=======
  renderTasksTeaser();
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
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
  applyEquippedSkinVisuals(d.equipped_skin || "default");
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
<<<<<<< HEAD
      } finally {
        btn.disabled = false;
=======
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
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

<<<<<<< HEAD
document.querySelectorAll("#page-casino [data-game]").forEach(btn => {
  btn.addEventListener("click", () => {
    haptic();
    casinoGame = btn.dataset.game;
    document.querySelectorAll("#page-casino [data-game]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll("#page-casino .game-panel").forEach(p => p.classList.remove("active"));
=======
document.querySelectorAll(".tswitch").forEach(btn => {
  btn.addEventListener("click", () => {
    haptic();
    casinoGame = btn.dataset.game;
    document.querySelectorAll(".tswitch").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".game-panel").forEach(p => p.classList.remove("active"));
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
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

// Для краша — упрощённый набор кнопок ставки: половина / удвоить / всё,
// вместо четырёх произвольных "+10/+50/+100/MAX". Меньше кнопок и понятнее
// логика (стандартная схема для крash-игр).
function crashQuickBetButtons() {
  const el = document.getElementById("crashBetQuick");
  el.innerHTML = "";
  const input = document.getElementById("crashBet");
  [
    { label: "½", apply: () => Math.max(1, Math.floor((Number(input.value) || 0) / 2)) },
    { label: "2×", apply: () => Math.max(1, Math.floor((Number(input.value) || 0) * 2)) },
    { label: "MAX", apply: () => Math.max(1, Math.floor(casinoBalance)) },
  ].forEach(({ label, apply }) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.addEventListener("click", () => { input.value = apply(); });
    el.appendChild(b);
  });
}

<<<<<<< HEAD
async function loadCasino(resume = true) {
=======
async function loadCasino() {
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  const data = await api("/api/casino/state");
  casinoBalance = data.points;
  document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);
  renderCasinoHistory(data.history);
  betQuickButtons("diceBetQuick", "diceBet", () => casinoBalance);
  betQuickButtons("slotBetQuick", "slotBet", () => casinoBalance);
  betQuickButtons("coinBetQuick", "coinBet", () => casinoBalance);
  crashQuickBetButtons();
  renderPaytable();
<<<<<<< HEAD
  if (resume) await resumeCrashRound();
=======
  await resumeCrashRound();
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
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
  const GAME_LABELS = { dice: "🎲 Кости", slots: "🎰 Слоты", coinflip: "🪙 Монетка", crash: "📈 Краш" };
  history.forEach(h => {
    const net = h.payout - h.bet;
    const row = document.createElement("div");
    row.className = "hist-row";
    const gameLabel = GAME_LABELS[h.game] || h.game;
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
<<<<<<< HEAD
    const [{ result, new_balance }] = await Promise.all([
      spinPromise,
      new Promise(r => setTimeout(r, 700)),
    ]);
=======
    await new Promise(r => setTimeout(r, 700)); // небольшая анимация перед результатом
    const { result, new_balance } = await spinPromise;
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
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

// ---- COINFLIP ----
let coinChoice = "heads";
document.querySelectorAll(".coin-choice-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    haptic();
    coinChoice = btn.dataset.choice;
    document.querySelectorAll(".coin-choice-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
  });
});

document.getElementById("coinFlipBtn").addEventListener("click", async () => {
  const bet = Number(document.getElementById("coinBet").value);
  const btn = document.getElementById("coinFlipBtn");
  const coinInner = document.getElementById("coinInner");
  btn.disabled = true;
  document.getElementById("coinResult").textContent = "Подкидываем…";

  try {
    const spinPromise = api("/api/casino/coinflip", { method: "POST", body: { bet, choice: coinChoice } });
    // запускаем визуальное вращение сразу, не дожидаясь ответа сервера
    const spins = 5 + Math.floor(Math.random() * 3);
    coinInner.style.transition = "none";
    coinInner.style.transform = "rotateY(0deg)";
    // force reflow, чтобы сброс трансформации точно применился перед новой анимацией
    void coinInner.offsetWidth;
    coinInner.style.transition = "";

    const { result, new_balance } = await spinPromise;
    const finalTails = result.result === "tails" ? 180 : 0;
    coinInner.style.transform = `rotateY(${spins * 360 + finalTails}deg)`;

    await new Promise(r => setTimeout(r, 1750));

    casinoBalance = new_balance;
    document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);
    const resultLabel = result.result === "heads" ? "🦅 Орёл" : "Р Решка";
    document.getElementById("coinResult").textContent = result.won
      ? `${resultLabel}! Победа +${result.net} ✦`
      : `${resultLabel}. Мимо... -${bet} ✦`;
    haptic(result.won ? "success" : "error");
    await loadCasino();
    await loadState();
  } catch (e) {
    haptic("error");
    toast(e.message);
    document.getElementById("coinResult").textContent = "Выбери сторону и подкинь монетку";
  } finally {
    btn.disabled = false;
  }
});

// ---- CRASH ----
let crashRoundId = null;
let crashStartedAt = null;
let crashAnimHandle = null;
let crashPollHandle = null;
let crashResolving = false;
const CRASH_GROWTH_RATE = 0.08; // должно совпадать с CRASH_GROWTH_RATE на бэкенде
const CRASH_POLL_MS = 300; // как часто сверяемся с сервером, взорвался ли раунд

function crashMultAt(elapsedSec) {
  return Math.min(1000, Math.exp(CRASH_GROWTH_RATE * Math.max(0, elapsedSec)));
}

function drawCrashGraph(elapsedSec, busted) {
  const canvas = document.getElementById("crashCanvas");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const T = Math.max(elapsedSec, 1);
  const points = [];
  const steps = 60;
  for (let i = 0; i <= steps; i++) {
    const t = (T * i) / steps;
    const m = crashMultAt(t);
    points.push({ t, m });
  }
  const maxM = Math.max(2, crashMultAt(elapsedSec) * 1.15);

  ctx.beginPath();
  points.forEach((p, i) => {
    const x = (p.t / T) * (W - 16) + 8;
    const y = H - 12 - ((p.m - 1) / (maxM - 1)) * (H - 24);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  const grad = ctx.createLinearGradient(0, 0, W, 0);
  grad.addColorStop(0, busted ? "#f87171" : "#a855f7");
  grad.addColorStop(1, busted ? "#ef4444" : "#c084fc");
  ctx.strokeStyle = grad;
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  ctx.stroke();

  // точка/ракета на конце линии
  const last = points[points.length - 1];
  const lx = (last.t / T) * (W - 16) + 8;
  const ly = H - 12 - ((last.m - 1) / (maxM - 1)) * (H - 24);
  ctx.beginPath();
  ctx.arc(lx, ly, 5, 0, Math.PI * 2);
  ctx.fillStyle = busted ? "#ef4444" : "#e9d5ff";
  ctx.fill();
}

function crashAnimLoop() {
  if (crashStartedAt === null) return;
  const elapsed = (Date.now() - crashStartedAt) / 1000;
  const mult = crashMultAt(elapsed);
  document.getElementById("crashMultLabel").textContent = mult.toFixed(2) + "x";
  drawCrashGraph(elapsed, false);
  crashAnimHandle = requestAnimationFrame(crashAnimLoop);
}

function stopCrashAnim() {
  if (crashAnimHandle) cancelAnimationFrame(crashAnimHandle);
  crashAnimHandle = null;
}

// Пока раунд активен, регулярно спрашиваем сервер "уже рвануло?".
// Раньше клиент просто рисовал график по локальному таймеру и ничего
// не проверял — из-за этого он мог расти сколько угодно, а реальный
// результат вскрывался только по клику "Забрать". Теперь взрыв
// подхватывается сам, в момент, когда он реально произошёл на сервере.
function startCrashPolling() {
  stopCrashPolling();
  crashPollHandle = setInterval(async () => {
    if (!crashRoundId || crashResolving) return;
    try {
      const { round } = await api("/api/casino/crash/state");
      if (round && round.busted) {
        await finishCrashRound(true);
      } else if (!round) {
        // раунд уже закрыт где-то ещё — просто синхронизируем интерфейс
        stopCrashPolling();
        stopCrashAnim();
        crashRoundId = null;
        crashStartedAt = null;
        setCrashUi("idle");
      }
    } catch (e) { /* сеть моргнула — попробуем на следующем тике */ }
  }, CRASH_POLL_MS);
}

function stopCrashPolling() {
  if (crashPollHandle) clearInterval(crashPollHandle);
  crashPollHandle = null;
}

function setCrashUi(state) {
  const startBtn = document.getElementById("crashStartBtn");
  const cashoutBtn = document.getElementById("crashCashoutBtn");
  if (state === "idle") {
    startBtn.style.display = "";
    cashoutBtn.style.display = "none";
    document.getElementById("crashStatus").textContent = "Сделай ставку и жми «Старт»";
    document.getElementById("crashMultLabel").className = "crash-mult";
    document.getElementById("crashMultLabel").textContent = "1.00x";
    drawCrashGraph(0.001, false);
  } else if (state === "running") {
    startBtn.style.display = "none";
    cashoutBtn.style.display = "";
    document.getElementById("crashStatus").textContent = "График растёт… успей забрать выигрыш!";
    document.getElementById("crashMultLabel").className = "crash-mult";
  }
}

async function resumeCrashRound() {
  try {
    const { round } = await api("/api/casino/crash/state");
    if (round) {
      crashRoundId = round.round_id;
      crashStartedAt = Date.now() - round.elapsed * 1000;
      setCrashUi("running");
      stopCrashAnim();
      crashAnimLoop();
      if (round.busted) {
        await finishCrashRound(true);
      } else {
        startCrashPolling();
      }
    } else {
      crashRoundId = null;
      crashStartedAt = null;
      setCrashUi("idle");
    }
  } catch (e) { /* ignore */ }
}

document.getElementById("crashStartBtn").addEventListener("click", async () => {
  const bet = Number(document.getElementById("crashBet").value);
  const btn = document.getElementById("crashStartBtn");
  btn.disabled = true;
  try {
    const res = await api("/api/casino/crash/start", { method: "POST", body: { bet } });
    crashRoundId = res.round_id;
    crashStartedAt = Date.now();
    casinoBalance = res.new_balance;
    document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);
    setCrashUi("running");
    stopCrashAnim();
    crashAnimLoop();
    startCrashPolling();
    haptic("light");
  } catch (e) {
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("crashCashoutBtn").addEventListener("click", async () => {
  await finishCrashRound(false);
});

// Единая точка завершения раунда — вызывается и по клику "Забрать",
// и автоматически, как только опрос сервера покажет, что график взорвался.
// autoBust=true — раунд закрылся сам, без ручного клика игрока.
async function finishCrashRound(autoBust) {
  if (!crashRoundId || crashResolving) return;
  crashResolving = true;
  stopCrashPolling();
  const btn = document.getElementById("crashCashoutBtn");
  btn.disabled = true;
  try {
    const res = await api("/api/casino/crash/cashout", { method: "POST", body: { round_id: crashRoundId } });
    stopCrashAnim();
    const label = document.getElementById("crashMultLabel");
    casinoBalance = res.new_balance;
    document.getElementById("casinoBalance").textContent = fmtNum(casinoBalance);

    if (res.won) {
      label.textContent = res.multiplier.toFixed(2) + "x";
      label.className = "crash-mult cashed";
      document.getElementById("crashStatus").textContent = `Забрал на ${res.multiplier.toFixed(2)}x! +${res.payout - res.bet} ✦`;
      drawCrashGraph((Date.now() - crashStartedAt) / 1000, false);
      haptic("success");
    } else {
      const point = res.crash_point || res.multiplier;
      // рисуем график ровно до точки взрыва, а не до момента, когда мы её заметили —
      // так анимация на экране совпадает с реальным результатом сервера
      const elapsedAtPoint = Math.log(Math.max(1, point)) / CRASH_GROWTH_RATE;
      label.textContent = point.toFixed(2) + "x 💥";
      label.className = "crash-mult busted";
      document.getElementById("crashStatus").textContent = autoBust
        ? `Взорвался на ${point.toFixed(2)}x — не успел забрать. -${res.bet} ✦`
        : `Взорвался на ${point.toFixed(2)}x. -${res.bet} ✦`;
      drawCrashGraph(elapsedAtPoint, true);
      haptic("error");
    }

    crashRoundId = null;
    crashStartedAt = null;
    document.getElementById("crashStartBtn").style.display = "";
    document.getElementById("crashCashoutBtn").style.display = "none";

<<<<<<< HEAD
    await loadCasino(false);
=======
    await loadCasino();
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
    await loadState();
  } catch (e) {
    haptic("error");
    if (!autoBust) toast(e.message);
    crashResolving = false; // снимаем блокировку до ресинка, иначе resumeCrashRound не сможет доработать
    // раунд мог уже закрыться параллельным запросом — просто сверим состояние
    await resumeCrashRound();
  } finally {
    btn.disabled = false;
    crashResolving = false;
  }
}

// ===================== TAPALKA (Purio Tap) =====================
<<<<<<< HEAD
// Серверное состояние + очередь ещё не отправленных тапов.
// Запросы на начисление не повторяются автоматически: это могло бы
// удвоить награду, если сервер обработал запрос, но ответ потерялся.
=======
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
let tapState = null;
let tapLocalEnergy = 0;
let tapQueue = 0;
let tapFlushTimer = null;
let tapTicker = null;
let tapFlushing = false;
<<<<<<< HEAD
let tapLoading = false;
let tapInFlight = 0;
let tapLastTick = performance.now();
let tapPulseTimer = null;

function tapCanEarn(points = tapState?.day_points || 0) {
  if (!tapState) return false;
  return tapState.day_cap - points >= tapState.reward_per_tap;
}

async function loadTap() {
  if (tapLoading || tapFlushing || tapQueue > 0) return;
  tapLoading = true;
  try {
    tapState = await api("/api/tap/state");
    tapLocalEnergy = tapState.energy;
    tapLastTick = performance.now();
    document.getElementById("tapRewardHint").textContent =
      tapState.reward_per_tap;
    renderTapUi();
    if (!tapTicker) tapTicker = setInterval(tickTapEnergy, 1000);
  } catch (e) {
    tapState = null;
    document.getElementById("tapHint").textContent =
      "Не удалось загрузить тапалку. Открой раздел ещё раз.";
    toast(e.message);
  } finally {
    tapLoading = false;
  }
}

function tickTapEnergy() {
  const now = performance.now();
  const elapsed = Math.max(0, (now - tapLastTick) / 1000);
  tapLastTick = now;
  if (!tapState || tapLoading || document.hidden) return;
  tapLocalEnergy = Math.min(
    tapState.energy_max,
    tapLocalEnergy + elapsed / Math.max(1, tapState.regen_seconds)
  );
  renderTapUi();
=======

async function loadTap() {
  try {
    tapState = await api("/api/tap/state");
  } catch (e) {
    toast(e.message);
    return;
  }
  tapLocalEnergy = tapState.energy;
  document.getElementById("tapRewardHint").textContent = tapState.reward_per_tap;
  renderTapUi();
  if (tapTicker) clearInterval(tapTicker);
  tapTicker = setInterval(tickTapEnergy, 1000);
}

function tickTapEnergy() {
  if (!tapState) return;
  if (tapLocalEnergy < tapState.energy_max) {
    tapLocalEnergy = Math.min(tapState.energy_max, tapLocalEnergy + 1 / tapState.regen_seconds);
    renderTapUi();
  }
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
}

function renderTapUi() {
  if (!tapState) return;
<<<<<<< HEAD
  const energy = Math.max(0, Math.floor(tapLocalEnergy));
  document.getElementById("tapEnergyVal").textContent =
    `${energy}/${tapState.energy_max}`;
  document.getElementById("tapEnergyFill").style.width =
    `${Math.min(100, Math.max(0, tapLocalEnergy) /
      Math.max(1, tapState.energy_max) * 100)}%`;
  document.getElementById("tapDayVal").textContent =
    `${tapState.day_points}/${tapState.day_cap}`;
  document.getElementById("tapDayFill").style.width =
    `${Math.min(100, tapState.day_points /
      Math.max(1, tapState.day_cap) * 100)}%`;

  const hint = document.getElementById("tapHint");
  if (!tapCanEarn()) {
    hint.textContent = "На сегодня всё — дневного остатка не хватает на тап.";
  } else if (energy < 1) {
    hint.textContent = "Энергия восстанавливается. Немного подожди ⚡";
  } else {
    hint.textContent = `Тапай Пурио! +${tapState.reward_per_tap} ✦ за тап`;
=======
  const energyShown = Math.floor(tapLocalEnergy);
  document.getElementById("tapEnergyVal").textContent = `${energyShown}/${tapState.energy_max}`;
  document.getElementById("tapEnergyFill").style.width = (tapLocalEnergy / tapState.energy_max * 100) + "%";
  document.getElementById("tapDayVal").textContent = `${tapState.day_points}/${tapState.day_cap}`;
  document.getElementById("tapDayFill").style.width = (Math.min(1, tapState.day_points / tapState.day_cap) * 100) + "%";
  const hint = document.getElementById("tapHint");
  if (tapState.day_points >= tapState.day_cap) {
    hint.textContent = "Дневной лимит тапалки исчерпан — держи VPN активным!";
  } else if (energyShown < 1) {
    hint.textContent = "Энергия закончилась, подожди немного";
  } else {
    hint.textContent = "Тапай дракона!";
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  }
}

function spawnTapFloat(x, y) {
  const stage = document.getElementById("tapStage");
<<<<<<< HEAD
  if (stage.querySelectorAll(".tap-float").length >= 24) return;
  const rect = stage.getBoundingClientRect();
  const span = document.createElement("div");
  span.className = "tap-float";
  span.textContent = "+" + tapState.reward_per_tap;
=======
  const rect = stage.getBoundingClientRect();
  const span = document.createElement("div");
  span.className = "tap-float";
  span.textContent = "+" + (tapState ? tapState.reward_per_tap : 1);
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  span.style.left = (x - rect.left) + "px";
  span.style.top = (y - rect.top) + "px";
  stage.appendChild(span);
  setTimeout(() => span.remove(), 850);
}

<<<<<<< HEAD
function onTapDragon(x, y) {
  if (!tapState || tapLoading) return;
  if (tapLocalEnergy < 1 || !tapCanEarn()) {
    haptic("warning");
    return;
  }

  tapLocalEnergy -= 1;
  tapState.day_points += tapState.reward_per_tap;
  tapQueue += 1;
  spawnTapFloat(x, y);
  haptic("light");

  const dragon = document.getElementById("tapDragon");
  dragon.classList.add("pressed");
  clearTimeout(tapPulseTimer);
  tapPulseTimer = setTimeout(() => dragon.classList.remove("pressed"), 90);
=======
function onTapDragon(clientX, clientY) {
  if (!tapState) return;
  if (tapLocalEnergy < 1) { haptic("warning"); return; }
  if (tapState.day_points >= tapState.day_cap) { haptic("warning"); toast("Дневной лимит тапалки исчерпан 🌙"); return; }

  tapLocalEnergy -= 1;
  tapState.day_points = Math.min(tapState.day_cap, tapState.day_points + tapState.reward_per_tap);
  tapQueue += 1;
  spawnTapFloat(clientX, clientY);
  haptic("light");

  const dragon = document.getElementById("tapDragon");
  dragon.classList.remove("pulse");
  void dragon.offsetWidth;
  dragon.classList.add("pulse");

>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  renderTapUi();
  scheduleTapFlush();
}

function scheduleTapFlush() {
<<<<<<< HEAD
  if (tapFlushTimer || tapFlushing || tapQueue <= 0) return;
  tapFlushTimer = setTimeout(() => {
    tapFlushTimer = null;
    void flushTaps();
  }, 400);
}

async function flushTaps() {
  if (!tapState || tapFlushing || tapQueue <= 0) return;
  clearTimeout(tapFlushTimer);
  tapFlushTimer = null;

  const count = tapQueue;
  tapQueue = 0;
  tapInFlight = count;
  tapFlushing = true;
  let failed = false;

  try {
    const res = await api("/api/tap", {
      method: "POST",
      body: { count },
    });

    // Новые тапы во время запроса остаются в очереди и не теряются
    // при применении ответа сервера.
    const reward = res.reward_per_tap;
    tapState = {
      ...tapState,
      energy: res.energy,
      energy_max: res.energy_max,
      regen_seconds: res.regen_seconds,
      reward_per_tap: reward,
      day_points: Math.min(res.day_cap, res.day_points + tapQueue * reward),
      day_cap: res.day_cap,
    };
    tapLocalEnergy = Math.max(0, res.energy - tapQueue);
    tapLastTick = performance.now();
    document.getElementById("tapRewardHint").textContent = reward;
    document.getElementById("topPointsValue").textContent =
      fmtNum(res.new_balance);
    if (STATE) STATE.points = res.new_balance;
    renderTapUi();
  } catch (e) {
    failed = true;
    // Без серверного idempotency key повторять неопределённый
    // запрос небезопасно. Перечитываем подтверждённое состояние.
    tapQueue = 0;
    tapState = null;
    toast("Связь прервалась. Обновляем подтверждённые сервером очки.");
  } finally {
    tapInFlight = 0;
    tapFlushing = false;
    if (failed) {
      await loadTap();
      try { await loadState(); } catch (e) { toast(e.message); }
    } else if (tapQueue > 0) {
      scheduleTapFlush();
    }
  }
}

const tapStageEl = document.getElementById("tapStage");
tapStageEl.setAttribute("role", "button");
tapStageEl.setAttribute("tabindex", "0");
tapStageEl.setAttribute("aria-label", "Тапнуть дракона Пурио");

tapStageEl.addEventListener("pointerdown", e => {
  if (e.pointerType === "mouse" && e.button !== 0) return;
  e.preventDefault();
  onTapDragon(e.clientX, e.clientY);
});
tapStageEl.addEventListener("keydown", e => {
  if ((e.key !== "Enter" && e.key !== " ") || e.repeat) return;
  e.preventDefault();
  const r = tapStageEl.getBoundingClientRect();
  onTapDragon(r.left + r.width / 2, r.top + r.height / 2);
});
tapStageEl.addEventListener("contextmenu", e => e.preventDefault());

document.addEventListener("visibilitychange", () => {
  tapLastTick = performance.now();
  if (document.hidden) {
    void flushTaps();
  } else if (!tapFlushing && tapQueue === 0) {
    void loadTap();
  }
});
=======
  if (tapFlushTimer) return;
  tapFlushTimer = setTimeout(flushTaps, 700);
}

async function flushTaps() {
  tapFlushTimer = null;
  if (tapQueue <= 0 || tapFlushing) return;
  const count = tapQueue;
  tapQueue = 0;
  tapFlushing = true;
  try {
    const res = await api("/api/tap", { method: "POST", body: { count } });
    tapState.energy = res.energy;
    tapLocalEnergy = res.energy;
    tapState.day_points = res.day_points;
    tapState.day_cap = res.day_cap;
    renderTapUi();
    document.getElementById("topPointsValue").textContent = fmtNum(res.new_balance);
    if (STATE) STATE.points = res.new_balance;
    if (res.capped && res.points_earned === 0) {
      toast("Дневной лимит тапалки исчерпан — вернись завтра или используй VPN 😉");
    }
  } catch (e) {
    toast(e.message);
  } finally {
    tapFlushing = false;
    if (tapQueue > 0) scheduleTapFlush();
  }
}

const tapDragonEl = document.getElementById("tapDragon");
tapDragonEl.addEventListener("click", (e) => onTapDragon(e.clientX, e.clientY));
tapDragonEl.addEventListener("touchstart", (e) => {
  e.preventDefault();
  for (const t of e.changedTouches) onTapDragon(t.clientX, t.clientY);
}, { passive: false });

window.addEventListener("beforeunload", () => { if (tapQueue > 0) flushTaps(); });
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91

// ===================== TOPUP (пополнение баланса) =====================
let topupTxId = null;
let topupPollTimer = null;
let topupPollTries = 0;

function topupShowStep(step) {
  document.getElementById("topupStepInput").style.display = step === "input" ? "" : "none";
  document.getElementById("topupStepWaiting").style.display = step === "waiting" ? "" : "none";
  document.getElementById("topupStepDone").style.display = step === "done" ? "" : "none";
}

function openTopupModal() {
  document.getElementById("topupModal").classList.add("show");
  topupShowStep("input");
}

function closeTopupModal() {
  document.getElementById("topupModal").classList.remove("show");
  clearInterval(topupPollTimer);
  topupPollTimer = null;
}

document.getElementById("topupOpenBtn").addEventListener("click", () => { haptic(); openTopupModal(); });
document.getElementById("topupCloseBtn").addEventListener("click", () => { haptic(); closeTopupModal(); });
document.getElementById("topupBackdrop").addEventListener("click", () => closeTopupModal());
document.getElementById("topupDoneBtn").addEventListener("click", () => closeTopupModal());

betQuickButtons("topupQuick", "topupAmount", () => 100000);
// перегружаем поведение MAX для этой кнопки — тут нет "баланса", это просто быстрые суммы
(function fixTopupQuickButtons() {
  const el = document.getElementById("topupQuick");
  el.innerHTML = "";
  [100, 300, 500, 1000].forEach(v => {
    const b = document.createElement("button");
    b.textContent = v + "₽";
    b.addEventListener("click", () => { document.getElementById("topupAmount").value = v; });
    el.appendChild(b);
  });
})();

document.getElementById("topupSubmitBtn").addEventListener("click", async () => {
  const amount = Number(document.getElementById("topupAmount").value);
  const btn = document.getElementById("topupSubmitBtn");
  if (!amount || amount <= 0) { toast("Укажи сумму пополнения"); return; }
  btn.disabled = true;
  try {
    const res = await api("/api/topup/create", { method: "POST", body: { amount } });
    topupTxId = res.transaction_id;
    if (tg && tg.openLink) tg.openLink(res.pay_url, { try_instant_view: false });
    else window.open(res.pay_url, "_blank");
    topupShowStep("waiting");
    startTopupPolling();
  } catch (e) {
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("topupCheckBtn").addEventListener("click", () => checkTopupStatus());

function startTopupPolling() {
  clearInterval(topupPollTimer);
  topupPollTries = 0;
  topupPollTimer = setInterval(() => checkTopupStatus(), 4000);
}

async function checkTopupStatus() {
  if (!topupTxId) return;
  topupPollTries++;
  try {
    const st = await api("/api/topup/status/" + topupTxId);
    if (st.status === "succeeded") {
      clearInterval(topupPollTimer);
      topupPollTimer = null;
      haptic("success");
      document.getElementById("topupDoneText").textContent =
        `Баланс пополнен! Текущий баланс: ${fmtNum(st.balance_rub)} ₽`;
      topupShowStep("done");
      await loadState();
      await loadProfile();
    } else if (st.status === "canceled") {
      clearInterval(topupPollTimer);
      topupPollTimer = null;
      toast("Платёж отменён");
      topupShowStep("input");
    }
  } catch (e) { /* тихо игнорируем единичные сетевые сбои поллинга */ }
  if (topupPollTries > 90 && topupPollTimer) { // ~6 минут
    clearInterval(topupPollTimer);
    topupPollTimer = null;
  }
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && topupTxId && topupPollTimer) checkTopupStatus();
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

<<<<<<< HEAD

  document.getElementById("refCopyBtn").onclick = async () => {
    const input = document.getElementById("refLinkInput");
    if (!/^https:\/\/t\.me\//i.test(input.value)) {
      toast("Реферальная ссылка пока недоступна");
      return;
    }
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("clipboard unavailable");
      }
      await navigator.clipboard.writeText(input.value);
      haptic("success");
      toast("Ссылка скопирована!");
    } catch (e) {
      input.focus();
      input.select();
      input.setSelectionRange(0, input.value.length);
      toast("Не удалось скопировать автоматически. Скопируй выделенную ссылку.");
    }
  };



=======
  document.getElementById("refCopyBtn").onclick = () => {
    const input = document.getElementById("refLinkInput");
    input.select();
    navigator.clipboard && navigator.clipboard.writeText(input.value).catch(() => {});
    haptic("success");
    toast("Ссылка скопирована!");
  };

>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  renderSkins();
}

function renderSkins() {
  if (!STATE) return;
  const grid = document.getElementById("skinsGrid");
  grid.innerHTML = "";
  STATE.dragon.skins.forEach(s => {
    const div = document.createElement("div");
    div.className = "skin-item" + (s.owned ? " unlocked" : "") + (s.equipped ? " equipped" : "");
    div.style.setProperty("--skin-filter", SKIN_FILTERS[s.code] || "none");
    const statusText = s.owned
      ? (s.equipped ? "надет" : "открыт")
      : `с ${s.min_level} ур.`;
    div.innerHTML = `
      ${s.locked ? `<div class="skin-lock">🔒</div>` : ""}
      <svg viewBox="0 0 200 200"><use href="#dragon-svg"/></svg>
      <div class="skin-name">${s.name}</div>
      <div class="skin-level-badge">${statusText}</div>
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

// ===================== ОБМЕН ОЧКОВ НА РУБЛИ =====================
let exchangeRate = 1000;
let exchangeMinPoints = 10000;

async function loadExchangeInfo() {
  try {
    const info = await api("/api/exchange/info");
    exchangeRate = info.rate;
    exchangeMinPoints = info.min_points;
    document.getElementById("exchangeRateHint").textContent =
      `Курс: ${fmtNum(exchangeRate)} ✦ = 1 ₽ (мин. сумма — ${fmtNum(exchangeMinPoints)} ✦)`;
    updateExchangePreview();
  } catch (e) { /* тихо игнорируем */ }
}

function updateExchangePreview() {
  const points = Number(document.getElementById("exchangePoints").value) || 0;
  const rub = (points / exchangeRate).toFixed(2);
  document.getElementById("exchangePreview").textContent = `Получишь: ${rub} ₽`;
}

document.getElementById("exchangePoints").addEventListener("input", updateExchangePreview);

(function initExchangeQuickButtons() {
  const el = document.getElementById("exchangeQuick");
  el.innerHTML = "";
  [10000, 25000, 50000, "MAX"].forEach(v => {
    const b = document.createElement("button");
    b.textContent = v === "MAX" ? "MAX" : fmtNum(v);
    b.addEventListener("click", () => {
      const input = document.getElementById("exchangePoints");
      input.value = v === "MAX" ? Math.max(0, Math.floor(STATE ? STATE.points : 0)) : v;
      updateExchangePreview();
    });
    el.appendChild(b);
  });
})();

document.getElementById("exchangeSubmitBtn").addEventListener("click", async () => {
  const points = Number(document.getElementById("exchangePoints").value);
  const btn = document.getElementById("exchangeSubmitBtn");
  if (!points || points <= 0) { toast("Укажи количество очков"); return; }
  btn.disabled = true;
  try {
    const res = await api("/api/exchange", { method: "POST", body: { points } });
    haptic("success");
    toast(`Обменяно ${fmtNum(res.points_spent)} ✦ → +${res.rub_credited} ₽`);
    document.getElementById("exchangePoints").value = exchangeMinPoints;
    updateExchangePreview();
    await loadState();
    await loadProfile();
  } catch (e) {
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

// ===================== PURIO SHOP =====================
const RARITY_LABEL = { common: "Обычный", rare: "Редкий", epic: "Эпик", legendary: "Легендарный" };
const TYPE_LABEL = {
  clothing: "👕 Одежда", frame: "🏷️ Рамки", effect: "✨ Эффекты",
  nickname_color: "🎨 Ник", badge: "💎 Значки", animation: "🔥 Анимация", title: "🏆 Титулы",
};
const BOX_LABEL = {
  common: { icon: "📦", name: "Обычный кейс" },
  rare: { icon: "🎁", name: "Редкий кейс" },
  epic: { icon: "🏆", name: "Эпический кейс" },
};

let SHOP_CATALOG = null;
let SHOP_ACTIVE_TYPE = "clothing";
let BOOSTER_CATALOG = null;
let BOX_TIERS = null;

function showRewardModal({ icon = "🎁", title = "Награда", text = "", sub = "" } = {}) {
  document.getElementById("rewardIcon").textContent = icon;
  document.getElementById("rewardTitle").textContent = title;
  document.getElementById("rewardText").textContent = text;
  document.getElementById("rewardSub").textContent = sub;
  document.getElementById("rewardModal").classList.add("show");
}
document.getElementById("rewardCloseBtn").addEventListener("click", () => {
  document.getElementById("rewardModal").classList.remove("show");
});
document.getElementById("rewardOkBtn").addEventListener("click", () => {
  document.getElementById("rewardModal").classList.remove("show");
});
document.getElementById("rewardBackdrop").addEventListener("click", () => {
  document.getElementById("rewardModal").classList.remove("show");
});

function boxRewardModal(kind, res) {
  if (kind === "points") {
    showRewardModal({
      icon: res.jackpot ? "🎉" : "✦",
      title: res.jackpot ? "Джекпот!" : "Награда",
      text: `+${fmtNum(res.amount)} Purio Points`,
      sub: res.jackpot ? "Невероятная удача!" : "",
    });
  } else if (kind === "item") {
    const item = res.item || {};
    showRewardModal({
      icon: item.icon || "🎁",
      title: "Новый предмет!",
      text: item.name || res.item_code,
      sub: RARITY_LABEL[item.rarity] || "",
    });
  } else if (kind === "booster") {
    const b = BOOSTER_CATALOG ? BOOSTER_CATALOG[res.booster_code] : null;
    showRewardModal({
      icon: "🪙",
      title: "XP-бустер!",
      text: b ? `x${b.multiplier} на ${Math.round(b.duration_seconds / 3600)} ч` : res.booster_code,
      sub: "Автоматически активирован",
    });
  }
}

// ---------- Cosmetics tab ----------

function renderShopTypeFilters() {
  const el = document.getElementById("shopTypeFilters");
  const types = Object.keys(TYPE_LABEL);
  el.innerHTML = "";
  types.forEach(t => {
    const b = document.createElement("button");
    b.textContent = TYPE_LABEL[t];
    b.className = t === SHOP_ACTIVE_TYPE ? "active" : "";
    b.addEventListener("click", () => { haptic(); SHOP_ACTIVE_TYPE = t; renderShopGrid(); renderShopTypeFilters(); });
    el.appendChild(b);
  });
}

function renderShopGrid() {
  if (!SHOP_CATALOG) return;
  const grid = document.getElementById("shopGrid");
  grid.innerHTML = "";
  const week = SHOP_CATALOG.rotating_this_week || [];
  document.getElementById("rotationCard").style.display = week.length ? "" : "none";

  const items = SHOP_CATALOG.items.filter(it => it.type === SHOP_ACTIVE_TYPE);
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = `shop-item rarity-${item.rarity}`;

    let badgeHtml = "";
    if (item.owned) badgeHtml = `<div class="shop-item-badge owned">Есть</div>`;
    else if (item.rotating) badgeHtml = `<div class="shop-item-badge exclusive">Неделя</div>`;
    else if (item.limited) badgeHtml = `<div class="shop-item-badge limited">Лимит</div>`;

    let priceHtml = item.price != null
      ? `<div class="shop-item-price">${fmtNum(item.price)} ✦</div>`
      : `<div class="shop-item-price muted">${item.achievement ? "Достижение" : "Из бокса"}</div>`;

    let stockHtml = "";
    if (item.limited && item.stock_remaining != null) {
      stockHtml = `<div class="shop-item-stock">Осталось: ${fmtNum(item.stock_remaining)}</div>`;
    }

    let btnHtml;
    const equipped = SHOP_CATALOG.equipped_state && SHOP_CATALOG.equipped_state[item.type] === item.code;
    if (item.type === "badge") {
      btnHtml = item.owned
        ? `<button class="shop-item-btn" data-action="equip-badge" data-code="${item.code}">Надеть значок</button>`
        : (item.purchasable
            ? `<button class="shop-item-btn buy" data-action="buy" data-code="${item.code}">Купить</button>`
            : `<button class="shop-item-btn" disabled>Недоступно</button>`);
    } else if (item.owned) {
      btnHtml = equipped
        ? `<button class="shop-item-btn equipped" data-action="unequip" data-type="${item.type}">Надето ✓</button>`
        : `<button class="shop-item-btn" data-action="equip" data-type="${item.type}" data-code="${item.code}">Надеть</button>`;
    } else if (item.purchasable) {
      btnHtml = `<button class="shop-item-btn buy" data-action="buy" data-code="${item.code}">Купить</button>`;
    } else {
      btnHtml = `<button class="shop-item-btn" disabled>Недоступно</button>`;
    }

    card.innerHTML = `
      ${badgeHtml}
      <div class="shop-item-icon">${item.icon}</div>
      <div class="shop-item-name">${item.name}</div>
      <div class="shop-item-desc">${item.desc}</div>
      ${priceHtml}
      ${stockHtml}
      ${btnHtml}
    `;
    grid.appendChild(card);
  });

  grid.querySelectorAll("[data-action]").forEach(btn => {
<<<<<<< HEAD
    btn.addEventListener("click", async () => {
      if (btn.disabled) return;
      btn.disabled = true;
      try {
        await handleShopItemAction(btn.dataset);
      } finally {
        btn.disabled = false;
      }
    });
=======
    btn.addEventListener("click", () => handleShopItemAction(btn.dataset));
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
  });
}

async function handleShopItemAction(ds) {
  haptic();
  try {
    if (ds.action === "buy") {
      const res = await api("/api/shop/buy", { method: "POST", body: { item_code: ds.code } });
      toast(`Куплено! -${fmtNum(res.price)} ✦`);
      haptic("success");
    } else if (ds.action === "equip") {
      await api("/api/shop/equip", { method: "POST", body: { type: ds.type, item_code: ds.code } });
      toast("Экипировано");
    } else if (ds.action === "unequip") {
      await api("/api/shop/equip", { method: "POST", body: { type: ds.type, item_code: "" } });
      toast("Снято");
    } else if (ds.action === "equip-badge") {
      await api("/api/shop/equip-badge", { method: "POST", body: { slot: 0, badge_code: ds.code } });
      toast("Значок надет (слот 1)");
    }
<<<<<<< HEAD
    await loadState();
    await loadShop();
=======
    await loadShop();
    await loadState();
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
    await loadProfile();
  } catch (e) {
    haptic("error");
    toast(e.message);
  }
}

// ---------- Boxes tab ----------

function renderMysteryBoxes() {
  if (!BOX_TIERS) return;
  const grid = document.getElementById("mysteryBoxGrid");
  grid.innerHTML = "";
  Object.keys(BOX_TIERS).forEach(tier => {
    const cfg = BOX_TIERS[tier];
    const meta = BOX_LABEL[tier] || { icon: "📦", name: tier };
    const card = document.createElement("div");
    card.className = "box-card";
    card.innerHTML = `
      <div class="box-card-icon">${meta.icon}</div>
      <div class="box-card-body">
        <div class="box-card-title">${meta.name}</div>
        <div class="box-card-desc">${fmtNum(cfg.price)} ✦ за открытие</div>
        <div class="box-card-limit">Лимит: ${cfg.daily_limit} в день</div>
      </div>
      <button class="box-card-btn" data-tier="${tier}">Открыть</button>
    `;
    grid.appendChild(card);
  });
  grid.querySelectorAll("[data-tier]").forEach(btn => {
    btn.addEventListener("click", async () => {
      haptic();
      btn.disabled = true;
      try {
        const res = await api("/api/box/open", { method: "POST", body: { tier: btn.dataset.tier } });
        haptic("success");
        boxRewardModal(res.kind, res);
        await loadState();
        await loadProfile();
      } catch (e) {
        haptic("error");
        toast(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

document.getElementById("dailyCaseBtn").addEventListener("click", async () => {
  haptic();
  const btn = document.getElementById("dailyCaseBtn");
  btn.disabled = true;
  try {
    const res = await api("/api/box/daily-claim", { method: "POST" });
    haptic("success");
    boxRewardModal("points", res);
    await loadState();
  } catch (e) {
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

// ---------- Wheel tab ----------

async function refreshWheelUI() {
  try {
    const state = await api("/api/wheel/state");
    document.getElementById("wheelCostLabel").textContent = fmtNum(state.spin_cost);
    const freeBtn = document.getElementById("wheelFreeSpinBtn");
    if (state.free_spin_available) {
      freeBtn.style.display = "";
      document.getElementById("wheelFreeHint").textContent = "Бесплатный спин доступен раз в сутки!";
    } else {
      freeBtn.style.display = "none";
      document.getElementById("wheelFreeHint").textContent = "Бесплатный спин уже использован сегодня — вернётся завтра.";
    }
  } catch (e) { /* тихо */ }
}

async function doWheelSpin(useFree) {
  haptic();
  const visual = document.getElementById("wheelVisual");
  visual.classList.add("spinning");
  document.getElementById("wheelFreeSpinBtn").disabled = true;
  document.getElementById("wheelPaidSpinBtn").disabled = true;
  try {
    const res = await api("/api/wheel/spin", { method: "POST", body: { use_free: useFree } });
    setTimeout(() => {
      visual.classList.remove("spinning");
      const won = res.multiplier > 1;
      const flat = res.multiplier === 1;
      document.getElementById("wheelResult").textContent =
        `Выпало x${res.multiplier} → ${won ? "+" : (flat ? "" : "")}${fmtNum(res.payout)} ✦`;
      haptic(won ? "success" : (flat ? "light" : "error"));
    }, 900);
    await loadState();
    await refreshWheelUI();
  } catch (e) {
    visual.classList.remove("spinning");
    haptic("error");
    toast(e.message);
  } finally {
    document.getElementById("wheelFreeSpinBtn").disabled = false;
    document.getElementById("wheelPaidSpinBtn").disabled = false;
  }
}
document.getElementById("wheelFreeSpinBtn").addEventListener("click", () => doWheelSpin(true));
document.getElementById("wheelPaidSpinBtn").addEventListener("click", () => doWheelSpin(false));

// ---------- Boosters tab ----------

function renderBoosterGrid() {
  if (!BOOSTER_CATALOG) return;
  const grid = document.getElementById("boosterGrid");
  grid.innerHTML = "";
  Object.keys(BOOSTER_CATALOG).forEach(code => {
    const cfg = BOOSTER_CATALOG[code];
    const hours = Math.round(cfg.duration_seconds / 3600);
    const card = document.createElement("div");
    card.className = "box-card";
    card.innerHTML = `
      <div class="box-card-icon">🪙</div>
      <div class="box-card-body">
        <div class="box-card-title">XP x${cfg.multiplier} — ${hours} ч</div>
        <div class="box-card-desc">${fmtNum(cfg.price)} ✦</div>
      </div>
      <button class="box-card-btn" data-code="${code}">Купить</button>
    `;
    grid.appendChild(card);
  });
  grid.querySelectorAll("[data-code]").forEach(btn => {
    btn.addEventListener("click", async () => {
      haptic();
      btn.disabled = true;
      try {
        const res = await api("/api/booster/buy", { method: "POST", body: { code: btn.dataset.code } });
        haptic("success");
        toast("Бустер активирован!");
        await loadState();
        await refreshActiveBoosterUI();
      } catch (e) {
        haptic("error");
        toast(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

async function refreshActiveBoosterUI() {
  if (!STATE) return;
  const card = document.getElementById("activeBoosterCard");
  const booster = STATE.active_booster;
  if (booster && booster.expires_at * 1000 > Date.now()) {
    const minsLeft = Math.max(1, Math.round((booster.expires_at * 1000 - Date.now()) / 60000));
    document.getElementById("activeBoosterText").textContent =
      `XP x${booster.multiplier} — осталось ~${minsLeft} мин`;
    card.style.display = "";
  } else {
    card.style.display = "none";
  }
}

document.getElementById("buyShieldBtn").addEventListener("click", async () => {
  haptic();
  const btn = document.getElementById("buyShieldBtn");
  btn.disabled = true;
  try {
    const res = await api("/api/streak/shield/buy", { method: "POST" });
    haptic("success");
    toast("Защита стрика куплена!");
    document.getElementById("shieldCount").textContent = res.streak_shields;
    await loadState();
  } catch (e) {
    haptic("error");
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
});

// ---------- Shop sub-tabs switching ----------

document.querySelectorAll("[data-shoptab]").forEach(btn => {
  btn.addEventListener("click", () => {
    haptic();
    document.querySelectorAll("[data-shoptab]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll("#page-shop .game-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("shoptab-" + btn.dataset.shoptab).classList.add("active");
    if (btn.dataset.shoptab === "wheel") refreshWheelUI();
  });
});

// ---------- Main loader ----------

async function loadShop() {
  try {
    const [catalog, boxCatalog, boosterCatalog] = await Promise.all([
      api("/api/shop"),
      api("/api/box/catalog"),
      api("/api/booster/catalog"),
    ]);
    SHOP_CATALOG = catalog;
    SHOP_CATALOG.equipped_state = STATE && STATE.cosmetics ? STATE.cosmetics.equipped : {};
    BOX_TIERS = boxCatalog.tiers;
    BOOSTER_CATALOG = boosterCatalog.boosters;

    renderShopTypeFilters();
    renderShopGrid();
    renderMysteryBoxes();
    renderBoosterGrid();

    if (STATE) {
      document.getElementById("shieldCount").textContent = (STATE.streak && STATE.streak.shields) || 0;
      const shieldBtnLabel = `🛡️ Купить защиту стрика`;
      document.getElementById("buyShieldBtn").textContent = shieldBtnLabel;
      refreshActiveBoosterUI();
    }
  } catch (e) {
    toast(e.message || "Не удалось загрузить магазин");
  }
}


(async function init() {
  try {
    await api("/api/auth", { method: "POST" });
  } catch (e) {
    console.error("auth failed", e);
    toast("Не удалось авторизоваться. Открой приложение через кнопку в боте.");
    return;
  }
<<<<<<< HEAD
  try {
    await loadState();
    await loadExchangeInfo();
    await loadTap();
  } catch (e) {
    console.error("initial load failed", e);
    toast("Не удалось загрузить приложение. Закрой и открой его ещё раз.");
  }
=======
  await loadState();
  await loadExchangeInfo();
>>>>>>> df6d2d6e09f4f0a797a32b4b9b2236764894ba91
})();
