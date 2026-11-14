// Demo 假資料。{ zh, en } 欄位會依目前語言換成字串（等同真後端依 Accept-Language 回傳）。
// 餐廳名稱、價格、等候時間全是示範用，不代表真實店家。

const SPICE = {
  id: 'spice', name: { zh: '辣度', en: 'Spice level' }, required: true, max_select: 1,
  choices: [
    { id: 'none', label: { zh: '不辣', en: 'Not spicy' }, price_delta: 0 },
    { id: 'mild', label: { zh: '小辣', en: 'Mild' }, price_delta: 0 },
    { id: 'hot', label: { zh: '大辣', en: 'Hot' }, price_delta: 0 },
  ],
};
const ADDON = {
  id: 'addon', name: { zh: '加點', en: 'Add-ons' }, required: false, max_select: 2,
  choices: [
    { id: 'rice', label: { zh: '加飯', en: 'Extra rice' }, price_delta: 0 },
    { id: 'egg', label: { zh: '加滷蛋', en: 'Braised egg' }, price_delta: 15 },
  ],
};
const ICE = {
  id: 'ice', name: { zh: '冰塊', en: 'Ice' }, required: true, max_select: 1,
  choices: [
    { id: 'regular', label: { zh: '正常冰', en: 'Regular ice' }, price_delta: 0 },
    { id: 'less', label: { zh: '少冰', en: 'Less ice' }, price_delta: 0 },
    { id: 'none', label: { zh: '去冰', en: 'No ice' }, price_delta: 0 },
  ],
};

const item = (id, category_id, name, description, price, prep_minutes, option_groups = [], extra = {}) => ({
  id, category_id, name, description, price, prep_minutes, option_groups,
  is_available: true, is_sold_out: false, image_url: null, ...extra,
});

export const SEED_RESTAURANTS = [
  {
    id: 'r1', area: 'shuimu', status: 'active', owner_account: 'shuimu_buffet', today_order_count: 128,
    name: { zh: '水木自助餐', en: 'Shuimu Buffet' },
    location: { zh: '水木生活中心 1F', en: 'Shuimu Center 1F' },
    location_detail: { zh: '水木生活中心 1F（近水木書苑）', en: 'Shuimu Center 1F (by the bookstore)' },
    description: { zh: '家常自助餐與便當，每日現做、提供素食選項。', en: 'Home-style buffet and bento boxes, made fresh daily, with vegetarian options.' },
    opening_hours_label: { zh: '10:30–13:30、16:30–19:30', en: '10:30–13:30, 16:30–19:30' },
    opening_hours: [
      { days: { zh: '週一至週五', en: 'Mon–Fri' }, hours: { zh: '10:30–13:30、16:30–19:30', en: '10:30–13:30, 16:30–19:30' } },
      { days: { zh: '週六', en: 'Sat' }, hours: { zh: '10:30–13:30', en: '10:30–13:30' } },
      { days: { zh: '週日、國定假日', en: 'Sun & holidays' }, hours: { zh: '公休', en: 'Closed' } },
    ],
    phone: '03-571-xxxx', is_open: true, is_accepting_orders: true,
    allow_cash_on_pickup: true, allow_scheduled_pickup: false, concurrent_capacity: 3, pickup_hold_minutes: 30,
    base_wait: 2, base_queue: 0, image_url: null, cover_image_url: null,
  },
  {
    id: 'r2', area: 'fengyun', status: 'active', owner_account: 'fengyun_noodle', today_order_count: 96,
    name: { zh: '風雲樓麵食館', en: 'Fengyun Noodle House' },
    location: { zh: '風雲樓 1F', en: 'Fengyun Hall 1F' },
    location_detail: { zh: '風雲樓 1F', en: 'Fengyun Hall 1F' },
    description: { zh: '牛肉麵、炸醬麵與手工餛飩。', en: 'Beef noodle soup, zhajiang noodles and handmade wontons.' },
    opening_hours_label: { zh: '11:00–14:00、17:00–20:00', en: '11:00–14:00, 17:00–20:00' },
    opening_hours: [], phone: '03-571-xxxx', is_open: true, is_accepting_orders: true,
    allow_cash_on_pickup: true, allow_scheduled_pickup: true, concurrent_capacity: 4, pickup_hold_minutes: 30,
    base_wait: 14, base_queue: 6, image_url: null, cover_image_url: null,
  },
  {
    id: 'r3', area: 'snack', status: 'active', owner_account: 'snack_brunch', today_order_count: 143,
    name: { zh: '小吃部早午餐', en: 'Snack Bar Brunch' },
    location: { zh: '學生活動中心 1F', en: 'Student Activity Center 1F' },
    location_detail: { zh: '學生活動中心 1F', en: 'Student Activity Center 1F' },
    description: { zh: '蛋餅、漢堡與現煮豆漿。', en: 'Egg crepes, burgers and fresh soy milk.' },
    opening_hours_label: { zh: '07:00–14:00', en: '07:00–14:00' },
    opening_hours: [], phone: '03-571-xxxx', is_open: true, is_accepting_orders: true,
    allow_cash_on_pickup: true, allow_scheduled_pickup: false, concurrent_capacity: 3, pickup_hold_minutes: 30,
    base_wait: 25, base_queue: 11, image_url: null, cover_image_url: null,
  },
  {
    id: 'r4', area: 'shuimu', status: 'active', owner_account: 'shuimu_curry', today_order_count: 45,
    name: { zh: '水木咖哩屋', en: 'Shuimu Curry House' },
    location: { zh: '水木生活中心 B1', en: 'Shuimu Center B1' },
    location_detail: { zh: '水木生活中心 B1', en: 'Shuimu Center B1' },
    description: { zh: '日式咖哩飯，晚餐時段營業。', en: 'Japanese curry rice, open for dinner.' },
    opening_hours_label: { zh: '17:00–20:00', en: '17:00–20:00' },
    opening_hours: [], phone: '03-571-xxxx', is_open: false, is_accepting_orders: true,
    allow_cash_on_pickup: true, allow_scheduled_pickup: false, concurrent_capacity: 2, pickup_hold_minutes: 30,
    base_wait: 8, base_queue: 0, image_url: null, cover_image_url: null,
  },
  {
    id: 'r5', area: 'other', status: 'pending', owner_account: 'nthu_cafe', today_order_count: 0,
    name: { zh: '清華咖啡', en: 'Tsing Hua Café' },
    location: { zh: '綜合二館 1F', en: 'General Building II 1F' },
    location_detail: { zh: '綜合二館 1F', en: 'General Building II 1F' },
    description: { zh: '咖啡與輕食。', en: 'Coffee and light meals.' },
    opening_hours_label: { zh: '08:00–17:00', en: '08:00–17:00' },
    opening_hours: [], phone: '03-571-xxxx', is_open: false, is_accepting_orders: false,
    allow_cash_on_pickup: false, allow_scheduled_pickup: false, concurrent_capacity: 2, pickup_hold_minutes: 30,
    base_wait: 5, base_queue: 0, image_url: null, cover_image_url: null,
  },
];

export const SEED_MENUS = {
  r1: {
    categories: [
      { id: 'bento', name: { zh: '便當', en: 'Bento' } },
      { id: 'single', name: { zh: '單點', en: 'À la carte' } },
      { id: 'soup', name: { zh: '湯品', en: 'Soups' } },
      { id: 'drink', name: { zh: '飲料', en: 'Drinks' } },
    ],
    items: [
      item('m1', 'bento', { zh: '招牌雞腿便當', en: 'Signature Chicken Leg Bento' }, { zh: '酥炸雞腿、三樣配菜、白飯，可免費加飯', en: 'Crispy fried chicken leg, three sides, rice; free extra rice' }, 95, 8, [SPICE, ADDON]),
      item('m2', 'bento', { zh: '滷排骨便當', en: 'Braised Pork Chop Bento' }, { zh: '古早味滷排骨、滷蛋、兩樣配菜', en: 'Classic braised pork chop, braised egg, two sides' }, 85, 7, [SPICE, ADDON]),
      item('m3', 'bento', { zh: '素食什錦便當', en: 'Vegetarian Medley Bento' }, { zh: '當季蔬菜、豆包、糙米飯', en: 'Seasonal vegetables, tofu skin, brown rice' }, 80, 6, [SPICE], { is_sold_out: true }),
      item('m4', 'bento', { zh: '紅燒牛腩飯', en: 'Braised Beef Brisket Rice' }, { zh: '慢燉牛腩、紅蘿蔔、白飯', en: 'Slow-braised beef brisket, carrots, rice' }, 110, 10, [SPICE, ADDON]),
      item('m5', 'single', { zh: '燙青菜', en: 'Blanched Greens' }, { zh: '當日青菜淋肉燥', en: 'Greens of the day with minced pork sauce' }, 35, 3),
      item('m6', 'single', { zh: '滷蛋', en: 'Braised Egg' }, { zh: '醬香滷蛋一顆', en: 'One soy-braised egg' }, 15, 1),
      item('m7', 'soup', { zh: '味噌湯', en: 'Miso Soup' }, { zh: '豆腐、海帶芽', en: 'Tofu and wakame' }, 30, 3),
      item('m8', 'drink', { zh: '冰紅茶', en: 'Iced Black Tea' }, { zh: '古早味紅茶', en: 'Classic black tea' }, 25, 1, [ICE]),
      item('m9', 'drink', { zh: '豆漿', en: 'Soy Milk' }, { zh: '微糖豆漿', en: 'Lightly sweetened soy milk' }, 25, 1, [ICE]),
    ],
  },
  r2: {
    categories: [
      { id: 'noodle', name: { zh: '麵食', en: 'Noodles' } },
      { id: 'side', name: { zh: '小菜', en: 'Sides' } },
    ],
    items: [
      item('n1', 'noodle', { zh: '紅燒牛肉麵', en: 'Braised Beef Noodle Soup' }, { zh: '牛腱、牛肋、手工寬麵', en: 'Beef shank and rib, hand-cut wide noodles' }, 150, 9, [SPICE]),
      item('n2', 'noodle', { zh: '炸醬麵', en: 'Zhajiang Noodles' }, { zh: '豆干肉燥炸醬、小黃瓜', en: 'Pork and tofu bean sauce, cucumber' }, 90, 6, [SPICE]),
      item('n3', 'noodle', { zh: '鮮蝦餛飩湯', en: 'Shrimp Wonton Soup' }, { zh: '手工鮮蝦餛飩八顆', en: 'Eight handmade shrimp wontons' }, 80, 6),
      item('n4', 'side', { zh: '燙青菜', en: 'Blanched Greens' }, { zh: '當日青菜', en: 'Greens of the day' }, 35, 3),
    ],
  },
  r3: {
    categories: [
      { id: 'brunch', name: { zh: '早午餐', en: 'Brunch' } },
      { id: 'drink', name: { zh: '飲料', en: 'Drinks' } },
    ],
    items: [
      item('b1', 'brunch', { zh: '火腿蛋餅', en: 'Ham Egg Crepe' }, { zh: '手工餅皮、火腿、蛋', en: 'Handmade crepe, ham, egg' }, 45, 5),
      item('b2', 'brunch', { zh: '培根起司漢堡', en: 'Bacon Cheeseburger' }, { zh: '培根、起司、生菜', en: 'Bacon, cheese, lettuce' }, 65, 7),
      item('b3', 'brunch', { zh: '薯餅', en: 'Hash Brown' }, { zh: '現炸薯餅兩片', en: 'Two crispy hash browns' }, 30, 4),
      item('b4', 'drink', { zh: '豆漿', en: 'Soy Milk' }, { zh: '現煮豆漿', en: 'Freshly made soy milk' }, 25, 1, [ICE]),
      item('b5', 'drink', { zh: '奶茶', en: 'Milk Tea' }, { zh: '紅茶加鮮奶', en: 'Black tea with fresh milk' }, 35, 2, [ICE]),
    ],
  },
  r4: {
    categories: [{ id: 'curry', name: { zh: '咖哩飯', en: 'Curry rice' } }],
    items: [
      item('c1', 'curry', { zh: '豬排咖哩飯', en: 'Pork Cutlet Curry Rice' }, { zh: '酥炸豬排、日式咖哩', en: 'Crispy pork cutlet, Japanese curry' }, 110, 8, [SPICE]),
      item('c2', 'curry', { zh: '雞肉咖哩飯', en: 'Chicken Curry Rice' }, { zh: '燉雞腿肉、馬鈴薯', en: 'Stewed chicken thigh, potatoes' }, 100, 7, [SPICE]),
    ],
  },
  r5: { categories: [], items: [] },
};

export const PAYMENT_METHODS = [
  { method: 'line_pay', short: 'LINE', label: { zh: 'LINE Pay', en: 'LINE Pay' }, hint: { zh: '模擬付款，不會真的扣款', en: 'Mock payment, no real charge' } },
  { method: 'apple_pay', short: 'Pay', label: { zh: 'Apple Pay', en: 'Apple Pay' }, hint: { zh: '模擬付款，不會真的扣款', en: 'Mock payment, no real charge' } },
  { method: 'credit_card', short: { zh: '卡', en: 'Card' }, label: { zh: '信用卡', en: 'Credit card' }, hint: { zh: '模擬付款，不會真的扣款', en: 'Mock payment, no real charge' } },
  { method: 'cash_on_pickup', short: { zh: '現金', en: 'Cash' }, label: { zh: '到店付款', en: 'Pay at pickup' }, hint: { zh: '取餐時在櫃台付款', en: 'Pay at the counter when you pick up' } },
];

export const USERS = {
  customer: { id: 'u1', role: 'customer', name: { zh: '王小明', en: 'Wang Xiao-Ming' }, first_name: { zh: '王小明', en: 'Xiao-Ming' }, department: { zh: '資工系', en: 'Computer Science' } },
  staff: { id: 's1', role: 'staff', restaurant_id: 'r1', name: { zh: '王小明（店長）', en: 'Wang Xiao-Ming (manager)' }, first_name: { zh: '王小明', en: 'Xiao-Ming' }, department: { zh: '水木餐廳', en: 'Shuimu Dining' } },
  admin: { id: 'a1', role: 'admin', restaurant_id: 'r1', name: { zh: '系統管理員', en: 'System admin' }, first_name: { zh: '管理員', en: 'Admin' }, department: { zh: '平台', en: 'Platform' } },
};

export const REPORTS = {
  summary: { order_count: 128, revenue: 11240, avg_wait_minutes: 7.5, cancel_rate: 2.3, delta_orders: 12, delta_revenue: 8, delta_wait: -1.2, delta_cancel: -0.4 },
  slots: [['10:30', 2], ['11:00', 5], ['11:30', 12], ['12:00', 27], ['12:30', 24], ['13:00', 9], ['16:30', 3], ['17:00', 6], ['17:30', 14], ['18:00', 15], ['18:30', 8], ['19:00', 3]],
  top_items: [
    { name: { zh: '招牌雞腿便當', en: 'Signature Chicken Leg Bento' }, qty: 46, revenue: 4370 },
    { name: { zh: '滷排骨便當', en: 'Braised Pork Chop Bento' }, qty: 31, revenue: 2635 },
    { name: { zh: '紅燒牛腩飯', en: 'Braised Beef Brisket Rice' }, qty: 18, revenue: 1980 },
    { name: { zh: '冰紅茶', en: 'Iced Black Tea' }, qty: 40, revenue: 1000 },
  ],
  platform: { restaurant_count: 5, pending_count: 1, orders_today: 412, delta_orders: 9, users: 2315, new_users_week: 87 },
};

// 開機時的示範訂單：接單看板上已經有幾張單，顧客也有幾筆歷史訂單
export function seedOrders() {
  const ago = (min) => new Date(Date.now() - min * 60000).toISOString();
  const line = (menu_item_id, name, qty, unit_price, options_label = null) => ({ menu_item_id, name, qty, unit_price, subtotal: qty * unit_price, options_label });
  const hist = (...pairs) => pairs.map(([status, min]) => ({ status, at: ago(min) }));
  const base = { pickup_type: 'asap', pickup_time: null, auto: false, payment_confirmed: true };
  return [
    { ...base, id: 'o28', pickup_number: 'A028', restaurant_id: 'r1', user_id: 'u9', status: 'ready', payment_method: 'line_pay', payment_status: 'paid', created_at: ago(12), estimated_ready_at: ago(2),
      items: [line('m1', { zh: '招牌雞腿便當', en: 'Signature Chicken Leg Bento' }, 2, 95)], total: 190, note: { zh: '分開裝', en: 'Pack separately' }, status_history: hist(['paid', 12], ['accepted', 11], ['preparing', 10], ['ready', 2]) },
    { ...base, id: 'o30', pickup_number: 'A030', restaurant_id: 'r1', user_id: 'u8', status: 'preparing', payment_method: 'line_pay', payment_status: 'paid', created_at: ago(7), estimated_ready_at: ago(-3),
      items: [line('m1', { zh: '招牌雞腿便當', en: 'Signature Chicken Leg Bento' }, 1, 95, { zh: '小辣、加飯', en: 'Mild, Extra rice' }), line('m2', { zh: '滷排骨便當', en: 'Braised Pork Chop Bento' }, 1, 85, { zh: '不辣', en: 'Not spicy' })], total: 180, note: null, status_history: hist(['paid', 7], ['accepted', 6], ['preparing', 5]) },
    { ...base, id: 'o32', pickup_number: 'A032', restaurant_id: 'r1', user_id: 'u7', status: 'preparing', payment_method: 'credit_card', payment_status: 'paid', created_at: ago(5), estimated_ready_at: ago(-4),
      items: [line('m4', { zh: '紅燒牛腩飯', en: 'Braised Beef Brisket Rice' }, 1, 110)], total: 110, note: { zh: '不要蔥蒜', en: 'No onion or garlic' }, status_history: hist(['paid', 5], ['accepted', 4], ['preparing', 3]) },
    { ...base, id: 'o33', pickup_number: 'A033', restaurant_id: 'r1', user_id: 'u6', status: 'paid', payment_method: 'apple_pay', payment_status: 'paid', created_at: ago(2), estimated_ready_at: ago(-8),
      items: [line('m2', { zh: '滷排骨便當', en: 'Braised Pork Chop Bento' }, 2, 85)], total: 170, note: { zh: '一份不要青椒', en: 'No green pepper in one' }, status_history: hist(['paid', 2]) },
    { ...base, id: 'o34', pickup_number: 'A034', restaurant_id: 'r1', user_id: 'u5', status: 'pending_payment', payment_method: 'cash_on_pickup', payment_status: 'unpaid', created_at: ago(1), estimated_ready_at: ago(-10),
      items: [line('m4', { zh: '紅燒牛腩飯', en: 'Braised Beef Brisket Rice' }, 1, 110), line('m8', { zh: '冰紅茶', en: 'Iced Black Tea' }, 1, 25)], total: 135, note: { zh: '飯少一點', en: 'Less rice' }, status_history: [] },
    { ...base, id: 'h1', pickup_number: 'B112', restaurant_id: 'r2', user_id: 'u1', status: 'picked_up', payment_method: 'line_pay', payment_status: 'paid', created_at: ago(60 * 19), estimated_ready_at: ago(60 * 19 - 12),
      items: [line('n1', { zh: '紅燒牛肉麵', en: 'Braised Beef Noodle Soup' }, 1, 150), line('n4', { zh: '燙青菜', en: 'Blanched Greens' }, 1, 35)], total: 185, note: null, status_history: hist(['paid', 1140], ['ready', 1128], ['picked_up', 1120]) },
    { ...base, id: 'h2', pickup_number: 'C087', restaurant_id: 'r3', user_id: 'u1', status: 'picked_up', payment_method: 'apple_pay', payment_status: 'paid', created_at: ago(60 * 52), estimated_ready_at: ago(60 * 52 - 8),
      items: [line('b1', { zh: '火腿蛋餅', en: 'Ham Egg Crepe' }, 1, 45), line('b4', { zh: '豆漿', en: 'Soy Milk' }, 1, 25)], total: 70, note: null, status_history: hist(['paid', 3120], ['picked_up', 3110]) },
    { ...base, id: 'h3', pickup_number: 'D020', restaurant_id: 'r4', user_id: 'u1', status: 'cancelled', payment_method: 'credit_card', payment_status: 'paid', created_at: ago(60 * 96), estimated_ready_at: ago(60 * 96 - 10),
      items: [line('c1', { zh: '豬排咖哩飯', en: 'Pork Cutlet Curry Rice' }, 1, 110)], total: 110, note: null, status_history: hist(['paid', 5760], ['cancelled', 5755]) },
  ];
}
