import multiprocessing
import shutil
import argparse
from services.http.app import run_http

def run_servers(app_name):
    """Launch services listeners for a specific app"""
    flask_process = multiprocessing.Process(target=run_http, args=(app_name,))
    flask_process.start()
    flask_process.join()

def clear_all():
    """Clear every persistent datas"""
    shutil.rmtree('./resources')
    return "Cleared every datas"

if __name__ == '__main__':
    # Create directory for storing captured packets
    parser = argparse.ArgumentParser(prog="manager", description="Manager for running services")
    parser.add_argument("--version", action="version", version="v1.0.0")
    subparsers = parser.add_subparsers(dest="command")

    run_servers_parser = subparsers.add_parser("run_servers")
    run_servers_parser.add_argument("app_name", help="Name of the app to run services for")

    clear_all_parser = subparsers.add_parser("clear_all")

    args = parser.parse_args()

    if args.command == "run_servers":
        run_servers(args.app_name)
    elif args.command == "clear_all":
        print(clear_all())
    else:
        parser.print_help()