# -------------------------------------------------------------------
# Dockerfile for the student-profile microservice
# Purpose: Build a small Python image that waits for the Postgres DB
#          then runs the Flask app (app.py).
#
# Notes:
# - This image uses python:3.11-slim (Debian-slim base) so we can use apt.
# - We install a minimal "netcat" tool to let the wait-for-it script
#   test whether the DB port is open before starting the app.
# - We copy requirements first to leverage Docker layer caching:
#   if only application code changes, pip install will be reused.
# -------------------------------------------------------------------

# Use the official Python slim image as the base.
# 'slim' keeps the image smaller than the full Debian image of Python but still
# provides apt-get for installing small utilities.
FROM python:3.11-slim

# Set the working directory inside the container. All subsequent
# commands (COPY, RUN, CMD...) are relative to /app.
WORKDIR /app

# Install netcat so our "wait-for-it.sh" script can check if Postgres is ready.
# -- We run apt-get update and install in one RUN to ensure package indexes
#   are fresh and to create a single image layer.
# -- --no-install-recommends reduces extra packages to keep the image small.
# -- We remove /var/lib/apt/lists/* afterwards to reduce image size.
# Note: on some systems the package name might be netcat-openbsd instead of netcat-traditional.
RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

# Copy the Python dependency manifest first.
# Why first? Docker caches layers: if requirements.txt hasn't changed,
# the next build will reuse this layer and skip re-installing packages.
COPY requirements.txt .

# Install Python dependencies using pip. --no-cache-dir keeps pip from
# caching wheels inside the image (saves space).
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code into the image.
# This includes: app.py, wait-for-it.sh, and any other project files.
COPY . .

# Make sure our helper script is executable.
# wait-for-it.sh will be used to wait for the DB to accept connections.
# (Ensure wait-for-it.sh has a proper shebang like #!/usr/bin/env bash)
RUN chmod +x wait-for-it.sh

# Command to run when the container starts.
# - We use the exec-form (JSON array) so the process receives signals directly.
# - The wait-for-it script blocks until student-db:5432 is reachable,
#   then runs the Python app (this prevents the app starting before DB is ready).
CMD ["./wait-for-it.sh", "student-db", "5432", "python", "app.py"]
