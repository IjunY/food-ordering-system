// 假後端：照 Figma 封面的 API 總表實作，資料存在瀏覽器 localStorage（同一台電腦的分頁共用，
// 所以顧客分頁下的單會出現在店家分頁的接單看板）。接真後端後這個檔案就不用了。
import { getLang } from '../i18n.js';
import { session } from '../store.js';
import { SEED_RESTAURANTS, SEED_MENUS, PAYMENT_METHODS, USERS, REPORTS, seedOrders } from './data.js';

const DB_KEY = 'mockdb_v2';
let memoryDb = null;

function freshDb() {
  return { restaurants: structuredClone(SEED_RESTAURANTS), menus: structuredClone(SEED_MENUS), orders: seedOrders(), seq: 35 };
}
function db() {
  try {
    const s = localStorage.getItem(DB_KEY);
    if (s) return JSON.parse(s);
  } catch { /* 退回記憶體 */ }
  if (!memoryDb) { memoryDb = freshDb(); save(memoryDb); }
  return memoryDb;
}
function save(d) {
  memoryDb = d;
  try { localStorage.setItem(DB_KEY, JSON.stringify(d)); } catch { /* 只存在記憶體 */ }
}
export function resetMockDb() {
  memoryDb = null;
  try { localStorage.removeItem(DB_KEY); } catch { /* 無妨 */ }
}

const sleep = (ms = 120) => new Promise((r) => setTimeout(r, ms));
const iso = (d = new Date()) => d.toISOString();
const loc = (v) => (v && typeof v === 'object' && !Array.isArray(v) && 'zh' in v ? v[getLang()] ?? v.zh : v);
const fail = (msg) => { throw new Error(msg); };
const me = () => session.get()?.user ?? fail('Not signed in');

// ---------- 排隊與等候時間（Demo 用的簡單算法，不是重點） ----------
const isActive = (o) => ['paid', 'accepted', 'preparing'].includes(o.status) || (o.status === 'pending_payment' && o.payment_confirmed);
function estimate(d, r) {
  const active = d.orders.filter((o) => o.restaurant_id === r.id && isActive(o)).length;
  const wait_minutes = r.base_wait + active * 2;
  return { wait_minutes, queue_count: r.base_queue + active, estimated_ready_at: iso(new Date(Date.now() + wait_minutes * 60000)) };
}

// 顧客付款後讓訂單自己往下走，Demo 時不用另開店家分頁也看得到進度；店家一按按鈕就改成手動
const AUTO_STEPS = [['accepted', 8], ['preparing', 15], ['ready', 40]];
function tick(o) {
  if (!o.auto || !o.confirmed_at || ['ready', 'picked_up', 'cancelled'].includes(o.status)) return;
  const t0 = new Date(o.confirmed_at).getTime();
  const sec = (Date.now() - t0) / 1000;
  for (const [status, after] of AUTO_STEPS) {
    if (sec >= after && !o.status_history.some((h) => h.status === status)) {
      o.status = status;
      o.status_history.push({ status, at: iso(new Date(t0 + after * 1000)) });
      if (status === 'ready') o.estimated_ready_at = iso(new Date(t0 + after * 1000));
    }
  }
}

function outRestaurant(d, r) {
  const e = estimate(d, r);
  return {
    id: r.id, area: r.area, name: loc(r.name), location: loc(r.location), location_detail: loc(r.location_detail),
    description: loc(r.description), opening_hours_label: loc(r.opening_hours_label),
    opening_hours: r.opening_hours.map((h) => ({ days: loc(h.days), hours: loc(h.hours) })),
    is_open: r.is_open, is_accepting_orders: r.is_accepting_orders, status: r.status,
    queue_count: e.queue_count, wait_minutes: e.wait_minutes,
    image_url: r.image_url, cover_image_url: r.cover_image_url, phone: r.phone,
    owner_account: r.owner_account, today_order_count: r.today_order_count,
    allow_cash_on_pickup: r.allow_cash_on_pickup, allow_scheduled_pickup: r.allow_scheduled_pickup,
    concurrent_capacity: r.concurrent_capacity, pickup_hold_minutes: r.pickup_hold_minutes,
  };
}
function outItem(i) {
  return {
    id: i.id, category_id: i.category_id, name: loc(i.name), description: loc(i.description), price: i.price,
    prep_minutes: i.prep_minutes, is_available: i.is_available, is_sold_out: i.is_sold_out, image_url: i.image_url,
    option_groups: i.option_groups.map((g) => ({ id: g.id, name: loc(g.name), required: g.required, max_select: g.max_select,
      choices: g.choices.map((c) => ({ id: c.id, label: loc(c.label), price_delta: c.price_delta })) })),
  };
}
function outOrder(d, o) {
  const r = d.restaurants.find((x) => x.id === o.restaurant_id);
  const ahead = d.orders.filter((x) => x.restaurant_id === o.restaurant_id && isActive(x) && x.created_at < o.created_at).length;
  return {
    id: o.id, pickup_number: o.pickup_number, restaurant_id: o.restaurant_id,
    restaurant_name: loc(r.name), restaurant_location: loc(r.location),
    status: o.status, payment_method: o.payment_method, payment_status: o.payment_status,
    total: o.total, note: loc(o.note), pickup_type: o.pickup_type, pickup_time: o.pickup_time,
    items: o.items.map((i) => ({ menu_item_id: i.menu_item_id, name: loc(i.name), qty: i.qty, unit_price: i.unit_price, subtotal: i.subtotal, options_label: loc(i.options_label), option_ids: i.option_ids || [] })),
    created_at: o.created_at, estimated_ready_at: o.estimated_ready_at,
    queue_ahead: isActive(o) ? ahead : 0, status_history: o.status_history,
  };
}
const findOrder = (d, id) => d.orders.find((o) => o.id === id) ?? fail('Order not found');
const findRestaurant = (d, id) => d.restaurants.find((r) => r.id === id) ?? fail('Restaurant not found');

// ======================= 顧客端 =======================
export async function login(student_id) {
  await sleep();
  const id = String(student_id || '').trim().toLowerCase();
  const role = id === 'admin' ? 'admin' : id === 'staff' ? 'staff' : 'customer';
  const u = USERS[role];
  return { access_token: `mock-${role}`, user: { id: u.id, role, student_id: role === 'customer' ? student_id : null, restaurant_id: u.restaurant_id ?? null } };
}

export async function getMe() {
  await sleep(40);
  const s = me();
  const u = USERS[s.role];
  const d = db();
  const r = s.restaurant_id ? d.restaurants.find((x) => x.id === s.restaurant_id) : null;
  return { id: u.id, role: s.role, name: loc(u.name), first_name: loc(u.first_name), student_id: s.student_id || '112012345', department: loc(u.department), restaurant_id: s.restaurant_id, store_name: r ? loc(r.name) : null };
}

export async function listRestaurants({ location = 'all', sort = 'wait' } = {}) {
  await sleep();
  const d = db();
  let list = d.restaurants.filter((r) => r.status === 'active').map((r) => outRestaurant(d, r));
  if (location !== 'all') list = list.filter((r) => r.area === location);
  const openFirst = (a, b) => Number(b.is_open && b.is_accepting_orders) - Number(a.is_open && a.is_accepting_orders);
  list.sort((a, b) => openFirst(a, b) || (sort === 'wait' ? a.wait_minutes - b.wait_minutes : a.name.localeCompare(b.name)));
  return list;
}

export async function getRestaurant(id) {
  await sleep(60);
  const d = db();
  return outRestaurant(d, findRestaurant(d, id));
}

export async function getMenu(id) {
  await sleep(60);
  const m = db().menus[id] ?? fail('Menu not found');
  return { categories: m.categories.map((c) => ({ id: c.id, name: loc(c.name), items: m.items.filter((i) => i.category_id === c.id).map(outItem) })) };
}

export async function getWaitEstimate(id) {
  await sleep(40);
  const d = db();
  return estimate(d, findRestaurant(d, id));
}

export async function createOrder({ restaurant_id, items, pickup_type = 'asap', pickup_time = null }) {
  await sleep();
  const d = db();
  const r = findRestaurant(d, restaurant_id);
  if (!r.is_open || !r.is_accepting_orders) fail(getLang() === 'en' ? 'This restaurant is not taking orders right now' : '這家餐廳目前暫停接單');
  const menu = d.menus[restaurant_id];
  const lines = items.map((l) => {
    const mi = menu.items.find((i) => i.id === l.menu_item_id) ?? fail('Item not found');
    if (mi.is_sold_out || !mi.is_available) fail((getLang() === 'en' ? 'Sold out: ' : '已售完：') + loc(mi.name));
    const chosen = mi.option_groups.flatMap((g) => g.choices.filter((c) => (l.option_ids || []).includes(`${g.id}:${c.id}`)));
    const unit_price = mi.price + chosen.reduce((s, c) => s + c.price_delta, 0);
    return {
      menu_item_id: mi.id, name: mi.name, qty: l.qty, unit_price, subtotal: unit_price * l.qty, option_ids: l.option_ids || [],
      options_label: chosen.length ? { zh: chosen.map((c) => c.label.zh).join('、'), en: chosen.map((c) => c.label.en).join(', ') } : null,
      note: l.note || '',
    };
  });
  const notes = lines.filter((l) => l.note).map((l) => l.note).join(' / ');
  const e = estimate(d, r);
  const o = {
    id: 'o' + Date.now(), pickup_number: 'A' + String(d.seq++).padStart(3, '0'), restaurant_id, user_id: me().id,
    status: 'pending_payment', payment_method: null, payment_status: 'unpaid', payment_confirmed: false,
    items: lines, total: lines.reduce((s, l) => s + l.subtotal, 0), note: notes || null,
    pickup_type, pickup_time, created_at: iso(), estimated_ready_at: pickup_time || e.estimated_ready_at,
    status_history: [], auto: true, confirmed_at: null,
  };
  d.orders.push(o);
  save(d);
  return outOrder(d, o);
}

export async function getOrder(id) {
  await sleep(60);
  const d = db();
  const o = findOrder(d, id);
  tick(o);
  save(d);
  return outOrder(d, o);
}

export async function listMyOrders() {
  await sleep();
  const d = db();
  const uid = me().id;
  const mine = d.orders.filter((o) => o.user_id === uid);
  mine.forEach(tick);
  save(d);
  return mine.sort((a, b) => b.created_at.localeCompare(a.created_at)).map((o) => outOrder(d, o));
}

export async function listPaymentMethods() {
  await sleep(40);
  return PAYMENT_METHODS.map((m) => ({ method: m.method, short: loc(m.short), label: loc(m.label), hint: loc(m.hint) }));
}

// 模擬付款：一律成功。到店付款不算付清，但訂單直接進店家的「新訂單」
export async function pay(order_id, method) {
  await sleep(500);
  const d = db();
  const o = findOrder(d, order_id);
  if (o.payment_confirmed) fail('Already paid');
  o.payment_method = method;
  o.payment_confirmed = true;
  o.confirmed_at = iso();
  if (method === 'cash_on_pickup') {
    o.payment_status = 'unpaid';
  } else {
    o.payment_status = 'paid';
    o.status = 'paid';
    o.status_history.push({ status: 'paid', at: o.confirmed_at });
  }
  save(d);
  return { payment_id: 'p' + Date.now(), status: 'succeeded' };
}

// ======================= 店家端 =======================
const myRestaurantId = () => me().restaurant_id ?? fail('No restaurant');

export async function adminListOrders() {
  await sleep(60);
  const d = db();
  const rid = myRestaurantId();
  const list = d.orders.filter((o) => o.restaurant_id === rid);
  list.forEach(tick);
  save(d);
  return list.filter((o) => ['paid', 'accepted', 'preparing', 'ready'].includes(o.status) || (o.status === 'pending_payment' && o.payment_confirmed))
    .sort((a, b) => a.created_at.localeCompare(b.created_at)).map((o) => outOrder(d, o));
}

export async function adminUpdateOrderStatus(id, status) {
  await sleep();
  const d = db();
  const o = findOrder(d, id);
  o.auto = false;
  const now = iso();
  if (status === 'preparing' && !o.status_history.some((h) => h.status === 'accepted')) o.status_history.push({ status: 'accepted', at: now });
  if (status === 'picked_up' && o.payment_status !== 'paid') o.payment_status = 'paid';
  if (status === 'ready') o.estimated_ready_at = now;
  o.status = status;
  o.status_history.push({ status, at: now });
  save(d);
  return outOrder(d, o);
}

export async function adminGetRestaurant() {
  await sleep(40);
  const d = db();
  return outRestaurant(d, findRestaurant(d, myRestaurantId()));
}

export async function adminUpdateRestaurant(patch) {
  await sleep();
  const d = db();
  const r = findRestaurant(d, myRestaurantId());
  const lang = getLang();
  for (const [k, v] of Object.entries(patch)) {
    if (r[k] && typeof r[k] === 'object' && 'zh' in r[k]) r[k][lang] = v; // 多語欄位只改目前語言
    else r[k] = v;
  }
  if ('location' in patch) r.location_detail[lang] = patch.location;
  save(d);
  return outRestaurant(d, r);
}

export async function adminListMenuItems() {
  await sleep(60);
  const m = db().menus[myRestaurantId()];
  const cats = m.categories.map((c) => ({ id: c.id, name: loc(c.name) }));
  return { categories: cats, items: m.items.map((i) => ({ ...outItem(i), category_name: cats.find((c) => c.id === i.category_id)?.name ?? '' })) };
}

export async function adminSaveMenuItem(data) {
  await sleep();
  const d = db();
  const m = d.menus[myRestaurantId()];
  const lang = getLang();
  let i = data.id ? m.items.find((x) => x.id === data.id) : null;
  if (!i) {
    i = { id: 'm' + Date.now(), name: { zh: '', en: '' }, description: { zh: '', en: '' }, option_groups: [], image_url: null };
    m.items.push(i);
  }
  for (const k of ['name', 'description']) {
    i[k][lang] = data[k];
    for (const other of ['zh', 'en']) if (!i[k][other]) i[k][other] = data[k];
  }
  Object.assign(i, { category_id: data.category_id, price: data.price, prep_minutes: data.prep_minutes, is_available: data.is_available, is_sold_out: data.is_sold_out });
  if ('image_url' in data) i.image_url = data.image_url || null;
  save(d);
  return outItem(i);
}

export async function adminPatchMenuItem(id, patch) {
  await sleep(60);
  const d = db();
  const i = d.menus[myRestaurantId()].items.find((x) => x.id === id) ?? fail('Item not found');
  Object.assign(i, patch);
  save(d);
  return outItem(i);
}

export async function adminDeleteMenuItem(id) {
  await sleep();
  const d = db();
  const m = d.menus[myRestaurantId()];
  m.items = m.items.filter((x) => x.id !== id);
  save(d);
  return { ok: true };
}

export async function adminReports(range = 'today') {
  await sleep();
  const k = { today: 1, week: 6.4, month: 27 }[range] ?? 1;
  const s = REPORTS.summary;
  return {
    summary: { ...s, order_count: Math.round(s.order_count * k), revenue: Math.round(s.revenue * k) },
    orders_by_slot: REPORTS.slots.map(([slot, count]) => ({ slot, count: Math.round(count * k) })),
    top_items: REPORTS.top_items.map((x) => ({ name: loc(x.name), qty: Math.round(x.qty * k), revenue: Math.round(x.revenue * k) })),
  };
}

// ======================= 平台管理（admin） =======================
export async function platformListRestaurants() {
  await sleep();
  if (me().role !== 'admin') fail('Forbidden');
  const d = db();
  return { stats: REPORTS.platform, restaurants: d.restaurants.map((r) => outRestaurant(d, r)) };
}

export async function platformSetRestaurantStatus(id, status) {
  await sleep();
  if (me().role !== 'admin') fail('Forbidden');
  const d = db();
  const r = findRestaurant(d, id);
  r.status = status;
  if (status === 'active' && id === 'r5') { r.is_open = true; r.is_accepting_orders = true; }
  save(d);
  return outRestaurant(d, r);
}

// 上傳圖片：假後端把照片縮到長邊 720px、轉成 JPEG data URL（存在 localStorage，不能太大）
export async function uploadImage(file) {
  if (!file || !file.type.startsWith('image/')) throw new Error(getLang() === 'en' ? 'Please choose an image file' : '請選擇圖片檔');
  if (file.size > 10 * 1024 * 1024) throw new Error(getLang() === 'en' ? 'Please choose a photo under 10 MB' : '照片太大，請選 10 MB 以下的檔案');
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => { const i = new Image(); i.onload = () => resolve(i); i.onerror = reject; i.src = url; });
    const scale = Math.min(1, 720 / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
    return { url: canvas.toDataURL('image/jpeg', 0.78) };
  } finally {
    URL.revokeObjectURL(url);
  }
}
