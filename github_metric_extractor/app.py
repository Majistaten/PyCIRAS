from datetime import datetime
import repository_downloader
import git_extraction
import json
import code_aspect_analyzer
import csv_builder


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    repository_paths = repository_downloader.download_repositories(repo_url_file='../repos.txt',
                                                                   destination_folder='../repositories')
    metrics = git_extraction.mine_pydriller_metrics(repository_paths, clone_repo_to="../repositories")
    repo_commits = {v["repository_address"]: v["commits"] for (_, v) in metrics.items()}
    code_aspects = code_aspect_analyzer.mine_pylint_metrics(repo_commits)

    # TODO: removes messages. Fix a better solution
    for repo, value in code_aspects.items():
        if value is None:
            continue
        for commit, v in value.items():
            if v is None:
                continue
            v.pop("messages")

    flat_pydriller_metrics = csv_builder.flatten_pydriller_metrics(metrics)
    flat_pylint_metrics = csv_builder.flatten_pylint_metrics(code_aspects)

    with open('./test_out.json', 'w') as file:
        json.dump(flat_pydriller_metrics, file, indent=4)
        csv_builder.write_pydriller_metrics_to_csv(flat_pydriller_metrics)

    with open('./test_code_aspects.json', 'w') as file:
        json.dump(flat_pylint_metrics, file, indent=4, cls=CustomEncoder)
        csv_builder.write_pylint_metrics_to_csv(flat_pylint_metrics)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
