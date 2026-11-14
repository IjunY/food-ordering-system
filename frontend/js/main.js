import { addRoute, render, setGuard, startEvents } from './router.js';
import { session, cart, homeOf } from './store.js';
import { setLang, getLang } from './i18n.js';
import { USE_MOCK } from './api.js';
import { resetMockDb, login } from './mock/api.js';
import * as P from './pages/customer.js';
import * as A from './pages/admin.js';

// 路由表：畫面編號對應 Figma
addRoute('login', P.loginPage, { public: true });           // C01
addRoute('register', P.registerPage, { public: true });     // 註冊（新，Figma 還沒有）
addRoute('home', P.homePage);                               // C02
addRoute('r-:rid', P.restaurantPage);                       // C03
addRoute('item-:rid-:iid', P.itemPage);                   // C04
addRoute('cart', P.cartPage);                               // C05
addRoute('pay-:oid', P.payPage);                            // C06
addRoute('paid-:oid', P.paidPage);                          // C07
addRoute('order-:oid', P.orderStatusPage);                 // C08 / C09
addRoute('orders', P.ordersPage);                           // C10
addRoute('profile', P.profilePage);                         // C11
addRoute('admin-orders', A.adminBoard, { staff: true });    // A01
addRoute('admin-menu', A.adminMenu, { staff: true });       // A02 / A03
addRoute('admin-settings', A.adminSettings, { staff: true });// A04
addRoute('admin-reports', A.adminReports, { staff: true }); // A05
addRoute('admin-platform', A.adminPlatform, { admin: true });// A06

setGuard((opts) => {
  const user = session.get()?.user;
  if (opts.public) return user ? homeOf(user.role) : null;
  if (!user) return 'login';
  if (opts.admin && user.role !== 'admin') return homeOf(user.role);
  if (opts.staff && user.role !== 'staff') return homeOf(user.role);
  return null;
});

// Demo 用的網址參數（只在假資料模式有效）：
//   ?lang=en            切成英文
//   ?as=customer|staff|admin   直接以該身分登入
//   ?reset=1            清掉示範資料、購物車與登入
async function applyDemoParams() {
  const q = new URLSearchParams(location.search);
  if (q.get('lang')) setLang(q.get('lang') === 'en' ? 'en' : 'zh');
  if (!USE_MOCK) return;
  if (q.get('reset')) { resetMockDb(); session.clear(); cart.clear(); }
  const as = q.get('as');
  if (as) {
    const res = await login(as === 'customer' ? '112012345' : as);
    session.set({ access_token: res.access_token, user: res.user });
  }
}

await applyDemoParams();
setLang(getLang());
startEvents();
render();
