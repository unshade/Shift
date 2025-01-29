import xml.etree.ElementTree as ET
from datetime import datetime
import os
import json
from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse, HTTP
from scapy.layers.inet import TCP, IP
from proto.http.request_service import decode_headers
from collections import defaultdict

# Global variables
path = ''
diff_path = None
apk_name = ''
testsuite: ET.Element = None

# Dictionary to store TCP stream data
tcp_streams = defaultdict(lambda: {"request": None, "response_headers": None, "response_body": b"", "packets": []})


def save_packet(request_data, response_data, packets):
    """
    Save packet data to a JSON file, filtering fields based on a predefined schema.

    :param request_data: Dictionary containing request data
    :param response_data: Dictionary containing response data
    :param packets: List of packets associated with the request/response
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

    # Save packets to a pcap file
    pcap_file_path = os.path.join(path, 'http.pcap')
    wrpcap(pcap_file_path, packets, append=True)

    print(f"Packet pcap updated to: {pcap_file_path}")


def packet_callback(pak: Packet):
    global tcp_streams

    if pak.haslayer(TCP) and pak.haslayer(IP):
        # Create a unique key for the TCP stream
        stream_key = (pak[IP].src, pak[TCP].sport, pak[IP].dst, pak[TCP].dport)

        # Track packets for this stream
        if not pak.haslayer(HTTPRequest) and not pak.haslayer(HTTPResponse):
            if pak.haslayer(Raw):
                print(f"Adding packet to stream: {stream_key}")
                tcp_streams[stream_key]["response_body"] += pak[Raw].load
                tcp_streams[stream_key]["packets"].append(pak)

        if pak.haslayer(HTTPRequest):
            # Stream key is reversed for the response
            stream_key = (pak[IP].dst, pak[TCP].dport, pak[IP].src, pak[TCP].sport)

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

            if pak.haslayer(Raw):
                try:
                    tcp_streams[stream_key]["response_body"] = pak[Raw].load
                except UnicodeDecodeError:
                    tcp_streams[stream_key]["response_body"] = b"Unable to decode payload"

        # Check if the TCP stream is ending (FIN flag)
        if pak[TCP].flags.F == 1:
            if tcp_streams[stream_key]["request"] is None or tcp_streams[stream_key]["response_headers"] is None:
                return
            print(f"TCP stream ended: {stream_key}")

            response_body = tcp_streams[stream_key]["response_body"]

            response_body_decoded = response_body.decode(errors='ignore')
            print(response_body_decoded)
            response_headers = tcp_streams[stream_key]["response_headers"]
            response_headers['Content-Length'] = len(response_body_decoded)
            response_headers['body'] = response_body_decoded

            save_packet(tcp_streams[stream_key]["request"], response_headers, tcp_streams[stream_key]["packets"])

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
