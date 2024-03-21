"""This module provides functionality for data manipulation and processing."""

import json
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
import rich.progress
from rich.pretty import pprint
import pandas as pd
from utility import config, util
from utility.progress_bars import RichIterableProgressBar


class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Path objects, sets and datetime objects produced by Pydriller and Pylint"""

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
        with rich.progress.open(path, 'r', description=f'Reading {path}') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    data.update(new_data)
    with open(path, 'w') as file:
        json.dump(data, file, indent=4, cls=CustomEncoder)


# TODO mata in mer rådata
# TODO progress
def lint_data_to_csv(lint_data: dict, path: Path):
    """Write lint data to a CSV file."""

    flat_data = []
    for repo, repo_data in lint_data.items():
        if repo_data is None:
            logging.error(f"Repository {repo} has no valid commits. Skipping repo")
            continue

        for commit_hash, commit_data in repo_data.items():
            if commit_data is None:
                logging.error(f"Commit {commit_hash} has no valid data. Skipping commit")
                continue

            commit_data.pop('messages')
            flat_commit_data = _flatten_dict(commit_data)

            entry = {
                'repo': repo,
                'date': commit_data['date'],
                'commit_hash': commit_hash
            }

            for data_point, value in flat_commit_data.items():
                entry[data_point] = value

            flat_data.append(entry)

    df = pd.DataFrame(flat_data)

    if df.empty:
        logging.warning("No data to process into DataFrame, skipping update")
        return

    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.drop(columns=[col for col in df.columns if
                     col.startswith('stats.by_module') or
                     col.startswith('stats.dependencies') or
                     col == 'stats.repository_name' or
                     col == 'stats.dependencies.util'],
            inplace=True,
            errors='ignore')

    _update_csv(path, df, ['repo', 'date', 'commit_hash'])


# TODO mata in mer rådata
# TODO progress
def git_data_to_csv(git_data: dict, path: Path):
    """Write git data to a CSV file."""

    flat_data = [_flatten_dict(repo) for repo in git_data.values()]

    df = pd.DataFrame(flat_data)

    if path.exists():
        existing_df = pd.read_csv(path)
        updated_df = pd.concat([existing_df, df]).drop_duplicates('repo', keep='last')
    else:
        updated_df = df

    cols = ['repo'] + [col for col in sorted(updated_df.columns) if col != 'repo']
    updated_df = updated_df[cols]
    updated_df.sort_values(by='repo', inplace=True)

    updated_df.to_csv(path, index=False, na_rep='nan')


# TODO få in commithashen också
# TODO mata in mer rådata förrutom summeringarna
# TODO progress
def test_data_to_csv(test_data: dict, path: Path):
    """Write test data to a CSV file."""

    flat_data = [
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

    df = pd.DataFrame(flat_data)

    if df.empty:
        logging.warning("No data to process into DataFrame.")
        return

    _update_csv(path, df, ['repo', 'date'])  # TODO commit hash också?


# TODO progress
def stargazers_data_to_csv(stargazers_data: dict, path: Path):
    """Write stargazers data to a CSV file."""

    flat_data = [
        {
            'repo': repo,
            'date': edge['starredAt'],
            'user': edge['node']['login']
        }
        for repo, data in stargazers_data.items()
        for edge in data["data"]["repository"]["stargazers"]["edges"]
        if 'node' in edge and 'login' in edge['node'] and 'starredAt' in edge
    ]

    df = pd.DataFrame(flat_data)

    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.sort_values(by='date', inplace=True)
    df['stargazers_count'] = df.groupby('repo').cumcount() + 1
    df = df.pivot_table(index='date', columns='repo', values='stargazers_count', aggfunc='last')
    df = df.ffill()
    df = df.fillna(0).astype(int)

    df.reset_index(inplace=True)

    cols = ['date'] + [col for col in sorted(df.columns) if col != 'date']
    df = df[cols]

    df.to_csv(path, mode='w', index=False)


# TODO progress
def metadata_to_csv(metadata: dict, path: Path):
    """Write repo metadata to a CSV file."""

    flat_data = [_flatten_dict(repo_metadata) for repo_metadata in metadata.values()]

    df = pd.DataFrame(flat_data)

    date_fields = ['createdAt', 'pushedAt', 'updatedAt', 'archivedAt']
    for field in date_fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], utc=True, errors='coerce')

    df['repo'] = df['resourcePath'].apply(util.get_repo_name_from_url_or_path)
    df['diskUsage'] = df['diskUsage'].apply(util.kb_to_mb_gb)
    df['languages.nodes'] = df['languages.nodes'].apply(
        lambda languages: tuple(sorted(lang['name'] for lang in languages)))

    with pd.option_context('future.no_silent_downcasting', True):
        df.replace('', np.nan, inplace=True)

    cols = ['repo'] + [col for col in sorted(df.columns) if col != 'repo']
    df = df[cols]
    df.sort_values(by='repo', inplace=True)

    df.to_csv(path, mode='w', index=False, na_rep='nan')


def _flatten_dict(dictionary: dict, parent_key: str = '', prefix_separator: str = '.') -> dict:
    """Flattens a nested dict. Takes nested keys, and uses them as prefixes."""
    items = []
    for key, value in dictionary.items():

        new_key = parent_key + prefix_separator + str(key) if parent_key else str(key)
        if isinstance(value, dict):
            items.extend(_flatten_dict(value, new_key, prefix_separator=prefix_separator).items())
        else:
            items.append((new_key, value))

    return dict(items)


def _update_csv(path: Path, new_df: pd.DataFrame, fixed_cols: list[str]):
    """Loads existing CSV data and updates it with new data, or writes new data to a CSV file."""

    if path.exists():
        logging.info(f'Loading existing CSV from {path}')
        existing_df = pd.read_csv(path, parse_dates=['date'])
        logging.info(f'Done loading existing CSV from {path}')
    else:
        existing_df = pd.DataFrame()

    if not existing_df.empty:
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        updated_df = updated_df.drop_duplicates(subset=['repo', 'date'], keep='last')
    else:
        updated_df = new_df

    cols = fixed_cols + [col for col in sorted(updated_df.columns) if col not in fixed_cols]
    updated_df = updated_df[cols]
    updated_df.sort_values(by=['repo', 'date'], inplace=True)

    updated_df.to_csv(path, index=False, na_rep='nan')
