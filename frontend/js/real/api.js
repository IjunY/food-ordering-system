// 真後端（FastAPI，app/）的轉接層：呼叫 /api，再把回傳轉成畫面用的欄位（和 mock/api.js 同一套）。
//
// 資料庫是唯一的資料來源：餐廳、菜單、加點選項、訂單、付款、店家設定、菜單管理、報表、平台管理、照片都走後端。
// 付款：線上付款導到後端設定的金流商（LINE Pay sandbox，或後端自己的模擬付款頁），付完再導回取餐券；
//       到店付款只是在訂單上註記，店家看板會顯示「未付款・到店付款」。
// 還在前端的只有等候時間：用後端給的排隊數（queue_count）和品項的備餐時間估
// 後端回傳的文字都是 {zh, en}，這裡依目前語言換成字串；店家要編輯兩種語言的欄位另外放在 edit 裡。
import { getLang, t } from '../i18n.js';
import { session } from '../store.js';
import { shrinkImage } from '../image.js';

export const API_BASE = '/api';

const loc = (v) => (v && typeof v === 'object' && 'zh' in v ? v[getLang()] ?? v.zh : v);
const en = () => getLang() === 'en';

// 後端錯誤 → 讀得懂的訊息。422（欄位格式不對）的 detail 是陣列
function errorMessage(body, res) {
  const d = body?.detail;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(-1)[0] ?? ''} ${e.msg}`.trim()).join('；');
  return d || `${res.status} ${res.statusText}`;
}

async function send(method, path, { json, blob } = {}) {
  const token = session.get()?.access_token;
  const res = await fetch(API_BASE + path, {
    method,
    headers: {
      ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(blob ? { 'Content-Type': blob.type } : {}),
      'Accept-Language': en() ? 'en' : 'zh-TW',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: blob ?? (json === undefined ? undefined : JSON.stringify(json)),
  });
  if (res.status === 401 && token) {
    // 登入過期：清掉登入狀態回登入頁
    session.clear();
    location.hash = 'login';
  }
  if (!res.ok) {
    const err = new Error(errorMessage(await res.json().catch(() => null), res));
    err.status = res.status; // 讓呼叫的地方分辨是哪一種錯誤
    throw err;
  }
  return res.status === 204 ? null : res.json();
}
const http = (method, path, json) => send(method, path, { json });

// 後端是否在線：/api/health 回 {status:'ok'} 才算
export async function isAvailable() {
  try {
    const res = await fetch(API_BASE + '/health', { headers: { Accept: 'application/json' } });
    return res.ok && (await res.json()).status === 'ok';
  } catch {
    return false;
  }
}

// ======================= 餐廳與菜單 =======================
const getVendors = () => http('GET', '/vendors');
const getVendor = (id) => http('GET', `/vendors/${encodeURIComponent(id)}`);
const getItems = (vendorId) => http('GET', vendorId == null ? '/menu-items' : `/menu-items?vendor_id=${encodeURIComponent(vendorId)}`);

// 等候時間（估計）：供應中品項的備餐時間取中位數，加上前面每張單 2 分鐘
function estimate(v, items) {
  const preps = items.filter((i) => i.is_available).map((i) => i.prep_minutes).sort((a, b) => a - b);
  const prep = preps.length ? preps[Math.floor(preps.length / 2)] : 8;
  const wait_minutes = Math.max(3, prep + v.queue_count * 2);
  return { wait_minutes, queue_count: v.queue_count, estimated_ready_at: new Date(Date.now() + wait_minutes * 60000).toISOString() };
}

function toRestaurant(v, items = []) {
  const e = estimate(v, items);
  return {
    id: String(v.id), area: v.area, name: loc(v.name), location: loc(v.location), location_detail: loc(v.location),
    description: loc(v.description), opening_hours_label: loc(v.opening_hours), opening_hours: [],
    is_open: true, is_accepting_orders: v.is_accepting_orders, status: 'active',
    queue_count: e.queue_count, wait_minutes: e.wait_minutes,
    image_url: v.image_url, cover_image_url: v.cover_image_url, phone: '',
    // 後端沒有這兩個設定：到店付款都可以；預約取餐的時間後端不會記下來，所以不開放
    allow_cash_on_pickup: true, allow_scheduled_pickup: false,
    // 店家設定頁編輯用（兩種語言）
    edit: { name: v.name, location: v.location, description: v.description, opening_hours: v.opening_hours, area: v.area },
  };
}

function toItem(row, category_id) {
  return {
    id: String(row.id), category_id, name: loc(row.item_name), description: loc(row.description),
    price: row.price, prep_minutes: row.prep_minutes,
    // 資料庫只有「供應中」一個開關；關掉就是售完（顧客看得到但不能點）
    is_available: row.is_available, is_sold_out: !row.is_available, image_url: row.image_url,
    option_groups: row.option_groups.map((g) => ({
      id: g.id, name: loc(g.name), required: g.required, max_select: g.max_select,
      choices: g.choices.map((c) => ({ id: c.id, label: loc(c.label), price_delta: c.price_delta })),
    })),
  };
}

// 品項依分類分組，分類照第一次出現的順序（以中文名稱判斷是不是同一類）
function groupByCategory(rows) {
  const cats = [];
  for (const row of rows) {
    let c = cats.find((x) => x.zh === row.category.zh);
    if (!c) cats.push((c = { id: `c${cats.length}`, zh: row.category.zh, en: row.category.en, rows: [] }));
    c.rows.push(row);
  }
  return cats;
}

export async function listRestaurants({ sort = 'wait' } = {}) {
  const [vendors, items] = await Promise.all([getVendors(), getItems()]);
  const list = vendors.map((v) => toRestaurant(v, items.filter((i) => i.vendor_id === v.id)));
  const open = (r) => Number(r.is_open && r.is_accepting_orders);
  // 暫停接單的排到後面
  return list.sort((a, b) => open(b) - open(a) || (sort === 'wait' ? a.wait_minutes - b.wait_minutes : a.name.localeCompare(b.name)));
}

export async function getRestaurant(id) {
  const [v, items] = await Promise.all([getVendor(id), getItems(id)]);
  return toRestaurant(v, items);
}

export async function getMenu(id) {
  return { categories: groupByCategory(await getItems(id)).map((c) => ({ id: c.id, name: loc(c), items: c.rows.map((r) => toItem(r, c.id)) })) };
}

export async function getWaitEstimate(id) {
  const [v, items] = await Promise.all([getVendor(id), getItems(id)]);
  return estimate(v, items);
}

// ======================= 登入 =======================
// 店家帳號：restaurant_id 是自己那家店（後端的 vendor_id）
function toSessionUser(u) {
  return {
    id: u.id, role: u.role, student_id: u.student_id, vendor_id: u.vendor_id ?? null,
    restaurant_id: u.role === 'staff' && u.vendor_id != null ? String(u.vendor_id) : null,
    must_change_password: !!u.must_change_password,
    must_choose_username: !!u.must_choose_username,
  };
}
const toSession = (res) => ({ access_token: res.access_token, user: toSessionUser(res.user) });

export async function login(student_id, password) {
  return toSession(await http('POST', '/auth/login', { student_id, password }));
}

export async function register({ student_id, email, phone_number, password }) {
  await http('POST', '/auth/register', { student_id, email, phone_number, password });
  return login(student_id, password);
}

// 換密碼；換完舊的登入就失效，所以回傳新的。
// 管理員建立的店家帳號第一次登入時，同時選自己的登入帳號（new_student_id），之後帳號就不能再改
// 後端的錯誤訊息（英文）→ 代碼，畫面再換成翻譯好的說明（pages/customer.js 的 PASSWORD_ERRORS）
const PASSWORD_ERRORS = [
  [/current password is incorrect/i, 'wrong_current'],
  [/must be different/i, 'same'],
  [/already taken/i, 'id_taken'],
  [/invalid or has expired/i, 'link_invalid'],
];
function tagPasswordError(err) {
  if (err.status === 400 || err.status === 409) err.code = PASSWORD_ERRORS.find(([re]) => re.test(err.message))?.[1];
  return err;
}

export async function changePassword(current_password, new_password, new_student_id) {
  const body = { current_password, new_password, ...(new_student_id ? { new_student_id } : {}) };
  // 目前密碼打錯是 400（不是 401，才不會被當成登入過期而登出）
  try { return toSession(await http('POST', '/auth/change-password', body)); } catch (err) { throw tagPasswordError(err); }
}

// 忘記密碼：後端把一次性的連結寄到帳號的 email（不管帳號存不存在都回一樣的結果）
export async function forgotPassword(account) {
  await http('POST', '/auth/forgot-password', { account });
}

// 從信裡的連結（#reset-<token>）設定新密碼，成功就直接登入
export async function resetPassword(token, new_password) {
  try { return toSession(await http('POST', '/auth/reset-password', { token, new_password })); } catch (err) { throw tagPasswordError(err); }
}

export async function getMe() {
  const u = await http('GET', '/auth/me');
  const vendor = u.role === 'staff' && u.vendor_id != null ? await getVendor(u.vendor_id).catch(() => null) : null;
  return {
    ...toSessionUser(u),
    name: u.student_id, first_name: u.student_id,
    email: u.email, phone_number: u.phone_number, department: '',
    store_name: vendor ? loc(vendor.name) : null,
  };
}

// ======================= 訂單 =======================
// 後端：confirming → preparing → ready → picked up（另有 cancelled）
// 畫面：pending_payment → paid → accepted → preparing → ready → picked_up
const toBackendStatus = (s) => (s === 'picked_up' ? 'picked up' : s === 'accepted' ? 'preparing' : s);

// 後端接的金流商：linepay 或 mock（模擬付款頁）。開一次問一次就好
let paymentConfig = null;
function getPaymentConfig() {
  paymentConfig ??= http('GET', '/payments/config').catch((err) => { paymentConfig = null; throw err; });
  return paymentConfig;
}
const onlineMethod = async () => ((await getPaymentConfig()).provider === 'linepay' ? 'line_pay' : 'mock');

// 訂單畫面要的店家位置與品項備餐時間：30 秒內重複用
let catalog = { at: 0, data: null };
async function getCatalog() {
  if (!catalog.data || Date.now() - catalog.at > 30000) {
    const [vendors, items] = await Promise.all([getVendors(), getItems()]);
    catalog = { at: Date.now(), data: { vendors: new Map(vendors.map((v) => [v.id, v])), prep: new Map(items.map((i) => [i.id, i.prep_minutes])) } };
  }
  return catalog.data;
}

// 後端的訂單 → 畫面的訂單（顧客和店家看到的一樣）
// 「確認中」的單：線上付好了是 paid（等店家接單）；還沒付是 pending_payment（到店付款的也是，但已經選好付款方式）
async function toOrder(o) {
  const [{ vendors, prep }, online] = await Promise.all([getCatalog(), onlineMethod()]);
  const v = vendors.get(o.vendor_id);
  const id = String(o.id);
  const paid = o.payment_status === 'paid';
  const method = paid ? online : o.pay_at_pickup ? 'cash_on_pickup' : null;

  let status = o.status === 'picked up' ? 'picked_up' : o.status;
  if (status === 'confirming') status = paid ? 'paid' : 'pending_payment';

  const longest = Math.max(5, ...o.items.map((i) => prep.get(i.item_id) ?? 0));
  const eta = new Date(new Date(o.created_at).getTime() + longest * 60000).toISOString();
  const history = status === 'pending_payment' || status === 'cancelled' ? [] : [{ status: 'paid', at: o.created_at }];
  const notes = o.items.filter((i) => i.note).map((i) => i.note).join(' / ');

  return {
    id,
    pickup_number: 'A' + String(o.id).padStart(3, '0'),
    restaurant_id: String(o.vendor_id),
    restaurant_name: loc(o.vendor_name),
    restaurant_location: v ? loc(v.location) : '',
    status,
    payment_method: method,
    // 到店付款的單，取餐時在櫃台付清
    payment_status: paid || (method === 'cash_on_pickup' && status === 'picked_up') ? 'paid' : 'unpaid',
    // 上一次線上付款的結果（failed / expired 時付款頁會說可以再試一次）
    payment_attempt: o.payment_status,
    total: o.total,
    note: notes || null,
    pickup_type: 'asap',
    pickup_time: null,
    items: o.items.map((i) => ({
      menu_item_id: String(i.item_id), name: loc(i.item_name), qty: i.quantity,
      unit_price: i.unit_price, subtotal: i.subtotal,
      options_label: i.options_label ? loc(i.options_label) : null, option_ids: i.option_ids, note: i.note,
    })),
    created_at: o.created_at,
    estimated_ready_at: eta,
    queue_ahead: 0,
    status_history: history,
  };
}

export async function createOrder({ items }) {
  const lines = items.map((l) => {
    const item_id = Number(l.menu_item_id);
    // 練習模式留下的品項（編號不是數字）不在資料庫裡
    if (!Number.isInteger(item_id)) throw new Error(en() ? 'This item is no longer on the menu. Please add it again.' : '這個品項已經不在菜單上，請重新加入購物車');
    return { item_id, quantity: l.qty, option_ids: l.option_ids || [], note: String(l.note || '').slice(0, 60) };
  });
  return toOrder(await http('POST', '/orders', { items: lines }));
}

export async function getOrder(id) {
  return toOrder(await http('GET', `/orders/${encodeURIComponent(id)}`));
}

export async function listMyOrders() {
  const list = await http('GET', '/orders?mine=true&limit=100');
  return Promise.all(list.map((o) => toOrder(o)));
}

// 付款方式：後端接的線上金流（LINE Pay 或模擬付款頁）＋到店付款
export async function listPaymentMethods() {
  const online = (await getPaymentConfig()).provider === 'linepay'
    ? { method: 'line_pay', short: 'LINE', label: 'LINE Pay', hint: t('pay.hint.linepay') }
    : { method: 'mock', short: 'Pay', label: t('pay.method.mock'), hint: t('pay.hint.mock') };
  return [online, { method: 'cash_on_pickup', short: t('pay.short.cash'), label: t('pay.method.cash_on_pickup'), hint: t('pay.hint.cash') }];
}

// 到店付款：註記在訂單上就好。線上付款：後端建立付款，回傳付款頁網址，畫面把瀏覽器導過去，
// 付完（或取消）後金流商把瀏覽器導回後端，後端確認後再導回取餐券（#paid-訂單）或付款頁（#pay-訂單）
export async function pay(order_id, method) {
  if (method === 'cash_on_pickup') {
    await http('POST', `/orders/${encodeURIComponent(order_id)}/pay-at-pickup`);
    return { status: 'succeeded' };
  }
  const res = await http('POST', '/payments', { order_id: Number(order_id) });
  return { status: 'redirect', url: res.checkout_url };
}

// 這個店家帳號的訂單（後端只給自己店的），新的在前。since：只要這個時間之後的（一頁 200 張，往前翻到夠為止）
async function vendorOrders(since = null) {
  const all = [];
  for (let offset = 0; offset < 2000; offset += 200) {
    const page = await http('GET', `/orders?limit=200&offset=${offset}`);
    all.push(...page);
    if (page.length < 200 || (since && new Date(page[page.length - 1].created_at) < since)) break;
  }
  return since ? all.filter((o) => new Date(o.created_at) >= since) : all;
}
const startOfToday = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };

// ======================= 店家接單看板 =======================
// 看板只放店家該處理的單：線上付好的、選了到店付款的，以及已接單、可取餐的。
// 還沒付款（也沒選到店付款）的單不放，免得顧客沒付錢店家就開始做
export async function adminListOrders() {
  const list = await http('GET', '/orders?limit=200');
  const active = list.filter((o) => (o.status === 'confirming' ? o.payment_status === 'paid' || o.pay_at_pickup : ['preparing', 'ready'].includes(o.status)));
  const orders = await Promise.all(active.map((o) => toOrder(o)));
  return orders.sort((a, b) => a.created_at.localeCompare(b.created_at));
}

export async function adminUpdateOrderStatus(id, status) {
  const o = status === 'cancelled'
    ? await http('POST', `/orders/${id}/cancel`)
    : await http('PATCH', `/orders/${id}/status`, { status: toBackendStatus(status) });
  return toOrder(o);
}

// ======================= 店家設定 =======================
async function myVendorId() {
  const id = session.get()?.user?.vendor_id;
  if (id != null) return id;
  return (await http('GET', '/vendors/me')).id;
}

export async function adminGetRestaurant() {
  const v = await http('GET', '/vendors/me');
  const [items, today] = await Promise.all([getItems(v.id), vendorOrders(startOfToday())]);
  return { ...toRestaurant(v, items), today_order_count: today.filter((o) => o.status !== 'cancelled').length };
}

// patch 的欄位：name / location / description / opening_hours 是 {zh, en}；area、is_accepting_orders、兩張照片照原樣
export async function adminUpdateRestaurant(patch) {
  const body = {};
  for (const k of ['name', 'location', 'description', 'opening_hours']) {
    if (patch[k]) { body[`${k}_zh`] = patch[k].zh; body[`${k}_en`] = patch[k].en; }
  }
  for (const k of ['area', 'is_accepting_orders', 'image_url', 'cover_image_url']) if (k in patch) body[k] = patch[k];
  const v = await http('PATCH', `/vendors/${await myVendorId()}`, body);
  return toRestaurant(v);
}

// ======================= 菜單管理 =======================
export async function adminListMenuItems() {
  const cats = groupByCategory(await getItems(await myVendorId()));
  return {
    categories: cats.map((c) => ({ id: c.id, name: loc(c), zh: c.zh, en: c.en })),
    items: cats.flatMap((c) => c.rows.map((r) => ({
      ...toItem(r, c.id), category_name: loc(c),
      edit: { name: r.item_name, description: r.description, category: r.category, option_groups: r.option_groups },
    }))),
  };
}

// data：{ id?, name: {zh,en}, category: {zh,en}, description: {zh,en}, price, prep_minutes, is_available, image_url,
//         option_groups: [{ id, name: {zh,en}, required, max_select, choices: [{ id, label: {zh,en}, price_delta }] }] }
export async function adminSaveMenuItem(data) {
  const body = {
    item_name_zh: data.name.zh, item_name_en: data.name.en,
    category_zh: data.category.zh, category_en: data.category.en,
    description_zh: data.description.zh, description_en: data.description.en,
    price: data.price, prep_minutes: data.prep_minutes, is_available: data.is_available,
    image_url: data.image_url || null,
    option_groups: data.option_groups,
  };
  const row = data.id
    ? await http('PATCH', `/menu-items/${encodeURIComponent(data.id)}`, body)
    : await http('POST', '/menu-items', { ...body, vendor_id: await myVendorId() });
  return toItem(row, null);
}

// 表格上的「供應中」開關
export async function adminPatchMenuItem(id, patch) {
  return toItem(await http('PATCH', `/menu-items/${encodeURIComponent(id)}`, { is_available: patch.is_available }), null);
}

export async function adminDeleteMenuItem(id) {
  await http('DELETE', `/menu-items/${encodeURIComponent(id)}`);
  return { ok: true };
}

// ======================= 營收報表（用這家店的真實訂單算） =======================
// 和前一段比：今日比上週同一天（到現在這個時間為止）；本週（近 7 天）比再前 7 天；本月（近 30 天）比再前 30 天
const DAY = 86400000;
const pct = (cur, prev) => (prev ? Math.round(((cur - prev) / prev) * 100) : null);
const round1 = (n) => Math.round(n * 10) / 10;

function summarize(orders) {
  const done = orders.filter((o) => o.status !== 'cancelled');
  return {
    done,
    order_count: done.length,
    revenue: done.reduce((s, o) => s + o.total, 0),
    cancel_rate: orders.length ? round1(((orders.length - done.length) / orders.length) * 100) : 0,
    placed: orders.length,
  };
}

export async function adminReports(range = 'today') {
  const days = { today: 1, week: 7, month: 30 }[range] ?? 1;
  const now = new Date();
  const start = new Date(startOfToday().getTime() - (days - 1) * DAY);
  const shift = range === 'today' ? 7 * DAY : days * DAY;
  const prevStart = new Date(start.getTime() - shift);
  const prevEnd = new Date(now.getTime() - shift);

  const orders = await vendorOrders(prevStart);
  const at = (o) => new Date(o.created_at);
  const cur = summarize(orders.filter((o) => at(o) >= start));
  const prev = summarize(orders.filter((o) => at(o) >= prevStart && at(o) < prevEnd && at(o) < start));

  // 每 30 分鐘一格，從有訂單的最早一格到最晚一格；沒有訂單時顯示午餐時段
  const slotOf = (o) => { const d = at(o); return d.getHours() * 2 + (d.getMinutes() >= 30 ? 1 : 0); };
  const counts = new Map();
  for (const o of cur.done) counts.set(slotOf(o), (counts.get(slotOf(o)) ?? 0) + 1);
  const keys = [...counts.keys()];
  const first = keys.length ? Math.min(...keys) : 22;
  const last = keys.length ? Math.max(...keys) : 27;
  const label = (k) => `${String(Math.floor(k / 2)).padStart(2, '0')}:${k % 2 ? '30' : '00'}`;
  const orders_by_slot = [];
  for (let k = first; k <= last; k++) orders_by_slot.push({ slot: label(k), count: counts.get(k) ?? 0 });

  const top = new Map();
  for (const o of cur.done) {
    for (const i of o.items) {
      const t = top.get(i.item_id) ?? { name: loc(i.item_name), qty: 0, revenue: 0 };
      t.qty += i.quantity;
      t.revenue += i.subtotal;
      top.set(i.item_id, t);
    }
  }

  return {
    summary: {
      order_count: cur.order_count, revenue: cur.revenue, cancel_rate: cur.cancel_rate,
      avg_wait_minutes: null, // 後端沒有記每張單做好的時間，算不出來
      delta_orders: pct(cur.order_count, prev.order_count), delta_revenue: pct(cur.revenue, prev.revenue),
      delta_wait: null, delta_cancel: prev.placed && cur.placed ? round1(cur.cancel_rate - prev.cancel_rate) : null,
    },
    orders_by_slot,
    top_items: [...top.values()].sort((a, b) => b.qty - a.qty || b.revenue - a.revenue).slice(0, 5),
  };
}

// ======================= 平台管理（admin） =======================
export async function platformOverview() {
  const o = await http('GET', '/admin/overview');
  return {
    stats: {
      restaurant_count: o.vendors.length,
      accepting_count: o.vendors.filter((row) => row.vendor.is_accepting_orders).length,
      orders_today: o.orders_today,
      users: o.customer_count,
    },
    restaurants: o.vendors.map((row) => ({ ...toRestaurant(row.vendor), owner_account: row.staff_accounts.join(', '), today_order_count: row.orders_today })),
  };
}

// 開一家新店：店家資料和登入帳號一起建立。data：{ vendor: {...後端 VendorCreate}, staff: { student_id, email, phone_number, password } }
export async function platformCreateVendor(data) {
  return http('POST', '/admin/vendors', data);
}

// ======================= 照片上傳 =======================
// 先縮到長邊 1280px 的 JPEG，再把檔案送到 POST /api/uploads，回傳 { url: '/uploads/...' }
export async function uploadImage(file) {
  const canvas = await shrinkImage(file, 1280);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82));
  if (!blob) throw new Error(en() ? 'This photo could not be processed' : '這張照片處理失敗，請換一張');
  return send('POST', '/uploads', { blob });
}
