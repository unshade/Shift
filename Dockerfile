FROM appium/appium:v2.11.4-p0

USER root

#================
# Basic Packages
#----------------
# dnsmasq
#   DNS server
# socat
#   Port forwarder
# supervisor
#   Process manager
#================
RUN apt-get -qqy update && apt-get -qqy install --no-install-recommends \
    dnsmasq \
    socat \
    supervisor \
    netcat \
 && apt autoremove -y \
 && apt clean all \
 && rm -rf /var/lib/apt/lists/*

#==================
# Configure Python
#==================
RUN apt-get -qqy update && \
    apt-get -qqy --no-install-recommends install \
    python3-pip \
    python3-numpy \
    python3-venv \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

#===============
# Expose Ports
#---------------
# 4723
#   Appium port
# 5554
#   Emulator port
# 5555
#   ADB connection port
#===============
EXPOSE 4723 5554 5555

#==================
# Android Packages
#==================
ARG EMULATOR_ANDROID_VERSION=14.0
ARG EMULATOR_API_LEVEL=34
ENV EMULATOR_ANDROID_VERSION=${EMULATOR_ANDROID_VERSION} \
    EMULATOR_API_LEVEL=${EMULATOR_API_LEVEL} \
    EMULATOR_SYS_IMG=x86_64 \
    EMULATOR_IMG_TYPE=google_apis \
    EMULATOR_BROWSER=chrome
ENV PATH=${PATH}:${ANDROID_HOME}/build-tools
RUN yes | sdkmanager --licenses \
 && sdkmanager --install \
    "platforms;android-${EMULATOR_API_LEVEL}" \
    "system-images;android-${EMULATOR_API_LEVEL};${EMULATOR_IMG_TYPE};${EMULATOR_SYS_IMG}" \
    "emulator" \
 && ln -sf ${ANDROID_HOME}/emulator/emulator /usr/bin/emulator

ENV PATH="${ANDROID_HOME}/tools/bin:${PATH}"

#=============
# UI Packages
#-------------
# ffmpeg
#   Video recorder
# feh
#   Screen background
# libxcomposite-dev
#   Window System for Emulator
# menu
#   Debian menu
# openbox
#   Windows manager
# x11vnc
#   VNC server
# xterm
#   Terminal emulator
#==================
RUN apt-get -qqy update && apt-get -qqy install --no-install-recommends \
    ffmpeg \
    feh \
    libxcomposite-dev \
    menu \
    openbox \
    x11vnc \
    xterm \
 && apt autoremove -y \
 && apt clean all \
 && rm -rf /var/lib/apt/lists/*

#=======
# noVNC
#=======
ENV NOVNC_VERSION="1.4.0" \
    WEBSOCKIFY_VERSION="0.11.0" \
    OPT_PATH="/opt"
RUN  wget -nv -O noVNC.zip "https://github.com/novnc/noVNC/archive/refs/tags/v${NOVNC_VERSION}.zip" \
 && unzip -x noVNC.zip \
 && rm noVNC.zip  \
 && mv noVNC-${NOVNC_VERSION} ${OPT_PATH}/noVNC \
 && wget -nv -O websockify.zip "https://github.com/novnc/websockify/archive/refs/tags/v${WEBSOCKIFY_VERSION}.zip" \
 && unzip -x websockify.zip \
 && mv websockify-${WEBSOCKIFY_VERSION} ${OPT_PATH}/noVNC/utils/websockify \
 && rm websockify.zip \
 && ln ${OPT_PATH}/noVNC/vnc.html ${OPT_PATH}/noVNC/index.html

ENV DISPLAY=:0 \
    SCREEN_NUMBER=0 \
    SCREEN_WIDTH=1600 \
    SCREEN_HEIGHT=900 \
    SCREEN_DEPTH=24+32 \
    VNC_PORT=5900 \
    WEB_VNC_PORT=6080

EXPOSE 5900 6080

#==========
# Copy app
#==========
# Base

ENV WORK_PATH="/home/androidusr"

COPY run.sh ${WORK_PATH}/
RUN chmod 760 ${WORK_PATH}/run.sh

COPY run-automation.sh ${WORK_PATH}/
RUN chmod 760 ${WORK_PATH}/run-automation.sh

# Appium
COPY appium ${WORK_PATH}/appium 
COPY server ${WORK_PATH}/server
RUN chown -R 1300:1301 ${WORK_PATH}/appium ${WORK_PATH}/server ${WORK_PATH}/run.sh ${WORK_PATH}/run-automation.sh

RUN python3 -m venv ${WORK_PATH}/venv 
RUN ${WORK_PATH}/venv/bin/pip install -r ${WORK_PATH}/appium/requirements.txt && \
${WORK_PATH}/venv/bin/pip install -r ${WORK_PATH}/server/requirements.txt

#==================
# Use created user
#==================
USER 1300:1301
ENV LOG_PATH=${WORK_PATH}/logs \
    WEB_LOG_PORT=9000
EXPOSE 9000
RUN mkdir -p ${LOG_PATH}
RUN mkdir -p "${WORK_PATH}/.config/Android Open Source Project" \
 && echo "[General]\nshowNestedWarning=false\n" > "${WORK_PATH}/.config/Android Open Source Project/Emulator.conf"

#=========
# Run App
#=========
STOPSIGNAL SIGTERM
ENV DEVICE_TYPE=emulator

CMD ["/bin/bash"]
