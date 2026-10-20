"""Safety gates and read-only PDF probing; optional unchanged-dependency roundtrip.

Set PDF_SKILL_DIR to the separately installed Anthropic PDF skill to exercise its
actual filler. This package intentionally does not bundle or replace that code.
Everything runs locally without opening applications, browser tabs or dialogs.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("probe_pdf", ROOT / "scripts/probe_pdf.py")
probe_pdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe_pdf)


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads((ROOT / "references/form-956-08-22.json").read_text())
        cls.diagnostics = json.loads((ROOT / "references" / cls.profile["widget_diagnostics"]["path"]).read_text())

    def test_sample_cannot_be_declared_ready_from_widget_count(self):
        p = self.profile
        self.assertEqual(p["readiness"]["status"], "blocked")
        self.assertEqual(p["template"]["sha256"], "bd4b0336994128f71cdb8b6b23756c46404dcc01a0a665893e344c830932e815")
        self.assertEqual(p["inspection"]["canonical_field_count"], 1)
        self.assertEqual(p["inspection"]["widget_count"], 129)
        self.assertEqual(p["inspection"]["synthetic_fill"]["status"], "failed")
        self.assertTrue(all(not m["verified"] for f in p["logical_fields"] for m in f["mappings"]))

    def test_all_observed_widgets_have_one_logical_owner(self):
        fields = self.profile["logical_fields"]
        self.assertEqual(len({f["key"] for f in fields}), len(fields))
        observed = {w["widget_id"] for w in self.diagnostics["widgets"]}
        mapped = [m["widget_id"] for f in fields for m in f["mappings"]]
        self.assertEqual(len(mapped), len(set(mapped)))
        self.assertEqual(set(mapped), observed)

    def test_branches_and_manual_areas_are_accounted_for(self):
        p = self.profile
        fields = {f["key"]: f for f in p["logical_fields"]}
        for branch in p["branches"]:
            field = fields[branch["selector_field"]]
            self.assertEqual(set(branch["options"]), set(field["options"]))
        self.assertEqual(p["repeated_clients"]["slots"], 5)
        self.assertEqual(p["capacity_rules"][0]["max_supported"], 5)
        self.assertEqual(p["repeated_clients"]["slot_roles"], [f"additional_client_{i}" for i in range(1, 6)])
        self.assertEqual(sum(f["question"] == 14 for f in fields.values()), 10)
        for field in fields.values():
            for dependency in field.get("conditions", {}):
                self.assertIn(dependency, fields)
            if field["type"] in {"signature", "signing_date", "declaration", "consent"}:
                self.assertTrue(field["manual"])
            if field["type"] == "signature":
                self.assertEqual(field["mappings"], [])

    def test_template_asset_if_packaged_stays_unchanged(self):
        asset = ROOT / self.profile["template"].get("asset", "assets/forms/form-956-08-22.pdf")
        if not asset.exists():
            self.skipTest("Sample template not packaged yet")
        import hashlib
        self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), self.profile["template"]["sha256"])

    def test_widget_diagnostics_preserved_hash(self):
        import hashlib
        reference = self.profile["widget_diagnostics"]
        diagnostics = ROOT / "references" / reference["path"]
        self.assertEqual(hashlib.sha256(diagnostics.read_bytes()).hexdigest(), reference["sha256"])
        self.assertEqual(self.diagnostics["template_sha256"], self.profile["template"]["sha256"])

    def test_bundled_profile_schema_and_unresolved_decisions(self):
        """Blocked PDF compatibility is not confused with invalid record shape."""
        validator_spec = importlib.util.spec_from_file_location("profile_validator", ROOT / "scripts/validate_records.py")
        validator = importlib.util.module_from_spec(validator_spec)
        validator_spec.loader.exec_module(validator)
        roles = {field["role"] for field in self.profile["logical_fields"]}
        bindings = {role: "synthetic:" + role for role in roles}
        manifest = {"schema_version": "1.0", "source_root": str(ROOT), "sources": []}
        evidence = {"schema_version": "1.0", "records": [], "user_answers": []}
        answers = {
            "schema_version": "1.0", "profile_id": self.profile["profile_id"],
            "template_sha256": self.profile["template"]["sha256"],
            "subject_id": bindings["client"], "matter_id": "synthetic:unresolved",
            "subject_bindings": bindings,
            "answers": [{"field_key": field["key"], "subject_id": bindings[field["role"]],
                         "role": field["role"], "status": "manual" if field["manual"] else "missing",
                         "evidence_ids": [], "user_answer_ids": [],
                         "reason": "Synthetic all-unresolved profile compatibility check"}
                        for field in self.profile["logical_fields"]],
            "qa": {"readback": "pending", "rendered": "pending", "originals": "pending", "notes": []},
        }
        result = validator.validate_records(manifest, evidence, self.profile, answers)
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["export_ready"])
        self.assertEqual(result["counts"]["fields"], 107)
        try:
            import jsonschema
        except ImportError:
            return  # Operational record checks above always run; schema package is optional.
        for schema_name, data in [("form-profile", self.profile), ("manifest", manifest), ("evidence", evidence), ("answers", answers)]:
            schema = json.loads((ROOT / f"assets/schemas/{schema_name}.schema.json").read_text())
            jsonschema.Draft202012Validator(schema).validate(data)


class ProbeTests(unittest.TestCase):
    def make_clean_fixture(self, path):
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            self.skipTest("reportlab is optional; install the PDF dependency runtime")
        c = canvas.Canvas(str(path), pagesize=(400, 300))
        c.drawString(30, 250, "SYNTHETIC TEST ONLY")
        c.drawString(30, 212, "Client name:")
        c.acroForm.textfield(name="client_name", x=110, y=200, width=240, height=24, borderWidth=1)
        c.drawString(50, 170, "Authority confirmed (synthetic)")
        c.acroForm.checkbox(name="authority", x=30, y=165, size=14, buttonStyle="check", checked=False)
        c.showPage()
        c.save()

    def test_clean_inventory_and_preserved_hash(self):
        try:
            import pypdf  # noqa
        except ImportError:
            self.skipTest("pypdf is supplied by the PDF dependency runtime")
        with tempfile.TemporaryDirectory() as temp:
            pdf = Path(temp) / "blank.pdf"
            self.make_clean_fixture(pdf)
            original = pdf.read_bytes()
            result = probe_pdf.probe(pdf)
            self.assertEqual(result["pages"], 1)
            self.assertEqual(result["canonical_field_count"], 2)
            self.assertEqual(result["widget_count"], 2)
            self.assertEqual(result["widget_names_missing_from_canonical_inventory"], [])
            self.assertEqual(len(result["structural_signature"]), 64)
            self.assertEqual(pdf.read_bytes(), original)
            box = next(w for w in result["widgets"] if w["field_id"] == "authority")
            self.assertEqual(set(box["export_values"]), {"/Off", "/Yes"})

    def test_probe_output_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blank.pdf"
            path.write_bytes(b"preserve me")
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/probe_pdf.py"), str(path), str(path)], capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(path.read_bytes(), b"preserve me")

    def test_separately_installed_filler_roundtrip(self):
        pdf_skill = os.environ.get("PDF_SKILL_DIR")
        if not pdf_skill:
            self.skipTest("Set PDF_SKILL_DIR for unchanged upstream filler integration")
        dependency = Path(pdf_skill)
        required = ["check_fillable_fields.py", "extract_form_field_info.py", "fill_fillable_fields.py", "convert_pdf_to_images.py"]
        self.assertTrue(all((dependency / "scripts" / name).is_file() for name in required))
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            blank, output = work / "blank.pdf", work / "filled.pdf"
            self.make_clean_fixture(blank)
            original = blank.read_bytes()
            def run_script(name, *args):
                result = subprocess.run([sys.executable, str(dependency / "scripts" / name), *map(str, args)], capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result
            run_script("check_fillable_fields.py", blank)
            run_script("extract_form_field_info.py", blank, work / "fields.json")
            info = json.loads((work / "fields.json").read_text())
            box = next(f for f in info if f["field_id"] == "authority")
            values = [{"field_id": "client_name", "page": 1, "value": "SYNTHETIC ALPHA", "description": "Synthetic name"},
                      {"field_id": "authority", "page": 1, "value": box["checked_value"], "description": "Synthetic authority choice"}]
            (work / "values.json").write_text(json.dumps(values))
            run_script("fill_fillable_fields.py", blank, work / "values.json", output)
            from pypdf import PdfReader
            readback = PdfReader(output).get_fields()
            self.assertEqual(str(readback["client_name"]["/V"]), "SYNTHETIC ALPHA")
            self.assertEqual(str(readback["authority"]["/V"]), box["checked_value"])
            render = work / "render"
            render.mkdir()
            run_script("convert_pdf_to_images.py", output, render)
            from PIL import Image
            with Image.open(render / "page_1.png") as img:
                self.assertGreater(img.width, 100)
                self.assertGreater(img.height, 100)
            self.assertEqual(blank.read_bytes(), original)
            # Automated render/readback is not a replacement for visual inspection.


if __name__ == "__main__":
    unittest.main()
