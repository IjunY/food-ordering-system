// 元件（紫色取餐券版，設計規則見根目錄 DESIGN.md）。參數名稱沿用 API 欄位（restaurant.name、order.status…）。
import { t, getLang } from './i18n.js';
import { icon } from './icons.js';

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// 兩種價格寫法：合計、按鈕上的金額、訂單紀錄用「NT$」；單價用「$」
export const money = (n) => `NT$${Number(n).toLocaleString('en-US')}`;
export const unit = (n) => `$${Number(n).toLocaleString('en-US')}`;
const two = (n) => String(n).padStart(2, '0');
export const hhmm = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${two(d.getHours())}:${two(d.getMinutes())}`;
};
export const hhmmss = (d = new Date()) => `${two(d.getHours())}:${two(d.getMinutes())}:${two(d.getSeconds())}`;
export const mmdd = (iso) => {
  const d = new Date(iso);
  return `${two(d.getMonth() + 1)}/${two(d.getDate())}`;
};
// 預約取餐時間：今天的只寫時間，其他天前面加「明天」或日期
const dayDiff = (iso) => {
  const a = new Date(iso); a.setHours(0, 0, 0, 0);
  const b = new Date(); b.setHours(0, 0, 0, 0);
  return Math.round((a - b) / 86400000);
};
export const dayLabel = (iso) => {
  const n = dayDiff(iso);
  return n === 0 ? t('pickup.today', { date: mmdd(iso) }) : n === 1 ? t('pickup.tomorrow', { date: mmdd(iso) }) : mmdd(iso);
};
export const pickupText = (iso) => {
  const n = dayDiff(iso);
  return n === 0 ? hhmm(iso) : `${n === 1 ? t('pickup.tomorrow_short') : mmdd(iso)} ${hhmm(iso)}`;
};
// 訂單頁那句「預估幾點可取餐」；預約的單改說「預約幾點取餐」
export const readyText = (o) => (o.pickup_type === 'scheduled' && o.pickup_time
  ? t('order.booked_for', { time: pickupText(o.pickup_time) })
  : t('order.ready_around', { time: hhmm(o.estimated_ready_at) }));
const dataAttrs = (data = {}) => Object.entries(data).map(([k, v]) => ` data-${k}="${esc(v)}"`).join('');
const actionAttr = (action) => (action ? ` data-action="${action}"` : '');

// 每個攤位一個紫色調，只用來染照片的空框（不當徽章、不當編號）
const TINTS = ['#5B2A86', '#7B3FB0', '#4A2370', '#9050C8', '#6A2C9E', '#7A3DAA'];
export function tint(id) {
  const n = [...String(id ?? '')].reduce((a, ch) => a + ch.charCodeAt(0), 0);
  return TINTS[n % TINTS.length];
}

export const SampleTag = () => `<span class="sample">${esc(t('sample'))}</span>`;

// Button：style＝primary / secondary（預設，紫框）/ text / danger / danger-fill；size＝lg / sm
export function Button({ label, style = 'secondary', size = 'lg', block = false, action, type = 'button', data, disabled = false }) {
  const cls = ['btn', style === 'secondary' ? '' : `btn--${style}`, size === 'sm' ? 'btn--sm' : '', block ? 'btn--block' : ''].filter(Boolean).join(' ');
  return `<button type="${type}" class="${cls}"${actionAttr(action)}${dataAttrs(data)}${disabled ? ' disabled' : ''}>${esc(label)}</button>`;
}

// 底部主要按鈕：figure 有值時左邊文字、右邊金額
export function Cta({ label, figure = '', action, data, href, type = 'button', disabled = false }) {
  const inner = `<span>${esc(label)}</span>${figure ? `<span class="num">${esc(figure)}</span>` : ''}`;
  const cls = `cta${figure ? '' : ' cta--center'}`;
  return href
    ? `<a class="${cls}" href="#${esc(href)}">${inner}</a>`
    : `<button type="${type}" class="${cls}"${actionAttr(action)}${dataAttrs(data)}${disabled ? ' disabled' : ''}>${inner}</button>`;
}

// 一次只顯示一種語言，用這顆切換
export function LangSwitch({ light = false } = {}) {
  const cur = getLang();
  return `<div class="tog${light ? ' tog--light' : ''}" role="group" aria-label="${esc(t('lang.switch'))}">
    <button type="button" data-action="set-lang" data-lang="zh" aria-pressed="${cur === 'zh'}" lang="zh-Hant">中</button>
    <button type="button" data-action="set-lang" data-lang="en" aria-pressed="${cur === 'en'}" lang="en">EN</button>
  </div>`;
}

// 紫色頂列：back＝是否有返回鍵
export function TopBar({ title, back = false }) {
  return `<header class="hdr">${back ? `<button type="button" class="back" data-action="back" aria-label="${esc(t('a11y.back'))}">${icon('back')}</button>` : ''}<h1>${esc(title)}</h1>${LangSwitch()}</header>`;
}

// 顧客端底部三個分頁；訂單分頁上的黃色數字＝進行中的訂單數
export const navState = { activeOrders: 0 };
export function BottomNav({ active }) {
  const tabs = [['home', 'nav.home', 'store'], ['orders', 'nav.orders', 'ticket'], ['profile', 'nav.profile', 'user']];
  return `<nav class="tabbar" aria-label="${esc(t('app.name'))}">${tabs.map(([k, key, ic]) => `<a href="#${k}"${k === active ? ' aria-current="page"' : ''}>${icon(ic)}${esc(t(key))}${k === 'orders' && navState.activeOrders ? `<span class="badge">${navState.activeOrders}</span>` : ''}</a>`).join('')}</nav>`;
}

export function Tabs(items, { sticky = false, label = '', area = false } = {}) {
  return `<div class="tabs${sticky ? ' tabs--sticky' : ''}${area ? ' tabs--area' : ''}" role="group"${label ? ` aria-label="${esc(label)}"` : ''}>${items.map(({ name, selected, action, data, count }) => `<button type="button" aria-pressed="${!!selected}"${actionAttr(action)}${dataAttrs(data)}>${esc(name)}${count == null ? '' : `<span class="cnt">${esc(count)}</span>`}</button>`).join('')}</div>`;
}

// 選項列（放在白色群組裡）：multi＝方形勾選，否則圓形單選
export function Choice({ label, aside = '', sub = '', selected, multi = false, action, data, disabled }) {
  return `<button type="button" class="ochk${multi ? '' : ' ochk--radio'}" role="${multi ? 'checkbox' : 'radio'}" aria-checked="${!!selected}"${actionAttr(action)}${dataAttrs(data)}${disabled ? ' disabled' : ''}>
    <span class="box" aria-hidden="true">${multi ? icon('check') : ''}</span><span class="ol">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ''}</span>${aside ? `<span class="od">${esc(aside)}</span>` : ''}
  </button>`;
}

// 有圖示的單選列（付款方式）
export function OptRow({ label, sub = '', ic = 'card', selected, action, data }) {
  return `<button type="button" class="opt" role="radio" aria-checked="${!!selected}"${actionAttr(action)}${dataAttrs(data)}>
    <span class="oi">${icon(ic)}</span><span><b>${esc(label)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</span><span class="rd" aria-hidden="true"></span>
  </button>`;
}

export function QtyStepper({ qty, action, data, small = false, min = 0, max = Infinity }) {
  return `<span class="step${small ? ' step--sm' : ''}">
    <button type="button"${actionAttr(action)} data-delta="-1"${dataAttrs(data)} aria-label="${esc(t('a11y.decrease'))}"${qty <= min ? ' disabled' : ''}>${icon('minus')}</button>
    <output aria-live="polite">${qty}</output>
    <button type="button"${actionAttr(action)} data-delta="1"${dataAttrs(data)} aria-label="${esc(t('a11y.increase'))}"${qty >= max ? ' disabled' : ''}>${icon('plus')}</button>
  </span>`;
}

// 欄位：num＝用數字字型（學號）；reveal＝密碼欄的顯示／隱藏鈕；hint＝欄位下方的 HTML
export function TextField({ label, name, value = '', placeholder = '', type = 'text', required = false, input, data, textarea = false, extra = '', num = false, reveal = false, hint = '' }) {
  const id = 'f-' + name;
  const common = `id="${id}" name="${esc(name)}"${placeholder ? ` placeholder="${esc(placeholder)}"` : ''}${required ? ' required' : ''}${input ? ` data-input="${input}"` : ''}${dataAttrs(data)} ${extra}`;
  const control = textarea
    ? `<textarea ${common} rows="3">${esc(value)}</textarea>`
    : `<div class="input"><input type="${type}"${num ? ' class="num"' : ''} ${common} value="${esc(value)}">${reveal ? `<button type="button" class="eye" data-action="toggle-password" data-for="${id}" aria-pressed="false" aria-label="${esc(t('auth.pw_show'))}">${icon('eye')}</button>` : ''}</div>`;
  return `<div class="field"><label for="${id}">${esc(label)}</label>${control}${hint}</div>`;
}

// 開關（按了就存）
export function Toggle({ on, action, data, label = '' }) {
  return `<button type="button" class="switch" role="switch" aria-checked="${!!on}" aria-label="${esc(label)}"${actionAttr(action)}${dataAttrs(data)}><i></i></button>`;
}

// 提示條：kind＝''（一般）/ err / ok
export function Note({ text, kind = '', ic = kind === 'err' ? 'alert' : kind === 'ok' ? 'check' : 'info', action = '' }) {
  return `<div class="note${kind ? ' note--' + kind : ''}" role="${kind === 'err' ? 'alert' : 'status'}">${icon(ic)}<span>${esc(text)}</span>${action}</div>`;
}

// 照片框：有網址放照片，沒有就用攤位色調的空框。kind：card／hero（4:3）、cover（餐廳頁橫幅）、thumb、mini
export function Photo({ url, alt = '', kind = 'thumb', cls = '' }) {
  const caption = kind === 'thumb' || kind === 'mini' ? '' : `<span class="phl">${esc(t('photo.none'))}</span>`;
  const inner = url ? `<img src="${esc(url)}" alt="${esc(alt)}" loading="lazy" decoding="async">` : `${icon('photo')}${caption}`;
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

// ======================= 取餐券 =======================
// 訂單狀態 → 券的樣式與進度（四段：確認、製作中、可取餐、已取餐）
const LEG_OF = { pending_payment: 0, paid: 0, accepted: 1, preparing: 1, ready: 2, picked_up: 3 };
const passTone = (status) => (status === 'ready' ? 's-ready' : status === 'cancelled' ? 's-cancelled' : status === 'accepted' || status === 'preparing' ? 's-preparing' : 's-confirming');

// 取餐號：字首的英文字母用黃色
export function codeHtml(no) {
  const m = /^([A-Za-z]+)-?(.+)$/.exec(String(no ?? ''));
  return m ? `<span class="pfx">${esc(m[1])}</span>${esc(m[2])}` : esc(no);
}

function legs(status) {
  const n = status === 'cancelled' ? -1 : LEG_OF[status] ?? 0;
  return `<div class="legs" aria-hidden="true">${[0, 1, 2, 3].map((i) => {
    const done = status === 'picked_up' || i < n;
    const now = status !== 'picked_up' && i === n;
    return `<div class="${done ? 'd' : ''}${now ? ' n' : ''}"><i></i><span>${esc(t('pass.leg.' + i))}</span></div>`;
  }).join('')}</div>`;
}

// mode＝'mini'（首頁、我的訂單；整張可點，href 是要去的頁）或 'full'（訂單頁；extra 接在進度條後面）
export function Pass(o, { mode = 'mini', href = '', extra = '', snapping = false } = {}) {
  const status = t('pass.st.' + o.status);
  const cls = `pass pass--${mode} ${passTone(o.status)}${snapping ? ' snapping' : ''}`;
  const booked = o.pickup_type === 'scheduled' && o.pickup_time;
  const label = `${t('pass.pickup')} ${o.pickup_number}, ${status}, ${o.restaurant_name}${booked ? ', ' + t('order.booked_for', { time: pickupText(o.pickup_time) }) : ''}`;
  const top = mode === 'mini'
    ? `<div class="top"><span class="lab">${esc(t('pass.pickup'))}</span><span class="lab">${esc(t('pass.status'))}</span>
        <span class="code">${codeHtml(o.pickup_number)}</span><span class="vend">${esc(o.restaurant_name)}${booked ? `<small class="booked">${esc(t('order.booked_short', { time: pickupText(o.pickup_time) }))}</small>` : ''}</span><div class="stat"><b>${esc(status)}</b></div></div>`
    : `<div class="top"><span class="lab">${esc(t('pass.pickup'))}</span><span class="code">${codeHtml(o.pickup_number)}</span><div class="stat"><b>${esc(status)}</b></div></div>
       <dl class="fields"><div><dt class="lab">${esc(t('pass.stall'))}</dt><dd>${esc(o.restaurant_name)}</dd></div><div><dt class="lab">${esc(t('pass.place'))}</dt><dd>${esc(o.restaurant_location)}</dd></div><div><dt class="lab">${esc(t('pass.placed'))}</dt><dd class="num">${hhmm(o.created_at)}</dd></div>${booked ? `<div class="wide"><dt class="lab">${esc(t('pass.pickup_time'))}</dt><dd class="booked">${esc(t('order.booked_short', { time: pickupText(o.pickup_time) }))}</dd></div>` : ''}</dl>`;
  const inner = `${top}<div class="perf"></div>${legs(o.status)}${extra}`;
  return mode === 'mini'
    ? `<a class="${cls}" href="#${esc(href)}" aria-label="${esc(label)}">${inner}</a>`
    : `<section class="${cls}" aria-label="${esc(label)}">${inner}</section>`;
}

// 攤位卡（首頁兩欄）：cartN＝購物車裡這家的件數
export function StallCard(r, cartN = 0) {
  const open = r.is_open && r.is_accepting_orders !== false;
  const state = open
    ? `<span class="on">${esc(t('home.open'))}</span>`
    : `<span class="off">${esc(r.is_open ? t('restaurant.paused') : t('wait.closed'))}</span>`;
  const side = cartN ? `<span class="cartn">${esc(t('home.in_cart', { n: cartN }))}</span>` : open ? `<span class="wait">${esc(t('wait.minutes', { n: r.wait_minutes }))}</span>` : '';
  return `<li><a class="scard${open ? '' : ' closed'}" href="#r-${esc(r.id)}" style="--sc:${tint(r.id)}">
    ${Photo({ url: r.image_url, alt: '', kind: 'card' })}
    <span class="body"><span class="nm">${esc(r.name)}</span><span class="mt">${esc(r.location)}</span><span class="mt">${esc(r.opening_hours_label)}</span>
      <span class="st">${state}${side}</span></span>
  </a></li>`;
}

// 品項卡（菜單兩欄）：整張卡是一顆按鈕，點了進品項頁
export function ItemCard(item, rid, { inCart = 0, canOrder = true } = {}) {
  const sold = item.is_sold_out || item.is_available === false;
  const label = `${item.name}, ${unit(item.price)}${sold ? ', ' + t('menu.sold_out') : ''}${inCart ? ', ' + t('menu.in_cart', { n: inCart }) : ''}`;
  return `<li><a class="icard${sold ? ' out' : ''}" href="#item-${esc(rid)}-${esc(item.id)}" aria-label="${esc(label)}">
    <span class="iimg">${Photo({ url: item.image_url, alt: '', kind: 'card' })}${sold ? `<span class="sold">${esc(t('menu.sold_out'))}</span>` : ''}${inCart ? `<span class="incart">${esc(t('menu.in_cart', { n: inCart }))}</span>` : ''}</span>
    <span class="ibody"><span class="nm">${esc(item.name)}</span>
      <span class="ifoot"><span class="p">${unit(item.price)}</span>${sold || !canOrder ? '' : `<span class="add" aria-hidden="true">${icon('plus')}</span>`}</span></span>
  </a></li>`;
}

export const optionsText = (labels) => labels.filter(Boolean).join(t('fmt.list_sep'));
export function itemsSummary(items, sep = '\n') {
  return items.map((i) => `${i.name} ×${i.qty}${i.options_label ? t('fmt.paren', { x: i.options_label }) : ''}`).join(sep);
}
export function paymentText(o) {
  const st = { paid: 'pay.paid', refunded: 'pay.refunded' }[o.payment_status] || 'pay.unpaid';
  return `${t('pay.method.' + o.payment_method)}${t('fmt.paren', { x: t(st) })}`;
}

// ======================= 店家端 =======================
// 看板的四欄（像 Notion 的看板）：
//   unpaid   未付款・到店付款（顧客選了到店付款，還沒接單）
//   paid     已付款・待接單
//   accepted 已接單・製作中
//   ready    可取餐
export const BOARD_COLUMNS = ['unpaid', 'paid', 'accepted', 'ready'];
export function boardColumn(status) {
  if (status === 'pending_payment') return 'unpaid';
  if (status === 'paid') return 'paid';
  if (status === 'accepted' || status === 'preparing') return 'accepted';
  if (status === 'ready') return 'ready';
  return null;
}
// 卡片可以拖到哪一欄，拖過去等於改成哪個狀態（取餐、拒單只能按按鈕）
export const BOARD_MOVES = { unpaid: { accepted: 'preparing' }, paid: { accepted: 'preparing' }, accepted: { ready: 'ready' } };

// 廚房票：一張訂單，和顧客手上的取餐券同一套（紫＝新單、黃標＝製作中、綠＝可取餐）
export function KitchenTicket(o, isNew = false) {
  const col = boardColumn(o.status);
  const acts = {
    unpaid: [['primary', 'admin.accept', 'preparing'], ['danger', 'admin.reject', 'cancelled']],
    paid: [['primary', 'admin.accept', 'preparing'], ['danger', 'admin.reject', 'cancelled']],
    accepted: [['primary', 'admin.mark_ready', 'ready']],
    ready: [['primary', 'admin.picked_up', 'picked_up'], ['secondary', 'admin.call_again', 'recall']],
  }[col];
  const tone = { unpaid: 's-confirming', paid: 's-confirming', accepted: 's-preparing', ready: 's-ready' }[col];
  const draggable = BOARD_MOVES[col] ? ` draggable="true" data-drag-id="${esc(o.id)}" data-col="${col}" data-no="${esc(o.pickup_number)}"` : '';
  const booked = o.pickup_type === 'scheduled' && o.pickup_time;
  const sched = booked
    ? `<p class="kt__sched"><b>${esc(t('admin.booked', { time: pickupText(o.pickup_time) }))}</b>${o.start_by && col !== 'ready' ? `<span>${esc(t('admin.start_by', { time: hhmm(o.start_by) }))}</span>` : ''}</p>`
    : '';
  return `<article class="pass kt ${tone}${booked ? ' kt--booked' : ''}${isNew ? ' snapping' : ''}"${draggable} aria-label="${esc(t('pass.pickup'))} ${esc(o.pickup_number)}${booked ? ', ' + esc(t('admin.booked', { time: pickupText(o.pickup_time) })) : ''}">
    <div class="top"><span class="lab">${esc(t('pass.pickup'))}</span><span class="lab">${esc(t('pass.placed'))} ${hhmm(o.created_at)}</span>
      <span class="code">${codeHtml(o.pickup_number)}</span><div class="stat"><b>${esc(t('admin.chip.' + col))}</b></div></div>
    <div class="perf"></div>
    ${sched}
    <ul class="kt__items">${o.items.map((i) => `<li><span class="q">${esc(i.qty)}</span><span>${esc(i.name)}${i.options_label ? `<small class="lopt">${esc(i.options_label)}</small>` : ''}</span></li>`).join('')}</ul>
    ${o.note ? `<p class="kt__note">${esc(t('admin.note', { note: o.note }))}</p>` : ''}
    <div class="kt__foot"><b>${money(o.total)}</b><span>${esc(paymentText(o))}</span></div>
    <div class="kt__actions">${acts.map(([st, key, to]) => Button({ label: t(key), style: st, block: true, action: 'order-status', data: { id: o.id, to, no: o.pickup_number, ...(to === 'cancelled' && o.payment_status === 'paid' ? { refund: o.total } : {}) } })).join('')}</div>
  </article>`;
}

// 平台的餐廳狀態 → [字串 key, 標籤樣式]
export function restaurantStatus(r) {
  if (r.status === 'pending') return ['admin.platform.pending', 'chip--info'];
  if (r.status === 'suspended') return ['admin.platform.suspended', 'chip--stop'];
  return r.is_open ? ['admin.platform.open', 'chip--on'] : ['admin.platform.closed', 'chip--off'];
}
