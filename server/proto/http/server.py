import json
import os
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from datetime import datetime

from flask import Flask, request, jsonify
from flask import Response, make_response
from scapy.all import wrpcap
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from proto.http.http_request_packet import HttpRequestPacket
from proto.http.http_response_packet import HttpResponsePacket
from services.dict_utils import arrange_differences
from services.file_service import load_schema
from services.xml_utils import json_to_xml


class PacketMatcher:
    def __init__(self, packet_directory, apk_name):
        """
        Initialize the packet matcher with packets from a given directory.
        
        :param packet_directory: Directory containing JSON packet files
        """
        self.apk_name = apk_name
        self.packets = []
        self.load_packets(packet_directory)
        self.request_number = 0
        self.testsuite = ET.Element('testsuite', name='HTTP Request Comparison', tests=str(len(self.packets)))
        self.compare_path = os.path.join(os.getcwd(), 'resources/http', self.apk_name, 'diff', str(datetime.now()))
        os.makedirs(self.compare_path, exist_ok=True)

    def compare_packets(self, incoming_request):
        if not self.packets:
            print("All requests compared")
            rough_string = ET.tostring(self.testsuite, 'utf-8')
            beautified = minidom.parseString(rough_string)
            pretty_xml_as_string = beautified.toprettyxml(indent="  ")

            report_path = os.path.join(self.compare_path, 'junit_report.xml')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml_as_string)
            print(f'JUnit report generated at {report_path}')
            # also write it in the root of the project and name it "junit_report.xml"
            with open('junit_report.xml', 'w', encoding='utf-8') as f:
                f.write(pretty_xml_as_string)
            return -1

        packet_number = -1
        for i, packet in enumerate(self.packets):
            if packet['request']['method'] == incoming_request['method'] and packet['request']['path'] == incoming_request['path']:
                packet_number = i
                break

        if packet_number == -1:
            print("No matching packet found")
            return None

        original_packet = self.packets.pop(packet_number)

        testcase = ET.Element('testcase', name=f'Request {self.request_number + 1}')
        schema = load_schema(self.apk_name)

        original_request = HttpRequestPacket(
            source_ip=original_packet['request']['source_ip'],
            destination_ip=original_packet['request']['destination_ip'],
            source_port=original_packet['request']['source_port'],
            destination_port=original_packet['request']['destination_port'],
            method=original_packet['request']['method'],
            path=original_packet['request']['path'],
            headers=original_packet['request']['headers']
        )
        original_request.add_body(original_packet['request'].get('body', ''))
        original_request.add_schema(schema.get('request', {}))

        new_request = HttpRequestPacket(
            source_ip=incoming_request['source_ip'],
            destination_ip=incoming_request['destination_ip'],
            source_port=int(incoming_request['source_port']),
            destination_port=int(incoming_request['destination_port']),
            method=incoming_request['method'],
            path=incoming_request['path'],
            headers=incoming_request['headers']
        )
        new_request.add_body(incoming_request.get('body', ''))
        new_request.add_schema(schema.get('request', {}))

        if original_request == new_request:
            print('Request matched')
            success = ET.Element('success')
            testcase.append(success)
        else:
            diff = arrange_differences(
                original_request.to_filtered_dict(),
                new_request.to_filtered_dict()
            )

            print('Request did not match')
            failure = ET.Element('failure', message='Request did not match')
            failure.append(json_to_xml(original_request.to_filtered_dict(), initial_name='original'))
            failure.append(json_to_xml(new_request.to_filtered_dict(), initial_name='new'))
            failure.append(json_to_xml(diff, initial_name='diff'))
            testcase.append(failure)
        self.testsuite.append(testcase)

        self.request_number += 1

        response = HttpResponsePacket(
            source_ip=original_packet['response']['source_ip'],
            destination_ip=original_packet['response']['destination_ip'],
            source_port=original_packet['response']['source_port'],
            destination_port=original_packet['response']['destination_port'],
            status_code=original_packet['response']['status_code'],
            reason_phrase=original_packet['response']['reason_phrase'],
            headers=original_packet['response']['headers']
        )
        response.add_body(original_packet['response'].get('body', ''))
        self.save_packet(original_request.to_dict(), response.to_dict())
        return response.to_dict()

    def save_packet(self, request_data, response_data):
        """
        Save packet data to a JSON file, filtering fields based on a predefined schema.

        :param request_data: Dictionary containing request data
        :param response_data: Dictionary containing response data
        """
        # Filter data based on schema
        packet_data = {
            'request': request_data,
            'response': response_data
        }

        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_name = f"packet_{timestamp}.json"
        file_path = os.path.join(self.compare_path, file_name)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save filtered data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(packet_data, f, ensure_ascii=False, indent=4)

        print(f"Packet saved to: {file_path}")

    def load_packets(self, directory):
        """
        Load all JSON packet files from the specified directory.
        
        :param directory: Path to the directory containing packet JSON files
        """
        files = sorted(os.listdir(directory))
        for filename in files:
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        packet = json.load(f)
                        self.packets.append(packet)
                except Exception as e:
                    print(f"Error loading packet {filename}: {e}")

        print(f"Loaded {len(self.packets)} packets")


def create_app(packet_directory, app_name):
    """
    Create and configure the Flask application.
    
    :param packet_directory: Directory containing JSON packet files
    :param app_name: Name of the application
    :return: Configured Flask app
    """
    # Disable Flask's default logging to reduce noise
    # log = logging.getLogger('werkzeug')
    # log.setLevel(logging.ERROR)
    app = Flask(__name__)
    packet_matcher = PacketMatcher(packet_directory, app_name)

    @app.before_request
    def catch_all():
        """
        Catch-all route to match any incoming request against pre-recorded packets.
        
        :return: Matched response or 404
        """
        incoming_request = {
            'source_ip': request.remote_addr,
            'destination_ip': request.host,
            'source_port': request.environ.get('REMOTE_PORT'),
            'destination_port': request.environ.get('SERVER_PORT'),
            'method': request.method,
            'path': request.path,
            'headers': dict(request.headers)
        }
        if request.data:
            incoming_request['body'] = request.data.decode()

        response = packet_matcher.compare_packets(incoming_request)

        pcap_file_path = os.path.join(packet_matcher.compare_path, 'http.pcap')
        request_packet = Ether() / IP(src=incoming_request['source_ip'], dst=incoming_request['destination_ip']) / \
                         TCP(sport=int(incoming_request['source_port']),
                             dport=int(incoming_request['destination_port'])) / \
                         HTTP() / \
                         HTTPRequest(
                             Method=incoming_request['method'].encode(),
                             Path=incoming_request['path'].encode(),
                             Http_Version=b"HTTP/1.1",
                         ) / \
                         Raw(load=incoming_request.get('body', '').encode())
        wrpcap(pcap_file_path, request_packet, append=True)

        print(f"Packet pcap updated to: {pcap_file_path}")

        if response == -1:
            os._exit(0)

        if response:
            response_packet = Ether() / IP(src=response['source_ip'], dst=response['destination_ip']) / \
                              TCP(sport=int(response['source_port']), dport=int(response['destination_port'])) / \
                              HTTP() / \
                              HTTPResponse(
                                  Status_Code=response['status_code'].encode(),
                                  Reason_Phrase=response['reason_phrase'].encode(),
                                  Http_Version=b"HTTP/1.1",
                              ) / \
                              Raw(load=response.get('body', '').encode())
            wrpcap(pcap_file_path, response_packet, append=True)
            flask_response = make_response(response['body'])
            flask_response.status_code = int(response['status_code'])
            for header, value in response['headers'].items():
                if header == "Transfer_Encoding" or header == "Content_Encoding" or header == "Content_Length":
                    continue
                elif header == "Unknown_Headers":
                    for h, v in value.items():
                        flask_response.headers[h.replace('_', '-')] = v
                elif header == 'Set-Cookie' or header == 'Set_Cookie':
                    for cookie in value.split('§'):
                        cookie = cookie.strip()
                        cookie_name = cookie.split('=')[0]
                        cookie_value = cookie.split('=')[1]
                        if ';' in cookie_value:
                            cookie_value = cookie_value.split(';')[0]

                        expire_date = cookie.split('Expires=')[1]
                        expire_date = expire_date.split(';')[0]
                        expire_date = datetime.strptime(expire_date, '%a, %d %b %Y %H:%M:%S %Z')

                        max_age = cookie.split('Max-Age=')[1]
                        max_age = max_age.split(';')[0]
                        max_age = int(max_age)

                        same_site = cookie.split('SameSite=')[1]
                        same_site = same_site.split(';')[0]

                        flask_response.set_cookie(cookie_name, cookie_value, expires=expire_date, max_age=max_age,
                                                  samesite=same_site, httponly=('HttpOnly' in cookie))
                else:
                    flask_response.headers[header.replace('_', '-')] = value
            return flask_response
        return jsonify({"error": "No matching packet found"}), 404

    return app


def run_server(packet_directory, host='0.0.0.0', port=80):
    """
    Run the Flask server with pre-recorded packets.
    
    :param packet_directory: Directory containing JSON packet files
    :param host: Host to bind the server to (default: 0.0.0.0)
    :param port: Port to run the server on (default: 80)
    """
    app_name = packet_directory
    packet_directory = "resources/http/" + packet_directory
    app = create_app(packet_directory, app_name)

    pkt = os.listdir(packet_directory)
    try:
        pkt.remove("diff")
    except ValueError:
        pass
    with open(packet_directory + '/' + pkt[0], 'r') as f:
        packet = json.load(f)
    domain = packet['request']['headers']['Host']
    print(f"Setting up domain: {domain}")
    with open('/etc/hosts', 'w') as f:
        f.write(f'{host} {domain}\n')
        f.write(f'{host} www.{domain}\n')
    # os.system('sudo systemctl restart systemd-resolved')
    print(f"Starting server on {host}:{port}")
    print(f"Using packets from directory: {packet_directory}")
    app.run(host=host, port=port, debug=True)
