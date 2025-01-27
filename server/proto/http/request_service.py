def decode_headers(headers):
    decoded_headers = {}
    for k, v in headers.items():
        if isinstance(k, bytes):
            k = k.decode()
        if isinstance(v, bytes):
            v = v.decode()
        elif isinstance(v, dict):
            v = decode_headers(v)
        # If this is a Cookie and there is already a Set-Cookie header, append the new value
        if 'cookie' in k.lower() and k in decoded_headers:
            decoded_headers[k] += f"§ {v}"
        else:
            decoded_headers[k] = v
    return decoded_headers
