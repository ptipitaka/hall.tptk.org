import glyphsData from '../../data/glyphs.json' with { type: 'json' };
import scriptsData from '../../data/scripts.json' with { type: 'json' };

export function loadGlyphs() {
  return glyphsData;
}

export function loadScripts() {
  return scriptsData;
}
