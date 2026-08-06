# Orphan headings — 27khu10 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/27khu10/out/27khu10.reading.pdf`
Hits: 7

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 192 | 205.8 | 1401 | h2 | 176 | เตสํ อิมา อุทฺทานคาถา |
| 200 | 414.0 | 1461 | h2 | 183 | 2. สาสนปฏฺฐานทุติยภูมิ ตตฺถิมา อุทฺทานคาถา |
| 229 | 97.9 | 1719 | boo | 210 | เปฏโกปเทสปาฬิ |
| 241 | 569.7 | 1794 | h2 | 218 | ตตฺถิมา อุทฺทานคาถา |
| 282 | 564.6 | 2024 | boo | 264 | เปฏโกปเทสปาฬิ |
| 329 | 527.5 | 2218 | boo | 302 | เปฏโกปเทสปาฬิ |
| 372 | 556.3 | 2458 | h2 | 340 | ตตฺถิมา อุทฺทานคาถา |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [1401, 1461, 1719, 1794, 2024, 2218, 2458]
}
```
