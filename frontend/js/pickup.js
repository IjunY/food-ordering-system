// 預約取餐的時段規則（和後端 app/orders/pickup.py 一樣，後端會再檢查一次）：
// 每 15 分鐘一個時段（12:00、12:15…），最早是現在起 30 分鐘後，最晚 24 小時內。
// 店家設了「可預約時段」（pickup_hours，例如 [{open: '11:00', close: '13:30'}]，每天一樣、台灣時間）
// 就只能選這些時段裡的時間，頭尾都可以選；沒設就全天都可以
export const SLOT_MINUTES = 15;
export const MIN_LEAD_MINUTES = 30;
export const MAX_AHEAD_HOURS = 24;

const STEP = SLOT_MINUTES * 60000;
const LEAD = MIN_LEAD_MINUTES * 60000;
const AHEAD = MAX_AHEAD_HOURS * 3600000;
const TAIWAN = 8 * 3600000;

const toMinutes = (hhmm) => { const [h, m] = hhmm.split(':').map(Number); return h * 60 + m; };

// 這個時間（UTC 毫秒）在不在店家的可預約時段裡
export function withinHours(at, hours = []) {
  if (!hours.length) return true;
  const local = new Date(at + TAIWAN);
  const min = local.getUTCHours() * 60 + local.getUTCMinutes();
  return hours.some((p) => toMinutes(p.open) <= min && min <= toMinutes(p.close));
}

// 現在可以選的所有時段（ISO 字串，由早到晚）。台灣是整點時區，所以用 UTC 毫秒對齊 15 分鐘就好
export function pickupSlots(now = Date.now(), hours = []) {
  const slots = [];
  for (let at = Math.ceil((now + LEAD) / STEP) * STEP; at <= now + AHEAD; at += STEP) {
    if (withinHours(at, hours)) slots.push(new Date(at).toISOString());
  }
  return slots;
}

// 這個時段現在還能不能選（在結帳頁停太久，原本選的時段可能已經不到 30 分鐘了）
export function slotAllowed(iso, now = Date.now(), hours = []) {
  const at = Date.parse(iso);
  return Number.isFinite(at) && at % STEP === 0 && at >= now + LEAD && at <= now + AHEAD && withinHours(at, hours);
}

// 給人看的時段文字：「11:00–13:30、17:00–19:30」
export const hoursText = (hours = []) => hours.map((p) => `${p.open}–${p.close}`).join('、');
