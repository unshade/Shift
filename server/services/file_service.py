import json
import os


def load_schema(app_name: str):
    try:
        init_folder('schema')

        schema_path = './schema/' + app_name + '.json'

        with open(schema_path, 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
    except FileNotFoundError:
        print("Schema file not found. Saving full data.")
        schema = {
            'request': True,
            'response': True
        }
    except json.JSONDecodeError:
        print("Error decoding schema file. Saving full data.")
        schema = {
            'request': True,
            'response': True
        }
    return schema

def init_folder(folder_type: str, app_name=None):
    path = None
    if folder_type == 'schema':
        path = './schema'

    if not os.path.exists(path):
        os.makedirs(path)