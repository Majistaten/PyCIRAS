"""This module provides functionality for data manipulation and processing."""
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from rich.pretty import pprint
import pandas as pd

import utility.util
from utility import config, util
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
# TODO refactor
# TODO mata in mer rådata
# TODO progress
def lint_data_to_csv(lint_data: dict, path: Path):
    """Processes lint data and updates an existing CSV file with new data, or writes new data to a CSV file."""

    flattened_data = []
    for repo, repo_data in lint_data.items():
        if repo_data is None:
            logging.error(f"Repository {repo} has no valid commits. Skipping repo")
            continue

        for commit_hash, commit_data in repo_data.items():
            if commit_data is None:
                logging.error(f"Commit {commit_hash} has no valid data. Skipping commit")
                continue

            commit_data.pop('messages', None)
            flat_data = _flatten_dict(commit_data)

            entry = {
                'repo': repo,
                'date': commit_data['date'],
                'commit_hash': commit_hash
            }

            # Add metrics to the entry
            for metric, value in flat_data.items():
                entry[metric] = value

            flattened_data.append(entry)

    new_df = pd.DataFrame(flattened_data)

    if new_df.empty:
        logging.warning("No data to process into DataFrame, skipping update")
        return

    if 'date' in new_df.columns:
        new_df['date'] = pd.to_datetime(new_df['date'], utc=True)

    new_df.drop(columns=[col for col in new_df.columns if
                         col.startswith('stats.by_module') or
                         col.startswith('stats.dependencies') or
                         col == 'stats.repository_name' or
                         col == 'stats.dependencies.util'],
                inplace=True,
                errors='ignore')

    # new_df.sort_values(by=['repo', 'date'], inplace=True)  # TODO redundant sortering?

    if path.exists():
        existing_df = pd.read_csv(path, parse_dates=['date'])
    else:
        existing_df = pd.DataFrame()

    if not existing_df.empty:
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        updated_df = updated_df.drop_duplicates(subset=['repo', 'date'], keep='last')
    else:
        updated_df = new_df

    fixed_cols = ['repo', 'date', 'commit_hash']
    cols = fixed_cols + [col for col in updated_df.columns if col not in fixed_cols]
    updated_df = updated_df[cols]
    updated_df.sort_values(by=['repo', 'date'], inplace=True)

    updated_df.to_csv(path, index=False, na_rep='nan')

# TODO mata in mer rådata
# TODO progress
def git_data_to_csv(git_data: dict, path: Path):
    """Loads existing git CSV data and updates it with new data, or writes new data to a CSV file."""

    flat_data = [_flatten_dict(repo, prefix_separator=".") for repo in git_data.values()]
    new_data_df = pd.DataFrame(flat_data)
    if path.exists():
        existing_data_df = pd.read_csv(path)
        updated_data_df = pd.concat([existing_data_df, new_data_df]).drop_duplicates('repo', keep='last')
    else:
        updated_data_df = new_data_df

    cols = ['repo'] + [col for col in sorted(updated_data_df.columns) if col != 'repo']
    updated_data_df = updated_data_df[cols]
    updated_data_df = updated_data_df.sort_values(by='repo')

    updated_data_df.to_csv(path, index=False, na_rep='nan')


# TODO få in commithashen också
# TODO mata in mer rådata förrutom summeringarna
# TODO sortera columner
# TODO progress
def test_data_to_csv(test_data: dict, path: Path):
    """Loads existing test CSV data and updates it with new data, or writes new data to a CSV file."""

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

    if path.exists():
        existing_df = pd.read_csv(path, parse_dates=['date'])
    else:
        existing_df = pd.DataFrame()

    if not existing_df.empty:
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        updated_df = updated_df.drop_duplicates(subset=['repo', 'date'], keep='last')
    else:
        updated_df = new_df

    fixed_cols = ['repo', 'date'] # TODO commit hash också
    cols = fixed_cols + [col for col in updated_df.columns if col not in fixed_cols]
    updated_df = updated_df[cols]
    updated_df.sort_values(by=['repo', 'date'], inplace=True)

    updated_df.to_csv(path, index=False, na_rep='nan')


# TODO progress
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


def metadata_to_csv(metadata: dict, path: Path):
    """Writes repo metadata to a CSV file."""

    data = [_flatten_dict(repo_metadata) for repo_metadata in metadata.values()]

    df = pd.DataFrame(data)

    with pd.option_context('future.no_silent_downcasting', True):
        df.replace('', np.nan, inplace=True)
    df['repo'] = df['resourcePath'].apply(util.get_repo_name_from_url_or_path)
    df['diskUsage'] = df['diskUsage'].apply(util.kb_to_mb_gb)
    date_fields = ['createdAt', 'pushedAt', 'updatedAt', 'archivedAt']
    df['languages.nodes'] = df['languages.nodes'].apply(
        lambda languages: tuple(sorted(lang['name'] for lang in languages)))
    for field in date_fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], utc=True, errors='coerce')

    cols = sorted(col for col in df.columns if col != 'repo')
    df = df[['repo'] + cols]
    df.sort_values(by='repo', inplace=True)

    df.to_csv(path, index=False, na_rep='nan')


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
