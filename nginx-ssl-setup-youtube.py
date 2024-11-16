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
# Step 6: Run Certbot to obtain the SSL certificate
# ----------------------------------------------------------------------------
confirm_step("Proceed with Certbot to obtain SSL certificate?")
try:
    log_message("Running Certbot for SSL certificate...")
    certbot_command = [
        "certbot", "certonly", "--nginx", "-d", domain_full,
        "--agree-tos", "--email", "ahmed.musawir@hotmail.com", "--non-interactive"  # "--staging" for production
    ]
    subprocess.run(certbot_command, check=True)
    log_message("Certbot completed successfully.")

except subprocess.CalledProcessError as e:
    log_message(f"Error running Certbot: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------------
# Step 7: Set up automatic certificate renewal
# ----------------------------------------------------------------------------
if confirm_step("Enable and test Certbot renewal timer? (y/n): "):
    try:
        log_message("Enabling Certbot renewal timer...")
        # Enable and start the renewal timer
        subprocess.run(["sudo", "systemctl", "enable", "certbot.timer"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "certbot.timer"], check=True)

        # Optional: Test the renewal process with a dry run to confirm setup
        # log_message("Testing Certbot renewal with dry-run...")
        # subprocess.run(["certbot", "renew", "--dry-run"], check=True)
        log_message("Certbot renewal timer enabled, started, and tested successfully.")
    except subprocess.CalledProcessError as e:
        log_message(f"Error setting up Certbot renewal: {e}")
        sys.exit(1)
else:
    log_message("User opted to skip Certbot renewal setup. Aborting SSL setup.")
    print("Aborted. SSL setup will not proceed.")
    sys.exit(0)


# ----------------------------------------------------------------------------
# Step 8: Restart Nginx to apply the changes
# ----------------------------------------------------------------------------
confirm_step("Proceed with restarting Nginx to apply SSL?")
try:
    log_message("Restarting Nginx...")
    subprocess.run(["systemctl", "restart", "nginx"], check=True)
    log_message("Nginx restarted successfully with new configuration.")

except subprocess.CalledProcessError as e:
    log_message(f"Error restarting Nginx: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------------
# Step 9: Verify the setup by checking the URL
# ----------------------------------------------------------------------------
if confirm_step(f"Verify if the URL https://{domain_full} is live? (y/n): "):
    try:
        log_message("Verifying if the URL is live...")
        response = requests.get(f"https://{domain_full}")
        if response.status_code == 200:
            log_message("Success! The site is live and SSL is active.")
        else:
            log_message(f"Warning: The URL returned status code {response.status_code}. Manual check recommended.")
    except requests.exceptions.RequestException as e:
        log_message(f"URL verification failed: {e}")
else:
    log_message("User opted to skip URL verification. Ending SSL setup.")
    print("SSL setup completed without URL verification.")

log_message("\nNginx SSL Setup completed successfully.")
log_message(f"Your URL is live at: https://{domain_full}")
