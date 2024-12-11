#!/usr/bin/env python3

import os
import time 
import subprocess
import logging
from enum import Enum
from typing import Union

import click

from src.application import Application
from src.device import DeviceType
from src.device.emulator import Emulator
from src.helper import convert_str_to_bool, get_env_value_or_raise
from src.constants import ENV
from src.logger import log

log.init()
logger = logging.getLogger("App")


def get_device(given_input: str) -> Union[Emulator, None]:
    """
    Get Device object based on given input

    :param given_input: Device type as a string
    :return: Platform object or None if invalid
    """
    input_lower = given_input.lower()

    if input_lower == DeviceType.EMULATOR.value.lower():
        try:
            emu_av = get_env_value_or_raise(ENV.EMULATOR_ANDROID_VERSION)
            emu_img_type = get_env_value_or_raise(ENV.EMULATOR_IMG_TYPE)
            emu_sys_img = get_env_value_or_raise(ENV.EMULATOR_SYS_IMG)

            emu_device = os.getenv(ENV.EMULATOR_DEVICE, "Nexus 5")
            emu_data_partition = os.getenv(ENV.EMULATOR_DATA_PARTITION, "550m")
            emu_additional_args = os.getenv(ENV.EMULATOR_ADDITIONAL_ARGS, "")

            emu_name = os.getenv(ENV.EMULATOR_NAME, f"{emu_device.replace(' ', '_').lower()}_{emu_av}")
            return Emulator(emu_name, emu_device, emu_av, emu_data_partition, emu_additional_args, emu_img_type, emu_sys_img)
        except KeyError as e:
            logger.error(f"Missing environment variable: {e}")
            return None
    return None


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli():
    """CLI entry point."""
    pass


def start_appium() -> None:
    """Start the Appium server."""
    cmd = "/usr/bin/appium"
    app_appium = Application("Appium", cmd, os.getenv(ENV.APPIUM_ADDITIONAL_ARGS, ""), False)
    app_appium.start()


def start_device() -> None:
    """Start the specified device."""
    given_device_type = get_env_value_or_raise(ENV.DEVICE_TYPE)
    selected_device = get_device(given_device_type)
    if selected_device is None:
        raise RuntimeError(f"Invalid device type: '{given_device_type}'. Please check the configuration.")
    selected_device.create()
    selected_device.start()
    selected_device.wait_until_ready()
    selected_device.reconfigure()
    selected_device.keep_alive()


def start_display_screen() -> None:
    """Start the display screen (Xvfb)."""
    cmd = "/usr/bin/Xvfb"
    args = f"{os.getenv(ENV.DISPLAY)} " \
           f"-screen {os.getenv(ENV.SCREEN_NUMBER)} " \
           f"{os.getenv(ENV.SCREEN_WIDTH)}x" \
           f"{os.getenv(ENV.SCREEN_HEIGHT)}x" \
           f"{os.getenv(ENV.SCREEN_DEPTH)}"
    display_screen = Application("DisplayScreen", cmd, args, False)
    display_screen.start()


def start_display_wm() -> None:
    """Start the window manager (Openbox)."""
    cmd = "/usr/bin/openbox-session"
    display_wm = Application("DisplayWM", cmd)
    display_wm.start()


def start_port_forwarder() -> None:
    """Start the port forwarder."""
    import socket
    local_ip = socket.gethostbyname(socket.gethostname())
    cmd = f"/usr/bin/socat tcp-listen:5554,bind={local_ip},fork tcp:127.0.0.1:5554 & " \
          f"/usr/bin/socat tcp-listen:5555,bind={local_ip},fork tcp:127.0.0.1:5555"
    port_forwarder = Application("PortForwarder", cmd)
    port_forwarder.start()


def start_vnc_server() -> None:
    """Start the VNC server."""
    cmd = "/usr/bin/x11vnc"
    vnc_password = os.getenv(ENV.VNC_PASSWORD)
    pass_path = None

    if vnc_password:
        pass_path = os.path.join(os.getenv(ENV.WORK_PATH, ""), ".vncpass")
        subprocess.check_call(f"{cmd} -storepasswd {vnc_password} {pass_path}", shell=True)

    args = f"-display {os.getenv(ENV.DISPLAY)} -forever -shared {'-rfbauth ' + pass_path if pass_path else '-nopw'}"
    vnc_server = Application("VNCServer", cmd, args, False)
    vnc_server.start()


def start_vnc_web() -> None:
    """Start the VNC web interface."""
    if convert_str_to_bool(os.getenv(ENV.WEB_VNC, "false")):
        vnc_port = get_env_value_or_raise(ENV.VNC_PORT)
        vnc_web_port = get_env_value_or_raise(ENV.WEB_VNC_PORT)
        cmd = "/opt/noVNC/utils/novnc_proxy"
        args = f"--vnc localhost:{vnc_port} localhost:{vnc_web_port}"
        vnc_web = Application("VNCWeb", cmd, args, False)
        vnc_web.start()
    else:
        logger.info("Environment variable WEB_VNC is not set. VNC Web will not start.")


def start_appium_automation() -> None:
    """Start the Appium automation process."""
    try:
        subprocess.check_call(["pgrep", "-f", "appium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Appium is already running.")
    except subprocess.CalledProcessError:
        logger.error("Appium is not running. Please start Appium first.")
        return


    while True:
        try:
            subprocess.check_call(["adb", "devices"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Device is connected.")
            break
        except subprocess.CalledProcessError:
            logger.error("No device connected. Please start an emulator.")
            return
    
    # wait 120 seconds for the device to be ready

    time.sleep(120)
    path = os.getenv(ENV.WORK_PATH, "")
    appium_path = os.path.join(path, "appium")
    if not os.path.exists(appium_path):
        logger.error(f"Path '{appium_path}' does not exist.")
        return

    venv_activate = os.path.join(path, "venv", "bin", "activate")
    immich_script = os.path.join(appium_path, "immich.py")

    if not os.path.exists(venv_activate):
        logger.error(f"Virtual environment activation script not found at '{venv_activate}'.")
        return

    if not os.path.exists(immich_script):
        logger.error(f"immich.py script not found at '{immich_script}'.")
        return

    try:
        cmd = f"bash -c 'source {venv_activate} && python {immich_script} {appium_path}/immich_x86.apk'"
        app_appium_automation = Application("appium_automation", cmd, "",False)
        app_appium_automation.start()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Appium automation: {e}")


@cli.command()
@click.argument("app", type=click.Choice([app.value for app in Application.App]))
def start(app):
    """Start a specified application."""
    app_mapping = {
        Application.App.APPIUM.value.lower(): start_appium,
        Application.App.DEVICE.value.lower(): start_device,
        Application.App.DISPLAY_SCREEN.value.lower(): start_display_screen,
        Application.App.DISPLAY_WM.value.lower(): start_display_wm,
        Application.App.PORT_FORWARDER.value.lower(): start_port_forwarder,
        Application.App.VNC_SERVER.value.lower(): start_vnc_server,
        Application.App.VNC_WEB.value.lower(): start_vnc_web,
        Application.App.APPIUM_AUTOMATION.value.lower(): start_appium_automation,
    }

    selected_app = app.lower()
    if selected_app in app_mapping:
        app_mapping[selected_app]()
    else:
        logger.error(f"Application '{selected_app}' is not supported!")


if __name__ == "__main__":
    cli()