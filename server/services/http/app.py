from scapy.all import *
from scapy.layers.http import HTTPRequest
from scapy.layers.inet import TCP, IP

path = ''

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


def packet_callback(pak: Packet):
    if pak.haslayer(HTTPRequest):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_name = f"packet_{timestamp}.json"
        file_path = os.path.join(path, file_name)

        http_layer = pak[HTTPRequest]
        packet_data = {
            'source_ip': pak[IP].src,
            'destination_ip': pak[IP].dst,
            'source_port': pak[TCP].sport,
            'destination_port': pak[TCP].dport,
            'method': http_layer.Method.decode(),
            'path': http_layer.Path.decode(),
            'headers': decode_headers(http_layer.fields),
        }

        # Try to decode the payload if it exists
        if pak.haslayer(Raw):
            try:
                packet_data['body'] = pak[Raw].load.decode()
            except UnicodeDecodeError:
                packet_data['body'] = "Unable to decode payload"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(packet_data, f, ensure_ascii=False, indent=4)

        # print(f"Captured HTTP packet: {file_name}")


def start_capture():
    # print("Starting packet capture... Press Ctrl+C to stop.")
    sniff(filter="tcp port 80", prn=packet_callback, store=0)

def run_http(app_name):
    # Create directory for storing captured packets
    resources_dir = os.path.join(os.getcwd(), 'resources/http')
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
    app_path = resources_dir + '/' + app_name
    global path
    path = app_path
    if not os.path.exists(app_path):
        os.makedirs(app_path)
        start_capture()