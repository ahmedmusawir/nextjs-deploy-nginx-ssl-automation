#!/bin/bash

# Load configuration
source ../conf/app.conf

echo $APP_ROOT
echo $APP_NAME_PM2
echo $PORT

# Check if PM2 process with the specified name exists
if pm2 list | grep -q $APP_NAME_PM2; then
  # Check if the process is in "online" status
  if pm2 list | grep $APP_NAME_PM2 | grep -q "online"; then
    echo "PM2 process '$APP_NAME_PM2' is already running."
  elif pm2 list | grep "$APP_NAME_PM2" | grep -q "stopped"; then
    # If the process exists but is "stopped," restart it
    pm2 restart $APP_NAME_PM2
    echo "PM2 process '$APP_NAME_PM2' was stopped. Restarting it."
  else
    echo "Unexpected status for PM2 process '$APP_NAME_PM2'. Check PM2 logs for details."
  fi
else
  # If the process doesn't exist, start it in the correct directory
  cd $APP_ROOT || exit 1  # Ensure we're in the correct directory before starting
  pm2 start npm --name $APP_NAME_PM2 -- start -- -p $PORT
  pm2 save
  echo "PM2 process '$APP_NAME_PM2' started successfully."
fi
