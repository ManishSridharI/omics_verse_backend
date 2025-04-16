# # app/mixomics_tasks.py

# from flask import jsonify, request
# import subprocess
# import numpy as np
# import pandas as pd
# import datetime
# import uuid
# from app.app import celery

# @celery.task(name="app.mixomics_tasks.run_r_script")
# def run_r_script(task_id, user_id, timepoint, timepoint_ids, mixomics_folder_path):
#     """Celery task to run the R script with appropriate parameters"""
#     try:
#         # Run R script with subprocess
#         cmd = ['Rscript', '/app/Mixomixs.R']
#         # , 
#         #        '--folder', mixomics_folder_path,
#         #        '--timepoint', str(timepoint),
#         #        '--timepoint-ids', timepoint_ids]
        
#         result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
#         # Connect to database
#         from app import mysql
#         conn = mysql.connect()
#         cursor = conn.cursor()
        
#         # Update task status in database
#         cursor.execute(
#             "UPDATE mixomics_tasks SET status = %s, completed_at = %s, result = %s WHERE id = %s",
#             ("completed", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result.stdout, task_id)
#         )
#         conn.commit()
#         conn.close()
        
#         return {"status": "success", "output": result.stdout}
    
#     except subprocess.CalledProcessError as e:
#         # Connect to database
#         from app import mysql
#         conn = mysql.connect()
#         cursor = conn.cursor()
        
#         # Update task status with error
#         cursor.execute(
#             "UPDATE mixomics_tasks SET status = %s, completed_at = %s, error = %s WHERE id = %s",
#             ("failed", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e.stderr, task_id)
#         )
#         conn.commit()
#         conn.close()
        
#         return {"status": "error", "error": e.stderr}

# def mixomics_start_task(mysql):
#     """Handle mixomics task creation and scheduling"""
#     data = request.json
#     user_id = data.get('user_id')
#     if not user_id:
#         return jsonify({'status': 'error', 'message': 'User ID is required'}), 400
    
#     mixomics_folder_paths = data.get('mixomics_folder_path')
#     timepoint_ids_list = data.get('timepoint_ids')
#     tps_list = data.get('tps')
    
#     if not (len(mixomics_folder_paths) == len(timepoint_ids_list) == len(tps_list)):
#         return jsonify({'status': 'error', 'message': 'Mismatched payload lengths'}), 400

#     task_ids = []
#     conn = mysql.connect()
#     cursor = conn.cursor()
    
#     try:
#         # Create tasks table if it doesn't exist
#         cursor.execute("""
#         CREATE TABLE IF NOT EXISTS mixomics_tasks (
#             id VARCHAR(36) PRIMARY KEY,
#             user_id VARCHAR(255) NOT NULL,
#             timepoint VARCHAR(255) NOT NULL,
#             timepoint_ids TEXT NOT NULL,
#             mixomics_folder_path TEXT NOT NULL,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             started_at TIMESTAMP NULL,
#             completed_at TIMESTAMP NULL,
#             status VARCHAR(20) DEFAULT 'pending',
#             result TEXT NULL,
#             error TEXT NULL
#         )
#         """)
#         conn.commit()
        
#         # Insert tasks and schedule them
#         for i in range(len(tps_list)):
#             task_id = str(uuid.uuid4())
            
#             # Insert task info into database
#             cursor.execute("""
#             INSERT INTO mixomics_tasks 
#             (id, user_id, timepoint, timepoint_ids, mixomics_folder_path, status, started_at) 
#             VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """, (
#                 task_id, 
#                 user_id, 
#                 tps_list[i], 
#                 timepoint_ids_list[i], 
#                 mixomics_folder_paths[i],
#                 "scheduled",
#                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             ))
            
#             # Schedule the task using Celery
#             run_r_script.delay(
#                 task_id,
#                 user_id,
#                 tps_list[i],
#                 timepoint_ids_list[i],
#                 mixomics_folder_paths[i]
#             )
            
#             task_ids.append(task_id)
        
#         conn.commit()
        
#         print(f"Tasks created and scheduled: {task_ids}")
#         return jsonify({
#             'status': 'success', 
#             'message': f'{len(task_ids)} tasks scheduled successfully',
#             'task_ids': task_ids
#         })
        
#     except Exception as e:
#         conn.rollback()
#         print(f"Error scheduling tasks: {str(e)}")
#         return jsonify({'status': 'error', 'message': f'Error scheduling tasks: {str(e)}'}), 500
    
#     finally:
#         cursor.close()
#         conn.close()