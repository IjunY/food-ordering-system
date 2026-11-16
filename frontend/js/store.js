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
