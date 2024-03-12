from utility import config, util
from pathlib import Path
import csv
import json
from datetime import datetime
from collections.abc import MutableMapping
import datahandling.data_converter as data_converter


class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle sets and datetime objects."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        elif isinstance(obj, Path):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def create_timestamped_data_directory() -> Path:
    """Creates a timestamped directory for the output data."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_directory = config.DATA_FOLDER / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def write_json_data(data: dict, path: Path):
    """Loads existing JSON data and updates it with new data, or writes new data to a JSON file."""
    try:
        with open(path, 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = {}

    existing_data.update(data)

    with open(path, 'w') as file:
        json.dump(existing_data, file, indent=4, cls=CustomEncoder)


def pydriller_data_csv(data: dict, path: Path):
    """Writes Pydriller data to a CSV file."""
    _write_to_csv(data, path / 'pydriller-flat.csv', None)


def pylint_data_csv(data: MutableMapping, path: Path):
    """Writes Pylint data to a CSV file."""
    for key, value in data.items():
        output_path = path / f"pylint-{util.get_repo_name_from_path(key)}.csv"
        if value.values() is None:
            continue
        _write_to_csv(value, output_path, insert_key_as="commit_hash")


def stargazers_data_csv(data: dict, path: Path) -> None:
    """Writes stargazers over time to a CSV file."""

    # Determine all unique repositories to establish the columns (other than the DATE column)
    repos = set()
    for day_data in data.values():
        repos.update(day_data.keys())
    repos = sorted(repos)  # Sort repositories for consistent column order

    with open(path / 'stargazers-over-time.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write the header
        writer.writerow(['DATE'] + repos)

        # Write data for each date
        for date, data in data.items():
            row = [date] + [data.get(repo, 0) for repo in repos]
            writer.writerow(row)


def _write_to_csv(data: MutableMapping, path: Path, insert_key_as: str | None) -> None:
    """Writes the data to a CSV file."""
    formatted_data = data_converter.dict_to_list(data, insert_key_as)
    with open(path, 'a', newline='') as file:
        field_names = set()
        for section in formatted_data:
            field_names.update([k for k in section.keys()])
        writer = csv.DictWriter(file, fieldnames=field_names)
        if path.stat().st_size == 0:
            writer.writeheader()
        writer.writerows(formatted_data)
