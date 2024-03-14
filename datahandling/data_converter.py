import logging
from collections import defaultdict
from collections.abc import MutableMapping
from datetime import datetime

def flatten_pydriller_data(metrics: dict) -> dict:
    """Flatten the Pydriller metrics to a single level dictionary."""
    flat_metrics = metrics
    for key, value in flat_metrics.items():
        flat_metrics[key] = _flatten_dict(value, sep=".")

    return flat_metrics


def flatten_pylint_data(metrics: dict) -> dict:
    """Flatten the Pylint metrics to a single level dictionary."""
    flat_metrics = metrics
    for key, value in flat_metrics.items():
        for k, v in value.items():
            flat_metrics[key][k] = v if not isinstance(v, dict) else _flatten_dict(v, sep=".")

    return flat_metrics


def clean_stargazers_data(stargazers_metrics: dict) -> dict:
    """Cleans the stargazers data to only contain the starred users and the time they starred the repository."""
    cleaned_metrics = {}
    for repo_key, item in stargazers_metrics.items():
        repository_data = item.get("data", {}).get("repository", {})
        edges = repository_data.get("stargazers", {}).get("edges", [])
        starred = {}
        for edge in edges:
            starred_at = edge.get("starredAt")
            user = edge.get("node", {}).get("login")
            starred[user] = starred_at

        cleaned_metrics[repo_key] = starred

    return cleaned_metrics


def get_stargazers_over_time(stargazers_metrics: dict) -> dict:
    """Gets the stargazers over time for each repository."""
    stars_over_time = defaultdict(dict)
    for repo, stargazers in stargazers_metrics.items():
        # Sort the stargazers by date
        sorted_dates = sorted(stargazers.values(), key=lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ"))

        star_count = 0
        for date in sorted_dates:
            star_count += 1

            # Convert date to just a date without time for daily granularity
            date_only = date.split("T")[0]

            # If the date already exists in the dictionary, update the star count for this repo
            if date_only in stars_over_time:
                stars_over_time[date_only][repo] = star_count
            else:
                stars_over_time[date_only][repo] = star_count

    # Normalize data to ensure every date has an entry for every repository
    all_dates = sorted(stars_over_time.keys())
    all_repos = stargazers_metrics.keys()
    for date in all_dates:
        for repo in all_repos:
            if repo not in stars_over_time[date]:

                # Find the last known star count for this repo and carry it forward
                previous_count = 0
                for previous_date in sorted(stars_over_time.keys()):
                    if previous_date >= date:
                        break
                    if repo in stars_over_time[previous_date]:
                        previous_count = stars_over_time[previous_date][repo]

                stars_over_time[date][repo] = previous_count

    return stars_over_time


def get_test_to_code_ratio_over_time(unit_testing_metrics: dict) -> dict:
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


def remove_pylint_messages(data: dict) -> dict:
    """Removes the messages from the pylint data"""
    for repo, value in data.items():
        if value is None:
            continue
        for commit, v in value.items():
            if v is None:
                continue
            v.pop("messages")
    return data


def _flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    """
    Flatten a nested dictionary. Takes nested keys, and uses them as prefixes.
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, MutableMapping):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


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
