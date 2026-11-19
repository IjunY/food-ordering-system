// 真後端（FastAPI，app/）的轉接層：呼叫 /api，再把回傳轉成畫面用的欄位（和 mock/api.js 同一套）。
//
// 目前接上真後端的：登入／註冊／我的資料、下單、訂單查詢、店家接單看板改狀態、店家「接單／暫停」開關，
// 以及餐廳是否接單（餐廳列表與餐廳頁的其餘內容仍來自 mock/data.js）。
// 還沒接的（菜單、等候時間、付款、店家其餘設定與菜單管理、報表、平台管理）照舊用 mock/api.js。
//
// 店家帳號屬於哪家餐廳：後端 users.vendor_id → 用店名對應到 mock/data.js 的餐廳。
// 後端只回傳該店家的訂單（平台管理員看得到全部）。
//
// 菜單仍顯示前端的示範資料，所以下單時要把示範品項換成資料庫裡的品項編號：
// 兩邊用「餐廳中文名＋品項中文名」對應（scripts/seed_demo.py 照 mock/data.js 灌進資料庫）。
// 後端回傳的名稱都是 {zh, en}，對應時一律用 zh。
// 付款仍是模擬的，付款紀錄只存在這台瀏覽器（paid_orders）。
import { getLang } from '../i18n.js';
import { session, read, write } from '../store.js';
import { SEED_RESTAURANTS, SEED_MENUS, USERS } from '../mock/data.js';
import * as mock from '../mock/api.js';

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
  const [rows, vendors] = await Promise.all([http('GET', '/menu-items'), http('GET', '/vendors')]);
  const vendorName = new Map(vendors.map((v) => [v.id, v.name.zh]));
  const byDbId = new Map();
  const byMockId = new Map();
  for (const row of rows) {
    const restaurant = restaurantByVendor(vendorName.get(row.vendor_id));
    const item = restaurant ? SEED_MENUS[restaurant.id]?.items.find((i) => i.name.zh === row.item_name.zh) : null;
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
  const r = first?.restaurant ?? restaurantByVendor(o.vendor_name.zh);
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
    restaurant_name: r ? loc(r.name) : loc(o.vendor_name),
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
        name: hit?.item ? loc(hit.item.name) : loc(i.item_name),
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

// ---------- 店家（後端 vendors）⇄ 畫面上的餐廳 ----------
const listVendors = () => http('GET', '/vendors');

// 後端的接單狀態蓋過 mock 資料裡的設定（以店名對應）
async function withVendorStatus(list) {
  const vendors = await listVendors().catch(() => null);
  if (!vendors) return list;
  const accepting = new Map(vendors.map((v) => [v.name.zh, v.is_accepting_orders]));
  return list.map((r) => {
    const zh = SEED_RESTAURANTS.find((x) => x.id === r.id)?.name.zh;
    return accepting.has(zh) ? { ...r, is_accepting_orders: accepting.get(zh) } : r;
  });
}

export async function listRestaurants(params) {
  const list = await withVendorStatus(await mock.listRestaurants(params));
  const open = (r) => Number(r.is_open && r.is_accepting_orders);
  return list.sort((a, b) => open(b) - open(a)); // 暫停接單的排到後面（sort 是穩定的，其餘順序不變）
}

export async function getRestaurant(id) {
  return (await withVendorStatus([await mock.getRestaurant(id)]))[0];
}

// ======================= 登入 =======================
// 店家：restaurant_id 是自己那家店（vendor_id → 店名 → 畫面上的餐廳）；沒綁店家就是 null。
// 平台管理員：後台頁面沿用示範的第一家餐廳。
async function toSessionUser(u) {
  let restaurant_id = null;
  if (u.role === 'admin') restaurant_id = USERS.admin.restaurant_id;
  if (u.role === 'staff' && u.vendor_id != null) {
    const vendor = (await listVendors()).find((v) => v.id === u.vendor_id);
    restaurant_id = vendor ? restaurantByVendor(vendor.name.zh)?.id ?? null : null;
  }
  return { id: u.id, role: u.role, student_id: u.student_id, vendor_id: u.vendor_id ?? null, restaurant_id };
}

export async function login(student_id, password) {
  const res = await http('POST', '/auth/login', { student_id, password });
  return { access_token: res.access_token, user: await toSessionUser(res.user) };
}

export async function register({ student_id, email, phone_number, password }) {
  await http('POST', '/auth/register', { student_id, email, phone_number, password });
  return login(student_id, password);
}

export async function getMe() {
  const u = await http('GET', '/auth/me');
  const su = await toSessionUser(u);
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
// 後端只回傳這個店家帳號的訂單；平台管理員拿到的是全部店家的，所以只留畫面上這家店的
export async function adminListOrders() {
  const user = session.get()?.user;
  const vendor = SEED_RESTAURANTS.find((r) => r.id === user?.restaurant_id)?.name.zh;
  const list = await http('GET', '/orders?limit=200');
  const active = list.filter((o) => (user?.role !== 'admin' || o.vendor_name.zh === vendor) && ['confirming', 'preparing', 'ready'].includes(o.status));
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

// ======================= 店家設定 =======================
// 「接單／暫停」開關寫進後端（PATCH /vendors/{id}），其餘設定仍只存在這台瀏覽器（mock）
async function myVendorId() {
  const user = session.get()?.user;
  if (user?.vendor_id != null) return user.vendor_id;
  const zh = SEED_RESTAURANTS.find((r) => r.id === user?.restaurant_id)?.name.zh;
  return (await listVendors()).find((v) => v.name.zh === zh)?.id ?? null;
}

export async function adminGetRestaurant() {
  return (await withVendorStatus([await mock.adminGetRestaurant()]))[0];
}

export async function adminUpdateRestaurant(patch) {
  if ('is_accepting_orders' in patch) {
    const id = await myVendorId();
    if (id == null) throw new Error(getLang() === 'en' ? 'This account is not linked to a vendor' : '這個帳號還沒綁定店家');
    await http('PATCH', `/vendors/${id}`, { is_accepting_orders: patch.is_accepting_orders });
  }
  return (await withVendorStatus([await mock.adminUpdateRestaurant(patch)]))[0];
}
