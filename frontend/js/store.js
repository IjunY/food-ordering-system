// 存在瀏覽器裡的狀態：登入資訊、購物車。localStorage 不能用時（私密視窗等）退回記憶體。
const memory = new Map();

export function read(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    if (v !== null) return JSON.parse(v);
  } catch { /* 退回記憶體 */ }
  return memory.has(key) ? structuredClone(memory.get(key)) : structuredClone(fallback);
}

export function write(key, value) {
  memory.set(key, structuredClone(value));
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* 只存在記憶體 */ }
}

export function remove(key) {
  memory.delete(key);
  try { localStorage.removeItem(key); } catch { /* 無妨 */ }
}

// { access_token, user: { id, role, student_id, restaurant_id } }
export const session = {
  get: () => read('session', null),
  set: (s) => write('session', s),
  clear: () => remove('session'),
};

// 使用教學（js/tour.js）。進行中的教學：{ role, uid, i: 第幾步, path: 上一次停在哪頁, oid: 店家練習單 }
// 教學進行中＝練習模式：訂單相關的 API 一律走假資料，不會真的下單或改到真的訂單（見 api.js）
export const tourState = {
  get: () => read('tour', null),
  set: (s) => write('tour', s),
  clear: () => remove('tour'),
};
export const inPractice = () => !!tourState.get();
// 看完（或略過）教學的帳號：每台瀏覽器各記一份
const doneKey = (user) => `tour_done:${user.role}:${user.student_id ?? user.id}`;
export const tourDone = {
  has: (user) => !!read(doneKey(user), false),
  set: (user) => write(doneKey(user), true),
};

// 各身分的起始頁：管理員只管平台，不進店家頁
export const homeOf = (role) => ({ customer: 'home', staff: 'admin-orders', admin: 'admin-platform' }[role] || 'login');

// 一張訂單限一家餐廳：restaurant_id 不同就要先清空
const EMPTY_CART = { restaurant_id: null, restaurant_name: '', items: [] };
export const cart = {
  get: () => read('cart', EMPTY_CART),
  set: (c) => write('cart', c),
  clear: () => write('cart', EMPTY_CART),
};
export const cartCount = (c) => c.items.reduce((s, i) => s + i.qty, 0);
export const cartTotal = (c) => c.items.reduce((s, i) => s + i.qty * i.unit_price, 0);
