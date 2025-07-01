library(circlize)
library(colorRamp2)
library(ComplexHeatmap)

args <- commandArgs(trailingOnly = TRUE)
task_id <- args[1]
user_id <- args[2]
cutoff <- as.numeric(args[3])

cutoff_t <- cutoff
input_path <- file.path("results", user_id, task_id, "chord_Correlation_matrix.csv")

# cutoff_t <- 0.95
# input_path <- "chord_Correlation_matrix.csv"

cat("Cutoff:", cutoff_t, "\n")
cat("Input path:", input_path, "\n")

# Read the matrix
mat <- read.csv(input_path, row.names = 1, check.names = FALSE)
mat <- as.matrix(mat)
diag(mat) <- NA  # Remove self-correlations

# Get upper triangle values
mat[lower.tri(mat, diag = TRUE)] <- NA
flat_vals <- na.omit(as.data.frame(as.table(mat)))
flat_vals <- flat_vals[abs(flat_vals$Freq) > cutoff_t, ]
flat_vals <- flat_vals[order(-abs(flat_vals$Freq)), ]

top_sizes <- c(25, 50, 100, 250)

for (top_n in top_sizes) {
  cat("\nGenerating plot for top_n =", top_n, "\n")
  
  # Reset circlize state
  circos.clear()

  # Filter top correlations
  top_subset <- head(flat_vals, top_n)

  if (nrow(top_subset) == 0) {
    cat("No values above cutoff for top_n =", top_n, "\n")
    next
  }

  top_mat <- matrix(0, nrow = nrow(mat), ncol = ncol(mat))
  rownames(top_mat) <- rownames(mat)
  colnames(top_mat) <- colnames(mat)

  for (i in 1:nrow(top_subset)) {
    r <- top_subset[i, 1]
    c <- top_subset[i, 2]
    val <- top_subset[i, 3]
    top_mat[r, c] <- val
    top_mat[c, r] <- val
  }

  top_mat[top_mat == 0] <- NA

  nm <- unique(c(rownames(top_mat), colnames(top_mat)))
clean_labels <- sub("^(Tran_|Prot_|Lip_)", "", nm)
names(clean_labels) <- nm  # Mapping of full name -> clean label

gene_names <- nm[grepl("^Tran_", nm) | grepl("^AT", nm)]
protein_names <- nm[grepl("^Prot_", nm)]
lipid_names <- nm[grepl("^Lip_", nm)]

g_len <- length(gene_names)
l1_len <- length(protein_names)
l2_len <- length(lipid_names)

group <- structure(
  c(rep("Genes", g_len), rep("Proteins", l1_len), rep("Lipids", l2_len)),
  names = nm
)

grid.col <- structure(
  c(rep("darkolivegreen2", g_len), rep("gold1", l1_len), rep("deepskyblue1", l2_len)),
  names = nm
)


  output_file <- file.path("results", user_id, task_id, paste0("circlize_Top ", top_n, ".pdf"))
  cat("Writing to", output_file, "\n")

  # Try block to ensure dev.off() always runs
  try({
    pdf(output_file)

    col_fun = colorRamp2(c(-0.99, 0, 0.99), c("royalblue2", "white", "red2"))
    circos.par(canvas.ylim = c(-2, 2))
    

    chordDiagram(
      top_mat,
      group = group,
      grid.col = grid.col,
      col = col_fun,
      annotationTrack = c("grid"),
      preAllocateTracks = list(
        track.height = mm_h(3),
        track.margin = c(mm_h(1), 0)
      )
    )

    # circos.track(
    #   track.index = 2,
    #   track.margin = c(0, mm_h(8)),
    #   panel.fun = function(x, y) {
    #     sector.index = get.cell.meta.data("sector.index")
    #     xlim = get.cell.meta.data("xlim")
    #     ylim = get.cell.meta.data("ylim")
    #    circos.text(mean(xlim), ylim[2] + 2, clean_labels[sector.index], 
    #             facing = "outside", adj = c(0.5, 0), cex = 0.5, niceFacing = TRUE)
    #   },
    #   bg.border = NA
    # )
    
# Get present sectors
sectors_present <- get.all.sector.index()

# Filter group names to existing sectors
gene_names <- gene_names[gene_names %in% sectors_present]
protein_names <- protein_names[protein_names %in% sectors_present]
lipid_names <- lipid_names[lipid_names %in% sectors_present]

# Highlight groups (inner track, with group labels like Genes/Proteins/Lipids)
# if (length(gene_names) > 0) {
#   highlight.sector(gene_names, track.index = 1, col = "darkolivegreen2", 
#                    text = "Genes", cex = 0.8, text.col = "black", niceFacing = TRUE)
# }
# if (length(protein_names) > 0) {
#   highlight.sector(protein_names, track.index = 1, col = "gold1", 
#                    text = "Proteins", cex = 0.8, text.col = "black", niceFacing = TRUE)
# }
# if (length(lipid_names) > 0) {
#   highlight.sector(lipid_names, track.index = 1, col = "deepskyblue1", 
#                    text = "Lipids", cex = 0.8, text.col = "black", niceFacing = TRUE)
# }

# New outer track for sector (node) labels
circos.track(
  track.index = 2,
  panel.fun = function(x, y) {
    sector.index = get.cell.meta.data("sector.index")
    xlim = get.cell.meta.data("xlim")
    ylim = get.cell.meta.data("ylim")
    circos.text(mean(xlim), ylim[2] + 1.5, clean_labels[sector.index], 
                cex = 0.5, facing = "clockwise", niceFacing = TRUE, adj = c(0.5, 0))
  },
  bg.border = NA, track.height = mm_h(3)
)

# --- Legend for omics types ---
lgd_omics <- Legend(
  labels = c("Genes", "Proteins", "Lipids"),
  legend_gp = gpar(fill = c("darkolivegreen2", "gold1", "deepskyblue1")),
  title = "Omics Type"
)

# --- Legend for correlation values ---
lgd_links <- Legend(
  at = c(-1, 0, 1),
  col_fun = col_fun,
  title_position = "topleft",
  direction = "horizontal",
  title = "Correlation"
)

# --- Draw legends side by side ---
draw(
  packLegend(lgd_omics, lgd_links),
  x = unit(1, "npc") - unit(2, "mm"),
  y = unit(4, "mm"),
  just = c("right", "bottom")
)
    dev.off()
  }, silent = FALSE)

  cat("Finished top_n =", top_n, "\n")
}