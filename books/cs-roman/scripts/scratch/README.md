# Scratch / ad-hoc scripts

One-off debug and audit scripts that are **not** part of the CS Roman
pipeline (`extract` → `headings` → `prepare` → `latexmk`).

They are kept for reference only and are not maintained.

## How to run

Most scripts assume:

- current working directory is `books/cs-roman/scripts/`
- sibling pipeline modules (`assign_cs_roman_heading_levels.py`, etc.)
  are importable via `sys.path`

Example:

```powershell
cd books/cs-roman/scripts
python scratch/_audit_matika2.py
```

Some older layout helpers (`analyze_layout.py`, `measure_ours.py`) still
use outdated paths from an earlier tree layout; treat them as notes, not
as runnable tooling.
