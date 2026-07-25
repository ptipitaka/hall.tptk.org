import { loadGlyphs } from './data.js';

export function normalizeRomanInput(text) {
  text = text.toLowerCase();
  const glyphs = loadGlyphs();
  for (const spec of glyphs.specials) {
    if (spec.id !== 'niggahita') continue;
    const canon = spec.roman;
    for (const alt of spec.roman_alt || []) {
      text = text.split(alt).join(canon);
    }
    text = text.split('ṁ').join(canon);
  }
  return text;
}
