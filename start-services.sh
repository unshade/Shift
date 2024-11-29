#!/bin/bash

#Fix rights for kvm
sudo chown -R root:kvm /dev/kvm
# Start Xvfb
Xvfb :1 -screen 0 1280x800x16 &
sleep 2

# Start window manager
fluxbox &

# Start VNC server
x11vnc -forever -usepw -display :1 &

# Start noVNC
/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 6080 &

sdkmanager --install "system-images;android-33;google_apis;x86_64" &&     echo "no" | avdmanager create avd -n test_device -k "system-images;android-33;google_apis;x86_64" -d pixel

# Start the Android emulator
echo "Starting Android emulator..."
emulator -avd test_device -no-audio &

# Wait for emulator to be ready
echo "Waiting for emulator to boot..."
adb wait-for-device

#wget https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/fastdroid-vnc/fastdroid-vnc
#adb push fastdroid-vnc /data/
#adb shell chmod 755 /data/fastdroid-vnc
#adb shell /data/fastdroid-vnc

echo "Emulator started"

sh setup.sh
pip install -r requirements.txt

# Can't install it during the image?
appium driver install uiautomator2

# Start Appium server
echo "Starting Appium server..."
appium --allow-insecure chromedriver_autodownload &

#python3 immich.py immich_x86.apk

cd server || exit 0
pip install -r requirements.txt
cd ..

# Add an alias for "python3 /home/appium/server/manager.py run_servers $1 &"
alias run_servers="python3 /home/appium/server/manager.py run_servers"

# Keep container running
#tail -f /dev/null
