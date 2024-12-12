import os
import json
from flask import Flask, request, jsonify
import logging

class PacketMatcher:
    def __init__(self, packet_directory):
        """
        Initialize the packet matcher with packets from a given directory.
        
        :param packet_directory: Directory containing JSON packet files
        """
        self.packets = []
        self.load_packets(packet_directory)
        self.request_number = 0

    def compare_packets(self, incoming_request):
        if self.request_number >= len(self.packets):
            print("All requests compared")
            return None

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
