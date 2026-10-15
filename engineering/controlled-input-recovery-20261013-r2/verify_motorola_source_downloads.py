"""Recheck recovered source bytes outside Git; does not grant product qualification."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fitz


def verify(cache: Path) -> dict:
    folder = Path(__file__).resolve().parent
    docs = json.loads((folder / "motorola-source-retrieval.json").read_text())["source_documents"]
    docs.append(json.loads((folder / "motorola-regulatory-battery-identity.json").read_text()))
    expected_markers = {
        "motorola_xt2551_level2_v1_0r": ("razr 60 ultra", "RS13", "RS35", "3520mAh", "Main FPC BTB Bracket"),
        "motorola_xt2551_level3_na_v1_0r": ("razr 60 ultra", "SCA8D57591", "PMIH0104", "SVCPE@lenovo.com"),
        "motorola_xt2551_sbom_v1_9": ("XT2551-1", "XT2551-2", "SB18E50881", "SB18E50882", "3520mAh"),
        "motorola_xt2551_6_eu_RED_rev19Jun2025": ("XT2551-6", "MC442", "RS13", "RS35"),
    }
    rows = []
    for source in docs:
        path = cache / (source["name"] + ".pdf")
        data = path.read_bytes()
        if not data.startswith(b"%PDF"):
            raise ValueError(f"Not a PDF: {source['name']}")
        digest = hashlib.sha256(data).hexdigest()
        if digest != source["sha256"] or len(data) != source["byte_count"]:
            raise ValueError(f"Source bytes differ: {source['name']}")
        with fitz.open(path) as pdf:
            if len(pdf) != source["pdf_pages"]:
                raise ValueError(f"Page count differs: {source['name']}")
            text = "\n".join(page.get_text() for page in pdf)
            for marker in expected_markers[source["name"]]:
                if marker not in text:
                    raise ValueError(f"Wrong source identity: {source['name']} missing {marker}")
        rows.append({"name": source["name"], "sha256": digest, "bytes": len(data),
                     "pages": source["pdf_pages"], "identity_markers_present": True})
    if len({row["sha256"] for row in rows}) != len(rows):
        raise ValueError("Different document identities aliased to the same bytes")
    visuals = json.loads((folder / "motorola-visual-review-receipt.json").read_text())["raster_reviews"]
    for row in visuals:
        path = cache / "renders" / f"{row['document']}_p{row['pdf_page_1based']:03}.png"
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["raster_sha256"]:
            raise ValueError(f"Reviewed image bytes changed: {path.name}")
    return {"schema": "razr-slide-oem-source-native-byte-verification-v1", "documents": rows,
            "native_document_identity_checks_pass": True, "reviewed_rasters_byte_checks": len(visuals),
            "independent_visual_review_claimed": False, "raw_files_republished": False,
            "actual_donor_identity_frozen": False, "native_assembly_received": False,
            "native_complete_ECAD_received": False, "hardware_qualification_performed": False,
            "manufacturing_go": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.cache_root)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"documents_verified": len(report["documents"]),
                      "reviewed_rasters_byte_checks": report["reviewed_rasters_byte_checks"],
                      "manufacturing_go": False}))


if __name__ == "__main__":
    main()
