import json
import os
import time
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime
import base64
from flask import Flask, request, jsonify, send_file
from flask import make_response
from scapy.all import wrpcap
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from io import BytesIO

from proto.http.http_request_packet import HttpRequestPacket
from proto.http.http_response_packet import HttpResponsePacket
from services.dict_utils import arrange_differences
from services.file_service import load_schema
from services.xml_utils import json_to_xml


class PacketMatcher:
    def __init__(self, packet_directory, apk_name):
        self.apk_name = apk_name
        self.packets = []
        self.load_packets(packet_directory)
        self.request_number = 0
        self.testsuite = ET.Element('testsuite', name='HTTP Request Comparison', tests=str(len(self.packets)))
        self.compare_path = os.path.join(os.getcwd(), 'resources/http', self.apk_name, 'diff', str(int(time.time())))
        os.makedirs(self.compare_path, exist_ok=True)

    def decode_body(self, body_data):
        """
        Decode body based on its encoding
        """
        if isinstance(body_data, dict):
            encoding = body_data.get('encoding')
            data = body_data.get('data', '')

            if encoding == 'base64':
                return base64.b64decode(data)
            elif encoding == 'utf-8':
                return data.encode('utf-8')
            else:
                return data.encode('utf-8')
        return body_data.encode('utf-8') if isinstance(body_data, str) else body_data

    def save_junit_report(self):
        # Add every missing packet as a failed test for now
        current_testsuite = deepcopy(self.testsuite)
        request_number = self.request_number + 1
        for packet in self.packets:
            testcase = ET.Element('testcase', name=f'Request {request_number}')
            failure = ET.Element('failure', message='Automation did not reach this request')
            failure.append(json_to_xml(packet['request'], initial_name='original'))
            testcase.append(failure)
            current_testsuite.append(testcase)
            request_number += 1

        rough_string = ET.tostring(current_testsuite, 'utf-8')
        beautified = minidom.parseString(rough_string)
        pretty_xml_as_string = beautified.toprettyxml(indent="  ")

        report_path = os.path.join(self.compare_path, 'junit_report.xml')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_string)
        print(f'Current JUnit report generated at {report_path}')
        # also write it in the root of the project
        with open('junit_report.xml', 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_string)

    def compare_packets(self, incoming_request):
        if not self.packets:
            print("All requests compared")
            self.save_junit_report()
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
        self.save_junit_report()

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
        """
        file_name = "packets.json"
        filepath = os.path.join(directory, file_name)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                packets_loaded = json.load(f)
                for packet in packets_loaded:
                    self.packets.append(packet)
                print(f"Loaded {len(self.packets)} packets from {filepath}")
        else:
            print(f"No packets found in {directory}. There should be a file named {file_name} with packets.")


def create_app(packet_directory, app_name):
    app = Flask(__name__)
    packet_matcher = PacketMatcher(packet_directory, app_name)

    @app.before_request
    def catch_all():
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
            # Create response packet for pcap
            response_body = packet_matcher.decode_body(response.get('body', ''))
            response_packet = Ether() / IP(src=response['source_ip'], dst=response['destination_ip']) / \
                              TCP(sport=int(response['source_port']), dport=int(response['destination_port'])) / \
                              HTTP() / \
                              HTTPResponse(
                                  Status_Code=response['status_code'].encode(),
                                  Reason_Phrase=response['reason_phrase'].encode(),
                                  Http_Version=b"HTTP/1.1",
                              ) / \
                              Raw(load=response_body)
            wrpcap(pcap_file_path, response_packet, append=True)

            content_type = response['headers'].get('Content_Type', 'text/plain')

            # Handle binary content (images, etc.)
            if content_type.startswith('image/') or 'octet-stream' in content_type:
                decoded_body = packet_matcher.decode_body(response['body'])
                return send_file(
                    BytesIO(decoded_body),
                    mimetype=content_type
                )

            # Handle regular responses
            decoded_body = packet_matcher.decode_body(response['body'])
            if isinstance(decoded_body, bytes):
                decoded_body = decoded_body.decode('utf-8', errors='replace')

            flask_response = make_response(decoded_body)
            flask_response.content_type = content_type
            flask_response.status_code = int(response['status_code'])

            # Set headers
            for header, value in response['headers'].items():
                if header in ["Transfer_Encoding", "Content_Encoding", "Content_Length"]:
                    continue
                elif header == "Unknown_Headers":
                    for h, v in value.items():
                        flask_response.headers[h.replace('_', '-')] = v
                elif header in ['Set-Cookie', 'Set_Cookie']:
                    for cookie in value.split('§'):
                        cookie = cookie.strip()
                        if not cookie:
                            continue

                        parts = cookie.split('=', 1)
                        if len(parts) != 2:
                            continue

                        cookie_name, rest = parts
                        cookie_parts = rest.split(';')
                        cookie_value = cookie_parts[0]

                        kwargs = {}
                        for part in cookie_parts[1:]:
                            part = part.strip()
                            if '=' in part:
                                k, v = part.split('=', 1)
                                k = k.lower()
                                if k == 'expires':
                                    try:
                                        kwargs['expires'] = datetime.strptime(v, '%a, %d %b %Y %H:%M:%S %Z')
                                    except ValueError:
                                        continue
                                elif k == 'max-age':
                                    try:
                                        kwargs['max_age'] = int(v)
                                    except ValueError:
                                        continue
                                elif k == 'samesite':
                                    kwargs['samesite'] = v
                            elif part.lower() == 'httponly':
                                kwargs['httponly'] = True

                        flask_response.set_cookie(cookie_name, cookie_value, **kwargs)
                else:
                    flask_response.headers[header.replace('_', '-')] = value

            return flask_response

        # Add failure to JUnit report
        testcase = ET.Element('testcase', name=f'Alleged request {packet_matcher.request_number + 1}')
        failure = ET.Element('failure', message='No matching request found')
        failure.append(json_to_xml(incoming_request, initial_name='new'))
        testcase.append(failure)
        packet_matcher.testsuite.append(testcase)
        packet_matcher.save_junit_report()

        return jsonify({"error": "No matching packet found"}), 404

    return app


def run_server(packet_directory, host='0.0.0.0', port=80):
    app_name = packet_directory
    packet_directory = "resources/http/" + packet_directory
    app = create_app(packet_directory, app_name)

    pkt = os.listdir(packet_directory)
    try:
        pkt.remove("diff")
    except ValueError:
        pass
    print(f"Starting server on {host}:{port}")
    print(f"Using packets from directory: {packet_directory}")
    app.run(host=host, port=port, debug=True)