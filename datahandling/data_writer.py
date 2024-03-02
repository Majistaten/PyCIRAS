import config
from pathlib import Path
import csv
import json
from github_metric_extractor import util
from datetime import datetime
from collections.abc import MutableMapping

ROOT_PATH = Path(__file__).parent.parent


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def create_timestamped_data_directory() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_directory = ROOT_PATH / config.OUTPUT_FOLDER / config.DATA_FOLDER / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def pydriller_data_json(data: dict, path: Path):
    output_path = path / 'pydriller_metrics.json'
    with open(str(output_path), 'w') as file:
        json.dump(data, file, indent=4)


def pylint_data_json(data: dict, path: Path):
    output_path = path / 'pylint_metrics.json'
    with open(output_path, 'w') as file:
        json.dump(data, file, indent=4, cls=CustomEncoder)


def pydriller_data_csv(data: dict, path: Path):
    write_to_csv(data, path / 'pydriller.csv')


# TODO varför mutablemapping?
def pylint_data_csv(data: MutableMapping, path: Path):
    for key, value in data.items():
        output_path = path / f"pylint-{util.get_repo_name_from_path(key)}.csv"
        if value.values() is None:
            continue
        write_to_csv(value, output_path)


def write_to_csv(data: MutableMapping, path: Path) -> None:
    formatted_data = reformat_dict_to_list(data)
    with open(path, 'w', newline='') as file:
        field_names = set()
        for section in formatted_data:
            field_names.update([k for k in section.keys()])
        writer = csv.DictWriter(file, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(formatted_data)


# TODO refactor to data formatter
def reformat_dict_to_list(dictionary: dict | MutableMapping) -> list:
    """Extracts all values from the dictionary, adds the keys and returns it wrapped in a list"""
    formatted_list = []
    for key, value in dictionary.items():
        if value is None:
            continue
        value["key"] = key
        formatted_list.append(value)
    return formatted_list