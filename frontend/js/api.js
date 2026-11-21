// 前端唯一的資料入口。頁面只呼叫這裡的函式，不直接 fetch。
//
// 開機時先問 /api/health：
// - 有真後端（用 uvicorn 開，網址同一個）→ 全部走 js/real/api.js，資料庫是唯一的資料來源
// - 沒有（直接開檔案、python -m http.server、claude.ai 上的示範頁）→ 全部用 js/mock/api.js 的假資料
//
// 使用教學進行中（練習模式）時，顧客點餐的整個流程（餐廳、菜單、下單、付款、訂單）和店家的接單看板
// 一律走假資料：練習下的單不會送到真的店家，店家練習接單也不會改到真的訂單。
// 店家設定、菜單管理、報表在教學裡只是看看，照樣顯示自己店的真實資料。
import * as mock from './mock/api.js';
import * as real from './real/api.js';
import { inPractice } from './store.js';

export const USE_MOCK = !(await real.isAvailable());
// 顧客點餐流程與接單看板：練習時走假資料
const pick = (name) => (USE_MOCK || inPractice() ? mock[name] : real[name]);
// 其餘：只看有沒有真後端
const data = (name) => (USE_MOCK ? mock[name] : real[name]);

export const api = {
  // 帳號不受練習模式影響
  login: (student_id, password) => data('login')(student_id, password),
  register: (d) => (USE_MOCK ? mock.login(d.student_id, d.password) : real.register(d)),
  // 第三個參數：第一次登入時選的登入帳號（之後不能改）
  changePassword: (current, next, newStudentId) => data('changePassword')(current, next, newStudentId),
  // 忘記密碼（寄重設連結）：只有真後端有，假資料模式是 null
  forgotPassword: USE_MOCK ? null : (account) => real.forgotPassword(account),
  resetPassword: (token, next) => real.resetPassword(token, next),
  me: () => data('getMe')(),

  // 餐廳與菜單
  listRestaurants: (params = {}) => pick('listRestaurants')(params),
  getRestaurant: (id) => pick('getRestaurant')(id),
  getMenu: (id) => pick('getMenu')(id),
  getWaitEstimate: (id) => pick('getWaitEstimate')(id),

  // 訂單
  createOrder: (payload) => pick('createOrder')(payload),
  getOrder: (id) => pick('getOrder')(id),
  listMyOrders: () => pick('listMyOrders')(),

  // 上傳照片：真後端存成檔案（POST /api/uploads）；假資料模式存在瀏覽器
  uploadImage: (file) => data('uploadImage')(file),

  // 付款：真後端導到後端設定的金流商（LINE Pay sandbox 或模擬付款頁）；練習時是假的，一律成功
  listPaymentMethods: () => pick('listPaymentMethods')(),
  pay: (order_id, method) => pick('pay')(order_id, method),

  // 店家後台
  admin: {
    listOrders: () => pick('adminListOrders')(),
    updateOrderStatus: (id, status) => pick('adminUpdateOrderStatus')(id, status),
    getRestaurant: () => data('adminGetRestaurant')(),
    updateRestaurant: (patch) => data('adminUpdateRestaurant')(patch),
    listMenuItems: () => data('adminListMenuItems')(),
    saveMenuItem: (item) => data('adminSaveMenuItem')(item),
    patchMenuItem: (id, patch) => data('adminPatchMenuItem')(id, patch),
    deleteMenuItem: (id) => data('adminDeleteMenuItem')(id),
    reports: (range) => data('adminReports')(range),
  },

  // 平台管理（role = admin）
  platform: {
    overview: () => data('platformOverview')(),
    // 開新店（店家資料＋登入帳號）：只有真後端有
    createVendor: USE_MOCK ? null : (d) => real.platformCreateVendor(d),
    // 停權／核准：只有假資料有（後端的管理員只看不改店家）
    setRestaurantStatus: USE_MOCK ? (id, status) => mock.platformSetRestaurantStatus(id, status) : null,
  },
};
