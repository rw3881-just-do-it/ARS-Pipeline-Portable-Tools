# Running the ARS Standard Pipeline — Step-by-Step Guide

*Last updated: 2026-06-25*

This guide walks through the end-to-end process for the Analysis Results Standard
(ARS) pipeline. By the end, you will have a generated `.R` script that computes
an ARD (Analysis Results Data) dataframe with counts, percentages, and
derived measures.

The toolkit provides **two ways** to get to the same JSON file:

| Workflow | What you do | What you need | What it's best for |
|----------|-------------|---------------|-------------------|
| **A — Excel** | Fill in `excel_tools/ARS Template.xlsx`, then run `excel2ars.py` | `ARS Template.xlsx` + `pip install openpyxl linkml-runtime` | CDISC standard workflow; no Python coding needed |
| **B — Python config** | Copy `example_table/config_orr.py`, edit the marked sections, then run `engine/build_json.py` | Python 3.10+ (standard library) | Direct JSON control; derived endpoints like ORR with CI; batch generation |

**This guide covers both workflows.** Workflow B is covered in detail (Sections 2-6)
because it gives you full control. Workflow A is simpler but has known differences
in JSON structure from what siera expects — see Section 7.

---

## Overview

```
  Workflow A (Excel):                    Workflow B (Python config):
  excel_tools/                           example_table/
  ARS Template.xlsx                      config_<your_table>.py
       │                                      │
       ▼                                      ▼
  excel2ars.py                         engine/build_json.py
       │                                      │
       └──────────────┬───────────────────────┘
                      ▼
               your_table.json
                      │
              run_pipeline.R
              (siera::readARS)
                      │
                      ▼
              ARD_Out_XX.R
              (source → ARD dataframe)
```

**What this pipeline produces**: an R script (`ARD_Out_XX.R`) that, when sourced,
creates an ARD dataframe — a structured table of statistics (counts, proportions,
derived endpoints with CIs) ready for verification and formatting.

**What this pipeline does NOT produce**: a formatted table (RTF, PDF, HTML). That is a
separate, downstream step not covered here.

---

## 1. Prerequisites

### 1.1 Required software

| Software | Version tested | Check with |
|----------|---------------|------------|
| Python | 3.10+ | `python --version` |
| R | 4.6.0+ | `R --version` |

### 1.2 Required Python packages

```bash
pip install openpyxl pyreadstat pandas
```

| Package | Used for |
|---------|----------|
| `pyreadstat` | Reading SAS `.sas7bdat` → CSV export |
| `pandas` | Data validation and manipulation |
| `openpyxl` | Optional: if using the Excel-based `excel2ars.py` route |

### 1.3 Required R packages

```r
install.packages(c("siera", "cards", "cardx", "dplyr", "readr", "tidyr", "broom", "parameters"))
```

| Package | Tested version | Used for |
|---------|---------------|----------|
| `siera` | 0.5.6 | Parsing ARS metadata and generating R scripts |
| `cards` | 0.8.0 | Statistical analysis (`ard_categorical()`) |
| `cardx` | 0.3.3 | Extra statistical method support |
| `dplyr` | 1.2.1 | Data manipulation |
| `readr` | 2.2.0 | Reading CSV files into R |
| `tidyr` | 1.3.2 | Data reshaping (`replace_na()` etc.) |
| `broom` | 1.0.13 | Tidying statistical test output |
| `parameters` | 0.29.1 | Parameter formatting |

### 1.4 Repository structure

```
analysis-results-standard/
├── utilities/
│   └── python/
│       ├── ARS Template.xlsx     ← Master Excel template
│       ├── excel2ars.py          ← Excel → JSON converter
│       └── ars2excel.py          ← JSON → Excel converter (round-trip)
└── my_testing/                   ← Example working directory (this study)
    ├── adsl.sas7bdat             ← ADSL SAS dataset
    ├── adrs.sas7bdat             ← ADRS SAS dataset
    ├── ADSL.csv                  ← ADSL exported to CSV
    ├── ADRS.csv                  ← ADRS exported to CSV
    ├── build_siera_json.py       ← Example: builds siera-compatible JSON
    ├── run_siera.R               ← Example: patches siera + runs readARS()
    └── patch_siera.R             ← Example: standalone siera bug fix
```

The files in `my_testing/` are **task-specific** — they are the working example for
this guide's study (ORR Table 14.2.4.1.1). For your own task, you will create
your own working directory with analogous files.

---

## 2. Step-by-Step Walkthrough

### Step 1: Export SAS data to CSV

siera only reads CSV files — it does NOT read SAS `.sas7bdat` directly.
Export your ADaM datasets using either Python (pyreadstat) or R (haven).

**Option A — Python:**
```python
import pyreadstat
import pandas as pd

df, meta = pyreadstat.read_sas7bdat("path/to/adrs.sas7bdat")

# Clean: remove embedded single quotes (e.g. 'Y' → Y)
# Some CDISC pilot datasets store flag values as 'Y' with literal quotes.
# siera's read_csv() will NOT strip these.
for col in df.columns:
    if df[col].dtype == object:
        df[col] = df[col].apply(lambda x: x.replace("'", "") if isinstance(x, str) else x)

df.to_csv("path/to/ADRS.csv", index=False)
```

**Option B — R:**
```r
library(haven)
adrs <- read_sas("path/to/adrs.sas7bdat")
clean <- function(x) { if(is.character(x)) gsub("'", "", x) else x }
adrs <- as.data.frame(lapply(adrs, clean))
write.csv(adrs, "path/to/ADRS.csv", row.names = FALSE)
```

> **Critical**: Always check for embedded single quotes in your data. Values like
> `'Y'` (with literal quotes) will fail to match filter conditions like
> `EASFL == 'Y'` in R. Clean them during export.

### Step 2: Profile your data

Before building the template, run exploratory checks in R to confirm your
assumptions about the data:

```r
# Load the CSV you just exported
adrs <- read.csv("path/to/ADRS.csv")

# What population flags exist and what do they filter?
table(adrs$EASFL)       # Example: Y=xxx, N=xxx

# What parameters (PARAMCD) exist?
table(adrs$PARAMCD)

# For your target parameter, what are the actual values?
table(adrs$AVALC[adrs$PARAMCD == "OVRLRESP"])

# What treatment arms exist?
table(adrs$ARMCD)

# How many unique subjects match your criteria?
length(unique(adrs$USUBJID[adrs$EASFL == "Y" & adrs$PARAMCD == "OVRLRESP"]))
```

> **Why this matters**: ARS metadata defines filters in exact terms. If you write
> `ANL01FL == "Y"` in your JSON but the data actually has blank `ANL01FL` for the
> records you need, the filter will return zero rows. Profile your data first.

### Step 3: Build the siera-compatible JSON file

This is the core step — you need to produce a JSON file that describes your
analyses in siera's expected format. **Choose your workflow:**

#### Workflow A (Excel-based)

Fill in the provided Excel template and convert it to JSON:

1. Open `excel_tools/ARS Template.xlsx` and fill in the relevant sheets
2. Install dependencies: `pip install openpyxl linkml-runtime`
3. Run: `cd excel_tools && python excel2ars.py -x "ARS Template.xlsx" -of json`
4. Move the generated `.json` file into the `output/` directory

> **Caveat**: The JSON produced by `excel2ars.py` uses the CDISC LinkML data model.
> Its column structure may differ from what siera 0.5.6's JSON reader expects,
> particularly in the flattening of nested objects like `referencedAnalysisOperations`.
> If siera fails with errors about missing columns, switch to Workflow B.

#### Workflow B (Python config — recommended)

Write a short Python config file that builds the JSON directly:

1. Copy `example_table/config_orr.py` → `example_table/config_<your_table>.py`
2. Edit the sections marked `CHANGE FOR YOUR TABLE` (see Section 3)
3. Run: `python engine/build_json.py example_table/config_<your_table>.py`
4. The JSON lands in `output/`

This guide uses **Workflow B** for the remaining sections because it gives you
full control over the JSON structure and supports derived endpoints (ORR with CI).

The JSON has 8 required top-level sections:

| Section | What it defines |
|---------|----------------|
| `analysisSets` | Population-level filter (e.g. `EASFL == "Y"`) |
| `dataSubsets` | Record-level filter (e.g. `PARAMCD == "OVRLRESP"`) |
| `analysisGroupings` | Grouping variable, group definitions, group labels |
| `methods` | Statistical method name, operations, and **R code template with parameter map** |
| `analyses` | Ties a method to a dataset, variable, analysis set, data subset, grouping, and denominator |
| `mainListOfContents` | Hierarchy of analyses within each output |
| `otherListsOfContents` | Output-level metadata (name, ID) |
| `analysisOutputCategorizations` | Output categorization taxonomy |

#### A typical two-table pattern: frequency table with derived endpoint

A frequency table like ORR typically needs **3 analyses**:

| Analysis | Purpose | Method | Example |
|----------|---------|--------|---------|
| An_01 | N per group (denominator) | Mth_01 — simple count | Count distinct SUBJID per ARMCD |
| An_02 | n, % per category per group | Mth_02 — grouped summary | Count AVALC categories per ARMCD |
| An_03 | Derived endpoint (e.g. ORR + 95% CI) | Mth_03 — custom R | Count CR+PR per ARMCD, compute CI |

Each analysis is linked through `referencedAnalysisOperations`: An_02 and An_03
both reference An_01 as their denominator.

#### The method code template system

Each method contains an R code template with **placeholders** that siera replaces
at generation time. Placeholders are defined as `parameters` mapping `name`
(the placeholder string in the template) to `valueSource` (a variable siera makes
available in its generation loop).

Example — Mth_01 (simple count):
```json
{
    "name": "anavarhere",           // placeholder in the R code
    "valueSource": "ana_var"        // siera variable: the analysis$variable field
}
```

After substitution, `dplyr::select(anavarhere, groupvar1here)` becomes
`dplyr::select(SUBJID, ARMCD)`.

**Available valueSource variables** (set by siera's internal loop):

| valueSource | What it resolves to | Example value |
|-------------|-------------------|---------------|
| `ana_var` | `analysis.variable` | `"SUBJID"` or `"AVALC"` |
| `AG_var1` | First grouping variable | `"ARMCD"` |
| `DEN_analysisid` | Denominator analysis ID | `"An_01"` |
| `AG_denom_var1` | Denominator's grouping variable | `"ARMCD"` |
| `by_vars` | `by`/`variables` statement for `cards` | `", variables = 'ARMCD'"` |
| `by_listc` | Grouping variables as character vector | `"'ARMCD'"` |
| `distinct_list` | All distinct-relevant variables | `"ARMCD, AVALC"` |
| `AG_max_dataDriven` | Whether grouping is data-driven | `"FALSE"` |

> **Important constraint**: siera does NOT let you define custom `valueSource`
> variables. You can only use what siera already computes in its generation loop.
> For Mth_03 (ORR with CI), we use only `ana_var` and `AG_var1` and write
> the rest of the logic directly in the template using R's base/stats packages.

### Step 4: Run siera to generate the ARD script

siera 0.5.6 has a known bug (see Section 6) that must be patched at runtime before
calling `readARS()`. The file `my_testing/run_siera.R` handles this:

```r
setwd("path/to/your/working/directory")
source("run_siera.R")
```

What `run_siera.R` does:
1. Loads `siera`
2. Patches `.generate_analysis_set_code()` (idempotent — skips if already patched)
3. Calls `siera::readARS("your_file.json", adam_path = ".", output_path = ".")`
4. Lists generated `.R` files

The `readARS()` arguments:
- `ARS_path` — path to your JSON file
- `adam_path` — directory containing CSV files (siera matches `<dataset>.csv`)
- `output_path` — directory where `.R` scripts are written

### Step 5: Run the generated ARD script

```r
source("ARD_Out_01.R")

# View the ARD dataframe
print(ARD)
View(ARD)      # In RStudio
```

The ARD contains columns like:

| Column | Description | Example |
|--------|-------------|---------|
| `group1_level` | Group level label | `"T-0.05-(28/28)"` |
| `variable_level` | Variable level (category) | `"CR"`, `"PR"` |
| `stat_name` | Statistic name | `"n"`, `"p"`, `"ci_lower"`, `"ci_upper"` |
| `stat` | Statistic value (list column) | `4`, `0.25`, `0.046`, `0.699` |
| `operationid` | Method operation ID | `"Mth_01_01_n"`, `"Mth_03_03_ci_lower"` |
| `AnalysisId` | Which analysis produced this row | `"An_01"`, `"An_02"`, `"An_03"` |
| `OutputId` | Which output this belongs to | `"Out_01"` |

> **Note**: `stat` is a **list column** (each value wrapped in `list()`).
> To extract numeric values, use `unlist(ARD$stat)`.

### Step 6: Verify results against known data counts

```r
# N per arm (denominator — An_01)
n_per_arm <- ARD[ARD$AnalysisId == "An_01", c("variable_level", "stat")]
print(n_per_arm)
sum(unlist(n_per_arm$stat))  # Total unique subjects

# Response categories per arm (An_02)
n_pct <- ARD[ARD$AnalysisId == "An_02",
             c("group1_level", "variable_level", "stat_name", "stat")]
print(n_pct, n = 50)

# Derived ORR with 95% CI (An_03)
orr <- ARD[ARD$AnalysisId == "An_03",
           c("group1_level", "stat_name", "stat")]
print(orr, n = 50)
```

Cross-check key numbers against what you found in Step 2. For example:
- `sum(unlist(n_per_arm$stat))` should equal the unique subject count from Step 2
- The total N for each arm from An_01 should match the denominator used in An_02/An_03
- ORR (CR+PR) counts per arm should be manually verifiable from the raw data

---

## 3. Adapting `build_siera_json.py` for a New Table

The example script `my_testing/build_siera_json.py` is designed to be adapted.
Below is a section-by-section guide to what you change and what stays the same.

### 3.1 Data validation section (lines 9-18)

```python
df, meta = pyreadstat.read_sas7bdat("my_testing/adrs.sas7bdat")

def clean(s):
    if isinstance(s, str): return s.replace("'", "")
    return str(s)

for col in ['EASFL','PARAMCD','AVALC','ARMCD','SUBJID']:
    df[col] = df[col].apply(clean)

sub = df[(df['EASFL']=='Y') & (df['PARAMCD']=='OVRLRESP')]
print(f"Data: {len(sub)} OVRLRESP records, {sub['SUBJID'].nunique()} unique subjects")
```

**What to change:**
- Path to your SAS file
- Column list in `for col in [...]` — the columns you'll reference in the JSON
- Filter conditions in `sub = df[...]` — match your analysis set + parameter
- Print statement — update to describe your data

This section is optional validation. You can delete it if you already know your data.

### 3.2 Group order (line 20-24)

```python
arm_order = [
    'T-0.05-(28/28)', 'T-0.10-(14/21)', 'T-0.10-(21/21-14/21)',
    'T-0.10-(28/28)', 'T-0.15-(14/21)', 'T-0.15-(28/28)',
    'T-0.20-(14/21)', 'T-0.25-(14/21)', 'T-0.40-(28/28)'
]
```

**What to change:** Replace with your actual group/arm values in display order.

### 3.3 `analysisSets` (lines 81-89)

```python
"analysisSets": [
    {
        "id": "AnalysisSet_01",
        "name": "Efficacy Analysis Set",
        "description": "EASFL = Y",
        "level": 1,
        "order": 1,
        "condition": {"dataset": "ADRS", "variable": "EASFL", "comparator": "EQ", "value": ["Y"]}
    }
],
```

**What to change:**
- `condition.dataset` — your ADaM dataset name (must match CSV filename)
- `condition.variable` — your population flag variable
- `condition.value` — the flag value that defines the population

### 3.4 `dataSubsets` (lines 91-100)

```python
"dataSubsets": [
    {
        "id": "Dss_01",
        "name": "Best Overall Response Records",
        "description": "PARAMCD = OVRLRESP",
        "label": "BOR records",
        "level": 1,
        "order": 1,
        "condition": {"dataset": "ADRS", "variable": "PARAMCD", "comparator": "EQ", "value": ["OVRLRESP"]}
    }
],
```

**What to change:**
- `condition.variable` — the record-level filter variable (e.g. `"PARAMCD"`)
- `condition.value` — the value that selects the right records
- `name` / `description` — describe what this subset means for your table

### 3.5 `analysisGroupings` (lines 102-115)

```python
"analysisGroupings": [
    {
        "id": "AnlsGrouping_01_ARMCD",
        "name": "Dose Group (ARMCD)",
        "label": "Dose Group",
        "groupingDataset": "ADRS",
        "groupingVariable": "ARMCD",
        "dataDriven": False,
        "groups": [
            {"id": "AnlsGrouping_01_ARMCD_01", "name": "0.05mg (28/28)", "label": "0.05mg",
             "level": 1, "order": i+1,
             "condition": {"dataset": "ADRS", "variable": "ARMCD", "comparator": "EQ", "value": [arm]}}
            for i, arm in enumerate(arm_order)
        ]
    }
],
```

**What to change:**
- `groupingVariable` — your grouping variable (e.g. `"ARMCD"`, `"TRT01P"`)
- `groupingDataset` — dataset containing the grouping variable
- The `groups` list — generated from your group order list (see 3.2)
- Group `name` and `label` — human-readable labels for each group

For a **second grouping dimension** (e.g. ARMCD × AVISIT), add a second
grouping factor with a different `id`.

### 3.6 `methods` — the code templates

This is the most complex section. Three method patterns are provided:

#### Mth_01 — Simple count (denominator)

Counts unique subjects per group. Uses `cards::ard_categorical()`.

**Rarely needs modification** — it's a standard denominator pattern.

#### Mth_02 — Grouped categorical summary (numerator)

Counts categories per group with percentage using a denominator reference.
Uses `cards::ard_categorical()` with `denominator`.

**What to change if the analysis variable changes:**
- Operation IDs and names can stay the same pattern
- The `referencedOperationRelationships` DEN entry's `analysisId` — point to your
  denominator analysis (An_01 equivalent)

#### Mth_03 — Derived endpoint with CI

This is a **custom R template** — it does NOT use `cards`. Instead, it uses
base R + `stats::binom.test()` + `dplyr` to:

1. Count distinct subjects per group
2. Filter for specific response values (CR + PR)
3. Join with N per group
4. Compute `binom.test()` confidence interval
5. Pivot results into a long-format dataframe compatible with the ARD

**What to change:**
- `name` / `label` / `description` — rename for your derived endpoint
- The response filter values: `AVALC %in% c('CR', 'PR')` → your categories
- The CI method: `stats::binom.test()` is standard for proportions; change to
  another method if needed
- Operation IDs — update to match your naming convention

**Critical detail — `stat` must be a list column**: The `cards` package stores
statistics as list-type columns. Any custom R template must do the same, or
`dplyr::bind_rows()` will fail when combining analyses. Use `as.list()`:

```r
# Wrong (produces numeric column):
stat = as.numeric(n_orr)

# Correct (produces list column, compatible with cards output):
stat = as.list(as.numeric(n_orr))
```

### 3.7 `analyses` (lines 200-232)

Each analysis object ties everything together:

```python
{
    "id": "An_02",
    "version": 1,
    "name": "Response Categories by Dose Group",
    "categoryIds": ["ANSET_01", "ANSET_01_ANINT_01"],
    "analysisSetId": "AnalysisSet_01",
    "dataSubsetId": "Dss_01",
    "dataset": "ADRS",
    "variable": "AVALC",
    "methodId": "Mth_02",
    "orderedGroupings": [{"order": 1, "groupingId": "AnlsGrouping_01_ARMCD", "resultsByGroup": True}],
    "referencedAnalysisOperations": [
        {"referencedOperationRelationshipId": "Mth_02_02_pct_NUM", "analysisId": "An_02"},
        {"referencedOperationRelationshipId": "Mth_02_02_pct_DEN", "analysisId": "An_01"}
    ]
},
```

**What to change for each analysis:**
- `dataset` — ADaM dataset name (must match CSV filename)
- `variable` — analysis variable (e.g. `"SUBJID"` for count, `"AVALC"` for categories)
- `methodId` — which method this analysis uses
- `analysisSetId` / `dataSubsetId` — references to your filter definitions
- `orderedGroupings[].groupingId` — reference to your grouping definition

**`referencedAnalysisOperations` rules:**
1. An analysis with **no denominator** (e.g. An_01, the denominator itself) —
   omit this field entirely
2. An analysis with a denominator needs **exactly 2 entries**:
   - Entry 1: NUM self-reference (points to its own ID)
   - Entry 2: DEN cross-reference (points to the denominator analysis ID)
3. The `referencedOperationRelationshipId` must match an operation relationship
   ID defined in the method's operations

### 3.8 `mainListOfContents` — sublist

```python
"sublist": {
    "listItems": [
        {"name": "Subjects per Dose Group (N)", "level": 2, "order": 1, "analysisId": "An_01"},
        {"name": "Response Categories by Dose Group", "level": 2, "order": 2, "analysisId": "An_02"},
        {"name": "ORR (CR+PR) by Dose Group", "level": 2, "order": 3, "analysisId": "An_03"}
    ]
}
```

**What to change:** Add/remove list items to match your analyses. Each item's
`analysisId` must match an analysis ID defined in the `analyses` section.

### 3.9 `outputs` — table metadata

Change the `name`, `label`, `displayTitle`, and display sections (title text,
footnotes) to match your table. This metadata is carried into the JSON but is
not consumed by siera — it's for documentation and potential downstream formatting.

### 3.10 Checklist for adapting to a new table

- [ ] Update SAS file path and column names in the validation section (or remove it)
- [ ] Replace `arm_order` with your group values in display order
- [ ] Update `analysisSets`: filter variable and value
- [ ] Update `dataSubsets`: filter variable and value (or remove if not needed)
- [ ] Update `analysisGroupings`: grouping variable and group labels
- [ ] Update `methods[].codeTemplate.code`: R code if the analysis logic differs
- [ ] Update `methods[].operations`: operation IDs and names
- [ ] Update `analyses[]`: dataset, variable, methodId, groupingId, referencedAnalysisOperations
- [ ] Update `mainListOfContents.sublist.listItems`: match your analyses
- [ ] Update `outputs[]`: name, label, display title, footnotes
- [ ] Update `otherListsOfContents.listItems[]`: output name and ID
- [ ] Update `analysisOutputCategorizations`: category IDs and labels

---

## 4. Files Provided vs. Files You Write

### Repository files (reusable — do not modify)

| File | Location | Purpose |
|------|----------|---------|
| `excel2ars.py` | `utilities/python/` | Excel → JSON converter (Path A — not used in this guide) |
| `ars2excel.py` | `utilities/python/` | JSON → Excel converter (round-trip validation) |
| `ARS Template.xlsx` | `utilities/python/` | Master Excel template for Path A |

### Example files (copy and adapt for your task)

| File | Location | What to change |
|------|----------|---------------|
| `build_siera_json.py` | `my_testing/` | See Section 3 — adapt for your table's filters, groups, methods |
| `run_siera.R` | `my_testing/` | Change the `ARS_path` argument to your JSON filename |
| `patch_siera.R` | `my_testing/` | No changes needed — reusable as-is |

### Files you create from scratch

| File | How to create |
|------|-------------|
| `ADSL.csv`, `ADRS.csv` | Step 1 — export from SAS via pyreadstat or haven |
| `your_table.json` | Step 3 — adapt `build_siera_json.py` and run it |
| `ARD_Out_XX.R` | Step 4 — generated by siera (do not edit) |

### Quick-start: adapting `run_siera.R`

The only line you need to change is the JSON filename:

```r
siera::readARS(
  ARS_path    = "your_table.json",   # ← change this
  output_path = ".",
  adam_path   = "."
)
```

---

## 5. Clean Run Checklist (from scratch)

```bash
# 1. Export SAS to CSV (Python or R — do once per dataset)
python -c "
import pyreadstat, pandas as pd
df, _ = pyreadstat.read_sas7bdat('path/to/adrs.sas7bdat')
for c in df.columns:
    if df[c].dtype == object:
        df[c] = df[c].apply(lambda x: x.replace(\"'\", '') if isinstance(x, str) else x)
df.to_csv('path/to/ADRS.csv', index=False)
print(f'ADRS.csv written: {len(df)} rows')
"

# 2. Profile data (R)
#    table(adrs$EASFL); table(adrs$PARAMCD); table(adrs$ARMCD)

# 3. Adapt and run build script
python build_siera_json.py
#    Verify: JSON written successfully

# 4. Generate ARD script (R)
#    setwd("your/working/directory")
#    source("run_siera.R")
#    Verify: ARD_Out_01.R created

# 5. Run the ARD script (R)
#    source("ARD_Out_01.R")
#    sum(unlist(ARD[ARD$AnalysisId == "An_01", "stat"]))  # Cross-check count
```

---

## 6. Known siera 0.5.6 Bugs and Workarounds (as of 2026-06-25)

### Bug 1: Hardcoded `anas[3, ]` index

**Location**: `.generate_analysis_set_code()`, internal to siera.

**Symptom**: `gsub("analysisADAMhere", ana_adam2, code)` fails with
"invalid replacement" when an output has fewer than 3 analyses.

**Cause**: The function hardcodes `Anas_2 <- anas[3, ]$listItem_analysisId` to
check whether the analysis set's condition dataset differs from the analysis dataset.
Row 3 doesn't exist for outputs with 1-2 analyses, so `Anas_s2$dataset` is empty.

**Fix**: `patch_siera.R` (or `run_siera.R`) replaces the line with:
`Anas_2 <- anas[min(2, nrow(anas)), ]$listItem_analysisId`
This is safe for 2 or 3+ analyses — the result is only used when analysis set
and analysis datasets differ, which is rare.

### Bug 2: Missing `referencedAnalysisOperations` entry crashes DEN_analysisid

**Symptom**: `dplyr::filter()` error: "..1 must be of size 2 or 1, not size 0."

**Cause**: siera's JSON reader assigns `row_number()` to each entry in
`referencedAnalysisOperations`, creating numbered columns. If only the DEN entry
exists, column `referencedAnalysisOperations_analysisId2` is never created, and
`DEN_analysisid` is NULL.

**Fix**: Always include **both** NUM (self) and DEN (cross-reference) entries
in `referencedAnalysisOperations`, in that order:
```json
"referencedAnalysisOperations": [
    {"referencedOperationRelationshipId": "Mth_XX_XX_pct_NUM", "analysisId": "SELF_ID"},
    {"referencedOperationRelationshipId": "Mth_XX_XX_pct_DEN", "analysisId": "DENOM_ID"}
]
```

### Bug 3: Custom method templates must produce list-column `stat`

**Symptom**: `dplyr::bind_rows()` error: "Can't combine '..1$stat'<list> and
'..3$stat'<double>."

**Cause**: `cards::ard_categorical()` stores statistics as list columns. Custom
R templates (like Mth_03) that use `as.numeric()` or bare numeric values produce
plain numeric columns, which `bind_rows()` cannot combine with list columns.

**Fix**: Wrap all stat values in `as.list()`:
```r
stat = as.list(as.numeric(n_orr))    # correct
stat = as.list(pct)                   # correct
stat = as.numeric(n_orr)              # WRONG — will crash bind_rows
```

### Bug 4: `run_siera.R` patch is session-scoped

**Symptom**: Running `run_siera.R` a second time in the same R session gives
"Could not find buggy line to patch."

**Cause**: The patch modifies siera's namespace in memory. If already patched,
the buggy line no longer exists.

**Fix**: The current `run_siera.R` is idempotent — it checks if the patch is
already applied and skips if so. If you see an unexpected error, restart R
(`.rs.restartR()` in RStudio, or `q()` then relaunch).

---

## 7. Common Troubleshooting

| Symptom | Likely cause | See |
|---------|-------------|-----|
| `gsub("analysisADAMhere", ...)` error | Fewer than 3 analyses | Bug 1 |
| `dplyr::filter()` size 0 error | Missing `referencedAnalysisOperations` entry | Bug 2 |
| `bind_rows()` type mismatch | Custom template uses numeric instead of list column | Bug 3 |
| Patch fails on second run | Already patched in same session | Bug 4 |
| `cards` package not found | Missing R package | Section 1.3 |
| CSV not found | CSV filename ≠ `dataset` field in JSON | Rename CSV or update JSON |
| Filter returns 0 rows | Analysis flag mismatch in data | Step 2 — check actual values |
| Embedded quote values not matching | `'Y'` in CSV instead of `Y` | Step 1 — clean during export |
| `library(siera)` fails | siera not installed | `install.packages("siera")` |
