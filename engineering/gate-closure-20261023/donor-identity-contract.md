# Fixed donor identity inventory

## Reproduced defect

Source inspected: `2a8893743c7e90935b1594e619eab9f2ae46b872` (PR #37).
The previous importer and bound-record reader derived the required donor field
inventory from the mutable `design/product_interfaces.json` `donor` keys. A
configuration reduced to `{"model": null}` could therefore import one observed
model and report no unknown identity fields. With complete synthetic part-label
fixtures, the bound-record reader returned `true`, and configuration validation
accepted `actual_donor_selected=true`. This was reproduced in a temporary unit
fixture; no real physical record or product status was changed.

Observed pre-fix output:

```json
{
  "donor": {"model": "SYNTHETIC-ADB-MODEL"},
  "bound": true,
  "known_identity_fields": 1,
  "unknown_identity_fields": [],
  "actual_donor_selected_accepted": true
}
```

The existing 22 hardware-evidence tests passed before this defect was fixed.

## Contract

The `razr-product-interfaces-v1` donor inventory is now owned by the validator:

| Required identity | Required observation boundary |
| --- | --- |
| `model` | Original selected-device readback must agree with the record |
| `region` | Identified source observation with a locator |
| `mainboard_revision` | Actual specimen label or physical measurement |
| `runtime_panel_id` | Identified source observation with a locator |
| `display_module_part` | Actual specimen label or physical measurement |
| `display_module_revision` | Actual specimen label or physical measurement |
| `touch_revision` | Actual specimen label or physical measurement |
| `pack_A_label` | Actual specimen label or physical measurement |
| `pack_B_label` | Actual specimen label or physical measurement |
| `USB_roles` | Identified source observation with a locator |
| `USB_version_rate` | Identified source observation with a locator |

Unknown values remain `null`; all eleven keys must remain present. Missing,
additional or malformed fields cannot reduce the qualification requirements.
The configuration validator, direct identity importer and bound-record reader
share this inventory. Partial observations remain importable and report all
remaining unknown fields. The seven physical part roles and twelve terminal
interfaces keep their existing independent requirements.

Four added regression methods exercise field deletion, model-only import,
rehashed matching records with a deleted physical revision, and malformed
values. The existing complete positive fixture and partial one-field fixture
remain accepted within their original scopes. In the partial fixture, one known
model leaves ten unknown identities and does not bind a complete donor.

## Validation and scope

```sh
python3 -B -m unittest discover -s integration/product-study-tests -p 'test_hardware_evidence.py' -v
```

The focused suite passed all 26 tests after the change in the available Python
runtime. These temporary synthetic regressions demonstrate validator behavior;
they are not physical observations, locked full-suite completion, same-specimen
measurements, terminal qualification, or G1 acceptance. The actual ten missing
identity observations, seven part roles and twelve terminal interfaces remain
open until the corresponding original evidence is supplied.
