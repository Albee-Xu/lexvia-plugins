"""Synthetic intake/conversion tests. No UI surfaces or real client documents."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import inventory
import convert_fallbacks


def registry(*readers, discovery="complete"):
    return {"discovery": discovery, "readers": list(readers)}


def reader(name, formats, available=True, headless=True):
    return {"id": name, "formats": formats, "version": "synthetic-1", "available": available, "headless": headless}


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "sources"
        self.source.mkdir()
        self.work = self.root / "work"

    def source_file(self, name, content=b"synthetic evidence"):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_no_registry_means_unknown_not_missing(self):
        self.source_file("client.docx")
        result = inventory.build_inventory(self.source)
        self.assertEqual(result["sources"][0]["route"]["status"], "capability_unknown")

    def test_partial_registry_preserves_undiscovered_formats(self):
        self.source_file("client.docx")
        result = inventory.build_inventory(self.source, registry(reader("text", ["txt"]), discovery="partial"))
        self.assertEqual(result["sources"][0]["route"]["status"], "capability_unknown")

    def test_native_first_and_only_missing_format_falls_back(self):
        self.source_file("a.docx")
        self.source_file("b.xlsx", b"spreadsheet placeholder")
        result = inventory.build_inventory(self.source, registry(reader("documents", ["docx"])))
        statuses = {r["format"]: r["route"]["status"] for r in result["sources"]}
        self.assertEqual(statuses, {"docx": "native", "xlsx": "fallback_needed"})

    def test_ui_capability_is_never_selected(self):
        route = inventory.choose_route("docx", registry(reader("ui-reader", ["docx"], headless=False)))
        self.assertEqual(route["status"], "fallback_needed")
        route = inventory.choose_route("docx", registry({"id": "unknown-mode", "formats": ["docx"], "available": True}))
        self.assertEqual(route["status"], "capability_unknown")

    def test_pdf_needs_explicit_anthropic_dependency(self):
        self.assertEqual(inventory.choose_route("pdf", registry(reader("other-pdf", ["pdf"])))["status"], "unsupported")
        self.assertEqual(inventory.choose_route("pdf", registry(reader("anthropic-pdf", ["pdf"])))["status"], "pdf")

    def test_explicit_missing_reader_is_enough_in_partial_discovery(self):
        route = inventory.choose_route("docx", registry(reader("documents", ["docx"], available=False), discovery="partial"))
        self.assertEqual(route["status"], "fallback_needed")

    def test_duplicates_keep_locations_and_stable_unique_source_ids(self):
        first = self.source_file("a.txt")
        self.source_file("sub/b.txt", first.read_bytes())
        manifest = inventory.build_inventory(self.source)
        again = inventory.build_inventory(self.source)
        a, b = manifest["sources"]
        self.assertNotEqual(a["source_id"], b["source_id"])
        self.assertEqual(a["content_id"], b["content_id"])
        self.assertEqual(b["duplicate_of"], a["source_id"])
        self.assertEqual(b["extraction"]["status"], "duplicate")
        self.assertEqual([r["source_id"] for r in manifest["sources"]], [r["source_id"] for r in again["sources"]])

    def test_work_outputs_outside_symlinks_and_directory_symlinks_are_excluded(self):
        self.source_file("good.txt")
        inside_work = self.source / "work"
        inside_work.mkdir()
        (inside_work / "generated.pdf").write_bytes(b"%PDF-test")
        outside = self.root / "outside.txt"
        outside.write_text("outside")
        (self.source / "escape.txt").symlink_to(outside)
        (self.source / "loop").symlink_to(self.source, target_is_directory=True)
        result = inventory.build_inventory(self.source, excluded_dirs=[inside_work])
        self.assertEqual([r["relative_path"] for r in result["sources"]], ["good.txt"])
        self.assertEqual(len(result["excluded"]), 3)

    def test_source_cannot_be_inside_excluded_output(self):
        with self.assertRaisesRegex(ValueError, "cannot equal or contain"):
            inventory.build_inventory(self.source, excluded_dirs=[self.root])

    def test_magic_pdf_detection_ignores_misleading_extension(self):
        self.source_file("looks-like-word.docx", b"%PDF-1.7\nsynthetic")
        record = inventory.build_inventory(self.source)["sources"][0]
        self.assertEqual(record["format"], "pdf")
        self.assertTrue(record["warnings"])

    def test_cli_refuses_to_overwrite_and_reports_json(self):
        self.source_file("client.txt")
        output = self.work / "manifest.json"
        command = [sys.executable, str(SCRIPTS / "inventory.py"), str(self.source), "--output", str(output)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        before = inventory.file_hash(output)
        rerun = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(rerun.returncode, 0)
        self.assertIn("error", json.loads(rerun.stdout))
        self.assertEqual(before, inventory.file_hash(output))


class ConversionTests(unittest.TestCase):
    setUp = IntakeTests.setUp
    source_file = IntakeTests.source_file
    def manifest(self, capabilities=None):
        return inventory.build_inventory(self.source, registry() if capabilities is None else capabilities)

    def test_native_source_cannot_silently_use_fallback(self):
        self.source_file("client.txt")
        manifest = self.manifest(registry(reader("text", ["txt"])))
        selected = manifest["sources"][0]["source_id"]
        with patch.object(convert_fallbacks, "convert_text", side_effect=AssertionError("should not convert")):
            report, _ = convert_fallbacks.convert_sources(manifest, self.work, [selected])
        self.assertTrue(report["errors"])
        self.assertFalse(self.work.exists())

    def test_unknown_capability_does_not_activate_fallback(self):
        self.source_file("client.txt")
        manifest = inventory.build_inventory(self.source)
        report, _ = convert_fallbacks.convert_sources(manifest, self.work)
        self.assertFalse(report["derivatives"])
        self.assertEqual(len(report["skipped"]), 1)

    def test_modified_source_is_rejected_before_conversion(self):
        original = self.source_file("client.txt")
        manifest = self.manifest()
        original.write_text("changed after inventory")
        report, _ = convert_fallbacks.convert_sources(manifest, self.work)
        self.assertIn("changed since inventory", report["errors"][0]["error"])
        self.assertFalse(self.work.exists())

    def test_output_inside_unexcluded_source_is_rejected(self):
        self.source_file("client.txt")
        with self.assertRaisesRegex(ValueError, "explicitly excluded"):
            convert_fallbacks.convert_sources(self.manifest(), self.source / "derived")

    def test_source_id_cannot_escape_output_directory(self):
        self.source_file("client.txt")
        manifest = self.manifest()
        manifest["sources"][0]["source_id"] = "../../escape"
        with self.assertRaisesRegex(ValueError, "safe identifiers"):
            convert_fallbacks.convert_sources(manifest, self.work)

    def test_unsupported_formats_and_spreadsheets_are_explicit_errors(self):
        self.source_file("mail.msg")
        self.source_file("book.xlsx", b"spreadsheet")
        report, _ = convert_fallbacks.convert_sources(self.manifest(), self.work)
        self.assertEqual(len(report["errors"]), 2)
        self.assertFalse(report["derivatives"])
        self.assertFalse(self.work.exists())

    def test_office_requires_explicit_headless_and_network_policy(self):
        self.source_file("client.docx")
        with patch.object(convert_fallbacks.subprocess, "run", side_effect=AssertionError("should not launch")):
            report, _ = convert_fallbacks.convert_sources(self.manifest(), self.work)
        self.assertIn("office-command", report["errors"][0]["error"])
        self.assertFalse(self.work.exists())

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "optional reportlab runtime is unavailable")
    def test_text_fallback_keeps_hash_and_provenance_and_refuses_rerun(self):
        original = self.source_file("client.txt", b"Name: Alex Sample\nAddress: Example Street\n")
        original_hash = inventory.file_hash(original)
        manifest = self.manifest()
        report, enriched = convert_fallbacks.convert_sources(manifest, self.work)
        self.assertFalse(report["errors"])
        derivative = report["derivatives"][0]
        self.assertEqual(derivative["original_sha256"], original_hash)
        self.assertEqual(inventory.file_hash(original), original_hash)
        self.assertEqual(derivative["conversion_status"], "complete")
        self.assertEqual(enriched["sources"][0]["derivatives"][0], derivative)
        self.assertEqual(derivative["coverage"]["source_lines"], 3)
        self.assertTrue(derivative["page_mapping"])
        if importlib.util.find_spec("pypdf"):
            from pypdf import PdfReader
            pdf = PdfReader(derivative["path"])
            self.assertIn("Alex Sample", pdf.pages[0].extract_text())
        repeated, _ = convert_fallbacks.convert_sources(manifest, self.work)
        self.assertIn("already exists", repeated["errors"][0]["error"])
        self.assertEqual(inventory.file_hash(original), original_hash)

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "optional reportlab runtime is unavailable")
    def test_explicit_inadequacy_enables_only_selected_native_source(self):
        self.source_file("client.txt")
        manifest = self.manifest(registry(reader("text", ["txt"])))
        selected = manifest["sources"][0]["source_id"]
        report, _ = convert_fallbacks.convert_sources(manifest, self.work, decisions={selected: "reader could not preserve required symbols"})
        self.assertFalse(report["errors"])
        self.assertEqual(report["derivatives"][0]["reason"], "reader could not preserve required symbols")

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "optional reportlab runtime is unavailable")
    def test_unknown_text_encoding_fails_without_character_replacement(self):
        self.source_file("client.txt", b"\x80\x81")
        report, _ = convert_fallbacks.convert_sources(self.manifest(), self.work)
        self.assertIn("decoding failed", report["errors"][0]["error"])
        self.assertFalse(report["derivatives"])

    @unittest.skipUnless(importlib.util.find_spec("reportlab") and importlib.util.find_spec("PIL"), "optional image runtime unavailable")
    def test_all_image_frames_are_converted_with_mapping(self):
        from PIL import Image
        first = Image.new("RGB", (80, 60), "white")
        second = Image.new("RGB", (70, 50), "blue")
        path = self.source / "pages.tiff"
        first.save(path, save_all=True, append_images=[second])
        original_hash = inventory.file_hash(path)
        report, _ = convert_fallbacks.convert_sources(self.manifest(), self.work)
        self.assertFalse(report["errors"])
        derivative = report["derivatives"][0]
        self.assertEqual(derivative["coverage"]["source_frames"], 2)
        self.assertEqual([entry["original_locator"]["frame"] for entry in derivative["page_mapping"]], [1, 2])
        self.assertEqual(inventory.file_hash(path), original_hash)
        if importlib.util.find_spec("pypdf"):
            from pypdf import PdfReader
            self.assertEqual(len(PdfReader(derivative["path"]).pages), 2)

    def test_cli_invalid_decision_has_nonzero_json_error(self):
        path = self.root / "decisions.json"
        path.write_text('[{"source_id":"s1", "status":"missing", "reason":""}]')
        self.source_file("client.txt")
        manifest_path = self.root / "manifest.json"
        inventory.write_new_json(manifest_path, self.manifest())
        result = subprocess.run([sys.executable, str(SCRIPTS / "convert_fallbacks.py"), "--manifest", str(manifest_path),
                                 "--output-dir", str(self.work), "--decisions", str(path)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
