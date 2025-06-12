
library(circlize)
library(colorRamp2)

args <- commandArgs(trailingOnly = TRUE)
task_id <- args[1]
user_id <- args[2]
cutoff <- as.numeric(args[3])

# Example: Use cutoff value for filtering or setting a threshold
cat("Task ID:", task_id, "\n")
cat("Cutoff:", cutoff, "\n")

cutoff_t <- cutoff
input_path <- file.path("results", user_id, task_id, "chord_Correlation_matrix.csv")

# cutoff_t <- 0.95
# input_path <- "chord_Correlation_matrix.csv"

cat("Cutoff:", cutoff_t, "\n")
cat("Input path:", input_path, "\n")
# Read the matrix
mat <- read.csv(input_path, row.names = 1, check.names = FALSE)

# Filter the matrix based on the cutoff
aaa <- mat[, (colSums(mat > cutoff_t | mat < -cutoff_t)) > 0]
aaa[aaa == 0] <- NA
bbb <- aaa[(rowSums(aaa > cutoff_t | aaa < -cutoff_t)) > 0,]
bbb <- as.matrix(bbb)
bbb[bbb == 0] <- NA
bbb[-cutoff_t<bbb & bbb<cutoff_t]<-0


# Convert to matrix
mymat <- as.matrix(bbb)
mymat[mymat == 0] <- NA
# Get the names for dimension calculation
nm = unique(c(rownames(mymat), colnames(mymat)))
g_len = nrow(mymat)
l1_len = sum(grepl("^Prot_", colnames(mymat)))
l2_len = sum(grepl("^Lip_", colnames(mymat)))
print(g_len)

# Create group structure
group = structure(c(rep("Genes", g_len), rep("Proteins", l1_len), rep("Lipids", l2_len)), names = nm)

# Color map
grid.col = structure(
  c(rep("darkolivegreen2", g_len), rep("gold1", l1_len), rep("deepskyblue1", l2_len)), 
  names = nm
)

# Save PDF
pdf("circlize_output.pdf")

# Color scale
col_fun = colorRamp2(c(-0.99, 0, 0.99), c("royalblue2", "white", "red2"))

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
    sector.index = get.cell.meta.data("sector.index")
    xlim = get.cell.meta.data("xlim")
    ylim = get.cell.meta.data("ylim")
    circos.text(mean(xlim), ylim[1] + 3, sector.index, cex = 0.5, facing = "clockwise", niceFacing = TRUE)
  },
  bg.border = NA
)

# Highlight sectors
highlight.sector(nm[1:g_len], track.index = 1, col = "darkolivegreen2", text = "Genes", cex = 0.8, text.col = "white", niceFacing = TRUE)
highlight.sector(nm[(g_len+1):(g_len+l1_len)], track.index = 1, col = "gold1", text = "Proteins", cex = 0.8, text.col = "white", niceFacing = TRUE)
highlight.sector(nm[(g_len+l1_len+1):(g_len+l1_len+l2_len)], track.index = 1, col = "deepskyblue1", text = "Lipids", cex = 0.8, text.col = "white", niceFacing = TRUE)

# Add legend
lgd_links = Legend(at = c(-1, 0, 1), col_fun = col_fun, title_position = "topleft", title = "Correlation")
draw(lgd_links, x = unit(1, "npc") - unit(2, "mm"), y = unit(4, "mm"), just = c("right", "bottom"))

# Close the PDF
dev.off()

# Clear circos
circos.clear()
