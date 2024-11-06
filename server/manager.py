#!/usr/bin/env python3

import multiprocessing
import shutil
from services.http.app import run_http

from pycli import CLI

cli = CLI(prog="manager", version="v1.0.0")

@cli.command
def run_servers(app_name):
    """Launch services listeners for a specific app"""
    flask_process = multiprocessing.Process(target=run_http, args=(app_name,))
    flask_process.start()
    flask_process.join()

@cli.command
def clear_all():
    """Clear every persistent datas"""
    shutil.rmtree('./resources')
    return "Cleared every datas"

if __name__ == '__main__':
    # Create directory for storing captured packets
    print(cli.run())