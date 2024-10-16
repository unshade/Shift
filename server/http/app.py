from flask import Flask, request
import json
import os
from datetime import datetime

app = Flask(__name__)

resources_dir = os.path.join(os.getcwd(), 'resources/http')
if not os.path.exists(resources_dir):
    os.makedirs(resources_dir)

@app.before_request
def log_request():
    request_data = {
        'method': request.method,
        'path': request.path,
        'headers': dict(request.headers),
        'body': request.get_data(as_text=True) if request.data else None,
        'GET_params': request.args.to_dict(),
        'POST_params': request.form.to_dict(),
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"request_{timestamp}.json"
    file_path = os.path.join(resources_dir, file_name)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(request_data, f, ensure_ascii=False, indent=4)

@app.route('/status')
def index():
    return "Running"

if __name__ == '__main__':
    app.run(debug=True, port=80, host='0.0.0.0')