#!/usr/bin/env python3
"""Read-only PDF-skill-guided structure probe; never repairs or fills a PDF.

This supplements the dependency's canonical field inventory with page-widget
observations so malformed hierarchies do not look like successful full coverage.
Coordinates are PDF points, origin at the bottom left. No UI or network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def _resolve(value):
    return value.get_object() if hasattr(value, "get_object") else value


def _inherited(obj, key, default=None):
    """Follow /Parent conservatively, guarding malformed/cyclic hierarchies."""
    seen = set()
    for _ in range(64):
        obj = _resolve(obj)
        identity = id(obj)
        if identity in seen:
            break
        seen.add(identity)
        if key in obj:
            return _resolve(obj[key])
        if "/Parent" not in obj:
            break
        obj = obj["/Parent"]
    return default


def _qualified_name(obj):
    parts = []
    seen = set()
    for _ in range(64):
        obj = _resolve(obj)
        if id(obj) in seen:
            break
        seen.add(id(obj))
        if "/T" in obj:
            parts.append(str(obj["/T"]))
        if "/Parent" not in obj:
            break
        obj = obj["/Parent"]
    return ".".join(reversed(parts)) or None


def probe(path):
    from importlib.metadata import version
    from pypdf import PdfReader

    path = Path(path).resolve(strict=True)
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    reader = PdfReader(path)
    fields = reader.get_fields() or {}
    widgets = []
    geometry = []
    annotation_count = 0
    for page_number, page in enumerate(reader.pages, 1):
        geometry.append({"page": page_number, "mediabox": [float(v) for v in page.mediabox], "rotation": page.rotation})
        annotations = _resolve(page.get("/Annots", []))
        annotation_count += len(annotations)
        for index, reference in enumerate(annotations):
            obj = _resolve(reference)
            if obj.get("/Subtype") != "/Widget":
                continue
            field_id = _qualified_name(obj)
            field_type = _inherited(obj, "/FT")
            appearance = _resolve(obj.get("/AP", {}))
            normal = _resolve(appearance.get("/N", {}))
            options = sorted(str(v) for v in normal) if field_type == "/Btn" and isinstance(normal, dict) else []
            widgets.append({
                "widget_id": f"p{page_number}-a{index}-o{getattr(reference, 'idnum', index)}",
                "page": page_number, "annotation_index": index,
                "object_id": getattr(reference, "idnum", None),
                "field_id": field_id, "own_field_id": str(obj["/T"]) if "/T" in obj else None,
                "pdf_type": str(field_type) if field_type is not None else None,
                "rect": [float(v) for v in obj.get("/Rect", [])],
                "export_values": options,
                "in_canonical_inventory": field_id in fields,
            })
    counts = Counter(widget["field_id"] for widget in widgets if widget["field_id"])
    duplicate_names = {key: count for key, count in sorted(counts.items()) if count > 1}
    absent_names = sorted({w["field_id"] for w in widgets if w["field_id"] and w["field_id"] not in fields})
    signature_source = {"geometry": geometry, "widgets": [
        {key: widget[key] for key in ("page", "annotation_index", "field_id", "pdf_type", "rect", "export_values")}
        for widget in widgets
    ]}
    signature = hashlib.sha256(json.dumps(signature_source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    issues = []
    if absent_names:
        issues.append("Page widget names are absent from the canonical field inventory; do not fill by field name until mappings are verified.")
    if duplicate_names:
        issues.append("Repeated widget names require group, parent, page and geometry review; duplicates are not independently addressable IDs.")
    if any(w["field_id"] is None for w in widgets):
        issues.append("Some widgets have no resolvable field name.")
    if original_hash != hashlib.sha256(path.read_bytes()).hexdigest():
        raise RuntimeError("Original PDF changed during read-only inspection")
    return {
        "probe_version": "1.0", "sha256": original_hash,
        "reader": {"name": "pypdf", "version": version("pypdf")},
        "encrypted": reader.is_encrypted, "pages": len(reader.pages),
        "geometry": geometry, "structural_signature": signature,
        "canonical_field_ids": sorted(fields), "canonical_field_count": len(fields),
        "annotation_count": annotation_count, "widget_count": len(widgets),
        "duplicate_widget_names": duplicate_names,
        "widget_names_missing_from_canonical_inventory": absent_names,
        "widgets": widgets, "issues": issues,
        "interpretation": "Observations only. A radio group legitimately has multiple widgets. This probe does not establish write/readback/render compatibility or semantic mapping.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.pdf.resolve():
        parser.error("The output JSON must not overwrite the input PDF")
    result = probe(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Observed {result['widget_count']} widgets, {result['canonical_field_count']} canonical fields; {len(result['issues'])} review issues")


if __name__ == "__main__":
    main()
