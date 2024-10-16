import multiprocessing
import time
import os

def start_flask_server():
    os.system("python http/app.py")

def launch_servers():
    flask_process = multiprocessing.Process(target=start_flask_server)

    flask_process.start()

    flask_process.join()

if __name__ == '__main__':
    print("Launching protocols listeners...")
    launch_servers()