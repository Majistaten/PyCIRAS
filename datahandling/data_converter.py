from collections.abc import MutableMapping


def flatten_pydriller_data(metrics: dict) -> dict:
    flat_metrics = metrics
    for key, value in flat_metrics.items():
        flat_metrics[key] = flatten_dict(value, sep=".")

    return flat_metrics


def flatten_pylint_data(metrics: dict) -> dict:
    flat_metrics = metrics
    for key, value in flat_metrics.items():
        for k, v in value.items():
            flat_metrics[key][k] = v if not isinstance(v, dict) else flatten_dict(v, sep=".")

    return flat_metrics


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    """
    Flatten a nested dictionary. Takes nested keys, and uses them as prefixes.
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def dict_to_list(dictionary: dict | MutableMapping) -> list:
    """Extracts all values from the dictionary, adds the keys and returns it wrapped in a list"""
    formatted_list = []
    for key, value in dictionary.items():
        if value is None:
            continue
        value["key"] = key
        formatted_list.append(value)
    return formatted_list
