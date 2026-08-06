# Orphan headings — 31Abhi03 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/31Abhi03/out/31Abhi03.reading.pdf`
Hits: 7

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 1 | 614.4 | 200 | h1 | 28 | 2. ทุติยนย |
| 15 | 610.9 | 100 | h2 | 14 | 7. ติก |
| 63 | 616.2 | 483 | h2 | 69 | 10. ทสมนย |
| 95 | 526.6 | 693 | boo | 102 | ปุคฺคลปญฺญตฺติปาฬิ |
| 108 | 531.3 | 871 | h1 | 113 | 8. อฏฺฐก-อุทฺเทส |
| 143 | 552.8 | 1191 | boo | 162 | ปุคฺคลปญฺญตฺติปาฬิ |
| 157 | 547.8 | 1242 | boo | 172 | ปุคฺคลปญฺญตฺติปาฬิ |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [200, 100, 483, 693, 871, 1191, 1242]
}
```
