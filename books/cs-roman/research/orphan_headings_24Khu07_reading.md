# Orphan headings — 24Khu07 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/24Khu07/out/24Khu07.reading.pdf`
Hits: 4

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 19 | 546.9 | 107 | h2 | 17 | 2. คุหฏฺฐกสุตฺตนิทฺเทส |
| 48 | 512.8 | 280 | h2 | 45 | 2. คุหฏฺฐกสุตฺตนิทฺเทส |
| 97 | 540.5 | 650 | h2 | 90 | ปรมฏฺฐกสุตฺตนิทฺเทโส ปญฺจโม. |
| 105 | 584.3 | 719 | h2 | 97 | 6. ชราสุตฺตนิทฺเทส |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [107, 280, 650, 719]
}
```
