# --- Auto-install helper ---
install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg)
  }
}
install_if_missing("jsonlite")
install_if_missing("ggvenn")
install_if_missing("ggplot2")
install_if_missing("RColorBrewer")

# Load libraries
library(jsonlite)
library(ggvenn)
library(ggplot2)
library(RColorBrewer)

# Parse command line args
args <- commandArgs(trailingOnly = TRUE)
json_path <- args[1]
output_pdf <- args[2]

# Load JSON
data <- fromJSON(json_path)

# Handle results as list
if (is.data.frame(data$results)) {
  results <- split(data$results, seq(nrow(data$results)))
} else {
  results <- data$results
}

# Helper to clean and normalize gene names
clean_genes <- function(g) {
  unique(tolower(trimws(g)))
}

# Build gene sets from cutoffs
gene_sets <- list()
for (i in seq_along(results)) {
  entry <- results[[i]]
  cutoff_label <- paste0("Cutoff_", as.character(entry$cutoff))
  
  gene_raw <- entry$matching_genes
  
  if (is.character(gene_raw) && length(gene_raw) == 1 && grepl("^c\\(", gene_raw)) {
    gene_vector <- tryCatch(eval(parse(text = gene_raw)), error = function(e) character(0))
  } else if (is.list(gene_raw)) {
    gene_vector <- unlist(gene_raw)
  } else {
    gene_vector <- gene_raw
  }
  
  gene_sets[[cutoff_label]] <- clean_genes(gene_vector)
}

print("Final gene sets:")
print(gene_sets)

# Skip if fewer than 2 sets
if (length(gene_sets) < 2) {
  stop("Venn diagram needs at least 2 sets")
}

# Assign colors
cutoff_names <- names(gene_sets)
set1_colors <- brewer.pal(min(9, length(cutoff_names)), "Set1")
if (length(cutoff_names) > 9) {
  set1_colors <- rep(set1_colors, length.out = length(cutoff_names))
}
color_subset <- setNames(set1_colors, cutoff_names)

# Build Venn plot
p <- ggvenn(
  gene_sets,
  fill_color = unname(color_subset),
  stroke_size = 0.5,
  set_name_size = 5,
  text_size = 4
) + ggtitle("Venn Diagram Across Cutoffs")

# Save to PDF
pdf(output_pdf, width = 12, height = 10)
print(p)
dev.off()
