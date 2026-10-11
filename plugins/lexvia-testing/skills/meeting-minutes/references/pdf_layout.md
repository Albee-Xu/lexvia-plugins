# PDF layout specification

This file governs body text, tables, and pagination. Use `assets/Logo Template.docx` as the authority for headers, footers, background, and page setup. Replacing the background must not change the rules below.

## Generation

1. Use both `meeting_minutes_template.md` and `Logo Template.docx`: the former defines the content structure, tables, and styles; the latter provides branded headers, footers, background, and page settings.
2. The template may contain only branded artwork and an empty body. Build the 4 × 2 meeting-information table, the 5-column action table, and the 3-column risk table from the body template. Do not use a prior meeting deliverable as a template.
3. Word/WPS or a programmatic DOCX workflow followed by LibreOffice/`soffice` PDF export is acceptable. Every approach must preserve the brand template and pass this specification.
4. Use A4 portrait pages and retain the template's margins, headers, footers, and background.

## Typography and hierarchy

- Use KaiTi for Chinese, or the template's designated fallback; use Times New Roman for English and numbers.
- Use a 19 pt black bold centered main title and an 11 pt black centered subtitle.
- Use 15 pt black bold main sections, numbered `一、` through `五、`; use 11 pt bold topic numbers, 12 pt bold topic names, and 10.5 pt body text.
- Use 9.5–10 pt bold white table headers and 9–10 pt black table body text.

## Tables and pagination

- The meeting-information table is always 4 × 2 with equal-width columns. Its left column uses pale pink fill and bold black text; its right column uses white fill and regular black text.
- The action table has five columns and the risk table has three. Use branded dark-red headers with bold white text, white body rows, thin light-gray borders, left-aligned text, and vertically centered cells.
- Keep `一、会议基本信息` and its table on the same page. Keep section headings, topic headings, and labels with their following content; never leave them alone at the bottom of a page.
- Follow natural document flow. If a complete table cannot fit and the remaining space only fits a header or a header plus one row, move the entire table to the next page.
- Repeat headers when a table spans pages and never split a row. Action-table continuation pages must use `四、行动项续`. Do not insert the risk table between action-table continuations.
- Render and inspect every page before delivery for Chinese-font support, hierarchy, column count and order, header colors, borders, wrapping, pagination, headers, footers, and background. Blank or near-blank pages, orphaned headings or table headers, missing continuation titles, or missing glyphs are unacceptable.
