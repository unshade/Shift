import xml.etree.ElementTree as ET
from datetime import datetime
import os
import json
import base64
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


def is_binary_content(headers):
    """
    Check if the content is likely binary based on Content-Type header
    """
    content_type = headers.get('Content-Type', '').lower()
    if not content_type:
        content_type = headers.get('Content_Type', '').lower()
    binary_types = ['image/', 'application/octet-stream', 'audio/', 'video/',
                    'application/pdf', 'application/zip', 'application/x-binary']
    return any(binary_type in content_type for binary_type in binary_types)


def process_response_body(body, headers):
    """
    Process response body based on content type
    """
    try:
        if is_binary_content(headers):
            # For binary content, encode as base64
            return {
                'encoding': 'base64',
                'data': base64.b64encode(body).decode('utf-8')
            }
        else:
            # For text content, try to decode as UTF-8
            return {
                'encoding': 'utf-8',
                'data': body.decode('utf-8', errors='replace')
            }
    except Exception as e:
        # If we can't determine the type or decode properly, default to base64
        return {
            'encoding': 'base64',
            'data': base64.b64encode(body).decode('utf-8')
        }


def save_packet(request_data, response_data, packets):
    """
    Save packet data to a JSON file, handling binary data appropriately
    """
    global path
    global diff_path

    # Process response body before saving
    if 'body' in response_data and isinstance(response_data['body'], (bytes, bytearray)):
        response_data['body'] = process_response_body(response_data['body'], response_data['headers'])

    packet_data = []

    file_name = f"packets.json"
    file_path = os.path.join(path, file_name) if not diff_path else os.path.join(diff_path, file_name)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    if not os.path.isfile(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('[]')
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            packet_data = json.load(f)

    packet_data.append({
        'request': request_data,
        'response': response_data
    })

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
                    # If request body is binary, encode it as base64
                    request_data['body'] = {
                        'encoding': 'base64',
                        'data': base64.b64encode(pak[Raw].load).decode('utf-8')
                    }
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
                tcp_streams[stream_key]["response_body"] = pak[Raw].load

        # Check if the TCP stream is ending (FIN flag)
        if pak[TCP].flags.F == 1:
            if tcp_streams[stream_key]["request"] is None or tcp_streams[stream_key]["response_headers"] is None:
                return
            print(f"TCP stream ended: {stream_key}")

            response_body = tcp_streams[stream_key]["response_body"]
            response_headers = tcp_streams[stream_key]["response_headers"]
            response_headers['Content-Length'] = len(response_body)
            response_headers['body'] = response_body

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
