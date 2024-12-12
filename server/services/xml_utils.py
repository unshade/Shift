import xml.etree.ElementTree as ET

def json_to_xml(json_data, parent=None, initial_name=None):
    if parent is None:
        if initial_name:
            parent = ET.Element(initial_name)
        else:
            parent = ET.Element('root')
    for key, value in json_data.items():
        if isinstance(value, dict):
            child = ET.Element(key)
            parent.append(child)
            json_to_xml(value, child)
        else:
            child = ET.Element(key)
            child.text = str(value)
            parent.append(child)
    return parent