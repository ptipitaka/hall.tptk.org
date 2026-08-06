# Orphan headings — 21Khu04 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/21Khu04/out/21Khu04.reading.pdf`
Hits: 5

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 135 | 230.7 | 1101 | h2 | 72 | 220. ปฏิสมฺภิทา จตสฺโส ฯเปฯ กตํ พุทฺธสฺส สาสนํ. (5158) |
| 137 | 369.7 | 1108 | h2 | 73 | สตานิ เทฺว โหนฺติ คาถา, อูนวีสติเมว จ. |
| 191 | 93.3 | 1526 | h2 | 100 | อสีติ เจตฺถ คาถาโย, ติสฺโส คาถา ตทุตฺตริ. |
| 460 | 192.8 | 3489 | h2 | 239 | คาถา สตานิ ปญฺเจว, นว จาปิ ตทุตฺตริ. |
| 725 | 608.4 | 5888 | h2 | 405 | 9. อลีนสตฺตุจริย |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [1101, 1108, 1526, 3489, 5888]
}
```
