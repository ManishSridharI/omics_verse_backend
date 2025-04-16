import pandas as pd
import os
import argparse

def count_differential_genes(file_path, cutoffs, genes_of_interest, fas_genes, filename):
    """Counts differentially expressed genes and checks for presence in gene lists."""
    # Try different delimiters to determine file format
    try:
        df = pd.read_csv(file_path, sep=None, engine="python")  # Auto-detect separator
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    print(f"Processing file: {file_path}")
    print("Column names in dataset:", df.columns.tolist())

    # Possible column name variations
    gene_col_candidates = ['gene','gene_id']  # Adjust if necessary
    q_value_candidates = ['q_value', 'padj', 'p.adjust', 'FDR']
    log2fc_candidates = ['log2(fold_change)', 'log2FoldChange', 'log2FC', 'logFC']

    gene_col = next((col for col in gene_col_candidates if col in df.columns), None)
    q_value_col = next((col for col in q_value_candidates if col in df.columns), None)
    log2fc_col = next((col for col in log2fc_candidates if col in df.columns), None)

    if not q_value_col or not log2fc_col or gene_col not in df.columns:
        print(f"Skipping {file_path} - Missing required columns.")
        return None

    # Convert values to numeric and handle NaNs
    df[q_value_col] = pd.to_numeric(df[q_value_col], errors='coerce')
    df[log2fc_col] = pd.to_numeric(df[log2fc_col], errors='coerce')
    df.dropna(subset=[q_value_col, log2fc_col], inplace=True)

    results = []
    for q_val, log2fc in cutoffs:
        filtered_df = df[df[q_value_col] <= q_val]
        upregulated = filtered_df[filtered_df[log2fc_col] >= log2fc]
        downregulated = filtered_df[filtered_df[log2fc_col] <= -log2fc]

        # Count genes in lists
        up_down_genes = set(upregulated[gene_col].tolist() + downregulated[gene_col].tolist())
        genes_in_interest_list = len(up_down_genes.intersection(genes_of_interest))
        genes_in_fas_list = len(up_down_genes.intersection(fas_genes))
        common_genes = len(up_down_genes.intersection(genes_of_interest, fas_genes))

        results.append({
            "file_name": filename,
            "q_value_cutoff": q_val,
            "log2fc_cutoff": log2fc,
            "total_differentially_expressed": len(upregulated) + len(downregulated),
            "upregulated": len(upregulated),
            "downregulated": len(downregulated),
            "genes_in_interest_list": genes_in_interest_list,
            "genes_in_FAS_list": genes_in_fas_list,
            "common_genes": common_genes
        })

    return pd.DataFrame(results)

def main(input_directory, output_directory, GOI_path, timepoints):
    # Define cutoffs
    cutoffs = [(0.05, i) for i in range(1, 13)] + [(0.01, i) for i in range(1, 13)] + [(0.001, i) for i in range(1, 13)]

    # Load gene lists
    genes_of_interest = set(pd.read_csv(GOI_path).iloc[:, 0].tolist())
    fas_genes = set(pd.read_csv("/app/FAS_description_genes.csv").iloc[:, 0].tolist())

    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    selected_timepoints = timepoints.split(",")

    # Process files
    all_results = []
    for filename in os.listdir(input_directory):
        if any(tp in filename for tp in selected_timepoints) and filename.endswith((".csv", ".tsv")):
            file_path = os.path.join(input_directory, filename)
            results_df = count_differential_genes(file_path, cutoffs, genes_of_interest, fas_genes, filename)

            if results_df is not None:
                all_results.append(results_df)

    # Combine all results into a single file
    if all_results:
        final_results_df = pd.concat(all_results, ignore_index=True)
        final_output_file = os.path.join(output_directory, "final_combined_results.csv")
        final_results_df.to_csv(final_output_file, index=False)
        print(f"Final combined results saved to {final_output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process differential gene expression files.")
    parser.add_argument("--input_directory", required=True, help="Path to input directory containing gene expression files.")
    parser.add_argument("--output_directory", required=True, help="Path to output directory to save results.")
    parser.add_argument("--GOI_path", required=True, help="Path to genes of interest CSV file.")
    parser.add_argument("--timepoints", required=True, help="Comma-separated list of timepoints to process")
    
    args = parser.parse_args()

    main(args.input_directory, args.output_directory, args.GOI_path, args.timepoints)


