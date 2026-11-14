// 顧客端畫面 C01–C11（收據版）＋註冊頁
import { api } from '../api.js';
import { t, getLang, setLang } from '../i18n.js';
import { session, cart, cartCount, cartTotal, homeOf } from '../store.js';
import { actions, forms, inputs, navigate, rerender, poll, toast, confirmDialog } from '../router.js';
import * as C from '../components.js';

const { esc, money, hhmm } = C;
const phone = (inner) => `<div class="phone">${inner}</div>`;

// 共用動作
actions.back = () => (history.length > 1 ? history.back() : navigate('home'));
actions.go = (d) => navigate(d.to);
actions['set-lang'] = (d) => { setLang(d.lang); rerender(); };
actions.logout = () => { session.clear(); cart.clear(); navigate('login'); };

// ======================= C01 登入 =======================
export async function loginPage() {
  return phone(`<div class="login">
    <div class="login__top">${C.LangSwitch()}</div>
    <div class="login__brand">
      <h1>${esc(t('app.name'))}</h1>
      <p>${esc(t('login.lead'))}</p>
    </div>
    <form data-form="login" novalidate>
      ${C.TextField({ label: t('login.student_id'), name: 'student_id', extra: 'autocomplete="username" inputmode="text" autocapitalize="off"' })}
      ${C.TextField({ label: t('login.password'), name: 'password', type: 'password', extra: 'autocomplete="current-password"' })}
      ${C.Button({ label: t('login.submit'), style: 'primary', type: 'submit', block: true })}
    </form>
    <p class="small muted">${esc(t('login.no_account'))} <a class="link" href="#register">${esc(t('login.to_register'))}</a></p>
  </div>`);
}
forms.login = async (fd, form) => {
  const id = String(fd.get('student_id') || '').trim();
  if (!id) { toast(t('login.need_id')); form.querySelector('[name=student_id]')?.focus(); return; }
  const res = await api.login(id, fd.get('password'));
  session.set({ access_token: res.access_token, user: res.user });
  navigate(homeOf(res.user.role));
};

// ======================= 註冊（新） =======================
export async function registerPage() {
  return phone(`<div class="login">
    <div class="login__top">${C.LangSwitch()}</div>
    <div class="login__brand">
      <h1>${esc(t('register.title'))}</h1>
      <p>${esc(t('register.lead'))}</p>
    </div>
    <form data-form="register" novalidate>
      ${C.TextField({ label: t('login.student_id'), name: 'student_id', extra: 'autocomplete="username" autocapitalize="off" maxlength="20"' })}
      ${C.TextField({ label: t('register.email'), name: 'email', type: 'email', extra: 'autocomplete="email"' })}
      ${C.TextField({ label: t('register.phone'), name: 'phone_number', type: 'tel', extra: 'autocomplete="tel" inputmode="tel"' })}
      ${C.TextField({ label: t('register.password_hint'), name: 'password', type: 'password', extra: 'autocomplete="new-password" minlength="8"' })}
      ${C.Button({ label: t('register.submit'), style: 'primary', type: 'submit', block: true })}
    </form>
    <p class="small muted">${esc(t('register.have_account'))} <a class="link" href="#login">${esc(t('register.to_login'))}</a></p>
  </div>`);
}
forms.register = async (fd, form) => {
  const data = Object.fromEntries(['student_id', 'email', 'phone_number'].map((k) => [k, String(fd.get(k) || '').trim()]));
  data.password = String(fd.get('password') || '');
  const empty = Object.keys(data).find((k) => !data[k]);
  if (empty) { toast(t('register.need_all')); form.querySelector(`[name=${empty}]`)?.focus(); return; }
  if (data.password.length < 8) { toast(t('register.short_password')); form.querySelector('[name=password]')?.focus(); return; }
  const res = await api.register(data);
  session.set({ access_token: res.access_token, user: res.user });
  navigate(homeOf(res.user.role));
};

// ======================= C02 首頁：等候看板 =======================
const home = { location: 'all', sort: 'wait', q: '', list: [] };
const LOCATIONS = [['all', 'home.loc_all'], ['shuimu', 'home.loc_shuimu'], ['fengyun', 'home.loc_fengyun'], ['snack', 'home.loc_snack']];

function restaurantListHtml() {
  const q = home.q.trim().toLowerCase();
  const list = home.list.filter((r) => !q || r.name.toLowerCase().includes(q));
  return list.length ? list.map(C.WaitRow).join('') : `<li class="empty">${esc(t('home.empty'))}</li>`;
}

export async function homePage() {
  const list = await api.listRestaurants({ location: home.location, sort: home.sort });
  home.list = list;
  const openCount = list.filter((r) => r.is_open && r.is_accepting_orders).length;
  poll(refreshRestaurantList, 30000);
  return phone(`
    <header class="topbar"><a class="wordmark grow" href="#home">${esc(t('app.name'))}</a></header>
    <main class="main">
      <div class="home-head">
        <div class="search field"><label class="visually-hidden" for="home-q">${esc(t('home.search_ph'))}</label>
          <input id="home-q" type="search" class="input" data-input="home-search" value="${esc(home.q)}" placeholder="${esc(t('home.search_ph'))}" autocomplete="off"></div>
        ${C.Tabs(LOCATIONS.map(([k, key]) => ({ name: t(key), selected: home.location === k, action: 'home-location', data: { loc: k } })))}
      </div>
      <section class="stack stack--tight" aria-labelledby="open-count">
        <div class="count-row">
          <h2 id="open-count" class="section-title">${esc(t('home.open_count', { n: openCount }))}</h2>
          <button type="button" class="link small" data-action="home-sort">${esc(t(home.sort === 'wait' ? 'home.sort_wait' : 'home.sort_name'))}</button>
        </div>
        <ul class="waitboard" id="restaurant-list">${restaurantListHtml()}</ul>
      </section>
    </main>
    ${C.BottomNav({ active: 'home' })}`);
}
async function refreshRestaurantList() {
  home.list = await api.listRestaurants({ location: home.location, sort: home.sort });
  const el = document.getElementById('restaurant-list');
  if (el) el.innerHTML = restaurantListHtml();
}
actions['home-location'] = (d) => { home.location = d.loc; rerender(); };
actions['home-sort'] = () => { home.sort = home.sort === 'wait' ? 'name' : 'wait'; rerender(); };
inputs['home-search'] = (el) => {
  home.q = el.value;
  document.getElementById('restaurant-list').innerHTML = restaurantListHtml();
};

// ======================= C03 餐廳頁：印刷菜單 =======================
const selectedCategory = {};

function waitLine(w) {
  return `<dt>${esc(t('restaurant.wait_label'))}</dt><dd>${esc(t('wait.banner', { n: w.wait_minutes, q: w.queue_count }))}</dd>`;
}

export async function restaurantPage({ rid }) {
  const [r, menu, wait] = await Promise.all([api.getRestaurant(rid), api.getMenu(rid), api.getWaitEstimate(rid)]);
  const canOrder = r.is_open && r.is_accepting_orders;
  const cat = selectedCategory[rid] ?? menu.categories[0]?.id;
  const items = menu.categories.find((c) => c.id === cat)?.items ?? [];
  const c = cart.get();
  const bar = c.items.length
    ? `<a class="cart-bar" href="#cart"><span>${esc(t('cart.view'))}</span><span class="small">${esc(t('cart.count', { n: cartCount(c) }))}</span><span class="fig-strong">${money(cartTotal(c))}</span></a>`
    : '';
  if (canOrder) {
    poll(async () => {
      const el = document.getElementById('wait-slot');
      if (el) el.innerHTML = waitLine(await api.getWaitEstimate(rid));
    }, 30000);
  }
  return phone(`${C.TopBar({ title: r.name, back: true })}
    <main class="main">
      ${C.Photo({ url: r.cover_image_url, alt: r.name, kind: 'cover', cls: 'bleed' })}
      <section class="r-intro">
        ${r.description ? `<p>${esc(r.description)}</p>` : ''}
        <dl class="facts">
          <dt>${esc(t('order.place'))}</dt><dd>${esc(r.location_detail)}</dd>
          <dt>${esc(t('admin.settings.hours'))}</dt><dd>${esc(r.opening_hours_label)}</dd>
          ${canOrder ? `<div id="wait-slot" style="display:contents">${waitLine(wait)}</div>` : ''}
        </dl>
        ${canOrder ? '' : `<p class="band band--stop">${esc(r.is_open ? t('restaurant.paused') : t('restaurant.closed_now', { hours: r.opening_hours_label }))}</p>`}
      </section>
      <section>
        ${C.Tabs(menu.categories.map((x) => ({ name: x.name, selected: x.id === cat, action: 'menu-category', data: { rid, cat: x.id } })), { sticky: true, label: r.name })}
        <ul class="menu">${items.map((i) => C.MenuRow(i, rid)).join('') || `<li class="empty">${esc(t('menu.empty'))}</li>`}</ul>
      </section>
    </main>${bar}`);
}
actions['menu-category'] = (d) => { selectedCategory[d.rid] = d.cat; rerender(); };

// ======================= C04 品項 =======================
const itemDraft = {}; // `${rid}/${iid}` → { sel: { groupId: [choiceId] }, qty, note }

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
  const canOrder = r.is_open && r.is_accepting_orders && item.is_available && !item.is_sold_out;
  const groups = item.option_groups.map((g) => `<fieldset class="group">
      <legend class="group__head"><span>${esc(g.name)}</span><span class="small">${esc(t(g.required ? 'item.pick_one' : 'item.optional').replace(/[（）()]/g, '').trim())}</span></legend>
      <div class="choices" role="${g.required ? 'radiogroup' : 'group'}" aria-label="${esc(g.name)}">
      ${g.choices.map((c) => C.Choice({ label: c.label, aside: c.price_delta ? `+${money(c.price_delta)}` : '', selected: d.sel[g.id].includes(c.id), multi: !g.required, action: 'pick-option', data: { key, group: g.id, choice: c.id, max: g.max_select, required: g.required ? 1 : 0 } })).join('')}
      </div>
    </fieldset>`).join('');
  const hint = canOrder ? '' : `<p class="hint" role="status">${esc(t(item.is_sold_out ? 'item.sold_out_hint' : 'item.closed_hint'))}</p>`;
  return phone(`${C.TopBar({ title: r.name, back: true })}
    <main class="main">
      ${C.Photo({ url: item.image_url, alt: item.name, kind: 'hero', cls: 'bleed' })}
      <section class="item-head">
        <h1>${esc(item.name)}</h1>
        ${item.description ? `<p class="muted">${esc(item.description)}</p>` : ''}
        <div class="item-head__price"><span class="fig-strong">${money(item.price)}</span><span class="small muted">${esc(t('item.prep', { n: item.prep_minutes }))}</span></div>
      </section>
      ${groups}
      ${C.TextField({ label: t('item.note'), name: 'note', value: d.note, placeholder: t('item.note_ph'), input: 'item-note', data: { key } })}
    </main>
    <div class="action-bar">
      <div class="action-bar__row">${C.QtyStepper({ qty: d.qty, action: 'item-qty', data: { key }, min: 1 })}
        ${C.Button({ label: t('item.add'), style: 'primary', block: true, action: 'add-to-cart', data: { rid, iid }, disabled: !canOrder, figure: money(unitPrice(item, d) * d.qty) })}</div>
      ${hint}
    </div>`);
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
inputs['item-note'] = (el) => { itemDraft[el.dataset.key].note = el.value; };
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

// ======================= C05 購物車：收據 =======================
const checkout = { pickup_type: 'asap', pickup_time: null };
function nextSlots() {
  const d = new Date(Date.now() + 15 * 60000);
  d.setMinutes(Math.ceil(d.getMinutes() / 15) * 15, 0, 0);
  return [0, 1, 2, 3].map((k) => new Date(d.getTime() + k * 15 * 60000).toISOString());
}

function slipLine(line) {
  const meta = [line.options_label, line.note ? t('cart.note_prefix') + line.note : ''].filter(Boolean);
  return `<div class="slip-line">
    <span class="slip-line__name">${esc(line.name)}</span>
    <span class="slip-line__price">${money(line.unit_price * line.qty)}</span>
    ${meta.map((m) => `<span class="slip-line__meta">${esc(m)}</span>`).join('')}
    <div class="slip-line__ctrl"><span class="small muted fig">${esc(t('cart.unit', { price: money(line.unit_price) }))}</span>${C.QtyStepper({ qty: line.qty, action: 'cart-qty', data: { line: line.line_id }, small: true })}</div>
  </div>`;
}

export async function cartPage() {
  const c = cart.get();
  if (!c.items.length) {
    return phone(`${C.TopBar({ title: t('cart.title'), back: true })}
      <main class="main"><div class="state"><p class="strong">${esc(t('cart.empty'))}</p>${C.Button({ label: t('cart.browse'), style: 'primary', action: 'go', data: { to: 'home' } })}</div></main>`);
  }
  const [r, wait] = await Promise.all([api.getRestaurant(c.restaurant_id), api.getWaitEstimate(c.restaurant_id)]);
  const total = cartTotal(c);
  const slots = nextSlots();
  const scheduled = checkout.pickup_type === 'scheduled';
  if (scheduled && !slots.includes(checkout.pickup_time)) checkout.pickup_time = slots[0];
  return phone(`${C.TopBar({ title: t('cart.title'), back: true })}
    <main class="main">
      <section class="slip" aria-label="${esc(c.restaurant_name)}">
        <div class="slip__head"><h2>${esc(c.restaurant_name)}</h2><span class="small muted">${esc(t('cart.count', { n: cartCount(c) }))}</span></div>
        ${c.items.map(slipLine).join('')}
        <div class="slip__total"><span class="strong">${esc(t('cart.total'))}</span><span class="fig-strong">${money(total)}</span></div>
      </section>
      <fieldset class="group">
        <legend class="group__head"><span>${esc(t('cart.pickup_time'))}</span></legend>
        <div class="choices" role="radiogroup" aria-label="${esc(t('cart.pickup_time'))}">
          ${C.Choice({ label: t('cart.asap'), aside: t('cart.around', { time: hhmm(wait.estimated_ready_at) }), selected: !scheduled, action: 'pickup-type', data: { type: 'asap' } })}
          ${C.Choice({ label: t('cart.scheduled'), aside: r.allow_scheduled_pickup ? '' : t('cart.scheduled_off'), selected: scheduled, action: 'pickup-type', data: { type: 'scheduled' }, disabled: !r.allow_scheduled_pickup })}
        </div>
        ${scheduled ? `<div class="slots" role="group" aria-label="${esc(t('cart.pick_slot'))}">${slots.map((s) => `<button type="button" class="slot" aria-pressed="${s === checkout.pickup_time}" data-action="pickup-slot" data-time="${esc(s)}">${hhmm(s)}</button>`).join('')}</div>` : ''}
      </fieldset>
    </main>
    <div class="action-bar">${C.Button({ label: t('cart.checkout'), style: 'primary', block: true, action: 'checkout', figure: money(total) })}</div>`);
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
actions['pickup-slot'] = (d) => { checkout.pickup_time = d.time; rerender(); };
actions.checkout = async (_, el) => {
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
    navigate(`pay-${order.id}`);
  } finally { if (el.isConnected) { el.disabled = false; el.removeAttribute('aria-busy'); } }
};

// ======================= C06 付款（模擬） =======================
const payState = { method: 'line_pay' };
export async function payPage({ oid }) {
  const [o, methods] = await Promise.all([api.getOrder(oid), api.listPaymentMethods()]);
  if (o.status !== 'pending_payment' || o.payment_method) { navigate(`order-${oid}`); return ''; }
  const rest = await api.getRestaurant(o.restaurant_id);
  const list = methods.filter((m) => m.method !== 'cash_on_pickup' || rest.allow_cash_on_pickup);
  if (!list.some((m) => m.method === payState.method)) payState.method = list[0].method;
  return phone(`${C.TopBar({ title: t('pay.title'), back: true })}
    <main class="main">
      <section class="due">
        <span class="small muted">${esc(t('pay.amount_due'))}</span>
        <span class="fig-strong">${money(o.total)}</span>
        <span class="small muted">${esc(t('pay.order_meta', { no: o.pickup_number, name: o.restaurant_name }))}</span>
      </section>
      <fieldset class="group">
        <legend class="group__head"><span>${esc(t('pay.choose'))}</span></legend>
        <div class="choices" role="radiogroup" aria-label="${esc(t('pay.choose'))}">
          ${list.map((m) => C.Choice({ label: m.label, sub: m.hint, selected: m.method === payState.method, action: 'pick-method', data: { method: m.method } })).join('')}
        </div>
      </fieldset>
    </main>
    <div class="action-bar">${C.Button({ label: t('pay.confirm', { price: '' }).trim(), style: 'primary', block: true, action: 'pay', data: { oid }, figure: money(o.total) })}</div>`);
}
actions['pick-method'] = (d) => { payState.method = d.method; rerender(); };
actions.pay = async (d, el) => {
  el.disabled = true;
  el.setAttribute('aria-busy', 'true');
  el.querySelector('span').textContent = t('pay.processing');
  const res = await api.pay(d.oid, payState.method);
  if (res.status !== 'succeeded') { toast(t('pay.failed')); rerender(); return; }
  cart.clear();
  navigate(`paid-${d.oid}`);
};

// ======================= 取餐票（C07、C08 共用） =======================
function ticket(o, { state, eta, sub, done = false }) {
  return `<section class="ticket${done ? ' is-done' : ''}" aria-label="${esc(t('order.pickup_number'))} ${esc(o.pickup_number)}">
    <div class="ticket__top">
      <span class="small muted">${esc(t('order.pickup_number'))}</span>
      <span class="ticket__no">${esc(o.pickup_number)}</span>
      <span class="ticket__state">${esc(state)}</span>
    </div>
    <div class="ticket__stub">
      ${eta ? `<span class="ticket__eta">${esc(eta)}</span>` : ''}
      ${sub ? `<span class="small muted">${esc(sub)}</span>` : ''}
      <span class="small">${esc(o.restaurant_name)}${t('fmt.paren', { x: o.restaurant_location })}</span>
    </div>
  </section>`;
}

// ======================= C07 付款完成 =======================
export async function paidPage({ oid }) {
  const o = await api.getOrder(oid);
  const cash = o.payment_method === 'cash_on_pickup';
  return phone(`${C.TopBar({ title: t(cash ? 'paid.title_cash' : 'paid.title') })}
    <main class="main">
      ${ticket(o, { state: t(cash ? 'paid.title_cash' : 'paid.title'), eta: t('order.ready_around', { time: hhmm(o.estimated_ready_at) }), sub: cash ? t('order.pay_at_pickup') : '' })}
    </main>
    <div class="action-bar">
      ${C.Button({ label: t('paid.track'), style: 'primary', block: true, action: 'go', data: { to: `order-${oid}` } })}
      ${C.Button({ label: t('paid.home'), style: 'text', block: true, action: 'go', data: { to: 'home' } })}
    </div>`);
}

// ======================= C08 / C09 訂單進度 =======================
const STEPS = ['paid', 'accepted', 'preparing', 'ready', 'picked_up'];
const seenStatus = {};
export async function orderStatusPage({ oid }) {
  const o = await api.getOrder(oid);
  const prev = seenStatus[oid];
  seenStatus[oid] = o.status;
  if (prev && prev !== 'ready' && o.status === 'ready') toast(t('order.ready_toast'));
  if (!['picked_up', 'cancelled'].includes(o.status)) poll(rerender, 3000);

  const ready = o.status === 'ready';
  const cancelled = o.status === 'cancelled';
  const finished = o.status === 'picked_up' || cancelled;
  const when = Object.fromEntries(o.status_history.map((h) => [h.status, h.at]));
  const cur = o.status === 'pending_payment' ? 0 : STEPS.indexOf(o.status);
  const steps = STEPS.map((s, i) => {
    let state = i < cur ? 'done' : i === cur ? 'current' : 'todo';
    if (o.status === 'picked_up') state = 'done';
    let time = when[s] ? hhmm(when[s]) : '';
    if (s === 'paid' && o.payment_method === 'cash_on_pickup') time = '';
    if (s === 'ready' && !when.ready) time = hhmm(o.estimated_ready_at);
    const label = s === 'paid' && o.payment_method === 'cash_on_pickup' ? t('order.pay_at_pickup') : t('step.' + s);
    return `<li class="is-${state}"${state === 'current' ? ' aria-current="step"' : ''}><span class="fig">${esc(time) || '&nbsp;'}</span><span class="log__label">${esc(label)}</span></li>`;
  }).join('');

  const eta = ready ? t('order.ready_at', { time: hhmm(when.ready || o.estimated_ready_at) })
    : finished ? '' : t('order.ready_around', { time: hhmm(o.estimated_ready_at) });
  const sub = ready ? t('order.hold') : finished ? '' : t('order.queue_ahead', { n: o.queue_ahead });
  return phone(`${C.TopBar({ title: t('order.title'), back: true })}
    <main class="main">
      ${ready ? `<p class="band band--ready" role="status">${esc(t('order.ready_alert', { place: o.restaurant_location }))}</p>` : ''}
      ${ticket(o, { state: t('status.' + o.status), eta, sub, done: finished })}
      ${cancelled ? '' : `<section class="stack stack--tight"><h2 class="section-title">${esc(t('order.progress'))}</h2><ol class="log">${steps}</ol></section>`}
      <section class="stack stack--tight">
        <h2 class="section-title">${esc(t('order.items'))}</h2>
        <dl class="facts">
          ${o.items.map((i) => `<dt class="fig">×${esc(i.qty)}</dt><dd>${esc(i.name)}${i.options_label ? `<span class="muted">${esc(t('fmt.paren', { x: i.options_label }))}</span>` : ''}</dd>`).join('')}
          <dt>${esc(t('cart.total'))}</dt><dd class="fig-strong">${money(o.total)}</dd>
          <dt>${esc(t('order.payment'))}</dt><dd>${esc(C.paymentText(o))}</dd>
        </dl>
      </section>
    </main>`);
}

// ======================= C10 我的訂單 =======================
const ACTIVE = ['pending_payment', 'paid', 'accepted', 'preparing', 'ready'];
export async function ordersPage() {
  const orders = await api.listMyOrders();
  const active = orders.filter((o) => ACTIVE.includes(o.status));
  const past = orders.filter((o) => !ACTIVE.includes(o.status));
  if (active.length) poll(rerender, 5000);
  const row = (o) => {
    const unpaid = o.status === 'pending_payment' && !o.payment_method;
    const btn = unpaid
      ? C.Button({ label: t('orders.pay_now'), style: 'primary', size: 'sm', action: 'go', data: { to: `pay-${o.id}` } })
      : ACTIVE.includes(o.status)
        ? C.Button({ label: t('orders.track'), size: 'sm', action: 'go', data: { to: `order-${o.id}` } })
        : C.Button({ label: t('orders.reorder'), size: 'sm', action: 'reorder', data: { id: o.id } });
    return `<li class="order-row">
      <span class="order-row__name">${esc(o.restaurant_name)}</span>${C.statusWord(o.status)}
      <span class="order-row__meta fig">${esc(o.pickup_number)}&emsp;${C.mmdd(o.created_at)} ${hhmm(o.created_at)}</span>
      <span class="order-row__items">${esc(C.itemsSummary(o.items, t('fmt.list_sep')))}</span>
      <div class="order-row__foot"><span class="fig-strong">${money(o.total)}</span>${btn}</div>
    </li>`;
  };
  const block = (title, list, none) => `<section class="stack stack--tight">
      <h2 class="section-title">${esc(title)}<span class="fig">${list.length}</span></h2>
      ${list.length ? `<ul class="orders">${list.map(row).join('')}</ul>` : `<p class="empty">${esc(none)}</p>`}
    </section>`;
  return phone(`${C.TopBar({ title: t('nav.orders') })}
    <main class="main">
      ${block(t('orders.active'), active, t('orders.none_active'))}
      ${block(t('orders.past'), past, t('orders.none_past'))}
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

// ======================= C11 我的 =======================
export async function profilePage() {
  const me = await api.me();
  const staff = me.role === 'staff' || me.role === 'admin';
  return phone(`${C.TopBar({ title: t('nav.profile') })}
    <main class="main me">
      <section class="stack stack--tight">
        <h1>${esc(me.name)}</h1>
        <dl class="facts">
          <dt>${esc(t('profile.student_id'))}</dt><dd class="fig">${esc(me.student_id)}</dd>
          ${me.department ? `<dt>${esc(t('profile.dept'))}</dt><dd>${esc(me.department)}</dd>` : ''}
          ${me.email ? `<dt>${esc(t('profile.email'))}</dt><dd>${esc(me.email)}</dd>` : ''}
          ${me.phone_number ? `<dt>${esc(t('profile.phone'))}</dt><dd class="fig">${esc(me.phone_number)}</dd>` : ''}
        </dl>
      </section>
      <ul class="rows">
        <li><span>${esc(t('lang.switch'))}</span>${C.LangSwitch()}</li>
        ${staff ? `<li><a href="#${homeOf(me.role)}"><span>${esc(t('profile.dashboard'))}</span><span class="muted" aria-hidden="true">›</span></a></li>` : ''}
      </ul>
      <div>${C.Button({ label: t('profile.logout'), action: 'logout' })}</div>
    </main>
    ${C.BottomNav({ active: 'profile' })}`);
}
