# pali_script — Pāli script converter

Maintainable Thai ↔ Roman (IAST) transliteration for hall.tptk.org.

- **Pivot:** Roman (IAST), matching CS Roman Tipitaka text
- **Shared data:** [`data/glyphs.json`](data/glyphs.json), [`data/scripts.json`](data/scripts.json)
- **Runtimes:** Python (`python/pali_script`) and JavaScript (`js/`)

Inspired by tipitaka.app’s beautify pipeline; glyph tables are rebuilt from standard Pāli orthography (not copied from tipitaka.app).

## Python

```python
from pali_script import convert, Script

convert("buddho", Script.ROMAN, Script.THAI)  # พุทฺโธ
convert("พุทฺโธ", Script.THAI, Script.ROMAN)    # buddho
convert("sandhiṃ", Script.ROMAN, Script.THAI)  # สนฺธิํ  (ิ + ํ, not ึ)
```

Pāli Thai keeps **ิํ** for *iṃ*. The Thai vowel mark **ึ** is not used; older text that still has `ึ` is normalized to `ิํ` on Thai→Roman.

Install editable (Docker / local):

```bash
pip install -e packages/pali_script/python
```

Tests:

```bash
# host
cd packages/pali_script && python -m unittest tests.test_python_roundtrip -v

# Docker (after pip install -e from requirements)
docker compose exec -T web python -m unittest discover -s packages/pali_script/tests -v
```

## JavaScript

```js
import { convert, Script } from '@hall/pali-script';

convert('buddho', Script.ROMAN, Script.THAI);
```

Frontend already depends on `@hall/pali-script` via `file:../packages/pali_script/js`.

```bash
cd packages/pali_script/js && npm test
```

## Adding a script later

1. Add glyph columns in `data/glyphs.json` (e.g. `"myanmar": "က"`).
2. Register metadata in `data/scripts.json`.
3. Add `beautify_*` / `unbeautify_*` hooks if the script needs display normalization.
4. Extend fixtures in `tests/fixtures/roundtrips.json`.
