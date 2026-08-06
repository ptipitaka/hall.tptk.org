# Orphan headings — 19Khu02 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/19Khu02/out/19Khu02.reading.pdf`
Hits: 11

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 6 | 623.5 | 3183 | cha | 263 | 3. ติกนิปาต |
| 9 | 634.4 | 3802 | cha | 307 | 11. เอกาทสนิปาต |
| 10 | 620.9 | 4258 | cha | 341 | 17. ติํสนิปาต |
| 367 | 550.0 | 3197 | boo | 264 | เถรคาถาปาฬิ |
| 377 | 527.5 | 3273 | h2 | 268 | ตตฺรุทฺทานํ |
| 404 | 598.6 | 3592 | h2 | 290 | ตตฺรุทฺทานํ |
| 430 | 410.2 | 3820 | h2 | 308 | เอกาทสนิปาตมฺหิ, คาถา เอกาทเสว จาติ. |
| 449 | 580.1 | 4046 | boo | 326 | เถรคาถาปาฬิ |
| 460 | 610.0 | 4170 | h2 | 335 | 16. วีสตินิปาต |
| 518 | 577.6 | 4680 | h2 | 377 | ขุทฺทกนิกาย |
| 569 | 573.5 | 5298 | h1 | 425 | 15. จตฺตาลีสนิปาต |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [3183, 3802, 4258, 3197, 3273, 3592, 3820, 4046, 4170, 4680, 5298]
}
```
