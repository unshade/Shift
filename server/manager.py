#!/usr/bin/env python3

import multiprocessing
import os
import shutil

from pycli import CLI

cli = CLI(prog="app", version="v1.0.0")

@cli.command
def run_servers(app_name):
    """Launch protocols listeners for a specific app"""
    flask_process = multiprocessing.Process(target=start_http_server)
    flask_process.start()
    flask_process.join()

@cli.command
def clear_all():
    """Clear every persistent datas"""
    shutil.rmtree('./resources')
    return "Cleared every datas"

def start_http_server():
    os.system("python http/app.py")

if __name__ == '__main__':
    print(cli.run())