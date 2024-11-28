from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse
from scapy.layers.inet import TCP, IP
from os import listdir
from os.path import isfile, join
import os
import json
from datetime import datetime

path = ''
diff_path = None
request_num = 0
comparing = False


def decode_headers(headers):
    decoded_headers = {}
    for k, v in headers.items():
        if isinstance(k, bytes):
            k = k.decode()
        if isinstance(v, bytes):
            v = v.decode()
        elif isinstance(v, dict):
            v = decode_headers(v)
        decoded_headers[k] = v
    return decoded_headers


def filter_data_by_schema(data, schema):
    """
    Filter the input data to only include fields specified in the schema.

    :param data: Input dictionary to filter
    :param schema: Schema dictionary specifying allowed fields
    :return: Filtered dictionary
    """
    if not isinstance(data, dict):
        return data

    filtered_data = {}
    for key, value in schema.items():
        if key in data:
            # If the value is True, include the entire field
            if value is True:
                filtered_data[key] = data[key]
            # If the value is a dictionary, recursively filter nested fields
            elif isinstance(value, dict):
                filtered_data[key] = filter_data_by_schema(data.get(key, {}), value)

    return filtered_data


def save_packet(request_data, response_data):
    """
    Save packet data to a JSON file, filtering fields based on a predefined schema.

    :param request_data: Dictionary containing request data
    :param response_data: Dictionary containing response data
    """
    # Load schema from the specified file
    global path
    global diff_path
    try:
        with open('./schema/immich.json', 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
    except FileNotFoundError:
        print("Schema file not found. Saving full data.")
        schema = {
            'request': True,
            'response': True
        }
    except json.JSONDecodeError:
        print("Error decoding schema file. Saving full data.")
        schema = {
            'request': True,
            'response': True
        }

    # Filter data based on schema
    filtered_packet_data = {
        'request': filter_data_by_schema(request_data, schema.get('request', {})),
        'response': filter_data_by_schema(response_data, schema.get('response', {}))
    }

    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"packet_{timestamp}.json"
    file_path = os.path.join(path, file_name) if not diff_path else os.path.join(diff_path, file_name)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save filtered data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_packet_data, f, ensure_ascii=False, indent=4)

    print(f"Packet saved to: {file_path}")


request_data = None


def packet_callback(pak: Packet):
    global request_data
    global comparing
    if pak.haslayer(HTTPRequest):
        http_layer = pak[HTTPRequest]
        request_data = {
            'source_ip': pak[IP].src,
            'destination_ip': pak[IP].dst,
            'source_port': pak[TCP].sport,
            'destination_port': pak[TCP].dport,
            'method': http_layer.Method.decode(),
            'path': http_layer.Path.decode(),
            'headers': decode_headers(http_layer.fields),
        }
        if pak.haslayer(Raw):
            try:
                request_data['body'] = pak[Raw].load.decode()
            except UnicodeDecodeError:
                request_data['body'] = "Unable to decode payload"

    if pak.haslayer(HTTPResponse) and request_data:
        http_layer = pak[HTTPResponse]
        response_data = {
            'source_ip': pak[IP].src,
            'destination_ip': pak[IP].dst,
            'source_port': pak[TCP].sport,
            'destination_port': pak[TCP].dport,
            'status_code': http_layer.Status_Code.decode(),
            'reason_phrase': http_layer.Reason_Phrase.decode(),
            'headers': decode_headers(http_layer.fields),
        }
        if pak.haslayer(Raw):
            try:
                response_data['body'] = pak[Raw].load.decode()
            except UnicodeDecodeError:
                response_data['body'] = "Unable to decode payload"
        save_packet(request_data, response_data)
        if comparing:
            global request_num
            originals = [f for f in listdir(path) if isfile(join(path, f))]
            print(request_num)
            if request_num >= len(originals):
                print('All requests compared')
                return
            original_to_compare = originals[request_num]
            with open(join(path, original_to_compare), 'r') as f:
                original_packet = json.load(f)

            with open('./schema/immich.json', 'r', encoding='utf-8') as schema_file:
                schema = json.load(schema_file)
            filtered_request_data = {
                'request': filter_data_by_schema(request_data, schema.get('request', {})),
                'response': filter_data_by_schema(response_data, schema.get('response', {}))
            }

            print(original_packet['request'],'\n', filtered_request_data)


            if original_packet['request'] == filtered_request_data['request'] and original_packet['response'] == filtered_request_data['response']:
                print('Request matched')
            else:
                print('Request did not match')

            request_num += 1
        request_data = None


def start_capture():
    sniff(filter="tcp port 80", prn=packet_callback, store=0)


def compare_requests():
    originals = [f for f in listdir(path) if isfile(join(path, f))]
    print(originals)

    start_capture()
    pass


def run_http(app_name: str):
    resources_dir = os.path.join(os.getcwd(), 'resources/http')
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
    app_path = resources_dir + '/' + app_name
    global path
    path = app_path
    if not os.path.exists(app_path):
        os.makedirs(app_path)
        print('HTTP initial capture started')
        start_capture()
    else:
        now = datetime.now()
        global diff_path
        global comparing
        comparing = True
        diff_path = path + '/diff/' + str(now)
        os.makedirs(diff_path, exist_ok=True)
        print('HTTP capture started, original trace detected, comparing requests based on :')
        compare_requests()
