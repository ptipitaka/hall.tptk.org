import { loadGlyphs, loadScripts } from './data.js';
import { normalizeRomanInput } from './roman.js';
import { beautifyThai, unbeautifyThai } from './thai.js';

export const Script = Object.freeze({
  ROMAN: 'roman',
  THAI: 'thai',
  AUTO: 'auto',
});

let _tables;

function tables() {
  if (_tables) return _tables;
  const g = loadGlyphs();
  const consByRoman = Object.fromEntries(g.consonants.map((c) => [c.roman, c]));
  const consByThai = Object.fromEntries(g.consonants.map((c) => [c.thai, c]));
  const vowByRoman = Object.fromEntries(g.vowels.map((v) => [v.roman, v]));
  const romanConsKeys = Object.keys(consByRoman).sort((a, b) => b.length - a.length);
  const romanVowKeys = Object.keys(vowByRoman).sort((a, b) => b.length - a.length);
  const niggahita = g.specials.find((s) => s.id === 'niggahita');
  const virama = g.thai.virama;
  const digitsR2T = Object.fromEntries(g.digits.map((d) => [d.roman, d.thai]));
  const digitsT2R = Object.fromEntries(g.digits.map((d) => [d.thai, d.roman]));
  const depVowelThai = {};
  for (const v of g.vowels) {
    if (v.thai_dep != null && v.thai_dep !== '') depVowelThai[v.thai_dep] = v;
  }
  const indepPairs = [];
  for (const v of g.vowels) {
    if (v.thai_indep) indepPairs.push([v.thai_indep, v]);
    if (v.thai_indep_short) indepPairs.push([v.thai_indep_short, v]);
  }
  indepPairs.sort((a, b) => b[0].length - a[0].length);
  _tables = {
    consByRoman,
    consByThai,
    vowByRoman,
    romanConsKeys,
    romanVowKeys,
    niggahita,
    virama,
    digitsR2T,
    digitsT2R,
    depVowelThai,
    indepPairs,
    toneMarks: new Set([...g.thai.tone_marks]),
    maiHan: g.thai.mai_han_akat,
    maiTaikhu: g.thai.mai_taikhu,
    saraA: g.thai.sara_a,
  };
  return _tables;
}

function matchLongest(text, i, keys) {
  for (const key of keys) {
    if (text.startsWith(key, i)) return key;
  }
  return null;
}

export function detectScript(text) {
  const scripts = loadScripts().scripts;
  const counts = Object.fromEntries(scripts.map((s) => [s.code, 0]));
  for (const ch of text) {
    const code = ch.codePointAt(0);
    for (const s of scripts) {
      for (const rng of s.ranges) {
        const [lo, hi] = rng;
        if (code >= lo && code <= hi) {
          if (s.code === 'roman' && code < 128 && !/\p{L}/u.test(ch)) break;
          counts[s.code] += 1;
          break;
        }
      }
    }
  }
  if ((counts.thai || 0) > 0) return Script.THAI;
  if ((counts.roman || 0) > 0) return Script.ROMAN;
  return Script.ROMAN;
}

export function convert(text, fromScript, toScript, { thaiPua = false } = {}) {
  let src = fromScript;
  let dst = toScript;
  if (src === Script.AUTO) src = detectScript(text);
  if (src === dst) {
    if (src === Script.ROMAN) return normalizeRomanInput(text);
    return text;
  }
  if (src === Script.ROMAN && dst === Script.THAI) return romanToThai(text, { thaiPua });
  if (src === Script.THAI && dst === Script.ROMAN) return thaiToRoman(text);
  throw new Error(`Unsupported conversion: ${src} → ${dst}`);
}

function romanToThai(text, { thaiPua = false } = {}) {
  text = normalizeRomanInput(text);
  const t = tables();
  const out = [];
  let i = 0;
  const n = text.length;
  let consBuf = [];

  function flushCluster(vowel) {
    if (!consBuf.length) {
      if (vowel) {
        if (vowel.roman === 'a') out.push(vowel.thai_indep_short || 'อ');
        else out.push(vowel.thai_indep || '');
      }
      return;
    }
    for (let k = 0; k < consBuf.length - 1; k++) {
      out.push(consBuf[k].thai + t.virama);
    }
    const last = consBuf[consBuf.length - 1].thai;
    if (vowel == null) out.push(last + t.virama);
    else if (vowel.inherent) out.push(last);
    else if (vowel.thai_dep == null) {
      out.push(last + t.virama);
      out.push(vowel.thai_indep || '');
    } else out.push(last + vowel.thai_dep);
    consBuf = [];
  }

  while (i < n) {
    const ch = text[i];
    if (/\s/.test(ch) || "[]()·–—.,;:/\\\"'?!…°ʼ-".includes(ch)) {
      flushCluster(null);
      out.push(ch);
      i += 1;
      continue;
    }
    if (t.digitsR2T[ch]) {
      flushCluster(null);
      out.push(t.digitsR2T[ch]);
      i += 1;
      continue;
    }
    const nig = t.niggahita.roman;
    if (text.startsWith(nig, i)) {
      if (consBuf.length) flushCluster(t.vowByRoman.a);
      else if (out.length && out[out.length - 1].endsWith(t.virama)) {
        out[out.length - 1] = out[out.length - 1].slice(0, -t.virama.length);
      }
      out.push(t.niggahita.thai);
      i += nig.length;
      continue;
    }
    const consKey = matchLongest(text, i, t.romanConsKeys);
    if (consKey != null) {
      consBuf.push(t.consByRoman[consKey]);
      i += consKey.length;
      continue;
    }
    const vowKey = matchLongest(text, i, t.romanVowKeys);
    if (vowKey != null) {
      flushCluster(t.vowByRoman[vowKey]);
      i += vowKey.length;
      continue;
    }
    flushCluster(null);
    out.push(ch);
    i += 1;
  }
  flushCluster(null);
  return beautifyThai(out.join(''), { thaiPua });
}

function thaiToRoman(text) {
  text = unbeautifyThai(text);
  const t = tables();
  const cons = t.consByThai;
  const out = [];
  let i = 0;
  const n = text.length;
  const { virama, maiHan, maiTaikhu, saraA, toneMarks } = t;
  const nig = t.niggahita.thai;

  while (i < n) {
    const ch = text[i];
    if (toneMarks.has(ch) || ch === maiTaikhu) {
      i += 1;
      continue;
    }
    if (t.digitsT2R[ch]) {
      out.push(t.digitsT2R[ch]);
      i += 1;
      continue;
    }
    if (/\s/.test(ch) || "[]()·–—.,;:/\\\"'?!…°ʼ-".includes(ch)) {
      out.push(ch);
      i += 1;
      continue;
    }
    if (ch === nig) {
      out.push(t.niggahita.roman);
      i += 1;
      continue;
    }

    let matchedIndep = false;
    for (const [indep, vow] of t.indepPairs) {
      if (!text.startsWith(indep, i)) continue;
      if (indep === 'อ') {
        const nxt = i + 1 < n ? text[i + 1] : '';
        if (t.depVowelThai[nxt] || nxt === maiHan || nxt === saraA || nxt === nig) {
          if (nxt === maiHan || nxt === saraA) {
            out.push('a');
            i += 2;
          } else if (nxt === nig) {
            out.push('aṃ');
            i += 2;
          } else {
            out.push(t.depVowelThai[nxt].roman);
            i += 2;
          }
          matchedIndep = true;
          break;
        }
        out.push('a');
        i += 1;
        matchedIndep = true;
        break;
      }
      out.push(vow.roman);
      i += indep.length;
      matchedIndep = true;
      break;
    }
    if (matchedIndep) continue;

    if (cons[ch]) {
      let clusterRoman = cons[ch].roman;
      let j = i + 1;
      while (j + 1 < n && text[j] === virama && cons[text[j + 1]]) {
        clusterRoman += cons[text[j + 1]].roman;
        j += 2;
      }
      if (j < n && text[j] === virama) {
        out.push(clusterRoman);
        i = j + 1;
        continue;
      }
      if (j < n && t.depVowelThai[text[j]]) {
        out.push(clusterRoman + t.depVowelThai[text[j]].roman);
        i = j + 1;
        continue;
      }
      if (j < n && (text[j] === maiHan || text[j] === saraA)) {
        out.push(clusterRoman + 'a');
        i = j + 1;
        continue;
      }
      if (j < n && text[j] === nig) {
        out.push(clusterRoman + 'a');
        i = j;
        continue;
      }
      out.push(clusterRoman + 'a');
      i = j;
      continue;
    }

    if (t.depVowelThai[ch]) {
      out.push(t.depVowelThai[ch].roman);
      i += 1;
      continue;
    }
    if (ch === maiHan || ch === saraA) {
      out.push('a');
      i += 1;
      continue;
    }
    if (ch === virama) {
      i += 1;
      continue;
    }
    out.push(ch);
    i += 1;
  }
  return out.join('').replace(/ {2,}/g, ' ');
}
