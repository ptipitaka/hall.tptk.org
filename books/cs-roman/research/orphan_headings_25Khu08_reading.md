# Orphan headings — 25Khu08 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/25Khu08/out/25Khu08.reading.pdf`
Hits: 5

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 15 | 600.2 | 156 | h2 | 13 | 7. นนฺทมาณวปุจฺฉา |
| 73 | 529.4 | 578 | h2 | 67 | 4. เมตฺตาคูมาณวปุจฺฉานิทฺเทส |
| 127 | 610.3 | 1012 | h2 | 121 | 7. นนฺทมาณวปุจฺฉานิทฺเทส |
| 269 | 580.3 | 1982 | h2 | 253 | เอโก จเร ขคฺควิสาณกปฺโป. (9) |
| 326 | 393.7 | 2396 | h2 | 307 | 19. ขคฺควิสาณสุตฺตนิทฺเทส |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [156, 578, 1012, 1982, 2396]
}
```
