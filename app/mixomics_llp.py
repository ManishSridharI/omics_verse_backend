# omiclens.py

import re
from flask import jsonify, request
import subprocess
import numpy as np
import pandas as pd
import csv
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
import subprocess
import os
import datetime

def goi_upload(mysql):
    if "file" not in request.files or "user_id" not in request.form:
        return jsonify({"error": "Missing file or user_id"}), 400

    file = request.files["file"]
    user_id = request.form["user_id"]
    timepoints = request.form["timepoints"]
    Organism = request.form["Organism"]
    OmicsType = request.form["OmicsType"]
    DevelopmentalStage = request.form["DevelopmentalStage"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith(".csv"):
        # Create timestamped folder for each upload
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
       
        folder_path = f"uploads/GOI_files/{user_id}/{timestamp_str}/"
        os.makedirs(folder_path, exist_ok=True)

        # Save file as goi.csv in the user-specific timestamped folder
        file_path = os.path.join(folder_path, "Genes_of_interest.csv")
        file.save(file_path)

        GOI_path = file_path
        
         # Define paths for each omics type
        cutoff_paths = {
            "Transcriptomics": f"organisms_cutoff/{Organism}/Transcriptomics/{DevelopmentalStage}/",
            "Proteomics": f"organisms_cutoff/{Organism}/Proteomics/{DevelopmentalStage}/",
            "Metabolomics": f"organisms_cutoff/{Organism}/Metabolomics/{DevelopmentalStage}/",
        }

        output_paths = {
            "Transcriptomics": f"uploads/cutoff/{user_id}/Transcriptomics/{timestamp_str}/",
            "Proteomics": f"uploads/cutoff/{user_id}/Proteomics/{timestamp_str}/",
            "Metabolomics": f"uploads/cutoff/{user_id}/Metabolomics/{timestamp_str}/",
        }

        # Insert file path into database
        try:
            conn = mysql.connect()
            cursor = conn.cursor()

            insert_query = """
                INSERT INTO genes_of_interest (file_path, uploaded_at, user_id, timepoints)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (file_path, timestamp, user_id, timepoints))
            conn.commit()
            cursor.close()
            conn.close()
            
            results_by_type = {}  # Store results separately by type

            for omics_type in ["Transcriptomics", "Proteomics", "Metabolomics"]:
                cutoff_path = cutoff_paths[omics_type]
                output_path = output_paths[omics_type]

                # Create output directory if it doesn't exist
                os.makedirs(output_path, exist_ok=True)

                # Run script for each omics type
                command = [
                    "python",
                    "New_count.py",
                    "--input_directory", cutoff_path,
                    "--output_directory", output_path,
                    "--GOI_path", GOI_path,
                    "--timepoints", timepoints,
                ]

                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode == 0:
                    # Path to the combined results file
                    combined_results_path = os.path.join(output_path, "final_combined_results.csv")
                    if os.path.exists(combined_results_path):
                        # Read and store the results separately
                        results_df = pd.read_csv(combined_results_path)
                        results_json = results_df.to_dict(orient="records")
                        results_by_type[omics_type] = results_json
                    else:
                        results_by_type[omics_type] = {"error": f"Results file not found for {omics_type}!"}
                else:
                    results_by_type[omics_type] = {"error": f"Error processing file for {omics_type}", "details": result.stderr}

            # Return results separately for each omics type
            return jsonify({"message": "File uploaded and processed successfully!", "cutoffs": results_by_type, "timestamp": timestamp_str}), 200

        except Exception as e:
            return jsonify({"error": f"Database or script error: {str(e)}"}), 500

    else:
        return jsonify({"error": "Invalid file type. Please upload a .csv file"}), 400
    
def mixomics_metadata(mysql):
    data = request.json
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is required'}), 400
    
    organism = data.get('selectedOrganism')
    omics_type = data.get('selectedOmicsType')
    extraction_type = data.get('selectedMasterSheetType')
    conditions = data.get('selectedDevelopmentalStage')

    try:
        connection = mysql.connect()
        with connection.cursor() as cursor:
            # Fetch mapping_table_name dynamically
            if omics_type == 'Transcriptomics':
                query = """
                    SELECT mapping_table_name
                    FROM multiomics_metadata
                    WHERE organism = %s AND omics_type = %s AND extraction_type = %s AND conditions = %s
                """
                cursor.execute(query, (organism, omics_type, extraction_type, conditions))
            else:
                query = """
                    SELECT mapping_table_name
                    FROM multiomics_metadata
                    WHERE organism = %s AND omics_type = %s 
                """
                cursor.execute(query, (organism, omics_type))
                
            result = cursor.fetchone()

            if result:
                mapping_table_name = result[0]
            else:
                return jsonify({'status': 'error', 'message': 'Mapping table name not found'}), 404
            
            # Prepare insert values
            timepoints = data.get('selectedTimepoints')
            top_degs = data.get('top_degs')
            q_value = data.get('q_value')
            log2fc_value = data.get('log2fc_value')
            up_regulated = data.get('up_regulated')
            down_regulated = data.get('down_regulated')
            genes_in_interest = data.get('genes_in_interest')
            genes_in_FAS = data.get('genes_in_FAS')
            common_genes = data.get('common_genes')
            created_at = data.get('created_at')
            
            # update_query = """
            #     UPDATE mixomics_metadata
            #     SET top_degs = %s, up_regulated = %s, down_regulated = %s, 
            #         q_value = %s, log2fc_value = %s, genes_in_interest = %s, 
            #         genes_in_FAS = %s, common_genes = %s
            #     WHERE mapping_table_name = %s AND timepoints = %s 
            #         AND user_id = %s AND created_at = %s AND omics_type = %s;
            # """
            # cursor.execute(update_query, (top_degs, up_regulated, down_regulated, q_value, log2fc_value, genes_in_interest, genes_in_FAS, common_genes, mapping_table_name, timepoints, user_id, created_at, omics_type))

                        
            # Insert into mixomics_metadata
         #   if cursor.rowcount == 0:
                # If no row was updated, insert a new one
            insert_query = """
                    INSERT INTO mixomics_metadata
                    (mapping_table_name, timepoints, top_degs, up_regulated, down_regulated, q_value, log2fc_value, genes_in_interest, genes_in_FAS, user_id, created_at, common_genes, omics_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    top_degs = VALUES(top_degs),
                    up_regulated = VALUES(up_regulated),
                    down_regulated = VALUES(down_regulated),
                    q_value = VALUES(q_value),
                    log2fc_value = VALUES(log2fc_value),
                    genes_in_interest = VALUES(genes_in_interest),
                    genes_in_FAS = VALUES(genes_in_FAS),
                    common_genes = VALUES(common_genes),
                    omics_type = VALUES(omics_type);
                                    """
            cursor.execute(insert_query, (mapping_table_name, timepoints, top_degs, up_regulated, down_regulated, q_value, log2fc_value, genes_in_interest, genes_in_FAS, user_id, created_at, common_genes, omics_type))
                    
        connection.commit()
    finally:
        connection.close()
    #trans_length, mixomics_folder_path, r_value_columns = filter_transcriptomics_data(mysql, organism)  
    try:
       # trans_length,pro_length,meta_length, mixomics_folder_path, r_value_columns = filter_data(mysql, organism)  
        
        if omics_type == 'Transcriptomics':
            trans_length, mixomics_folder_path, r_value_columns = filter_transcriptomics_data(mysql, organism)  
            filtered_data = {
                "trans_length": trans_length,
                "mixomics_folder_path": mixomics_folder_path, 
                "timepoints": r_value_columns
            }
        elif omics_type == 'Proteomics':
            pro_length = filter_proteomics_data(mysql, organism)  
            filtered_data = {
                "pro_length": pro_length
            }
        elif omics_type == 'Metabolomics':
            meta_length = filter_metabolomics_data(mysql, organism)  
            filtered_data = {
                "meta_length": meta_length
            }
            
        response = {'status': 'success', 'message': 'Data inserted successfully', 'data': filtered_data}
    
    except Exception as e:
        response = {'status': 'error', 'message': str(e), 'data': {}}

    return jsonify(response)

def filter_transcriptomics_data(mysql, organism):
    try:
        connection = mysql.connect()
        with connection.cursor() as cursor:
            # Fetch all metadata for filtering (including the timepoints)
            metadata_query = """
                SELECT mapping_table_name, timepoints, q_value, log2fc_value, user_id, created_at 
                FROM mixomics_metadata WHERE omics_type = 'Transcriptomics'
                AND created_at = (
                    SELECT MAX(created_at) 
                    FROM mixomics_metadata 
                    WHERE omics_type = 'Transcriptomics'
                )
            """
            cursor.execute(metadata_query)
            metadata_rows = cursor.fetchall()  # This will return all matching rows

            if not metadata_rows:
                return jsonify({'status': 'error', 'message': 'No metadata found'}), 404

            trans_lengths = []  # To store results for all timepoints
            all_folder_paths = []  # To store paths for all timepoints
            all_r_value_columns = []  # To store columns for each timepoint

            # Loop through all the metadata rows (timepoints)
            for metadata in metadata_rows:
                mapping_table_name, tp, q_value, log2fc_value, user_id, created_at = metadata
                created_at = created_at.strftime('%Y%m%d%H%M%S')

                # Dynamically generate the required columns (p_value, q_value, log2FC for each timepoint)
                stat_columns = []
                p_q_conditions = []
                log2_conditions = []
                r_value_columns = []
                stat_columns.extend([f"{tp}_p_value", f"{tp}_q_value", f"{tp}__log2FC"])

                # Add p/q conditions only if q_value is not None
                if q_value is not None:
                    p_q_conditions.append(f"({tp}_q_value <= %s)")

                # Add log2FC conditions only if log2fc_value is not None
                if log2fc_value is not None:
                    log2_conditions.append(f"({tp}__log2FC >= %s OR {tp}__log2FC <= %s)")

                tp1, tp2 = tp.split("_vs_")

                # Add corresponding R1, R2, R3, R4 columns for each timepoint (tp1, tp2)
                for i in range(1, 5):
                    r_value_columns.append(f"{tp1}_R{i}")
                    r_value_columns.append(f"{tp2}R{i}")

                selected_columns = ", ".join(["gene_id", "ATGeneID"] + stat_columns + r_value_columns)

                # Construct WHERE clause for p/q and log2FC filtering, only include conditions that are not empty
                where_conditions = []
                if p_q_conditions:
                    where_conditions.append("(" + " AND ".join(p_q_conditions) + ")")
                if log2_conditions:
                    where_conditions.append("(" + " AND ".join(log2_conditions) + ")")

                # Combine the conditions with AND
                where_clause = " AND ".join(where_conditions)

                query = f"""
                    SELECT {selected_columns} 
                    FROM {mapping_table_name}
                    WHERE {where_clause}
                """
                
                # Create query parameters for p/q and log2FC conditions
                query_params = []

                if p_q_conditions:
                    if q_value is not None:
                        query_params.append(q_value)

                if log2_conditions:
                    if log2fc_value is not None:
                        query_params.append(log2fc_value)
                        query_params.append(-log2fc_value)

                cursor.execute(query, query_params)
                filtered_data = cursor.fetchall()
                trans_length = len(filtered_data)

                # Create a new dataset containing only gene_id and R1, R2, R3, R4 values for all timepoints
                gene_r_values = []
                for row in filtered_data:
                    gene_id = row[0]  # Assuming the gene_id is in the first column
                    r_values = row[2 + len(stat_columns):]  # Extract only the R1, R2, R3, R4 values

                    # Append gene_id and the corresponding R values
                    gene_r_values.append([gene_id] + list(r_values))

                headers = ['gene_id'] + r_value_columns
                gene_r_values_with_headers = [headers] + gene_r_values

                # Convert gene_r_values to a NumPy array for easy transposition
                transposed_data = np.array(gene_r_values_with_headers).T  # Transpose the data

                # Create a DataFrame from the transposed data
                df = pd.DataFrame(transposed_data[1:], columns=transposed_data[0])

                # Save the DataFrame to a CSV file
                folder_path = f"uploads/mixomics_input_files/{user_id}/{created_at}/{tp}/"
                os.makedirs(folder_path, exist_ok=True)
                output_file_transposed = os.path.join(folder_path, "transcriptomics.csv")
                df.to_csv(output_file_transposed, index=False, sep ='\t')

                # Store the results for each timepoint
                trans_lengths.append(trans_length)
                all_folder_paths.append(folder_path)
                all_r_value_columns.append(r_value_columns)

            connection.close()

            return trans_lengths, all_folder_paths, all_r_value_columns

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def filter_proteomics_data(mysql,organism):
    try:
        connection = mysql.connect()
        with connection.cursor() as cursor:
            # Fetch metadata for filtering
            metadata_query = """
                SELECT mapping_table_name, timepoints, q_value, log2fc_value, user_id, created_at 
                FROM mixomics_metadata WHERE omics_type = 'Proteomics'
                AND created_at = (
                    SELECT MAX(created_at) 
                    FROM mixomics_metadata 
                    WHERE omics_type = 'Proteomics'
                )
            """
            cursor.execute(metadata_query)
            metadata_rows = cursor.fetchall()  # This will return all matching rows
            
            if not metadata_rows:
                return jsonify({'status': 'error', 'message': 'No metadata found'}), 404
            
            pros_lengths = []

            for metadata in metadata_rows:
                mapping_table_name, tp, q_value, log2fc_value, user_id, created_at = metadata
                created_at = created_at.strftime('%Y%m%d%H%M%S')
                
                stat_columns = []
                p_q_conditions = []
                log2_conditions = []
                r_value_columns = []
                stat_columns.extend([f"{tp}_PValue", f"{tp}_FDR", f"{tp}_logFC"])
                
                if q_value is not None:
                    p_q_conditions.append(f"({tp}_FDR <= %s)")

                if log2fc_value is not None:
                    log2_conditions.append(f"({tp}_logFC >= %s OR {tp}_logFC <= %s)")

                tp1, tp2 = tp.split("_vs_")
                
                for i in range(1, 5):
                    r_value_columns.append(f"{tp1}_R{i}")
                    r_value_columns.append(f"{tp2}R{i}")
                
                selected_columns = ", ".join(["gene_id"] + stat_columns + r_value_columns)
            
                where_conditions = []
                if p_q_conditions:
                    where_conditions.append("(" + " AND ".join(p_q_conditions) + ")")
                if log2_conditions:
                    where_conditions.append("(" + " AND ".join(log2_conditions) + ")")

                where_clause = " AND ".join(where_conditions)

                query = f"""
                    SELECT {selected_columns} 
                    FROM {mapping_table_name}
                    WHERE {where_clause}
                """
               
                query_params = []
                
                if p_q_conditions:
                    if q_value is not None:
                        query_params.append(q_value)

                if log2_conditions:
                    if log2fc_value is not None:
                        query_params.append(log2fc_value)
                        query_params.append(-log2fc_value)
               
                cursor.execute(query, query_params)
                filtered_data = cursor.fetchall()
               
                pro_length = len(filtered_data)
 
                gene_r_values = []
                for row in filtered_data:
                    gene_id = row[0]  
                    r_values = row[1 + len(stat_columns):]  

                    gene_r_values.append([gene_id] + list(r_values))
                
                headers = ['gene_id'] + r_value_columns
                gene_r_values_with_headers = [headers] + gene_r_values

                transposed_data = np.array(gene_r_values_with_headers).T 
                df = pd.DataFrame(transposed_data[1:], columns=transposed_data[0])
                #print(df)
                folder_path = f"uploads/mixomics_input_files/{user_id}/{created_at}/{tp}/"
               
                os.makedirs(folder_path, exist_ok=True)
                output_file_transposed = os.path.join(folder_path, "proteomics.csv")
                
                df.to_csv(output_file_transposed, index=False, sep ='\t')
              
                pros_lengths.append(pro_length)

        connection.close()

        return pros_lengths

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def filter_metabolomics_data(mysql,organism):
    try:
        connection = mysql.connect()
        with connection.cursor() as cursor:
            # Fetch metadata for filtering
            metadata_query = """
                SELECT mapping_table_name, timepoints, q_value, log2fc_value, user_id, created_at 
                FROM mixomics_metadata WHERE omics_type = 'Metabolomics'
                AND created_at = (
                    SELECT MAX(created_at) 
                    FROM mixomics_metadata 
                    WHERE omics_type = 'Metabolomics'
                )
            """
            cursor.execute(metadata_query)
            metadata_rows = cursor.fetchall()  # This will return all matching rows

            if not metadata_rows:
                return jsonify({'status': 'error', 'message': 'No metadata found'}), 404
            
            meta_lengths = []

            for metadata in metadata_rows:
                mapping_table_name, tp, q_value, log2fc_value, user_id, created_at = metadata
                created_at = created_at.strftime('%Y%m%d%H%M%S')
                
                stat_columns = []
                p_q_conditions = []
                log2_conditions = []
                r_value_columns = []
                stat_columns.extend([f"{tp}_PValue", f"{tp}_FDR", f"{tp}_logFC"])
                
                if q_value is not None:
                    p_q_conditions.append(f"({tp}_FDR <= %s)")

                if log2fc_value is not None:
                    log2_conditions.append(f"({tp}_logFC >= %s OR {tp}_logFC <= %s)")

                tp1, tp2 = tp.split("_vs_")
                
                for i in range(1, 5):
                    r_value_columns.append(f"{tp1}_R{i}")
                    r_value_columns.append(f"{tp2}R{i}")
                
                selected_columns = ", ".join(["gene_id"] + stat_columns + r_value_columns)
            
                where_conditions = []
                if p_q_conditions:
                    where_conditions.append("(" + " AND ".join(p_q_conditions) + ")")
                if log2_conditions:
                    where_conditions.append("(" + " AND ".join(log2_conditions) + ")")

                where_clause = " AND ".join(where_conditions)

                query = f"""
                    SELECT {selected_columns} 
                    FROM {mapping_table_name}
                    WHERE {where_clause}
                """
            
                query_params = []
                
                if p_q_conditions:
                    if q_value is not None:
                        query_params.append(q_value)

                if log2_conditions:
                    if log2fc_value is not None:
                        query_params.append(log2fc_value)
                        query_params.append(-log2fc_value)

                cursor.execute(query, query_params)
                filtered_data = cursor.fetchall()
                m_length = len(filtered_data)
 
                gene_r_values = []
                for row in filtered_data:
                    gene_id = row[0]  
                    r_values = row[1 + len(stat_columns):]  

                    gene_r_values.append([gene_id] + list(r_values))
                
                headers = ['gene_id'] + r_value_columns
                gene_r_values_with_headers = [headers] + gene_r_values

                transposed_data = np.array(gene_r_values_with_headers).T 
                df = pd.DataFrame(transposed_data[1:], columns=transposed_data[0])
            
                folder_path = f"uploads/mixomics_input_files/{user_id}/{created_at}/{tp}/"
                os.makedirs(folder_path, exist_ok=True)
                output_file_transposed = os.path.join(folder_path, "metabolomics.csv")
                
                df.to_csv(output_file_transposed, index=False, sep ='\t')
                
                meta_lengths.append(m_length)

        connection.close()
        
        return meta_lengths

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
    # try:
    #     result = subprocess.run(
    #         ['Rscript', 'Mixomixs.R'], 
    #         check=True, 
    #         capture_output=True, 
    #         text=True
    #     )
    #     print("R Script Output:", result.stdout)
    #     print("R Script Error (if any):", result.stderr)
    #     # Return success message with R script output
    #     return {'status': 'success', 'output': result.stdout.strip()}

    # except subprocess.CalledProcessError as e:
    #     error_message = e.stderr.strip() if e.stderr else "Unknown error in R script."
    #     print("Error Running R Script:", error_message)  # Debugging

    #     # Return error response
    #     return {'status': 'error', 'error': error_message}
    