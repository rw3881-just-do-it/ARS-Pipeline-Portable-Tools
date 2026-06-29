# Standard Method Templates
#
# These are the three reusable method definitions for frequency tables.
# Each method is a Python dict that gets inserted into the JSON "methods" array.
#
# To use a custom R code template, copy one of these and modify the "code" string.
# Available siera valueSource variables:
#   ana_var        → analysis.variable        e.g. "SUBJID", "AVALC"
#   AG_var1        → first grouping variable   e.g. "ARMCD"
#   DEN_analysisid → denominator analysis ID   e.g. "An_01"
#   AG_denom_var1  → denominator's group var   e.g. "ARMCD"
#   by_vars        → ", variables = 'ARMCD'"    (for cards ard_categorical)
#   by_listc       → "'ARMCD'"                  (as character vector)
#   distinct_list  → "ARMCD, AVALC"             (comma-separated vars)
#   AG_max_dataDriven → "FALSE" or "TRUE"


# ---------------------------------------------------------------------------
# Mth_01 — Denominator: count of unique subjects per group
#   Uses: cards::ard_categorical() with by/variables statement
#   Result: one row per group with stat_name="n"
#   Typically used as An_01 (the denominator analysis)
# ---------------------------------------------------------------------------
MTH_DENOMINATOR = {
    "id": "Mth_01",
    "name": "Count by group for a categorical variable",
    "label": "Grouped count for categorical variable",
    "description": "Count across groups for a categorical variable, based on subject occurrence",
    "operations": [
        {"id": "Mth_01_01_n", "name": "Count of subjects", "order": 1, "label": "n", "resultPattern": "(N=)"}
    ],
    "codeTemplate": {
        "context": "R (siera)",
        "code": """in_data = df2_analysisidhere |>
    dplyr::select(anavarhere, groupvar1here) |>
    unique()
df3_analysisidhere <-
  cards::ard_categorical(
    data = in_data
    bystmthere
  ) |>
dplyr::filter(stat_name == 'n') |>
 dplyr::mutate(operationid = 'Mth_01_01_n')""",
        "parameters": [
            {"name": "anavarhere",    "description": "Analysis variable to be summarised", "valueSource": "ana_var"},
            {"name": "groupvar1here", "description": "Analysis grouping variable",          "valueSource": "AG_var1"},
            {"name": "bystmthere",    "description": "Combined by/variables statement",     "valueSource": "by_vars"}
        ]
    }
}


# ---------------------------------------------------------------------------
# Mth_02 — Numerator: count and percentage per category per group
#   Uses: cards::ard_categorical() with denominator
#   Result: rows per group × category with stat_name="n" and stat_name="p"
#   Requires: referencedAnalysisOperations with NUM + DEN entries in analyses
# ---------------------------------------------------------------------------
MTH_CATEGORICAL = {
    "id": "Mth_02",
    "name": "Summary by group of a categorical variable",
    "label": "Grouped summary of categorical variable",
    "description": "Descriptive summary statistics across groups for a categorical variable",
    "operations": [
        {"id": "Mth_02_01_n", "name": "n", "order": 1, "label": "n", "resultPattern": "XX"},
        {"id": "Mth_02_02_pct", "name": "%", "order": 2, "label": "%", "resultPattern": "(XX.XX)",
         "referencedOperationRelationships": [
             {"id": "Mth_02_02_pct_NUM", "referencedOperationRole": {"controlledTerm": "NUMERATOR"},
              "operationId": "Mth_02_01_n", "description": "n per category (numerator)"},
             {"id": "Mth_02_02_pct_DEN", "referencedOperationRole": {"controlledTerm": "DENOMINATOR"},
              "operationId": "Mth_01_01_n", "analysisId": "An_01",
              "description": "N per arm (denominator)"}
         ]}
    ],
    "codeTemplate": {
        "context": "R (siera)",
        "code": """denom_dataset = df2_denomanaidhere |>
  dplyr::select(denom_anagroupvarshere)

in_data = df2_analysisidhere |>
    dplyr::distinct(distinctlisthere) |>
    dplyr::mutate(dummy = 'dummyvar')

dataDriven = isdatadrivenhere
if(dataDriven == TRUE){
df3_analysisidhere <-
  cards::ard_categorical(
    data = in_data,
    strata = c(byvarshere),
    variables = 'dummy',
    denominator = denom_dataset
  ) } else {
df3_analysisidhere <-
 cards::ard_categorical(
    data = in_data,
    by = c(byvarshere),
    variables = 'dummy',
    denominator = denom_dataset
  ) }
df3_analysisidhere <- df3_analysisidhere|>
dplyr::filter(stat_name %in% c('n', 'p')) |>
dplyr::mutate(operationid = dplyr::case_when(stat_name == 'n' ~ 'Mth_02_01_n',
                                      stat_name == 'p' ~ 'Mth_02_02_pct'))""",
        "parameters": [
            {"name": "distinctlisthere",       "description": "list of variables for distinct",     "valueSource": "distinct_list"},
            {"name": "denomanaidhere",         "description": "Analysis ID for Denominator",         "valueSource": "DEN_analysisid"},
            {"name": "denom_anagroupvarshere", "description": "Denominator grouping variables",      "valueSource": "AG_denom_var1"},
            {"name": "isdatadrivenhere",       "description": "dataDriven boolean",                  "valueSource": "AG_max_dataDriven"},
            {"name": "byvarshere",             "description": "by statement variables",              "valueSource": "by_listc"}
        ]
    }
}


# ---------------------------------------------------------------------------
# Mth_03 — Derived endpoint: ORR (CR+PR) with 95% Clopper-Pearson CI
#   Does NOT use cards — custom base R + dplyr + stats::binom.test()
#   Result: rows per group with n, p, ci_lower, ci_upper
#
#   ADAPT THIS FOR OTHER DERIVED ENDPOINTS:
#   - Change the filter values (e.g. "CR", "PR" → "CR", "PR", "SD" for DCR)
#   - Change operation IDs and names to match your endpoint
#   - The "Mth_03_02_pct_DEN" relationship's analysisId should always be "An_01"
#     (the denominator) — update if your denominator has a different ID
# ---------------------------------------------------------------------------
MTH_ORR_CI = {
    "id": "Mth_03",
    "name": "Objective Response Rate (ORR) with 95% CI by group",
    "label": "ORR with CI",
    "description": "Derived ORR (CR+PR) per group with percentage and exact binomial 95% confidence interval",
    "operations": [
        {"id": "Mth_03_01_n", "name": "ORR n", "order": 1, "label": "n", "resultPattern": "XX"},
        {"id": "Mth_03_02_pct", "name": "ORR %", "order": 2, "label": "%", "resultPattern": "(XX.XX)",
         "referencedOperationRelationships": [
             {"id": "Mth_03_02_pct_NUM", "referencedOperationRole": {"controlledTerm": "NUMERATOR"},
              "operationId": "Mth_03_01_n", "description": "ORR n (numerator)"},
             {"id": "Mth_03_02_pct_DEN", "referencedOperationRole": {"controlledTerm": "DENOMINATOR"},
              "operationId": "Mth_01_01_n", "analysisId": "An_01",
              "description": "N per arm (denominator)"}
         ]},
        {"id": "Mth_03_03_ci_lower", "name": "95% CI Lower", "order": 3, "label": "CI Lower", "resultPattern": "(XX.XX)"},
        {"id": "Mth_03_04_ci_upper", "name": "95% CI Upper", "order": 4, "label": "CI Upper", "resultPattern": "(XX.XX)"}
    ],
    "codeTemplate": {
        "context": "R (siera)",
        "code": """# ORR: count distinct subjects with CR/PR per group
in_data <- df2_analysisidhere |>
  dplyr::select(SUBJID, groupvar1here, anavarhere) |>
  dplyr::distinct()

# N per group (denominator: all subjects in analysis set per group)
N_per_group <- in_data |>
  dplyr::count(groupvar1here, name = 'N_total')

# ORR n per group (CR + PR only)
orr_n <- in_data |>
  dplyr::filter(anavarhere %in% c('CR', 'PR')) |>
  dplyr::count(groupvar1here, name = 'n_orr')

# Join and compute % with 95% Clopper-Pearson CI
orr_df <- dplyr::left_join(N_per_group, orr_n, by = 'groupvar1here') |>
  dplyr::mutate(n_orr = tidyr::replace_na(n_orr, 0L)) |>
  dplyr::rowwise() |>
  dplyr::mutate(
    pct = n_orr / N_total,
    ci = list(stats::binom.test(as.integer(n_orr), as.integer(N_total))$conf.int)
  ) |>
  dplyr::mutate(
    ci_lower = ci[1],
    ci_upper = ci[2]
  ) |>
  dplyr::ungroup()

# Pivot to ARD long format — stat MUST be list column (as.list) for bind_rows compatibility
df3_analysisidhere <- dplyr::bind_rows(
  orr_df |> dplyr::transmute(group1_level = groupvar1here, stat_name = 'n',         stat = as.list(as.numeric(n_orr)), operationid = 'Mth_03_01_n'),
  orr_df |> dplyr::transmute(group1_level = groupvar1here, stat_name = 'p',         stat = as.list(pct),              operationid = 'Mth_03_02_pct'),
  orr_df |> dplyr::transmute(group1_level = groupvar1here, stat_name = 'ci_lower',  stat = as.list(ci_lower),           operationid = 'Mth_03_03_ci_lower'),
  orr_df |> dplyr::transmute(group1_level = groupvar1here, stat_name = 'ci_upper',  stat = as.list(ci_upper),           operationid = 'Mth_03_04_ci_upper')
)""",
        "parameters": [
            {"name": "anavarhere",    "description": "Analysis variable (response variable)", "valueSource": "ana_var"},
            {"name": "groupvar1here", "description": "Analysis grouping variable",            "valueSource": "AG_var1"}
        ]
    }
}


# ---------------------------------------------------------------------------
# Convenience: return all three standard methods as a list
# ---------------------------------------------------------------------------
def get_standard_methods():
    """Return the three standard frequency-table methods as a Python list."""
    return [MTH_DENOMINATOR, MTH_CATEGORICAL, MTH_ORR_CI]
