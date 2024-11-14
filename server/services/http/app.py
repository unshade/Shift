from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse
from scapy.layers.inet import TCP, IP
from os import listdir
from os.path import isfile, join

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

def save_packet(request_data, response_data):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"packet_{timestamp}.json"
    file_path = os.path.join(path, file_name) if not diff_path else os.path.join(diff_path, file_name)
    print(file_path)
    packet_data = {
        'request': request_data,
        'response': response_data
    }
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(packet_data, f, ensure_ascii=False, indent=4)

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

            if original_packet['request'] == request_data and original_packet['response'] == response_data:
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

def run_http(app_name):
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
        print('HTTP capture started, comparing requests')
        compare_requests()
