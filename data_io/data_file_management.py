"""This module provides functionality for file IO and directory management."""

from utility import config
from pathlib import Path
import csv
import json
from datetime import datetime
import data_io.data_management as data_converter
import pandas as pd

# TODO refactor date formatting etc to data_manipulation instead


# TODO ta bort när allt görs med pandas
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


# TODO flytta in i data_management
def make_data_directory() -> Path:
    """Creates a timestamped directory for the output data."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    data_dir = config.DATA_FOLDER / f'./{timestamp}'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# TODO flytta in i data_management och förenkla, kommer inte behöva custom encoder för att dumpa raw json
def write_json(new_data: dict, path: Path):
    """Loads existing JSON data and updates it with new data, or writes new data to a JSON file."""
    try:
        with open(path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    data.update(new_data)
    with open(path, 'w') as file:
        json.dump(data, file, indent=4, cls=CustomEncoder)


# TODO refaktorera bort sortering och mangling in i data_manipulation, gör CSV skrivningen där
def write_stargazers_csv(data: dict, path: Path):
    """Writes stargazers data to a CSV file."""

    repos = set()
    for date in data.values():
        repos.update(date.keys())

    repos = sorted(repos)

    with open(path, mode='w', newline='') as file:

        writer = csv.writer(file)
        writer.writerow(['date'] + repos)

        # Write data for each date
        for date, repo_stargazers in data.items():
            row = [date] + [repo_stargazers.get(repo, 0) for repo in repos]
            writer.writerow(row)
