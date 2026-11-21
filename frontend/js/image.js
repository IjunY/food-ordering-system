// 上傳前先把照片縮小（長邊 maxSide px）。回傳畫好的 canvas，呼叫的人再轉成 JPEG：
// 假後端轉成 data URL 存在瀏覽器（js/mock/api.js），真後端轉成檔案送到 POST /api/uploads（js/real/api.js）。
import { getLang } from './i18n.js';

const MAX_FILE = 10 * 1024 * 1024;

export async function shrinkImage(file, maxSide) {
  if (!file || !file.type.startsWith('image/')) throw new Error(getLang() === 'en' ? 'Please choose an image file' : '請選擇圖片檔');
  if (file.size > MAX_FILE) throw new Error(getLang() === 'en' ? 'Please choose a photo under 10 MB' : '照片太大，請選 10 MB 以下的檔案');
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => { const i = new Image(); i.onload = () => resolve(i); i.onerror = reject; i.src = url; });
    const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas;
  } catch {
    throw new Error(getLang() === 'en' ? 'This photo could not be opened' : '這張照片打不開，請換一張');
  } finally {
    URL.revokeObjectURL(url);
  }
}
