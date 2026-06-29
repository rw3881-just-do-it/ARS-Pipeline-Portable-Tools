# run_pipeline.R — One-line entry point
#
# After building the JSON (see README), run this in R to generate the ARD script.
#
#   setwd("ars_portable")
#   source("run_pipeline.R")
#
# Change the CONFIG_FILE and ADAM_PATH below for your table.

# ---------------------------------------------------------------------------
# CHANGE FOR YOUR TABLE
# ---------------------------------------------------------------------------
CONFIG_FILE <- "output/t_14_2_4_1_1_siera.json"   # path to your JSON
ADAM_PATH   <- "."                                  # directory with CSV files

# ---------------------------------------------------------------------------
# Apply siera patch + run readARS
# ---------------------------------------------------------------------------
source("engine/siera_patch.R")

siera::readARS(
  ARS_path    = CONFIG_FILE,
  output_path = dirname(CONFIG_FILE),
  adam_path   = ADAM_PATH
)

cat("\nGenerated R scripts:\n")
print(list.files(dirname(CONFIG_FILE), pattern = "\\.R$", full.names = TRUE))

# Uncomment to auto-source the generated script:
# ard_file <- list.files(dirname(CONFIG_FILE), pattern = "^ARD_.*\\.R$", full.names = TRUE)[1]
# if (!is.na(ard_file)) source(ard_file)
