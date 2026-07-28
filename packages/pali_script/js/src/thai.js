import { loadGlyphs } from './data.js';

// Front vowels in Thai writing order (Pāli uses เ/โ; ไ/ใ kept for legacy symmetry).
const FRONT = 'เโไใ';
// Final letters of กล้ำ pairs (y r l v h ḷ).
const GLIDE = 'ยรลวฬห';

const SWAP1 = new RegExp(`([ก-ฮ])([${FRONT}])`, 'g');
const SWAP2 = new RegExp(`((?:[ก-ฮ]ฺ)*)([ก-ฮ]ฺ)([${FRONT}])([${GLIDE}])`, 'g');
const UNSWAP_CLUSTER = new RegExp(`([${FRONT}])([ก-ฮ]ฺ[${GLIDE}])`, 'g');
// After cluster unswap (…CฺGโ → …CฺGโ), front vowel sits after ฺG — do not move it again.
// Still unswap normal …วโต / …หโต where the glide is not a กล้ำ pair.
const UNSWAP_SINGLE = new RegExp(`(?<!ฺ[${GLIDE}])([${FRONT}])([ก-ฮ])`, 'g');

function thaiMeta() {
  return loadGlyphs().thai;
}

function swapFrontVowels(text) {
  // 1) Single consonant: กเ → เก, ทฺวเ → ทฺเว
  text = text.replace(SWAP1, '$2$1');
  // 2) กล้ำ pair: ทฺเว → เทฺว, นฺทฺเร → นฺเทฺร (skip geminate ยฺย / ลฺล)
  text = text.replace(SWAP2, (_, codas, baseVir, front, glide) => {
    if (baseVir[0] === glide) return `${codas}${baseVir}${front}${glide}`;
    return `${codas}${front}${baseVir}${glide}`;
  });
  return text;
}

function unswapFrontVowels(text) {
  text = text.replace(UNSWAP_CLUSTER, '$2$1');
  text = text.replace(UNSWAP_SINGLE, '$2$1');
  return text;
}

export function beautifyThai(text, { thaiPua = false } = {}) {
  const meta = thaiMeta();
  text = swapFrontVowels(text);
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
  text = unswapFrontVowels(text);
  return text;
}
