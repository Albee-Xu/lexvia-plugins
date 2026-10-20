#!/usr/bin/env python3
"""Inventory an explicit evidence folder without reading document semantics.

Only a caller supplied, actually discovered reader registry can select a reader.
An absent registry or an incomplete discovery never means a reader is missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


SCHEMA_VERSION = "1.0"
DEFAULT_SKIP_DIRS = {".git", ".codex", ".agents", "__pycache__", "node_modules", ".venv", ".fill-pdf-work"}
FORMATS = {
    ".pdf": "pdf", ".doc": "doc", ".docx": "docx", ".odt": "odt", ".rtf": "rtf",
    ".xls": "xls", ".xlsx": "xlsx", ".xlsm": "xlsm", ".ods": "ods", ".csv": "csv", ".tsv": "tsv",
    ".ppt": "ppt", ".pptx": "pptx", ".odp": "odp", ".eml": "eml", ".msg": "msg",
    ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".tif": "tiff", ".tiff": "tiff",
    ".gif": "gif", ".bmp": "bmp", ".webp": "webp", ".txt": "txt", ".md": "txt",
    ".html": "html", ".htm": "html", ".xml": "xml", ".json": "json",
}


def within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new_json(path: Path, data: dict) -> None:
    """Create only; never overwrite a source or a previous run artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(data, output, ensure_ascii=False, indent=2)
        output.write("\n")


def normalize_format(value: str) -> str:
    value = value.lower().lstrip(".")
    return {"jpg": "jpeg", "tif": "tiff", "md": "txt", "htm": "html"}.get(value, value)


def validate_capabilities(data: dict | None) -> dict:
    if data is None:
        return {"discovery": "not_provided", "readers": []}
    if not isinstance(data, dict) or data.get("discovery") not in {"complete", "partial", "not_provided"}:
        raise ValueError("capabilities.discovery must be complete, partial, or not_provided")
    if not isinstance(data.get("readers"), list):
        raise ValueError("capabilities.readers must be an array")
    seen = set()
    for reader in data["readers"]:
        if not isinstance(reader, dict) or not isinstance(reader.get("id"), str) or not reader["id"]:
            raise ValueError("every reader needs a nonempty id")
        if reader["id"] in seen:
            raise ValueError("reader IDs must be unique")
        seen.add(reader["id"])
        if not isinstance(reader.get("formats"), list) or not all(isinstance(f, str) and f for f in reader["formats"]):
            raise ValueError("every reader needs a formats array")
        if reader.get("available") not in (True, False, "available", "unavailable", "unknown", None):
            raise ValueError("reader.available must be a boolean or available/unavailable/unknown")
        if "headless" in reader and not isinstance(reader["headless"], bool):
            raise ValueError("reader.headless must be a boolean when supplied")
    return data


def choose_route(source_format: str, capabilities: dict) -> dict:
    candidates = [r for r in capabilities["readers"] if source_format in {normalize_format(f) for f in r["formats"]}]
    if source_format == "pdf":
        candidates = [r for r in candidates if r.get("is_anthropic_pdf") is True or r["id"] == "anthropic-pdf"]
    ready = [r for r in candidates if r.get("available") in (True, "available") and r.get("headless") is True]
    if ready:
        reader = ready[0]
        route = {"status": "pdf" if source_format == "pdf" else "native", "reader_id": reader["id"],
                 "reader_version": reader.get("version") or "unrecorded", "reason": "matching available headless reader"}
        if not reader.get("version"):
            route["limitations"] = ["Record the discovered reader version before extracting evidence."]
        return route
    unresolved = any(r.get("available") in (None, "unknown") or
                     (r.get("available") in (True, "available") and r.get("headless") is None)
                     for r in candidates)
    if unresolved or (not candidates and capabilities["discovery"] != "complete"):
        return {"status": "capability_unknown", "reason": "discover actual reader support and headless access before choosing a fallback"}
    if source_format == "pdf":
        return {"status": "unsupported", "reason": "Anthropic PDF extraction dependency is unavailable as a headless reader"}
    return {"status": "fallback_needed", "reason": "complete discovery or an explicit unavailable entry found no suitable headless native reader"}


def detect_format(path: Path) -> tuple[str, list[str]]:
    source_format = FORMATS.get(path.suffix.lower(), path.suffix.lower().lstrip(".") or "unknown")
    with path.open("rb") as stream:
        header = stream.read(16)
    detected = None
    if header.startswith(b"%PDF-"):
        detected = "pdf"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "png"
    elif header.startswith(b"\xff\xd8\xff"):
        detected = "jpeg"
    elif header.startswith((b"II*\x00", b"MM\x00*")):
        detected = "tiff"
    elif header.startswith((b"GIF87a", b"GIF89a")):
        detected = "gif"
    elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        detected = "webp"
    warnings = []
    if detected and detected != source_format:
        warnings.append("extension differs from detected magic signature")
    return detected or source_format, warnings


def build_inventory(source_root: Path, capabilities: dict | None = None, excluded_dirs: list[Path] | None = None,
                    excluded_files: list[Path] | None = None) -> dict:
    root = source_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("source must be an existing folder")
    capabilities = validate_capabilities(capabilities)
    excluded_dirs = [p.expanduser().resolve() for p in (excluded_dirs or [])]
    excluded_files = [p.expanduser().resolve() for p in (excluded_files or [])]
    if any(within(root, excluded) for excluded in excluded_dirs):
        raise ValueError("a work/output/excluded directory cannot equal or contain the selected source folder")
    manifest = {"schema_version": SCHEMA_VERSION, "kind": "source_manifest", "source_root": str(root),
                "generated_at": datetime.now(timezone.utc).isoformat(), "capability_inventory": capabilities,
                "excluded_directories": [str(p) for p in excluded_dirs], "sources": [], "excluded": [], "errors": []}
    first_by_hash = {}

    def excluded(path: Path, reason: str) -> None:
        manifest["excluded"].append({"relative_path": str(path.relative_to(root)), "reason": reason})

    def walk_error(error: OSError) -> None:
        manifest["errors"].append({"path": error.filename, "error": str(error)})

    for current, directories, filenames in os.walk(root, followlinks=False, onerror=walk_error):
        current_path = Path(current)
        keep = []
        for name in sorted(directories):
            path = current_path / name
            resolved = path.resolve()
            if name in DEFAULT_SKIP_DIRS:
                excluded(path, "generated/dependency directory")
            elif not within(resolved, root):
                excluded(path, "symlink target is outside source folder")
            elif path.is_symlink():
                excluded(path, "directory symlink is not traversed (cycle/duplicate protection)")
            elif any(within(resolved, p) for p in excluded_dirs):
                excluded(path, "explicit work/output/excluded directory")
            else:
                keep.append(name)
        directories[:] = keep
        for name in sorted(filenames):
            path = current_path / name
            try:
                resolved = path.resolve(strict=True)
                if not within(resolved, root):
                    excluded(path, "symlink target is outside source folder")
                    continue
                if resolved in excluded_files or any(within(resolved, p) for p in excluded_dirs):
                    excluded(path, "generated output or explicit exclusion")
                    continue
                if not resolved.is_file():
                    excluded(path, "not a regular file")
                    continue
                relative = str(path.relative_to(root))
                digest = file_hash(path)
                source_format, warnings = detect_format(path)
                source_id = "src_" + hashlib.sha256((relative + "\0" + digest).encode("utf-8")).hexdigest()[:20]
                record = {"source_id": source_id, "content_id": "sha256:" + digest, "relative_path": relative,
                          "original_path": str(path), "format": source_format, "size_bytes": path.stat().st_size,
                          "sha256": digest, "route": choose_route(source_format, capabilities),
                          "extraction": {"status": "pending"}, "lineage": {}}
                if path.is_symlink():
                    record["symlink_target"] = str(resolved)
                if warnings:
                    record["warnings"] = warnings
                if digest in first_by_hash:
                    record["duplicate_of"] = first_by_hash[digest]
                    record["extraction"]["status"] = "duplicate"
                else:
                    first_by_hash[digest] = source_id
                manifest["sources"].append(record)
            except (OSError, ValueError) as error:
                manifest["errors"].append({"path": str(path), "error": str(error)})
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--capabilities", type=Path, help="JSON discovered reader registry; omission means discovery is unresolved")
    parser.add_argument("--work-dir", type=Path, help="exclude the run's working directory if within source")
    parser.add_argument("--output-dir", type=Path, help="exclude the delivery directory if within source")
    parser.add_argument("--exclude-dir", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, help="write a new manifest; existing files are never replaced")
    args = parser.parse_args(argv)
    try:
        capabilities = json.loads(args.capabilities.read_text(encoding="utf-8")) if args.capabilities else None
        exclusions = args.exclude_dir + [p for p in (args.work_dir, args.output_dir) if p]
        files = [args.output] if args.output else []
        if args.output and args.capabilities and args.output.resolve() == args.capabilities.resolve():
            raise ValueError("manifest output cannot overwrite the capabilities input")
        if args.output and args.output.exists():
            raise ValueError("manifest output already exists; use a fresh run path")
        manifest = build_inventory(args.source, capabilities, exclusions, files)
        if args.output:
            write_new_json(args.output, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 1 if manifest["errors"] else 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
