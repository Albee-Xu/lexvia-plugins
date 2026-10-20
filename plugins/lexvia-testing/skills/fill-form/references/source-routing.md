# Native source readers and capability discovery

Select a reader per file, not once for the whole folder. Detect actual format and supported variants. Record the skill/tool identity, version or file hash, supported extensions, availability and headless capability. Skill display names are hints, not proof of support. Skill discovery/metadata loading must not open an app or connector UI.

| Source | Preferred reader | Evidence location and coverage |
| --- | --- | --- |
| PDF | Authorized Anthropic PDF skill | One-based page/region; text and image pages, form fields if relevant |
| DOC/DOCX | Documents skill; its compatible DOC-to-DOCX path when needed | Paragraph/section/table/cell; headers, footers, text boxes, revision/comment treatment |
| XLS/XLSX | Spreadsheets skill | Workbook/sheet/cell or range; all sheet names/hidden states, used ranges, formulas and cached results |
| CSV/TSV | Spreadsheets skill | File/row/column header; delimiter, encoding, quoted multiline records and leading zeros |
| PPT/PPTX | Presentations skill when supported | Slide/shape; tables, notes and image-only content |
| EML/MSG | Compatible local email reader/parser | Message-ID, headers/body part; Date timezone, quoted/forwarded authorship, attachment lineage |
| Images | Available file-image/vision/OCR reader | Frame and region; rotation, language, uncertain characters |
| TXT/HTML | Native local file/HTML parser | Line/section or stable element; encoding and complete content |
| Other/unsupported variant | Discover a compatible reader, then conditional PDF fallback | Original hash and coverage/loss report |

Availability states matter:

- Available: a verified compatible reader can operate without UI. Use it first.
- Unavailable: discovery established no working compatible reader, or access is unavailable. Record the reason and consider PDF fallback.
- Unknown: discovery is incomplete. Continue discovery; do not pretend absence has been proved.
- Inadequate: the attempted reader failed or omitted material needed for this form. Retain its coverage and error, then consider fallback for that file or missing portion.

Do not declare PDF available merely because a generic Python PDF library is installed. Confirm the requested Anthropic PDF skill is loaded and use its workflow. Do not install or connect unrelated services automatically to satisfy an optional reader.

For spreadsheets read natively without using print ranges as extraction boundaries. Preserve values as strings when necessary for identifiers and leading zeros. Distinguish original cached results from intentional recalculation. Do not refresh external links or silently recalculate source workbooks. If a native reader recalculates a working copy, label the results as derived and retain originals.

For Word, paragraph/table references are preferable to invented page numbers. A page locator is valid only against a retained, verified rendering. For CSV a logical record may span physical lines: use a stable row number and column identity. For emails keep the original, headers and parent-child attachment links; do not attribute quoted history to the newest sender.

Archives are containers, not a supported document format by default. If explicitly required, inspect members safely in an isolated work directory, prevent path traversal, and inventory extracted documents independently; do not silently scan large archives during ordinary folder intake.

All selected readers feed one evidence ledger. Their native locators remain intact. A missing email reader must not force an available Word or spreadsheet reader to use PDF conversion.
