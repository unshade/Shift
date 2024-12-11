import json
import logging
import os
import platform
import requests
import signal
import time

from abc import ABC, abstractmethod
from enum import Enum

from src.helper import convert_str_to_bool, get_env_value_or_raise
from src.constants import DEVICE, ENV


class DeviceType(Enum):
    EMULATOR = "emulator"

class Device(ABC):

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device_type = None
        self.interval_waiting = int(os.getenv(ENV.DEVICE_INTERVAL_WAITING, 2))
        signal.signal(signal.SIGTERM, self.tear_down)

    def set_status(self, current_status) -> None:
        bashrc_file = f"{os.getenv(ENV.WORK_PATH)}/device_status"
        with open(bashrc_file, "w+") as bf:
            bf.write(current_status)

    def create(self) -> None:
        self.set_status(DEVICE.STATUS_CREATING)

    def start(self) -> None:
        self.set_status(DEVICE.STATUS_STARTING)

    def wait_until_ready(self) -> None:
        self.set_status(DEVICE.STATUS_BOOTING)

    def reconfigure(self) -> None:
        self.set_status(DEVICE.STATUS_RECONFIGURING)

    def keep_alive(self) -> None:
        self.set_status(DEVICE.STATUS_READY)
        self.logger.warning(f"{self.device_type} process will be kept alive to be able to get sigterm signal...")
        while True:
            time.sleep(2)

    @abstractmethod
    def tear_down(self, *args) -> None:
        pass
