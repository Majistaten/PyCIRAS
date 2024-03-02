from pathlib import Path
import csv
import json
from github_metric_extractor import util
from datetime import datetime
from collections.abc import MutableMapping


def write_pydriller_metrics_to_csv(metrics: dict) -> None:

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_directory = Path(__file__).parent.parent / 'csv' / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)

    csv_file_name = 'pydriller.csv'
    csv_file_path = output_directory / csv_file_name
    write_to_csv(metrics, csv_file_path)

    return


def flatten_pydriller_metrics(metrics: dict) -> dict:

    flat_metrics = metrics
    for key, value in flat_metrics.items():
        flat_metrics[key] = flatten_dict(value, sep=".")

    return flat_metrics


def flatten_pylint_metrics(metrics: dict) -> dict:

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


def write_pylint_metrics_to_csv(metrics: MutableMapping):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_directory = Path(__file__).parent.parent / 'csv' / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)

    for key, value in metrics.items():
        csv_file_path = output_directory / f"pylint-{util.get_repo_name_from_path(key)}.csv"
        if value.values() is None:
            continue
        write_to_csv(value, csv_file_path)

    return


def write_to_csv(data: MutableMapping, filename: str | Path) -> None:
    formatted_data = reformat_dict_to_list(data)
    with open(filename, 'w', newline='') as csvfile:
        field_names = set()
        for section in formatted_data:
            field_names.update([k for k in section.keys()])
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(formatted_data)


def reformat_dict_to_list(dictionary: dict | MutableMapping) -> list:
    """Extracts all values from the dictionary, adds the keys and returns it wrapped in a list"""
    formatted_list = []
    for key, value in dictionary.items():
        if value is None:
            continue
        value["key"] = key
        formatted_list.append(value)
    return formatted_list


def read_json_from_file(file_path):
    """
    Read JSON data from a file using pathlib.

    :param file_path: Path to the JSON file, as a Path object.
    :return: A list of JSON objects.
    """
    with file_path.open('r', encoding='utf-8') as file:
        return json.load(file)


if __name__ == "__main__":
    pass
