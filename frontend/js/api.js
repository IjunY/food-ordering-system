// 前端唯一的資料入口。頁面只呼叫這裡的函式，不直接 fetch。
//
// 開機時先問 /api/health：
// - 有真後端（用 uvicorn 開，網址同一個）→ 登入、註冊、下單、訂單、店家接單看板、接單開關走 js/real/api.js
// - 沒有（直接開檔案、python -m http.server、claude.ai 上的示範頁）→ 全部用 js/mock/api.js 的資料
// 餐廳與菜單的內容（清大學餐的真實店家）兩種情況都來自 js/mock/data.js；真後端模式下「是否接單」以後端為準。
// 等候時間、付款、店家其餘設定、菜單管理、報表、平台管理兩種情況都是假資料。
//
// 使用教學進行中（練習模式）時，下單、付款、訂單、接單看板一律走假資料：
// 練習下的單不會送到真的店家，店家練習接單也不會改到真的訂單。
import * as mock from './mock/api.js';
import * as real from './real/api.js';
import { inPractice } from './store.js';

export const USE_MOCK = !(await real.isAvailable());
const pick = (name) => (USE_MOCK || inPractice() ? mock[name] : real[name]);

export const api = {
  // auth（真後端）
  // 帳號不受練習模式影響，一律照有沒有真後端
  login: (student_id, password) => (USE_MOCK ? mock : real).login(student_id, password),
  register: (data) => (USE_MOCK ? mock.login(data.student_id, data.password) : real.register(data)),
  me: () => (USE_MOCK ? mock : real).getMe(),

  // menu：內容來自 mock/data.js；真後端模式下「是否接單」用後端的
  listRestaurants: (params = {}) => pick('listRestaurants')(params),
  getRestaurant: (id) => pick('getRestaurant')(id),
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

  // admin（店家）：接單看板與接單開關接真後端，其餘假資料
  admin: {
    listOrders: () => pick('adminListOrders')(),
    updateOrderStatus: (id, status) => pick('adminUpdateOrderStatus')(id, status),
    getRestaurant: () => pick('adminGetRestaurant')(),
    updateRestaurant: (patch) => pick('adminUpdateRestaurant')(patch),
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
