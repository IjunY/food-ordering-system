// 顧客端畫面 C01–C11＋註冊頁（紫色取餐券版）
import { api, USE_MOCK } from '../api.js';
import { t, setLang } from '../i18n.js';
import { session, cart, cartCount, cartTotal, homeOf } from '../store.js';
import { actions, forms, inputs, navigate, rerender, poll, toast, confirmDialog } from '../router.js';
import { icon } from '../icons.js';
import * as C from '../components.js';
import { maybeStartTour } from '../tour.js';
import { pickupSlots, slotAllowed } from '../pickup.js';

const { esc, money, unit, hhmm } = C;
const phone = (inner) => `<div class="phone">${inner}</div>`;

// 定時更新用：使用者正在打字時不重畫（重畫會打斷中文輸入法選字）
const idleRerender = () => {
  const a = document.activeElement;
  if (a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA')) return;
  rerender();
};

// 訂單狀態剛變的那一次重畫，券上的狀態要「跳」一下
const ACTIVE = ['pending_payment', 'paid', 'accepted', 'preparing', 'ready'];
const lastStatus = {};
function changed(o) {
  const was = lastStatus[o.id];
  lastStatus[o.id] = o.status;
  return !!was && was !== o.status;
}
const passHref = (o) => (o.status === 'pending_payment' && !o.payment_method ? `pay-${o.id}` : `order-${o.id}`);
const miniPass = (o) => C.Pass(o, { href: passHref(o), snapping: changed(o) });

// 共用動作
actions.back = () => (history.length > 1 ? history.back() : navigate('home'));
actions.go = (d) => navigate(d.to);
actions['set-lang'] = (d) => { setLang(d.lang); rerender(); };
actions.logout = () => { session.clear(); cart.clear(); C.navState.activeOrders = 0; navigate('login'); };
actions['toggle-password'] = (d, el) => {
  const input = document.getElementById(d.for);
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  el.setAttribute('aria-pressed', String(show));
  el.setAttribute('aria-label', t(show ? 'auth.pw_hide' : 'auth.pw_show'));
  el.innerHTML = icon(show ? 'eyeOff' : 'eye');
};

// ======================= C01 登入 =======================
// 標題裡的「NTHU」用黃色，呼應取餐號的字首
const brand = () => esc(t('app.name')).replace(/^NTHU/, '<span class="pfx">NTHU</span>');

export async function loginPage() {
  forgotSent = false;
  return phone(`<div class="auth">
    <section class="ahero"><div class="bar"><span></span>${C.LangSwitch()}</div>
      <h1>${brand()}</h1><p>${esc(t('login.lead'))}</p></section>
    <form class="acard" data-form="login" novalidate>
      <h2>${esc(t('login.title'))}</h2>
      ${C.TextField({ label: t('login.account'), name: 'student_id', num: true, extra: 'autocomplete="username" inputmode="text" autocapitalize="off" spellcheck="false"' })}
      ${C.TextField({ label: t('login.password'), name: 'password', type: 'password', reveal: true, extra: 'autocomplete="current-password"' })}
      ${C.Cta({ label: t('login.submit'), type: 'submit' })}
      <p class="alink"><a href="#forgot">${esc(t('login.forgot'))}</a></p>
      <p class="alink">${esc(t('login.no_account'))} <a href="#register">${esc(t('login.to_register'))}</a></p>
    </form>
  </div>`);
}
forms.login = async (fd, form) => {
  const id = String(fd.get('student_id') || '').trim();
  if (!id) { toast(t('login.need_id')); form.querySelector('[name=student_id]')?.focus(); return; }
  const res = await api.login(id, fd.get('password'));
  session.set({ access_token: res.access_token, user: res.user });
  // 管理員建立的帳號：先選自己的帳號、換密碼（設定完才開始使用教學）
  if (res.user.must_change_password || res.user.must_choose_username) { navigate('password'); return; }
  await maybeStartTour(res.user); // 這個帳號第一次登入：開始使用教學
  navigate(homeOf(res.user.role));
};

// ======================= 註冊 =======================
export async function registerPage() {
  const rule = `<ul class="checks" id="pw-rules"><li>${icon('dot')}${esc(t('register.pw_rule'))}</li></ul>`;
  return phone(`<div class="auth">
    <section class="ahero"><div class="bar"><a class="back" href="#login" aria-label="${esc(t('a11y.back'))}">${icon('back')}</a>${C.LangSwitch()}</div>
      <h1>${esc(t('register.title'))}</h1><p>${esc(t('register.lead'))}</p></section>
    <form class="acard" data-form="register" novalidate>
      ${C.TextField({ label: t('login.student_id'), name: 'student_id', num: true, extra: 'autocomplete="username" autocapitalize="off" spellcheck="false" maxlength="20"' })}
      ${C.TextField({ label: t('register.email'), name: 'email', type: 'email', extra: 'autocomplete="email"' })}
      <div class="field"><label for="f-email_code">${esc(t('register.code'))}</label>
        <div class="coderow">
          <div class="input"><input type="text" class="num" id="f-email_code" name="email_code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" aria-describedby="code-hint"></div>
          ${codeButton()}
        </div>
        <p class="hint" id="code-hint">${esc(t(codeState.sentTo ? 'register.code_sent' : 'register.code_hint', { email: codeState.sentTo }))}</p>
      </div>
      ${C.TextField({ label: t('register.phone'), name: 'phone_number', type: 'tel', num: true, extra: 'autocomplete="tel" inputmode="tel"' })}
      ${C.TextField({ label: t('login.password'), name: 'password', type: 'password', reveal: true, input: 'password-rule', extra: 'autocomplete="new-password" minlength="8" aria-describedby="pw-rules"', hint: rule })}
      ${C.Cta({ label: t('register.submit'), type: 'submit' })}
      <p class="alink">${esc(t('register.have_account'))} <a href="#login">${esc(t('register.to_login'))}</a></p>
    </form>
  </div>`);
}
// Email 驗證碼：按「寄驗證碼」後 60 秒內不能再按（後端也是一分鐘一封）
const CODE_COOLDOWN = 60;
const codeState = { sentTo: '', until: 0, timer: null };
const codeWait = () => Math.max(0, Math.ceil((codeState.until - Date.now()) / 1000));
function codeButton() {
  const wait = codeWait();
  const label = wait ? t('register.code_wait', { n: wait }) : t(codeState.sentTo ? 'register.code_resend' : 'register.code_send');
  return `<button type="button" class="btn btn--sm" id="code-btn" data-action="send-code"${wait ? ' disabled' : ''}>${esc(label)}</button>`;
}
// 倒數只改按鈕，不重畫整頁（不然打到一半的欄位會清掉）
function tickCodeButton() {
  clearInterval(codeState.timer);
  codeState.timer = setInterval(() => {
    const btn = document.getElementById('code-btn');
    if (btn) btn.outerHTML = codeButton();
    if (!codeWait()) clearInterval(codeState.timer);
  }, 1000);
}
// 後端的錯誤訊息（英文）→ 翻譯好的說明
const SIGNUP_ERRORS = [
  [/email is already registered/i, 'register.err.email_taken'],
  [/student ID is already registered|student ID or email/i, 'register.err.id_taken'],
  [/code was just sent/i, 'register.err.wait'],
  [/code is incorrect/i, 'register.err.code_wrong'],
  [/code has expired|was not sent/i, 'register.err.code_expired'],
];
const signupError = (err) => {
  const hit = SIGNUP_ERRORS.find(([re]) => re.test(err.message || ''));
  return hit ? t(hit[1]) : err.message || String(err);
};
actions['send-code'] = async (_, el) => {
  const input = document.querySelector('[name=email]');
  const email = String(input?.value || '').trim();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { toast(t('register.need_email')); input?.focus(); return; }
  el.disabled = true;
  try {
    const res = await api.sendSignupCode(email);
    codeState.sentTo = email;
    codeState.until = Date.now() + CODE_COOLDOWN * 1000;
    const hint = document.getElementById('code-hint');
    if (hint) hint.textContent = t('register.code_sent', { email });
    // 假資料模式不會寄信：直接把驗證碼告訴使用者
    toast(res?.demo_code ? t('register.code_demo', { code: res.demo_code }) : t('register.code_toast', { email }));
    document.querySelector('[name=email_code]')?.focus();
  } catch (err) {
    if (err.status === 429) codeState.until = Date.now() + CODE_COOLDOWN * 1000;
    toast(signupError(err));
  } finally {
    const btn = document.getElementById('code-btn');
    if (btn) btn.outerHTML = codeButton();
    if (codeWait()) tickCodeButton();
  }
};

// 邊打邊檢查密碼長度，不重畫（焦點留在欄位裡）
inputs['password-rule'] = (el) => {
  const li = document.querySelector('#pw-rules li');
  if (!li) return;
  const ok = el.value.length >= 8;
  if (li.classList.contains('ok') === ok) return;
  li.classList.toggle('ok', ok);
  li.querySelector('svg').outerHTML = icon(ok ? 'check' : 'dot');
};
forms.register = async (fd, form) => {
  const data = Object.fromEntries(['student_id', 'email', 'email_code', 'phone_number'].map((k) => [k, String(fd.get(k) || '').trim()]));
  data.password = String(fd.get('password') || '');
  const empty = Object.keys(data).find((k) => !data[k]);
  if (empty === 'email_code') { toast(t(codeState.sentTo ? 'register.need_code' : 'register.send_first')); form.querySelector('[name=email_code]')?.focus(); return; }
  if (empty) { toast(t('register.need_all')); form.querySelector(`[name=${empty}]`)?.focus(); return; }
  if (!/^[0-9]{6}$/.test(data.email_code)) { toast(t('register.code_format')); form.querySelector('[name=email_code]')?.focus(); return; }
  if (data.password.length < 8) { toast(t('register.short_password')); form.querySelector('[name=password]')?.focus(); return; }
  let res;
  try { res = await api.register(data); } catch (err) { toast(signupError(err)); return; }
  Object.assign(codeState, { sentTo: '', until: 0 });
  session.set({ access_token: res.access_token, user: res.user });
  await maybeStartTour(res.user);
  navigate(homeOf(res.user.role));
};

// ======================= 設定新密碼 =======================
// 管理員建立的店家帳號第一次登入時一定會到這裡（main.js 的 guard）：選自己的登入帳號（之後不能改）和密碼。
// 其他時候是一般的「修改密碼」（個人頁、店家後台上方的連結）。換完密碼，舊的登入就失效
const pwRule = () => `<ul class="checks" id="pw-rules"><li>${icon('dot')}${esc(t('register.pw_rule'))}</li></ul>`;
export async function passwordPage() {
  const u = session.get()?.user;
  const pickId = !!u?.must_choose_username;
  const forced = pickId || !!u?.must_change_password;
  const lead = pickId ? 'setup.lead' : forced ? 'password.lead_forced' : 'password.lead';
  return phone(`<div class="auth">
    <section class="ahero"><div class="bar">${forced ? '<span></span>' : `<a class="back" href="#${homeOf(u?.role)}" aria-label="${esc(t('a11y.back'))}">${icon('back')}</a>`}${C.LangSwitch()}</div>
      <h1>${esc(t(pickId ? 'setup.title' : 'password.title'))}</h1><p>${esc(t(lead))}</p></section>
    <form class="acard" data-form="password" novalidate>
      <div class="form-err" aria-live="assertive"></div>
      ${pickId ? C.TextField({ label: t('setup.username'), name: 'new_student_id', extra: 'autocomplete="username" autocapitalize="off" spellcheck="false" maxlength="20" aria-describedby="id-rule"', hint: `<p class="hint" id="id-rule">${esc(t('setup.username_rule'))}</p>` }) : ''}
      ${C.TextField({ label: t(pickId ? 'setup.current' : 'password.current'), name: 'current_password', type: 'password', reveal: true, extra: 'autocomplete="current-password"' })}
      ${C.TextField({ label: t('password.new'), name: 'new_password', type: 'password', reveal: true, input: 'password-rule', extra: 'autocomplete="new-password" minlength="8" aria-describedby="pw-rules"', hint: pwRule() })}
      ${C.TextField({ label: t('password.confirm'), name: 'confirm_password', type: 'password', reveal: true, extra: 'autocomplete="new-password" minlength="8"' })}
      ${USE_MOCK ? `<p class="hint">${esc(t('password.mock'))}</p>` : ''}
      ${C.Cta({ label: t('password.submit'), type: 'submit' })}
      ${forced ? `<p class="alink"><button type="button" class="textlink" data-action="logout">${esc(t('profile.logout'))}</button></p>` : ''}
    </form>
  </div>`);
}
// 錯誤顯示在表單最上面（不重畫，打好的字不會被清掉），游標移到要改的那一欄
function formError(form, text, field) {
  form.querySelector('.form-err').innerHTML = C.Note({ text, kind: 'err' });
  form.querySelector(`[name=${field}]`)?.focus();
}
// 新密碼的兩欄：長度、兩次一樣。不對就顯示錯誤並回傳 null
function readNewPassword(fd, form) {
  const next = String(fd.get('new_password') || '');
  if (next.length < 8) { formError(form, t('register.short_password'), 'new_password'); return null; }
  if (next !== fd.get('confirm_password')) { formError(form, t('password.mismatch'), 'confirm_password'); return null; }
  return next;
}
// 後端拒絕的原因（real/api.js 標上的 code）→ 翻譯好的訊息、要改的欄位
const PASSWORD_ERRORS = {
  wrong_current: ['password.wrong_current', 'current_password'],
  same: ['password.same', 'new_password'],
  id_taken: ['password.id_taken', 'new_student_id'],
};
forms.password = async (fd, form) => {
  const newId = fd.has('new_student_id') ? String(fd.get('new_student_id') || '').trim() : null;
  if (newId !== null && !/^[A-Za-z0-9]{4,20}$/.test(newId)) return formError(form, t('setup.need_username'), 'new_student_id');
  const current = String(fd.get('current_password') || '');
  if (!current) return formError(form, t('password.need_current'), 'current_password');
  const next = readNewPassword(fd, form);
  if (next === null) return;
  if (next === current) return formError(form, t('password.same'), 'new_password');
  let res;
  try {
    res = await api.changePassword(current, next, newId);
  } catch (err) {
    const [key, field] = PASSWORD_ERRORS[err.code] ?? [];
    return formError(form, key ? t(key) : err.message || String(err), field ?? 'current_password');
  }
  session.set({ access_token: res.access_token, user: res.user });
  toast(newId ? t('setup.done', { id: res.user.student_id }) : t('password.done'));
  await maybeStartTour(res.user);
  navigate(homeOf(res.user.role));
};

// ======================= 忘記密碼 =======================
// 輸入登入帳號或 email → 後端把一次性的重設連結寄到帳號的 email。
// 不管帳號存不存在，畫面都一樣（不透露哪些帳號存在）
let forgotSent = false;
export async function forgotPage() {
  const head = `<section class="ahero"><div class="bar"><a class="back" href="#login" aria-label="${esc(t('a11y.back'))}">${icon('back')}</a>${C.LangSwitch()}</div>
      <h1>${esc(t('forgot.title'))}</h1><p>${esc(t(forgotSent ? 'forgot.sent_lead' : 'forgot.lead'))}</p></section>`;
  const back = `<p class="alink"><a href="#login">${esc(t('forgot.back'))}</a></p>`;
  // 假資料模式沒有寄信的後端
  if (!api.forgotPassword) return phone(`<div class="auth">${head}<div class="acard">${C.Note({ text: t('forgot.mock') })}${back}</div></div>`);
  if (forgotSent) {
    return phone(`<div class="auth">${head}<div class="acard">
      ${C.Note({ text: t('forgot.sent_note'), kind: 'ok', ic: 'check' })}
      ${back}
      <p class="alink">${esc(t('forgot.no_email'))} <button type="button" class="textlink" data-action="forgot-again">${esc(t('forgot.again'))}</button></p>
    </div></div>`);
  }
  return phone(`<div class="auth">${head}
    <form class="acard" data-form="forgot" novalidate>
      ${C.TextField({ label: t('forgot.account'), name: 'account', extra: 'autocomplete="username" autocapitalize="off" spellcheck="false" maxlength="255"' })}
      ${C.Cta({ label: t('forgot.submit'), type: 'submit' })}
      ${back}
    </form>
  </div>`);
}
forms.forgot = async (fd, form) => {
  const account = String(fd.get('account') || '').trim();
  if (!account) { toast(t('forgot.need')); form.querySelector('[name=account]')?.focus(); return; }
  await api.forgotPassword(account);
  forgotSent = true;
  rerender();
};
actions['forgot-again'] = () => { forgotSent = false; rerender(); };

// ======================= 從信裡的連結設定新密碼 =======================
// #reset-<token>：連結只能用一次、30 分鐘內有效；設定好就直接登入
export async function resetPage({ token }) {
  return phone(`<div class="auth">
    <section class="ahero"><div class="bar"><a class="back" href="#login" aria-label="${esc(t('a11y.back'))}">${icon('back')}</a>${C.LangSwitch()}</div>
      <h1>${esc(t('reset.title'))}</h1><p>${esc(t('reset.lead'))}</p></section>
    <form class="acard" data-form="reset" novalidate>
      <div class="form-err" aria-live="assertive"></div>
      <input type="hidden" name="token" value="${esc(token)}">
      ${C.TextField({ label: t('password.new'), name: 'new_password', type: 'password', reveal: true, input: 'password-rule', extra: 'autocomplete="new-password" minlength="8" aria-describedby="pw-rules"', hint: pwRule() })}
      ${C.TextField({ label: t('password.confirm'), name: 'confirm_password', type: 'password', reveal: true, extra: 'autocomplete="new-password" minlength="8"' })}
      ${C.Cta({ label: t('reset.submit'), type: 'submit' })}
      <p class="alink"><a href="#forgot">${esc(t('reset.new_link'))}</a></p>
    </form>
  </div>`);
}
forms.reset = async (fd, form) => {
  const next = readNewPassword(fd, form);
  if (next === null) return;
  let res;
  try {
    res = await api.resetPassword(String(fd.get('token')), next);
  } catch (err) {
    // 用過、過期或打錯的連結
    return formError(form, err.code === 'link_invalid' ? t('reset.invalid') : err.message || String(err), 'new_password');
  }
  // 這台裝置上原本登入的若是別人，購物車是他的
  if (session.get()?.user?.id !== res.user.id) cart.clear();
  session.set({ access_token: res.access_token, user: res.user });
  toast(t('password.done'));
  if (res.user.must_change_password || res.user.must_choose_username) { navigate('password'); return; }
  await maybeStartTour(res.user);
  navigate(homeOf(res.user.role));
};

// ======================= C02 首頁：取餐券＋攤位 =======================
const home = { location: 'all', sort: 'wait', q: '', list: [] };
const LOCATIONS = [['all', 'home.loc_all'], ['shuimu', 'home.loc_shuimu'], ['snack', 'home.loc_snack'], ['fengyun', 'home.loc_fengyun']];

function restaurantListHtml() {
  const q = home.q.trim().toLowerCase();
  const c = cart.get();
  const list = home.list.filter((r) => (home.location === 'all' || r.area === home.location) && (!q || r.name.toLowerCase().includes(q)));
  return list.length
    ? list.map((r) => C.StallCard(r, c.restaurant_id === r.id ? cartCount(c) : 0)).join('')
    : `<li class="empty">${esc(t('home.empty'))}</li>`;
}

export async function homePage() {
  const [list, orders] = await Promise.all([api.listRestaurants({ location: 'all', sort: home.sort }), api.listMyOrders().catch(() => [])]);
  home.list = list;
  const active = orders.filter((o) => ACTIVE.includes(o.status));
  C.navState.activeOrders = active.length;
  poll(idleRerender, active.length ? 5000 : 30000);
  const areas = LOCATIONS.map(([k, key]) => ({
    name: t(key), selected: home.location === k, action: 'home-location', data: { loc: k },
    count: k === 'all' ? list.length : list.filter((r) => r.area === k).length,
  }));
  return phone(`${C.TopBar({ title: t('nav.home') })}
    <main class="main">
      ${active.length ? `<div class="sec"><h2>${esc(t('home.passes'))}</h2></div><div class="stack">${active.map(miniPass).join('')}</div>` : ''}
      <div class="sec"><h2>${esc(t('home.all'))}</h2>${C.SampleTag()}</div>
      <div class="tools">
        <label class="input input--sm search">${icon('search')}<span class="visually-hidden">${esc(t('home.search_ph'))}</span>
          <input id="home-q" type="search" data-input="home-search" value="${esc(home.q)}" placeholder="${esc(t('home.search_ph'))}" autocomplete="off"></label>
        <button type="button" class="lnk" data-action="home-sort">${esc(t(home.sort === 'wait' ? 'home.sort_wait' : 'home.sort_name'))}</button>
      </div>
      ${C.Tabs(areas, { area: true, label: t('home.all') })}
      <ul class="sgrid" id="restaurant-list">${restaurantListHtml()}</ul>
    </main>
    ${C.BottomNav({ active: 'home' })}`);
}
actions['home-location'] = (d) => { home.location = d.loc; rerender(); };
actions['home-sort'] = () => { home.sort = home.sort === 'wait' ? 'name' : 'wait'; rerender(); };
inputs['home-search'] = (el) => {
  home.q = el.value;
  document.getElementById('restaurant-list').innerHTML = restaurantListHtml();
};

// ======================= C03 攤位頁：菜單 =======================
const selectedCategory = {};
const waitText = (w) => `${t('wait.minutes', { n: w.wait_minutes })} · ${t('home.ahead', { n: w.queue_count })}`;

export async function restaurantPage({ rid }) {
  const [r, menu, wait] = await Promise.all([api.getRestaurant(rid), api.getMenu(rid), api.getWaitEstimate(rid)]);
  const canOrder = r.is_open && r.is_accepting_orders;
  const cat = selectedCategory[rid] ?? menu.categories[0]?.id;
  const items = menu.categories.find((c) => c.id === cat)?.items ?? [];
  const c = cart.get();
  const mine = c.restaurant_id === rid ? c.items : [];
  const inCart = (id) => mine.filter((i) => i.menu_item_id === id).reduce((s, i) => s + i.qty, 0);
  const closedText = r.is_open ? t('restaurant.paused') : t('restaurant.closed_now', { hours: r.opening_hours_label });
  if (canOrder) {
    poll(async () => {
      const el = document.getElementById('wait-slot');
      if (el) el.textContent = waitText(await api.getWaitEstimate(rid));
    }, 30000);
  }
  return phone(`${C.TopBar({ title: r.name, back: true })}
    <main class="main" style="--sc:${C.tint(r.id)}">
      <section class="hero${canOrder ? '' : ' closed'}">
        ${C.Photo({ url: r.cover_image_url, alt: r.name, kind: 'cover' })}
        <div class="hcard">
          <h2>${esc(r.name)}</h2>
          ${r.description ? `<p class="desc">${esc(r.description)}</p>` : ''}
          <div class="chips">
            <span>${esc(r.location_detail)}</span><span>${esc(r.opening_hours_label)}</span>
            <span><b class="${canOrder ? 'on' : 'off'}">${esc(canOrder ? t('home.open') : r.is_open ? t('restaurant.paused') : t('wait.closed'))}</b></span>
            ${canOrder ? `<span id="wait-slot">${esc(waitText(wait))}</span>` : ''}
          </div>
          ${C.SampleTag()}
        </div>
      </section>
      ${canOrder ? '' : C.Note({ text: closedText })}
      ${C.Tabs(menu.categories.map((x) => ({ name: x.name, selected: x.id === cat, action: 'menu-category', data: { rid, cat: x.id } })), { sticky: true, label: r.name })}
      <ul class="igrid">${items.map((i) => C.ItemCard(i, rid, { inCart: inCart(i.id), canOrder })).join('') || `<li class="empty">${esc(t('menu.empty'))}</li>`}</ul>
    </main>
    ${c.items.length ? `<div class="dock">${C.Cta({ label: `${t('menu.checkout')} · ${t('cart.count', { n: cartCount(c) })}`, figure: money(cartTotal(c)), href: 'cart' })}</div>` : ''}`);
}
actions['menu-category'] = (d) => { selectedCategory[d.rid] = d.cat; rerender(); };

// ======================= C04 品項 =======================
const itemDraft = {}; // `${rid}/${iid}` → { sel: { groupId: [choiceId] }, qty, note }
const NOTE_MAX = 60;

async function loadItem(rid, iid) {
  const [r, menu] = await Promise.all([api.getRestaurant(rid), api.getMenu(rid)]);
  const item = menu.categories.flatMap((c) => c.items).find((i) => i.id === iid);
  return { r, item };
}
function draftFor(key, item) {
  return (itemDraft[key] ??= {
    sel: Object.fromEntries(item.option_groups.map((g) => [g.id, g.required ? [g.choices[0].id] : []])),
    qty: 1, note: '',
  });
}
function unitPrice(item, d) {
  return item.price + item.option_groups.flatMap((g) => g.choices.filter((c) => d.sel[g.id].includes(c.id))).reduce((s, c) => s + c.price_delta, 0);
}

export async function itemPage({ rid, iid }) {
  const { r, item } = await loadItem(rid, iid);
  if (!item) return phone(`${C.TopBar({ title: t('item.title'), back: true })}<main class="main"><p class="empty">${esc(t('common.not_found'))}</p></main>`);
  const key = `${rid}/${iid}`;
  const d = draftFor(key, item);
  const sold = item.is_sold_out || !item.is_available;
  const open = r.is_open && r.is_accepting_orders;
  const canOrder = open && !sold;
  const groups = item.option_groups.map((g) => `<fieldset class="ogroup"${canOrder ? '' : ' disabled'}>
      <legend>${esc(g.name)}<small>${esc(g.required ? t('item.required') : t('item.multi', { n: g.max_select }))}</small></legend>
      <div role="${g.required ? 'radiogroup' : 'group'}" aria-label="${esc(g.name)}">
      ${g.choices.map((c) => C.Choice({ label: c.label, aside: c.price_delta ? `+${unit(c.price_delta)}` : '', selected: d.sel[g.id].includes(c.id), multi: !g.required, action: 'pick-option', data: { key, group: g.id, choice: c.id, max: g.max_select, required: g.required ? 1 : 0 }, disabled: !canOrder })).join('')}
      </div>
    </fieldset>`).join('');
  const label = sold ? t('menu.sold_out') : open ? t('item.add') : t(r.is_open ? 'restaurant.paused' : 'wait.closed');
  return phone(`${C.TopBar({ title: item.name, back: true })}
    <main class="main itempage" style="--sc:${C.tint(r.id)}">
      <div class="himg">${C.Photo({ url: item.image_url, alt: item.name, kind: 'hero' })}${sold ? `<span class="sold sold--big">${esc(t('menu.sold_out'))}</span>` : ''}</div>
      <section class="ihead">
        <h2>${esc(item.name)}</h2><span class="p">${unit(item.price)}</span>
        <p class="mt">${esc(r.name)} · ${esc(r.location)} · ${esc(t('item.prep', { n: item.prep_minutes }))}</p>
        ${item.description ? `<p class="desc">${esc(item.description)}</p>` : ''}
        ${C.SampleTag()}
      </section>
      ${canOrder ? '' : C.Note({ text: t(sold ? 'item.sold_out_hint' : 'item.closed_hint'), kind: sold ? 'err' : '' })}
      ${groups}
      <div class="ogroup"><label class="legend" for="f-note">${esc(t('item.note'))}<small>${esc(t('item.note_optional'))}</small></label>
        <textarea id="f-note" name="note" rows="3" maxlength="${NOTE_MAX}" placeholder="${esc(t('item.note_ph'))}" data-input="item-note" data-key="${esc(key)}"${canOrder ? '' : ' disabled'}>${esc(d.note)}</textarea>
        <span class="hint cnt num" id="note-cnt">${d.note.length} / ${NOTE_MAX}</span></div>
      <div class="qrow"><span>${esc(t('item.qty'))}</span>${canOrder ? C.QtyStepper({ qty: d.qty, action: 'item-qty', data: { key }, min: 1, max: 20 }) : ''}</div>
    </main>
    <div class="dock">${C.Cta({ label, figure: canOrder ? money(unitPrice(item, d) * d.qty) : '', action: 'add-to-cart', data: { rid, iid }, disabled: !canOrder })}</div>`);
}
actions['pick-option'] = (d) => {
  const sel = itemDraft[d.key].sel;
  const cur = sel[d.group];
  if (d.required === '1') sel[d.group] = [d.choice];
  else if (cur.includes(d.choice)) sel[d.group] = cur.filter((x) => x !== d.choice);
  else if (cur.length < Number(d.max)) sel[d.group] = [...cur, d.choice];
  else { toast(t('item.max_reached', { n: d.max })); return; }
  rerender();
};
actions['item-qty'] = (d) => {
  const draft = itemDraft[d.key];
  draft.qty = Math.max(1, Math.min(20, draft.qty + Number(d.delta)));
  rerender();
};
inputs['item-note'] = (el) => {
  itemDraft[el.dataset.key].note = el.value;
  const cnt = document.getElementById('note-cnt');
  if (cnt) cnt.textContent = `${el.value.length} / ${NOTE_MAX}`;
};
actions['add-to-cart'] = async (d) => {
  const { r, item } = await loadItem(d.rid, d.iid);
  const key = `${d.rid}/${d.iid}`;
  const draft = itemDraft[key];
  let c = cart.get();
  if (c.restaurant_id && c.restaurant_id !== r.id && c.items.length) {
    if (!(await confirmDialog(t('cart.switch_confirm', { name: c.restaurant_name })))) return;
    cart.clear();
    c = cart.get();
  }
  const chosen = item.option_groups.flatMap((g) => g.choices.filter((ch) => draft.sel[g.id].includes(ch.id)).map((ch) => ({ id: `${g.id}:${ch.id}`, label: ch.label })));
  c.restaurant_id = r.id;
  c.restaurant_name = r.name;
  c.items.push({
    line_id: Math.random().toString(36).slice(2, 10), menu_item_id: item.id, name: item.name,
    option_ids: chosen.map((x) => x.id), options_label: C.optionsText(chosen.map((x) => x.label)),
    unit_price: unitPrice(item, draft), qty: draft.qty, note: draft.note.trim(),
  });
  cart.set(c);
  delete itemDraft[key];
  toast(t('cart.added'));
  navigate(`r-${r.id}`);
};

// ======================= C05 確認訂單 =======================
const checkout = { pickup_type: 'asap', pickup_time: null };

// 預約時段的下拉選單：依日期分組（今天／明天），每 15 分鐘一個
function slotSelect(slots, selected) {
  const days = [];
  for (const s of slots) {
    const day = new Date(s).toDateString();
    if (days.at(-1)?.day !== day) days.push({ day, label: C.dayLabel(s), slots: [] });
    days.at(-1).slots.push(s);
  }
  return `<div class="slotpick">
    <label class="lab" for="pickup-slot">${esc(t('cart.pick_slot'))}</label>
    <select id="pickup-slot" class="num" data-input="pickup-slot">
      ${days.map((g) => `<optgroup label="${esc(g.label)}">${g.slots.map((s) => `<option value="${esc(s)}"${s === selected ? ' selected' : ''}>${hhmm(s)}</option>`).join('')}</optgroup>`).join('')}
    </select>
    <small>${esc(t('cart.slot_rule'))}</small>
  </div>`;
}

function cartLine(line) {
  const meta = [line.options_label, line.note ? t('cart.note_prefix') + line.note : ''].filter(Boolean);
  return `<li class="line">
    <span class="nm">${esc(line.name)}${meta.map((m) => `<span class="lopt">${esc(m)}</span>`).join('')}</span>
    ${C.QtyStepper({ qty: line.qty, action: 'cart-qty', data: { line: line.line_id } })}
    <span class="sub">${unit(line.unit_price * line.qty)}</span>
  </li>`;
}

export async function cartPage() {
  const c = cart.get();
  if (!c.items.length) {
    return phone(`${C.TopBar({ title: t('cart.review'), back: true })}
      <main class="main"><div class="empty">${esc(t('cart.empty'))}<br><a class="textlink" href="#home">${esc(t('cart.browse'))}</a></div></main>`);
  }
  const [r, wait] = await Promise.all([api.getRestaurant(c.restaurant_id), api.getWaitEstimate(c.restaurant_id)]);
  const total = cartTotal(c);
  const slots = pickupSlots();
  const scheduled = checkout.pickup_type === 'scheduled';
  if (scheduled && !slots.includes(checkout.pickup_time)) checkout.pickup_time = slots[0];
  return phone(`${C.TopBar({ title: t('cart.review'), back: true })}
    <main class="main">
      <div class="meta"><span>${esc(c.restaurant_name)} · ${esc(r.location)}</span>${C.SampleTag()}</div>
      <div class="sec"><h2>${esc(t('cart.lines'))}</h2><span class="aside">${esc(t('cart.count', { n: cartCount(c) }))}</span></div>
      <ul class="linelist">${c.items.map(cartLine).join('')}</ul>
      <div class="sum"><span>${esc(t('cart.total'))}</span><b>${money(total)}</b></div>
      <fieldset class="ogroup">
        <legend>${esc(t('cart.pickup_time'))}</legend>
        <div role="radiogroup" aria-label="${esc(t('cart.pickup_time'))}">
          ${C.Choice({ label: t('cart.asap'), aside: t('cart.around', { time: hhmm(wait.estimated_ready_at) }), selected: !scheduled, action: 'pickup-type', data: { type: 'asap' } })}
          ${C.Choice({ label: t('cart.scheduled'), aside: r.allow_scheduled_pickup ? '' : t('cart.scheduled_off'), selected: scheduled, action: 'pickup-type', data: { type: 'scheduled' }, disabled: !r.allow_scheduled_pickup })}
        </div>
        ${scheduled ? slotSelect(slots, checkout.pickup_time) : ''}
      </fieldset>
      ${C.Note({ text: t('cart.mock_note') })}
    </main>
    <div class="dock">${C.Cta({ label: t('cart.checkout'), figure: money(total), action: 'checkout' })}</div>`);
}
actions['cart-qty'] = (d) => {
  const c = cart.get();
  const line = c.items.find((i) => i.line_id === d.line);
  line.qty += Number(d.delta);
  c.items = c.items.filter((i) => i.qty > 0);
  if (!c.items.length) { cart.clear(); } else cart.set(c);
  rerender();
};
actions['pickup-type'] = (d) => { checkout.pickup_type = d.type; if (d.type === 'asap') checkout.pickup_time = null; rerender(); };
inputs['pickup-slot'] = (el) => { checkout.pickup_time = el.value; };
actions.checkout = async (_, el) => {
  // 在這頁停太久，選的時段可能已經不到 30 分鐘後了：請顧客重選
  if (checkout.pickup_type === 'scheduled' && !slotAllowed(checkout.pickup_time)) {
    toast(t('cart.slot_expired'));
    rerender();
    return;
  }
  el.disabled = true;
  el.setAttribute('aria-busy', 'true');
  const c = cart.get();
  try {
    const order = await api.createOrder({
      restaurant_id: c.restaurant_id,
      items: c.items.map((i) => ({ menu_item_id: i.menu_item_id, qty: i.qty, option_ids: i.option_ids, note: i.note })),
      pickup_type: checkout.pickup_type,
      pickup_time: checkout.pickup_type === 'scheduled' ? checkout.pickup_time : null,
    });
    Object.assign(checkout, { pickup_type: 'asap', pickup_time: null });
    navigate(`pay-${order.id}`);
  } finally { if (el.isConnected) { el.disabled = false; el.removeAttribute('aria-busy'); } }
};

// ======================= C06 付款（模擬） =======================
const payState = { method: 'line_pay' };
const METHOD_ICON = { credit_card: 'card', cash_on_pickup: 'store' };
export async function payPage({ oid }) {
  const [o, methods] = await Promise.all([api.getOrder(oid), api.listPaymentMethods()]);
  if (o.status !== 'pending_payment' || o.payment_method) { navigate(`order-${oid}`); return ''; }
  const rest = await api.getRestaurant(o.restaurant_id);
  const list = methods.filter((m) => m.method !== 'cash_on_pickup' || rest.allow_cash_on_pickup);
  if (!list.some((m) => m.method === payState.method)) payState.method = list[0].method;
  return phone(`${C.TopBar({ title: t('pay.title'), back: true })}
    <main class="main">
      <section class="due">
        <span class="lab">${esc(t('pay.amount_due'))}</span>
        <b>${money(o.total)}</b>
        <span class="mt">${esc(t('pay.order_meta', { no: o.pickup_number, name: o.restaurant_name }))}</span>
      </section>
      ${['failed', 'expired'].includes(o.payment_attempt) ? C.Note({ text: t('pay.retry_note'), kind: 'err' }) : ''}
      ${C.Note({ text: t(list.some((m) => m.method === 'line_pay') ? 'pay.sandbox_note' : 'pay.mock_note') })}
      <div class="sec"><h2>${esc(t('pay.choose'))}</h2></div>
      <div class="opts" role="radiogroup" aria-label="${esc(t('pay.choose'))}">
        ${list.map((m) => C.OptRow({ label: m.label, sub: m.hint, ic: METHOD_ICON[m.method] || 'wallet', selected: m.method === payState.method, action: 'pick-method', data: { method: m.method } })).join('')}
      </div>
    </main>
    <div class="dock">${C.Cta({ label: t('pay.confirm', { price: '' }).trim(), figure: money(o.total), action: 'pay', data: { oid } })}</div>`);
}
actions['pick-method'] = (d) => { payState.method = d.method; rerender(); };
actions.pay = async (d, el) => {
  el.disabled = true;
  el.setAttribute('aria-busy', 'true');
  el.querySelector('span').textContent = t('pay.processing');
  const res = await api.pay(d.oid, payState.method);
  if (res.status === 'redirect') {
    // 線上付款：到金流商的付款頁（LINE Pay 或後端的模擬付款頁），付完會被導回這張單的取餐券
    cart.clear();
    el.querySelector('span').textContent = t('pay.redirecting');
    location.assign(res.url);
    return;
  }
  if (res.status !== 'succeeded') { toast(t('pay.failed')); rerender(); return; }
  cart.clear();
  navigate(`paid-${d.oid}`);
};

// ======================= 取餐券下半：明細（C07、C08 共用） =======================
function passLines(o) {
  return `<div class="rule"></div><div class="lines">
    ${o.items.map((i) => `<div><span>${esc(i.name)} × ${esc(i.qty)}${i.options_label ? `<small class="lopt">${esc(i.options_label)}</small>` : ''}</span><span class="num">${unit(i.subtotal ?? i.unit_price * i.qty)}</span></div>`).join('')}
    <div class="t"><span>${esc(t('cart.total'))}</span><span class="num">${money(o.total)}</span></div>
    <div class="pay"><span>${esc(t('order.payment'))}</span><span>${esc(C.paymentText(o))}</span></div>
  </div>`;
}

// ======================= C07 付款完成 =======================
export async function paidPage({ oid }) {
  const o = await api.getOrder(oid);
  lastStatus[o.id] = o.status;
  const cash = o.payment_method === 'cash_on_pickup';
  return phone(`${C.TopBar({ title: t(cash ? 'paid.title_cash' : 'paid.title') })}
    <main class="main">
      ${cash ? C.Note({ text: t('order.pay_at_pickup') }) : ''}
      <div class="passwrap">
        ${C.Pass(o, { mode: 'full', extra: passLines(o) })}
        <p class="msg">${esc(C.readyText(o))}</p>
      </div>
    </main>
    <div class="dock">
      ${C.Cta({ label: t('paid.track'), href: `order-${oid}` })}
      <a class="btn btn--text btn--block" href="#home">${esc(t('paid.home'))}</a>
    </div>`);
}

// ======================= C08 / C09 訂單：整張取餐券 =======================
export async function orderStatusPage({ oid }) {
  const o = await api.getOrder(oid);
  const was = lastStatus[o.id];
  const snapping = changed(o);
  if (was && was !== 'ready' && o.status === 'ready') toast(t('order.ready_toast'));
  const live = !['picked_up', 'cancelled'].includes(o.status);
  if (live) poll(idleRerender, 3000);

  const unpaid = o.status === 'pending_payment' && !o.payment_method;
  const when = Object.fromEntries(o.status_history.map((h) => [h.status, h.at]));
  const eta = [C.readyText(o), o.queue_ahead ? t('order.queue_ahead', { n: o.queue_ahead }) : ''].filter(Boolean).join(' · ');
  const msg = o.status === 'ready' ? `<p class="msg msg--ready" role="status">${esc(t('order.ready_alert', { place: o.restaurant_location }))}</p><p class="upd">${esc(t('order.ready_at', { time: hhmm(when.ready || o.estimated_ready_at) }))} · ${esc(t('order.hold'))}</p>`
    : o.status === 'cancelled' ? `<p class="msg msg--cancel">${esc(t('pass.cancel_msg'))}</p>`
    : o.status === 'picked_up' ? `<p class="msg">${esc(t('pass.picked_msg'))}</p>`
    : unpaid ? `<p class="msg">${esc(t('pass.unpaid_msg'))}</p>`
    : `<p class="msg">${esc(t('pass.show'))}</p><p class="upd">${esc(eta)}</p>`;
  const dock = unpaid ? C.Cta({ label: t('orders.pay_now'), href: `pay-${o.id}` })
    : o.status === 'cancelled' && o.restaurant_id ? C.Cta({ label: t('pass.back_to_stall'), href: `r-${o.restaurant_id}` }) : '';
  return phone(`${C.TopBar({ title: o.restaurant_name, back: true })}
    <main class="main">
      <div class="passwrap">
        ${C.Pass(o, { mode: 'full', extra: passLines(o), snapping })}
        ${msg}
        ${live ? `<p class="upd num">${esc(t('pass.updated', { time: C.hhmmss() }))}</p>` : ''}
      </div>
    </main>
    ${dock ? `<div class="dock">${dock}</div>` : ''}`);
}

// ======================= C10 我的訂單 =======================
export async function ordersPage() {
  const orders = await api.listMyOrders();
  const active = orders.filter((o) => ACTIVE.includes(o.status));
  const past = orders.filter((o) => !ACTIVE.includes(o.status));
  C.navState.activeOrders = active.length;
  if (active.length) poll(idleRerender, 5000);
  if (!orders.length) {
    return phone(`${C.TopBar({ title: t('nav.orders') })}
      <main class="main"><div class="empty">${esc(t('orders.empty'))}<br><a class="textlink" href="#home">${esc(t('cart.browse'))}</a></div></main>
      ${C.BottomNav({ active: 'orders' })}`);
  }
  const hist = (o) => `<li class="hist">
      <span class="code">${esc(o.pickup_number)}</span>
      <a class="nm" href="#order-${esc(o.id)}">${esc(o.restaurant_name)}</a>
      <span class="r"><b>${money(o.total)}</b><span${o.status === 'cancelled' ? ' class="x"' : ''}>${esc(t('pass.st.' + o.status))}</span></span>
      <span class="mt num">${C.mmdd(o.created_at)} · ${hhmm(o.created_at)}${o.pickup_type === 'scheduled' ? ` · ${esc(t('order.booked_short', { time: C.pickupText(o.pickup_time) }))}` : ''}</span>
      <span class="its">${esc(C.itemsSummary(o.items, t('fmt.list_sep')))}</span>
      <button type="button" class="lnk" data-action="reorder" data-id="${esc(o.id)}">${esc(t('orders.reorder'))}</button>
    </li>`;
  return phone(`${C.TopBar({ title: t('nav.orders') })}
    <main class="main">
      <div class="sec"><h2>${esc(t('orders.active'))}</h2></div>
      ${active.length ? `<div class="stack">${active.map(miniPass).join('')}</div>` : `<p class="quiet">${esc(t('orders.none_active'))}</p>`}
      <div class="sec"><h2>${esc(t('orders.past'))}</h2>${past.length ? `<span class="aside num">${past.length}</span>` : ''}</div>
      ${past.length ? `<ul class="histlist">${past.map(hist).join('')}</ul>` : `<p class="quiet">${esc(t('orders.none_past'))}</p>`}
    </main>
    ${C.BottomNav({ active: 'orders' })}`);
}
actions.reorder = async (d) => {
  const o = await api.getOrder(d.id);
  const c = cart.get();
  if (c.items.length && c.restaurant_id !== o.restaurant_id && !(await confirmDialog(t('cart.switch_confirm', { name: c.restaurant_name })))) return;
  cart.set({
    restaurant_id: o.restaurant_id, restaurant_name: o.restaurant_name,
    items: o.items.map((i) => ({ line_id: Math.random().toString(36).slice(2, 10), menu_item_id: i.menu_item_id, name: i.name, option_ids: i.option_ids, options_label: i.options_label || '', unit_price: i.unit_price, qty: i.qty, note: '' })),
  });
  navigate('cart');
};

// ======================= C11 我的帳號 =======================
export async function profilePage() {
  const me = await api.me();
  const staff = me.role === 'staff' || me.role === 'admin';
  const fields = [
    me.email && [t('profile.email'), me.email, ''],
    me.phone_number && [t('profile.phone'), me.phone_number, 'num'],
    me.department && [t('profile.dept'), me.department, ''],
  ].filter(Boolean);
  return phone(`${C.TopBar({ title: t('profile.title') })}
    <main class="main">
      <section class="idcard" aria-label="${esc(t('profile.student_id'))} ${esc(me.student_id)}">
        <div class="top"><span class="lab">${esc(t('profile.student_id'))}</span><span class="lab">${esc(t('profile.role'))}</span>
          <span class="code">${esc(me.student_id)}</span><div class="stat"><b>${esc(t('profile.role.' + me.role))}</b></div></div>
        ${fields.length ? `<div class="perf"></div><dl class="fields">${fields.map(([k, v, cls]) => `<div><dt class="lab">${esc(k)}</dt><dd${cls ? ` class="${cls}"` : ''}>${esc(v)}</dd></div>`).join('')}</dl>` : ''}
      </section>
      <div class="sec"><h2>${esc(t('profile.settings'))}</h2></div>
      <div class="acct">
        <div class="setrow"><span class="oi">${icon('lang')}</span><span class="tx"><b>${esc(t('lang.name'))}</b><small>${esc(t('lang.current'))}</small></span>${C.LangSwitch({ light: true })}</div>
        ${me.role === 'admin' ? '' : `<button type="button" class="setrow navrow" data-action="tour-replay"><span class="oi">${icon('info')}</span><span class="tx"><b>${esc(t('tour.replay'))}</b><small>${esc(t('tour.replay_sub'))}</small></span><span class="chev">${icon('chev')}</span></button>`}
        <a class="setrow navrow" href="#password"><span class="oi">${icon('lock')}</span><span class="tx"><b>${esc(t('password.change'))}</b><small>${esc(t('password.change_sub'))}</small></span><span class="chev">${icon('chev')}</span></a>
        ${staff ? `<a class="setrow navrow" href="#${homeOf(me.role)}"><span class="oi">${icon('store')}</span><span class="tx"><b>${esc(t('profile.dashboard'))}</b></span><span class="chev">${icon('chev')}</span></a>` : ''}
      </div>
      <button type="button" class="signout" data-action="logout">${esc(t('profile.logout'))}</button>
    </main>
    ${C.BottomNav({ active: 'profile' })}`);
}
