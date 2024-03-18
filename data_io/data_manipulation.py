"""This module provides functionality for data manipulation and processing."""

import logging
from collections import defaultdict
from collections.abc import MutableMapping
from datetime import datetime
from rich.pretty import pprint
import pandas as pd


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
        clean_data[repo] = {}
        for commit_hash, lint_data in commits.items():
            try:
                date = lint_data.pop("date")
            except Exception as e:
                logging.error(f"Commit {commit_hash} in repository {repo} has no date. Skipping. \nError: {e}")
                continue
            cleaned_lint_data = {}
            for key, value in lint_data.items():
                if key.startswith("stats.by_module") \
                        or key.startswith("stats.dependencies") \
                        or key == "stats.repository_name" \
                        or key == "stats.dependencies.util":
                    continue

                cleaned_lint_data[key] = value

            clean_data[repo][date] = {
                "commit_hash": commit_hash,
                **cleaned_lint_data
            }

    return clean_data


def clean_stargazers_data(data: dict) -> dict:
    """Cleans stargazers data."""

    clean_data = {}
    for repo, stargazers_data in data.items():
        edges = stargazers_data \
            .get("data", {}) \
            .get("repository", {}) \
            .get("stargazers", {}) \
            .get("edges", [])

        starred = {}
        for edge in edges:
            starred_at = edge.get("starredAt")
            user = edge.get("node", {}).get("login")
            starred[user] = starred_at

        clean_data[repo] = starred

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


def get_test_data_over_time(unit_testing_metrics: dict) -> dict:
    """Gets the test-to-code-ratio over time for each repository."""
    test_info_over_time = defaultdict(lambda: defaultdict(dict))
    for repo, metrics in unit_testing_metrics.items():
        for commit_hash, data in metrics.items():
            try:
                date_str = str(data['date'])
                test_to_code_ratio = data['test-to-code-ratio']
                test_frameworks = set()
                # Aggregate unique imports from each file
                for file_details in data['files'].values():
                    for import_item in file_details['imports']:
                        test_frameworks.add(import_item)
                test_frameworks = sorted(list(test_frameworks))
                test_classes = sum(len(file.get('unittest_classes', [])) for file in data['files'].values())
                test_functions = sum(len(file.get('pytest_functions', [])) for file in data['files'].values())

                test_info_over_time[repo][date_str] = {
                    'test-to-code-ratio': test_to_code_ratio,
                    'test-classes': test_classes,
                    'test-functions': test_functions,
                    'test-frameworks': test_frameworks
                }

            except TypeError as e:
                logging.error(f"Error when compiling test-to-code-ratio metrics for "
                              f"{repo} commit {commit_hash}: " + str(e) + "\nSkipping this commit.")
                continue
            except Exception as e:
                logging.error(f"Unexpected Error when compiling test-to-code-ratio metrics for "
                              f"{repo} commit {commit_hash}: " + str(e) + "\nSkipping this commit.")
                continue

    return test_info_over_time


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


# TODO remove insert_key_as, skickas alltid in som None - inget syfte
# TODO få bort mutablemapping?
def dict_to_list(dictionary: dict | MutableMapping, insert_key_as: str | None = None) -> list:
    """Extracts all values from the dictionary, adds the keys and returns it wrapped in a list"""
    formatted_list = []
    for key, value in dictionary.items():
        if value is None:
            continue
        if insert_key_as is not None:
            value[insert_key_as] = key
        formatted_list.append(value)
    return formatted_list
