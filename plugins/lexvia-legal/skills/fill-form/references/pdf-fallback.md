# Conditional PDF fallback

Use fallback only for a particular source whose compatible native reader is unavailable or demonstrably inadequate. First record the selected/attempted reader, exact reason and coverage gap. Incomplete discovery is not a missing reader. Native extraction remains preferred for every other supported source.

Convert in an isolated work directory using a tested local headless converter. Never open a desktop app, browser, picker, print dialog or preview. Do not execute macros, fetch remote images, refresh external data or use an external conversion service without authorization. Keep source bytes unchanged.

The bundled `convert_fallbacks.py` exposes only supported adapters. Check `--help` and its capability report. Missing converter support must produce an explicit failure/unsupported outcome, not an empty successful PDF. No adapter is a universal document reader.

For every derivative record original source ID/hash, derivative ID/path/hash, converter/version, reason, page count, original-to-PDF map where known, limitations, and conversion status. Preserve the original as the primary evidence reference. After conversion, explicitly load Anthropic PDF and use it to read/extract/OCR the derivative.

Coverage checks depend on the format:

- Office documents: verify every relevant section, headers/footers, tables, notes, revision state, fonts and pagination. Do not silently accept an export containing only the first page or selected slide.
- Spreadsheets: ordinary print export can omit cells outside print areas. Inventory all sheets/used ranges and hidden states; retain the inclusion/exclusion decision. Full-sheet export can make tiny unreadable text. If cell coverage or formula provenance cannot be established, report incomplete conversion and do not accept affected facts.
- Emails: preserve headers, timezone, message identity and full body. Process attachments separately and retain their parent message. Rendering only an HTML body without headers is insufficient. Remote resources remain unfetched.
- Images: retain every TIFF frame/page, orientation and readable resolution. Do not shrink scans to fit an arbitrary small canvas before OCR.
- Text/HTML: retain encoding, complete body and source attribution. HTML conversion must not fetch remote resources. A text-only fallback must disclose omitted images or complex layout.

A successful renderer exit is not coverage proof. Inspect the generated PDF through Anthropic PDF. Missing fonts, stripped attachments, dropped sheets, clipped tables, or unreadable regions become reportable gaps. Do not invent native cell/page locators from a flattened representation.

Fallback conversion does not repair a damaged target form. Target-template normalization/repair is a separate, PDF-skill-led working-copy operation with structural and visual verification. Do not silently flatten or replace a template to bypass a failed fill.
