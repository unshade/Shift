#!/bin/bash
 echo "no" | avdmanager create avd -f -n emu -b x86_64 -k "system-images;android-34;google_apis;x86_64" -d pixel_5

sudo chown 1300:1301 /dev/kvm

# Start the display screen (Xvfb)
DISPLAY=:1
SCREEN_NUMBER=0
SCREEN_WIDTH=1920
SCREEN_HEIGHT=1080
SCREEN_DEPTH=24
/usr/bin/Xvfb $DISPLAY -screen $SCREEN_NUMBER ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x$SCREEN_DEPTH &

# Start the window manager (Openbox)
/usr/bin/openbox-session &

# Start the VNC server
/usr/bin/x11vnc -display $DISPLAY -forever -shared -nopw &

# Start the VNC web interface (noVNC)
WEB_VNC=true
VNC_PORT=5900
WEB_VNC_PORT=6080
if [ "$WEB_VNC" = true ]; then
    /opt/noVNC/utils/novnc_proxy --vnc localhost:$VNC_PORT --listen 0.0.0.0:$WEB_VNC_PORT &
else
    echo "Environment variable WEB_VNC is not set. VNC Web will not start."
fi

emulator -avd emu -no-audio -gpu swiftshader_indirect -no-snapshot -no-boot-anim -accel on -no-snapshot-save -no-snapshot-load -writable-system -verbose -wipe-data &
echo "Trying to start emulator"
adb wait-for-device
echo "Finished waiting for device"

A=$(adb shell getprop sys.boot_completed | tr -d '\r')
while [ "$A" != "1" ]; do
    echo "Waiting for emulator to boot..."
    sleep 2
    A=$(adb shell getprop sys.boot_completed | tr -d '\r')
done

adb shell cmd bluetooth_manager disable

adb root

adb remount

adb reboot

adb wait-for-device

A=$(adb shell getprop sys.boot_completed | tr -d '\r')
while [ "$A" != "1" ]; do
    echo "Waiting for emulator to boot..."
    sleep 2
    A=$(adb shell getprop sys.boot_completed | tr -d '\r')
done

adb root

adb remount

echo "Emulator booted"

/usr/bin/appium &
while ! nc -z localhost 4723; do
    echo "Waiting for Appium to start..."
    sleep 2
done
echo "Appium started"

export STAGE="CI"
echo "Starting the server (logs are saved in /home/androidusr/server/logs.txt)"
cd /home/androidusr/server
sudo -E /home/androidusr/venv/bin/python /home/androidusr/server/manager.py run_servers immich >> /home/androidusr/server/logs.txt 2>&1 &
adb push /etc/hosts /etc/hosts
adb push /etc/hosts /system/etc/hosts
echo "Starting appium automation"
cd /home/androidusr/appium
/home/androidusr/venv/bin/python /home/androidusr/appium/immich.py /home/androidusr/appium/immich_x86.apk
