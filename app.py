from datetime import datetime
from github_metric_extractor import repo_cloner
from github_metric_extractor import git_miner
from github_metric_extractor import csv_builder
from github_metric_extractor import code_quality
import json
import config
from datahandling import data_writer

# config.REPOSITORIES_FOLDER = 'repositories/'


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


# TODO skapa möjligheten att dra gång flera processer som analyserar samtidigt och skriver resultat efter varje analys

def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    repository_paths = repo_cloner.download_repositories(repo_url_file=config.REPOSITORY_URLS,
                                                         destination_folder=config.REPOSITORIES_FOLDER)
    addr = []
    with open(config.REPOSITORY_URLS, 'r') as file:
        for line in file:
            addr.append(line)

    metrics = git_miner.mine_pydriller_metrics(addr, repository_directory=config.REPOSITORIES_FOLDER)
    repo_commits = git_miner.get_commit_dates(repository_paths, repository_directory=config.REPOSITORIES_FOLDER)
    code_aspects = code_quality.mine_pylint_metrics(repo_commits)

    # TODO: removes messages - find a better solution
    for repo, value in code_aspects.items():
        if value is None:
            continue
        for commit, v in value.items():
            if v is None:
                continue
            v.pop("messages")

    flat_pydriller_metrics = csv_builder.flatten_pydriller_metrics(metrics)
    flat_pylint_metrics = csv_builder.flatten_pylint_metrics(code_aspects)

    # Create data directory for the analysis
    data_directory = data_writer.create_timestamped_data_directory()

    # write json to file
    data_writer.pydriller_data_json(flat_pydriller_metrics, data_directory)
    data_writer.pylint_data_json(flat_pylint_metrics, data_directory)

    # write csv to file
    data_writer.pydriller_data_csv(flat_pydriller_metrics, data_directory)
    data_writer.pylint_data_csv(flat_pylint_metrics, data_directory)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
