#!/usr/bin/env python3
"""Validate evidence-to-field records. Never extracts, edits, signs, or submits a PDF.

Uses the standard library. Record consistency does not prove that a claim is true:
source interpretation, identity matching, and visual QA remain the host's work.
"""
import argparse
import hashlib
from datetime import date
import os
import tempfile
import json
from pathlib import Path
import sys

STATUSES = {'supported', 'conflict', 'missing', 'unreadable', 'not_applicable', 'manual'}
MANUAL_TYPES = {'signature', 'signing_date'}
CONSENT_TYPES = {'consent', 'declaration'}
FIELD_TYPES = {'text', 'date', 'boolean', 'choice', 'signature', 'signing_date', 'declaration', 'consent'}
HEX = set('0123456789abcdef')


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def is_hash(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def same(a, b):
    # JSON booleans and numbers must not compare equal (False != 0 here).
    return type(a) is type(b) and a == b


def read_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def guard_output(path, protected=()):
    target = Path(path).expanduser().resolve()
    if target in {Path(item).expanduser().resolve() for item in protected if item}:
        raise ValueError(f'output path collides with a protected input: {target}')
    if Path(path).exists() or Path(path).is_symlink():
        raise ValueError(f'output already exists; choose a new run/artifact path: {path}')
    return target


def atomic_text(path, content, protected=()):
    target = guard_output(path, protected)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, prefix='.' + target.name + '.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        # Hard link creation is atomic and refuses an existing target, including a symlink.
        os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_json(path, data, protected=()):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n', protected)


def input_paths(manifest, extra=()):
    protected = list(extra)
    for source in manifest.get('sources', []):
        protected.append(source.get('original_path'))
        protected.extend(item.get('path') for item in source.get('derivatives', []))
    return [item for item in protected if item]


def _index(items, key, label, errors):
    result = {}
    if not isinstance(items, list):
        errors.append(f'{label}: expected a list')
        return result
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip():
            errors.append(f'{label}: each record needs nonempty {key}')
            continue
        if item[key] in result:
            errors.append(f'{label}: duplicate {key} {item[key]}')
        result[item[key]] = item
    return result


def _locator_errors(locator, fmt, derivative=False):
    if not isinstance(locator, dict):
        return ['typed locator is required']
    kind = locator.get('kind')
    allowed = {
        'pdf': {'pdf'}, 'doc': {'word'}, 'docx': {'word'},
        'xls': {'spreadsheet'}, 'xlsx': {'spreadsheet'}, 'xlsm': {'spreadsheet'},
        'csv': {'csv'}, 'tsv': {'csv'}, 'ppt': {'slide'}, 'pptx': {'slide'},
        'eml': {'email'}, 'msg': {'email'}, 'txt': {'text'}, 'md': {'text'},
        'html': {'html'}, 'htm': {'html'}, 'png': {'image'}, 'jpg': {'image'},
        'jpeg': {'image'}, 'tif': {'image'}, 'tiff': {'image'},
    }
    issues = []
    if kind not in {'pdf', 'word', 'spreadsheet', 'csv', 'slide', 'email', 'text', 'html', 'image'}:
        return ['unknown locator kind']
    if derivative and kind != 'pdf':
        issues.append('a PDF derivative needs a PDF locator')
    elif not derivative and fmt in allowed and kind not in allowed[fmt]:
        issues.append(f'locator kind {kind} does not match original format {fmt}')
    positive = lambda x: isinstance(x, int) and not isinstance(x, bool) and x > 0
    if kind == 'pdf' and not positive(locator.get('page')):
        issues.append('PDF page must be a one-based integer')
    if kind == 'word' and not (positive(locator.get('paragraph')) or all(positive(locator.get(k)) for k in ('table', 'row', 'column')) or positive(locator.get('rendered_page'))):
        issues.append('Word locator needs paragraph, table/row/column, or verified rendered_page')
    if kind == 'word' and 'rendered_page' in locator and locator.get('rendered_page_verified') is not True:
        issues.append('Word rendered page must be verified')
    if kind == 'spreadsheet' and not (locator.get('sheet') and (locator.get('cell') or locator.get('range'))):
        issues.append('spreadsheet locator needs sheet and cell or range')
    if kind == 'csv' and not (positive(locator.get('row')) and isinstance(locator.get('column'), (str, int)) and not isinstance(locator.get('column'), bool) and str(locator.get('column')).strip()):
        issues.append('CSV locator needs one-based row and column/header')
    if kind == 'slide' and not positive(locator.get('slide')):
        issues.append('slide locator needs one-based slide')
    if kind == 'email' and not (locator.get('section') and (locator.get('message_id') or locator.get('message_id_unavailable') is True)):
        issues.append('email locator needs section and message_id, or an explicit unavailable flag')
    if kind == 'text' and not positive(locator.get('line')):
        issues.append('text locator needs one-based line')
    if kind == 'html' and not (locator.get('section') or locator.get('selector') or positive(locator.get('line'))):
        issues.append('HTML locator needs section, selector, or one-based line')
    if kind == 'image' and not (positive(locator.get('frame')) and locator.get('region')):
        issues.append('image locator needs one-based frame and region')
    return issues


def validate_records(manifest, evidence, profile, answers, check_files=False, template_path=None):
    errors, warnings = [], []
    docs = [('manifest', manifest), ('evidence', evidence), ('profile', profile), ('answers', answers)]
    for label, obj in docs:
        if not isinstance(obj, dict):
            errors.append(f'{label}: expected an object')
        elif obj.get('schema_version') != '1.0':
            errors.append(f'{label}: schema_version must be 1.0')
    if any(not isinstance(obj, dict) for _, obj in docs):
        return {'valid': False, 'export_ready': False, 'errors': errors, 'warnings': warnings, 'counts': {}}
    sources = _index(manifest.get('sources'), 'source_id', 'sources', errors)
    facts = _index(evidence.get('records'), 'evidence_id', 'evidence', errors)
    user_answers = _index(evidence.get('user_answers', []), 'answer_id', 'user_answers', errors)
    fields = _index(profile.get('logical_fields'), 'key', 'logical_fields', errors)
    decisions = _index(answers.get('answers'), 'field_key', 'answers', errors)
    if not profile.get('profile_id') or answers.get('profile_id') != profile.get('profile_id'):
        errors.append('answers.profile_id must match profile.profile_id')
    template = profile.get('template', {})
    if not isinstance(template, dict):
        template = {}
        errors.append('profile.template must be an object')
    template_hash = template.get('sha256')
    if not is_hash(template_hash) or answers.get('template_sha256') != template_hash:
        errors.append('answers.template_sha256 must match a valid profile template hash')
    if not isinstance(template.get('pages'), int) or isinstance(template.get('pages'), bool) or template['pages'] < 1:
        errors.append('profile.template.pages must be a positive integer')
    if not answers.get('subject_id') or not answers.get('matter_id'):
        errors.append('answers needs subject_id and matter_id')
    if template_path:
        try:
            if digest(template_path) != template_hash:
                errors.append('current template hash does not match profile')
        except OSError as exc:
            errors.append(f'cannot read current template: {exc}')
    derivatives = {}
    source_root = Path(manifest.get('source_root', '')).expanduser().resolve() if manifest.get('source_root') else None
    if source_root is None:
        errors.append('manifest.source_root required for source containment checks')
    for sid, source in sources.items():
        fmt = str(source.get('format', '')).lower().lstrip('.')
        if not fmt or not is_hash(source.get('sha256')):
            errors.append(f'{sid}: format and valid original sha256 required')
        if not source.get('original_path') or not source.get('relative_path'):
            errors.append(f'{sid}: original_path and relative_path required')
        if source.get('duplicate_of') and source['duplicate_of'] not in sources:
            errors.append(f'{sid}: duplicate_of references unknown source')
        if source.get('lineage', {}).get('parent_source_id') and source['lineage']['parent_source_id'] not in sources:
            errors.append(f'{sid}: unknown parent attachment source')
        route = source.get('route', {})
        if not isinstance(route, dict) or route.get('status') not in {'native', 'pdf', 'fallback_needed', 'capability_unknown', 'unsupported', 'fallback_pdf'}:
            errors.append(f'{sid}: unknown reader route')
            route = {}
        if route.get('status') == 'pdf' and fmt != 'pdf':
            errors.append(f'{sid}: native PDF route cannot be used for non-PDF original')
        status = source.get('extraction', {}).get('status')
        if status not in {'complete', 'partial', 'pending', 'duplicate', 'excluded', 'error', 'unreadable', 'unsupported'}:
            errors.append(f'{sid}: invalid extraction status')
        elif status not in {'complete', 'duplicate', 'excluded'}:
            warnings.append(f'{sid}: source extraction is {status}; coverage remains unresolved')
        source_path = Path(source.get('original_path', '')).expanduser().resolve()
        relative = Path(source.get('relative_path', ''))
        within = source_root is not None and source_path.is_relative_to(source_root) and not relative.is_absolute() and (source_root / relative).resolve() == source_path
        if not within:
            errors.append(f'{sid}: original_path/relative_path escapes or mismatches selected source_root')
        if check_files and within:
            try:
                if digest(source.get('original_path', '')) != source.get('sha256'):
                    errors.append(f'{sid}: original content hash changed')
            except (OSError, TypeError) as exc:
                errors.append(f'{sid}: cannot read original: {exc}')
        for derivative in source.get('derivatives', []):
            did = derivative.get('derivative_id')
            if not did or did in derivatives:
                errors.append(f'{sid}: duplicate or absent derivative_id')
                continue
            derivatives[did] = (sid, derivative)
            if derivative.get('format') != 'pdf' or not is_hash(derivative.get('sha256')) or not derivative.get('reason'):
                errors.append(f'{did}: PDF hash and fallback reason required')
            if not derivative.get('converter', {}).get('id') or not derivative.get('converter', {}).get('version'):
                errors.append(f'{did}: converter id and version required')
            if derivative.get('conversion_status') not in {'complete', 'partial', 'failed'}:
                errors.append(f'{did}: conversion_status required')
            elif derivative.get('conversion_status') != 'complete':
                warnings.append(f'{did}: conversion is {derivative.get("conversion_status")}')
            if check_files:
                try:
                    if digest(derivative.get('path', '')) != derivative.get('sha256'):
                        errors.append(f'{did}: derivative hash changed')
                except (OSError, TypeError) as exc:
                    errors.append(f'{did}: cannot read derivative: {exc}')
    for eid, fact in facts.items():
        source = sources.get(fact.get('source_id'))
        if source is None:
            errors.append(f'{eid}: unknown source_id')
            continue
        for key in ('field_key', 'subject_id', 'role'):
            if not isinstance(fact.get(key), str) or not fact[key].strip():
                errors.append(f'{eid}: nonempty {key} required')
        if 'value' not in fact or 'raw_value' not in fact or not fact.get('excerpt'):
            errors.append(f'{eid}: raw_value, value, and source excerpt required')
        if fact.get('status') not in {'candidate', 'accepted', 'rejected'}:
            errors.append(f'{eid}: status must be candidate, accepted, or rejected')
        if fact.get('status') == 'rejected' and not fact.get('rejection_reason'):
            errors.append(f'{eid}: rejected evidence needs rejection_reason')
        if fact.get('assertion') not in {'explicit', 'inferred', 'ambiguous'}:
            errors.append(f'{eid}: assertion must be explicit, inferred, or ambiguous')
        extraction = fact.get('extraction', {})
        if not all(extraction.get(k) for k in ('reader_id', 'reader_version', 'method')):
            errors.append(f'{eid}: extraction reader_id, reader_version, and method required')
        did = fact.get('derivative_id')
        derivative = derivatives.get(did) if did else None
        if did and (derivative is None or derivative[0] != fact.get('source_id')):
            errors.append(f'{eid}: derivative does not belong to original source')
        if did and derivative and derivative[1].get('conversion_status') == 'failed':
            errors.append(f'{eid}: failed conversion cannot supply evidence')
        if did and not fact.get('original_locator'):
            warnings.append(f'{eid}: fallback original locator unavailable; cite original file plus derivative page')
        loc_errors = _locator_errors(fact.get('locator'), str(source.get('format', '')).lower().lstrip('.'), bool(did))
        errors.extend(f'{eid}: {issue}' for issue in loc_errors)
        if did and fact.get('original_locator'):
            errors.extend(f'{eid}: {issue}' for issue in _locator_errors(fact['original_locator'], source.get('format')))
        if not did and source.get('format') != 'pdf' and fact.get('locator', {}).get('kind') == 'pdf':
            errors.append(f'{eid}: non-PDF source page locator requires tracked PDF derivative')
        if fact.get('formula_provenance') == 'recalculated' and not fact.get('transformations'):
            errors.append(f'{eid}: recalculated formula needs a recorded transformation')
    for uid, item in user_answers.items():
        if item.get('explicit') is not True or item.get('source') != 'user' or not item.get('provided_by'):
            errors.append(f'{uid}: explicit user source and provided_by required')
        if not all(item.get(k) for k in ('field_key', 'subject_id', 'role')) or 'value' not in item:
            errors.append(f'{uid}: field_key, subject_id, role, value required')
    for key in decisions.keys() - fields.keys():
        errors.append(f'{key}: answer has no logical field in profile')
    for key in fields.keys() - decisions.keys():
        errors.append(f'{key}: logical field is unaccounted for')
    status_counts = {status: 0 for status in sorted(STATUSES)}
    fill_count = 0
    roles = {field.get('role') for field in fields.values()}
    bindings = answers.get('subject_bindings', {})
    if not isinstance(bindings, dict):
        errors.append('answers.subject_bindings must be a role-to-subject object')
        bindings = {}
    mapping_issues = []
    for key, field in fields.items():
        if field.get('type') not in FIELD_TYPES or not field.get('role'):
            errors.append(f'{key}: profile needs a known type and role')
        decision = decisions.get(key)
        if decision is None:
            continue
        status = decision.get('status')
        if status not in STATUSES:
            errors.append(f'{key}: unknown answer status')
            continue
        status_counts[status] += 1
        if decision.get('role') != field.get('role'):
            errors.append(f'{key}: answer role does not match profile')
        expected_subject = field.get('subject_id') or bindings.get(field.get('role'))
        if not expected_subject and len(roles) == 1:
            expected_subject = answers.get('subject_id')
        if not expected_subject:
            errors.append(f'{key}: multi-role answer map needs subject_bindings for {field.get("role")}')
        if decision.get('subject_id') != expected_subject:
            errors.append(f'{key}: answer subject does not match profile/matter')
        conditions = field.get('conditions', {})
        if not isinstance(conditions, dict):
            errors.append(f'{key}: conditions must be a field-to-value object')
            conditions = {}
        applicable, unknown = True, False
        for selector, expected in conditions.items():
            parent = decisions.get(selector)
            if selector not in fields:
                errors.append(f'{key}: condition references unknown field {selector}')
            if not parent or parent.get('status') != 'supported':
                unknown = True
            elif not same(parent.get('value'), expected):
                applicable = False
        if not applicable and status != 'not_applicable':
            errors.append(f'{key}: inactive branch must be not_applicable')
        if unknown and applicable and status in {'supported', 'not_applicable'}:
            errors.append(f'{key}: unresolved branch cannot be filled or declared inapplicable')
        if status == 'not_applicable' and applicable and not unknown and not decision.get('reason'):
            errors.append(f'{key}: not_applicable requires a documented reason or inactive branch')
        if status != 'supported':
            if 'value' in decision and decision['value'] is not None:
                errors.append(f'{key}: unresolved/manual/inactive answer must not carry a fill value')
            continue
        fill_count += 1
        value = decision.get('value')
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f'{key}: supported answer needs a nonempty value')
        if field.get('type') in MANUAL_TYPES:
            errors.append(f'{key}: signatures and signing dates must remain manual; automatic signing is forbidden')
        if field.get('manual') is True and field.get('type') not in CONSENT_TYPES and not decision.get('user_answer_ids'):
            errors.append(f'{key}: manual decision needs an explicit user answer')
        if field.get('type') in {'text', 'date'} and not isinstance(value, str):
            errors.append(f'{key}: text/date field needs a string')
        if field.get('type') == 'date' and isinstance(value, str):
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError('not canonical')
            except ValueError:
                errors.append(f'{key}: date must be an unambiguous valid YYYY-MM-DD string')
        if field.get('type') == 'boolean' and type(value) is not bool:
            errors.append(f'{key}: boolean field needs a JSON boolean')
        if field.get('type') == 'choice' and (not field.get('options') or not any(same(value, option) for option in field['options'])):
            errors.append(f'{key}: value is not an allowed choice')
        if isinstance(value, str) and field.get('max_length') is not None and len(value) > field['max_length']:
            errors.append(f'{key}: value exceeds max_length; do not truncate silently')
        eids, uids = decision.get('evidence_ids', []), decision.get('user_answer_ids', [])
        if not isinstance(eids, list) or not isinstance(uids, list):
            errors.append(f'{key}: evidence_ids and user_answer_ids must be lists')
            continue
        if not eids and not uids:
            errors.append(f'{key}: supported answer has no evidence or explicit user answer')
        selected = []
        for rid, pool, label in [(rid, facts, 'evidence') for rid in eids] + [(rid, user_answers, 'user answer') for rid in uids]:
            item = pool.get(rid)
            if item is None:
                errors.append(f'{key}: unknown {label} {rid}')
                continue
            if any(item.get(attr) != decision.get(attr) for attr in ('field_key', 'subject_id', 'role')):
                errors.append(f'{key}: {label} {rid} belongs to another field/person/role')
            if not same(item.get('value'), value):
                errors.append(f'{key}: answer differs from normalized {label} {rid}')
            if label == 'evidence':
                if item.get('status') != 'accepted':
                    errors.append(f'{key}: selected evidence {rid} must be accepted after source review')
                if item.get('assertion') != 'explicit':
                    errors.append(f'{key}: inferred/ambiguous evidence {rid} cannot authorize filling')
            selected.append(item)
        if field.get('type') in CONSENT_TYPES and not any(user_answers.get(uid, {}).get('confirmation_scope') == field['type'] and user_answers.get(uid, {}).get('appropriate_person_confirmed') is True for uid in uids):
            errors.append(f'{key}: {field["type"]} needs explicit scoped user confirmation from appropriate person')
        competing = [eid for eid, item in facts.items() if item.get('field_key') == key and item.get('subject_id') == decision.get('subject_id') and item.get('role') == decision.get('role') and item.get('status') != 'rejected' and not same(item.get('value'), value)]
        if competing and not (uids and decision.get('resolution_reason')):
            errors.append(f'{key}: unresolved competing evidence {", ".join(competing)}')
        for mapping in field.get('mappings', []):
            if mapping.get('kind') != 'fillable':
                mapping_issues.append(f'{key}: annotation data must be prepared by PDF skill')
            if mapping.get('verified') is not True or mapping.get('unique') is not True:
                mapping_issues.append(f'{key}: mapping has not been verified unique')
            if not mapping.get('field_id') or not isinstance(mapping.get('page'), int) or not (1 <= mapping['page'] <= template.get('pages', 0)):
                mapping_issues.append(f'{key}: mapping needs valid field_id/page')
        if not field.get('mappings'):
            mapping_issues.append(f'{key}: no verified PDF mapping')
    capacity_rules = profile.get('capacity_rules', [])
    if isinstance(capacity_rules, dict):
        warnings.append('profile capacity rules are descriptive; host must review repeated-person capacity and overflow')
        capacity_rules = []
    for rule in capacity_rules:
        if not isinstance(rule, dict) or not isinstance(rule.get('field_keys'), list) or not isinstance(rule.get('max_supported'), int):
            errors.append('capacity_rules needs field_keys and integer max_supported')
            continue
        occupied = sum(decisions.get(key, {}).get('status') == 'supported' for key in rule['field_keys'])
        if occupied > rule['max_supported']:
            errors.append(f'{rule.get("name", "capacity")}: overflow requires review, never drop entries')
    qa = answers.get('qa', {})
    if not isinstance(qa, dict):
        errors.append('answers.qa must be an object')
        qa = {}
    for name in ('readback', 'rendered', 'originals'):
        if qa.get(name) not in {'pending', 'pass', 'fail', 'not_applicable'}:
            errors.append(f'qa.{name}: expected pending/pass/fail/not_applicable')
        elif qa.get(name) != 'pass':
            warnings.append(f'qa.{name}: {qa.get(name)}; draft is not fully verified')
    readiness = profile.get('readiness', {}).get('status')
    if readiness != 'verified':
        warnings.append(f'profile readiness is {readiness or "missing"}; filling/export is blocked')
    warnings.extend(mapping_issues)
    if not check_files:
        warnings.append('current original hashes were not checked')
    if not template_path:
        warnings.append('current template bytes were not checked')
    return {
        'schema_version': '1.0', 'valid': not errors,
        'export_ready': not errors and readiness == 'verified' and not mapping_issues and check_files and bool(template_path),
        'errors': errors, 'warnings': warnings,
        'counts': {'sources': len(sources), 'evidence': len(facts), 'fields': len(fields), 'supported': fill_count, 'statuses': status_counts},
        'limits': ['Consistency checks do not prove factual accuracy, authority, or visual legibility.', 'QA flags are recorded claims; independently inspect PDF skill readback and rendered pages.'],
    }


def export_values(profile, answers, result):
    if not result.get('valid') or not result.get('export_ready'):
        raise ValueError('export refused: validation, current hashes, template, and verified unique fillable mappings are required')
    fields = {item['key']: item for item in profile['logical_fields']}
    output, used = [], set()
    for item in answers['answers']:
        if item['status'] != 'supported':
            continue
        field = fields[item['field_key']]
        for mapping in field['mappings']:
            identity = (mapping['field_id'], mapping['page'])
            if identity in used:
                raise ValueError(f'export refused: repeated physical field {identity}')
            used.add(identity)
            value = item['value']
            export_map = mapping.get('export_values', {})
            if type(value) is bool or field['type'] == 'choice' or export_map:
                token = ('true' if value else 'false') if type(value) is bool else str(value)
                if token not in export_map:
                    raise ValueError(f'{field["key"]}: verified PDF export_values missing for {token}')
                value = export_map[token]
            output.append({'field_id': mapping['field_id'], 'page': mapping['page'], 'value': value})
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'evidence', 'profile', 'answers'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check-files', action='store_true', help='verify current original and derivative hashes')
    parser.add_argument('--template', help='current blank PDF; hash checked against exact profile')
    parser.add_argument('--output', help='write validation JSON')
    parser.add_argument('--export-values', help='write official PDF skill fillable values JSON only after safe validation')
    args = parser.parse_args(argv)
    try:
        manifest, evidence, profile, answers = [read_json(getattr(args, name)) for name in ('manifest', 'evidence', 'profile', 'answers')]
        protected = input_paths(manifest, [args.manifest, args.evidence, args.profile, args.answers, args.template])
        for output in (args.output, args.export_values):
            if output:
                guard_output(output, protected)
        if args.output and args.export_values and Path(args.output).resolve() == Path(args.export_values).resolve():
            raise ValueError('validation and export outputs must be distinct')
        result = validate_records(manifest, evidence, profile, answers, args.check_files or bool(args.export_values), args.template)
        if args.export_values:
            try:
                values = export_values(profile, answers, result)
                atomic_json(args.export_values, values, protected)
            except (ValueError, KeyError, TypeError) as exc:
                result['valid'] = False
                result['export_ready'] = False
                result['errors'].append(str(exc))
        if args.output:
            atomic_json(args.output, result, protected)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['valid'] else 1
    except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
        print(f'Invalid input: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
