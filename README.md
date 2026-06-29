# ARS Pipeline Portable Tool — Quick Start


## What this is

A self-contained toolkit with **two** workflows for generating Analysis Results Data
(ARD) statistics via the `siera` R package:

| Workflow | Input | What you do | Best for |
|----------|-------|-------------|----------|
| **A — Excel-based** | `ARS Template.xlsx` (filled in) | Fill in the Excel sheet, run `excel2ars.py` | CDISC standard; no Python coding |
| **B — Config-based** | a `config_*.py` file | Copy `config_orr.py`, edit marked sections | Direct JSON control; derived endpoints with CI |

Both produce a JSON file that `siera::readARS()` converts to an R script.
When you source the R script, you get an ARD dataframe with counts, percentages,
and derived measures.

```
  Workflow A:                              Workflow B:
  ARS Template.xlsx                        config_<your_table>.py
       │                                        │
       ▼                                        ▼
  excel2ars.py                           engine/build_json.py
       │                                        │
       └─────────────┬──────────────────────────┘
                     ▼
              output/*.json
                     │
              run_pipeline.R
              (siera::readARS)
                     │
                     ▼
              ARD_Out_01.R
              (source → ARD dataframe)
```
Developed based on CDISC's analysis-result-standard repo: https://github.com/cdisc-org/analysis-results-standard.

## Prerequisites

| Tool     | Minimum version | Packages |
|----------|----------------|----------|
| Python   | 3.10            | **Workflow A**: `pip install openpyxl linkml-runtime` |
|          |                 | **Workflow B**: standard library only |
| R        | 4.6             | siera, cards, cardx, dplyr, readr, tidyr, broom, parameters |

You need to convert your dataset into .CSV format first.

```r
# One-time R package install:
install.packages(c("siera", "cards", "cardx", "dplyr", "readr", "tidyr", "broom", "parameters"))
```

## Quick Start — Workflow A (Excel-based, CDISC standard)

### 1. Fill in the Excel template

Open `excel_tools/ARS Template.xlsx`. It has ~25 sheets covering every ARS concept.
Fill in the sheets for your table:

| Sheet | What to fill in |
|-------|----------------|
| `ReportingEvent` | Study name, ID, version |
| `AnalysisSets` | Population filter (dataset, variable, comparator, value) |
| `DataSubsets` | Record-level filter (parameter, visit, etc.) |
| `AnalysisGroupings` | Grouping variable and group definitions |
| `AnalysisMethods` | Method name, operations, code template |
| `Analyses` | Link method to dataset, variable, set, subset, grouping |
| `Outputs` | Output name, label, display sections |
| `MainListOfContents` | Hierarchy of analyses within the output |
| `OtherListsOfContents` | Output-level metadata |

### 2. Convert Excel to JSON

```bash
cd ars_portable/excel_tools
python excel2ars.py -x "ARS Template.xlsx" -of json
```

This creates `ARS Template.json` in the same directory.

### 3. Generate and run the ARD script

Move the JSON to `output/`, then:

```r
# In R, from ars_portable/
source("run_pipeline.R")
source("output/ARD_Out_01.R")
print(ARD)
```

> **Note**: `excel2ars.py` uses the CDISC LinkML data model. The JSON it produces
> may differ in column structure from what siera expects. If siera fails, try
> Workflow B instead, or inspect the JSON against siera's `exampleARS_2.json`.

## Quick Start — Workflow B (Config-based, direct JSON control)

### 1. Build the JSON

```bash
cd ars_portable
python engine/build_json.py example_table/config_orr.py
```

This reads `example_table/config_orr.py` and writes `output/t_14_2_4_1_1_siera.json`.

### 2. Generate the ARD script

Open R in the `ars_portable/` directory:

```r
source("run_pipeline.R")
```

> **First time only**: edit `run_pipeline.R` line 10 — change `CONFIG_FILE` to point
> to your JSON file.  The example defaults to `output/t_14_2_4_1_1_siera.json`.

### 3. Run the ARD script

```r
source("output/ARD_Out_01.R")

# View results
print(ARD)

# Check specific analysis
ARD[ARD$AnalysisId == "An_01", c("variable_level", "stat")]       # N per arm
ARD[ARD$AnalysisId == "An_02", c("group1_level", "variable_level", "stat_name", "stat")]  # categories
ARD[ARD$AnalysisId == "An_03", c("group1_level", "stat_name", "stat")]                    # ORR + CI
```

> `stat` is a list column — use `unlist(ARD$stat)` to get numeric values.

## For a New Table

1. **Copy** `example_table/config_orr.py` → `example_table/config_<your_table>.py`

2. **Edit the config file** — the sections marked `CHANGE FOR YOUR TABLE`:
   - `GROUP_ORDER` — your treatment arms or groups in display order
   - `ANALYSIS_SET` — population filter variable and value
   - `DATA_SUBSET` — record-level filter (or set to `None`)
   - `GROUPING` — variable that defines the columns
   - `ANALYSES` — what to compute (you rarely need to change this for frequency tables)
   - `OUTPUT` — table title, footnotes
   - Report-level metadata (name, ID, labels)

3. **If you need a different derived endpoint** (e.g. DCR instead of ORR):
   - Open `engine/method_templates.py`
   - Copy `MTH_ORR_CI`, paste below it, rename and modify
   - Change the filter values: `c('CR', 'PR')` → `c('CR', 'PR', 'SD')` for DCR
   - Change operation IDs accordingly
   - Import and use your new method in your config file

4. **Build and run** as above.

## Files

| File | Role | Do I modify it? |
|------|------|-----------------|
| `run_pipeline.R` | Entry point for siera | Change `CONFIG_FILE` path |
| `PIPELINE_GUIDE.md` | Full walkthrough with troubleshooting | No |
| **Engine (Workflow B)** | | |
| `engine/build_json.py` | JSON assembly engine | No |
| `engine/method_templates.py` | Standard R code templates | Only for new stat methods |
| `engine/siera_patch.R` | Fixes siera 0.5.6 bug | No |
| **Example config (Workflow B)** | | |
| `example_table/config_orr.py` | ORR table example | **Copy + adapt** |
| **Excel tools (Workflow A)** | | |
| `excel_tools/ARS Template.xlsx` | Master Excel template | **Fill in** for your table |
| `excel_tools/excel2ars.py` | Excel → JSON converter | No |
| `excel_tools/ars2excel.py` | JSON → Excel (round-trip) | No |
| `excel_tools/excel2yaml.py` | Excel → YAML converter | No |
| `excel_tools/list_of_contents.py` | Generate LoC from JSON | No |
| `excel_tools/ars_ldm.py` | CDISC LinkML data model | No |
| `excel_tools/ars_ldm_api.py` | LinkML API helper | No |
| `excel_tools/requirements.txt` | Python deps for Workflow A | No |
| **Generated** | | |
| `output/*.json` | Generated JSON | No (auto-generated) |
| `output/ARD_Out_*.R` | Generated R script | No (auto-generated) |

## Known siera 0.5.6 Bugs (patched at runtime)

1. **`anas[3, ]` hardcoded** — crashes for < 3 analyses.
2. **`referencedAnalysisOperations` needs 2 entries** — NUM + DEN, in that order.
3. **Custom templates need `as.list()`** — `stat` must be a list column to match `cards` output.

All three are handled automatically — `engine/build_json.py` generates correct JSON,
and `run_pipeline.R` applies the siera patch before calling `readARS()`.

## CSV Requirements

- CSV filenames must match the `dataset` field in your analyses (e.g. `"ADRS"` → `ADRS.csv`)
- Clean embedded single quotes from flag columns (`'Y'` → `Y`) during SAS export
- CSV files must be in the directory specified by `ADAM_PATH` in `run_pipeline.R`
