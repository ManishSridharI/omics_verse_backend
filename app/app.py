# -*- coding: utf-8 -*-

import os
import pandas as pd
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS  # Import CORS
import mysql.connector
from flaskext.mysql import MySQL
import json
import re

# Define allowed hosts
ALLOWED_HOSTS = [
    'http://trbil.missouri.edu', 
    'http://digbio-soykb2.rnet.missouri.edu:3030/',
    'http://digbio-soykb2.rnet.missouri.edu:3030',
    'http://digbio-soykb2.rnet.missouri.edu'
]

app = Flask(__name__)
CORS(app, origins=ALLOWED_HOSTS)

mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'KBCommons'
app.config['MYSQL_DATABASE_PASSWORD'] = 'KsdbsaKNm55d3QtvtX44nSzS_'
app.config['MYSQL_DATABASE_DB'] = 'Omics_verse'
app.config['MYSQL_DATABASE_HOST'] = 'digbio-db1.rnet.missouri.edu'
mysql.init_app(app)

@app.route('/')
def home():
    return jsonify({
        "hello": "world"
    })

@app.route('/omic_lens', methods=['GET'])
def test_info():

    conn = mysql.connect()
    cursor =conn.cursor()

    cursor.execute("SELECT * FROM multiomics_metadata;")
    result = cursor.fetchall()

    return jsonify(result)

@app.route('/search', methods=['POST'])
def search():

    response = {"data": []}

    data = request.json
    
    organism = data.get("selectedOrganism")
    omics_type = data.get("selectedOmicsType")
    extraction_type = data.get("selectedMasterSheetType")
    conditions = data.get("selectedDevelopmentalStage")
    gene_id = data.get("geneId")
    gene_id_list = [gene.strip() for gene in gene_id.split(",") if gene.strip()]
    homolog_id = data.get("homolog_id")
    homolog_id_list = [gene.strip() for gene in homolog_id.split(",") if gene.strip()]
    pathway_id = data.get("pathway_id")
    pathway_id_list = [pathway.strip() for pathway in pathway_id.split(",") if pathway.strip()]
    pathway_name = data.get("pathway_name")
    pathway_name_list = [pathway.strip() for pathway in pathway_name.split(",") if pathway.strip()]
    keywords = data.get("keyword")
    keywords_list = [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]

    conn = mysql.connect()
    cursor =conn.cursor()
    query = """
            SELECT mapping_table_name
            FROM multiomics_metadata
            WHERE organism = %s AND omics_type = %s AND extraction_type = %s and conditions = %s
        """
    cursor.execute(query, (organism, omics_type, extraction_type, conditions))
    mapping_table_name = cursor.fetchall()[0]
    if isinstance(mapping_table_name, tuple):
        mapping_table_name = mapping_table_name[0]
    # cursor.close()
    # conn.close()
    search_results = []
    if gene_id_list:
        if gene_id_list[0].startswith("Cluster"):  # Check if the first element is a cluster ID
            clusters = ", ".join(["%s"] * len(gene_id_list))        
            search_query = f"SELECT * FROM {mapping_table_name} WHERE cluster_id IN ({clusters});"
            cursor.execute(search_query, gene_id_list)
            cluster_results = cursor.fetchall()
            search_results.extend(cluster_results)
        else:
            genes = ", ".join(["%s"] * len(gene_id_list))        
            search_query = f"SELECT * FROM {mapping_table_name} WHERE gene_id IN ({genes});"
            cursor.execute(search_query, gene_id_list)
            gene_results = cursor.fetchall()
            search_results.extend(gene_results)
    # if gene_id_list:
    #     genes = ", ".join(["%s"] * len(gene_id_list))        
    #     search_query = f"SELECT * FROM {mapping_table_name} WHERE gene_id IN ({genes});"

    #     cursor.execute(search_query, gene_id_list)
    #     gene_results = cursor.fetchall()
    #     search_results.extend(gene_results)
    if homolog_id_list:
        homologs = ", ".join(["%s"] * len(homolog_id_list))
        search_query = f"SELECT * FROM {mapping_table_name} WHERE ATGeneID IN ({homologs});"

        cursor.execute(search_query, homolog_id_list)
        homolog_results = cursor.fetchall()
        search_results.extend(homolog_results) 
    if pathway_id_list:        
        conditions = []
        for pathway in pathway_id_list:
            conditions.append(f"Arabidopsis__KEGG_ID LIKE %s")
        search_query = f"SELECT * FROM {mapping_table_name} WHERE ({' OR '.join(conditions)});"
        params = [f"%{pathway_id}%" for pathway_id in pathway_id_list]
        cursor.execute(search_query, params)
        
        pathway_id_results = cursor.fetchall()
        search_results.extend(pathway_id_results)
    if pathway_name_list:        
        conditions = []
        for pathway in pathway_name_list:
            conditions.append(f"Arabidopsis__KEGG_Pathway LIKE %s")
        search_query = f"SELECT * FROM {mapping_table_name} WHERE ({' OR '.join(conditions)});"
        print(search_query)
        params = [f"%{pathway_name}%" for pathway_name in pathway_name_list]
        cursor.execute(search_query, params)
        
        pathway_name_results = cursor.fetchall()
        search_results.extend(pathway_name_results)
    if keywords_list:
        cursor.execute(f"DESCRIBE {mapping_table_name};")
        columns = [column[0] for column in cursor.fetchall() if column[1] in ('varchar', 'text', 'char') and column[0] not in ('Arabidopsis__KEGG_Pathway', 'Arabidopsis__KEGG_ID')]
        conditions = []
        for keyword in keywords_list:
            conditions.append(" OR ".join([f"`{col}` LIKE %s" for col in columns]))
        search_query = f"SELECT * FROM {mapping_table_name} WHERE ({' OR '.join(conditions)});"
        params = [f"%{keyword}%" for keyword in keywords_list for _ in columns]
        cursor.execute(search_query, params)
        keyword_results = cursor.fetchall()
        search_results.extend(keyword_results) 

    headers = [desc[0] for desc in cursor.description]
    response = {
    "headers": headers,
    "data": search_results,
    "table_name": mapping_table_name
        }
    
    return jsonify(response)

# Function to extract numeric values from column names for sorting
def extract_numeric_sort_key(column_name):
    match = re.search(r'(\d+)', column_name)  # Extracts first number found
    return int(match.group(1)) if match else float('inf')  # Sort MAT last

@app.route('/OmicLens_plots', methods=['POST'])
def omiclens_plots():
    response = {"data": []}

    data = request.json
    mapping_table_name = data.get("experiment")
    gene_ids = data.get("input")
    gene_ids = [gene.strip() for gene in gene_ids.split(",") if gene.strip()]
    conn = mysql.connect()
    cursor =conn.cursor()
    
    cursor.execute(f"""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = %s 
        AND (COLUMN_NAME LIKE '%%p_value%%' OR COLUMN_NAME LIKE '%%log2FC%%' OR COLUMN_NAME IN ('gene_id', 'cluster_id', 'ATGeneID'))
    """, (mapping_table_name,))
    selected_columns = [row[0] for row in cursor.fetchall()]
    columns_str = ", ".join(selected_columns)
    
    timepoints = [col.replace("__log2FC", "") for col in selected_columns if "log2FC" in col]
    
    if gene_ids[0].startswith("Cluster"):  # Check if the first element is a cluster ID
        # Ensure gene_ids is passed as a tuple (for parameterized queries)
        clusters = ", ".join(["%s"] * len(gene_ids))
        search_query = f"SELECT {columns_str} FROM {mapping_table_name} WHERE cluster_id IN ({clusters});"
        cursor.execute(search_query, tuple(gene_ids))  # Pass gene_ids as a tuple
    else:
        # Ensure gene_ids is passed as a tuple (for parameterized queries)
        genes = ", ".join(["%s"] * len(gene_ids))
        search_query = f"SELECT {columns_str} FROM {mapping_table_name} WHERE gene_id IN ({genes});"
        cursor.execute(search_query, tuple(gene_ids))  # Pass gene_ids as a tuple
        
    search_results = cursor.fetchall()
    
    headers = [desc[0] for desc in cursor.description]

    response = {
    "headers": headers,
    "data": search_results,
    "timepoints": timepoints,
    "table_name": mapping_table_name
        }
    
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 3300)))
    
