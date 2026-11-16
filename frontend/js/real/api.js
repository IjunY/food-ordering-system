// 真後端（FastAPI，app/）的轉接層：呼叫 /api，再把回傳轉成畫面用的欄位（和 mock/api.js 同一套）。
//
// 目前接上真後端的：登入／註冊／我的資料、下單、訂單查詢、店家接單看板改狀態。
// 還沒接的（餐廳列表、菜單、等候時間、付款、店家設定與菜單管理、報表、平台管理）照舊用 mock/api.js。
//
// 菜單仍顯示前端的示範資料，所以下單時要把示範品項換成資料庫裡的品項編號：
// 兩邊用「餐廳中文名＋品項中文名」對應（scripts/seed_demo.py 照 mock/data.js 灌進資料庫）。
// 付款仍是模擬的，付款紀錄只存在這台瀏覽器（paid_orders）。
import { getLang } from '../i18n.js';
import { session, read, write } from '../store.js';
import { SEED_RESTAURANTS, SEED_MENUS, USERS } from '../mock/data.js';

export const API_BASE = '/api';

const loc = (v) => (v && typeof v === 'object' && 'zh' in v ? v[getLang()] ?? v.zh : v);

// 後端錯誤 → 讀得懂的訊息。422（欄位格式不對）的 detail 是陣列
function errorMessage(body, res) {
  const d = body?.detail;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(-1)[0] ?? ''} ${e.msg}`.trim()).join('；');
  return d || `${res.status} ${res.statusText}`;
}

async function http(method, path, body) {
  const token = session.get()?.access_token;
  const res = await fetch(API_BASE + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Accept-Language': getLang() === 'en' ? 'en' : 'zh-TW',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401 && token) {
    // 登入過期：清掉登入狀態回登入頁
    session.clear();
    location.hash = 'login';
  }
  if (!res.ok) throw new Error(errorMessage(await res.json().catch(() => null), res));
  return res.status === 204 ? null : res.json();
}

// 後端是否在線：/api/health 回 {status:'ok'} 才算
export async function isAvailable() {
  try {
    const res = await fetch(API_BASE + '/health', { headers: { Accept: 'application/json' } });
    return res.ok && (await res.json()).status === 'ok';
  } catch {
    return false;
  }
}

// ---------- 示範菜單 ⇄ 資料庫品項 ----------
const restaurantByVendor = (vendor) => SEED_RESTAURANTS.find((r) => r.name.zh === vendor) ?? null;

let catalog = null; // { byDbId: Map<dbId, {restaurant, item, row}>, byMockId: Map<"rid/iid", dbId> }
async function getCatalog(force = false) {
  if (catalog && !force) return catalog;
  const rows = await http('GET', '/menu-items');
  const byDbId = new Map();
  const byMockId = new Map();
  for (const row of rows) {
    const restaurant = restaurantByVendor(row.vendor);
    const item = restaurant ? SEED_MENUS[restaurant.id]?.items.find((i) => i.name.zh === row.item_name) : null;
    byDbId.set(row.id, { restaurant, item, row });
    if (item) byMockId.set(`${restaurant.id}/${item.id}`, row.id);
  }
  catalog = { byDbId, byMockId };
  return catalog;
}

// ---------- 狀態對照 ----------
// 後端：confirming → preparing → ready → picked up（另有 cancelled）
// 畫面：pending_payment → paid → accepted → preparing → ready → picked_up
const toBackendStatus = (s) => (s === 'picked_up' ? 'picked up' : s === 'accepted' ? 'preparing' : s);

const paidOrders = {
  get: () => read('paid_orders', {}),
  set: (id, method) => write('paid_orders', { ...paidOrders.get(), [id]: method }),
};

// 後端的訂單 → 畫面的訂單。view = 'customer'（自己的單）或 'staff'（店家看板）
async function toOrder(o, view = 'customer') {
  const { byDbId } = await getCatalog();
  const first = byDbId.get(o.items[0]?.item_id);
  const r = first?.restaurant ?? restaurantByVendor(o.vendor);
  const id = String(o.id);
  const method = view === 'customer' ? paidOrders.get()[id] ?? null : null;

  let status = o.status === 'picked up' ? 'picked_up' : o.status;
  if (status === 'confirming') status = view === 'staff' || method ? 'paid' : 'pending_payment';

  const prep = Math.max(5, ...o.items.map((i) => byDbId.get(i.item_id)?.item?.prep_minutes ?? 0));
  const eta = new Date(new Date(o.created_at).getTime() + (prep + (r?.base_wait ?? 0)) * 60000).toISOString();
  const history = status === 'pending_payment' || status === 'cancelled' ? [] : [{ status: 'paid', at: o.created_at }];

  return {
    id,
    pickup_number: 'A' + String(o.id).padStart(3, '0'),
    restaurant_id: r?.id ?? null,
    restaurant_name: r ? loc(r.name) : o.vendor,
    restaurant_location: r ? loc(r.location) : '',
    status,
    payment_method: view === 'staff' ? 'mock' : method,
    payment_status: view === 'staff' || (method && method !== 'cash_on_pickup') ? 'paid' : 'unpaid',
    total: o.total,
    note: null,
    pickup_type: 'asap',
    pickup_time: null,
    items: o.items.map((i) => {
      const hit = byDbId.get(i.item_id);
      return {
        menu_item_id: hit?.item?.id ?? String(i.item_id),
        name: hit?.item ? loc(hit.item.name) : i.item_name,
        qty: i.quantity,
        unit_price: i.unit_price,
        subtotal: i.subtotal,
        options_label: null,
        option_ids: [],
      };
    }),
    created_at: o.created_at,
    estimated_ready_at: eta,
    queue_ahead: 0,
    status_history: history,
  };
}

// ======================= 登入 =======================
const toSessionUser = (u) => ({
  id: u.id,
  role: u.role,
  student_id: u.student_id,
  // 後端還沒有「店家帳號屬於哪家餐廳」，店家一律管示範的第一家
  restaurant_id: u.role === 'customer' ? null : USERS.staff.restaurant_id,
});

export async function login(student_id, password) {
  const res = await http('POST', '/auth/login', { student_id, password });
  return { access_token: res.access_token, user: toSessionUser(res.user) };
}

export async function register({ student_id, email, phone_number, password }) {
  await http('POST', '/auth/register', { student_id, email, phone_number, password });
  return login(student_id, password);
}

export async function getMe() {
  const u = await http('GET', '/auth/me');
  const su = toSessionUser(u);
  const r = su.restaurant_id ? SEED_RESTAURANTS.find((x) => x.id === su.restaurant_id) : null;
  return {
    ...su,
    name: u.student_id,
    first_name: u.student_id,
    email: u.email,
    phone_number: u.phone_number,
    department: '',
    store_name: r ? loc(r.name) : null,
  };
}

// ======================= 訂單 =======================
export async function createOrder({ restaurant_id, items }) {
  const { byMockId } = await getCatalog(true); // 每次下單重抓，菜單有改也對得上
  const lines = items.map((l) => {
    const item_id = byMockId.get(`${restaurant_id}/${l.menu_item_id}`);
    if (!item_id) throw new Error(getLang() === 'en' ? 'This item is not in the database yet' : '這個品項還沒建到資料庫裡');
    return { item_id, quantity: l.qty };
  });
  return toOrder(await http('POST', '/orders', { items: lines }));
}

export async function getOrder(id) {
  const o = await http('GET', `/orders/${encodeURIComponent(id)}`);
  return toOrder(o, session.get()?.user?.role === 'customer' ? 'customer' : 'staff');
}

export async function listMyOrders() {
  const list = await http('GET', '/orders?mine=true&limit=100');
  return Promise.all(list.map((o) => toOrder(o)));
}

// 模擬付款：一律成功，只記在這台瀏覽器
export async function pay(order_id, method) {
  await new Promise((r) => setTimeout(r, 400));
  paidOrders.set(String(order_id), method);
  return { payment_id: 'p' + Date.now(), status: 'succeeded' };
}

// ======================= 店家接單看板 =======================
export async function adminListOrders() {
  const rid = session.get()?.user?.restaurant_id;
  const vendor = SEED_RESTAURANTS.find((r) => r.id === rid)?.name.zh;
  const list = await http('GET', '/orders?limit=200');
  const active = list.filter((o) => o.vendor === vendor && ['confirming', 'preparing', 'ready'].includes(o.status));
  const orders = await Promise.all(active.map((o) => toOrder(o, 'staff')));
  return orders.sort((a, b) => a.created_at.localeCompare(b.created_at));
}

export async function adminUpdateOrderStatus(id, status) {
  const path = status === 'cancelled' ? `/orders/${id}/cancel` : `/orders/${id}/status`;
  const o = status === 'cancelled'
    ? await http('POST', path)
    : await http('PATCH', path, { status: toBackendStatus(status) });
  return toOrder(o, 'staff');
}
