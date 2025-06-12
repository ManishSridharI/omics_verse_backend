library(optparse)
library(mixOmics)
library(caret)  # For nearZeroVar function
library(jsonlite)
library(stringr)
library(dplyr)
library(circlize)
trim.trailing <- function (x) sub("\\s+$", "", x)

option_list <- list(
  make_option(c('--folder'), type='character', help='Path to the folder'),
  make_option(c('--ids'), type='character', help='Comma-separated IDs'),
  make_option(c('--timepoints'), type='character', help='Comma-separated timepoint IDs'),
  make_option(c('--task_id'), type='character', help='task_id'),
  make_option(c('--user_id'), type='character', help='user_id'),
  make_option(c('--GOI_path'), type='character', help='GOI_path')
)

opts <- parse_args(OptionParser(option_list=option_list))

# Access the parsed arguments
mixomics_folder_path <- opts$folder
timepoint_ids <- unlist(strsplit(opts$timepoints, ","))  # Split the comma-separated string into a vector
Y_ids <- factor(unlist(strsplit(opts$ids, ",")))
GOI_path <- opts$GOI_path
output_dir <- file.path("results", opts$user_id, opts$task_id)

# Create directory if it doesn't exist
if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# Construct path for error.txt
error_path <- file.path(output_dir, "error.txt")

# Redirect stderr to error.txt
if (!is.null(opts$user_id) && !is.null(opts$task_id)) {
  dir.create(dirname(error_path), recursive = TRUE, showWarnings = FALSE)
  zz <- file(error_path, open = "wt")
  sink(zz, type = "message")  # Redirect messages (includes errors)
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
GOI <- readLines(GOI_path)

# Function to remove zero-variance features
# remove_zero_var <- function(data, name) {
#   # Identify zero-variance features
#   zero_var_features <- apply(data, 1, function(x) var(x, na.rm = TRUE) == 0)
  
#   if (sum(zero_var_features) > 0) {
#     message("Removing ", sum(zero_var_features), " zero-variance features from ", name)
#     data <- data[!zero_var_features, , drop = FALSE]  # Ensure matrix structure is maintained
#   } else {
#     message("No zero-variance features found in ", name)
#   }
  
#   return(data)
# }

remove_zero_var <- function(data, name) {
  zero_var_features <- apply(data, 1, function(x) {
    if (all(is.na(x))) {
      TRUE
    } else {
      var(as.numeric(x), na.rm = TRUE) == 0
    }
  })
  
  if (sum(zero_var_features, na.rm = TRUE) > 0) {
    message("Removing ", sum(zero_var_features, na.rm = TRUE), " zero-variance features from ", name)
    data <- data[!zero_var_features, , drop = FALSE]
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

colnames(transcriptome) <- paste0("Tran_", colnames(transcriptome))
colnames(proteome) <- paste0("Prot_", colnames(proteome))
colnames(lipidome) <- paste0("Lip_", colnames(lipidome))

X <- list(
  Transcriptomics = as.matrix(sapply(transcriptome, as.numeric)), 
  Proteomics = as.matrix(sapply(proteome, as.numeric)), 
  Lipidomics = as.matrix(sapply(lipidome, as.numeric))
)

# **Final Check Before DIABLO**
# check_zero_variance <- function(data, name) {
#   zero_var <- apply(data, 1, function(x) var(x, na.rm = TRUE) == 0)
#   if (any(zero_var)) {
#     stop(paste("Error: Zero-variance features still exist in", name, "! Please check data processing."))
#   } else {
#     message("✅ No zero-variance features detected in ", name)
#   }
# }

check_zero_variance <- function(data, name) {
  zero_var <- apply(data, 1, function(x) {
    if (all(is.na(x))) {
      TRUE
    } else {
      var(as.numeric(x), na.rm = TRUE) == 0
    }
  })

  zero_var[is.na(zero_var)] <- FALSE  # Ensure NAs don't break if()
  
  if (any(zero_var)) {
    message("Found ", sum(zero_var), " zero-variance features in ", name)
  } else {
    message("✅ No zero-variance features detected in ", name)
  }
}


check_zero_variance(X$Tran, "Tran")
check_zero_variance(X$Prot, "Prot")
check_zero_variance(X$Lip, "Lip")

# Run DIABLO
MyResult.diablo <- block.splsda(X, Y)

correlation_matrix<-circosPlot(MyResult.diablo, cutoff = 0.98, size.variables = 0.4, plot = FALSE)
write.csv(correlation_matrix, file.path(output_dir, "Correlation_matrix.csv"), row.names = TRUE)

# Ensure row/col names are character
rownames(correlation_matrix) <- as.character(rownames(correlation_matrix))
colnames(correlation_matrix) <- as.character(colnames(correlation_matrix))

# Filter correlation_matrix: remove Tran columns and Prot/Lip rows
filtered_matrix <- correlation_matrix[
  !grepl("^(Prot|Lip)", rownames(correlation_matrix)),  # keep rows NOT starting with Prot or Lip
  !grepl("^Tran", colnames(correlation_matrix))         # keep columns NOT starting with Tran
]

# Optionally write this filtered matrix
write.csv(filtered_matrix, file.path(output_dir, "chord_Correlation_matrix.csv"), row.names = TRUE)

# Initialize list to hold counts per cutoff
cutoffs <- c(0.7, 0.75, 0.8, 0.85, 0.9, 0.95)
results <- list()

# Helper function to extract prefix
get_prefix <- function(name) {
  prefix <- str_extract(name, "^(Tran|Prot|Lip)")
  ifelse(is.na(prefix), "Unknown", prefix)
}

for (cutoff in cutoffs) {
  type_to_ids <- list()

  for (i in 1:(nrow(correlation_matrix)-1)) {
    for (j in (i+1):ncol(correlation_matrix)) {
      val <- correlation_matrix[i, j]
      if (!is.na(val) && val >= cutoff) {
        name1 <- rownames(correlation_matrix)[i]
        name2 <- colnames(correlation_matrix)[j]
        p1 <- get_prefix(name1)
        p2 <- get_prefix(name2)
        type <- paste(sort(c(p1, p2)), collapse = "_")

        if (!type %in% names(type_to_ids)) {
          type_to_ids[[type]] <- character()
        }

        # Add both elements to the type group
        type_to_ids[[type]] <- unique(c(type_to_ids[[type]], name1, name2))
      }
    }
  }

  # Count unique items per type
  type_to_counts <- lapply(type_to_ids, length)
  results[[as.character(cutoff)]] <- type_to_counts
}

# Save to JSON
json_output_path <- file.path(output_dir, "correlation_type_counts.json")
write_json(results, json_output_path, pretty = TRUE)

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

circosPlot(MyResult.diablo, cutoff = 0.98, size.variables = 0.4)
plotArrow(MyResult.diablo)
try({
  network(MyResult.diablo, blocks = c(1,2,3), 
          cutoff = 0.7,
          color.node = c('darkorchid', 'brown1', 'lightgreen'))
}, silent = TRUE)
dev.off()

circos.clear()

# # Convert to long format
# cor_long <- reshape2::melt(correlation_matrix)
# cor_filtered <- cor_long[abs(cor_long$value) > 0.98 & cor_long$Var1 != cor_long$Var2, ]

# # Determine omics block for group (example using prefixes)
# get_group <- function(name) {
#   if (grepl("^Tran", name)) return("Transcriptomics")
#   if (grepl("^Prot", name)) return("Proteomics")
#   if (grepl("^Lip", name)) return("Lipidomics")
#   return("Unknown")
# }

# nodes <- unique(c(cor_filtered$Var1, cor_filtered$Var2))
# nodes_df <- data.frame(
#   id = nodes,
#   group = sapply(nodes, get_group)
# )

# edges_df <- cor_filtered
# colnames(edges_df) <- c("source", "target", "value")

# # Create JSON
# network_json <- list(
#   nodes = nodes_df,
#   edges = edges_df
# )

# # Save or return as JSON
# write_json(network_json, file.path(output_dir, "network_data.json"), pretty = TRUE)

# # Extract relevant data from MyResult.diablo

# # Block 1 (Transcriptomics) components
# transcriptomics_components <- MyResult.diablo$variates$Transcriptomics[, 1]  # First component

# # Block 2 (Proteomics) components
# proteomics_components <- MyResult.diablo$variates$Proteomics[, 1]  # First component

# # Block 3 (Lipidomics) components
# lipidomics_components <- MyResult.diablo$variates$Lipidomics[, 1]  # First component

# # Outcome Y (e.g., cancer subtypes)
# subtypes <- as.character(MyResult.diablo$Y)  # Convert factor to character if needed
# subtypes <- gsub('(^"|"$)', '', subtypes) 
# subtypes <- trimws(subtypes)

# # Correlations between components
# correlation_t_p <- cor(transcriptomics_components, proteomics_components)
# correlation_t_l <- cor(transcriptomics_components, lipidomics_components)
# correlation_p_l <- cor(proteomics_components, lipidomics_components)

# indiv_t <- as.data.frame(MyResult.diablo$variates$Transcriptomics)
# indiv_p <- as.data.frame(MyResult.diablo$variates$Proteomics)
# indiv_l <- as.data.frame(MyResult.diablo$variates$Lipidomics)

# # Structure the data for the frontend

# plot_corr <- list(
#   components = list(
#     transcriptomics = transcriptomics_components,
#     proteomics = proteomics_components,
#     lipidomics = lipidomics_components
#   ),
#   subtypes = subtypes,
#   correlations = list(
#     t_p = correlation_t_p,
#     t_l = correlation_t_l,
#     p_l = correlation_p_l
#   )
# )

# plot_indiv <- list(
#   indiv_t = indiv_t,
#   indiv_p = indiv_p,
#   indiv_l = indiv_l,
#   subtypes = subtypes
# )

# data_for_react <- list(
#   plot_corr = plot_corr,
#   plot_indiv = plot_indiv
# )

# # Send this data as JSON or save it to a file for the React frontend
# #jsonlite::toJSON(data_for_react, pretty = TRUE)
# write_json(data_for_react, file.path(output_dir, "data_for_react.json"), pretty = TRUE)