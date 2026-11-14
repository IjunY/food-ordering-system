// 前端唯一的資料入口。頁面只呼叫這裡的函式，不直接 fetch。
//
// 開機時先問 /api/health：
// - 有真後端（用 uvicorn 開，網址同一個）→ 登入、註冊、下單、訂單、店家接單看板走 js/real/api.js
// - 沒有（直接開檔案、python -m http.server、claude.ai 上的示範頁）→ 全部用 js/mock/api.js 的假資料
// 其餘功能（餐廳、菜單、等候時間、付款、店家設定、菜單管理、報表、平台管理）兩種情況都是假資料。
import * as mock from './mock/api.js';
import * as real from './real/api.js';

export const USE_MOCK = !(await real.isAvailable());
const pick = (name) => (USE_MOCK ? mock[name] : real[name]);

export const api = {
  // auth（真後端）
  login: (student_id, password) => pick('login')(student_id, password),
  register: (data) => (USE_MOCK ? mock.login(data.student_id, data.password) : real.register(data)),
  me: () => pick('getMe')(),

  // menu（假資料：菜單畫面先沿用示範資料）
  listRestaurants: (params = {}) => mock.listRestaurants(params),
  getRestaurant: (id) => mock.getRestaurant(id),
  getMenu: (id) => mock.getMenu(id),
  getWaitEstimate: (id) => mock.getWaitEstimate(id),

  // orders（真後端）
  createOrder: (payload) => pick('createOrder')(payload),
  getOrder: (id) => pick('getOrder')(id),
  listMyOrders: () => pick('listMyOrders')(),

  // 上傳圖片：真後端還沒有 POST /api/uploads，先用假資料（存在瀏覽器）
  uploadImage: (file) => mock.uploadImage(file),

  // payments（模擬付款；真後端模式只記在這台瀏覽器）
  listPaymentMethods: () => mock.listPaymentMethods(),
  pay: (order_id, method) => pick('pay')(order_id, method),

  // admin（店家）：接單看板接真後端，其餘假資料
  admin: {
    listOrders: () => pick('adminListOrders')(),
    updateOrderStatus: (id, status) => pick('adminUpdateOrderStatus')(id, status),
    getRestaurant: () => mock.adminGetRestaurant(),
    updateRestaurant: (patch) => mock.adminUpdateRestaurant(patch),
    listMenuItems: () => mock.adminListMenuItems(),
    saveMenuItem: (item) => mock.adminSaveMenuItem(item),
    patchMenuItem: (id, patch) => mock.adminPatchMenuItem(id, patch),
    deleteMenuItem: (id) => mock.adminDeleteMenuItem(id),
    reports: (range) => mock.adminReports(range),
  },

  // 平台管理（role = admin）：假資料
  platform: {
    listRestaurants: () => mock.platformListRestaurants(),
    setRestaurantStatus: (id, status) => mock.platformSetRestaurantStatus(id, status),
  },
};
