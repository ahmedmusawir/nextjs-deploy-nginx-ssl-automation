#!/usr/bin/env python3

import os
from datetime import datetime
import subprocess
import sys

# Define paths
config_path = "../conf/app.conf"
logs_dir = "../logs"
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
log_file = f"{logs_dir}/next-deploy-{timestamp}.log"

# ----------------------------------------------------------------
# Part 1: Configuration and .env.local check
# ----------------------------------------------------------------

ready = input("Do you have your .env.local ready? (y/n): ")
if ready.lower() != "y":
    print("Please prepare your .env.local file before deployment.")
    sys.exit(0)

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

config["TIMESTAMP"] = timestamp
config["APP_ROOT"] = os.path.join(config["DEPLOYMENT_ROOT"], config["APP_NAME_PM2"], config["APP_NAME_GITHUB"])

print("\nLoaded Configuration:")
max_label_length = max(len(key) for key in config.keys())
for key, value in config.items():
    print(f"{key.upper():<{max_label_length}}: {value}")

verify = input("\nIs this configuration correct? (y/n): ")
if verify.lower() != "y":
    print("Please update your configuration in app.conf.")
    sys.exit(0)

os.makedirs(logs_dir, exist_ok=True)
with open(log_file, "w") as log:
    log.write(f"Deployment log - {timestamp}\n")
    log.write("Configuration Loaded:\n")
    for key, value in config.items():
        log.write(f"{key}: {value}\n")
    log.write("Deployment process initialized.\n")

print(f"\nConfiguration logged to: {log_file}")
print("Script completed Part 1 successfully.")

# ----------------------------------------------------------------
# Part 2: Shutting down if a previous app is running
# ----------------------------------------------------------------
shutdown_confirm = input("\nA previous instance of the app may be running. Proceed with shutdown and removal? (y/n): ")
if shutdown_confirm.lower() != "y":
    print("Shutdown and removal process skipped by user.")
else:
    try:
        # Check if the PM2 process is running
        check_process = subprocess.run(["pm2", "list"], capture_output=True, text=True)
        if config["APP_NAME_PM2"] in check_process.stdout:
            print(f"PM2 process '{config['APP_NAME_PM2']}' is currently running. Stopping and removing it.")
            
            # Stop the process if found
            stop_process = subprocess.run(["pm2", "stop", config["APP_NAME_PM2"]], capture_output=True, text=True)
            if stop_process.returncode == 0:
                print(f"PM2 process '{config['APP_NAME_PM2']}' stopped successfully.")
            else:
                print(f"Warning: PM2 process '{config['APP_NAME_PM2']}' not running or already stopped.")
            
            # Delete the process
            delete_process = subprocess.run(["pm2", "delete", config["APP_NAME_PM2"]], capture_output=True, text=True)
            if delete_process.returncode == 0:
                print(f"PM2 process '{config['APP_NAME_PM2']}' removed successfully.")
            else:
                print(f"Warning: PM2 process '{config['APP_NAME_PM2']}' could not be found or was already removed.")
            
            with open(log_file, "a") as log:
                log.write(f"PM2 process '{config['APP_NAME_PM2']}' stopped and removed successfully if running.\n")

        else:
            print(f"PM2 process '{config['APP_NAME_PM2']}' not found in the PM2 list; skipping stop and removal.")
            with open(log_file, "a") as log:
                log.write(f"PM2 process '{config['APP_NAME_PM2']}' not found; no action taken.\n")

    except subprocess.CalledProcessError as e:
        error_message = f"Error during PM2 shutdown process: {e}"
        with open(log_file, "a") as log:
            log.write(f"{error_message}\n")
        print(error_message)
        sys.exit(1)

# ----------------------------------------------------------------
# Part 3: Backing up the previously deployed code
# ----------------------------------------------------------------

# Confirm before proceeding with the backup
backup_confirm = input("\nProceed with creating a backup of the existing deployment? (y/n): ")
if backup_confirm.lower() != "y":
    print("Backup process skipped by user.")
else:
    # Check if the application folder exists to back up
    if os.path.exists(config["APP_ROOT"]):
        # Define backup file name with timestamp
        backup_filename = f"BK-{config['APP_NAME_GITHUB']}-{config['TIMESTAMP']}.tar.gz"
        backup_filepath = os.path.join(config["BACKUP_DIR"], backup_filename)
        staging_dir = os.path.join(config["DEPLOYMENT_ROOT"], "backup_staging")

        try:
            # Create a staging directory for the backup
            if not os.path.exists(staging_dir):
                os.makedirs(staging_dir)

            # Copy the app folder to the staging area without node_modules
            print("Copying application to staging directory without node_modules...")
            subprocess.run(["rsync", "-a", "--exclude=node_modules", config["APP_ROOT"] + "/", staging_dir], check=True)

            # Create the compressed backup from the staging directory
            print("Creating backup file...")
            subprocess.run(["tar", "-czf", backup_filepath, "-C", config["DEPLOYMENT_ROOT"], "backup_staging"], check=True)

            # Remove the staging directory after backup
            subprocess.run(["rm", "-rf", staging_dir], check=True)

            # Log and print confirmation of backup completion
            with open(log_file, "a") as log:
                log.write(f"Backup created successfully: {backup_filepath}\n")
            print(f"Backup created successfully: {backup_filepath}")

            # Display contents of backup directory for verification
            print("Current backup files in the backup directory:")
            subprocess.run(["ls", "-ltr", config["BACKUP_DIR"]])

        except subprocess.CalledProcessError as e:
            error_message = f"Error during backup: {e}"
            with open(log_file, "a") as log:
                log.write(f"{error_message}\n")
            print(error_message)
            sys.exit(1)

    else:
        print(f"No application folder found for backup; skipping backup.")
        with open(log_file, "a") as log:
            log.write("No application folder found for backup; skipping backup.\n")

# ----------------------------------------------------------------
# Part 4: Clone Repository
# ----------------------------------------------------------------
clone_confirm = input("\nReady to clone the repository? (y/n): ")
if clone_confirm.lower() != "y":
    print("Repository cloning aborted by the user.")
    sys.exit(0)

if os.path.exists(config["APP_ROOT"]):
    overwrite_confirm = input(f"Directory {config['APP_ROOT']} already exists. Delete and re-clone? (y/n): ")
    if overwrite_confirm.lower() == "y":
        print(f"Removing existing directory at {config['APP_ROOT']}.")
        subprocess.run(["rm", "-rf", config["APP_ROOT"]], check=True)
    else:
        print("Cloning skipped because directory exists and user opted not to delete.")
        sys.exit(0)

print(f"Cloning repository from {config['REPO_URL']} into {config['APP_ROOT']}.")
clone_command = ["git", "clone", config["REPO_URL"], config["APP_ROOT"]]
try:
    subprocess.run(clone_command, check=True)
    with open(log_file, "a") as log:
        log.write("Repository cloned successfully.\n")
    print("Repository cloned successfully.")
except subprocess.CalledProcessError as e:
    error_message = f"Error cloning repository: {e}"
    with open(log_file, "a") as log:
        log.write(f"{error_message}\n")
    print(error_message)
    sys.exit(1)

print("\nRepository clone step completed and logged.")

# ----------------------------------------------------------------
# Part 5: npm install, .env.local copy and npm build
# ----------------------------------------------------------------
# npm install
install_confirm = input("\nProceed with npm install? (y/n): ")
if install_confirm.lower() != "y":
    print("npm install skipped by user.")
else:
    try:
        subprocess.run(["npm", "install"], cwd=config["APP_ROOT"], check=True)
        with open(log_file, "a") as log:
            log.write("npm install completed successfully.\n")
        print("npm install completed.")
    except subprocess.CalledProcessError as e:
        error_message = f"Error during npm install: {e}"
        with open(log_file, "a") as log:
            log.write(f"{error_message}\n")
        print(error_message)
        sys.exit(1)

# Copy .env.local
env_path = "../.env.local"
copy_confirm = input("\nProceed with copying .env.local to app root? (y/n): ")
if copy_confirm.lower() != "y":
    print(".env.local copy skipped by user.")
elif not os.path.exists(env_path):
    error_message = f".env.local file not found at {env_path}."
    with open(log_file, "a") as log:
        log.write(f"{error_message}\n")
    print(error_message)
    sys.exit(1)
else:
    try:
        subprocess.run(["cp", env_path, os.path.join(config["APP_ROOT"], ".env.local")], check=True)
        with open(log_file, "a") as log:
            log.write(".env.local copied to app root.\n")
        print(".env.local copied to app root.")
    except subprocess.CalledProcessError as e:
        error_message = f"Error copying .env.local: {e}"
        with open(log_file, "a") as log:
            log.write(f"{error_message}\n")
        print(error_message)
        sys.exit(1)

# npm run build
build_confirm = input("\nProceed with npm run build? (y/n): ")
if build_confirm.lower() != "y":
    print("npm build skipped by user.")
else:
    try:
        subprocess.run(["npm", "run", "build"], cwd=config["APP_ROOT"], check=True)
        with open(log_file, "a") as log:
            log.write("npm build completed successfully.\n")
        print("npm build completed.")
    except subprocess.CalledProcessError as e:
        error_message = f"Error during npm build: {e}"
        with open(log_file, "a") as log:
            log.write(f"{error_message}\n")
        print(error_message)
        sys.exit(1)

# ----------------------------------------------------------------
# Part 6: Starting the app as a pm2 process
# ----------------------------------------------------------------        

# Confirm before proceeding with PM2 start
start_confirm = input("\nProceed with PM2 deployment (start only) directly? (y/n): ")
if start_confirm.lower() != "y":
    print("PM2 deployment skipped by user.")
else:
    try:
        # Start the app with PM2
        subprocess.run(
            ["pm2", "start", "npm", "--name", config["APP_NAME_PM2"], "--", "start", "--", "-p", config["PORT"]],
            cwd=config["APP_ROOT"],
            check=True
        )
        
        with open(log_file, "a") as log:
            log.write("PM2 start executed successfully.\n")
        print("PM2 deployment executed successfully.")

    except subprocess.CalledProcessError as e:
        error_message = f"Error during PM2 deployment process: {e}"
        with open(log_file, "a") as log:
            log.write(f"{error_message}\n")
        print(error_message)
        sys.exit(1)


print("\nDeployment process completed and logged.")
