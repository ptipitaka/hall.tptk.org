# Orphan headings — 08Di03 (reading)

PDF: `C:/Dev/hall.tptk.org/books/cs-roman/volumes/08Di03/out/08Di03.reading.pdf`
Hits: 6

Physical page = `\thepage` / key for visual check; **order** goes in `page_breaks_reading_mode.before_orders`.

| physical | y0 | order | kind | src folio | text |
|---------:|---:|------:|------|----------:|------|
| 5 | 622.7 | 832 | cha | 158 | 9. อาฏานาฏิยสุตฺต |
| 128 | 567.5 | 584 | h2 | 123 | 7. ลกฺขณสุตฺต |
| 135 | 459.3 | 640 | h2 | 131 | 7. ลกฺขณสุตฺต |
| 145 | 494.0 | 682 | h2 | 137 | 7. ลกฺขณสุตฺต |
| 198 | 588.7 | 986 | h2 | 178 | หิรี จ โอตฺตปฺปญฺจ. (5) |
| 199 | 603.7 | 1001 | h2 | 179 | อินฺทฺริเยสุ อคุตฺตทฺวารตา จ โภชเน อมตฺตญฺญุตา จ. (19) |

## Suggested `before_orders`

```json
"page_breaks_reading_mode": {
  "before_orders": [832, 584, 640, 682, 986, 1001]
}
```
