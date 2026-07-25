import { loadGlyphs } from './data.js';

function thaiMeta() {
  return loadGlyphs().thai;
}

export function beautifyThai(text, { thaiPua = false } = {}) {
  const meta = thaiMeta();
  text = text.replace(/([ก-ฮ])([เโไใ])/g, '$2$1');
  // Keep i + niggahita as ิํ (not Thai sara ue ึ — that mark is not Pāli).
  if (thaiPua) {
    text = text.split(meta.pua_yo.from).join(meta.pua_yo.to);
    text = text.split(meta.pua_tho.from).join(meta.pua_tho.to);
  }
  return text;
}

export function unbeautifyThai(text) {
  const meta = thaiMeta();
  text = text.split(meta.wrong_tt.from).join(meta.wrong_tt.to);
  text = text.split(meta.pua_yo.to).join(meta.pua_yo.from);
  text = text.split(meta.pua_tho.to).join(meta.pua_tho.from);
  // Legacy tipitaka-style ึ → ิํ so Thai→Roman still works on older text.
  const legacy = meta.legacy_im_composite;
  text = text.split(legacy.from).join(legacy.to);
  text = text.replace(/([เโไใ])([ก-ฮ])/g, '$2$1');
  return text;
}
