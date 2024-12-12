def arrange_differences(original, new):
    diff = {}
    for key, value in original.items():
        if isinstance(value, dict):
            diff[key] = arrange_differences(value, new.get(key, {}))
        elif value != new.get(key):
            diff[key] = {'original': value, 'new': new.get(key)}
    return diff