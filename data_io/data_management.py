"""This module provides functionality for data manipulation and processing."""
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


def flatten_git_data(data: dict) -> dict:
    """Flatten git data metrics to a single level dict."""

    flat_data = data
    for key, value in flat_data.items():
        flat_data[key] = _flatten_dict(value, prefix_separator=".")

    return flat_data


# TODO flytta in denna i den stora funktionen med enbart pandas
def clean_stargazers_data(data: dict) -> dict:
    """Cleans stargazers data using pandas."""

    clean_data = {}
    for repo, stargazers_data in data.items():
        edges = stargazers_data.get("data", {}).get("repository", {}).get("stargazers", {}).get("edges", [])

        if edges:
            data_frame = pd.DataFrame(edges)
            data_frame['login'] = data_frame['node'].apply(lambda x: x.get('login'))
            starred = data_frame.set_index('login')['starredAt'].to_dict()
            clean_data[repo] = starred
        else:
            clean_data[repo] = {}

    return clean_data


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


# TODO gör allt innan detta i en och samma funktion med enbart pandas och skriv direkt till CSV
def stargazers_over_time(stargazers_data: dict) -> dict:
    """Accumulates stargazers over time based on clean stargazers data"""

    # TODO refaktorera in och förenkla, enbart pandas
    # clean_stargazers_data
    # write_stargazers_csv

    data = []
    for repo, stargazers in stargazers_data.items():
        if stargazers:
            for user, date in stargazers.items():
                data.append({'repo': repo, 'date': pd.to_datetime(date, utc=True), 'user': user})
        else:
            logging.error(f"Repository {repo} has no stargazers data. Skipping stargazers over time for this repo.")

    data_frame = pd.DataFrame(data)
    data_frame.sort_values(by='date', inplace=True)
    data_frame['stargazers_count'] = data_frame.groupby('repo').cumcount() + 1
    data_frame = data_frame.pivot_table(index='date', columns='repo', values='stargazers_count', aggfunc='last')
    data_frame.ffill(inplace=True)
    data_frame.index = data_frame.index.astype(str)

    return data_frame.to_dict('index')


def get_test_data_over_time(test_data: dict) -> dict:
    """Gets the test-to-code-ratio over time for each repository."""

    # TODO refaktorera in och förenkla, enbart pandas
    # write_test_csv

    aggregated_data = []
    for repo, commits in test_data.items():
        for commit_hash, data in commits.items():
            try:
                test_to_code_ratio = data['test-to-code-ratio']
                test_frameworks = set()
                test_classes = 0
                test_functions = 0
                for file_data in data['files'].values():
                    test_frameworks.update(file_data.get('imports', []))
                    test_classes += len(file_data.get('unittest_classes', []))
                    test_functions += len(file_data.get('pytest_functions', []))

                aggregated_data.append({
                    'repo': repo,
                    'date': pd.to_datetime(data['date'], utc=True),
                    'test-to-code-ratio': test_to_code_ratio,
                    'test-frameworks': sorted(test_frameworks),
                    'test-classes': test_classes,
                    'test-functions': test_functions
                })

            except Exception as e:
                logging.error(f"Error processing metrics for {repo} commit {commit_hash}: {e}"
                              f"\nSkipping this commit.")
                continue

    data_frame = pd.DataFrame(aggregated_data)

    if data_frame.empty:
        logging.warning("No data to process into DataFrame.")
        return {}

    data_frame['date'] = pd.to_datetime(data_frame['date'], utc=True)
    data_frame.sort_values(by=['repo', 'date'], inplace=True)
    data_frame['date'] = data_frame['date'].astype(str)
    data_frame.set_index(['repo', 'date'], inplace=True)

    result_dict = data_frame.groupby(level=0).apply(lambda df: df.xs(df.name).to_dict(orient='index')).to_dict()
    return result_dict


# TODO ta bort när allt görs i pandas
def dict_to_list(dictionary: dict) -> list:
    """Extracts all values from the dictionary, adds the keys and returns it wrapped in a list"""
    formatted_list = []
    for key, value in dictionary.items():
        if value is None:
            continue
        formatted_list.append(value)
    return formatted_list
