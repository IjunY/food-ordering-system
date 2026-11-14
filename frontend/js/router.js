// 簡單的 hash 路由，加上全站共用的事件分派、輪詢、提示訊息與對話框。
// 網址用 #home、#r-r1、#item-r1-m1 這種純名稱（不用 #/path），上架到 claude.ai 時連結才帶得過去。
import { t } from './i18n.js';

export const actions = {}; // data-action="名稱" 被點擊時呼叫 actions[名稱](dataset, element, event)
export const forms = {};   // <form data-form="名稱"> 送出時呼叫 forms[名稱](FormData, form)
export const inputs = {};  // data-input="名稱" 輸入時呼叫 inputs[名稱](element)

const routes = [];
let timers = [];
let lastPath = null;

export function addRoute(pattern, page, opts = {}) {
  const keys = [];
  const re = new RegExp('^' + pattern.replace(/:(\w+)/g, (_, k) => { keys.push(k); return '([A-Za-z0-9]+)'; }) + '$');
  routes.push({ re, keys, page, opts });
}

export function currentPath() {
  return location.hash.slice(1) || 'login';
}

export function navigate(path) {
  if (location.hash.slice(1) === path) render();
  else location.hash = path;
}

// 頁面要定時更新時呼叫；換頁或重畫時自動停止
export function poll(fn, ms) {
  timers.push(setInterval(fn, ms));
}

let guard = () => null;
export function setGuard(fn) { guard = fn; }

export async function render() {
  timers.forEach(clearInterval);
  timers = [];
  const path = currentPath();
  const match = routes.map((r) => ({ r, m: r.re.exec(path) })).find((x) => x.m);
  if (!match) { navigate('login'); return; }
  const redirect = guard(match.r.opts);
  if (redirect) { navigate(redirect); return; }
  const params = Object.fromEntries(match.r.keys.map((k, i) => [k, decodeURIComponent(match.m[i + 1])]));
  const samePage = path === lastPath;
  if (!samePage) closeModal();
  const y = window.scrollY;
  // 換頁時資料超過 200 毫秒還沒回來，先放骨架（同一頁重畫不閃）
  const app = document.getElementById('app');
  const loadingTimer = samePage ? null : setTimeout(() => {
    if (currentPath() === path) app.innerHTML = `<div class="skel-rows" aria-busy="true" aria-label="${escText(t('common.loading'))}"><span class="skel"></span><span class="skel"></span><span class="skel"></span><span class="skel"></span></div>`;
  }, 200);
  try {
    const html = await match.r.page(params);
    if (currentPath() !== path) return; // 等資料時使用者已經換頁
    app.innerHTML = html;
    window.scrollTo(0, samePage ? y : 0);
    lastPath = path;
  } catch (err) {
    console.error(err);
    if (samePage) { toast(err.message || String(err)); return; }
    app.innerHTML = `<div class="phone"><div class="main"><div class="state" role="alert">
      <p class="strong">${escText(t('common.error'))}</p><p class="small">${escText(err.message || String(err))}</p>
      <button type="button" class="btn btn--primary" data-action="retry">${escText(t('common.retry'))}</button></div></div></div>`;
    lastPath = path;
  } finally {
    clearTimeout(loadingTimer);
  }
}
actions.retry = () => render();

export const rerender = () => render();

let toastTimer;
export function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('is-shown');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('is-shown'), 2400);
}

export function openModal(html) {
  settleConfirm(false);
  document.getElementById('modal-root').innerHTML = `<div class="modal-backdrop" data-action="modal-backdrop">${html}</div>`;
}
export function closeModal() {
  settleConfirm(false);
  document.getElementById('modal-root').innerHTML = '';
}

// 網頁內的確認框（取代瀏覽器的 confirm()，上架環境會擋掉那個）。回傳 Promise<boolean>
let pendingConfirm = null;
function settleConfirm(value) {
  const resolve = pendingConfirm;
  pendingConfirm = null;
  if (resolve) resolve(value);
}
const escText = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export function confirmDialog(message, { danger = false } = {}) {
  openModal(`<div class="dialog dialog--sm" role="alertdialog" aria-modal="true" aria-label="${escText(message)}">
    <p>${escText(message)}</p>
    <div class="dialog__foot"><span class="grow"></span>
      <button type="button" class="btn btn--sm" data-action="confirm-no">${escText(t('common.cancel'))}</button>
      <button type="button" class="btn btn--sm ${danger ? 'btn--danger-fill' : 'btn--primary'}" data-action="confirm-yes">${escText(t('common.confirm'))}</button>
    </div>
  </div>`);
  document.querySelector('[data-action=confirm-yes]')?.focus();
  return new Promise((resolve) => { pendingConfirm = resolve; });
}
actions['confirm-yes'] = () => { const r = pendingConfirm; pendingConfirm = null; closeModal(); r?.(true); };
actions['confirm-no'] = () => closeModal();
actions['modal-backdrop'] = (_, el, ev) => { if (ev.target === el) closeModal(); };
actions['modal-close'] = () => closeModal();

export function startEvents() {
  document.addEventListener('click', async (ev) => {
    const el = ev.target.closest('[data-action]');
    if (!el || el.disabled) return;
    // 對話框裡沒有 data-action 的按鈕（例如表單送出）會一路冒泡到遮罩，不能攔下來
    if (el.dataset.action === 'modal-backdrop' && ev.target !== el) return;
    const fn = actions[el.dataset.action];
    if (!fn) return;
    ev.preventDefault();
    try { await fn(el.dataset, el, ev); } catch (err) { console.error(err); toast(err.message || String(err)); }
  });
  document.addEventListener('submit', async (ev) => {
    const form = ev.target.closest('form[data-form]');
    if (!form) return;
    ev.preventDefault();
    const fn = forms[form.dataset.form];
    if (!fn) return;
    const btn = form.querySelector('[type=submit]');
    if (btn) btn.disabled = true;
    try { await fn(new FormData(form), form); } catch (err) { console.error(err); toast(err.message || String(err)); }
    finally { if (btn && btn.isConnected) btn.disabled = false; }
  });
  document.addEventListener('input', (ev) => {
    const el = ev.target.closest('[data-input]');
    if (el && inputs[el.dataset.input]) inputs[el.dataset.input](el);
  });
  window.addEventListener('hashchange', render);
}
