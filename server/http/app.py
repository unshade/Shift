from scapy.all import *
from scapy.layers.http import HTTP
from scapy.layers.inet import TCP, IP

# Create directory for storing captured packets
resources_dir = os.path.join(os.getcwd(), 'resources/http')
if not os.path.exists(resources_dir):
    os.makedirs(resources_dir)


def packet_callback(pak):
    if pak.haslayer(HTTP):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_name = f"packet_{timestamp}.json"
        file_path = os.path.join(resources_dir, file_name)

        print(pak)
        packet_data = {
            'source_ip': pak[IP].src,
            'destination_ip': pak[IP].dst,
            'source_port': pak[TCP].sport,
            'destination_port': pak[TCP].dport,
            #'method': pak[HTTP].Method.decode() if pak[HTTP].Method else None,
            #'path': pak[HTTP].Path.decode() if pak[HTTP].Path else None,
            'headers': dict(pak[HTTP].fields),
        }

        # Try to decode the payload if it exists
        if pak.haslayer(Raw):
            try:
                packet_data['body'] = pak[Raw].load.decode()
            except UnicodeDecodeError:
                packet_data['body'] = "Unable to decode payload"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(packet_data, f, ensure_ascii=False, indent=4)

        print(f"Captured HTTP packet: {file_name}")


def start_capture():
    print("Starting packet capture... Press Ctrl+C to stop.")
    sniff(filter="tcp port 80", prn=packet_callback, store=0)


if __name__ == '__main__':
    start_capture()
