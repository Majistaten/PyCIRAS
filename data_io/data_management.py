"""This module provides functionality for data manipulation and processing."""

import json
import logging
import threading
from datetime import datetime
from multiprocessing import current_process
from pathlib import Path

import numpy as np
import pandas as pd
from rich.progress import Progress

from utility import config, util

meta_lock = threading.Lock()
file_locks = {}


def get_lock_for_file(file_path: Path) -> threading.Lock:
    """Get a lock for a file path, creating one if it doesn't exist."""

    global meta_lock, file_locks

    with meta_lock:
        if file_path not in file_locks:
            logging.debug(f'{current_process().name} creating lock for file {file_path}')
            file_locks[file_path] = threading.Lock()

        logging.debug(f'{current_process().name} aquiring lock for file {file_path}')
        return file_locks[file_path]


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


def write_json(new_data: dict, path: Path, progress: Progress):
    """Loads existing JSON data and updates it with new data, or writes new data to a JSON file."""

    lock = get_lock_for_file(path)
    with lock:
        try:
            read_task = progress.add_task(f'Reading JSON: {util.absolute_data_path_to_relative(str(path))}', total=None)
            with open(path, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}
        progress.stop_task(read_task)
        progress.remove_task(read_task)

        data.update(new_data)

        write_task = progress.add_task(f'Writing JSON: {util.absolute_data_path_to_relative(str(path))}', total=None)
        with open(path, 'w') as file:
            json.dump(data, file, indent=4, cls=CustomEncoder)
        progress.stop_task(write_task)
        progress.remove_task(write_task)


def lint_data_to_csv(lint_data: dict, path: Path, progress: Progress):
    """Write lint data to a CSV file."""

    processing_task = progress.add_task(f'Processing Data: {util.get_repo_name_from_url_or_path(path)}', total=None)

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
        logging.info("\nNo lint data to process into DataFrame")
        return

    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.drop(columns=[col for col in df.columns if
                     col.startswith('stats.by_module') or
                     col.startswith('stats.dependencies') or
                     col.startswith('stats.duplicated_lines') or
                     col == 'stats.repository_name' or
                     col == 'stats.dependencies.util'],
            inplace=True,
            errors='ignore')

    df.columns = [col.replace('stats.', '') for col in df.columns]
    df.columns = [col.replace('by_msg.', '') for col in df.columns]

    progress.stop_task(processing_task)
    progress.remove_task(processing_task)

    fixed_columns = [
        'repo',
        'date',
        'commit_hash',
        'info',
        'refactor',
        'convention',
        'warning',
        'error',
        'fatal',
        'global_note',
        'avg_mccabe_complexity',
        'percent_duplicated_lines',
        'nb_duplicated_lines',
        'statement'
    ]

    prefixes_dynamic_fixed_columns = ['undocumented', 'bad_names', 'code_type', 'node_count']
    fixed_dynamic_columns = sorted([col for col in df.columns if
                                    any(col.startswith(prefix) for prefix in prefixes_dynamic_fixed_columns)])

    _update_csv(path, df, fixed_columns + fixed_dynamic_columns, progress)


# TODO mata in mer rådata
def git_data_to_csv(git_data: dict, path: Path, progress: Progress):
    """Write git data to a CSV file."""

    processing_task = progress.add_task(f'Processing Data: {util.get_repo_name_from_url_or_path(path)}', total=None)

    dict_nested_keys = ['lines_count', 'hunks_count', 'contributors_experience', 'contributors_count',
                        'history_complexity', 'code_churn']
    for repo, data in git_data.items():
        for key in dict_nested_keys:
            data.pop(key, None)

    flat_data = [_flatten_dict(repo) for repo in git_data.values()]

    df = pd.DataFrame(flat_data)

    if df.empty:
        logging.info("\nNo git data to process into DataFrame.")
        return

    progress.stop_task(processing_task)
    progress.remove_task(processing_task)

    lock = get_lock_for_file(path)
    with lock:
        if path.exists():
            read_task = progress.add_task(f'Reading CSV: {util.absolute_data_path_to_relative(str(path))}', total=None)
            existing_df = pd.read_csv(path)
            progress.stop_task(read_task)
            progress.remove_task(read_task)
            updated_df = pd.concat([existing_df, df]).drop_duplicates('repo', keep='last')
        else:
            updated_df = df

        write_task = progress.add_task(f'Writing CSV: {util.absolute_data_path_to_relative(str(path))}', total=None)
        updated_df = _sort_rows_and_cols(updated_df, ['repo'], ['repo'])
        updated_df.to_csv(path, mode='w', index=False, na_rep='nan')
        progress.stop_task(write_task)
        progress.remove_task(write_task)


# TODO få in commithashen också
# TODO mata in mer rådata förrutom summeringarna
def test_data_to_csv(test_data: dict, path: Path, progress: Progress):
    """Write test data to a CSV file."""

    processing_task = progress.add_task(f'Processing Data: {util.get_repo_name_from_url_or_path(path)}', total=None)

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
        logging.info("\nNo test data to process into DataFrame.")
        return

    progress.stop_task(processing_task)
    progress.remove_task(processing_task)

    _update_csv(path, df, ['repo', 'date'], progress)  # TODO commit hash också?


def stargazers_data_to_csv(stargazers_data: dict, path: Path, progress):
    """Write stargazers data to a CSV file."""

    processing_task = progress.add_task(f'Processing Data: {util.get_repo_name_from_url_or_path(path)}', total=None)

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

    if df.empty:
        logging.info("\nNo stargazers data to process into DataFrame.")
        return

    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.sort_values(by='date', inplace=True)
    df['stargazers_count'] = df.groupby('repo').cumcount() + 1
    df = df.pivot_table(index='date', columns='repo', values='stargazers_count', aggfunc='last')
    df = df.ffill()
    df = df.fillna(0).astype(int)

    df.reset_index(inplace=True)
    df = _sort_cols(df, ['date'])

    progress.stop_task(processing_task)
    progress.remove_task(processing_task)

    write_task = progress.add_task(f'Writing CSV: {util.absolute_data_path_to_relative(str(path))}', total=None)
    df.to_csv(path, mode='w', index=False)
    progress.stop_task(write_task)
    progress.remove_task(write_task)


def metadata_to_csv(metadata: dict, path: Path, progress: Progress):
    """Write repo metadata to a CSV file."""

    processing_task = progress.add_task(f'Processing Data: {util.get_repo_name_from_url_or_path(path)}', total=None)

    flat_data = [_flatten_dict(repo_metadata) for repo_metadata in metadata.values()]

    df = pd.DataFrame(flat_data)

    if df.empty:
        logging.info("\nNo metadata to process into DataFrame.")
        return

    date_fields = ['createdAt', 'pushedAt', 'updatedAt', 'archivedAt']
    for field in date_fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], utc=True, errors='coerce')

    df['repo'] = df['resourcePath'].apply(util.get_repo_name_from_url_or_path)
    df['diskUsage'] = df['diskUsage'].apply(util.kb_to_mb)

    df['languages.nodes'] = df.apply(
        lambda row: _calculate_language_percentages(row['languages.edges'], row['languages.totalSize']), axis=1
    )
    df = df.rename(columns={'languages.nodes': 'languages'})
    df = df.drop(['languages.edges', 'languages.totalSize'], axis=1)

    with pd.option_context('future.no_silent_downcasting', True):
        df.replace('', np.nan, inplace=True)

    df = _sort_rows_and_cols(df, ['repo'], ['repo'])

    progress.stop_task(processing_task)
    progress.remove_task(processing_task)

    write_task = progress.add_task(f'Writing CSV: {util.absolute_data_path_to_relative(str(path))}', total=None)
    df.to_csv(path, mode='w', index=False, na_rep='nan')
    progress.stop_task(write_task)
    progress.remove_task(write_task)


def _calculate_language_percentages(languages_edges, total_size):
    if total_size > 0:
        return [(edge['node']['name'], round((edge['size'] / total_size) * 100, 1)) for edge in languages_edges]
    return []


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


def _update_csv(path: Path, new_df: pd.DataFrame, fixed_cols: list[str], progress):
    """Loads existing CSV data and updates it with new data, or writes new data to a CSV file."""

    lock = get_lock_for_file(path)
    with lock:
        if path.exists():
            read_task = progress.add_task(f'Reading CSV: {util.absolute_data_path_to_relative(str(path))}', total=None)
            existing_df = pd.read_csv(path, parse_dates=['date'])
            progress.stop_task(read_task)
            progress.remove_task(read_task)
        else:
            existing_df = pd.DataFrame()

        write_task = progress.add_task(f'Writing CSV: {util.absolute_data_path_to_relative(str(path))}', total=None)
        if not existing_df.empty:
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df = updated_df.drop_duplicates(subset=['repo', 'date'], keep='last')
        else:
            updated_df = new_df

        updated_df = _sort_rows_and_cols(updated_df, ['repo', 'date'], fixed_cols)

        updated_df.to_csv(path, index=False, na_rep='nan')
        progress.stop_task(write_task)
        progress.remove_task(write_task)


def _sort_rows_and_cols(df: pd.DataFrame, sort_rows_by: list[str], fixed_cols: list[str]):
    """Sorts rows and columns in a DataFrame."""
    df = _sort_cols(df, fixed_cols)
    df.sort_values(sort_rows_by, inplace=True)
    return df


def _sort_cols(df: pd.DataFrame, fixed_cols: list[str]):
    """Sorts columns in a DataFrame, with fixed columns first."""
    return df[fixed_cols + [col for col in sorted(df.columns) if col not in fixed_cols]]
