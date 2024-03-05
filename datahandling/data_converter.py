from collections.abc import MutableMapping


def flatten_pydriller_data(metrics: dict) -> dict:
    """Flatten the Pydriller metrics to a single level dictionary."""
    flat_metrics = metrics
    for key, value in flat_metrics.items():
        flat_metrics[key] = _flatten_dict(value, sep=".")

    return flat_metrics


def flatten_pylint_data(metrics: dict) -> dict:
    """Flatten the Pylint metrics to a single level dictionary."""
    flat_metrics = metrics
    for key, value in flat_metrics.items():
        for k, v in value.items():
            flat_metrics[key][k] = v if not isinstance(v, dict) else _flatten_dict(v, sep=".")

    return flat_metrics


def flatten_stargazers_data(stargazers_metrics):
    pass


# TODO extrahera ut/ konvertera så man får en lista med dictionaries
# där key är owner/repo och value är listan som finns i edges
def clean_stargazers_data(stargazers_metrics):

    # cleaned_metrics = stargazers_metrics
    # for key in stargazers_metrics:
    #     if key is None:
    #         continue
    #     repository_data = key.get("repository")
    #     cleaned_metrics.append(repository_data)
    #
    # return cleaned_metrics

    cleaned_metrics = []
    for item in stargazers_metrics:
        # Extract repository data
        repository_data = item.get("data", {}).get("repository", {})
        name = repository_data.get("name")
        edges = repository_data.get("stargazers", {}).get("edges", [])

        # Create a new dictionary with 'name' as key and 'edges' as its value
        if name and edges:  # Ensure both name and edges are not empty
            cleaned_metrics.append({name: edges})

    return cleaned_metrics


#TODO convert to get a format suitable to achieve:
# Row: Datum Col: repository cell: stargazers
def get_stargazers_over_time(stargazers_metrics):
    pass


def remove_pylint_messages(data: dict) -> dict:
    """Removes the messages from the pylint data"""
    for repo, value in data.items():
        if value is None:
            continue
        for commit, v in value.items():
            if v is None:
                continue
            v.pop("messages")
    return data


def _flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    """
    Flatten a nested dictionary. Takes nested keys, and uses them as prefixes.
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, MutableMapping):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
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

