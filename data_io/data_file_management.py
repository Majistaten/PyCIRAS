"""This module provides functionality for file IO and directory management."""

from utility import config
from pathlib import Path
import csv
import json
from datetime import datetime
import data_io.data_manipulation as data_converter
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


# TODO Refactor sorting and formatting to data_manipulation, fixa fixed column för repo namn. Sortera lite finare
# TODO flytta in i data_management gör CSV skrivningen där
def write_git_csv(new_data: dict, path: Path):
    """Loads existing git CSV data and updates it with new data, or writes new data to a CSV file."""

    new_data = data_converter.dict_to_list(new_data)
    with open(path, 'a', newline='') as file:
        column_names = set()
        for repo in new_data:
            column_names.update([data_point for data_point in repo.keys()])

        column_names = sorted(column_names)

        writer = csv.DictWriter(file, fieldnames=column_names, restval='nan') # TODO ska inte behöva bry sig om restvals här, få bort dictwriter?
        if path.stat().st_size == 0:
            writer.writeheader()

        writer.writerows(new_data)


# TODO refaktorera bort sortering och mangling in i data_manipulation, gör CSV skrivningen där
def write_lint_csv(data: dict, path: Path):
    """Writes lint data to separate CSV files for each repo."""

    for repo, dates in data.items():
        data_rows = []
        for date, lint_data in dates.items():
            row = {'date': date, **lint_data}
            data_rows.append(row)

        data_frame = pd.DataFrame(data_rows)
        data_frame['date'] = pd.to_datetime(data_frame['date'], utc=True)
        data_frame.sort_values(by='date', inplace=True)

        fixed_columns = ['date', 'commit_hash']
        other_columns = sorted([col for col in data_frame.columns if col not in fixed_columns])
        data_frame = data_frame[fixed_columns + other_columns]
        data_frame = data_frame.astype(str)

        data_frame.to_csv(path / f'lint-{repo}.csv', index=False)


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


# TODO refaktorera bort sortering och mangling in i data_manipulation, gör CSV skrivningen där
def write_test_csv(data: dict, path: Path):
    """Loads existing test data and updates it with new data, or writes new data to a CSV file."""

    try:
        existing_df = pd.read_csv(path, index_col='date', parse_dates=True)
    except FileNotFoundError:
        existing_df = pd.DataFrame()

    new_data = []
    for repo, dates in data.items():
        for date, test_data in dates.items():
            new_data.append({
                'date': date,
                repo: test_data.get('test-to-code-ratio')
            })

    new_df = pd.DataFrame(new_data)
    new_df['date'] = pd.to_datetime(new_df['date'], utc=True)
    new_df.set_index('date', inplace=True)

    if not existing_df.empty:
        updated_df = pd.merge(existing_df, new_df, left_index=True, right_index=True, how='outer')
    else:
        updated_df = new_df

    updated_df = updated_df.reindex(sorted(updated_df.columns), axis=1)
    updated_df.sort_index(inplace=True)
    updated_df = updated_df.astype(str)

    updated_df.to_csv(path)
