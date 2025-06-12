import pandas as pd

def compare_mixomics(paths):
    cutoffs = [0.6, 0.7, 0.8, 0.9]
    results = []

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
                            if row_gene in goi_genes:
                                selected_genes.add(row_gene)
                            if col_gene in goi_genes:
                                selected_genes.add(col_gene)

            results.append({
                "matrix_path": matrix_path,
                "goi_path": goi_path,
                "tp": tp,
                "cutoff": cutoff,
                "matching_genes": sorted(selected_genes),
                "count": len(selected_genes)
            })

    return {
        "status": "success",
        "message": f"Processed {len(paths)} path pairs.",
        "results": results
    }
