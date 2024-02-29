from datetime import datetime
import csv
import itertools
from collections.abc import MutableMapping
import repository_downloader
import git_extraction
import logging
import json
import code_aspect_analyzer
import pandas as pd
import csv_builder


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def pandas_flatten_dict(d: MutableMapping, sep: str = '.', max_level=None) -> MutableMapping:
    [flat_dict] = pd.json_normalize(d, sep=sep, max_level=None).to_dict(orient='records')
    return flat_dict


def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    repository_paths = repository_downloader.download_repositories(repo_url_file='../repos.txt',
                                                                   destination_folder='../repositories')
    metrics = git_extraction.process_repositories(repository_paths, clone_repo_to="../repositories")
    repo_commits = {v["repository_address"]: v["commits"] for (_, v) in metrics.items()}
    code_aspects = code_aspect_analyzer.analyze_repositories_commits(repo_commits)

    with open('./test_out.json', 'w') as file:
        flat_pydriller_metrics = csv_builder.flatten_pydriller_metrics(metrics)
        json.dump(flat_pydriller_metrics, file, indent=4)

    with open('./test_code_aspects.json', 'w') as file:
        flat_pylint_metrics = csv_builder.flatten_pylint_metrics(metrics)
        json.dump(flat_pylint_metrics, file, indent=4, cls=CustomEncoder)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
