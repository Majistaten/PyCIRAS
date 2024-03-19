"""This module provides functionality for data manipulation and processing."""
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from rich.pretty import pprint
import pandas as pd
from utility import config
from utility.progress_bars import RichIterableProgressBar


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


def make_data_directory() -> Path:
    """Creates a timestamped directory for the output data."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    data_dir = config.DATA_FOLDER / f'./{timestamp}'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


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


# TODO fixa så att alla rader ligger i samma CSV, med repo/date som index
def lint_data_to_csv(lint_data: dict, path: Path):
    """
    Processes lint data and writes it to CSV files, one per repository.

    Parameters:
    - lint_data: A dictionary containing lint data for multiple repositories.
    - output_dir: The directory where the CSV files will be saved.
    """

    for repo, repo_data in RichIterableProgressBar(lint_data.items(),
                                                   description="Processing lint data",
                                                   disable=config.DISABLE_PROGRESS_BARS):
        if repo_data is None:
            continue

        data_list = []
        for commit_hash, commit_data in repo_data.items():
            if commit_data is None:
                continue

            commit_data.pop('messages', None)
            flattened_data = _flatten_dict(commit_data)

            for metric, value in flattened_data.items():
                data_list.append({'commit_hash': commit_hash, 'metric': metric, 'value': value})

        df = pd.DataFrame(data_list)

        if df.empty:
            logging.error(f"Repository {repo} has no valid commits. Skipping...")
            continue

        df_formatted = df.pivot_table(index=['commit_hash'],
                                      columns='metric',
                                      values='value',
                                      aggfunc='first').reset_index()

        df_formatted.columns.name = None
        df_formatted.reset_index(drop=True, inplace=True)

        df_formatted.drop(columns=[col for col in df_formatted.columns if
                                   col.startswith('stats.by_module') or
                                   col.startswith('stats.dependencies') or
                                   col == 'stats.repository_name' or
                                   col == 'stats.dependencies.util'],
                          inplace=True,
                          errors='ignore')

        if 'date' in df_formatted.columns:
            df_formatted['date'] = pd.to_datetime(df_formatted['date'], utc=True)
            df_formatted.sort_values(by='date', inplace=True)
            cols = ['date', 'commit_hash'] + [col for col in df_formatted.columns if col not in ['date', 'commit_hash']]
            df_formatted = df_formatted[cols]

        df_formatted.to_csv(path / f'lint-{repo}.csv', index=False, na_rep='nan')


def git_data_to_csv(git_data: dict, path: Path):
    """Loads existing git CSV data and updates it with new data, or writes new data to a CSV file."""

    flat_data = [_flatten_dict(repo, prefix_separator=".") for repo in git_data.values()]
    new_data_df = pd.DataFrame(flat_data)
    if Path(path).exists():
        existing_data_df = pd.read_csv(path)
        updated_data_df = pd.concat([existing_data_df, new_data_df]).drop_duplicates('repository_name', keep='last')
    else:
        updated_data_df = new_data_df

    cols = ['repository_name'] + [col for col in sorted(updated_data_df.columns) if col != 'repository_name']
    updated_data_df = updated_data_df[cols]
    updated_data_df = updated_data_df.sort_values(by='repository_name')

    updated_data_df.fillna('nan').to_csv(path, index=False)


def test_data_to_csv(test_data: dict, path: Path):
    """Loads existing test CSV data and updates it with new data, or writes new data to a CSV file."""

    # pprint(test_data)

    flattened_data = [
        {
            'repo': repo,
            'date': pd.to_datetime(data['date'], utc=True),
            'test-to-code-ratio': data['test-to-code-ratio'],
            'test-frameworks': tuple(sorted(set([
                import_name for file_data in data['files'].values() for import_name in file_data.get('imports', [])
            ]))),
            'test-classes': sum(len(file_data.get('unittest_classes', [])) for file_data in data['files'].values()),
            'test-functions': sum(len(file_data.get('pytest_functions', [])) for file_data in data['files'].values()),
        }
        for repo, commits in test_data.items()
        for commit_hash, data in commits.items()
    ]

    new_df = pd.DataFrame(flattened_data)

    if new_df.empty:
        logging.warning("No data to process into DataFrame.")
        return

    new_df.sort_values(by=['repo', 'date'], inplace=True)
    new_df.set_index(['repo', 'date'], inplace=True)

    try:
        existing_df = pd.read_csv(path, index_col=['repo', 'date'], parse_dates=['date'])
    except FileNotFoundError:
        existing_df = pd.DataFrame()

    if not existing_df.empty:
        existing_df = existing_df.reset_index()
        new_df = new_df.reset_index()
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        updated_df.sort_values(by=['repo', 'date'], inplace=True)
        updated_df = updated_df.drop_duplicates(subset=['repo', 'date'], keep='last')
        updated_df.set_index(['repo', 'date'], inplace=True)
    else:
        updated_df = new_df

    updated_df.to_csv(path)


def stargazers_data_to_csv(stargazers_data: dict, path: Path):
    """Writes stargazers data to a CSV file. Needs to be filtered by repo creation date"""

    rows_list = []
    for repo, data in stargazers_data.items():
        edges = data.get("data", {}).get("repository", {}).get("stargazers", {}).get("edges", [])
        for edge in edges:
            if 'node' in edge and 'login' in edge['node'] and 'starredAt' in edge:
                rows_list.append({'repo': repo, 'date': edge['starredAt'], 'user': edge['node']['login']})

    df = pd.DataFrame(rows_list)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.sort_values(by='date', inplace=True)
    df['stargazers_count'] = df.groupby('repo').cumcount() + 1
    df = df.pivot_table(index='date', columns='repo', values='stargazers_count', aggfunc='last').ffill()

    df.to_csv(path, mode='w', na_rep=0.0)


def _flatten_dict(dictionary: dict, parent_key: str = '', prefix_separator: str = '.') -> dict:
    """Flatten a nested dict. Takes nested keys, and uses them as prefixes."""
    items = []
    for key, value in dictionary.items():

        new_key = parent_key + prefix_separator + str(key) if parent_key else str(key)
        if isinstance(value, dict):
            items.extend(_flatten_dict(value, new_key, prefix_separator=prefix_separator).items())
        else:
            items.append((new_key, value))

    return dict(items)
