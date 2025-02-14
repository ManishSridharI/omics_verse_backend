# -*- coding: utf-8 -*-

import os
import pandas as pd
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS  # Import CORS
import mysql.connector
from flaskext.mysql import MySQL
import json
import re
from omic_lens import search, omiclens_plots

# Define allowed hosts
ALLOWED_HOSTS = [
    'http://trbil.missouri.edu', 
    'http://digbio-soykb2.rnet.missouri.edu:3030/',
    'http://digbio-soykb2.rnet.missouri.edu:3030',
    'http://digbio-soykb2.rnet.missouri.edu',
    'http://digbio-devel.missouri.edu:3030/',
    'http://digbio-devel.missouri.edu:3030',
    'http://digbio-devel.missouri.edu'
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

@app.route('/meta_data', methods=['GET'])
def meta_data():

    conn = mysql.connect()
    cursor =conn.cursor()

    cursor.execute("SELECT * FROM multiomics_metadata;")
    result = cursor.fetchall()

    return jsonify(result)

@app.route('/search', methods=['POST'])
def search_endpoint():
    return search(mysql)

@app.route('/OmicLens_plots', methods=['POST'])
def omiclens_plots_endpoint():
    return omiclens_plots(mysql)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 3300)))
    
