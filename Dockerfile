# # Use the official lightweight Python image.
# # https://hub.docker.com/_/python
# FROM python:3.7-slim

# # Allow statements and log messages to immediately appear in the Knative logs
# ENV PYTHONUNBUFFERED True

# # Copy local code to the container image.
# ENV APP_HOME /app
# WORKDIR $APP_HOME
# COPY . ./

# # Install production dependencies.
# RUN pip install --no-cache-dir -r requirements.txt

# # Run the web service on container startup. Here we use the gunicorn
# # webserver, with one worker process and 8 threads.
# # For environments with multiple CPU cores, increase the number of workers
# # to be equal to the cores available.
# # Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
# #CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
# CMD ["gunicorn", "--bind", ":9900", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]

# Use the official lightweight Python image.
FROM python:3.9-slim

# Install dependencies for R (if required) and system packages for Python packages
RUN apt-get update && apt-get install -y \
    r-base \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set the Flask environment to development to enable auto-reload
ENV FLASK_ENV=development

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Add Redis for Celery
RUN apt-get update && apt-get install -y redis-server

# # Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the R package installation script into the container
COPY install_packages.R /install_packages.R

# Install R packages from the script
RUN Rscript /install_packages.R
RUN Rscript -e "library(mixOmics); packageVersion('mixOmics')"

#Use the flask command to run the app to take advantage of the reload mechanism
CMD ["flask", "run", "--host=0.0.0.0", "--port=3300"]



