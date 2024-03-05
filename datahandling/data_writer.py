from utility import config, util
from pathlib import Path
import csv
import json
from datetime import datetime
from collections.abc import MutableMapping
import datahandling.data_converter as data_converter

# ROOT_PATH = Path(__file__).parent.parent


class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle sets and datetime objects."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def create_timestamped_data_directory() -> Path:
    """Creates a timestamped directory for the output data."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    # output_directory = ROOT_PATH / config.OUTPUT_FOLDER / config.DATA_FOLDER / f'./{timestamp}'
    output_directory = config.DATA_FOLDER / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def pydriller_data_json(data: dict, path: Path):
    """Writes Pydriller data to a JSON file."""
    output_path = path / 'pydriller_metrics.json'
    with open(str(output_path), 'a') as file:
        json.dump(data, file, indent=4)


def pylint_data_json(data: dict, path: Path):
    """Writes Pylint data to a JSON file."""
    output_path = path / 'pylint_metrics.json'
    with open(output_path, 'a') as file:
        json.dump(data, file, indent=4, cls=CustomEncoder)


def pydriller_data_csv(data: dict, path: Path):
    """Writes Pydriller data to a CSV file."""
    _write_to_csv(data, path / 'pydriller.csv')


def pylint_data_csv(data: MutableMapping, path: Path):
    """Writes Pylint data to a CSV file."""
    for key, value in data.items():
        output_path = path / f"pylint-{util.get_repo_name_from_path(key)}.csv"
        if value.values() is None:
            continue
        _write_to_csv(value, output_path)


def stargazers_data_json(data: dict, path: Path):
    """Writes stargazers data to a JSON file."""
    output_path = path / 'stargazers.json'
    with open(str(output_path), 'a') as file:
        json.dump(data, file, indent=4)


def _write_to_csv(data: MutableMapping, path: Path) -> None:
    """Writes the data to a CSV file."""
    formatted_data = data_converter.dict_to_list(data)
    with open(path, 'a', newline='') as file:
        field_names = set()
        for section in formatted_data:
            field_names.update([k for k in section.keys()])
        writer = csv.DictWriter(file, fieldnames=field_names)
        if path.stat().st_size == 0:
            writer.writeheader()
        writer.writerows(formatted_data)
