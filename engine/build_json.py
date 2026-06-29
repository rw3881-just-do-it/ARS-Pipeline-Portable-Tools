"""
build_json.py — Build a siera-compatible ARS JSON file from a table config.

This is the engine. You give it a config dict (from a config_*.py file) and it
assembles and writes the JSON that siera::readARS() expects.

Usage:
    python engine/build_json.py example_table/config_orr.py

Or import it:
    from engine.build_json import build_and_write
    from example_table.config_orr import CONFIG
    build_and_write(CONFIG, "output/t_14_2_4_1_1.json")

The config dict controls WHAT the table does (filters, groups, labels).
This file controls HOW the JSON is assembled.
"""

import json
import sys
import os


def build_reporting_event(config):
    """
    Build a complete ARS ReportingEvent dict from a table config.

    Parameters
    ----------
    config : dict
        A config dict with the following keys:
        - report_name, report_id
        - analysis_set    (id, name, desc, condition dict)
        - data_subset     (id, name, desc, condition dict)
        - grouping        (id, name, variable, groups list)
        - methods         (list of method dicts from method_templates)
        - analyses        (list of analysis dicts)
        - output          (id, name, label, display sections)
        - group_order     (list of group values in display order)
        - lopa_name       (name of the analysis block)
        - lopa_label      (short label)
        - output_name     (output name for LOPO)

    Returns
    -------
    dict
        The complete ARS ReportingEvent JSON structure.
    """
    c = config

    # Build group entries from group_order
    group_entries = []
    for i, grp_val in enumerate(c["group_order"]):
        group_entries.append({
            "id": f"{c['grouping']['id']}_{i+1:02d}",
            "name": str(grp_val),
            "label": str(grp_val),
            "level": 1,
            "order": i + 1,
            "condition": {
                "dataset": c["grouping"]["dataset"],
                "variable": c["grouping"]["variable"],
                "comparator": "EQ",
                "value": [grp_val]
            }
        })

    # Build sublist from analyses
    sublist_items = []
    for i, ana in enumerate(c["analyses"]):
        sublist_items.append({
            "name": ana["list_name"],
            "level": 2,
            "order": i + 1,
            "analysisId": ana["id"]
        })

    ars = {
        "name": c["report_name"],
        "id": c["report_id"],
        "version": 1,
        "@type": "ReportingEvent",

        # --- Content lists ---
        "mainListOfContents": {
            "name": "List of Planned Analyses",
            "label": "LOPA",
            "contentsList": {
                "listItems": [{
                    "name": c["lopa_name"],
                    "label": c["lopa_label"],
                    "level": 1,
                    "order": 1,
                    "outputId": c["output"]["id"],
                    "sublist": {"listItems": sublist_items}
                }]
            }
        },
        "otherListsOfContents": [{
            "name": "List of Planned Outputs",
            "label": "LOPO",
            "contentsList": {
                "listItems": [{
                    "name": c["output_name"],
                    "label": c["output"]["label"],
                    "level": 1,
                    "order": 1,
                    "outputId": c["output"]["id"]
                }]
            }
        }],

        # --- Taxonomies ---
        "analysisOutputCategorizations": [{
            "id": "ANSET",
            "label": "Analysis Sets",
            "categories": [{
                "id": "ANSET_01",
                "label": c.get("category_label", "Efficacy"),
                "subCategorizations": [{
                    "id": "ANSET_01_ANINT",
                    "label": "Analysis Of Interest",
                    "categories": [{
                        "id": "ANSET_01_ANINT_01",
                        "label": c.get("subcategory_label", "Primary")
                    }]
                }]
            }]
        }],

        # --- Analysis set ---
        "analysisSets": [{
            "id": c["analysis_set"]["id"],
            "name": c["analysis_set"]["name"],
            "description": c["analysis_set"]["desc"],
            "level": 1,
            "order": 1,
            "condition": c["analysis_set"]["condition"]
        }],

        # --- Data subset ---
        "dataSubsets": [{
            "id": c["data_subset"]["id"],
            "name": c["data_subset"]["name"],
            "description": c["data_subset"]["desc"],
            "label": c["data_subset"]["label"],
            "level": 1,
            "order": 1,
            "condition": c["data_subset"]["condition"]
        }],

        # --- Grouping ---
        "analysisGroupings": [{
            "id": c["grouping"]["id"],
            "name": c["grouping"]["name"],
            "label": c["grouping"]["label"],
            "groupingDataset": c["grouping"]["dataset"],
            "groupingVariable": c["grouping"]["variable"],
            "dataDriven": False,
            "groups": group_entries
        }],

        # --- Methods (from method_templates) ---
        "methods": c["methods"],

        # --- Analyses ---
        "analyses": c["analyses"],

        # --- Outputs ---
        "outputs": [{
            "id": c["output"]["id"],
            "version": 1,
            "name": c["output"]["name"],
            "label": c["output"]["label"],
            "categoryIds": ["ANSET_01", "ANSET_01_ANINT_01"],
            "displays": [{
                "order": 1,
                "display": {
                    "id": c["output"].get("display_id", "Disp_01"),
                    "name": c["output"].get("display_name", "Table Display"),
                    "version": 1,
                    "displayTitle": c["output"].get("display_title", c["output"]["name"]),
                    "displaySections": c["output"]["display_sections"]
                }
            }],
            "programmingCode": {
                "context": "R",
                "code": c["output"].get("rtf_filename", "output.rtf"),
                "parameters": [
                    {"name": "output_format", "value": ["rtf"]},
                    {"name": "orientation", "value": ["landscape"]}
                ]
            }
        }]
    }

    return ars


def build_and_write(config, output_path):
    """
    Build a JSON file from a config and write it to disk.

    Parameters
    ----------
    config : dict
        Table config dict (see build_reporting_event).
    output_path : str
        Path to write the JSON file to.
    """
    ars = build_reporting_event(config)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ars, f, indent=2, ensure_ascii=False)
    print(f"JSON written to {output_path}")
    return ars


# === CLI entry point ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python engine/build_json.py <config_module_path> [output_json_path]")
        print("Example: python engine/build_json.py example_table/config_orr.py")
        sys.exit(1)

    config_path = sys.argv[1]

    # Allow running from any directory — add cwd to path
    sys.path.insert(0, os.getcwd())

    # Import the config module by path
    import importlib.util
    spec = importlib.util.spec_from_file_location("table_config", config_path)
    cfg_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_module)

    config = cfg_module.CONFIG

    # Default output path
    out = sys.argv[2] if len(sys.argv) > 2 else config.get("output_json", "output.json")
    build_and_write(config, out)
