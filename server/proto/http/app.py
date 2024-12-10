import json
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from os import listdir
from os.path import isfile, join

from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse
from scapy.layers.inet import TCP, IP

from proto.http.request_service import decode_headers
from services.file_service import load_schema

path = ''
diff_path = None
request_num = 0
original_num = 0
comparing = False
apk_name = ''
testsuite: ET.Element = None


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
    schema = load_schema(app_name=apk_name)

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

def json_to_xml(json_data, parent=None, initial_name=None):
    if parent is None:
        if initial_name:
            parent = ET.Element(initial_name)
        else:
            parent = ET.Element('root')
    for key, value in json_data.items():
        if isinstance(value, dict):
            child = ET.Element(key)
            parent.append(child)
            json_to_xml(value, child)
        else:
            child = ET.Element(key)
            child.text = str(value)
            parent.append(child)
    return parent

def arrange_differences(original, new):
    diff = {}
    for key, value in original.items():
        if isinstance(value, dict):
            diff[key] = arrange_differences(value, new.get(key, {}))
        elif value != new.get(key):
            diff[key] = {'original': value, 'new': new.get(key)}
    return diff


def packet_callback(pak: Packet):
    global request_data
    global comparing
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

            testcase = ET.Element('testcase', name=f'Request {request_num + 1}')

            schema = load_schema(apk_name)
            filtered_request_data = {
                'request': filter_data_by_schema(request_data, schema.get('request', {})),
                'response': filter_data_by_schema(response_data, schema.get('response', {}))
            }

            print(original_packet['request'], '\n', filtered_request_data)

            if original_packet['request'] == filtered_request_data['request'] and original_packet['response'] == \
                    filtered_request_data['response']:
                print('Request matched')
                success = ET.Element('success')
                testcase.append(success)
            else:
                diff = arrange_differences(original_packet, filtered_request_data)
                print('Request did not match')
                failure = ET.Element('failure', message='Request did not match')
                failure.append(json_to_xml(original_packet, initial_name='original'))
                failure.append(json_to_xml(filtered_request_data, initial_name='new'))
                failure.append(json_to_xml(diff, initial_name='diff'))
                testcase.append(failure)
            testsuite.append(testcase)

            request_num += 1
        request_data = None


def stop_filter(pak: Packet):
    if not comparing:
        return False
    global request_num
    global original_num
    return request_num >= original_num


def start_capture():
    sniff(filter="tcp port 80", prn=packet_callback, store=0, stop_filter=stop_filter)


def compare_requests():
    originals = [f for f in listdir(path) if isfile(join(path, f))]
    global original_num
    original_num = len(originals)
    print(originals)
    global testsuite
    testsuite = ET.Element('testsuite', name='HTTP Request Comparison', tests=str(len(originals)))

    start_capture()

    rough_string = ET.tostring(testsuite, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

    report_path = os.path.join(diff_path, 'junit_report.xml')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_as_string)
    print(f'JUnit report generated at {report_path}')


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
    else:
        now = datetime.now()
        global diff_path
        global comparing
        comparing = True
        diff_path = path + '/diff/' + str(now)
        os.makedirs(diff_path, exist_ok=True)
        print('HTTP capture started, original trace detected, comparing requests based on :')
        compare_requests()
