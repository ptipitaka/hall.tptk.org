# Orphan headings — 22Khu05 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/22Khu05/out/22Khu05.reading.pdf`
Hits: 6

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 6 | 376.8 | 2153 | h4 | 146 | 2. ขรปุตฺตวคฺค |
| 68 | 539.2 | 834 | h2 | 53 | 202. เกฬิสีลชาตก (2-6-2) |
| 69 | 566.9 | 845 | h2 | 54 | 204. วีรกชาตก (2-6-4) |
| 129 | 572.6 | 1627 | h1 | 109 | 4. จตุกฺกนิปาต 4. โกกิลวคฺค |
| 190 | 595.4 | 2388 | h6 | 165 | 7. สตฺตกนิปาต 2. คนฺธารวคฺค |
| 213 | 566.7 | 2683 | h6 | 187 | 9. นวกนิปาต |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [2153, 834, 845, 1627, 2388, 2683]
}
```
