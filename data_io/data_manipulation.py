"""This module provides functionality for data manipulation and processing."""

import logging
from rich.pretty import pprint
import pandas as pd


# TODO städa upp och refaktorera, sedan flytta all skrivning in i dessa funktioner istället och migrera hit
# alla andra funktioner från data_file_management och ta bort filen.
# gör alla skrivningar till csv och json med pandas, kolla om man kan köra flatten också med pandas
# Döp om till data_management.py


def flatten_git_data(data: dict) -> dict:
    """Flatten git data metrics to a single level dict."""

    flat_data = data
    for key, value in flat_data.items():
        flat_data[key] = _flatten_dict(value, prefix_separator=".")

    return flat_data


def flatten_lint_data(metrics: dict) -> dict:
    """Flatten lint data to a single level dict."""

    flat_data = metrics
    for key, value in flat_data.items():
        for k, v in value.items():
            flat_data[key][k] = v if not isinstance(v, dict) else _flatten_dict(v, prefix_separator=".")

    return flat_data


def clean_lint_data(data: dict) -> dict:
    """Swaps to use date as key for commits, cleans lint data."""

    clean_data = {}
    for repo, commits in data.items():
        commit_list = [{"commit_hash": commit_hash, **commit_info} for commit_hash, commit_info in commits.items() if
                       "date" in commit_info]

        if commit_list:
            data_frame = pd.DataFrame(commit_list)
            data_frame.drop(
                columns=[col for col in data_frame.columns if col.startswith("stats.by_module") or
                         col.startswith("stats.dependencies") or
                         col == "stats.repository_name" or
                         col == "stats.dependencies.util"],
                inplace=True)

            data_frame.set_index("date", inplace=True)
            cleaned_lint_data = data_frame.to_dict("index")
            clean_data[repo] = cleaned_lint_data

        else:
            clean_data[repo] = {}
            logging.error(f"Repository {repo} has no valid commits with dates.")

    return clean_data


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


def stargazers_over_time(stargazers_data: dict) -> dict:
    """Accumulates stargazers over time based on clean stargazers data"""

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


def remove_lint_messages(data: dict) -> dict:
    """Removes the messages from the pylint data"""
    for repo, value in data.items():
        if value is None:
            continue
        for commit, v in value.items():
            if v is None:
                continue
            v.pop("messages")
    return data


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


def dict_to_list(dictionary: dict) -> list:
    """Extracts all values from the dictionary, adds the keys and returns it wrapped in a list"""
    formatted_list = []
    for key, value in dictionary.items():
        if value is None:
            continue
        formatted_list.append(value)
    return formatted_list
