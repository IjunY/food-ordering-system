// 預約取餐的時段規則（和後端 app/orders/pickup.py 一樣，後端會再檢查一次）：
// 每 15 分鐘一個時段（12:00、12:15…），最早是現在起 30 分鐘後，最晚 24 小時內
export const SLOT_MINUTES = 15;
export const MIN_LEAD_MINUTES = 30;
export const MAX_AHEAD_HOURS = 24;

const STEP = SLOT_MINUTES * 60000;
const LEAD = MIN_LEAD_MINUTES * 60000;
const AHEAD = MAX_AHEAD_HOURS * 3600000;

// 現在可以選的所有時段（ISO 字串，由早到晚）。台灣是整點時區，所以用 UTC 毫秒對齊 15 分鐘就好
export function pickupSlots(now = Date.now()) {
  const slots = [];
  for (let at = Math.ceil((now + LEAD) / STEP) * STEP; at <= now + AHEAD; at += STEP) slots.push(new Date(at).toISOString());
  return slots;
}

// 這個時段現在還能不能選（在結帳頁停太久，原本選的時段可能已經不到 30 分鐘了）
export function slotAllowed(iso, now = Date.now()) {
  const at = Date.parse(iso);
  return Number.isFinite(at) && at % STEP === 0 && at >= now + LEAD && at <= now + AHEAD;
}
