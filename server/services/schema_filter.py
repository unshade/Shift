def filter_data_by_schema(data, schema):
    """
    Filter the input data to only include fields specified in the schema.

    :param data: Input dictionary to filter
    :param schema: Schema dictionary specifying allowed fields
    :return: Filtered dictionary
    """
    if not isinstance(data, dict):
        return data

    filtered_data = {}
    for key, value in schema.items():
        if key in data:
            # If the value is True, include the entire field
            if value is True:
                filtered_data[key] = data[key]
            # If the value is a dictionary, recursively filter nested fields
            elif isinstance(value, dict):
                filtered_data[key] = filter_data_by_schema(data.get(key, {}), value)

    return filtered_data