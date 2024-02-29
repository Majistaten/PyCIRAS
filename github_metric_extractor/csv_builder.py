from pathlib import Path
import csv
import json
from datetime import datetime
from collections.abc import MutableMapping


def write_pydriller_metrics_to_csv(metrics: dict) -> None:

    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    output_directory = Path(__file__).parent.parent / 'csv' / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)

    csv_file_name = 'pydriller.csv'
    csv_file_path = output_directory / csv_file_name



    # rad = repository
    # k/v pairs blir kolumner/celler

    headers = metrics.keys() #TODO vad ska bli headers? Hur få in repositories som rader, resten som kolumner?

    with open(csv_file_path, 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)

    return

    # Full path for the CSV file


def flatten_pydriller_metrics(metrics: dict) -> dict:

    flat_metrics = metrics
    for key, value in flat_metrics.items():
        flat_metrics[key].pop("commits")
        flat_metrics[key] = flatten_dict(value, sep="->")

    return flat_metrics


def flatten_pylint_metrics(metrics: dict) -> dict:

    flat_metrics = metrics
    for key, value in flat_metrics.items():
        for k, v in value.items():
            flat_metrics[key][k] = v if not isinstance(v, dict) else flatten_dict(v, sep="->")

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
