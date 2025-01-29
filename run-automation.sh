# Copy files from the CI
cp -r * /home/androidusr/appium
cp -r server /home/androidusr

# Export needed environment variables
export STAGE="CI"
export PYTHONUNBUFFERED=1 # Otherwise some logs are not printed in the background

# Run initial setup of the container (including setting up the display, the emulator, VNC)
/home/androidusr/run.sh

echo "Starting the server (logs are saved in /home/androidusr/server/logs.txt)"
cd /home/androidusr/server
# Setup hosts
(sudo -E /home/androidusr/venv/bin/python /home/androidusr/server/manager.py update_hosts $SCHEMA_NAME)
# Run the server in the background
(sudo -E /home/androidusr/venv/bin/python /home/androidusr/server/manager.py run_servers $SCHEMA_NAME) &> /home/androidusr/server/logs.txt &

# Prepare device hosts
adb remount
adb push /etc/hosts /etc/hosts
adb push /etc/hosts /system/etc/hosts

# Prepare redirection between host and emulator
adb reverse tcp:80 tcp:80

# Server might take some time to appear so waiting for it
echo "Waiting for the server to start"
sleep 15

# Ready for the automation
echo "Starting appium automation"
/home/androidusr/venv/bin/python /home/androidusr/appium/$APPIUM_SCRIPT_FILE /home/androidusr/appium/$APP_FILE
echo "Finished appium automation"