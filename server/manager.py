import multiprocessing
import shutil
import argparse
import os
import json

from proto.http.app import run_http
from proto.http.server import run_server

def run_servers(app_name):
    """Launch service listeners for a specific app."""
    # Check the environment variable
    stage = os.getenv("STAGE", "DEV")
    print(f"STAGE environment variable: {stage}")
    # Start the HTTP process only if ENVIRONNEMENT is set to "DEV"
    http_process = None
    if stage == "DEV":
        http_process = multiprocessing.Process(target=run_http, args=(app_name,))
        http_process.start()

    # Always start the server process
    http_server_answer = None
    if stage == "CI":
        http_server_answer = multiprocessing.Process(target=run_server, args=(app_name,))
        http_server_answer.start()

    # Wait for the processes to finish
    if http_process is not None:
        http_process.join()
    
    if http_server_answer is not None:
        http_server_answer.join()

def clear_all():
    """Clear every persistent datas"""
    shutil.rmtree('./resources')
    return "Cleared every datas"

def update_hosts(packet_directory, host='0.0.0.0'):
    packet_directory = "resources/http/"+packet_directory

    pkt = os.listdir(packet_directory)
    pkt.remove("diff")
    with open(packet_directory + '/' + pkt[0], 'r') as f:
        packet = json.load(f)
    domain = packet['request']['headers']['Host']
    print(f"Setting up domain: {domain}")
    with open('/etc/hosts', 'w') as f:
        f.write(f'{host} {domain}\n')
        f.write(f'{host} www.{domain}\n')

if __name__ == '__main__':
    # create if not exist directory ./resources
    if not os.path.exists('./resources'):
        os.makedirs('./resources')
    # Create directory for storing captured packets
    parser = argparse.ArgumentParser(prog="manager", description="Manager for running services")
    parser.add_argument("--version", action="version", version="v1.0.0")
    subparsers = parser.add_subparsers(dest="command")

    run_servers_parser = subparsers.add_parser("run_servers")
    run_servers_parser.add_argument("app_name", help="Name of the app to run services for")

    update_hosts_parser = subparsers.add_parser("update_hosts")
    update_hosts_parser.add_argument("app_name", help="Name of the app to update hosts for")

    clear_all_parser = subparsers.add_parser("clear_all")

    args = parser.parse_args()

    if args.command == "run_servers":
        run_servers(args.app_name)
    elif args.command == "clear_all":
        print(clear_all())
    elif args.command == "update_hosts":
        update_hosts(args.app_name)
    else:
        parser.print_help()