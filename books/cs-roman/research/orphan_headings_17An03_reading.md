# Orphan headings — 17An03 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/17An03/out/17An03.reading.pdf`
Hits: 7

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 10 | 632.9 | 3471 | cha | 530 | 2. อนุสฺสติวคฺค |
| 376 | 607.1 | 1464 | h2 | 246 | 8. ปรินิพฺพานสุตฺต |
| 544 | 578.2 | 2190 | cha | 361 | (8) 3. อากงฺขวคฺค |
| 683 | 615.7 | 2889 | h2 | 455 | 11. ทุกฺขวิปากสุตฺต |
| 729 | 536.3 | 3151 | h2 | 485 | สาธุวคฺโค ตติโย. |
| 764 | 579.3 | 3352 | h2 | 512 | สามญฺญวคฺโค ทุติโย. |
| 769 | 606.1 | 3392 | h2 | 517 | 3. ปฐม-อุปนิสาสุตฺต |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [3471, 1464, 2190, 2889, 3151, 3352, 3392]
}
```
