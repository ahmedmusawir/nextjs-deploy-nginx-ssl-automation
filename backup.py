#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
import sys

# Define paths
config_path = "../app.conf"
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
log_file = f"../logs/backup-log-{timestamp}.log"

# Load configuration
config = {}
with open(config_path, "r") as conf_file:
    for line in conf_file:
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"')
            except ValueError:
                print(f"Invalid line in config file: {line}")
                sys.exit(1)

# Define paths based on configuration
app_folder = os.path.join("..", config["APP_NAME_GITHUB"])
backup_folder = "../backup"
backup_file = f"{backup_folder}/BK-{config['APP_NAME_GITHUB']}-{timestamp}.tar.gz"

# Verify that the app folder exists
if not os.path.isdir(app_folder):
    print(f"Error: The application folder '{app_folder}' does not exist.")
    sys.exit(1)

# Log the start of the backup
with open(log_file, "w") as log:
    log.write(f"Backup log - {timestamp}\n")
    log.write(f"Backing up '{app_folder}' to '{backup_file}'\n")

# Remove node_modules to save space
node_modules_path = os.path.join(app_folder, "node_modules")
if os.path.isdir(node_modules_path):
    print(f"Removing 'node_modules' from '{app_folder}' to reduce backup size.")
    subprocess.run(["rm", "-rf", node_modules_path], check=True)

# Create a compressed archive of the app folder
try:
    print(f"Creating backup '{backup_file}'...")
    subprocess.run(["tar", "-czf", backup_file, "-C", "..", config["APP_NAME_GITHUB"]], check=True)
    with open(log_file, "a") as log:
        log.write(f"Backup created successfully at '{backup_file}'.\n")
    print(f"Backup created successfully: {backup_file}")
except subprocess.CalledProcessError as e:
    error_message = f"Error creating backup: {e}"
    with open(log_file, "a") as log:
        log.write(f"{error_message}\n")
    print(error_message)
    sys.exit(1)

# List contents of backup directory
print("\nCurrent backups:")
subprocess.run(["ls", "-ltr", backup_folder])

# Log completion
with open(log_file, "a") as log:
    log.write("Backup operation completed successfully.\n")

print(f"\nBackup operation logged to: {log_file}")
