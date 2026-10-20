#!/usr/bin/env python3
"""Make local PDF derivatives only after a native reader is missing/inadequate.

This is a conversion helper, not an extraction or form-filling engine. No GUI,
application automation, browser, remote service, or external-link refresh is used.
Optional Pillow/reportlab enable images/text. Office export is opt-in and partial
until the host checks completeness; spreadsheet export is deliberately unsupported.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from inventory import file_hash, within, write_new_json


TEXT_FORMATS = {"txt", "csv", "tsv", "json", "xml"}
IMAGE_FORMATS = {"png", "jpeg", "tiff", "gif", "bmp", "webp"}
OFFICE_FORMATS = {"doc", "docx", "odt", "rtf", "ppt", "pptx", "odp"}
SPREADSHEET_FORMATS = {"xls", "xlsx", "xlsm", "ods"}


class ConversionError(ValueError):
    pass


def version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def inspect_capabilities(office_command: str | None = None) -> dict:
    office = shutil.which(office_command) if office_command else None
    return {"reportlab": version("reportlab"), "Pillow": version("Pillow"),
            "office_command": office, "office_enabled": office is not None,
            "spreadsheet_pdf_export": "unsupported: no verified all-sheet/used-range pagination adapter",
            "email_html_pdf_export": "unsupported: use a discovered local adapter that preserves headers/attachments and blocks remote resources"}


def load_decisions(path: Path | None) -> dict:
    if not path:
        return {}
    decisions = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(decisions, dict) and "decisions" in decisions:
        decisions = decisions["decisions"]
    if not isinstance(decisions, list):
        raise ValueError("decisions must be an array (or an object with a decisions array)")
    result = {}
    for decision in decisions:
        if not isinstance(decision, dict) or not isinstance(decision.get("source_id"), str):
            raise ValueError("every fallback decision needs source_id")
        if decision.get("status") != "inadequate" or not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
            raise ValueError("every decision must explicitly mark a native extraction inadequate and explain why")
        if decision["source_id"] in result:
            raise ValueError("duplicate fallback decisions are ambiguous")
        result[decision["source_id"]] = decision["reason"].strip()
    return result


def safe_output_directory(manifest: dict, output: Path) -> Path:
    root = Path(manifest["source_root"]).resolve(strict=True)
    output = output.expanduser().resolve()
    exclusions = [Path(p).resolve() for p in manifest.get("excluded_directories", [])]
    if output == root or (within(output, root) and not any(output == p or within(output, p) for p in exclusions)):
        raise ValueError("fallback output inside source must be under an explicitly excluded work/output directory")
    if output.is_file():
        raise ValueError("fallback output directory is a file")
    return output


def require_unchanged_source(manifest: dict, source: dict) -> Path:
    root = Path(manifest["source_root"]).resolve(strict=True)
    path = Path(source["original_path"]).resolve(strict=True)
    if not within(path, root) or not path.is_file():
        raise ValueError("source path is outside the authorized folder or not a regular file")
    expected = (root / source["relative_path"]).resolve(strict=True)
    if path != expected:
        raise ValueError("manifest original_path and relative_path disagree")
    if file_hash(path) != source["sha256"]:
        raise ValueError("source changed since inventory; rebuild inventory before conversion")
    return path


def _font_for_text(text: str, explicit: Path | None):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if explicit is None and all(ord(character) < 128 for character in text):
        return "Helvetica"
    candidates = [explicit] if explicit else [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            font = TTFont("FallbackTextFont", str(candidate))
            unsupported = {c for c in text if not c.isspace() and ord(c) not in font.face.charToGlyph}
            if unsupported:
                continue
            pdfmetrics.registerFont(font)
            return "FallbackTextFont"
    raise ConversionError("no discovered font covers every source character; supply --font and recheck glyphs")


def convert_text(source: Path, destination: Path, encoding: str | None = None, font: Path | None = None) -> dict:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import A4
    except ImportError as error:
        raise ConversionError("text conversion requires reportlab in the selected local runtime") from error
    raw = source.read_bytes()
    selected_encoding = encoding or ("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    try:
        text = raw.decode(selected_encoding, errors="strict")
    except (UnicodeDecodeError, LookupError) as error:
        raise ConversionError("text decoding failed; provide the verified --encoding instead of replacing characters") from error
    if any(ord(c) < 32 and c not in "\t\r\n\f" for c in text):
        raise ConversionError("text contains binary/control characters; select a compatible converter")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    font_name = _font_for_text(text, font)
    canvas = Canvas(str(destination), pagesize=A4, pageCompression=1)
    width, height = A4
    margin, font_size, leading = 36, 9, 12
    maximum_width = width - margin * 2
    y, page = height - margin, 1
    mapping = [{"page": 1, "original_locator": {"kind": "text", "line_start": 1}}]
    limitations = ["PDF pages preserve wrapped source text; semantic interpretation remains with Anthropic PDF.",
                   "Tabs expand to four-column stops; line wrapping is a recorded presentation change."]
    if source.suffix.lower() in {".csv", ".tsv"}:
        limitations.append("Delimited text is rendered verbatim; use original row/column locators only after independently verifying them.")
    canvas.setFont(font_name, font_size)

    def next_page(line_number: int):
        nonlocal y, page
        canvas.showPage()
        canvas.setFont(font_name, font_size)
        page += 1
        y = height - margin
        mapping.append({"page": page, "original_locator": {"kind": "text", "line_start": line_number}})

    for line_number, line in enumerate(text.split("\n"), 1):
        line = line.removesuffix("\r").expandtabs(4)
        chunks = line.split("\f")
        for chunk_number, chunk in enumerate(chunks):
            if chunk_number:
                next_page(line_number)
            while chunk:
                lower, upper = 1, len(chunk)
                while lower < upper:
                    midpoint = (lower + upper + 1) // 2
                    if pdfmetrics.stringWidth(chunk[:midpoint], font_name, font_size) <= maximum_width:
                        lower = midpoint
                    else:
                        upper = midpoint - 1
                if y < margin:
                    next_page(line_number)
                canvas.drawString(margin, y, chunk[:lower])
                y -= leading
                chunk = chunk[lower:]
            if not line or not chunks[chunk_number]:
                if y < margin:
                    next_page(line_number)
                y -= leading
    canvas.showPage()
    canvas.save()
    return {"converter": {"id": "reportlab-text", "version": version("reportlab")},
            "conversion_status": "complete", "limitations": limitations, "page_mapping": mapping,
            "coverage": {"encoding": selected_encoding, "source_lines": len(text.split("\n")), "pages": page,
                         "font": font_name, "character_count": len(text)}}


def convert_image(source: Path, destination: Path) -> dict:
    try:
        from PIL import Image, ImageOps, ImageSequence
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
    except ImportError as error:
        raise ConversionError("image conversion requires Pillow and reportlab in the selected local runtime") from error
    canvas = Canvas(str(destination), pagesize=A4, pageCompression=1)
    width, height = A4
    mapping = []
    with Image.open(source) as original:
        for frame_number, frame in enumerate(ImageSequence.Iterator(original), 1):
            image = ImageOps.exif_transpose(frame.copy())
            if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
                rgba = image.convert("RGBA")
                image = Image.new("RGB", rgba.size, "white")
                image.paste(rgba, mask=rgba.getchannel("A"))
            else:
                image = image.convert("RGB")
            scale = min((width - 72) / image.width, (height - 72) / image.height)
            drawn_width, drawn_height = image.width * scale, image.height * scale
            canvas.drawImage(ImageReader(image), (width - drawn_width) / 2, (height - drawn_height) / 2,
                             width=drawn_width, height=drawn_height)
            mapping.append({"page": frame_number, "original_locator": {"kind": "image", "frame": frame_number},
                            "source_pixel_dimensions": [image.width, image.height]})
            canvas.showPage()
    canvas.save()
    return {"converter": {"id": "pillow-reportlab-image", "version": f"Pillow {version('Pillow')}; reportlab {version('reportlab')}"},
            "conversion_status": "complete", "limitations": ["Images are displayed on A4 pages; all frames are retained.",
                "EXIF orientation is applied; transparency is composited over white and colors convert to RGB.",
                "PDF extraction needs image inspection/OCR; small text may require higher-resolution inspection."],
            "page_mapping": mapping, "coverage": {"source_frames": len(mapping), "pages": len(mapping)}}


def convert_office(source: Path, destination: Path, office_command: str) -> dict:
    """Optional direct CLI export; a fresh profile and staged copy protect originals."""
    binary = shutil.which(office_command)
    if not binary:
        raise ConversionError("explicit headless Office executable was not found")
    with tempfile.TemporaryDirectory(prefix="office-export-", dir=destination.parent) as temporary:
        root = Path(temporary)
        profile = root / "profile"
        (profile / "user").mkdir(parents=True)
        # Do not permit document macros; never reuse a person's running GUI profile.
        (profile / "user" / "registrymodifications.xcu").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Writer/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>0</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Calc/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>0</value></prop></item>'
            '</oor:items>', encoding="utf-8")
        staged = root / ("source" + source.suffix.lower())
        shutil.copyfile(source, staged)
        exported = root / "exported"
        exported.mkdir()
        command = [binary, "-env:UserInstallation=" + profile.as_uri(), "--headless", "--norestore", "--nodefault",
                   "--nolockcheck", "--nofirststartwizard", "--convert-to", "pdf", "--outdir", str(exported), str(staged)]
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120, check=False)
            version_result = subprocess.run([binary, "-env:UserInstallation=" + profile.as_uri(), "--headless", "--version"],
                                            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20, check=False)
        except subprocess.TimeoutExpired as error:
            raise ConversionError("headless Office export timed out") from error
        candidate = exported / "source.pdf"
        if result.returncode or not candidate.is_file():
            raise ConversionError(f"headless Office export failed (exit {result.returncode}); no verified PDF produced")
        shutil.copyfile(candidate, destination)
        converter_version = version_result.stdout.strip() if version_result.returncode == 0 else "unrecorded"
    return {"converter": {"id": "libreoffice-headless", "version": converter_version}, "conversion_status": "partial",
            "limitations": ["Host must inspect exported pages against the original before calling conversion complete.",
                "Comments, tracked changes, speaker notes, text boxes, embedded objects and hidden content are not proven covered.",
                "Link updates are disabled in an isolated profile; run only under a network-restricted local execution policy.",
                "Original-to-PDF page mapping has not been established."], "page_mapping": []}


def convert_sources(manifest: dict, output_dir: Path, source_ids: list[str] | None = None, decisions: dict | None = None,
                    encoding: str | None = None, font: Path | None = None, office_command: str | None = None,
                    office_network_restricted: bool = False) -> tuple[dict, dict]:
    if manifest.get("kind") != "source_manifest" or not isinstance(manifest.get("sources"), list):
        raise ValueError("input must be an inventory source_manifest")
    output_dir = safe_output_directory(manifest, output_dir)
    ids = {source["source_id"] for source in manifest["sources"]}
    if len(ids) != len(manifest["sources"]):
        raise ValueError("manifest has duplicate source IDs")
    if not all(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) for value in ids):
        raise ValueError("source IDs must be safe identifiers, never paths")
    decisions = decisions or {}
    unknown = (set(source_ids or []) | set(decisions)) - ids
    if unknown:
        raise ValueError("unknown source ID(s): " + ", ".join(sorted(unknown)))
    enriched = deepcopy(manifest)
    report = {"schema_version": "1.0", "kind": "conversion_report", "generated_at": datetime.now(timezone.utc).isoformat(),
              "capabilities": inspect_capabilities(office_command), "derivatives": [], "skipped": [], "errors": []}
    selected = set(source_ids) if source_ids else None
    for source in enriched["sources"]:
        source_id = source["source_id"]
        if selected is not None and source_id not in selected:
            continue
        reason = decisions.get(source_id)
        if not reason and source.get("route", {}).get("status") == "fallback_needed":
            reason = source["route"].get("reason")
        if not reason:
            message = "native route/discovery is unresolved; PDF fallback was not authorized by a missing/inadequate reader result"
            if selected is not None:
                report["errors"].append({"source_id": source_id, "error": message})
            else:
                report["skipped"].append({"source_id": source_id, "reason": message})
            continue
        if source.get("duplicate_of"):
            report["skipped"].append({"source_id": source_id, "reason": "duplicate content; use derivative of " + source["duplicate_of"]})
            continue
        destination = output_dir / (source_id + ".pdf")
        temporary = None
        try:
            original = require_unchanged_source(manifest, source)
            if destination.exists():
                raise ConversionError("derivative already exists; use a fresh output directory")
            source_format = source["format"]
            if source_format == "pdf":
                raise ConversionError("PDF input must use Anthropic PDF directly; PDF-to-PDF fallback is not supported")
            if source_format in SPREADSHEET_FORMATS:
                raise ConversionError("spreadsheet export is unsupported until a headless adapter proves every sheet/used range, hidden content and formula provenance")
            if source_format not in TEXT_FORMATS | IMAGE_FORMATS | OFFICE_FORMATS:
                raise ConversionError("no compatible headless converter for " + source_format + "; discover a local adapter or keep this source unresolved")
            if source_format in OFFICE_FORMATS and (not office_command or not office_network_restricted):
                raise ConversionError("Office fallback needs --office-command and --office-network-restricted after verifying a headless executable and network isolation")
            output_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix=".conversion-", suffix=".pdf", dir=output_dir, delete=False) as handle:
                temporary = Path(handle.name)
            if source_format in TEXT_FORMATS:
                details = convert_text(original, temporary, encoding, font)
            elif source_format in IMAGE_FORMATS:
                details = convert_image(original, temporary)
            else:
                details = convert_office(original, temporary, office_command)
            with temporary.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise ConversionError("converter output is not a PDF")
            # Check again before publishing, then create exclusively rather than replacing.
            if file_hash(original) != source["sha256"]:
                raise ConversionError("source changed during conversion")
            with temporary.open("rb") as source_stream, destination.open("xb") as output_stream:
                shutil.copyfileobj(source_stream, output_stream)
            digest = file_hash(destination)
            derivative = {"derivative_id": "pdf_" + digest[:20], "source_id": source_id, "format": "pdf",
                          "path": str(destination), "sha256": digest, "original_sha256": source["sha256"],
                          "reason": reason, **details}
            source.setdefault("derivatives", []).append(derivative)
            report["derivatives"].append(derivative)
            if derivative["conversion_status"] != "complete":
                report["errors"].append({"source_id": source_id, "error": "conversion is partial; completeness review is required"})
        except (OSError, ValueError, ImportError) as error:
            report["errors"].append({"source_id": source_id, "error": str(error)})
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
    return report, enriched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-id", action="append")
    parser.add_argument("--decisions", type=Path, help="explicit inadequate native-reader outcomes with reasons")
    parser.add_argument("--encoding", help="verified input text encoding")
    parser.add_argument("--font", type=Path, help="local font that covers every source character")
    parser.add_argument("--office-command", help="explicitly verified local headless LibreOffice executable")
    parser.add_argument("--office-network-restricted", action="store_true", help="assert current execution policy blocks network access for Office conversion")
    parser.add_argument("--output", type=Path, help="write a new conversion report")
    parser.add_argument("--output-manifest", type=Path, help="write a new manifest with derivative lineage")
    parser.add_argument("--check-capabilities", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_capabilities:
            print(json.dumps(inspect_capabilities(args.office_command), indent=2))
            return 0
        if not args.manifest or not args.output_dir:
            raise ValueError("--manifest and --output-dir are required unless checking capabilities")
        protected = {p.resolve() for p in (args.manifest, args.decisions, args.font) if p}
        outputs = [p for p in (args.output, args.output_manifest) if p]
        if len({p.resolve() for p in outputs}) != len(outputs):
            raise ValueError("report and enriched manifest need different output paths")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        protected.update(Path(s["original_path"]).resolve() for s in manifest.get("sources", []))
        for path in outputs:
            if path.resolve() in protected or path.exists():
                raise ValueError("output conflicts with an input or existing artifact; use a fresh path")
            safe_output_directory(manifest, path.parent)
        report, enriched = convert_sources(manifest, args.output_dir, args.source_id, load_decisions(args.decisions),
                                          args.encoding, args.font, args.office_command, args.office_network_restricted)
        if args.output:
            write_new_json(args.output, report)
        if args.output_manifest:
            write_new_json(args.output_manifest, enriched)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["errors"] else 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
