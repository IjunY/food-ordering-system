// v2 元件：收據／票券風格。參數名稱沿用 API 欄位（restaurant.name、order.status…），接後端時不用改。
import { t, getLang } from './i18n.js';
import { icon } from './icons.js';

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const money = (n) => `NT$ ${Number(n).toLocaleString('en-US')}`;
export const hhmm = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};
export const mmdd = (iso) => {
  const d = new Date(iso);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
};
const dataAttrs = (data = {}) => Object.entries(data).map(([k, v]) => ` data-${k}="${esc(v)}"`).join('');
const actionAttr = (action) => (action ? ` data-action="${action}"` : '');

// Button：style＝primary / secondary（預設，外框）/ text / danger；size＝lg / sm
export function Button({ label, style = 'secondary', size = 'lg', block = false, action, type = 'button', data, disabled = false, figure = '' }) {
  const cls = ['btn', style === 'secondary' ? '' : `btn--${style}`, size === 'sm' ? 'btn--sm' : '', block ? 'btn--block' : '', figure ? 'btn--split' : ''].filter(Boolean).join(' ');
  return `<button type="${type}" class="${cls}"${actionAttr(action)}${dataAttrs(data)}${disabled ? ' disabled' : ''}><span>${esc(label)}</span>${figure ? `<span class="fig-strong">${esc(figure)}</span>` : ''}</button>`;
}

// 頂列：back＝是否有返回鍵
export function TopBar({ title, back = false, right = '' }) {
  return `<header class="topbar">${back ? `<button type="button" class="icon-btn" data-action="back" aria-label="${esc(t('a11y.back'))}">${icon('back')}</button>` : ''}<h1 class="topbar__title">${esc(title)}</h1>${right}</header>`;
}

// 顧客端底部三個文字分頁
export function BottomNav({ active }) {
  const tabs = [['home', 'nav.home'], ['orders', 'nav.orders'], ['profile', 'nav.profile']];
  return `<nav class="bottom-nav" aria-label="${esc(t('app.name'))}">${tabs.map(([k, key]) => `<a href="#${k}"${k === active ? ' aria-current="page"' : ''}>${esc(t(key))}</a>`).join('')}</nav>`;
}

export function LangSwitch() {
  const cur = getLang();
  return `<div class="seg" role="group" aria-label="${esc(t('lang.switch'))}">
    <button type="button" data-action="set-lang" data-lang="zh" aria-pressed="${cur === 'zh'}">中文</button>
    <button type="button" data-action="set-lang" data-lang="en" aria-pressed="${cur === 'en'}">EN</button>
  </div>`;
}

export function Tabs(items, { sticky = false, label = '' } = {}) {
  return `<div class="tabs${sticky ? ' tabs--sticky' : ''}" role="group"${label ? ` aria-label="${esc(label)}"` : ''}>${items.map(({ name, selected, action, data }) => `<button type="button" class="tab" aria-pressed="${!!selected}"${actionAttr(action)}${dataAttrs(data)}>${esc(name)}</button>`).join('')}</div>`;
}

// 單選／複選列
export function Choice({ label, aside = '', sub = '', selected, multi = false, action, data, disabled }) {
  return `<button type="button" class="choice${multi ? ' choice--multi' : ''}" role="${multi ? 'checkbox' : 'radio'}" aria-checked="${!!selected}"${actionAttr(action)}${dataAttrs(data)}${disabled ? ' disabled' : ''}>
    <span class="choice__mark" aria-hidden="true"></span><span class="choice__label">${esc(label)}${sub ? `<span class="choice__sub">${esc(sub)}</span>` : ''}</span>${aside ? `<span class="choice__aside">${esc(aside)}</span>` : ''}
  </button>`;
}

export function QtyStepper({ qty, action, data, small = false, min = 0 }) {
  return `<span class="qty${small ? ' qty--sm' : ''}">
    <button type="button"${actionAttr(action)} data-delta="-1"${dataAttrs(data)} aria-label="${esc(t('a11y.decrease'))}"${qty <= min ? ' disabled' : ''}>${icon('minus')}</button>
    <output aria-live="polite">${qty}</output>
    <button type="button"${actionAttr(action)} data-delta="1"${dataAttrs(data)} aria-label="${esc(t('a11y.increase'))}">${icon('plus')}</button>
  </span>`;
}

export function TextField({ label, name, value = '', placeholder = '', type = 'text', required = false, input, data, textarea = false, extra = '' }) {
  const id = 'f-' + name;
  const common = `id="${id}" name="${esc(name)}"${placeholder ? ` placeholder="${esc(placeholder)}"` : ''}${required ? ' required' : ''}${input ? ` data-input="${input}"` : ''}${dataAttrs(data)} ${extra}`;
  const control = textarea ? `<textarea ${common} rows="3">${esc(value)}</textarea>` : `<input type="${type}" ${common} value="${esc(value)}">`;
  return `<div class="field"><label for="${id}">${esc(label)}</label>${control}</div>`;
}

export function Toggle({ on, action, data, label = '' }) {
  return `<button type="button" class="toggle" role="switch" aria-checked="${!!on}" aria-label="${esc(label)}"${actionAttr(action)}${dataAttrs(data)}></button>`;
}

// 照片框：有網址放照片，沒有就留一個標示「照片」的空框（尺寸由 kind 決定：cover 16:9、hero 4:3、thumb 方形、mini 小方形）
export function Photo({ url, alt = '', kind = 'thumb', cls = '' }) {
  const inner = url
    ? `<img src="${esc(url)}" alt="${esc(alt)}" loading="lazy" decoding="async">`
    : `<span class="photo__empty">${esc(t('photo.none'))}</span>`;
  return `<span class="photo photo--${kind}${url ? '' : ' is-empty'}${cls ? ' ' + cls : ''}" data-slot="${kind}" data-alt="${esc(alt)}">${inner}</span>`;
}

// 後台上傳欄位：預覽＋上傳／更換＋移除；name＝送出時的欄位（image_url、cover_image_url）
export function PhotoField({ name, label, url, kind = 'hero' }) {
  const id = 'up-' + name;
  return `<div class="photo-field" data-photo-field="${esc(name)}">
    <span class="field__label" id="${id}-label">${esc(label)}</span>
    <div class="photo-field__body">
      <span class="photo-field__preview">${Photo({ url, kind })}</span>
      <div class="photo-field__actions">
        <label class="btn btn--sm photo-field__pick"><input type="file" accept="image/*" class="visually-hidden" data-input="photo-upload" data-name="${esc(name)}" data-kind="${esc(kind)}" aria-labelledby="${id}-label"><span>${esc(t(url ? 'photo.replace' : 'photo.upload'))}</span></label>
        <button type="button" class="btn btn--text btn--sm" data-action="photo-remove" data-name="${esc(name)}" data-kind="${esc(kind)}"${url ? '' : ' hidden'}>${esc(t('photo.remove'))}</button>
      </div>
    </div>
    <input type="hidden" name="${esc(name)}" value="${esc(url || '')}">
  </div>`;
}

// 等候看板的一列：營業中顯示分鐘數，休息顯示開門時間
export function WaitRow(r) {
  const open = r.is_open && r.is_accepting_orders !== false;
  const right = open
    ? `<span class="wb-row__min">${esc(r.wait_minutes)}<small>${esc(t('home.min'))}</small></span><span class="small muted">${esc(t('home.ahead', { n: r.queue_count }))}</span>`
    : `<span class="wb-row__min">${esc(r.is_open ? t('restaurant.paused') : t('wait.closed'))}</span><span class="small muted">${esc(t('home.opens_at', { hours: r.opening_hours_label }))}</span>`;
  return `<li><a class="wb-row${open ? '' : ' is-closed'}" href="#r-${esc(r.id)}">
    ${Photo({ url: r.image_url, kind: 'thumb' })}
    <span class="stack stack--tight"><span class="wb-row__name">${esc(r.name)}</span><span class="small muted">${esc(r.location)}</span></span>
    <span class="wb-row__wait">${right}</span>
  </a></li>`;
}

// 菜單一列：品名……價格（點點引線）
export function MenuRow(item, rid) {
  const sold = item.is_sold_out || item.is_available === false;
  const inner = `${Photo({ url: item.image_url, kind: 'thumb', cls: 'menu-row__photo' })}<span class="menu-row__name">${esc(item.name)}${sold ? `<span class="menu-row__tag">${esc(t('menu.sold_out'))}</span>` : ''}</span>
    <span class="menu-row__lead" aria-hidden="true"></span>
    <span class="menu-row__price">${money(item.price)}</span>
    ${item.description ? `<span class="menu-row__desc">${esc(item.description)}</span>` : ''}`;
  return `<li>${sold ? `<div class="menu-row is-sold-out">${inner}</div>` : `<a class="menu-row" href="#item-${esc(rid)}-${esc(item.id)}">${inner}</a>`}</li>`;
}

// 訂單狀態的文字（不用彩色徽章）
export function statusWord(status) {
  return `<span class="order-row__status${status === 'ready' ? ' is-ready' : ''}">${esc(t('status.' + status))}</span>`;
}

export const optionsText = (labels) => labels.filter(Boolean).join(t('fmt.list_sep'));
export function itemsSummary(items, sep = '\n') {
  return items.map((i) => `${i.name} ×${i.qty}${i.options_label ? t('fmt.paren', { x: i.options_label }) : ''}`).join(sep);
}
export function paymentText(o) {
  return `${t('pay.method.' + o.payment_method)}${t('fmt.paren', { x: t(o.payment_status === 'paid' ? 'pay.paid' : 'pay.unpaid') })}`;
}

// 看板欄位
export function boardColumn(status) {
  if (status === 'paid' || status === 'pending_payment') return 'new';
  if (status === 'accepted' || status === 'preparing') return 'preparing';
  if (status === 'ready') return 'ready';
  return null;
}

// 廚房票：一張訂單
export function KitchenTicket(o, isNew = false) {
  const col = boardColumn(o.status);
  const acts = {
    new: [['ink', 'admin.accept', 'preparing'], ['secondary', 'admin.reject', 'cancelled']],
    preparing: [['ink', 'admin.mark_ready', 'ready']],
    ready: [['ink', 'admin.picked_up', 'picked_up'], ['secondary', 'admin.call_again', 'recall']],
  }[col];
  return `<article class="kt${isNew ? ' is-new' : ''}" aria-label="#${esc(o.pickup_number)}">
    <div class="kt__head"><span class="kt__no">${esc(o.pickup_number)}</span><span class="fig small muted">${hhmm(o.created_at)}</span></div>
    <ul class="kt__items">${o.items.map((i) => `<li><span class="fig">${esc(i.qty)}</span><span>${esc(i.name)}${i.options_label ? `<span class="small muted">${esc(t('fmt.paren', { x: i.options_label }))}</span>` : ''}</span></li>`).join('')}</ul>
    ${o.note ? `<div class="kt__note">${esc(t('admin.note', { note: o.note }))}</div>` : ''}
    <div class="kt__foot"><span class="fig-strong">${money(o.total)}</span><span class="small muted">${esc(paymentText(o))}</span></div>
    <div class="kt__actions">${acts.map(([st, key, to]) => Button({ label: t(key), style: st, size: 'sm', block: true, action: 'order-status', data: { id: o.id, to, no: o.pickup_number } })).join('')}</div>
  </article>`;
}

export function restaurantStatus(r) {
  if (r.status === 'pending') return ['admin.platform.pending', 'is-warn'];
  if (r.status === 'suspended') return ['admin.platform.suspended', 'is-stop'];
  return r.is_open ? ['admin.platform.open', ''] : ['admin.platform.closed', 'is-off'];
}
