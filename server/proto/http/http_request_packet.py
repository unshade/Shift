from services.schema_filter import filter_data_by_schema


class HttpRequestPacket:
    def __init__(self, source_ip, destination_ip, source_port, destination_port, method, path, headers):
        self.body = None
        self.schema = None
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.source_port = source_port
        self.destination_port = destination_port
        self.method = method
        self.path = path
        self.headers = headers

    def add_body(self, body):
        self.body = body

    def add_schema(self, schema):
        self.schema = schema

    def to_dict(self):
        return {
            'source_ip': self.source_ip,
            'destination_ip': self.destination_ip,
            'source_port': self.source_port,
            'destination_port': self.destination_port,
            'method': self.method,
            'path': self.path,
            'headers': self.headers,
            'body': self.body
        }

    def to_filtered_dict(self):
        return filter_data_by_schema(self.to_dict(), self.schema)

    def __eq__(self, other):
        """
        Compare two HttpPacket objects.
        :param other: The other HttpPacket object
        :param schema: Optional schema to filter the comparison
        :return: True if the objects are equal, False otherwise
        """

        if not self.schema:
            return self.to_dict() == other.to_dict()

        self_filtered = filter_data_by_schema(self.to_dict(), self.schema)
        other_filtered = filter_data_by_schema(other.to_dict(), self.schema)

        print('Comparing : ', self_filtered, other_filtered)

        return self_filtered == other_filtered