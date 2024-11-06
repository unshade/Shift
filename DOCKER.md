# Android Docker image

The image is based on Ubuntu 22.04 and installs the necessary tools to run Android applications.

## Notes

- The image is only working on Linux x86_64.
- The image is only working on a machine with KVM support.
- There is a VNC server running on port 5900 and a noVNC server running on port 6080 which you can access from your
  browser at `http://localhost:6080`. Password for VNC is `android`.

## Known or previous issues

- The Android device might not be created for some reason. In this case you have to connect to the container and run the
  following command:

```bash
sdkmanager --install "system-images;android-29;google_apis;x86" && echo "no" | avdmanager create avd -n test_device -k "system-images;android-29;google_apis;x86" -d pixel
```

- If the permissions on /dev/kvm are not set correctly, you can run the following debug command inside the container:

```bash
chmod 777 /dev/kvm
```

To connect to the container as root, use the parameter `-u 0`.

## Using the image

To build the image, you can use the following command:

```bash
docker build -t android-image .
```

To run the image, you can use the following command:

```bash
docker run -it --device /dev/kvm --privileged -p 5900:5900 -p 6080:6080 android-image
```