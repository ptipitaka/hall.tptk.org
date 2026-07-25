import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { convert, Script } from '../src/index.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(
  readFileSync(join(__dirname, '..', '..', 'tests', 'fixtures', 'roundtrips.json'), 'utf8'),
);

describe('roman → thai', () => {
  for (const row of fixtures) {
    it(row.roman, () => {
      assert.equal(convert(row.roman, Script.ROMAN, Script.THAI), row.thai);
    });
  }
});

describe('thai → roman', () => {
  for (const row of fixtures) {
    it(row.thai, () => {
      assert.equal(convert(row.thai, Script.THAI, Script.ROMAN), row.roman);
    });
  }
});

describe('round-trip roman', () => {
  for (const row of fixtures) {
    it(row.roman, () => {
      const thai = convert(row.roman, Script.ROMAN, Script.THAI);
      assert.equal(convert(thai, Script.THAI, Script.ROMAN), row.roman);
    });
  }
});

it('niggahita alt ṁ', () => {
  assert.equal(convert('dhammaṁ', Script.ROMAN, Script.THAI), 'ธมฺมํ');
});

it('iṃ stays as ิํ (not sara ue ึ)', () => {
  assert.equal(convert('sandhiṃ', Script.ROMAN, Script.THAI), 'สนฺธิํ');
  assert.ok(!convert('sandhiṃ', Script.ROMAN, Script.THAI).includes('ึ'));
  assert.equal(convert('สนฺธึ', Script.THAI, Script.ROMAN), 'sandhiṃ');
});

it('auto detect thai', () => {
  assert.equal(convert('พุทฺโธ', Script.AUTO, Script.ROMAN), 'buddho');
});
