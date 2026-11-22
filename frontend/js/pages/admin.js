// 店家端與平台管理畫面 A01–A06（紫色取餐券版；桌機／平板優先）
import { api, USE_MOCK } from '../api.js';
import { t, getLang } from '../i18n.js';
import { actions, forms, inputs, rerender, poll, toast, openModal, closeModal, confirmDialog } from '../router.js';
import { icon } from '../icons.js';
import * as C from '../components.js';

const { esc, money, unit } = C;

async function layout(active, inner) {
  const me = await api.me();
  const items = me.role === 'admin'
    ? [['platform', 'admin.nav.platform']]
    : [['orders', 'admin.nav.orders'], ['menu', 'admin.nav.menu'], ['settings', 'admin.nav.settings'], ['reports', 'admin.nav.reports']];
  return `<div class="admin">
    <header class="admin-bar">
      <div class="admin-bar__brand"><span class="wordmark">${esc(t('app.name'))}</span>${me.role === 'staff' && me.store_name ? `<span class="store">${esc(me.store_name)}</span>` : ''}</div>
      <nav class="admin-nav" aria-label="${esc(t('profile.dashboard'))}">${items.map(([k, key]) => `<a href="#admin-${k}"${k === active ? ' aria-current="page"' : ''}>${esc(t(key))}</a>`).join('')}</nav>
      <div class="admin-bar__me"><span class="who">${esc(me.name)}</span>${C.LangSwitch()}${me.role === 'staff' ? `<button type="button" class="barlink" data-action="tour-replay">${esc(t('tour.replay_short'))}</button>` : ''}${me.role === 'admin' ? `<a class="barlink" href="#password">${esc(t('password.change_short'))}</a>` : ''}<button type="button" class="barlink" data-action="logout">${esc(t('profile.logout'))}</button></div>
    </header>
    <main class="admin-main">${inner}</main>
  </div>`;
}
function pageHeader(title, sub = '', right = '') {
  return `<div class="page-head"><div><h1>${esc(title)}</h1>${sub ? `<p class="page-head__sub">${esc(sub)}</p>` : ''}</div>${right ? `<div class="page-head__right">${right}</div>` : ''}</div>`;
}

// ======================= A01 接單看板（像 Notion 的看板） =======================
// 四欄：未付款・到店付款 → 已付款・待接單 → 已接單・製作中 → 可取餐。
// 卡片可以拖到下一欄（接單、做好了），也可以按卡片上的按鈕；取餐、拒單只能按按鈕
let seenOrderIds = null;
let dragging = null; // 拖曳中的卡片 { id, col, no }；拖曳時不要定時重畫
export async function adminBoard() {
  const [r, orders] = await Promise.all([api.admin.getRestaurant(), api.admin.listOrders()]);
  const fresh = new Set(seenOrderIds ? orders.filter((o) => !seenOrderIds.has(o.id)).map((o) => o.id) : []);
  if (fresh.size) toast(t('admin.new_order_toast', { n: fresh.size }));
  seenOrderIds = new Set(orders.map((o) => o.id));
  poll(() => { if (!dragging) rerender(); }, 4000);

  const accepting = r.is_accepting_orders;
  const right = `<label class="accepting${accepting ? '' : ' is-paused'}"><span>${esc(t(accepting ? 'admin.accepting' : 'admin.paused'))}</span>${C.Toggle({ on: accepting, action: 'toggle-accepting', label: t('admin.accepting') })}</label>`;
  return layout('orders', `
    ${pageHeader(t('admin.nav.orders'), `${t('admin.board_sub', { n: r.today_order_count ?? 0 })} · ${t('admin.board_hint')}`, right)}
    <div class="rails board">${C.BOARD_COLUMNS.map((k) => {
      const list = orders.filter((o) => C.boardColumn(o.status) === k);
      return `<section class="rail rail--${k}" data-col="${k}" aria-label="${esc(t('admin.col.' + k))}">
        <div class="rail__head"><h2 class="rail__tag"><i aria-hidden="true"></i>${esc(t('admin.col.' + k))}</h2><span class="cnt">${list.length}</span></div>
        ${list.map((o) => C.KitchenTicket(o, fresh.has(o.id))).join('') || `<p class="rail__empty">${esc(t('admin.col_empty'))}</p>`}
      </section>`;
    }).join('')}</div>`);
}
async function changeStatus(d) {
  if (d.to === 'recall') { toast(t('admin.called', { no: d.no })); return; }
  if (d.to === 'cancelled' && !(await confirmDialog(t('admin.reject_confirm', { no: d.no }), { danger: true }))) return;
  await api.admin.updateOrderStatus(d.id, d.to);
  if (d.to === 'ready') toast(t('admin.notified', { no: d.no }));
  rerender();
}
actions['order-status'] = (d) => changeStatus(d);
actions['toggle-accepting'] = async () => {
  const r = await api.admin.getRestaurant();
  await api.admin.updateRestaurant({ is_accepting_orders: !r.is_accepting_orders });
  rerender();
};

// 拖曳：只有 C.BOARD_MOVES 允許的欄位會亮起來、可以放
const dropTarget = (ev) => {
  const rail = ev.target.closest?.('.board .rail');
  return rail && dragging && C.BOARD_MOVES[dragging.col]?.[rail.dataset.col] ? rail : null;
};
const clearDrop = () => document.querySelectorAll('.board .rail.is-drop, .board .rail.can-drop').forEach((el) => el.classList.remove('is-drop', 'can-drop'));
document.addEventListener('dragstart', (ev) => {
  const card = ev.target.closest?.('.board [data-drag-id]');
  if (!card) return;
  dragging = { id: card.dataset.dragId, col: card.dataset.col, no: card.dataset.no };
  ev.dataTransfer.effectAllowed = 'move';
  ev.dataTransfer.setData('text/plain', card.dataset.no);
  card.classList.add('is-dragging');
  for (const col of Object.keys(C.BOARD_MOVES[dragging.col] ?? {})) document.querySelector(`.board .rail[data-col="${col}"]`)?.classList.add('can-drop');
});
document.addEventListener('dragover', (ev) => {
  const rail = dropTarget(ev);
  if (!rail) return;
  ev.preventDefault();
  ev.dataTransfer.dropEffect = 'move';
  if (!rail.classList.contains('is-drop')) { clearDrop(); rail.classList.add('is-drop', 'can-drop'); }
});
document.addEventListener('drop', async (ev) => {
  const rail = dropTarget(ev);
  const d = dragging;
  if (!rail || !d) return;
  ev.preventDefault();
  dragging = null;
  clearDrop();
  try {
    await changeStatus({ id: d.id, no: d.no, to: C.BOARD_MOVES[d.col][rail.dataset.col] });
  } catch (err) {
    toast(err.message || String(err));
    rerender();
  }
});
document.addEventListener('dragend', (ev) => {
  ev.target.closest?.('[data-drag-id]')?.classList.remove('is-dragging');
  dragging = null;
  clearDrop();
});

// ======================= A02 菜單管理 / A03 品項編輯 =======================
// 每一列一個「供應中」開關：關掉後顧客看得到但不能點（顯示售完）
const menuState = { cat: 'all', data: null };
const availableNow = (i) => i.is_available && !i.is_sold_out;
// 兩種語言的欄位標籤：「品名（中文）」「品名（英文）」
const inLang = (key, lang) => t(key) + t('fmt.paren', { x: t('field.' + lang) });

export async function adminMenu() {
  const data = await api.admin.listMenuItems();
  menuState.data = data;
  if (menuState.cat !== 'all' && !data.categories.some((c) => c.id === menuState.cat)) menuState.cat = 'all';
  const items = menuState.cat === 'all' ? data.items : data.items.filter((i) => i.category_id === menuState.cat);
  const soldOut = data.items.filter((i) => !availableNow(i)).length;
  const tabs = [{ id: 'all', name: t('home.loc_all') }, ...data.categories];
  const L = (k) => esc(t(k));
  const rows = items.map((i) => `<tr>
      <td data-label="${L('admin.menu.col_item')}"><span class="cell-media">${C.Photo({ url: i.image_url, kind: 'mini' })}<span>${esc(i.name)}</span></span></td>
      <td data-label="${L('admin.menu.col_category')}" class="mute">${esc(i.category_name)}</td>
      <td data-label="${L('admin.menu.col_price')}" class="num">${unit(i.price)}</td>
      <td data-label="${L('admin.menu.col_prep')}" class="num">${esc(t('unit.minutes', { n: i.prep_minutes }))}</td>
      <td data-label="${L('admin.menu.col_available')}">${C.Toggle({ on: availableNow(i), action: 'menu-toggle', data: { id: i.id }, label: `${i.name} ${t('admin.menu.col_available')}` })}</td>
      <td class="act">${C.Button({ label: t('common.edit'), size: 'sm', action: 'menu-edit', data: { id: i.id } })}</td>
    </tr>`).join('');
  return layout('menu', `
    ${pageHeader(t('admin.nav.menu'), t('admin.menu.sub', { n: data.items.length, s: soldOut }), C.Button({ label: t('admin.menu.new'), style: 'primary', size: 'sm', action: 'menu-new' }))}
    ${data.categories.length > 1 ? C.Tabs(tabs.map((c) => ({ name: c.name, selected: c.id === menuState.cat, action: 'admin-menu-cat', data: { cat: c.id } })), { label: t('admin.menu.col_category') }) : ''}
    ${items.length ? `<div class="table-wrap"><table class="data data--stack">
      <thead><tr><th scope="col">${L('admin.menu.col_item')}</th><th scope="col">${L('admin.menu.col_category')}</th><th scope="col" class="num">${L('admin.menu.col_price')}</th><th scope="col" class="num">${L('admin.menu.col_prep')}</th><th scope="col">${L('admin.menu.col_available')}</th><th scope="col" class="act"><span class="visually-hidden">${L('admin.menu.col_actions')}</span></th></tr></thead>
      <tbody>${rows}</tbody></table></div>`
      : `<div class="state"><p>${esc(t('menu.empty'))}</p>${C.Button({ label: t('admin.menu.new'), style: 'primary', size: 'sm', action: 'menu-new' })}</div>`}`);
}
actions['admin-menu-cat'] = (d) => { menuState.cat = d.cat; rerender(); };
actions['menu-toggle'] = async (d) => {
  const item = menuState.data.items.find((i) => i.id === d.id);
  await api.admin.patchMenuItem(d.id, { is_available: !availableNow(item) });
  rerender();
};

function menuDialog(item) {
  const cats = menuState.data.categories;
  const isNew = !item;
  const blank = { zh: '', en: '' };
  const cat = cats.find((c) => c.id === menuState.cat) ?? cats[0];
  const i = item ?? { id: '', price: '', prep_minutes: '', is_available: true, is_sold_out: false, option_groups: [], image_url: null,
    edit: { name: blank, description: blank, category: cat ? { zh: cat.zh, en: cat.en } : blank, option_groups: [] } };
  const e = i.edit;
  const title = t(isNew ? 'admin.menu.new_title' : 'admin.menu.edit_title');
  // 分類可以選現有的，也可以打新的；選了現有的中文名稱會自動帶出英文
  const list = (id, lang) => `<datalist id="${id}">${cats.map((c) => `<option value="${esc(c[lang])}"></option>`).join('')}</datalist>`;
  return `<form class="dialog dialog--wide" data-form="menu-item" role="dialog" aria-modal="true" aria-label="${esc(title)}" novalidate>
    <input type="hidden" name="id" value="${esc(i.id)}">
    <div class="dialog__head"><h2>${esc(title)}</h2><button type="button" class="icon-btn" data-action="modal-close" aria-label="${esc(t('common.close'))}">${icon('x')}</button></div>
    <div class="field-pair">
      ${C.TextField({ label: inLang('admin.menu.f_name', 'zh'), name: 'name_zh', value: e.name.zh, required: true, extra: 'maxlength="100"' })}
      ${C.TextField({ label: inLang('admin.menu.f_name', 'en'), name: 'name_en', value: e.name.en, required: true, extra: 'maxlength="100"' })}
    </div>
    <div class="field-pair">
      ${C.TextField({ label: inLang('admin.menu.col_category', 'zh'), name: 'category_zh', value: e.category.zh, required: true, input: 'category-zh', extra: 'maxlength="100" list="cats-zh" autocomplete="off"' })}
      ${C.TextField({ label: inLang('admin.menu.col_category', 'en'), name: 'category_en', value: e.category.en, required: true, extra: 'maxlength="100" list="cats-en" autocomplete="off"' })}
    </div>
    ${list('cats-zh', 'zh')}${list('cats-en', 'en')}
    <div class="field-pair">
      ${C.TextField({ label: t('admin.menu.f_price'), name: 'price', type: 'number', value: i.price, required: true, extra: 'min="0" max="100000" step="1" inputmode="numeric"' })}
      ${C.TextField({ label: t('admin.menu.f_prep'), name: 'prep_minutes', type: 'number', value: i.prep_minutes, required: true, extra: 'min="0" max="180" step="1" inputmode="numeric"' })}
    </div>
    ${C.TextField({ label: inLang('admin.menu.f_desc', 'zh'), name: 'description_zh', value: e.description.zh, textarea: true, extra: 'maxlength="1000"' })}
    ${C.TextField({ label: inLang('admin.menu.f_desc', 'en'), name: 'description_en', value: e.description.en, textarea: true, extra: 'maxlength="1000"' })}
    ${C.PhotoField({ name: 'image_url', label: t('admin.menu.f_photo'), url: i.image_url, kind: 'hero' })}
    ${addOnEditor(e.option_groups ?? [])}
    <div class="switch-rows">
      <label class="switch-row"><span>${esc(t('admin.menu.f_available'))}</span><input type="checkbox" class="switch" name="is_available"${availableNow(i) ? ' checked' : ''}></label>
    </div>
    <div class="dialog__foot">
      ${isNew ? '' : C.Button({ label: t('admin.menu.delete'), style: 'danger', size: 'sm', action: 'menu-delete', data: { id: i.id } })}
      <span class="grow"></span>
      ${C.Button({ label: t('common.cancel'), style: 'text', size: 'sm', action: 'modal-close' })}
      ${C.Button({ label: t('common.save'), style: 'primary', size: 'sm', type: 'submit' })}
    </div>
  </form>`;
}
inputs['category-zh'] = (el) => {
  const cat = menuState.data?.categories.find((c) => c.zh === el.value.trim());
  const other = el.form?.querySelector('[name=category_en]');
  if (cat && other && !other.value.trim()) other.value = cat.en;
};
actions['menu-new'] = () => { openModal(menuDialog(null)); document.getElementById('f-name_zh')?.focus(); };
actions['menu-edit'] = (d) => { openModal(menuDialog(menuState.data.items.find((i) => i.id === d.id))); document.getElementById('f-name_zh')?.focus(); };
actions['menu-delete'] = async (d) => {
  if (!(await confirmDialog(t('admin.menu.delete_confirm'), { danger: true }))) return;
  await api.admin.deleteMenuItem(d.id);
  closeModal();
  toast(t('admin.menu.deleted'));
  rerender();
};
const pair = (fd, name) => ({ zh: String(fd.get(`${name}_zh`) || '').trim(), en: String(fd.get(`${name}_en`) || '').trim() });
function invalid(form) {
  // 空白也算沒填
  form.querySelectorAll('[required]').forEach((el) => el.setCustomValidity(el.value.trim() ? '' : t('form.required')));
  if (form.checkValidity()) return false;
  form.reportValidity();
  form.querySelector(':invalid')?.focus();
  return true;
}
forms['menu-item'] = async (fd, form) => {
  if (invalid(form)) return;
  const option_groups = readAddOns(form);
  if (option_groups.some((g) => !g.choices.length)) { toast(t('admin.og.need_choice')); return; }
  await api.admin.saveMenuItem({
    option_groups,
    id: fd.get('id') || undefined,
    name: pair(fd, 'name'),
    category: pair(fd, 'category'),
    description: pair(fd, 'description'),
    price: Number(fd.get('price')),
    prep_minutes: Number(fd.get('prep_minutes')),
    is_available: fd.get('is_available') === 'on',
    image_url: fd.get('image_url') || null,
  });
  closeModal();
  toast(t('common.saved'));
  rerender();
};

// ---------- 加點選項編輯（菜單品項視窗裡） ----------
// 每個群組：名稱（中英）、怎麼選（必選一項／可不選、最多 N 項）、選項（名稱中英＋加價）。
// 欄位沒有 name，送出時照畫面順序讀（readAddOns）；原本的群組、選項編號保留，新的自動產生
const newId = (prefix) => prefix + Math.random().toString(36).slice(2, 8);
const ogInput = (cls, value, label, extra = '') => `<span class="input input--sm"><input class="${cls}" value="${esc(value)}" aria-label="${esc(label)}" ${extra}></span>`;

function choiceRow(c) {
  return `<li class="og-choice" data-cid="${esc(c.id)}">
    ${ogInput('oc-zh', c.label.zh, inLang('admin.og.choice', 'zh'), 'required maxlength="100"')}
    ${ogInput('oc-en', c.label.en, inLang('admin.og.choice', 'en'), 'required maxlength="100"')}
    ${ogInput('oc-price', c.price_delta ?? 0, t('admin.og.price'), 'type="number" min="0" max="10000" step="1" inputmode="numeric"')}
    <button type="button" class="icon-btn" data-action="og-remove-choice" aria-label="${esc(t('admin.og.remove_choice'))}">${icon('x')}</button>
  </li>`;
}

function groupBlock(g) {
  const multi = !g.required;
  return `<div class="og" data-gid="${esc(g.id)}">
    <div class="og__head">
      ${ogInput('og-zh', g.name.zh, inLang('admin.og.name', 'zh'), `required maxlength="100" placeholder="${esc(inLang('admin.og.name', 'zh'))}"`)}
      ${ogInput('og-en', g.name.en, inLang('admin.og.name', 'en'), `required maxlength="100" placeholder="${esc(inLang('admin.og.name', 'en'))}"`)}
      <button type="button" class="icon-btn" data-action="og-remove-group" aria-label="${esc(t('admin.og.remove_group'))}">${icon('x')}</button>
    </div>
    <div class="og__rule">
      <select class="og-rule" data-input="og-rule" aria-label="${esc(t('admin.og.rule'))}">
        <option value="one"${multi ? '' : ' selected'}>${esc(t('admin.og.rule_one'))}</option>
        <option value="multi"${multi ? ' selected' : ''}>${esc(t('admin.og.rule_multi'))}</option>
      </select>
      <span class="og__max"${multi ? '' : ' hidden'}>${ogInput('og-max', g.max_select ?? 1, t('admin.og.max'), 'type="number" min="1" max="20" step="1" inputmode="numeric"')}</span>
    </div>
    <div class="og__cols" aria-hidden="true"><span>${esc(inLang('admin.og.choice', 'zh'))}</span><span>${esc(inLang('admin.og.choice', 'en'))}</span><span>${esc(t('admin.og.price'))}</span></div>
    <ul class="og__choices">${g.choices.map(choiceRow).join('')}</ul>
    <button type="button" class="lnk" data-action="og-add-choice">＋ ${esc(t('admin.og.add_choice'))}</button>
  </div>`;
}

function addOnEditor(groups) {
  return `<fieldset class="og-editor">
    <legend class="field__label">${esc(t('admin.og.title'))}</legend>
    <p class="hint">${esc(t('admin.og.hint'))}</p>
    <div class="og-list">${groups.map(groupBlock).join('')}</div>
    <button type="button" class="btn btn--sm" data-action="og-add-group">＋ ${esc(t('admin.og.add_group'))}</button>
  </fieldset>`;
}

const blankChoice = () => ({ id: newId('c'), label: { zh: '', en: '' }, price_delta: 0 });
actions['og-add-group'] = (_, el) => {
  const list = el.closest('.og-editor').querySelector('.og-list');
  list.insertAdjacentHTML('beforeend', groupBlock({ id: newId('g'), name: { zh: '', en: '' }, required: true, max_select: 1, choices: [blankChoice()] }));
  list.lastElementChild.querySelector('.og-zh').focus();
};
actions['og-remove-group'] = (_, el) => el.closest('.og').remove();
actions['og-add-choice'] = (_, el) => {
  const ul = el.closest('.og').querySelector('.og__choices');
  ul.insertAdjacentHTML('beforeend', choiceRow(blankChoice()));
  ul.lastElementChild.querySelector('.oc-zh').focus();
};
actions['og-remove-choice'] = (_, el) => el.closest('.og-choice').remove();
inputs['og-rule'] = (el) => { el.closest('.og').querySelector('.og__max').hidden = el.value !== 'multi'; };

function readAddOns(form) {
  const val = (root, sel) => root.querySelector(sel).value.trim();
  return [...form.querySelectorAll('.og')].map((g) => {
    const required = g.querySelector('.og-rule').value === 'one';
    const choices = [...g.querySelectorAll('.og-choice')].map((c) => ({
      id: c.dataset.cid, label: { zh: val(c, '.oc-zh'), en: val(c, '.oc-en') },
      price_delta: Math.max(0, Math.round(Number(c.querySelector('.oc-price').value) || 0)),
    }));
    const max = Math.round(Number(g.querySelector('.og-max').value) || 1);
    return {
      id: g.dataset.gid, name: { zh: val(g, '.og-zh'), en: val(g, '.og-en') }, required,
      max_select: required ? 1 : Math.max(1, Math.min(max, choices.length || 1)), choices,
    };
  });
}

// ======================= A04 店家設定 =======================
const AREAS = [['fengyun', 'home.loc_fengyun'], ['shuimu', 'home.loc_shuimu'], ['snack', 'home.loc_snack'], ['other', 'area.other']];
const areaSelect = (value, name = 'area') => `<div class="field"><label for="f-${name}">${esc(t('admin.settings.f_area'))}</label>
  <select id="f-${name}" name="${name}">${AREAS.map(([k, key]) => `<option value="${k}"${k === value ? ' selected' : ''}>${esc(t(key))}</option>`).join('')}</select></div>`;
// 一組中英文欄位，並排
const langPair = (key, name, value, opts = {}) => `<div class="field-pair">
  ${C.TextField({ label: inLang(key, 'zh'), name: `${name}_zh`, value: value?.zh ?? '', ...opts })}
  ${C.TextField({ label: inLang(key, 'en'), name: `${name}_en`, value: value?.en ?? '', ...opts })}
</div>`;

// 店家的登入帳號：帳號第一次登入時選好就不能改，密碼可以在這裡改（假資料模式沒有）
const accountPanel = (me) => (USE_MOCK ? '' : `<section class="panel">
  <h2>${esc(t('admin.settings.account'))}</h2>
  <dl class="account-id"><dt>${esc(t('admin.settings.login_id'))}</dt><dd class="num">${esc(me.student_id)}</dd></dl>
  <p class="hint">${esc(t('admin.settings.login_id_fixed'))}</p>
  <div><a class="btn btn--sm" href="#password">${esc(t('password.change'))}</a></div>
</section>`);

export async function adminSettings() {
  const [r, me] = await Promise.all([api.admin.getRestaurant(), api.me()]);
  const e = r.edit;
  return layout('settings', `<form class="settings-form" data-form="settings" novalidate>
    ${pageHeader(t('admin.nav.settings'), '', C.Button({ label: t('common.save'), style: 'primary', size: 'sm', type: 'submit' }))}
    <div class="settings">
      <div class="settings__col">
      <section class="panel">
        <h2>${esc(t('admin.settings.profile'))}</h2>
        ${langPair('admin.settings.f_name', 'name', e.name, { required: true, extra: 'maxlength="100" autocomplete="off"' })}
        ${areaSelect(e.area)}
        ${langPair('admin.settings.f_location', 'location', e.location, { extra: 'maxlength="100"' })}
        ${langPair('admin.settings.hours', 'opening_hours', e.opening_hours, { extra: 'maxlength="100"' })}
        ${C.TextField({ label: inLang('admin.settings.f_desc', 'zh'), name: 'description_zh', value: e.description.zh, textarea: true })}
        ${C.TextField({ label: inLang('admin.settings.f_desc', 'en'), name: 'description_en', value: e.description.en, textarea: true })}
      </section>
      </div>
      <div class="settings__col">
        <section class="panel">
          <h2>${esc(t('admin.settings.photos'))}</h2>
          ${C.PhotoField({ name: 'cover_image_url', label: t('admin.settings.cover'), url: r.cover_image_url, kind: 'cover' })}
          ${C.PhotoField({ name: 'image_url', label: t('admin.settings.thumb'), url: r.image_url, kind: 'thumb' })}
        </section>
        <section class="panel">
          <h2>${esc(t('admin.settings.orders'))}</h2>
          <div class="switch-rows">
            <label class="switch-row"><span>${esc(t('admin.settings.accept_online'))}</span><input type="checkbox" class="switch" name="is_accepting_orders"${r.is_accepting_orders ? ' checked' : ''}></label>
          </div>
        </section>
        ${accountPanel(me)}
      </div>
    </div>
  </form>`);
}
forms.settings = async (fd, form) => {
  if (invalid(form)) return;
  await api.admin.updateRestaurant({
    name: pair(fd, 'name'), location: pair(fd, 'location'), opening_hours: pair(fd, 'opening_hours'),
    description: pair(fd, 'description'), area: fd.get('area'),
    is_accepting_orders: fd.get('is_accepting_orders') === 'on',
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
  // 算不出來的數字（例如沒有前一段的訂單可比）顯示「—」，比較那一行留空
  const vsPct = (d) => (d == null ? '' : `${vs} ${sign(d)}%`);
  const ranges = [['today', 'reports.today'], ['week', 'reports.week'], ['month', 'reports.month']];
  const vs = t('reports.vs_' + reportState.range);
  const fig = (label, value, delta) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd><dd class="delta">${esc(delta)}</dd></div>`;
  const seg = `<div class="tog tog--light" role="group" aria-label="${esc(t('admin.nav.reports'))}">${ranges.map(([k, key]) => `<button type="button" data-action="report-range" data-range="${k}" aria-pressed="${k === reportState.range}">${esc(t(key))}</button>`).join('')}</div>`;
  return layout('reports', `
    ${pageHeader(t('admin.nav.reports'), '', seg)}
    <dl class="figures">
      ${fig(t('reports.orders'), s.order_count.toLocaleString('en-US'), vsPct(s.delta_orders))}
      ${fig(t('reports.revenue'), money(s.revenue), vsPct(s.delta_revenue))}
      ${fig(t('reports.avg_wait'), s.avg_wait_minutes == null ? '—' : t('unit.minutes', { n: s.avg_wait_minutes }), s.delta_wait == null ? '' : `${vs} ${t('unit.minutes', { n: sign(s.delta_wait) })}`)}
      ${fig(t('reports.cancel_rate'), `${s.cancel_rate}%`, vsPct(s.delta_cancel))}
    </dl>
    <div class="reports-row">
      <section class="panel"><h2>${esc(t('reports.chart_title'))}</h2>${barChart(orders_by_slot)}</section>
      <section class="panel"><h2>${esc(t('reports.top_items'))}</h2>
        <table class="data"><thead><tr><th scope="col" class="num">#</th><th scope="col">${esc(t('admin.menu.col_item'))}</th><th scope="col" class="num">${esc(t('cart.qty'))}</th><th scope="col" class="num">${esc(t('reports.revenue'))}</th></tr></thead>
        <tbody>${top_items.map((x, k) => `<tr><td class="num">${k + 1}</td><td>${esc(x.name)}</td><td class="num">${esc(x.qty)}</td><td class="num">${money(x.revenue)}</td></tr>`).join('') || `<tr><td colspan="4" class="mute">${esc(t('reports.none'))}</td></tr>`}</tbody></table>
      </section>
    </div>`);
}
actions['report-range'] = (d) => { reportState.range = d.range; rerender(); };

// ======================= A06 平台管理 =======================
// 真後端：列出所有店家、登入帳號與今日訂單，可以開新店（店家資料＋登入帳號一起建立）。
// 管理員只看不改店家，所以沒有停權按鈕；假資料模式才有停權／核准的示範。
export async function adminPlatform() {
  const { stats, restaurants } = await api.platform.overview();
  const L = (k) => esc(t(k));
  const moderate = !!api.platform.setRestaurantStatus;
  const rows = restaurants.map((r) => {
    const [key, cls] = r.status === 'active' && r.is_accepting_orders === false ? ['restaurant.paused', 'chip--off'] : C.restaurantStatus(r);
    const act = r.status === 'pending' ? ['admin.platform.approve', 'active', 'primary'] : r.status === 'suspended' ? ['admin.platform.restore', 'active', 'secondary'] : ['admin.platform.suspend', 'suspended', 'danger'];
    return `<tr>
      <td data-label="${L('admin.platform.col_name')}"><span class="cell-media">${C.Photo({ url: r.image_url, kind: 'mini' })}<span>${esc(r.name)}</span></span></td>
      <td data-label="${L('admin.settings.f_location')}" class="mute">${esc(r.location)}</td>
      <td data-label="${L('admin.platform.col_account')}">${esc(r.owner_account || '—')}</td>
      <td data-label="${L('admin.platform.col_status')}"><span class="chip ${cls}">${esc(t(key))}</span></td>
      <td data-label="${L('admin.platform.col_orders')}" class="num">${r.status === 'pending' ? '' : esc(r.today_order_count)}</td>
      ${moderate ? `<td class="act">${C.Button({ label: t(act[0]), style: act[2], size: 'sm', action: 'restaurant-status', data: { id: r.id, to: act[1] } })}</td>` : ''}
    </tr>`;
  }).join('');
  const sub = (text) => (text ? `<dd class="delta">${esc(text)}</dd>` : '');
  const create = api.platform.createVendor ? C.Button({ label: t('admin.platform.new'), style: 'primary', size: 'sm', action: 'vendor-new' }) : '';
  return layout('platform', `
    ${pageHeader(t('admin.platform.title'), '', create)}
    <dl class="figures">
      <div><dt>${L('admin.platform.restaurants')}</dt><dd>${esc(t('admin.platform.count', { n: stats.restaurant_count }))}</dd>${sub(stats.pending_count != null ? t('admin.platform.pending_n', { n: stats.pending_count }) : t('admin.platform.accepting_n', { n: stats.accepting_count }))}</div>
      <div><dt>${L('admin.platform.orders_today')}</dt><dd>${esc(stats.orders_today.toLocaleString('en-US'))}</dd>${sub(stats.delta_orders != null ? `${t('reports.vs_today')} +${stats.delta_orders}%` : '')}</div>
      <div><dt>${L(moderate ? 'admin.platform.users' : 'admin.platform.customers')}</dt><dd>${esc(stats.users.toLocaleString('en-US'))}</dd>${sub(stats.new_users_week != null ? t('admin.platform.new_users', { n: stats.new_users_week }) : '')}</div>
    </dl>
    <div class="table-wrap"><table class="data data--stack">
      <thead><tr><th scope="col">${L('admin.platform.col_name')}</th><th scope="col">${L('admin.settings.f_location')}</th><th scope="col">${L('admin.platform.col_account')}</th><th scope="col">${L('admin.platform.col_status')}</th><th scope="col" class="num">${L('admin.platform.col_orders')}</th>${moderate ? `<th scope="col" class="act"><span class="visually-hidden">${L('admin.menu.col_actions')}</span></th>` : ''}</tr></thead>
      <tbody>${rows}</tbody></table></div>`);
}
actions['restaurant-status'] = async (d) => {
  if (d.to === 'suspended' && !(await confirmDialog(t('admin.platform.suspend_confirm'), { danger: true }))) return;
  await api.platform.setRestaurantStatus(d.id, d.to);
  rerender();
};

// 新增店家：店家資料＋給店家用的登入帳號（第一次登入要換密碼）
function vendorDialog() {
  const title = t('admin.platform.new_title');
  return `<form class="dialog" data-form="vendor-new" role="dialog" aria-modal="true" aria-label="${esc(title)}" novalidate>
    <div class="dialog__head"><h2>${esc(title)}</h2><button type="button" class="icon-btn" data-action="modal-close" aria-label="${esc(t('common.close'))}">${icon('x')}</button></div>
    <h3 class="dialog__sub">${esc(t('admin.platform.store'))}</h3>
    ${langPair('admin.settings.f_name', 'name', null, { required: true, extra: 'maxlength="100" autocomplete="off"' })}
    ${areaSelect('fengyun')}
    ${langPair('admin.settings.f_location', 'location', null, { extra: 'maxlength="100"' })}
    <h3 class="dialog__sub">${esc(t('admin.platform.login'))}</h3>
    <p class="hint">${esc(t('admin.platform.login_hint'))}</p>
    <div class="field-pair">
      ${C.TextField({ label: t('admin.platform.f_account'), name: 'student_id', required: true, num: true, extra: 'maxlength="20" pattern="[A-Za-z0-9]{4,20}" autocomplete="off" autocapitalize="off" spellcheck="false"', hint: `<p class="hint">${esc(t('admin.platform.account_rule'))}</p>` })}
      ${C.TextField({ label: t('admin.platform.f_password'), name: 'password', required: true, extra: 'minlength="8" maxlength="128" autocomplete="new-password"' })}
    </div>
    <div class="field-pair">
      ${C.TextField({ label: t('register.email'), name: 'email', type: 'email', required: true, extra: 'autocomplete="off"' })}
      ${C.TextField({ label: t('register.phone'), name: 'phone_number', type: 'tel', required: true, num: true, extra: 'pattern="\\+?[0-9]{8,15}" inputmode="tel" autocomplete="off"' })}
    </div>
    <div class="dialog__foot">
      <span class="grow"></span>
      ${C.Button({ label: t('common.cancel'), style: 'text', size: 'sm', action: 'modal-close' })}
      ${C.Button({ label: t('admin.platform.create'), style: 'primary', size: 'sm', type: 'submit' })}
    </div>
  </form>`;
}
actions['vendor-new'] = () => { openModal(vendorDialog()); document.getElementById('f-name_zh')?.focus(); };
forms['vendor-new'] = async (fd, form) => {
  if (invalid(form)) return;
  const name = pair(fd, 'name');
  const location = pair(fd, 'location');
  const staff = Object.fromEntries(['student_id', 'password', 'email', 'phone_number'].map((k) => [k, String(fd.get(k) || '').trim()]));
  await api.platform.createVendor({
    vendor: { name_zh: name.zh, name_en: name.en, area: fd.get('area'), location_zh: location.zh, location_en: location.en },
    staff,
  });
  closeModal();
  toast(t('admin.platform.created', { name: getLang() === 'en' ? name.en : name.zh, id: staff.student_id }));
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
