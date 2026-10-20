#!/usr/bin/env python3
"""Build a local Markdown review report without opening any application or browser."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from validate_records import read_json, validate_records, atomic_text, input_paths


def safe(value):
    return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def locator_text(locator):
    if not isinstance(locator, dict):
        return 'locator unavailable'
    return ', '.join(f'{key}={value}' for key, value in locator.items() if key != 'kind') or str(locator.get('kind', 'unavailable'))


def build_report(manifest, evidence, profile, answers, validation):
    sources = {source['source_id']: source for source in manifest.get('sources', [])}
    facts = {record['evidence_id']: record for record in evidence.get('records', [])}
    fields = {field['key']: field for field in profile.get('logical_fields', [])}
    decisions = answers.get('answers', [])
    passed = validation.get('valid', False)
    qa = answers.get('qa', {})
    unresolved_required = any(fields.get(item.get('field_key'), {}).get('required') and item.get('status') not in {'supported', 'not_applicable'} for item in decisions)
    verified = passed and profile.get('readiness', {}).get('status') == 'verified' and not unresolved_required and all(qa.get(name) == 'pass' for name in ('readback', 'rendered', 'originals'))
    lines = [
        '# PDF draft review', '',
        f'Profile: `{safe(profile.get("profile_id", "unknown"))}`. Matter: `{safe(answers.get("matter_id", "unknown"))}`.', '',
        f'Status: **{"record checks passed; QA recorded as complete" if verified else "review required; draft is not fully verified"}**.', '',
        'This report records evidence, unresolved items, and QA claims. Automated record checks do not establish factual accuracy, decision authority, or visual legibility.', '',
        '## Gaps, conflicts, and manual actions', '',
        '| Field | Status | Required | Action/reason |', '| --- | --- | --- | --- |',
    ]
    unresolved = [item for item in decisions if item.get('status') not in {'supported', 'not_applicable'}]
    for item in unresolved:
        field = fields.get(item.get('field_key'), {})
        lines.append(f'| {safe(item.get("field_key"))} | {safe(item.get("status"))} | {"yes" if field.get("required") else "no"} | {safe(item.get("reason", "Review source evidence or obtain an explicit answer."))} |')
    accounted = {item.get('field_key') for item in decisions}
    for key in fields.keys() - accounted:
        lines.append(f'| {safe(key)} | unaccounted | {"yes" if fields[key].get("required") else "no"} | Add a decision; do not silently omit this field. |')
    if not unresolved and not (fields.keys() - accounted):
        lines.append('| — | — | — | No unresolved field records. |')
    for overflow in answers.get('overflow', []):
        lines.extend(['', f'- Overflow: {safe(overflow)}'])
    lines.extend(['', '## Source coverage', '', '| Original source | Reader route | Extraction | Fallback/limitations |', '| --- | --- | --- | --- |'])
    for source in sources.values():
        route = source.get('route', {})
        extraction = source.get('extraction', {})
        derivatives = source.get('derivatives', [])
        notes = []
        if source.get('duplicate_of'):
            notes.append(f'duplicate of {source["duplicate_of"]}')
        if derivatives:
            for derivative in derivatives:
                notes.append(f'PDF fallback {derivative.get("derivative_id")}: {derivative.get("reason", "reason missing")}; conversion {derivative.get("conversion_status", "unknown")}')
                notes.extend(str(limit) for limit in derivative.get('limitations', []))
        if route.get('reason'):
            notes.append(route['reason'])
        for key in ('coverage', 'limitations', 'error'):
            if extraction.get(key):
                notes.append(f'{key}: {json.dumps(extraction[key], ensure_ascii=False) if isinstance(extraction[key], (dict, list)) else extraction[key]}')
        reader = f'{route.get("status", "unknown")} / {route.get("reader_id", "unselected")} {route.get("reader_version", "")}'
        lines.append(f'| {safe(source.get("relative_path", source.get("source_id")))} | {safe(reader)} | {safe(extraction.get("status", "unknown"))} | {safe("; ".join(notes) or "No recorded limitation; verify coverage record.")} |')
    for label in ('excluded', 'errors'):
        for item in manifest.get(label, []):
            lines.extend(['', f'- Intake {label}: {safe(json.dumps(item, ensure_ascii=False))}'])
    lines.extend(['', '## Proposed field evidence', '', '| Field | Status | Value | Original evidence location / user answer |', '| --- | --- | --- | --- |'])
    for item in decisions:
        citations = []
        for eid in item.get('evidence_ids', []):
            record = facts.get(eid, {})
            source = sources.get(record.get('source_id'), {})
            location = f'{source.get("relative_path", record.get("source_id", "unknown"))}: {locator_text(record.get("original_locator") or record.get("locator"))}'
            if record.get('derivative_id'):
                location += f' [PDF derivative {record["derivative_id"]}, {locator_text(record.get("locator"))}]'
            citations.append(f'{eid} — {location}')
        citations.extend(f'explicit user answer {uid}' for uid in item.get('user_answer_ids', []))
        value = json.dumps(item.get('value'), ensure_ascii=False) if item.get('status') == 'supported' else '—'
        lines.append(f'| {safe(item.get("field_key"))} | {safe(item.get("status"))} | {safe(value)} | {safe("; ".join(citations) or "—")} |')
    lines.extend(['', '## Validation and PDF QA', '', f'- Record consistency: {"pass" if passed else "fail"}.', f'- Safe fillable values export: {"eligible" if validation.get("export_ready") else "blocked or not checked"}.'])
    for name in ('readback', 'rendered', 'originals'):
        lines.append(f'- {name.capitalize()}: {safe(qa.get(name, "unrecorded"))}.')
    for note in qa.get('notes', []):
        lines.append(f'- QA note: {safe(note)}')
    for label in ('errors', 'warnings'):
        for item in validation.get(label, []):
            lines.append(f'- {label[:-1].capitalize()}: {safe(item)}')
    lines.extend(['', 'Signatures and signing dates remain manual. The skill does not sign or submit the form. Source originals and the blank template must remain unchanged.', ''])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'evidence', 'profile', 'answers'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--validation', help='optional prior validation JSON; fresh checks still run')
    parser.add_argument('--check-files', action='store_true')
    parser.add_argument('--template')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        manifest, evidence, profile, answers = [read_json(getattr(args, name)) for name in ('manifest', 'evidence', 'profile', 'answers')]
        validation = validate_records(manifest, evidence, profile, answers, args.check_files, args.template)
        if args.validation:
            prior = read_json(args.validation)
            # Never let stale prior pass override fresh failure or unverified bytes.
            for label in ('errors', 'warnings'):
                validation[label].extend(f'Prior check: {item}' for item in prior.get(label, []))
            if not prior.get('valid'):
                validation['valid'] = validation['export_ready'] = False
        output = Path(args.output)
        protected = input_paths(manifest, [args.manifest, args.evidence, args.profile, args.answers, args.validation, args.template])
        atomic_text(output, build_report(manifest, evidence, profile, answers, validation), protected)
        print(json.dumps({'report': str(output), 'record_checks_passed': validation['valid'], 'unresolved_fields': sum(item.get('status') not in {'supported', 'not_applicable'} for item in answers.get('answers', []))}))
        return 0 if validation['valid'] else 1
    except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError) as exc:
        print(f'Cannot build report: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
