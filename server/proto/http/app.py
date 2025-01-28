import xml.etree.ElementTree as ET
from datetime import datetime
import os
import json
from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse, HTTP
from scapy.layers.inet import TCP, IP
from proto.http.request_service import decode_headers
from collections import defaultdict

path = ''
diff_path = None
request_num = 0
original_num = 0
apk_name = ''
testsuite: ET.Element = None

# Dictionary to store TCP stream data
tcp_streams = defaultdict(lambda: {"request": None, "response_headers": None, "response_body": b""})

def save_packet(request_data, response_data, packet):
    """
    Save packet data to a JSON file, filtering fields based on a predefined schema.

    :param request_data: Dictionary containing request data
    :param response_data: Dictionary containing response data
    """
    global path
    global diff_path

    packet_data = {
        'request': request_data,
        'response': response_data
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"packet_{timestamp}.json"
    file_path = os.path.join(path, file_name) if not diff_path else os.path.join(diff_path, file_name)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(packet_data, f, ensure_ascii=False, indent=4)

    print(f"Packet saved to: {file_path}")

    file_path = os.path.join(path, 'http.pcap')
    wrpcap(file_path, packet, append=True)

    print(f"Packet pcap updated to: {file_path}")

def packet_callback(pak: Packet):
    global tcp_streams

    if pak.haslayer(TCP) and pak.haslayer(IP):
        # Create a unique key for the TCP stream
        stream_key = (pak[IP].src, pak[TCP].sport, pak[IP].dst, pak[TCP].dport)

        if pak.haslayer(HTTPRequest):
            # Handle HTTP request
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
            tcp_streams[stream_key]["request"] = request_data

        elif pak.haslayer(HTTPResponse):
            # Handle HTTP response headers
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
            tcp_streams[stream_key]["response_headers"] = response_data

        elif pak.haslayer(Raw) and stream_key in tcp_streams:
            # Handle HTTP response payload (Raw layer only)
            tcp_streams[stream_key]["response_body"] += pak[Raw].load

            # Check if the response is complete
            response_headers = tcp_streams[stream_key]["response_headers"]
            if response_headers:
                content_length = int(response_headers['headers'].get('Content-Length', 0))
                if len(tcp_streams[stream_key]["response_body"]) >= content_length:
                    # Response is complete
                    response_data = tcp_streams[stream_key]["response_headers"]
                    response_data['body'] = tcp_streams[stream_key]["response_body"].decode('utf-8', errors='replace')
                    save_packet(tcp_streams[stream_key]["request"], response_data, pak)
                    # Clear the stream data
                    del tcp_streams[stream_key]

def start_capture(port=8000):
    # Bind layers
    bind_layers(TCP, HTTP, sport=port)
    bind_layers(TCP, HTTP, dport=port)
    sniff(filter=f"tcp port {port}", prn=packet_callback, store=0)

def run_http(app_name: str):
    resources_dir = os.path.join(os.getcwd(), 'resources/http')
    global apk_name
    apk_name = app_name
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
    app_path = resources_dir + '/' + app_name
    global path
    path = app_path
    if not os.path.exists(app_path):
        os.makedirs(app_path)
        print('HTTP initial capture started')
        start_capture()