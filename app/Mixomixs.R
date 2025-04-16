library(optparse)
library(mixOmics)
library(caret)  # For nearZeroVar function

trim.trailing <- function (x) sub("\\s+$", "", x)

option_list <- list(
  make_option(c('--folder'), type='character', help='Path to the folder'),
  make_option(c('--Y-ids'), type='character', help='Comma-separated Y IDs'),
  make_option(c('--timepoint-ids'), type='character', help='Comma-separated timepoint IDs'),
  make_option(c('--task_id'), type='character', help='task_id'),
  make_option(c('--user_id'), type='character', help='user_id')
)

opts <- parse_args(OptionParser(option_list=option_list))

# Access the parsed arguments
mixomics_folder_path <- opts$folder
timepoint_ids <- unlist(strsplit(opts$timepoint_ids, ","))  # Split the comma-separated string into a vector
Y_ids <- factor(unlist(strsplit(opts$`Y-ids`, ",")))

output_dir <- file.path("results", opts$user_id, opts$task_id)

# Create directory if it doesn't exist
if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# File paths
# Tran_f <- "/app/C10_35_Transcriptome_T.csv"
# Prot_f <- "/app/C10_35_Proteomics_T.csv"
# Lip_f <- "/app/C10_35_Lipid_T.csv"
Tran_f <- file.path(mixomics_folder_path, "transcriptomics.csv")
Prot_f <- file.path(mixomics_folder_path, "proteomics.csv")
Lip_f <- file.path(mixomics_folder_path, "metabolomics.csv")

# Read data
transcriptome <- read.csv(Tran_f, header = TRUE, sep = "\t", check.names = FALSE, row.names = 1)
proteome <- read.csv(Prot_f, header = TRUE, sep = "\t", check.names = FALSE, row.names = 1)
lipidome <- read.csv(Lip_f, header = TRUE, sep = "\t", check.names = FALSE, row.names = 1)

# Function to remove zero-variance features
remove_zero_var <- function(data, name) {
  # Identify zero-variance features
  zero_var_features <- apply(data, 1, function(x) var(x, na.rm = TRUE) == 0)
  
  if (sum(zero_var_features) > 0) {
    message("Removing ", sum(zero_var_features), " zero-variance features from ", name)
    data <- data[!zero_var_features, , drop = FALSE]  # Ensure matrix structure is maintained
  } else {
    message("No zero-variance features found in ", name)
  }
  
  return(data)
}

# Apply zero-variance filtering
transcriptome <- remove_zero_var(transcriptome, "Transcriptome")
proteome <- remove_zero_var(proteome, "Proteome")
lipidome <- remove_zero_var(lipidome, "Lipidome")

# Female and Male sample IDs
#id_female <- c("WT35R1", "WT35R2", "WT35R3", "WT35R4", "C10_35_R1", "C10_35_R2", "C10_35_R3", "C10_35_R4") 
#id_male <- c("WT35R1", "WT35R2", "WT35R3", "WT35R4", "C10_35_R1", "C10_35_R2", "C10_35_R2", "C10_35_R2")
id_female <- as.character(timepoint_ids)

# Assign class labels
# Y_female <- factor(c("WT35", "WT35", "WT35", "WT35", "C10_35", "C10_35", "C10_35", "C10_35"))
Y_female <- Y_ids
#Y_male <- factor(c("WT", "WT", "WT", "WT", "CT", "CT", "CT", "CT"))

# Ensure IDs exist in the datasets before subsetting
check_samples_exist <- function(data, sample_ids, dataset_name) {
  valid_ids <- sample_ids[sample_ids %in% rownames(data)]
  
  if (length(valid_ids) < length(sample_ids)) {
    missing_ids <- setdiff(sample_ids, valid_ids)
    message("Warning: Some sample IDs are missing from ", dataset_name, ": ", paste(missing_ids, collapse = ", "))
  }
  
  return(valid_ids)
}

id_female <- check_samples_exist(transcriptome, id_female, "Transcriptome")

# Create the multi-omics dataset
X <- list(
  Tran = as.matrix(transcriptome[id_female, ]),
  Prot = as.matrix(proteome[id_female, ]),
  Lip = as.matrix(lipidome[id_female, ])
)
Y <- Y_female

X <- list(
  Transcriptomics = as.matrix(sapply(transcriptome, as.numeric)), 
  Proteomics = as.matrix(sapply(proteome, as.numeric)), 
  Lipidomics = as.matrix(sapply(lipidome, as.numeric))
)

# **Final Check Before DIABLO**
check_zero_variance <- function(data, name) {
  zero_var <- apply(data, 1, function(x) var(x, na.rm = TRUE) == 0)
  if (any(zero_var)) {
    stop(paste("Error: Zero-variance features still exist in", name, "! Please check data processing."))
  } else {
    message("✅ No zero-variance features detected in ", name)
  }
}

check_zero_variance(X$Tran, "Tran")
check_zero_variance(X$Prot, "Prot")
check_zero_variance(X$Lip, "Lip")

# Run DIABLO
MyResult.diablo <- block.splsda(X, Y)

# Visualization
pdf(file.path(output_dir, "DIABLO_Plots.pdf"))
plotDiablo(MyResult.diablo, ncomp = 1)
plotIndiv(MyResult.diablo)
plotVar(MyResult.diablo, var.names = FALSE, style = 'graphics', legend = TRUE, 
        pch = c(16, 17, 15), cex = c(2,2,2), 
        col = c('darkorchid', 'brown1', 'lightgreen'),)
#plotLoadings
plotLoadings(MyResult.diablo, comp = 1, contrib = 'max', method = 'median')
#cimDiablo
cimDiablo(MyResult.diablo, color.blocks = c('darkorchid', 'brown1', 'lightgreen'),
          comp = 1, margin=c(8,20), legend.position = "right")
correlation_matrix<-circosPlot(MyResult.diablo, cutoff = 0.98, size.variables = 0.4)
write.csv(correlation_matrix, file.path(output_dir, "Correlation_matrix.csv"), row.names = TRUE)

circosPlot(MyResult.diablo, cutoff = 0.98, size.variables = 0.4)
plotArrow(MyResult.diablo)
try({
  network(MyResult.diablo, blocks = c(1,2,3), 
          cutoff = 0.7,
          color.node = c('darkorchid', 'brown1', 'lightgreen'))
}, silent = TRUE)
dev.off()