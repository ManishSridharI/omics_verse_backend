import pandas as pd
from datetime import datetime
import os
import json
import subprocess

def compare_mixomics(paths, user_id):
    cutoffs = [0.6, 0.7, 0.8, 0.9]
    results = []
    user_id = user_id

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(f"compare_inputs/{user_id}", exist_ok=True)
    output_json_path = f"compare_inputs/{user_id}/{timestamp}.json"
    os.makedirs(f"venn_results/{user_id}", exist_ok=True)
    venn_output_path = f"venn_results/{user_id}/compare_{timestamp}.pdf"

    for path_pair in paths:
        matrix_path = f"{path_pair[0]}/chord_Correlation_matrix.csv"
        goi_path = path_pair[1]
        tp = path_pair[2]

        # Read files
        try:
            matrix_df = pd.read_csv(matrix_path, index_col=0)
            # Clean prefixes from index and columns
            matrix_df.index = matrix_df.index.str.replace(r'^(Tran_|Prot_|Lip_)', '', regex=True)
            matrix_df.columns = matrix_df.columns.str.replace(r'^(Tran_|Prot_|Lip_)', '', regex=True)

            # # Also check and clean the index name if needed
            # if matrix_df.index.name:
            #     matrix_df.index.name = matrix_df.index.name.replace('Tran_', '').replace('Pro_', '').replace('Lip_', '')
            goi_df = pd.read_csv(goi_path, header=None)
            goi_genes = set(goi_df[0].astype(str).str.strip())
        except Exception as e:
            results.append({
                "matrix_path": matrix_path,
                "goi_path": goi_path,
                "error": str(e)
            })
            continue

        # Remove diagonal if it's a square matrix with same row/column names
        for cutoff in cutoffs:
            selected_genes = set()

            for i, row_gene in enumerate(matrix_df.index):
                for j, col_gene in enumerate(matrix_df.columns):
                    if row_gene != col_gene:
                        value = matrix_df.iloc[i, j]
                        if pd.notna(value) and abs(value) >= cutoff:
                            # if row_gene in goi_genes:
                            #     selected_genes.add(row_gene)
                            # if col_gene in goi_genes:
                            #     selected_genes.add(col_gene)
                            selected_genes.add(row_gene)
                            selected_genes.add(col_gene)

            results.append({
                # "matrix_path": matrix_path,
                # "goi_path": goi_path,
                "tp": tp,
                "cutoff": cutoff,
                "matching_genes": sorted(selected_genes),
                "count": len(selected_genes)
            })

    with open(output_json_path, "w") as f:
        json.dump({"results": results}, f, indent=2)

    # Run R script with JSON input and PDF output paths
    command = ["Rscript", "venn.R", output_json_path, venn_output_path]
    r_process = subprocess.run(command, capture_output=True, text=True)

    if r_process.returncode != 0:
        return {
            "status": "error",
            "message": "Venn R script failed.",
            "stderr": r_process.stderr
        }

    return {
        "status": "success",
        "message": f"Processed {len(paths)} path pairs.",
        # "results": results,
        # "user_id": user_id,
        "venn_plot_path": venn_output_path,
    }


def compare_mixomics_cutoff(result_path, GOI_path, cutoffs, user_id):
    cutoffs = cutoffs
    results = []
    user_id = user_id
    print(result_path, GOI_path, cutoffs, user_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(f"compare_inputs_cutoff/{user_id}", exist_ok=True)
    output_json_path = f"compare_inputs_cutoff/{user_id}/{timestamp}.json"
    os.makedirs(f"venn_results_cutoff/{user_id}", exist_ok=True)
    venn_output_path = f"venn_results_cutoff/{user_id}/compare_{timestamp}.pdf"

    matrix_path = f"{result_path}/chord_Correlation_matrix.csv"
    goi_path = GOI_path

    # Read files
    try:
        matrix_df = pd.read_csv(matrix_path, index_col=0)
        # Clean prefixes from index and columns
        matrix_df.index = matrix_df.index.str.replace(r'^(Tran_|Prot_|Lip_)', '', regex=True)
        matrix_df.columns = matrix_df.columns.str.replace(r'^(Tran_|Prot_|Lip_)', '', regex=True)

        # # Also check and clean the index name if needed
        # if matrix_df.index.name:
        #     matrix_df.index.name = matrix_df.index.name.replace('Tran_', '').replace('Pro_', '').replace('Lip_', '')
        goi_df = pd.read_csv(goi_path, header=None)
        goi_genes = set(goi_df[0].astype(str).str.strip())
    except Exception as e:
        results.append({
            "matrix_path": matrix_path,
            "goi_path": goi_path,
            "error": str(e)
        })
        

    # Remove diagonal if it's a square matrix with same row/column names
    for cutoff in map(float, cutoffs):
        selected_genes = set()

        for i, row_gene in enumerate(matrix_df.index):
            for j, col_gene in enumerate(matrix_df.columns):
                if row_gene != col_gene:
                    value = matrix_df.iloc[i, j]
                    if pd.notna(value) and abs(value) >= cutoff:
                        # if row_gene in goi_genes:
                        #     selected_genes.add(row_gene)
                        # if col_gene in goi_genes:
                        #     selected_genes.add(col_gene)
                        selected_genes.add(row_gene)
                        selected_genes.add(col_gene)

        results.append({
            # "matrix_path": matrix_path,
            # "goi_path": goi_path,
            "cutoff": cutoff,
            "matching_genes": sorted(selected_genes),
            "count": len(selected_genes)
        })
    results.append({
        "cutoff": "goi",
        "matching_genes": sorted(goi_genes),
        "count": len(goi_genes)
    })

    with open(output_json_path, "w") as f:
        json.dump({"results": results}, f, indent=2)

    #Run R script with JSON input and PDF output paths
    command = ["Rscript", "venn_cutoff.R", output_json_path, venn_output_path]
    r_process = subprocess.run(command, capture_output=True, text=True)

    if r_process.returncode != 0:
        return {
            "status": "error",
            "message": "Venn R script failed.",
            "stderr": r_process.stderr
        }

    return {
        "status": "success",
        "message": f"Processed cutoff pairs.",
        # "results": results,
        # "user_id": user_id,
        "venn_plot_path": venn_output_path,
    }
