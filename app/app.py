# -*- coding: utf-8 -*-

import os
from flask import Flask, jsonify, request, session, Blueprint, send_file, send_from_directory
from flask_cors import CORS  # Import CORS
import mysql.connector
from flaskext.mysql import MySQL
import json
import re
from omic_lens import search, omiclens_plots
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from mixomics_llp import mixomics_metadata, goi_upload
from celery_config import make_celery
from compare import compare_mixomics, compare_mixomics_cutoff
import subprocess
import numpy as np
import pandas as pd
import datetime
import uuid
import logging
import shutil
from io import BytesIO
import tempfile
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Define allowed hosts
ALLOWED_HOSTS = [
    'http://trbil.missouri.edu', 
    'http://digbio-soykb2.rnet.missouri.edu:3030/',
    'http://digbio-soykb2.rnet.missouri.edu:3030',
    'http://digbio-soykb2.rnet.missouri.edu',
    'http://digbio-devel.missouri.edu:3030/',
    'http://digbio-devel.missouri.edu:3030',
    'http://digbio-devel.missouri.edu',
    'omics_portal_frontend',
    'omics_verse_frontend-web',
    '127.0.0.1',
    'localhost',
    'http://omics_portal_frontend:3030',
    'http://omics_verse_frontend-web:3030',
    'http://127.0.0.1:3030',
    'http://localhost:3030',
]

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=ALLOWED_HOSTS)

mysql = MySQL()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.init_app(app)

app.config['MYSQL_DATABASE_USER'] = 'KBCommons'
app.config['MYSQL_DATABASE_PASSWORD'] = 'KsdbsaKNm55d3QtvtX44nSzS_'
app.config['MYSQL_DATABASE_DB'] = 'Omics_verse'
app.config['MYSQL_DATABASE_HOST'] = 'digbio-db1.rnet.missouri.edu'
app.config['SECRET_KEY'] = 'supersecretkey'

mysql.init_app(app)

celery = make_celery(app)

# User Model for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        
# User Loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user[0], user[1], user[2], user[3])
    return None

# Email validation function
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email)

# Register Endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    organization = data.get('organization')

    if not username or not email or not password:
        return jsonify({"message": "Missing username, email, or password"}), 400

    if not is_valid_email(email):
        return jsonify({"message": "Invalid email format"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = mysql.connect()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password, organization) VALUES (%s, %s, %s, %s)", (username, email, hashed_password, organization))
        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except:
        return jsonify({"message": "Username or email already exists"}), 400

# Login Endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if user and bcrypt.check_password_hash(user[2], password):
        user_obj = User(user[0], user[1], user[2], user[3])
        login_user(user_obj)
        response = jsonify({
        "message": "Login successful",
        "user": {
            "username": user[1],  # Modify this based on your actual DB column
            "user_id": user[0],
        }
    })
        return response, 200
    return jsonify({"message": "Invalid username or password"}), 401

# Logout Endpoint
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200

# Protected Route (Only Logged-In Users)
@app.route('/protected', methods=['GET'])
@login_required
def protected():
    return jsonify({"message": f"Hello, {current_user.username} ({current_user.email})!"}), 200

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

@app.route('/goi_upload', methods=['POST'])
def goi_upload_endpoint():
    return goi_upload(mysql)

@app.route('/mixomics_metadata', methods=['POST'])
def mixomics_metadata_endpoint():
    return mixomics_metadata(mysql)

# @app.route('/start_task', methods=['POST'])
# def mixomics_start_task_endpoint():
#     return mixomics_start_task(mysql)

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    conn = mysql.connect()
    cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
    
    try:
        cursor.execute("SELECT id, user_id, organism, timepoint, status, created_at, started_at, completed_at FROM mixomics_tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({"status": "error", "message": "Task not found"}), 404
            
        return jsonify({"status": "success", "task": task})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
    finally:
        cursor.close()
        conn.close()

# Get all tasks for a user
@app.route('/user_tasks/<user_id>', methods=['GET'])
def user_tasks(user_id):
    conn = mysql.connect()
    cursor = conn.cursor()  # Return results as dictionaries

    try:
        cursor.execute(
            "SELECT id, organism, timepoint,status, created_at, started_at, completed_at, q_value, log2_fc FROM mixomics_tasks WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,))
        
        tasks = cursor.fetchall()
        return jsonify({"status": "success", "tasks": tasks})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
        

@celery.task(name="run_r_script")
def run_r_script(task_id, user_id, timepoint, timepoint_ids, mixomics_folder_path, GOI_path):
    """Celery task to run the R script with appropriate parameters"""
    
    Y_ids = [id.split('R')[0].rstrip('_') for id in timepoint_ids]
   
    try:
        # Run R script with subprocess
        cmd = ['Rscript', '/app/Mixomixs_R.R', 
               '--folder', mixomics_folder_path,
               '--ids', ",".join([f'"{i}"' for i in Y_ids]),
               '--timepoints', ",".join([f'"{tp}"' for tp in timepoint_ids]),
               '--task_id', task_id,
               '--user_id', user_id,
               '--GOI_path', GOI_path]
       
        logger.info(f"Running command: {cmd}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Connect to database
        conn = mysql.connect()
        cursor = conn.cursor()
        
        # Update task status in database
        cursor.execute(
            "UPDATE mixomics_tasks SET status = %s, completed_at = %s, result = %s WHERE id = %s",
            ("success", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result.stdout, task_id)
        )
        conn.commit()
        conn.close()
        
        return {"status": "success", "output": result.stdout}
    
    except subprocess.CalledProcessError as e:
        # Connect to database
        
        conn = mysql.connect()
        cursor = conn.cursor()
        
        # Update task status with error
        cursor.execute(
            "UPDATE mixomics_tasks SET status = %s, completed_at = %s, error = %s WHERE id = %s",
            ("failed", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e.stderr, task_id)
        )
        conn.commit()
        conn.close()
        
        return {"status": "error", "error": e.stderr}

@app.route('/start_task', methods=['POST'])
def mixomics_start_task():
    """Handle mixomics task creation and scheduling"""
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is required'}), 400
    
    mixomics_folder_paths = data.get('mixomics_folder_path')
    timepoint_ids_list = data.get('timepoint_ids')
    log2fc_for_compare_list = data.get('log2fc_for_compare')
    qvalue_for_compare_list = data.get('qvalue_for_compare')
    tps_list = data.get('tps')
    organism = data.get('selectedOrganism')
    GOI_path = data.get('GOI_path')
    
    if not (len(mixomics_folder_paths) == len(timepoint_ids_list) == len(tps_list) == len(log2fc_for_compare_list)):
        return jsonify({'status': 'error', 'message': 'Mismatched payload lengths'}), 400

    task_ids = []
    conn = mysql.connect()
    cursor = conn.cursor()
    
    try:
        # Create tasks table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mixomics_tasks (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            organism VARCHAR(255) NOT NULL,
            timepoint VARCHAR(255) NOT NULL,
            timepoint_ids TEXT NOT NULL,
            mixomics_folder_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP NULL,
            completed_at TIMESTAMP NULL,
            status VARCHAR(20) DEFAULT 'pending',
            result TEXT NULL,
            error TEXT NULL,
            GOI_path VARCHAR(200) NULL,
            q_value FLOAT NOT NULL,
            log2_fc INT NOT NULL
        )
        """)
        conn.commit()
        
        # Insert tasks and schedule them
        for i in range(len(tps_list)):
            task_id = str(uuid.uuid4())
            
            timepoint_ids_str = json.dumps(timepoint_ids_list[i])
            
            # Insert task info into database
            cursor.execute("""
            INSERT INTO mixomics_tasks 
            (id, user_id, organism, timepoint, timepoint_ids, mixomics_folder_path, status, started_at, GOI_path, q_value, log2_fc) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                task_id, 
                user_id, 
                organism,
                tps_list[i], 
                timepoint_ids_str, 
                str(mixomics_folder_paths[i]),
                "scheduled",
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                GOI_path,
                qvalue_for_compare_list[i],
                log2fc_for_compare_list[i]
            ))
            
            Y_ids = [id.split('R')[0].rstrip('_') for id in (timepoint_ids_list[i])]
       
           
            cmd = ['Rscript', '/app/Mixomixs_R.R', 
               '--folder', mixomics_folder_paths[i],
               '--ids', ",".join([f'"{i}"' for i in Y_ids]),
               '--timepoints', str(timepoint_ids_list[i]),
               '--task_id', task_id,
               '--user_id', user_id,
               '--GOI_path', GOI_path]
            print(cmd)
            
            # Schedule the task using Celery
            run_r_script.delay(
                task_id,
                user_id,
                tps_list[i],
                timepoint_ids_list[i],
                mixomics_folder_paths[i],
                GOI_path
            )
            
            task_ids.append(task_id)
        
        conn.commit()
        
        print(f"Tasks created and scheduled: {task_ids}")
        return jsonify({
            'status': 'success', 
            'message': f'{len(task_ids)} tasks scheduled successfully',
            'task_ids': task_ids
        })
        
    except Exception as e:
        conn.rollback()
        print(f"Error scheduling tasks: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error scheduling tasks: {str(e)}'}), 500
    
    finally:
        cursor.close()
        conn.close()
   
@app.route('/results/<user_id>/<task_id>', methods=['GET'])
def download_results(user_id, task_id):
    # Define the folder path to the task directory
    folder_path = os.path.join('results', user_id, task_id)  # Adjust path as needed
    print(folder_path)
    # Check if folder exists
    if not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"}), 404

    # Create a temporary file to hold the ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')

    try:
        # Create a ZIP archive of the folder in the temporary file
        shutil.make_archive(temp_zip.name, 'zip', folder_path)

        # Open the temporary file in binary mode
        with open(temp_zip.name, 'rb') as zip_file:
            # Send the file as a response
            return send_file(zip_file, as_attachment=True, download_name=f'mixomics_results_{task_id}.zip', mimetype='application/zip')

    finally:
        # Clean up by removing the temporary zip file
        os.remove(temp_zip.name)

@app.route('/app/results/<user_id>/<task_id>/<filename>')
def serve_file(user_id, task_id, filename):
    file_path = f'/app/results/{user_id}/{task_id}/{filename}'
    if os.path.exists(file_path):
        return send_from_directory(os.path.dirname(file_path), filename)
    else:
        return "File not found", 404

@app.route('/app/venn_results/<user_id>/<filename>')
def download_venn(user_id, filename):
    directory = os.path.join("venn_results", user_id)
    if not os.path.exists(os.path.join(directory, filename)):
        return abort(404)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/app/venn_results_cutoff/<user_id>/<filename>')
def download_venn_cutoff(user_id, filename):
    directory = os.path.join("venn_results_cutoff", user_id)
    if not os.path.exists(os.path.join(directory, filename)):
        return abort(404)
    return send_from_directory(directory, filename, as_attachment=True)
    
@app.route('/app/results/plots/<user_id>/<task_id>')
def view_plots(user_id, task_id):
    file_path = f'/app/results/{user_id}/{task_id}/data_for_react.json'
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)

        return jsonify(data)
    else:
        return jsonify({"error": "File not found"}), 404
    
@app.route('/app/results/summary/<user_id>/<task_id>')
def view_summary(user_id, task_id):
    file_path = f'/app/results/{user_id}/{task_id}/correlation_type_counts.json'

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            counts = json.load(f)

        return jsonify(counts)
    else:
        return jsonify({"error": "File not found"}), 404
    
@app.route('/app/results/summary/chord', methods=['POST'])
def view_chord():
    try:
        # Get the parameters from the request
        data = request.get_json()
        task_id = data.get('taskId')
        cutoff = data.get('cutoff')
        userId = data.get('userId')

        if not task_id or not cutoff:
            return jsonify({"error": "Missing task ID or cutoff"}), 400

        # Prepare the command to run the R script
        command = [
            'Rscript', 'chord_split.R', str(task_id), str(userId), str(cutoff)
        ]
        print(command)
        # Run the R script
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            print("STDERR from R script:", result.stderr)  # Print to server logs
            return jsonify({
                "error": "Error running chord.R",
                "stderr": result.stderr,
                "stdout": result.stdout
            }), 500
        

        # Construct path to result PDFs
        output_dir = os.path.join("results", userId, task_id)
        pdf_labels = ["Top 25", "Top 50", "Top 100", "Top 250"]
        pdfs = []

        for label in pdf_labels:
            filename = f"circlize_{label}.pdf"
            filepath = os.path.join(output_dir, filename)
            if os.path.isfile(filepath):
                pdfs.append({
                    "label": label,
                    "url": f"/results/{userId}/{task_id}/{filename}"
                })

        return jsonify({"pdfs": pdfs})
    except Exception as e:
        return jsonify({"error": "Server error", "message": str(e)}), 500

from flask import request, jsonify

@app.route('/app/compare', methods=['POST'])
def compare_results():
    try:
        # Parse the JSON data
        data = request.get_json()
        tasks = data.get('data', [])
        user_id = data.get('user_id', [])
        paths=[]
        if not tasks:
            return jsonify({"error": "No task data provided"}), 400

        conn = mysql.connect()
        cursor = conn.cursor()
    
        # Example: Loop through task list and log them
        for task in tasks:
            task_id = task.get('taskid')
            user_id = task.get('user_id')
            tp = task.get('time_point')
            result_path = f"/app/results/{user_id}/{task_id}"
            cursor.execute("SELECT GOI_path FROM mixomics_tasks WHERE id = %s", (task_id,))
            GOI_path = cursor.fetchone()[0]
            
            paths.append([result_path,GOI_path,tp])
            
        cursor.close()
        conn.close()
        print(f"Comparing Tasks path: {paths}")
        
        result = compare_mixomics(paths, user_id)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/app/compare_cutoff', methods=['POST'])
def compare_results_cutoff():
    try:
        # Parse the JSON data
        req_data = request.get_json()
        data = req_data.get('data', {})
        cutoffs = data.get('cutoffs', [])
        task_id = data.get('taskid', "")
        user_id = data.get('user_id',"")

        conn = mysql.connect()
        cursor = conn.cursor()
    
        result_path = f"/app/results/{user_id}/{task_id}"
        cursor.execute("SELECT GOI_path FROM mixomics_tasks WHERE id = %s", (task_id,))
        GOI_path = cursor.fetchone()[0]
            
        cursor.close()
        conn.close()
        
        result = compare_mixomics_cutoff(result_path, GOI_path, cutoffs, user_id)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 3300)))
    
