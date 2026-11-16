// 店家端與平台管理畫面 A01–A06（收據版）
import { api } from '../api.js';
import { t } from '../i18n.js';
import { actions, forms, inputs, rerender, poll, toast, openModal, closeModal, confirmDialog } from '../router.js';
import { icon } from '../icons.js';
import * as C from '../components.js';

const { esc, money } = C;

async function layout(active, inner) {
  const me = await api.me();
  const items = me.role === 'admin'
    ? [['platform', 'admin.nav.platform']]
    : [['orders', 'admin.nav.orders'], ['menu', 'admin.nav.menu'], ['settings', 'admin.nav.settings'], ['reports', 'admin.nav.reports']];
  return `<div class="admin">
    <header class="admin-bar">
      <div class="admin-bar__brand"><span class="wordmark">${esc(t('app.name'))}</span>${me.role === 'staff' && me.store_name ? `<span class="small muted">${esc(me.store_name)}</span>` : ''}</div>
      <nav class="admin-nav" aria-label="${esc(t('profile.dashboard'))}">${items.map(([k, key]) => `<a href="#admin-${k}"${k === active ? ' aria-current="page"' : ''}>${esc(t(key))}</a>`).join('')}</nav>
      <div class="admin-bar__me"><span class="who muted">${esc(me.name)}</span>${C.LangSwitch()}<button type="button" class="link small" data-action="logout">${esc(t('profile.logout'))}</button></div>
    </header>
    <main class="admin-main">${inner}</main>
  </div>`;
}
function pageHeader(title, sub = '', right = '') {
  return `<div class="page-head"><div class="stack stack--tight"><h1>${esc(title)}</h1>${sub ? `<p class="page-head__sub">${esc(sub)}</p>` : ''}</div>${right ? `<div class="page-head__right">${right}</div>` : ''}</div>`;
}

// ======================= A01 接單看板：票軌 =======================
let seenOrderIds = null;
export async function adminBoard() {
  const [r, orders] = await Promise.all([api.admin.getRestaurant(), api.admin.listOrders()]);
  const fresh = new Set(seenOrderIds ? orders.filter((o) => !seenOrderIds.has(o.id)).map((o) => o.id) : []);
  if (fresh.size) toast(t('admin.new_order_toast', { n: fresh.size }));
  seenOrderIds = new Set(orders.map((o) => o.id));
  poll(rerender, 4000);

  const cols = [['new', 'admin.col_new'], ['preparing', 'admin.col_preparing'], ['ready', 'admin.col_ready']];
  const accepting = r.is_accepting_orders;
  const right = `<label class="accepting${accepting ? '' : ' is-paused'}"><span>${esc(t(accepting ? 'admin.accepting' : 'admin.paused'))}</span>${C.Toggle({ on: accepting, action: 'toggle-accepting', label: t('admin.accepting') })}</label>`;
  return layout('orders', `
    ${pageHeader(t('admin.nav.orders'), t('admin.board_sub', { n: r.today_order_count ?? 0 }), right)}
    <div class="rails">${cols.map(([k, key]) => {
      const list = orders.filter((o) => C.boardColumn(o.status) === k);
      return `<section class="rail" aria-label="${esc(t(key))}">
        <div class="rail__head"><h2>${esc(t(key))}</h2><span class="fig-strong">${list.length}</span></div>
        ${list.map((o) => C.KitchenTicket(o, fresh.has(o.id))).join('') || `<p class="empty small">${esc(t('admin.col_empty'))}</p>`}
      </section>`;
    }).join('')}</div>`);
}
actions['order-status'] = async (d) => {
  if (d.to === 'recall') { toast(t('admin.called', { no: d.no })); return; }
  if (d.to === 'cancelled' && !(await confirmDialog(t('admin.reject_confirm', { no: d.no }), { danger: true }))) return;
  await api.admin.updateOrderStatus(d.id, d.to);
  if (d.to === 'ready') toast(t('admin.notified', { no: d.no }));
  rerender();
};
actions['toggle-accepting'] = async () => {
  const r = await api.admin.getRestaurant();
  await api.admin.updateRestaurant({ is_accepting_orders: !r.is_accepting_orders });
  rerender();
};

// ======================= A02 菜單管理 / A03 品項編輯 =======================
const menuState = { cat: 'all', data: null };
export async function adminMenu() {
  const data = await api.admin.listMenuItems();
  menuState.data = data;
  const items = menuState.cat === 'all' ? data.items : data.items.filter((i) => i.category_id === menuState.cat);
  const soldOut = data.items.filter((i) => i.is_sold_out).length;
  const tabs = [{ id: 'all', name: t('home.loc_all') }, ...data.categories];
  const L = (k) => esc(t(k));
  const rows = items.map((i) => `<tr>
      <td data-label="${L('admin.menu.col_item')}"><span class="cell-media">${C.Photo({ url: i.image_url, kind: 'mini' })}<span>${esc(i.name)}</span></span></td>
      <td data-label="${L('admin.menu.col_category')}" class="muted">${esc(i.category_name)}</td>
      <td data-label="${L('admin.menu.col_price')}" class="num">${money(i.price)}</td>
      <td data-label="${L('admin.menu.col_prep')}" class="num">${esc(t('unit.minutes', { n: i.prep_minutes }))}</td>
      <td data-label="${L('admin.menu.col_listed')}">${C.Toggle({ on: i.is_available, action: 'menu-toggle', data: { id: i.id, field: 'is_available' }, label: `${i.name} ${t('admin.menu.col_listed')}` })}</td>
      <td data-label="${L('admin.menu.col_sold_out')}">${C.Toggle({ on: i.is_sold_out, action: 'menu-toggle', data: { id: i.id, field: 'is_sold_out' }, label: `${i.name} ${t('admin.menu.col_sold_out')}` })}</td>
      <td class="act">${C.Button({ label: t('common.edit'), size: 'sm', action: 'menu-edit', data: { id: i.id } })}</td>
    </tr>`).join('');
  return layout('menu', `
    ${pageHeader(t('admin.nav.menu'), t('admin.menu.sub', { n: data.items.length, s: soldOut }), C.Button({ label: t('admin.menu.new'), style: 'primary', size: 'sm', action: 'menu-new' }))}
    ${C.Tabs(tabs.map((c) => ({ name: c.name, selected: c.id === menuState.cat, action: 'admin-menu-cat', data: { cat: c.id } })), { label: t('admin.menu.col_category') })}
    ${items.length ? `<div class="table-wrap"><table class="data data--stack">
      <thead><tr><th scope="col">${L('admin.menu.col_item')}</th><th scope="col">${L('admin.menu.col_category')}</th><th scope="col" class="num">${L('admin.menu.col_price')}</th><th scope="col" class="num">${L('admin.menu.col_prep')}</th><th scope="col">${L('admin.menu.col_listed')}</th><th scope="col">${L('admin.menu.col_sold_out')}</th><th scope="col" class="act"><span class="visually-hidden">${L('admin.menu.col_actions')}</span></th></tr></thead>
      <tbody>${rows}</tbody></table></div>`
      : `<div class="state"><p>${esc(t('menu.empty'))}</p>${C.Button({ label: t('admin.menu.new'), style: 'primary', size: 'sm', action: 'menu-new' })}</div>`}`);
}
actions['admin-menu-cat'] = (d) => { menuState.cat = d.cat; rerender(); };
actions['menu-toggle'] = async (d) => {
  const item = menuState.data.items.find((i) => i.id === d.id);
  await api.admin.patchMenuItem(d.id, { [d.field]: !item[d.field] });
  rerender();
};

function menuDialog(item) {
  const cats = menuState.data.categories;
  const isNew = !item;
  const i = item ?? { id: '', name: '', description: '', price: '', prep_minutes: '', category_id: menuState.cat !== 'all' ? menuState.cat : cats[0]?.id, is_available: true, is_sold_out: false, option_groups: [] };
  const title = t(isNew ? 'admin.menu.new_title' : 'admin.menu.edit_title');
  const groups = i.option_groups.map((g) => `<li><span class="strong">${esc(g.name)}</span> <span class="muted">${esc(t(g.required ? 'item.pick_one' : 'item.optional'))}</span><br><span class="small">${esc(g.choices.map((c) => `${c.label} +${c.price_delta}`).join(t('fmt.list_sep')))}</span></li>`).join('');
  return `<form class="dialog" data-form="menu-item" role="dialog" aria-modal="true" aria-label="${esc(title)}" novalidate>
    <input type="hidden" name="id" value="${esc(i.id)}">
    <div class="dialog__head"><h2>${esc(title)}</h2><button type="button" class="icon-btn" data-action="modal-close" aria-label="${esc(t('common.close'))}">${icon('x')}</button></div>
    <div class="field-pair">
      ${C.TextField({ label: t('admin.menu.f_name'), name: 'name', value: i.name, required: true })}
      <div class="field"><label for="f-category_id">${esc(t('admin.menu.col_category'))}</label>
        <select id="f-category_id" name="category_id">${cats.map((c) => `<option value="${esc(c.id)}"${c.id === i.category_id ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}</select></div>
    </div>
    <div class="field-pair">
      ${C.TextField({ label: t('admin.menu.f_price'), name: 'price', type: 'number', value: i.price, required: true, extra: 'min="0" step="1" inputmode="numeric"' })}
      ${C.TextField({ label: t('admin.menu.f_prep'), name: 'prep_minutes', type: 'number', value: i.prep_minutes, required: true, extra: 'min="0" step="1" inputmode="numeric"' })}
    </div>
    ${C.TextField({ label: t('admin.menu.f_desc'), name: 'description', value: i.description, textarea: true })}
    ${C.PhotoField({ name: 'image_url', label: t('admin.menu.f_photo'), url: i.image_url, kind: 'hero' })}
    ${groups ? `<div class="stack stack--tight"><span class="small muted">${esc(t('admin.menu.option_groups'))}</span><ul class="rows" style="padding-top:var(--space-2xs)">${groups}</ul></div>` : ''}
    <div>
      <label class="switch-row"><span>${esc(t('admin.menu.f_listed'))}</span><input type="checkbox" class="switch" name="is_available"${i.is_available ? ' checked' : ''}></label>
      <label class="switch-row"><span>${esc(t('admin.menu.f_sold_out'))}</span><input type="checkbox" class="switch" name="is_sold_out"${i.is_sold_out ? ' checked' : ''}></label>
    </div>
    <div class="dialog__foot">
      ${isNew ? '' : C.Button({ label: t('admin.menu.delete'), style: 'danger', size: 'sm', action: 'menu-delete', data: { id: i.id } })}
      <span class="grow"></span>
      ${C.Button({ label: t('common.cancel'), style: 'text', size: 'sm', action: 'modal-close' })}
      ${C.Button({ label: t('common.save'), style: 'primary', size: 'sm', type: 'submit' })}
    </div>
  </form>`;
}
actions['menu-new'] = () => { openModal(menuDialog(null)); document.getElementById('f-name')?.focus(); };
actions['menu-edit'] = (d) => { openModal(menuDialog(menuState.data.items.find((i) => i.id === d.id))); document.getElementById('f-name')?.focus(); };
actions['menu-delete'] = async (d) => {
  if (!(await confirmDialog(t('admin.menu.delete_confirm'), { danger: true }))) return;
  await api.admin.deleteMenuItem(d.id);
  closeModal();
  toast(t('admin.menu.deleted'));
  rerender();
};
forms['menu-item'] = async (fd, form) => {
  if (!form.checkValidity()) { form.reportValidity(); form.querySelector(':invalid')?.focus(); return; }
  await api.admin.saveMenuItem({
    id: fd.get('id') || undefined,
    name: String(fd.get('name')).trim(),
    description: String(fd.get('description') || '').trim(),
    category_id: fd.get('category_id'),
    price: Number(fd.get('price')),
    prep_minutes: Number(fd.get('prep_minutes')),
    is_available: fd.get('is_available') === 'on',
    is_sold_out: fd.get('is_sold_out') === 'on',
    image_url: fd.get('image_url') || null,
  });
  closeModal();
  toast(t('common.saved'));
  rerender();
};

// ======================= A04 店家設定 =======================
export async function adminSettings() {
  const r = await api.admin.getRestaurant();
  const switchRow = (name, title, checked) => `<label class="switch-row"><span>${esc(title)}</span><input type="checkbox" class="switch" name="${name}"${checked ? ' checked' : ''}></label>`;
  return layout('settings', `<form class="stack stack--loose" data-form="settings" novalidate>
    ${pageHeader(t('admin.nav.settings'), '', C.Button({ label: t('common.save'), style: 'primary', size: 'sm', type: 'submit' }))}
    <div class="settings">
      <div class="stack stack--loose">
      <section>
        <h2>${esc(t('admin.settings.profile'))}</h2>
        ${C.TextField({ label: t('admin.settings.f_name'), name: 'name', value: r.name, required: true, extra: 'autocomplete="organization"' })}
        ${C.TextField({ label: t('admin.settings.f_location'), name: 'location', value: r.location, required: true })}
        ${C.TextField({ label: t('admin.settings.f_desc'), name: 'description', value: r.description, textarea: true })}
        ${C.TextField({ label: t('admin.settings.f_phone'), name: 'phone', value: r.phone, type: 'tel', extra: 'autocomplete="tel" inputmode="tel"' })}
      </section>
      <section>
        <h2>${esc(t('admin.settings.photos'))}</h2>
        ${C.PhotoField({ name: 'cover_image_url', label: t('admin.settings.cover'), url: r.cover_image_url, kind: 'cover' })}
        ${C.PhotoField({ name: 'image_url', label: t('admin.settings.thumb'), url: r.image_url, kind: 'thumb' })}
      </section>
      </div>
      <div class="stack stack--loose">
        <section>
          <h2>${esc(t('admin.settings.hours'))}</h2>
          ${r.opening_hours.length ? `<dl class="hours">${r.opening_hours.map((h) => `<dt>${esc(h.days)}</dt><dd>${esc(h.hours)}</dd>`).join('')}</dl>` : `<p class="muted">${esc(r.opening_hours_label)}</p>`}
        </section>
        <section>
          <h2>${esc(t('admin.settings.orders'))}</h2>
          <div>
            ${switchRow('is_accepting_orders', t('admin.settings.accept_online'), r.is_accepting_orders)}
            ${switchRow('allow_cash_on_pickup', t('admin.settings.cash'), r.allow_cash_on_pickup)}
            ${switchRow('allow_scheduled_pickup', t('admin.settings.scheduled'), r.allow_scheduled_pickup)}
          </div>
          <div class="field-pair">
            ${C.TextField({ label: t('admin.settings.capacity'), name: 'concurrent_capacity', type: 'number', value: r.concurrent_capacity, extra: 'min="1" step="1" inputmode="numeric"' })}
            ${C.TextField({ label: t('admin.settings.hold'), name: 'pickup_hold_minutes', type: 'number', value: r.pickup_hold_minutes, extra: 'min="5" step="5" inputmode="numeric"' })}
          </div>
        </section>
      </div>
    </div>
  </form>`);
}
forms.settings = async (fd, form) => {
  if (!form.checkValidity()) { form.reportValidity(); form.querySelector(':invalid')?.focus(); return; }
  await api.admin.updateRestaurant({
    name: String(fd.get('name')).trim(), location: String(fd.get('location')).trim(),
    description: String(fd.get('description') || '').trim(), phone: String(fd.get('phone') || '').trim(),
    is_accepting_orders: fd.get('is_accepting_orders') === 'on', allow_cash_on_pickup: fd.get('allow_cash_on_pickup') === 'on',
    allow_scheduled_pickup: fd.get('allow_scheduled_pickup') === 'on',
    concurrent_capacity: Number(fd.get('concurrent_capacity')), pickup_hold_minutes: Number(fd.get('pickup_hold_minutes')),
    cover_image_url: fd.get('cover_image_url') || null, image_url: fd.get('image_url') || null,
  });
  toast(t('common.saved'));
  rerender();
};

// ======================= A05 營收報表 =======================
const reportState = { range: 'today' };
function barChart(slots) {
  const peak = Math.max(...slots.map((s) => s.count), 1);
  const step = peak <= 10 ? 2 : peak <= 40 ? 10 : peak <= 200 ? 50 : 200;
  const top = Math.ceil(peak / step) * step;
  const ticks = Array.from({ length: top / step + 1 }, (_, k) => k * step);
  const peakIdx = slots.findIndex((s) => s.count === peak);
  return `<div class="chart" role="img" aria-label="${esc(t('reports.chart_title'))}">
    <div class="chart__grid" aria-hidden="true">${ticks.map((v) => `<div class="chart__line${v === 0 ? ' chart__line--base' : ''}" style="bottom:${(v / top) * 100}%"><span>${v}</span></div>`).join('')}</div>
    <div class="chart__bars">${slots.map((s, k) => `<div class="chart__col" tabindex="0" data-tip="${esc(s.slot)}　${esc(t('reports.orders_n', { n: s.count }))}" aria-label="${esc(s.slot)} ${esc(t('reports.orders_n', { n: s.count }))}">
        <div class="chart__area">${k === peakIdx ? `<span class="chart__val">${s.count}</span>` : ''}<div class="chart__bar${k === peakIdx ? ' is-peak' : ''}" style="height:${(s.count / top) * 100}%"></div></div>
        <span class="chart__label">${esc(s.slot)}</span></div>`).join('')}</div>
  </div>
  <table class="visually-hidden"><caption>${esc(t('reports.chart_title'))}</caption><tbody>${slots.map((s) => `<tr><th scope="row">${esc(s.slot)}</th><td>${s.count}</td></tr>`).join('')}</tbody></table>`;
}
export async function adminReports() {
  const { summary: s, orders_by_slot, top_items } = await api.admin.reports(reportState.range);
  const sign = (n) => (n > 0 ? `+${n}` : `${n}`.replace('-', '−'));
  const ranges = [['today', 'reports.today'], ['week', 'reports.week'], ['month', 'reports.month']];
  const vs = t('reports.vs_' + reportState.range);
  const fig = (label, value, delta) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd><dd class="delta">${esc(delta)}</dd></div>`;
  const seg = `<div class="seg" role="group" aria-label="${esc(t('admin.nav.reports'))}">${ranges.map(([k, key]) => `<button type="button" data-action="report-range" data-range="${k}" aria-pressed="${k === reportState.range}">${esc(t(key))}</button>`).join('')}</div>`;
  return layout('reports', `
    ${pageHeader(t('admin.nav.reports'), '', seg)}
    <dl class="figures">
      ${fig(t('reports.orders'), s.order_count.toLocaleString('en-US'), `${vs} ${sign(s.delta_orders)}%`)}
      ${fig(t('reports.revenue'), money(s.revenue), `${vs} ${sign(s.delta_revenue)}%`)}
      ${fig(t('reports.avg_wait'), t('unit.minutes', { n: s.avg_wait_minutes }), `${vs} ${t('unit.minutes', { n: sign(s.delta_wait) })}`)}
      ${fig(t('reports.cancel_rate'), `${s.cancel_rate}%`, `${vs} ${sign(s.delta_cancel)}%`)}
    </dl>
    <div class="reports-row">
      <section><h2>${esc(t('reports.chart_title'))}</h2>${barChart(orders_by_slot)}</section>
      <section><h2>${esc(t('reports.top_items'))}</h2>
        <table class="data"><thead><tr><th scope="col" class="num">#</th><th scope="col">${esc(t('admin.menu.col_item'))}</th><th scope="col" class="num">${esc(t('cart.qty'))}</th><th scope="col" class="num">${esc(t('reports.revenue'))}</th></tr></thead>
        <tbody>${top_items.map((x, k) => `<tr><td class="num">${k + 1}</td><td>${esc(x.name)}</td><td class="num">${esc(x.qty)}</td><td class="num">${money(x.revenue)}</td></tr>`).join('')}</tbody></table>
      </section>
    </div>`);
}
actions['report-range'] = (d) => { reportState.range = d.range; rerender(); };

// ======================= A06 平台管理 =======================
export async function adminPlatform() {
  const { stats, restaurants } = await api.platform.listRestaurants();
  const L = (k) => esc(t(k));
  const rows = restaurants.map((r) => {
    const [key, cls] = C.restaurantStatus(r);
    const act = r.status === 'pending' ? ['admin.platform.approve', 'active', 'primary'] : r.status === 'suspended' ? ['admin.platform.restore', 'active', 'secondary'] : ['admin.platform.suspend', 'suspended', 'danger'];
    return `<tr>
      <td data-label="${L('admin.platform.col_name')}"><span class="cell-media">${C.Photo({ url: r.image_url, kind: 'mini' })}<span>${esc(r.name)}</span></span></td>
      <td data-label="${L('admin.settings.f_location')}" class="muted">${esc(r.location)}</td>
      <td data-label="${L('admin.platform.col_account')}" class="fig">${esc(r.owner_account)}</td>
      <td data-label="${L('admin.platform.col_status')}"><span class="status-word ${cls}">${esc(t(key))}</span></td>
      <td data-label="${L('admin.platform.col_orders')}" class="num">${r.status === 'pending' ? '' : esc(r.today_order_count)}</td>
      <td class="act">${C.Button({ label: t(act[0]), style: act[2], size: 'sm', action: 'restaurant-status', data: { id: r.id, to: act[1] } })}</td>
    </tr>`;
  }).join('');
  return layout('platform', `
    ${pageHeader(t('admin.platform.title'))}
    <dl class="figures">
      <div><dt>${L('admin.platform.restaurants')}</dt><dd>${esc(t('admin.platform.count', { n: stats.restaurant_count }))}</dd><dd class="delta">${esc(t('admin.platform.pending_n', { n: stats.pending_count }))}</dd></div>
      <div><dt>${L('admin.platform.orders_today')}</dt><dd>${esc(stats.orders_today.toLocaleString('en-US'))}</dd><dd class="delta">${esc(`${t('reports.vs_today')} +${stats.delta_orders}%`)}</dd></div>
      <div><dt>${L('admin.platform.users')}</dt><dd>${esc(stats.users.toLocaleString('en-US'))}</dd><dd class="delta">${esc(t('admin.platform.new_users', { n: stats.new_users_week }))}</dd></div>
    </dl>
    <div class="table-wrap"><table class="data data--stack">
      <thead><tr><th scope="col">${L('admin.platform.col_name')}</th><th scope="col">${L('admin.settings.f_location')}</th><th scope="col">${L('admin.platform.col_account')}</th><th scope="col">${L('admin.platform.col_status')}</th><th scope="col" class="num">${L('admin.platform.col_orders')}</th><th scope="col" class="act"><span class="visually-hidden">${L('admin.menu.col_actions')}</span></th></tr></thead>
      <tbody>${rows}</tbody></table></div>`);
}
actions['restaurant-status'] = async (d) => {
  if (d.to === 'suspended' && !(await confirmDialog(t('admin.platform.suspend_confirm'), { danger: true }))) return;
  await api.platform.setRestaurantStatus(d.id, d.to);
  rerender();
};

// ======================= 照片上傳（菜單品項、店家設定共用） =======================
function setPhoto(name, url, kind) {
  const box = document.querySelector(`[data-photo-field="${name}"]`);
  if (!box) return;
  box.querySelector(`input[type=hidden][name="${name}"]`).value = url || '';
  box.querySelector('.photo-field__preview').innerHTML = C.Photo({ url, kind });
  box.querySelector('.photo-field__pick span').textContent = t(url ? 'photo.replace' : 'photo.upload');
  box.querySelector('[data-action=photo-remove]').hidden = !url;
}
inputs['photo-upload'] = async (el) => {
  const file = el.files?.[0];
  if (!file) return;
  const label = el.closest('.photo-field__pick').querySelector('span');
  label.textContent = t('photo.working');
  try {
    const { url } = await api.uploadImage(file);
    setPhoto(el.dataset.name, url, el.dataset.kind);
  } catch (err) {
    toast(err.message || String(err));
    label.textContent = t('photo.upload');
  } finally {
    el.value = '';
  }
};
actions['photo-remove'] = (d) => setPhoto(d.name, null, d.kind);
