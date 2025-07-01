# --- Auto-install helper ---
install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg)
  }
}
install_if_missing("jsonlite")
install_if_missing("ggvenn")
install_if_missing("ggplot2")
install_if_missing("gridExtra")
install_if_missing("RColorBrewer")

# Load libraries
library(jsonlite)
library(ggvenn)
library(ggplot2)
library(gridExtra)
library(RColorBrewer)

args <- commandArgs(trailingOnly = TRUE)
json_path <- args[1]
output_pdf <- args[2]

# Load JSON
data <- fromJSON(json_path)
results <- data$results

# Group by cutoff
grouped_by_cutoff <- split(results, results$cutoff)

# Define Set1 colors
all_tps <- unique(results$tp)
set1_colors <- brewer.pal(min(9, length(all_tps)), "Set1")
if (length(all_tps) > 9) {
  set1_colors <- rep(set1_colors, length.out = length(all_tps))
}
tp_colors <- setNames(set1_colors, all_tps)

# Create plot list
plot_list <- list()

for (cutoff_value in names(grouped_by_cutoff)) {
  subset <- grouped_by_cutoff[[cutoff_value]]

  gene_sets <- list()
  for (i in 1:nrow(subset)) {
    tp <- subset$tp[i]
    gene_sets[[tp]] <- unique(subset$matching_genes[[i]])
  }

  # Fill colors without names (Set1 palette)
color_subset <- unname(tp_colors[names(gene_sets)])

# Build ggvenn plot
p <- ggvenn(
  gene_sets,
  fill_color = color_subset,
  stroke_size = 0.5,
  set_name_size = 5,
  text_size = 4
) + ggtitle(paste("Cutoff:", cutoff_value))

  plot_list[[paste0("cutoff_", cutoff_value)]] <- p
}

# Output to single PDF
pdf(output_pdf, width = 12, height = 10)
do.call("grid.arrange", c(plot_list, ncol = 2))
dev.off()
