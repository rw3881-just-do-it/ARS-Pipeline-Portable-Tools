# siera_patch.R — Runtime patch for siera 0.5.6
#
# Fixes: .generate_analysis_set_code() hardcodes anas[3, ] on line ~62
#        Crashes when an output has fewer than 3 analyses.
#
# Usage (in R):
#   source("engine/siera_patch.R")
#   siera::readARS("your_file.json", adam_path = ".", output_path = ".")
#
# Idempotent: sourcing a second time is safe (skips if already patched).

library(siera)

orig <- get(".generate_analysis_set_code", envir = asNamespace("siera"), inherits = FALSE)
fixed_lines <- deparse(orig)

line_idx <- grep("Anas_2 <- anas[3, ]$listItem_analysisId", fixed_lines, fixed = TRUE)

if (length(line_idx) == 1) {
  fixed_lines[line_idx] <- "    Anas_2 <- anas[min(2, nrow(anas)), ]$listItem_analysisId"
  new_body <- parse(text = paste(fixed_lines, collapse = "\n"))[[1]]
  new_fn <- eval(new_body)
  environment(new_fn) <- environment(orig)
  unlockBinding(".generate_analysis_set_code", asNamespace("siera"))
  assign(".generate_analysis_set_code", new_fn, envir = asNamespace("siera"))
  lockBinding(".generate_analysis_set_code", asNamespace("siera"))
  message("siera patch applied.")
} else if (length(line_idx) == 0) {
  message("siera already patched, skipping.")
} else {
  stop("Unexpected: found multiple matching lines in .generate_analysis_set_code")
}
