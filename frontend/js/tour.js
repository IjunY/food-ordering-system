// 使用教學：第一次登入時帶使用者照順序把功能用過一遍。
// - 顧客（點餐的學生）和店家各一套流程；平台管理員不用。
// - 教學進行中是「練習模式」（store.js 的 inPractice）：下單、付款、接單都走假資料，不會送到真的店家。
// - 每一步指著畫面上的一個元素（反白＋說明框）。要使用者自己操作的步驟，做完會自動跳下一步；
//   只看說明的步驟按「下一步」。
// - 看完或略過就記在這台瀏覽器（tourDone），之後可以在帳號頁／店家後台上方的「教學」重看。
import { t, getLang } from './i18n.js';
import { actions, onRender, currentPath, navigate, toast } from './router.js';
import { session, cart, tourState, tourDone, homeOf } from './store.js';
import { addPracticeOrder } from './mock/api.js';
import { esc } from './components.js';

const is = (re) => () => re.test(currentPath());
const exists = (sel) => () => !!document.querySelector(sel);

// 每一步：
//   key     字串 tour.<流程>.<key>.title / .body
//   at      這一步在哪些頁面成立（不在這些頁面就顯示「回到教學」）
//   target  要指的元素（字串或函式）；沒有就是置中的說明卡
//   done    使用者做完這一步的條件（成立就自動往下）；沒有就顯示「下一步」
//   go      按「下一步」時順便換到這一頁
const CUSTOMER = [
  { key: 'welcome', at: is(/^home$/) },
  { key: 'areas', at: is(/^home$/), target: '.tabs--area' },
  { key: 'stall', at: is(/^home$/), target: '.scard:not(.closed)', done: is(/^r-/) },
  { key: 'categories', at: is(/^r-/), target: '.tabs--sticky' },
  { key: 'item', at: is(/^r-/), target: '.icard:not(.out)', done: is(/^item-/) },
  { key: 'options', at: is(/^item-/), target: '.itempage .ogroup' },
  { key: 'add', at: is(/^item-/), target: '[data-action="add-to-cart"]', done: () => cart.get().items.length > 0 },
  { key: 'to_cart', at: is(/^r-/), target: '.dock .cta', done: is(/^cart$/) },
  { key: 'lines', at: is(/^cart$/), target: '.linelist' },
  { key: 'pickup', at: is(/^cart$/), target: 'main fieldset.ogroup' },
  { key: 'checkout', at: is(/^cart$/), target: '[data-action="checkout"]', done: is(/^pay-/) },
  { key: 'method', at: is(/^pay-/), target: '.opts' },
  { key: 'pay', at: is(/^pay-/), target: '[data-action="pay"]', done: is(/^paid-/) },
  { key: 'pass', at: is(/^paid-/), target: '.pass' },
  { key: 'track', at: is(/^paid-/), target: '.dock .cta', done: is(/^order-/) },
  { key: 'progress', at: is(/^order-/), target: '.pass .legs', go: 'orders' },
  { key: 'orders', at: is(/^orders$/), target: '.main .stack, .main .histlist' },
  { key: 'profile_tab', at: is(/^orders$/), target: '.tabbar a[href="#profile"]', done: is(/^profile$/) },
  { key: 'lang', at: is(/^profile$/), target: '.acct .tog' },
  { key: 'replay', at: is(/^profile$/), target: '.acct [data-action="tour-replay"]' },
  { key: 'finish', at: is(/^profile$/) },
];

// 店家：先在看板上把一張練習單從接單做到取餐，再逛菜單管理、店家設定、營收報表
const ticket = (to) => () => {
  const oid = tourState.get()?.oid;
  return oid ? `[data-action="order-status"][data-id="${oid}"][data-to="${to}"]` : null;
};
// 反白整張練習單（說明框才不會蓋住取餐號）
const wholeTicket = (to) => () => { const sel = ticket(to)(); return sel ? `.kt:has(${sel})` : null; };
const ticketIs = (to) => () => { const sel = ticket(to)(); return !!sel && !!document.querySelector(sel); };
// 練習單出現過、現在不見了（按了已取餐，或被拒單）。一定要先出現過：
// 看板可能還是開始教學前的舊畫面，那時候本來就沒有練習單
const ticketGone = () => {
  const s = tourState.get();
  return !!s?.seen && currentPath() === 'admin-orders' && !!document.querySelector('.rails') && !document.querySelector(`[data-id="${s.oid}"]`);
};
const STAFF = [
  { key: 'welcome', at: is(/^admin-orders$/) },
  { key: 'board', at: is(/^admin-orders$/), target: '.rails' },
  { key: 'accepting', at: is(/^admin-orders$/), target: '.accepting' },
  { key: 'accept', at: is(/^admin-orders$/), target: wholeTicket('preparing'), done: () => ticketIs('ready')() || ticketGone() },
  { key: 'ready', at: is(/^admin-orders$/), target: wholeTicket('ready'), done: () => ticketIs('picked_up')() || ticketGone() },
  { key: 'picked', at: is(/^admin-orders$/), target: wholeTicket('picked_up'), done: ticketGone },
  { key: 'menu_tab', at: is(/^admin-orders$/), target: '.admin-nav a[href="#admin-menu"]', done: is(/^admin-menu$/) },
  { key: 'menu_table', at: is(/^admin-menu$/), target: '.table-wrap' },
  { key: 'menu_new', at: is(/^admin-menu$/), target: '.page-head [data-action="menu-new"]' },
  { key: 'settings_tab', at: is(/^admin-menu$/), target: '.admin-nav a[href="#admin-settings"]', done: is(/^admin-settings$/) },
  { key: 'settings', at: is(/^admin-settings$/), target: '.settings' },
  { key: 'reports_tab', at: is(/^admin-settings$/), target: '.admin-nav a[href="#admin-reports"]', done: is(/^admin-reports$/) },
  { key: 'reports', at: is(/^admin-reports$/), target: '.figures' },
  { key: 'finish', at: is(/^admin-reports$/) },
];
const FLOWS = { customer: CUSTOMER, staff: STAFF };
const flowName = { customer: 'c', staff: 's' };

const hasTour = (user) => !!user && user.role in FLOWS;

// ======================= 開始／結束 =======================
// 登入、註冊成功後呼叫：這個帳號在這台瀏覽器還沒看過教學就開始
export async function maybeStartTour(user) {
  if (hasTour(user) && !tourDone.has(user)) await startTour(user);
}

export async function startTour(user) {
  const s = { role: user.role, uid: user.student_id ?? user.id, i: 0, path: homeOf(user.role), oid: null };
  tourState.set(s); // 先進練習模式，後面的假資料操作才算數
  if (user.role === 'customer') cart.clear();
  if (user.role === 'staff') {
    const o = await addPracticeOrder();
    tourState.set({ ...s, oid: o.id, no: o.pickup_number });
  }
  shownStep = -1;
  sync();
}

function endTour({ skipped = false } = {}) {
  const s = tourState.get();
  const user = session.get()?.user;
  tourState.clear();
  if (user) tourDone.set(user);
  if (s?.role === 'customer') cart.clear(); // 練習時放進購物車的東西不留到真的點餐
  hide();
  if (skipped) toast(t(s?.role === 'staff' ? 'tour.skipped_staff' : 'tour.skipped'));
  if (user) navigate(homeOf(user.role));
}

actions['tour-replay'] = async () => {
  const user = session.get()?.user;
  if (!hasTour(user)) return;
  await startTour(user);
  navigate(homeOf(user.role));
};
actions['tour-next'] = () => {
  const s = tourState.get();
  if (!s) return;
  const step = FLOWS[s.role][s.i];
  if (s.i >= FLOWS[s.role].length - 1) { endTour(); return; }
  tourState.set({ ...s, i: s.i + 1 });
  if (step.go) navigate(step.go);
  sync();
};
actions['tour-skip'] = () => endTour({ skipped: true });
actions['tour-return'] = () => {
  const s = tourState.get();
  if (s) navigate(s.path);
};

// ======================= 畫面 =======================
let root = null;
let shownStep = -1;
function layer() {
  if (!root) {
    root = document.createElement('div');
    root.id = 'tour-root';
    document.body.appendChild(root);
  }
  return root;
}
function hide() {
  drawnKey = '';
  if (root) root.innerHTML = '';
  document.body.classList.remove('touring');
}

const resolve = (target) => (typeof target === 'function' ? target() : target);

// 檢查進度並把說明框畫到正確的位置。每次換頁、重畫、捲動、點擊後都會跑。
export function sync() {
  const s = tourState.get();
  if (!s) { hide(); return; }
  const user = session.get()?.user;
  // 登出了，或換成別的帳號：教學作廢（下次這個帳號登入會重新開始）
  if (!user || (user.student_id ?? user.id) !== s.uid || user.role !== s.role) { tourState.clear(); hide(); return; }
  const flow = FLOWS[s.role];
  if (s.oid && !s.seen && document.querySelector(`[data-id="${s.oid}"]`)) tourState.set({ ...s, seen: true });

  // 做完的步驟往下跳（一次可能跳好幾步，例如加入購物車後直接回到攤位頁）
  let i = s.i;
  while (i < flow.length - 1 && flow[i].done && flow[i].done()) i++;
  if (i !== s.i) tourState.set({ ...tourState.get(), i });
  const step = flow[i];
  const onPage = step.at();
  if (onPage && s.path !== currentPath()) tourState.set({ ...tourState.get(), path: currentPath() });

  document.body.classList.add('touring');
  const el = onPage && step.target ? document.querySelector(resolve(step.target)) : null;
  if (onPage && el && shownStep !== i) {
    el.scrollIntoView({ block: 'center', behavior: shownStep === -1 ? 'auto' : 'smooth' });
  }
  const changed = shownStep !== i;
  if (onPage) shownStep = i;
  draw({ s: tourState.get(), step, i, total: flow.length, el, onPage, changed });
}

let drawnKey = '';
function draw({ s, step, i, total, el, onPage, changed }) {
  const host = layer();
  const base = `tour.${flowName[s.role]}.${step.key}`;
  const vars = { no: s.no ?? '' };
  const last = i === total - 1;
  const mode = !onPage ? 'off' : step.target && el ? 'point' : 'center';
  // 內容只在換步驟、換語言、換模式時重建；其他時候只移動位置（不然焦點會一直被洗掉）
  const key = [s.role, i, mode, getLang()].join('|');
  if (key !== drawnKey) {
    drawnKey = key;
    if (mode === 'off') {
      // 不在這一步的頁面：底部一條「回到教學」
      host.innerHTML = `<div class="tour-off" role="status">
        <span>${esc(t('tour.off_track', { title: t(base + '.title', vars) }))}</span>
        <button type="button" class="btn btn--sm btn--primary" data-action="tour-return">${esc(t('tour.return'))}</button>
        <button type="button" class="btn btn--sm btn--text" data-action="tour-skip">${esc(t('tour.skip'))}</button>
      </div>`;
    } else {
      // 要使用者自己操作的步驟不放「下一步」；但元素找不到時給一顆，免得卡住
      const needsNext = !step.done || mode === 'center';
      host.innerHTML = `${mode === 'point' ? '<div class="tour-hole"></div>' : `<div class="tour-dim${step.target ? '' : ' tour-dim--block'}"></div>`}
        <div class="tour-card${mode === 'center' ? ' tour-card--center' : ''}" role="dialog" aria-modal="false" aria-labelledby="tour-title" aria-describedby="tour-body">
          <div class="tour-card__head"><span class="tour-card__n num">${i + 1} / ${total}</span>${i === 0 ? `<span class="tour-card__tag">${esc(t('tour.practice_tag'))}</span>` : ''}</div>
          <h2 id="tour-title" tabindex="-1">${esc(t(base + '.title', vars))}</h2>
          <p id="tour-body">${esc(t(base + '.body', vars))}</p>
          <div class="tour-card__foot">
            ${last ? '' : `<button type="button" class="btn btn--sm btn--text" data-action="tour-skip">${esc(t('tour.skip'))}</button>`}
            <span class="grow"></span>
            ${needsNext ? `<button type="button" class="btn btn--sm btn--primary" data-action="tour-next">${esc(t(last ? 'tour.finish' : i === 0 ? 'tour.start' : 'tour.next'))}</button>` : `<span class="tour-card__do">${esc(t('tour.do_it'))}</span>`}
          </div>
        </div>`;
    }
    // 換步驟時讓螢幕報讀唸出新的說明：有「下一步」就把焦點放在那顆按鈕，否則放在標題
    if (changed && mode !== 'off') (host.querySelector('[data-action="tour-next"]') || host.querySelector('#tour-title'))?.focus({ preventScroll: true });
  }
  if (mode === 'point') place(host, el);
}

// 反白框對準元素；說明框放在元素上方或下方空間比較大的那邊，兩邊都放不下（元素很高）就貼在畫面底部
function place(host, el) {
  const hole = host.querySelector('.tour-hole');
  const card = host.querySelector('.tour-card');
  if (!hole || !card) return;
  const r = el.getBoundingClientRect();
  const vw = document.documentElement.clientWidth;
  const vh = window.innerHeight;
  const pad = 6;
  Object.assign(hole.style, { left: `${r.left - pad}px`, top: `${r.top - pad}px`, width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px` });
  const w = Math.min(360, vw - 32);
  const h = card.offsetHeight || 180;
  const left = Math.max(16, Math.min(vw - w - 16, r.left + r.width / 2 - w / 2));
  const below = vh - r.bottom - pad - 10;
  const above = r.top - pad - 10;
  const s = { width: `${w}px`, left: `${left}px`, top: '', bottom: '' };
  if (below >= h + 16 && below >= above) s.top = `${r.bottom + pad + 10}px`;
  else if (above >= h + 16) s.bottom = `${vh - r.top + pad + 10}px`;
  else { s.left = `${(vw - w) / 2}px`; s.bottom = '16px'; }
  Object.assign(card.style, s);
}

// 畫面重畫、捲動、縮放、點擊後重新對準
onRender(sync);
let raf = 0;
const later = () => { if (!tourState.get()) return; cancelAnimationFrame(raf); raf = requestAnimationFrame(sync); };
window.addEventListener('scroll', later, { passive: true });
window.addEventListener('resize', later);
document.addEventListener('click', () => setTimeout(later, 60));
// 平滑捲動、字型載入、圖片撐開版面時元素會移動，進行中每 0.5 秒再對一次
setInterval(later, 500);
