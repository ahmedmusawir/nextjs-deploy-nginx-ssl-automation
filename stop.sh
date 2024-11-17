#!/bin/bash

# Load configuration
source ../conf/app.conf

# Check if PM2 process with the specified name is running
if pm2 list | grep -q "$APP_NAME_PM2"; then
  # Stop the app if it's running
  pm2 stop "$APP_NAME_PM2"
  echo "PM2 process '$APP_NAME_PM2' stopped successfully."
else
  echo "PM2 process '$APP_NAME_PM2' is not running."
fi
