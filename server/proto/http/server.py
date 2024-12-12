import os
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from datetime import datetime

from flask import Flask, request, jsonify
import logging

from proto.http.http_request_packet import HttpRequestPacket
from services.dict_utils import arrange_differences
from services.file_service import load_schema
from services.schema_filter import filter_data_by_schema
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
        if self.request_number >= len(self.packets):
            print("All requests compared")
            rough_string = ET.tostring(self.testsuite, 'utf-8')
            beautified = minidom.parseString(rough_string)
            pretty_xml_as_string = beautified.toprettyxml(indent="  ")

            report_path = os.path.join(self.compare_path, 'junit_report.xml')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml_as_string)
            print(f'JUnit report generated at {report_path}')
            exit(0)

        original_packet = self.packets[self.request_number]

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
            source_port=incoming_request['source_port'],
            destination_port=incoming_request['destination_port'],
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




    def load_packets(self, directory):
        """
        Load all JSON packet files from the specified directory.
        
        :param directory: Path to the directory containing packet JSON files
        """
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, 'r') as f:
                        packet = json.load(f)
                        self.packets.append(packet)
                except Exception as e:
                    print(f"Error loading packet {filename}: {e}")
        
        print(f"Loaded {len(self.packets)} packets")
    
    def find_matching_packet(self, incoming_request):
        """
        Find a matching pre-recorded packet for the incoming request.
        
        :param incoming_request: Flask request object
        :return: Matching packet or None
        """
        for packet in self.packets:
            req = packet.get('request', {})
            
            # Check method
            if req.get('method') != incoming_request.method:
                continue
            
            # Check path
            if req.get('path') != incoming_request.path:
                continue
            
            # Optional: Add more matching criteria here
            # For example, check specific headers or other request details
            
            return packet
        
        return None

def create_app(packet_directory):
    """
    Create and configure the Flask application.
    
    :param packet_directory: Directory containing JSON packet files
    :return: Configured Flask app
    """
    # Disable Flask's default logging to reduce noise
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app = Flask(__name__)
    packet_matcher = PacketMatcher(packet_directory)
    
    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def catch_all(path):
        """
        Catch-all route to match any incoming request against pre-recorded packets.
        
        :param path: The requested path
        :return: Matched response or 404
        """
        # Print the received packet
        print(request)
        # Check if there's a matching packet
        matching_packet = packet_matcher.find_matching_packet(request)
        
        if matching_packet:
            # Extract response from the matching packet
            response_data = matching_packet.get('response', {})
            
            # Create Flask response
            response_body = response_data.get('body', '')
            response = app.response_class(
                response=response_body,
                status=int(response_data.get('status_code', 200)),
                mimetype='application/json'
            )
            
            # Add headers from the original packet
            headers = response_data.get('headers', {})
            for header, value in headers.items():
                # Skip some internal headers
                if header.lower() not in ['status_code', 'reason_phrase', 'http_version']:
                    # Convert header names to standard HTTP header format
                    formatted_header = header.replace('_', '-')
                    response.headers[formatted_header] = str(value)
            
            return response
        
        # If no matching packet found
        return jsonify({"error": "No matching packet found"}), 404
    
    return app


def run_server(packet_directory, host='0.0.0.0', port=80):
    """
    Run the Flask server with pre-recorded packets.
    
    :param packet_directory: Directory containing JSON packet files
    :param host: Host to bind the server to (default: 0.0.0.0)
    :param port: Port to run the server on (default: 80)
    """
    packet_directory = "resources/http/"+packet_directory
    app = create_app(packet_directory)
    print(f"Starting server on {host}:{port}")
    print(f"Using packets from directory: {packet_directory}")
    app.run(host=host, port=port)
