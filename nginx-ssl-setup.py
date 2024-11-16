#!/usr/bin/env python3

import os
import subprocess
import sys
import time
from datetime import datetime
import requests

# Define paths
config_path = "../conf/app.conf"
logs_dir = "../logs"
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
log_file = f"{logs_dir}/nginx-ssl-{timestamp}.log"

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

# Define important variables from configuration
domain_full = f"{config['SUBDOMAIN']}.{config['DOMAIN']}"
template_path = config.get("SSL_TEMPLATE_PATH", "../nginx-ssl.conf")
nginx_available_path = os.path.join(config["NGINX_AVAILABLE_DIR"], domain_full)
nginx_enabled_path = os.path.join(config["NGINX_ENABLED_DIR"], domain_full)

# Initialize log file
os.makedirs(logs_dir, exist_ok=True)
with open(log_file, "w") as log:
    log.write(f"Nginx SSL Setup Log - {timestamp}\n\n")

# Helper function for logging
def log_message(message):
    print(message)
    with open(log_file, "a") as log:
        log.write(f"{message}\n")

# Utility function for confirmation with proper handling
def confirm_step(prompt):
    # Display the prompt in a more visually separated format
    print("\n" + "#" * 76)
    print(f"# {prompt}")
    print("#" * 76)

    while True:
        response = input("Answer (y/n): ").strip().lower()
        if response == "y":
            return True
        elif response == "n":
            print("\nUser opted to skip this step. Aborting SSL setup.")
            log_message("User opted to skip this step. Aborting SSL setup.")
            sys.exit(0)
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

# ----------------------------------------------------------------------------
# Step 1: Confirm DNS setup
# ----------------------------------------------------------------------------
confirm_step("Have you created the subdomain A record in Digital Ocean DNS? (y/n): ")

# ----------------------------------------------------------------------------
# Step 2: Configuration Verification
# ----------------------------------------------------------------------------
log_message("Loaded Configuration for Verification:")
for key, value in config.items():
    log_message(f"{key}: {value}")
confirm_step("Is this configuration correct? (y/n): ")

# ----------------------------------------------------------------------------
# Step 3: Replace placeholders in the template to create the Nginx config
# ----------------------------------------------------------------------------
if confirm_step("Replace placeholders in SSL template and create Nginx config file? (y/n): "):
    try:
        log_message("Reading and replacing placeholders in the SSL template...")
        with open(template_path, "r") as template_file:
            template_content = template_file.read()
        nginx_config_content = template_content.replace("SUBDOMAIN.DOMAIN", domain_full).replace("PORT", config["PORT"])
        log_message("Placeholders replaced successfully.")
    except FileNotFoundError:
        log_message(f"Error: SSL template file not found at {template_path}")
        sys.exit(1)
else:
    log_message("User opted to skip replacing placeholders. Aborting SSL setup.")
    print("Aborted. SSL setup will not proceed.")
    sys.exit(0)

# ----------------------------------------------------------------------------
# Step 4: Write config to Nginx sites-available
# ----------------------------------------------------------------------------
if os.path.exists(nginx_available_path):
    overwrite_confirm = confirm_step(f"Configuration file {nginx_available_path} already exists. Overwrite? (y/n): ")
    if not overwrite_confirm:
        log_message("User opted to skip overwriting existing Nginx configuration. Aborting SSL setup.")
        print("Aborted. SSL setup will not proceed.")
        sys.exit(0)

# Proceed with writing the configuration
if confirm_step(f"Write Nginx configuration to {nginx_available_path}? (y/n): "):
    try:
        log_message(f"Writing configuration to {nginx_available_path}...")
        with open(nginx_available_path, "w") as nginx_conf:
            nginx_conf.write(nginx_config_content)
        log_message(f"Configuration written to {nginx_available_path}.")
    except Exception as e:
        log_message(f"Error writing Nginx config: {e}")
        sys.exit(1)
else:
    log_message("User opted to skip writing Nginx configuration. Aborting SSL setup.")
    print("Aborted. SSL setup will not proceed.")
    sys.exit(0)

# ----------------------------------------------------------------------------
# Step 5: Create symlink in Nginx sites-enabled
# ----------------------------------------------------------------------------
if os.path.exists(nginx_enabled_path):
    remove_confirm = confirm_step(f"Symlink {nginx_enabled_path} already exists. Remove and recreate? (y/n): ")
    if remove_confirm:
        try:
            subprocess.run(["rm", nginx_enabled_path], check=True)
            log_message(f"Existing symlink {nginx_enabled_path} removed.")
        except subprocess.CalledProcessError as e:
            log_message(f"Error removing existing symlink: {e}")
            sys.exit(1)
    else:
        log_message("User opted to skip removing existing symlink. Aborting SSL setup.")
        print("Aborted. SSL setup will not proceed.")
        sys.exit(0)

# Create the new symlink
if confirm_step(f"Create symlink for Nginx config in sites-enabled? (y/n): "):
    try:
        log_message("Creating symlink in sites-enabled...")
        subprocess.run(["ln", "-s", nginx_available_path, nginx_enabled_path], check=True)
        log_message(f"Symlink created at {nginx_enabled_path}.")
    except subprocess.CalledProcessError as e:
        log_message(f"Error creating symlink: {e}")
        sys.exit(1)
else:
    log_message("User opted to skip symlink creation. Aborting SSL setup.")
    print("Aborted. SSL setup will not proceed.")
    sys.exit(0)

# ----------------------------------------------------------------------------
# Step 6: Display manual commands for SSL certificate setup
# ----------------------------------------------------------------------------
confirm_step("Proceed with manual SSL setup instructions for Certbot and Nginx restart?")

# Display instructions for the admin to follow manually
log_message("Manual steps required to complete SSL setup. Follow the instructions below:")
print("\n# ----------------------------------------------------------------------------")
print("# Step-by-Step Commands for Completing SSL Setup")
print("# ----------------------------------------------------------------------------\n")

# Display the commands for the admin to copy and run manually
manual_commands = f"""
# Test Nginx configuration to ensure it’s valid
nginx -t

# Run Certbot to obtain and configure the SSL certificate for the domain
sudo certbot --nginx -d {domain_full}

# Reload Nginx to apply the changes once Certbot has completed successfully
sudo systemctl reload nginx

# Optional: Check the status of the Certbot renewal timer to confirm automatic renewal setup
sudo systemctl status certbot.timer

# Optional: Test Certbot renewal process with a dry run to ensure it will work smoothly at renewal time
sudo certbot renew --dry-run
"""

print(manual_commands)
log_message(manual_commands)

print("\n# ----------------------------------------------------------------------------")
print("# SSL Setup Steps Completed Up to Automated Point")
print("# Copy and paste the above commands in the terminal to finalize the setup.")
print("# ----------------------------------------------------------------------------\n")

# Log message to indicate completion up to this step
log_message("SSL setup steps up to this point have been completed. Manual steps are required to finalize.")
log_message("Your SSL setup is almost complete! Follow the above commands to enable HTTPS.")

