import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from os import listdir
from os.path import isfile, join

from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse
from scapy.layers.inet import TCP, IP

from proto.http.request_service import decode_headers

path = ''
diff_path = None
request_num = 0
original_num = 0
apk_name = ''
testsuite: ET.Element = None


def save_packet(request_data, response_data, packet):
    """
    Save packet data to a JSON file, filtering fields based on a predefined schema.

    :param request_data: Dictionary containing request data
    :param response_data: Dictionary containing response data
    """
    # Load schema from the specified file
    global path
    global diff_path

    # Filter data based on schema
    packet_data = {
        'request': request_data,
        'response': response_data
    }

    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"packet_{timestamp}.json"
    file_path = os.path.join(path, file_name) if not diff_path else os.path.join(diff_path, file_name)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save filtered data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(packet_data, f, ensure_ascii=False, indent=4)

    print(f"Packet saved to: {file_path}")

    file_path = os.path.join(path, 'http.pcap')
    # Save pak to pcap file (append)

    wrpcap(file_path, packet, append=True)

    print(f"Packet pcap updated to: {file_path}")


request_data = None


def packet_callback(pak: Packet):
    global request_data
    print(pak.summary())
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
        save_packet(request_data, response_data, pak)
        request_data = None

def start_capture():
    sniff(filter="tcp port 80", prn=packet_callback, store=0)

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
