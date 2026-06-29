# config_orr.py — Table configuration for ORR Table 14.2.4.1.1
#
# This file defines WHAT the table computes. It uses the standard method
# templates from engine/method_templates.py. For a new table, copy this file
# and modify the sections marked with "CHANGE FOR YOUR TABLE".
#
# The CONFIG dict is consumed by engine/build_json.py.
#
# Usage:
#   python engine/build_json.py example_table/config_orr.py output/t_14_2_4_1_1.json

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from method_templates import get_standard_methods

# =============================================================================
# CHANGE FOR YOUR TABLE: Group order (in display order, left to right)
# =============================================================================
GROUP_ORDER = [
    'T-0.05-(28/28)', 'T-0.10-(14/21)', 'T-0.10-(21/21-14/21)',
    'T-0.10-(28/28)', 'T-0.15-(14/21)', 'T-0.15-(28/28)',
    'T-0.20-(14/21)', 'T-0.25-(14/21)', 'T-0.40-(28/28)'
]

# =============================================================================
# CHANGE FOR YOUR TABLE: Analysis set (population-level filter)
# =============================================================================
ANALYSIS_SET = {
    "id":   "AnalysisSet_01",
    "name": "Efficacy Analysis Set",
    "desc": "EASFL = Y",
    "condition": {"dataset": "ADRS", "variable": "EASFL", "comparator": "EQ", "value": ["Y"]}
}

# =============================================================================
# CHANGE FOR YOUR TABLE: Data subset (record-level filter)
#   Set to None if no subset is needed.
# =============================================================================
DATA_SUBSET = {
    "id":    "Dss_01",
    "name":  "Best Overall Response Records",
    "desc":  "PARAMCD = OVRLRESP",
    "label": "BOR records",
    "condition": {"dataset": "ADRS", "variable": "PARAMCD", "comparator": "EQ", "value": ["OVRLRESP"]}
}

# =============================================================================
# CHANGE FOR YOUR TABLE: Grouping (what defines the columns)
# =============================================================================
GROUPING = {
    "id":       "AnlsGrouping_01_ARMCD",
    "name":     "Dose Group (ARMCD)",
    "label":    "Dose Group",
    "dataset":  "ADRS",
    "variable": "ARMCD"
}

# =============================================================================
# DO NOT MODIFY unless you need custom methods
#   get_standard_methods() returns Mth_01 (denominator), Mth_02 (categorical),
#   and Mth_03 (ORR with CI).
#   To customize, copy one method from engine/method_templates.py and modify it.
# =============================================================================
METHODS = get_standard_methods()

# =============================================================================
# CHANGE FOR YOUR TABLE: Analyses — define each statistical computation
#
#   Essential fields per analysis:
#     id           — unique ID (An_01, An_02, An_03, ...)
#     list_name    — display name in the LOPA sublist
#     name         — analysis description
#     dataset      — ADaM dataset name (must match CSV filename without .csv)
#     variable     — analysis variable (column in the dataset)
#     methodId     — which method to use (Mth_01, Mth_02, Mth_03)
#     analysisSetId    — reference to analysis set (default: "AnalysisSet_01")
#     dataSubsetId     — reference to data subset (default: "Dss_01"; set to None to omit)
#     groupingId       — reference to grouping (default: GROUPING["id"])
#
#   For analyses with a denominator (Mth_02, Mth_03), also set:
#     has_denom → True (the build_json engine auto-generates referencedAnalysisOperations)
# =============================================================================
ANALYSES = [
    {
        "id":        "An_01",
        "list_name": "Subjects per Dose Group (N)",
        "name":      "Subjects per Dose Group",
        "dataset":   "ADRS",
        "variable":  "SUBJID",
        "methodId":  "Mth_01",
        "analysisSetId":  "AnalysisSet_01",
        "dataSubsetId":   "Dss_01",
        "groupingId":     "AnlsGrouping_01_ARMCD",
        "has_denom":      False
    },
    {
        "id":        "An_02",
        "list_name": "Response Categories by Dose Group",
        "name":      "Response Categories by Dose Group",
        "dataset":   "ADRS",
        "variable":  "AVALC",
        "methodId":  "Mth_02",
        "analysisSetId":  "AnalysisSet_01",
        "dataSubsetId":   "Dss_01",
        "groupingId":     "AnlsGrouping_01_ARMCD",
        "has_denom":      True,
        "denom_id":       "An_01"
    },
    {
        "id":        "An_03",
        "list_name": "ORR (CR+PR) by Dose Group",
        "name":      "ORR (CR+PR) with 95% CI by Dose Group",
        "dataset":   "ADRS",
        "variable":  "AVALC",
        "methodId":  "Mth_03",
        "analysisSetId":  "AnalysisSet_01",
        "dataSubsetId":   "Dss_01",
        "groupingId":     "AnlsGrouping_01_ARMCD",
        "has_denom":      True,
        "denom_id":       "An_01"
    }
]

# =============================================================================
# CHANGE FOR YOUR TABLE: Output display — table title, footnotes, etc.
#   These are metadata carried into the JSON; siera does not consume them,
#   but they are useful for documentation and potential downstream formatting.
# =============================================================================
OUTPUT = {
    "id":              "Out_01",
    "name":            "Table 14.2.4.1.1 ORR Summary (EAS)",
    "label":           "Table 14.2.4.1.1",
    "display_id":      "Disp_01",
    "display_name":    "ORR Table Display",
    "display_title":   "Table 14.2.4.1.1 Objective Response Rate (ORR) by Dose Group (EAS)",
    "rtf_filename":    "t_14_2_4_1_1_rtf.R",
    "display_sections": [
        {"sectionType": "Title", "orderedSubSections": [
            {"order": 1, "subSection": {"id": "Disp_Title_01", "text": "Table 14.2.4.1.1 ORR Summary by Dose Group (EAS)"}},
            {"order": 2, "subSection": {"id": "Disp_Title_02", "text": "Study Title — CHANGE FOR YOUR TABLE"}}
        ]},
        {"sectionType": "Rowlabel Header", "orderedSubSections": [
            {"order": 1, "subSection": {"id": "Disp_RowHdr_01", "text": "Characteristics"}}
        ]},
        {"sectionType": "Footnote", "orderedSubSections": [
            {"order": 1, "subSection": {"id": "Disp_Fn_01", "text": "CR=Complete Response; PR=Partial Response; SD=Stable Disease; PD=Progressive Disease; NE=Not Evaluable."}},
            {"order": 2, "subSection": {"id": "Disp_Fn_02", "text": "CI = Confidence Interval; N = subjects in analysis set; n = subjects in category."}},
            {"order": 3, "subSection": {"id": "Disp_Fn_03", "text": "a Percentage: n/N*100%."}},
            {"order": 4, "subSection": {"id": "Disp_Fn_04", "text": "b 95% CI based on Clopper-Pearson exact binomial method."}}
        ]}
    ]
}

# =============================================================================
# CHANGE FOR YOUR TABLE: Report-level metadata
# =============================================================================
REPORT_NAME   = "Clinical Study Report"
REPORT_ID     = "CSR"
LOPA_NAME     = "Objective Response Rate Summary by Dose Group (EAS)"
LOPA_LABEL    = "ORR Summary"
OUTPUT_NAME   = "Table 14.2.4.1.1 ORR Summary"

# =============================================================================
# Optional: default output JSON path
# =============================================================================
OUTPUT_JSON = "output/t_14_2_4_1_1_siera.json"


# =============================================================================
# DO NOT MODIFY BELOW — assembles the CONFIG dict
# =============================================================================
def _build_analyses(analyses):
    """Convert simplified analysis specs to siera-compatible format."""
    result = []
    for ana in analyses:
        entry = {
            "id": ana["id"],
            "version": 1,
            "name": ana["name"],
            "list_name": ana["list_name"],   # preserved for sublist building
            "categoryIds": ["ANSET_01", "ANSET_01_ANINT_01"],
            "analysisSetId": ana.get("analysisSetId", "AnalysisSet_01"),
            "dataset": ana["dataset"],
            "variable": ana["variable"],
            "methodId": ana["methodId"],
            "orderedGroupings": [
                {"order": 1, "groupingId": ana.get("groupingId", "AnlsGrouping_01"), "resultsByGroup": True}
            ]
        }
        if ana.get("dataSubsetId"):
            entry["dataSubsetId"] = ana["dataSubsetId"]

        # Auto-generate referencedAnalysisOperations for denominator analyses
        if ana.get("has_denom"):
            # Find the NUM relationship ID from the corresponding method
            method_id = ana["methodId"]
            num_rel_id = None
            den_rel_id = None
            for m in METHODS:
                if m["id"] == method_id:
                    for op in m.get("operations", []):
                        rels = op.get("referencedOperationRelationships", [])
                        for rel in rels:
                            role = rel.get("referencedOperationRole", {}).get("controlledTerm", "")
                            if role == "NUMERATOR":
                                num_rel_id = rel["id"]
                            elif role == "DENOMINATOR":
                                den_rel_id = rel["id"]
                    break
            if num_rel_id and den_rel_id:
                entry["referencedAnalysisOperations"] = [
                    {"referencedOperationRelationshipId": num_rel_id, "analysisId": ana["id"]},
                    {"referencedOperationRelationshipId": den_rel_id, "analysisId": ana["denom_id"]}
                ]
        result.append(entry)
    return result


CONFIG = {
    "report_name":   REPORT_NAME,
    "report_id":     REPORT_ID,
    "lopa_name":     LOPA_NAME,
    "lopa_label":    LOPA_LABEL,
    "output_name":   OUTPUT_NAME,
    "output_json":   OUTPUT_JSON,
    "group_order":   GROUP_ORDER,
    "analysis_set":  ANALYSIS_SET,
    "data_subset":   DATA_SUBSET,
    "grouping":      GROUPING,
    "methods":       METHODS,
    "analyses":      _build_analyses(ANALYSES),
    "output":        OUTPUT
}
