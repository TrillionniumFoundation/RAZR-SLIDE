from pathlib import Path
import hashlib
import json
import tempfile
import unittest

import cadquery as cq

from occ_signed_volume import InconsistentGeometry
from verify_step_payload import full_solid_payload


class CompleteStepPayloadTests(unittest.TestCase):
    def test_real_nested_solid_assembly_is_allowed(self):
        box = cq.Workplane("XY").box(1, 2, 3).val()
        nested = cq.Compound.makeCompound([cq.Compound.makeCompound([box])])
        solids, counts = full_solid_payload([nested])
        self.assertEqual(len(solids), 1)
        self.assertEqual(counts, {"Compound": 2, "Solid": 1})

    def test_actual_step_free_wire_survives_transfer_and_is_rejected(self):
        box = cq.Workplane("XY").box(1, 2, 3).val()
        wire = cq.Workplane("XY").rect(1, 1).val().translate((10, 0, 0))
        compound = cq.Compound.makeCompound([box, wire])
        target = Path(__file__).with_name("REJECTED_solid_plus_loose_wire.step")
        cq.exporters.export(compound, str(target), "STEP")
        imported = cq.importers.importStep(str(target))
        # The old traversal would see one valid solid and silently miss the wire.
        self.assertEqual(len(imported.solids().vals()), 1)
        with self.assertRaisesRegex(InconsistentGeometry, "Free non-solid STEP payload leaf"):
            full_solid_payload(imported.vals())
        receipt = {"actual_export_reimport_witness": True,
                   "path": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                   "filtered_solids_count_that_silently_discards_wire": 1,
                   "raw_transfer_root_types": [root.ShapeType() for root in imported.vals()],
                   "full_payload_parser_rejects_free_wire": True, "manufacturing_go": False}
        target.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")

    def test_empty_compound_is_rejected(self):
        with self.assertRaises(InconsistentGeometry):
            full_solid_payload([cq.Compound.makeCompound([])])


if __name__ == "__main__":
    unittest.main()
