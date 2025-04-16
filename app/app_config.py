# # -*- coding: utf-8 -*-

# from flask import Flask
# from flask_cors import CORS  # Import CORS
# import mysql.connector
# from flaskext.mysql import MySQL
# from flask_bcrypt import Bcrypt
# from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# from celery_config import make_celery

# # Define allowed hosts
# ALLOWED_HOSTS = [
#     'http://trbil.missouri.edu', 
#     'http://digbio-soykb2.rnet.missouri.edu:3030/',
#     'http://digbio-soykb2.rnet.missouri.edu:3030',
#     'http://digbio-soykb2.rnet.missouri.edu',
#     'http://digbio-devel.missouri.edu:3030/',
#     'http://digbio-devel.missouri.edu:3030',
#     'http://digbio-devel.missouri.edu'
# ]

# app = Flask(__name__)
# CORS(app, origins=ALLOWED_HOSTS)

# mysql = MySQL()
# bcrypt = Bcrypt()
# login_manager = LoginManager()
# login_manager.init_app(app)

# app.config['MYSQL_DATABASE_USER'] = 'KBCommons'
# app.config['MYSQL_DATABASE_PASSWORD'] = 'KsdbsaKNm55d3QtvtX44nSzS_'
# app.config['MYSQL_DATABASE_DB'] = 'Omics_verse'
# app.config['MYSQL_DATABASE_HOST'] = 'digbio-db1.rnet.missouri.edu'
# app.config['SECRET_KEY'] = 'supersecretkey'

# mysql.init_app(app)

# celery = make_celery(app)