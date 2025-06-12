library(circlize)
library(colorRamp2)

# args <- commandArgs(trailingOnly = TRUE)
# task_id <- args[1]
# user_id <- args[2]
# cutoff <- as.numeric(args[3])

# # Example: Use cutoff value for filtering or setting a threshold
# cat("Task ID:", task_id, "\n")
# cat("Cutoff:", cutoff, "\n")

# cutoff_t <- cutoff
# input_path <- file.path("results", user_id, task_id, "chord_Correlation_matrix.csv")

cutoff_t <- 0.95
input_path <- "chord_Correlation_matrix.csv"

cat("Cutoff:", cutoff_t, "\n")
cat("Input path:", input_path, "\n")

# Read the matrix
mat <- read.csv(input_path, row.names = 1, check.names = FALSE)

# Function to get top N correlations and create subset matrix
get_top_correlations <- function(matrix, n_top, cutoff_threshold) {
  # Convert to matrix if not already
  mat_work <- as.matrix(matrix)
  
  # Set diagonal to NA to exclude self-correlations
  diag(mat_work) <- NA
  
  # Get absolute values for ranking but keep original signs
  abs_mat <- abs(mat_work)
  
  # Get the top N correlations (excluding NA values)
  top_indices <- order(abs_mat, decreasing = TRUE, na.last = TRUE)[1:min(n_top, sum(!is.na(abs_mat)))]
  
  # Create a new matrix with only top correlations
  result_mat <- matrix(0, nrow = nrow(mat_work), ncol = ncol(mat_work))
  rownames(result_mat) <- rownames(mat_work)
  colnames(result_mat) <- colnames(mat_work)
  
  # Fill in the top correlations
  result_mat[top_indices] <- mat_work[top_indices]
  
  # Apply cutoff threshold
  result_mat[abs(result_mat) < cutoff_threshold] <- 0
  
  # Filter out rows and columns that are all zeros
  non_zero_cols <- colSums(abs(result_mat) > 0) > 0
  non_zero_rows <- rowSums(abs(result_mat) > 0) > 0
  
  result_mat <- result_mat[non_zero_rows, non_zero_cols, drop = FALSE]
  
  # Convert zeros to NA for visualization
  result_mat[result_mat == 0] <- NA
  
  return(result_mat)
}

# Function to create chord diagram
create_chord_diagram <- function(mymat, title_suffix = "") {
  # Skip if matrix is empty or has no valid correlations
  if (nrow(mymat) == 0 || ncol(mymat) == 0 || all(is.na(mymat))) {
    cat("Skipping", title_suffix, "- no valid correlations found\n")
    return(FALSE)
  }
  
  # Get the names for dimension calculation
  nm <- unique(c(rownames(mymat), colnames(mymat)))
  g_len <- sum(!grepl("^(Prot_|Lip_)", nm))  # Genes (everything not starting with Prot_ or Lip_)
  l1_len <- sum(grepl("^Prot_", nm))         # Proteins
  l2_len <- sum(grepl("^Lip_", nm))          # Lipids
  
  cat("Creating diagram for", title_suffix, "\n")
  cat("Genes:", g_len, "Proteins:", l1_len, "Lipids:", l2_len, "\n")
  
  # Create group structure
  group <- structure(
    c(rep("Genes", g_len), rep("Proteins", l1_len), rep("Lipids", l2_len)), 
    names = nm
  )
  
  # Color map
  grid.col <- structure(
    c(rep("darkolivegreen2", g_len), rep("gold1", l1_len), rep("deepskyblue1", l2_len)), 
    names = nm
  )
  
  # Color scale
  col_fun <- colorRamp2(c(-0.99, 0, 0.99), c("royalblue2", "white", "red2"))
  
  # Initialize circos
  circos.par(canvas.ylim = c(-1.5, 1.5))
  
  # Draw chord diagram
  chordDiagram(
    mymat,
    group = group,
    grid.col = grid.col,
    col = col_fun,
    annotationTrack = c("grid"),
    preAllocateTracks = list(
      track.height = mm_h(3),
      track.margin = c(mm_h(1), 0)
    )
  )
  
  # Add sector labels
  circos.track(
    track.index = 2,
    track.margin = c(0, mm_h(8)),
    panel.fun = function(x, y) {
      sector.index <- get.cell.meta.data("sector.index")
      xlim <- get.cell.meta.data("xlim")
      ylim <- get.cell.meta.data("ylim")
      circos.text(mean(xlim), ylim[1] + 3, sector.index, cex = 0.5, facing = "clockwise", niceFacing = TRUE)
    },
    bg.border = NA
  )
  
  # Highlight sectors (only if they exist)
  if (g_len > 0) {
    gene_indices <- nm[!grepl("^(Prot_|Lip_)", nm)]
    if (length(gene_indices) > 0) {
      highlight.sector(gene_indices, track.index = 1, col = "darkolivegreen2", text = "Genes", cex = 0.8, text.col = "white", niceFacing = TRUE)
    }
  }
  
  if (l1_len > 0) {
    prot_indices <- nm[grepl("^Prot_", nm)]
    if (length(prot_indices) > 0) {
      highlight.sector(prot_indices, track.index = 1, col = "gold1", text = "Proteins", cex = 0.8, text.col = "white", niceFacing = TRUE)
    }
  }
  
  if (l2_len > 0) {
    lip_indices <- nm[grepl("^Lip_", nm)]
    if (length(lip_indices) > 0) {
      highlight.sector(lip_indices, track.index = 1, col = "deepskyblue1", text = "Lipids", cex = 0.8, text.col = "white", niceFacing = TRUE)
    }
  }
  
  # Add legend
  lgd_links <- Legend(at = c(-1, 0, 1), col_fun = col_fun, title_position = "topleft", title = "Correlation")
  draw(lgd_links, x = unit(1, "npc") - unit(2, "mm"), y = unit(4, "mm"), just = c("right", "bottom"))
  
  # Add title
  title(main = paste("Top", title_suffix, "Correlations"), line = -2)
  
  # Clear circos for next plot
  circos.clear()
  
  return(TRUE)
}

# Define the top N values to create plots for
top_values <- c( 100, 250)

# Create separate PDF files for each top N
for (n_top in top_values) {
  cat("\n=== Processing Top", n_top, "correlations ===\n")
  
  # Get top correlations
  top_mat <- get_top_correlations(mat, n_top, cutoff_t)
  
  # Create filename
  output_filename <- paste0("circlize_top_", n_top, "_correlations.pdf")
  
  # Create PDF
  pdf(output_filename, width = 10, height = 10)
  
  # Create chord diagram
  success <- create_chord_diagram(top_mat, as.character(n_top))
  
  if (!success) {
    # Create empty plot with message if no valid correlations
    plot.new()
    text(0.5, 0.5, paste("No valid correlations found for top", n_top), 
         cex = 1.5, col = "red")
  }
  
  # Close PDF
  dev.off()
  
  cat("Saved:", output_filename, "\n")
}

# Also create a combined PDF with all plots
cat("\n=== Creating combined PDF ===\n")
pdf("circlize_all_tops_combined.pdf", width = 12, height = 10)

par(mfrow = c(2, 2))  # 2x2 layout for 4 plots

for (i in 1:length(top_values)) {
  n_top <- top_values[i]
  cat("Adding plot for top", n_top, "to combined PDF\n")
  
  # Get top correlations
  top_mat <- get_top_correlations(mat, n_top, cutoff_t)
  
  # Create chord diagram
  success <- create_chord_diagram(top_mat, as.character(n_top))
  
  if (!success) {
    # Create empty plot with message if no valid correlations
    plot.new()
    text(0.5, 0.5, paste("No valid correlations\nfound for top", n_top), 
         cex = 1.2, col = "red")
  }
}

dev.off()
cat("Saved: circlize_all_tops_combined.pdf\n")

cat("\n=== Summary ===\n")
cat("Created individual PDFs for top 25, 50, 100, and 250 correlations\n")
cat("Created combined PDF with all plots\n")
cat("Files saved in current working directory\n")