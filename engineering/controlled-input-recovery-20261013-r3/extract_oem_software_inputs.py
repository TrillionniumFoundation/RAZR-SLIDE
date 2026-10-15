"""Extract limited software inputs from exact upstream bytes, never OEM manufacturing ratings."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def without_comments(source: str) -> str:
    # These source files contain no URL string properties. This is a bounded
    # extractor for their scalar configuration fields, not a DTS compiler.
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//[^\n]*", "", source)


def scalar_values(source: str, property_name: str) -> list[int]:
    vals = re.findall(re.escape(property_name) + r"\s*=\s*<\s*(0x[0-9a-fA-F]+|\d+)\s*>\s*;", source)
    return sorted({int(v, 0) for v in vals})


def extract(cache: Path) -> dict:
    folder = Path(__file__).resolve().parent
    index = json.loads((folder / "official-oem-source-index.json").read_text())
    sources = {}
    proof = []
    for item in index["sources"]:
        data = (cache / item["private_basename"]).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != item["git_blob"]:
            raise ValueError(f"Exact upstream source identity differs: {item['path']}")
        sources[item["private_basename"]] = data.decode("utf-8")
        proof.append({"path": item["path"], "git_blob": blob, "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    selector = without_comments(sources["sun-sde-display-leap-common.dtsi"])
    includes = set(re.findall(r'#include\s+"([^\"]+)"', selector))
    included_main_panel_configs = sorted(name for name in includes
                                         if "-csot-" in name and "-cli_" not in name)
    variants = []
    for name, content in sources.items():
        if not name.startswith("dsi-panel-mot-csot-"):
            continue
        clean = without_comments(content)
        panel_names = re.findall(r'qcom,mdss-dsi-panel-name\s*=\s*"([^\"]+)"', clean)
        lanes = sorted({int(v) for v in re.findall(r"qcom,mdss-dsi-lane-(\d)-state\s*;", clean)})
        variants.append({"file": name, "referenced_directly_by_leap_selector": name in includes,
                         "selected_on_actual_donor": None, "source_panel_names": panel_names,
                         "software_physical_width_integer": scalar_values(clean, "qcom,mdss-pan-physical-width-dimension"),
                         "software_physical_height_integer": scalar_values(clean, "qcom,mdss-pan-physical-height-dimension"),
                         "software_pixel_width": scalar_values(clean, "qcom,mdss-dsi-panel-width"),
                         "software_pixel_height": scalar_values(clean, "qcom,mdss-dsi-panel-height"),
                         "active_source_framerates": scalar_values(clean, "qcom,mdss-dsi-panel-framerate"),
                         "DSI_lane_indices": lanes,
                         "DSC_version_integer": scalar_values(clean, "qcom,mdss-dsc-version"),
                         "DSC_bits_per_component": scalar_values(clean, "qcom,mdss-dsc-bit-per-component"),
                         "DSC_bits_per_pixel": scalar_values(clean, "qcom,mdss-dsc-bit-per-pixel"),
                         "DSC_slice_width": scalar_values(clean, "qcom,mdss-dsc-slice-width"),
                         "DSC_slice_height": scalar_values(clean, "qcom,mdss-dsc-slice-height"),
                         "orderable_module_number": None, "controlled_MCAD_sha256": None,
                         "controlled_connector_terminal_map_sha256": None,
                         "dynamic_rolling_qualification_sha256": None})
    touch = without_comments(sources["sun-leap-touchscreen-overlay.dtsi"])
    main_touch = touch.split("goodix-berlin@0 {", 1)[1].split("\n\t};", 1)[0]
    main_touch_compatible = re.findall(r'compatible\s*=\s*"([^\"]+)"', main_touch)
    usb = without_comments(sources["sun-leap-device-common-overlay.dtsi"])
    charger = without_comments(sources["sun-leap-charger-overlay.dtsi"])
    ids = {key: re.findall(re.escape(key) + r'\s*=\s*"([^\"]+)"\s*,\s*"([^\"]+)"', charger)
           for key in ["main-ids-map", "flip-ids-map"]}
    main_supply = selector.split("dsi_panel_pwr_supply_main:", 1)[1].split("dsi_panel_pwr_supply_sec:", 1)[0]
    regulator_votes = []
    for entry in re.findall(r"qcom,panel-supply-entry@\d+\s*\{(.*?)\};", main_supply, re.S):
        names = re.findall(r'qcom,supply-name\s*=\s*"([^\"]+)"', entry)
        regulator_votes.append({"name": names[0], "min_microvolt_vote": scalar_values(entry, "qcom,supply-min-voltage"),
                                "max_microvolt_vote": scalar_values(entry, "qcom,supply-max-voltage"),
                                "enable_load_vote_raw": scalar_values(entry, "qcom,supply-enable-load"),
                                "measured_module_current_or_rating": None})
    if len(variants) != 8 or sum(v["referenced_directly_by_leap_selector"] for v in variants) != 6:
        raise ValueError("Unexpected software variant set: requires fresh review")
    return {"schema": "razr-slide-oem-software-input-extraction-r3-v1", "source_bytes": proof,
            "actual_donor_panel_ID": None, "actual_donor_label_or_board_identity": None,
            "directly_included_main_panel_config_filenames": included_main_panel_configs,
            "selector_also_includes_667_1080x2640_config": any("-667-1080x2640-" in name for name in includes),
            "include_list_does_not_identify_selected_physical_module": True,
            "variants": sorted(variants, key=lambda v: v["file"]),
            "main_touch_software_compatible": main_touch_compatible,
            "main_touch_SPI_max_frequency_from_DT_Hz": scalar_values(main_touch, "spi-max-frequency"),
            "touch_compatible_literal_present": 'compatible = "goodix,gt9916P"' in touch,
            "USB_maximum_speed_high_speed_literal_present": 'maximum-speed = "high-speed"' in usb,
            "main_OLED_regulator_votes": regulator_votes,
            "regulator_votes_are_not_vendor_electrical_ratings": True,
            "charger_ID_maps_literal": ids,
            "charger_raw_pd_power_max": scalar_values(charger, "mmi,pd-power-max"),
            "charger_raw_max_fcc_ma": scalar_values(charger, "mmi,max-fcc-ma"),
            "charger_raw_values_not_converted_to_pack_current_ratings": True,
            "software_source_does_not_supply_package_geometry_or_manufacturing_netlist": True,
            "native_MCAD_received": False, "complete_native_ECAD_received": False,
            "hardware_qualification_performed": False, "manufacturing_go": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.cache_root)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"exact_sources": len(result["source_bytes"]), "software_variants": len(result["variants"]),
                      "directly_referenced_by_selector": sum(x["referenced_directly_by_leap_selector"] for x in result["variants"]),
                      "actual_donor_panel_ID": None, "manufacturing_go": False}))


if __name__ == "__main__":
    main()
