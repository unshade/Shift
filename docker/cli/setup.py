import os

from setuptools import setup

app_version = os.getenv("DOCKER_ANDROID_VERSION", "test-version")

with open("requirements.txt", "r") as f:
    reqs = f.read().splitlines()

setup(
    name="docker-android",
    version=app_version,
    install_requires=reqs,
    py_modules=["cli", "docker-android"],
    entry_points={"console_scripts": "docker-android=src.app:cli"}
)