FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV SDK_VERSION="commandlinetools-linux-9477386_latest.zip" \
    ANDROID_HOME="/opt/android-sdk" \
    ANDROID_SDK_ROOT="/opt/android-sdk" \
    PATH="$PATH:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/opt/android-sdk/emulator" \
    DISPLAY=:1 \
    RESOLUTION=1280x800

# Install required packages including X11, VNC, and noVNC dependencies
RUN apt-get update && apt-get install -y \
    sudo \
    wget \
    default-jdk \
    vim \
    unzip \
    openjdk-11-jdk \
    git \
    python3 \
    python3-pip \
    python3-numpy \
    python3-venv \
    curl \
    adb \
    libqt5webkit5-dev \
    libgconf-2-4 \
    libnss3-dev \
    libxkbcommon-x11-0 \
    libpulse0 \
    libasound2 \
    x11-xserver-utils \
    libxdamage1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libpcap-dev \
    libxtst6 \
    libegl1 \
    zlib1g-dev \
    libgl1 \
    pulseaudio \
    socat \
    qemu-kvm \
    ca-certificates \
    gnupg \
    xvfb \
    x11vnc \
    xterm \
    fluxbox \
    novnc \
    websockify \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18.x
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Android SDK
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools && \
    cd ${ANDROID_HOME}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/${SDK_VERSION} && \
    unzip -q ${SDK_VERSION} && \
    mv cmdline-tools latest && \
    rm ${SDK_VERSION}

# Accept licenses before installing SDK packages
RUN mkdir -p ${ANDROID_HOME}/licenses && \
    echo "24333f8a63b6825ea9c5514f83c2829b004d1fee" > ${ANDROID_HOME}/licenses/android-sdk-license && \
    echo "84831b9409646a918e30573bab4c9c91346d8abd" > ${ANDROID_HOME}/licenses/android-sdk-preview-license

# Install Android SDK packages
RUN sdkmanager --update

RUN sdkmanager "platform-tools"
RUN sdkmanager "platforms;android-33"
RUN sdkmanager "build-tools;33.0.0"
RUN sdkmanager "system-images;android-33;google_apis;x86_64"
RUN sdkmanager "emulator"

# Fix missing emulator
#RUN sdkmanager --install "system-images;android-29;google_apis;x86" &&     echo "no" | avdmanager create avd -n test_device -k "system-images;android-29;google_apis;x86" -d pixel

# Create AVD
RUN echo "no" | avdmanager create avd \
    --name "test_device" \
    --package "system-images;android-33;google_apis;x86_64" \
    --device "pixel_4"

# Install Appium and UiAutomator2 driver
RUN npm install -g appium@2.12.1 && \
    appium driver install uiautomator2

RUN npm install @appium/doctor -g

# Create a non-root user
RUN useradd -m -d /home/appium -s /bin/bash appium && \
    usermod -aG sudo appium && \
    echo 'appium ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set VNC password
RUN mkdir -p /home/appium/.vnc && \
    x11vnc -storepasswd android /home/appium/.vnc/passwd

# Set up noVNC
RUN ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html

COPY appium/* /home/appium/

RUN mkdir -p /home/appium/server
COPY server/* /home/appium/server/

# Set working directory
WORKDIR /home/appium

#COPY ./server /home/appium/server
#RUN cd /home/appium/server && pip install -r requirements.txt

# Copy startup script
COPY start-services.sh /home/appium/
RUN chmod +x /home/appium/start-services.sh && \
    chown -R appium:appium /home/appium && \
    chown -R appium:appium /home/appium/.vnc && \
    chown -R appium:appium ${ANDROID_HOME}

# Set net admin capabilities for python
RUN setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3.10

# Add appium to groups
RUN usermod -aG render,kvm,sudo appium

USER appium

# Expose ports for Appium, VNC, and noVNC
EXPOSE 4723 5900 6080 8080

CMD ["/home/appium/start-services.sh"]
