"""Synthetic consistency/safety tests; no source interpretation or PDF-fill claims."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from validate_records import validate_records, export_values, atomic_json, input_paths
from build_review_report import build_report


def fixture(root):
    root = Path(root)
    sources = root / 'sources'
    sources.mkdir()
    original = sources / 'facts.csv'
    original.write_text('name,has_dependants\nAlex Test,false\n', encoding='utf-8')
    template = root / 'blank.pdf'
    template.write_bytes(b'synthetic template bytes: validator does not parse PDFs')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'schema_version': '1.0', 'source_root': str(sources), 'sources': [{
        'source_id': 's1', 'relative_path': 'facts.csv', 'original_path': str(original), 'format': 'csv',
        'sha256': sha(original), 'size_bytes': original.stat().st_size,
        'route': {'status': 'native', 'reader_id': 'spreadsheets', 'reader_version': 'test'},
        'extraction': {'status': 'complete', 'coverage': {'rows': 2, 'columns': 2}},
    }]}
    profile = {'schema_version': '1.0', 'profile_id': 'synthetic', 'profile_version': '1.0',
        'template': {'sha256': sha(template), 'pages': 1},
        'readiness': {'status': 'verified', 'issues': []}, 'logical_fields': [{
            'key': 'client.name', 'role': 'client', 'type': 'text', 'required': True, 'manual': False,
            'mappings': [{'kind': 'fillable', 'field_id': 'Name', 'page': 1, 'verified': True, 'unique': True}],
        }]}
    evidence = {'schema_version': '1.0', 'records': [{
        'evidence_id': 'e1', 'source_id': 's1', 'field_key': 'client.name', 'subject_id': 'person-alex',
        'role': 'client', 'raw_value': 'Alex Test', 'value': 'Alex Test', 'locator': {'kind': 'csv', 'row': 2, 'column': 'name'},
        'excerpt': 'Alex Test', 'extraction': {'reader_id': 'spreadsheets', 'reader_version': 'test', 'method': 'native'},
        'status': 'accepted', 'assertion': 'explicit',
    }], 'user_answers': []}
    answers = {'schema_version': '1.0', 'profile_id': 'synthetic', 'template_sha256': sha(template),
        'subject_id': 'person-alex', 'matter_id': 'test-matter', 'answers': [{
            'field_key': 'client.name', 'subject_id': 'person-alex', 'role': 'client', 'status': 'supported',
            'value': 'Alex Test', 'evidence_ids': ['e1'], 'user_answer_ids': [],
        }], 'qa': {'readback': 'pending', 'rendered': 'pending', 'originals': 'pass', 'notes': []}}
    return manifest, evidence, profile, answers, template


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.m, self.e, self.p, self.a, self.template = fixture(self.temp.name)

    def validate(self, **kwargs):
        return validate_records(self.m, self.e, self.p, self.a, **kwargs)

    def assertError(self, text):
        result = self.validate()
        self.assertFalse(result['valid'], result)
        self.assertTrue(any(text in error for error in result['errors']), result)

    def test_native_csv_positive_and_exact_export(self):
        result = self.validate(check_files=True, template_path=self.template)
        self.assertTrue(result['valid'], result)
        self.assertTrue(result['export_ready'], result)
        self.assertEqual(export_values(self.p, self.a, result), [{'field_id': 'Name', 'page': 1, 'value': 'Alex Test'}])

    def test_wrong_person_is_rejected(self):
        self.e['records'][0]['subject_id'] = 'different-person'
        self.assertError('another field/person/role')

    def test_wrong_field_is_rejected(self):
        self.e['records'][0]['field_key'] = 'representative.name'
        self.assertError('another field/person/role')

    def test_wrong_role_is_rejected(self):
        self.e['records'][0]['role'] = 'representative'
        self.assertError('another field/person/role')

    def test_multirole_needs_subject_bindings(self):
        extra = copy.deepcopy(self.p['logical_fields'][0])
        extra.update(key='representative.name', role='representative')
        self.p['logical_fields'].append(extra)
        self.a['answers'].append({'field_key': 'representative.name', 'subject_id': 'person-rep', 'role': 'representative', 'status': 'missing'})
        self.assertError('subject_bindings')
        self.a['subject_bindings'] = {'client': 'person-alex', 'representative': 'person-rep'}
        self.assertTrue(self.validate()['valid'])
        self.a['answers'][1]['subject_id'] = 'person-alex'
        self.assertError('subject does not match')

    def test_supported_value_must_equal_evidence(self):
        self.a['answers'][0]['value'] = 'Different Test'
        self.assertError('differs from normalized')

    def test_missing_cannot_become_false(self):
        self.p['logical_fields'][0]['type'] = 'boolean'
        self.a['answers'][0]['value'] = False
        self.a['answers'][0]['evidence_ids'] = []
        self.assertError('no evidence')

    def test_explicit_false_supported_and_exported_with_verified_token(self):
        self.p['logical_fields'][0]['type'] = 'boolean'
        self.p['logical_fields'][0]['mappings'][0]['export_values'] = {'true': '/Yes', 'false': '/No'}
        self.e['records'][0].update(raw_value='No', value=False, excerpt='has_dependants: false')
        self.a['answers'][0]['value'] = False
        result = self.validate(check_files=True, template_path=self.template)
        self.assertTrue(result['valid'], result)
        self.assertEqual(export_values(self.p, self.a, result)[0]['value'], '/No')

    def test_false_and_zero_not_equal(self):
        self.a['answers'][0]['value'] = False
        self.e['records'][0]['value'] = 0
        self.assertError('differs from normalized')

    def test_inference_cannot_fill(self):
        self.e['records'][0]['assertion'] = 'inferred'
        self.assertError('inferred/ambiguous')

    def test_conflict_cannot_silently_fill(self):
        other = copy.deepcopy(self.e['records'][0])
        other.update(evidence_id='e2', value='Alex Other', raw_value='Alex Other')
        self.e['records'].append(other)
        self.assertError('competing evidence')
        self.e['records'][1].update(status='rejected', rejection_reason='Different person in same source, verified against identity section.')
        self.assertTrue(self.validate()['valid'])

    def test_unresolved_fields_cannot_carry_values(self):
        self.a['answers'][0]['status'] = 'conflict'
        self.assertError('must not carry a fill value')

    def test_every_field_accounted(self):
        self.a['answers'] = []
        self.assertError('unaccounted')

    def test_signature_and_signing_date_not_exported(self):
        for kind in ('signature', 'signing_date'):
            self.p['logical_fields'][0]['type'] = kind
            self.assertError('automatic signing is forbidden')

    def test_consent_requires_scoped_appropriate_user(self):
        self.p['logical_fields'][0]['type'] = 'consent'
        self.assertError('explicit scoped user confirmation')
        self.e['user_answers'] = [{'answer_id': 'u1', 'field_key': 'client.name', 'subject_id': 'person-alex', 'role': 'client', 'value': 'Alex Test', 'explicit': True, 'source': 'user', 'provided_by': 'Alex Test', 'confirmation_scope': 'consent', 'appropriate_person_confirmed': True}]
        self.a['answers'][0]['user_answer_ids'] = ['u1']
        self.assertTrue(self.validate()['valid'])

    def test_manual_choice_permits_explicit_decision(self):
        self.p['logical_fields'][0].update(type='choice', manual=True, options=['Alex Test'])
        self.assertError('manual decision needs')
        self.e['user_answers'] = [{'answer_id': 'u1', 'field_key': 'client.name', 'subject_id': 'person-alex', 'role': 'client', 'value': 'Alex Test', 'explicit': True, 'source': 'user', 'provided_by': 'Alex Test'}]
        self.a['answers'][0]['user_answer_ids'] = ['u1']
        self.assertTrue(self.validate()['valid'])

    def test_unknown_source_and_wrong_locator(self):
        self.e['records'][0]['source_id'] = 'unknown'
        self.assertError('unknown source_id')
        self.e['records'][0]['source_id'] = 's1'
        self.e['records'][0]['locator'] = {'kind': 'pdf', 'page': 1}
        self.assertError('requires tracked PDF derivative')

    def test_native_word_and_spreadsheet_locators(self):
        for fmt, locator in [('docx', {'kind': 'word', 'table': 1, 'row': 2, 'column': 1}), ('xlsx', {'kind': 'spreadsheet', 'sheet': 'Identity', 'cell': 'B2'})]:
            self.m['sources'][0]['format'] = fmt
            self.e['records'][0]['locator'] = locator
            self.assertTrue(self.validate()['valid'])
        self.e['records'][0]['locator'] = {'kind': 'spreadsheet', 'page': 1}
        self.assertError('sheet and cell')

    def test_tracked_fallback(self):
        self.m['sources'][0]['format'] = 'unknown'
        self.m['sources'][0]['route'] = {'status': 'fallback_pdf', 'reason': 'No native reader'}
        self.m['sources'][0]['derivatives'] = [{'derivative_id': 'd1', 'format': 'pdf', 'path': str(self.template), 'sha256': self.p['template']['sha256'], 'reason': 'No native reader', 'converter': {'id': 'test-converter', 'version': '1'}, 'conversion_status': 'complete', 'limitations': []}]
        self.e['records'][0].update(derivative_id='d1', locator={'kind': 'pdf', 'page': 1})
        self.assertTrue(self.validate()['valid'])
        self.m['sources'][0]['derivatives'][0]['conversion_status'] = 'failed'
        self.assertError('failed conversion')

    def test_inactive_branch_cannot_fill(self):
        self.p['logical_fields'][0]['conditions'] = {'client.name': 'Different'}
        self.assertError('inactive branch')

    def test_unresolved_branch_does_not_become_inapplicable(self):
        selector = copy.deepcopy(self.p['logical_fields'][0])
        selector.update(key='action')
        self.p['logical_fields'].append(selector)
        self.a['answers'].append({'field_key': 'action', 'subject_id': 'person-alex', 'role': 'client', 'status': 'missing'})
        self.p['logical_fields'][0]['conditions'] = {'action': 'new'}
        self.assertError('unresolved branch')

    def test_dates_and_text_types(self):
        self.p['logical_fields'][0]['type'] = 'date'
        self.assertError('valid YYYY-MM-DD')
        self.e['records'][0]['value'] = self.a['answers'][0]['value'] = '2024-02-29'
        self.assertTrue(self.validate()['valid'])
        self.e['records'][0]['value'] = self.a['answers'][0]['value'] = '2023-02-29'
        self.assertError('valid YYYY-MM-DD')

    def test_changed_template_blocks(self):
        self.template.write_bytes(b'changed')
        result = self.validate(check_files=True, template_path=self.template)
        self.assertFalse(result['valid'])
        self.assertIn('current template hash does not match profile', result['errors'])

    def test_changed_source_blocks(self):
        Path(self.m['sources'][0]['original_path']).write_text('changed')
        result = self.validate(check_files=True, template_path=self.template)
        self.assertFalse(result['valid'])
        self.assertTrue(any('original content hash changed' in error for error in result['errors']))

    def test_source_escape_blocks_before_reading(self):
        self.m['sources'][0].update(original_path='/etc/passwd', relative_path='../../etc/passwd')
        result = self.validate(check_files=True)
        self.assertFalse(result['valid'])
        self.assertTrue(any('escapes or mismatches' in error for error in result['errors']))

    def test_profile_unverified_export_denied(self):
        self.p['readiness']['status'] = 'blocked'
        result = self.validate(check_files=True, template_path=self.template)
        self.assertTrue(result['valid'])
        self.assertFalse(result['export_ready'])
        with self.assertRaises(ValueError):
            export_values(self.p, self.a, result)

    def test_missing_boolean_token_and_duplicate_mapping_export_denied(self):
        self.p['logical_fields'][0]['type'] = 'boolean'
        self.e['records'][0]['value'] = self.a['answers'][0]['value'] = False
        result = self.validate(check_files=True, template_path=self.template)
        with self.assertRaises(ValueError):
            export_values(self.p, self.a, result)
        self.p['logical_fields'][0]['mappings'][0]['export_values'] = {'false': '/No'}
        self.p['logical_fields'][0]['mappings'].append(copy.deepcopy(self.p['logical_fields'][0]['mappings'][0]))
        result = self.validate(check_files=True, template_path=self.template)
        with self.assertRaises(ValueError):
            export_values(self.p, self.a, result)

    def test_choice_semantics_need_export_mapping(self):
        self.p['logical_fields'][0].update(type='choice', options=['Alex Test'])
        result = self.validate(check_files=True, template_path=self.template)
        with self.assertRaises(ValueError):
            export_values(self.p, self.a, result)
        self.p['logical_fields'][0]['mappings'][0]['export_values'] = {'Alex Test': '/Option1'}
        self.assertEqual(export_values(self.p, self.a, result)[0]['value'], '/Option1')

    def test_output_refuses_inputs_existing_and_derivative(self):
        source = Path(self.m['sources'][0]['original_path'])
        before = source.read_bytes()
        for target in (source, self.template):
            with self.assertRaises(ValueError):
                atomic_json(target, {}, input_paths(self.m, [self.template]))
        self.assertEqual(source.read_bytes(), before)
        target = Path(self.temp.name) / 'result.json'
        atomic_json(target, {'valid': True})
        with self.assertRaises(ValueError):
            atomic_json(target, {'valid': False})
        self.assertEqual(json.loads(target.read_text()), {'valid': True})

    def test_report_qa_pass_never_hides_blocked_profile_or_required_gap(self):
        self.a['qa'].update(readback='pass', rendered='pass', originals='pass')
        self.p['readiness']['status'] = 'blocked'
        report = build_report(self.m, self.e, self.p, self.a, self.validate())
        self.assertIn('review required; draft is not fully verified', report)
        self.p['readiness']['status'] = 'verified'
        self.a['answers'][0].pop('value')
        self.a['answers'][0].update(status='missing', evidence_ids=[])
        report = build_report(self.m, self.e, self.p, self.a, self.validate())
        self.assertIn('review required; draft is not fully verified', report)
        self.assertIn('facts.csv', report)
        self.assertIn('missing', report)


if __name__ == '__main__':
    unittest.main()
