# Headless helper contracts

All paths in commands below are examples to replace with the user's selected paths. Use the available Python executable. No helper opens an application or calls a language model; the host agent loads the matching extraction skills and interprets evidence. Run `--help` for the installed CLI before calling it.

## Reader registry and inventory

After discovery, create `readers.json` in the excluded run directory. Example shape:

```json
{
  "discovery": "partial",
  "readers": [
    {"id": "documents", "version": "actual-installed-version", "formats": ["docx"], "available": true, "headless": true},
    {"id": "spreadsheets", "version": "actual-installed-version", "formats": ["xlsx", "csv", "tsv"], "available": true, "headless": true},
    {"id": "anthropic-pdf", "version": "actual-revision-or-hash", "formats": ["pdf"], "available": true, "headless": true, "is_anthropic_pdf": true}
  ]
}
```

The example is not proof that any reader is installed. Set actual versions and supported variants. Add checked unavailable readers or mark discovery complete only after the relevant tools have actually been checked. Unlisted formats under partial discovery remain unknown.

```bash
python scripts/inventory.py /selected/source-folder \
  --capabilities /run/readers.json \
  --work-dir /run/work \
  --output-dir /run/output \
  --output /run/work/manifest.json
```

Use fresh output paths. The manifest records `source_id`, original path/hash, detected format, route, extraction status and duplicate/attachment lineage. Preserve `source_id` and original hash when adding evidence. Inventory alone leaves extraction pending.

For each source actually read, update a new manifest revision with `extraction.status` (`complete`, `partial`, `error`, etc.), the performed coverage checks, and limitations. Do not mark it complete because the file was listed. Native evidence refers to these source IDs; originals are never edited.

## Conditional conversion

```bash
python scripts/convert_fallbacks.py \
  --manifest /run/work/manifest.json \
  --output-dir /run/work/fallbacks \
  --source-id src_selected \
  --output /run/work/conversion-report.json \
  --output-manifest /run/work/manifest-with-derivatives.json
```

Only sources explicitly needing fallback may be converted. If an available native reader was attempted but inadequate, supply a JSON array via `--decisions` with entries such as `{"source_id":"src_selected","status":"inadequate","reason":"Attempted reader omitted the relevant text box"}`. Do not change an unknown route to unavailable without discovery. A derivative is not extracted evidence until Anthropic PDF has actually read it.

The bundled adapters support text and images using optional reportlab/Pillow. Office conversion additionally requires `--office-command` with a verified LibreOffice executable and `--office-network-restricted` only when the current execution policy actually blocks network access. It uses a fresh profile and staged input with `--headless`, and remains partial until completeness is reviewed. Spreadsheet, email and HTML PDF conversion adapters are not bundled: use a separately verified headless converter if required, or report the unsupported fallback. Native readers remain preferred. The helper does not silently render every source or implement a replacement document reader.

## Evidence ledger

Use `assets/schemas/evidence.schema.json`. The top-level object contains `schema_version: "1.0"`, `records`, and `user_answers`. A native CSV candidate looks like:

```json
{
  "evidence_id": "ev-client-id",
  "source_id": "src_from_the_manifest",
  "field_key": "client.id",
  "subject_id": "person-client",
  "role": "client",
  "raw_value": "001234",
  "value": "001234",
  "locator": {"kind": "csv", "row": 2, "column": "Client ID"},
  "excerpt": "Client ID: 001234",
  "extraction": {"reader_id": "spreadsheets", "reader_version": "actual-version", "method": "native CSV reading"},
  "assertion": "explicit",
  "status": "accepted"
}
```

Examples illustrate record syntax; never reuse their facts for a real matter. `candidate` becomes `accepted` only after source/identity review. Rejected competitors require a rejection reason. An inferred/ambiguous claim cannot authorize filling. Record transformations, formula provenance, date context and a fallback derivative ID when applicable.

An explicit user answer belongs in `user_answers` with `answer_id`, field/person/role/value, `source: "user"`, `explicit: true`, `provided_by`, and confirmation scope where applicable. Consent/declaration choices also require `appropriate_person_confirmed: true` after that has actually been established. Never invent a user answer or an authority confirmation to clear validation.

## Profile and answer map

Profiles use `profile_id`, `schema_version`, `template` (including exact SHA-256 and page count), `readiness`, and `logical_fields`. Inspect the profile schema and the bundled Form 956 example. Do not change `readiness.status` to `verified` to bypass the sample's failed round trip. Mechanical verification must be supported by actual PDF inspection/tests.

Every profile field requires one answer-map decision with the same `field_key`. The map contains `profile_id`, `template_sha256`, primary `subject_id`, `matter_id`, role-to-person `subject_bindings` for multiple people, `answers`, and `qa`. Bind representative and client roles to their actual distinct subjects; reusable profiles must not bake in a client's identity.

Each decision contains `field_key`, `subject_id`, `role`, `status`, `evidence_ids`, `user_answer_ids`, and a reason for unresolved/manual decisions. A supported decision also carries its exact normalized `value`. Unresolved or inactive decisions must not carry a fill value. QA starts pending; change it only after the actual check.

## Validation and field-value export

```bash
python scripts/validate_records.py \
  --manifest /run/work/manifest-extracted.json \
  --evidence /run/work/evidence.json \
  --profile /run/work/verified-profile.json \
  --answers /run/work/answers.json \
  --check-files --template /selected/blank.pdf \
  --output /run/work/validation.json
```

This command distinguishes record validity from export readiness. A valid partial evidence draft can still be blocked by unverified mappings or the template gate. Hash checks do not prove evidence interpretation.

To export a verified **fillable-field** payload, add `--export-values /run/work/field-values.json` with a fresh path. This rechecks files and the actual template. The helper emits the Anthropic PDF workflow's `[{"field_id": "…", "page": 1, "value": "…"}]` list. It does not fill the PDF. Unknown, duplicate or unverified mappings must be resolved; checkbox/choice tokens come from the inspected template, not generic Yes/No guesses. Annotation data must be prepared and checked through Anthropic PDF's own workflow.

## Report and verification

```bash
python scripts/build_review_report.py \
  --manifest /run/work/manifest-extracted.json \
  --evidence /run/work/evidence.json \
  --profile /run/work/verified-profile.json \
  --answers /run/work/answers-after-qa.json \
  --check-files --template /selected/blank.pdf \
  --output /run/output/review-report.md
```

The report can be useful even when validation fails; its status must show the failure and gaps. It does not claim a PDF was produced. Keep source coverage, export eligibility, and actual PDF QA separate.

For structural inspection use `python scripts/probe_pdf.py --help`; the probe is read-only and does not repair or fill a template. A normal widget-to-field count difference is not itself corruption; use the detailed relationships and issues.

Run helper regression tests with `python -m unittest discover -s tests -v`. Tests use temporary synthetic fixtures and must never read the surrounding client folder.
