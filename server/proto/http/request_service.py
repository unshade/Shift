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